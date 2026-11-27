"""Offline tests for Gemini 4 Hydrogen fallback behind Groq analysis and narration."""
import importlib.util
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from google import genai
import groq
import httpx
import pytest

from backend import cli as app_cli
from backend.api.main import create_app
from backend.core import config
from backend.core import conversation_state
from backend.core import databuddy
from backend.core import executor
from backend.core import llm_clients
from backend.core import message_handler
from backend.core import response_stream as delivery
from backend.core import telemetry
from backend.legacy import streamlit_support


SAMPLE_CSV = (
    b"Month,Region,Product,Sales,Units\n"
    b"2026-01-01,North,Notebook,100,2\n"
    b"2026-01-01,South,Pen,200,4\n"
    b"2026-02-01,North,Pen,300,6\n"
    b"2026-02-01,South,Notebook,400,8\n"
)


def _load_isolated_config(monkeypatch, **env):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: False)
    for key in ("GEMINI_FALLBACK_MODEL", "GEMINI_EXPLANATION_MODEL", "MISTRAL_FALLBACK_MODEL", "MEMORY_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        if value is not None:
            monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("_isolated_fallback_config", Path(config.__file__))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gemini_fallback_model_default_override_and_isolation(monkeypatch):
    assert "GEMINI_FALLBACK_MODEL" in streamlit_support._SECRET_KEYS
    default_cfg = _load_isolated_config(monkeypatch)
    assert default_cfg.GEMINI_FALLBACK_MODEL == "gemini-4-hydrogen"
    assert default_cfg.GEMINI_EXPLANATION_MODEL == "gemini-4-hydrogen"
    assert default_cfg.FALLBACK_MODEL == "ministral-14b-latest"

    override_cfg = _load_isolated_config(
        monkeypatch,
        GEMINI_FALLBACK_MODEL="custom-fallback-hydrogen",
        GEMINI_EXPLANATION_MODEL="custom-explain-hydrogen",
    )
    assert override_cfg.GEMINI_FALLBACK_MODEL == "custom-fallback-hydrogen"
    assert override_cfg.GEMINI_EXPLANATION_MODEL == "custom-explain-hydrogen"


def test_groq_success_and_hydrogen_fallback_for_calculation_and_chart_without_mistral(monkeypatch):
    real_groq = groq.Groq
    real_genai = genai.Client
    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-groq-key")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", None)
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **k: {
        "choice": "visualization" if "Chart" in a[0] else ("modify_chart" if "title" in a[0].lower() else "analysis"),
        "confidence": 0.96,
    })
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Note.")

    # 1. Groq succeeds normally for calculation.
    def groq_ok(request):
        body = json.loads(request.content)
        content = "result = df['Sales'].sum()" if "code generator" in body["messages"][0]["content"] else "Total Sales are 1,000."
        return httpx.Response(200, json={
            "id": "g1", "object": "chat.completion", "created": 1, "model": config.ANALYSIS_MODEL,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        })

    monkeypatch.setattr(groq, "Groq", lambda **kw: real_groq(**kw, http_client=httpx.Client(transport=httpx.MockTransport(groq_ok))))
    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    ok_calc = buddy.ask("What is total Sales?")
    assert ok_calc.status == "success" and ok_calc.result_text == "1000"

    # 2. Groq returns 503 for code & chart (including chart edit); Hydrogen falls back buffered and feeds Python worker.
    gemini_requests = []

    def groq_503(request):
        return httpx.Response(503, json={"error": {"message": "Groq down"}})

    def gemini_fallback(request):
        gemini_requests.append((str(request.url), json.loads(request.content)))
        prompt = gemini_requests[-1][1]["contents"][0]["parts"][0]["text"]
        if "visualization code generator" in prompt:
            text = (
                "```python\n"
                "result = df.groupby('Region')['Sales'].sum()\n"
                "fig = px.bar(x=result.index, y=result.values, title='Sales')\n"
                "chart_description = 'Sales by Region'\n"
                "```"
            )
        elif "data-analysis code generator" in prompt:
            text = "```python\nresult = df['Sales'].sum()\n```"
        else:
            text = "Hydrogen fallback explanation."
        return httpx.Response(200, json={
            "candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 40, "candidatesTokenCount": 12, "totalTokenCount": 52},
        })

    monkeypatch.setattr(groq, "Groq", lambda **kw: real_groq(**kw, http_client=httpx.Client(transport=httpx.MockTransport(groq_503))))
    monkeypatch.setattr(genai, "Client", lambda **kw: real_genai(**{
        **kw,
        "http_options": kw["http_options"].model_copy(update={"httpx_client": httpx.Client(transport=httpx.MockTransport(gemini_fallback))}),
    }))

    events = []
    with telemetry.observe(events):
        fb_calc = buddy.ask("What is total Sales?")
        fb_chart = buddy.ask("Chart total Sales by Region")
        fb_edit = buddy.ask("Change the chart title to Regional Sales")
    assert fb_calc.status == "success" and fb_calc.result_text == "1000"
    assert fb_chart.status == "success" and fb_chart.chart_json
    assert "400" in fb_chart.result_text and "600" in fb_chart.result_text
    assert fb_edit.status == "success" and fb_edit.chart_json
    assert len(gemini_requests) == 6
    assert all(config.GEMINI_FALLBACK_MODEL in url for url, _ in gemini_requests)
    assert all(body["generationConfig"]["thinkingConfig"]["thinking_level"] == "LOW" for _, body in gemini_requests)
    summary = telemetry.summarize(events)
    assert summary["fallbacks"] == 6


def test_interrupted_groq_narration_streams_hydrogen_without_rerunning_worker(monkeypatch):
    real_groq = groq.Groq
    real_genai = genai.Client
    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-groq-key")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", None)
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **k: {"choice": "analysis", "confidence": 0.96})
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Total Sales 1000.")

    worker_calls = 0
    orig_run_code = executor.run_code

    def counted_worker(code, df):
        nonlocal worker_calls
        worker_calls += 1
        return orig_run_code(code, df)

    monkeypatch.setattr(executor, "run_code", counted_worker)

    def groq_handler(request):
        body = json.loads(request.content)
        if not body.get("stream"):
            return httpx.Response(200, json={
                "id": "g1", "object": "chat.completion", "created": 1, "model": config.ANALYSIS_MODEL,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "result = df['Sales'].sum()"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
            })
        # Emit partial SSE chunk then end without finish_reason so stream fails midstream!
        frame = {"id": "g2", "created": 1, "model": config.ANALYSIS_MODEL, "object": "chat.completion.chunk",
                 "choices": [{"index": 0, "delta": {"content": "Partial Groq draft "}, "finish_reason": None}]}
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content="data: " + json.dumps(frame) + "\n\n")

    def gemini_stream(request):
        frames = [
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "Hydrogen total "}]}}]},
            {
                "candidates": [{"content": {"role": "model", "parts": [{"text": "is 1,000."}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 40, "candidatesTokenCount": 8, "totalTokenCount": 48},
            },
        ]
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content="".join("data: " + json.dumps(f) + "\n\n" for f in frames))

    monkeypatch.setattr(groq, "Groq", lambda **kw: real_groq(**kw, http_client=httpx.Client(transport=httpx.MockTransport(groq_handler))))
    monkeypatch.setattr(genai, "Client", lambda **kw: real_genai(**{
        **kw,
        "http_options": kw["http_options"].model_copy(update={"httpx_client": httpx.Client(transport=httpx.MockTransport(gemini_stream))}),
    }))

    with TestClient(create_app()) as client:
        headers = {"Authorization": "Bearer " + client.post("/api/session").json()["token"]}
        assert client.post("/api/sample", headers=headers).status_code == 200
        key = "groq-to-hyd-0001"
        assert client.post("/api/messages", headers=headers, json={"question": "What is total Sales?", "request_id": key}).status_code == 202
        updates = []
        with client.stream("GET", f"/api/jobs/{key}/events", headers=headers) as stream:
            for line in stream.iter_lines():
                if line.startswith("data:"):
                    updates.append(json.loads(line[5:]))
        for _ in range(300):
            state = client.get("/api/session", headers=headers).json()
            if state["job"]["state"] == "done":
                break
            time.sleep(0.01)

    assert worker_calls == 1
    assert any(u.get("notice") == "The explanation was interrupted. Restarting with the backup provider." for u in updates)
    assert len(state["turns"]) == 1
    assert state["usage"]["used"] == 1
    assert state["turns"][0]["answer"] == "Hydrogen total is 1,000."
    assert "Partial Groq draft" not in state["turns"][0]["answer"]
    assert state["turns"][0]["result_text"] == "1000"
    assert state["usage"]["fallbacks"] == 1
    assert any(c["provider"] == "Gemini" and c["model"] == config.GEMINI_FALLBACK_MODEL for c in state["usage"]["calls"])


def test_missing_backup_key_and_expired_or_short_budget_do_not_claim_fallback(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-groq-key")
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(llm_clients, "_groq_completion", MagicMock(side_effect=llm_clients.ProviderUnavailableError("Groq down")))

    # 1. Missing GEMINI_API_KEY -> no fallback event recorded, evidence preserved in DataBuddy.
    events = []
    with telemetry.observe(events):
        with pytest.raises(llm_clients.ProviderUnavailableError, match="Gemini fallback is not configured"):
            llm_clients.call_narration_llm("computed evidence")
    assert telemetry.summarize(events)["fallbacks"] == 0

    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **k: {"choice": "analysis", "confidence": 0.96})
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Note.")
    monkeypatch.setattr(llm_clients, "_groq_completion", lambda prompt, *a, **kw: (
        "result = df['Sales'].sum()" if "code generator" in prompt
        else (_ for _ in ()).throw(llm_clients.ProviderUnavailableError("Groq narration down"))
    ))
    partial = buddy.ask("What is total Sales?")
    assert partial.status == "partial" and partial.result_text == "1000" and partial.code

    # 2. Expired or <10s remaining budget after primary failure -> no fallback event or Gemini call!
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    gemini_factory = MagicMock()
    monkeypatch.setattr(genai, "Client", gemini_factory)
    clock = [100.0]
    monkeypatch.setattr(llm_clients.time, "monotonic", lambda: clock[0])

    def expire_primary(*a, **kw):
        clock[0] = 125.0  # Exceeds 20s outer budget.
        raise llm_clients.ProviderUnavailableError("Groq timed out")

    monkeypatch.setattr(llm_clients, "_groq_completion", expire_primary)
    events.clear()
    with telemetry.observe(events), llm_clients.request_budget(seconds=20):
        with pytest.raises(llm_clients.ProviderUnavailableError, match="time limit"):
            llm_clients.call_narration_llm("evidence")
    assert telemetry.summarize(events)["fallbacks"] == 0
    gemini_factory.assert_not_called()

    # 3. Tight 15s budget reserves >= 10.1s for Gemini so Hydrogen CAN run!
    fake = MagicMock()
    fake.__enter__.return_value = fake
    fake.models.generate_content.return_value = SimpleNamespace(
        text="Hydrogen saved it.",
        usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5, total_token_count=15),
    )
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))
    clock[0] = 100.0

    def slow_primary(*a, **kw):
        clock[0] = llm_clients._deadline.get()
        raise llm_clients.ProviderUnavailableError("Groq slice elapsed")

    monkeypatch.setattr(llm_clients, "_groq_completion", slow_primary)
    events.clear()
    with telemetry.observe(events), llm_clients.request_budget(seconds=15):
        assert llm_clients.call_narration_llm("evidence") == "Hydrogen saved it."
    assert telemetry.summarize(events)["fallbacks"] == 1
    assert genai.Client.call_args.kwargs["http_options"].timeout >= 10000


def test_narration_fallback_propagates_cancellation(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-groq-key")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", None)
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)

    token = delivery.Cancellation()
    backup_called = []

    def cancel_primary(*a, **kw):
        token.set()
        delivery.check_cancelled()

    monkeypatch.setattr(llm_clients, "_groq_completion", cancel_primary)
    monkeypatch.setattr(llm_clients, "call_narration_fallback_llm", lambda *a: backup_called.append(a))
    with delivery.observe(lambda *_: None, token):
        with pytest.raises(delivery.ResponseCancelled):
            llm_clients.call_narration_llm("evidence")
    assert not backup_called


def test_cli_and_streamlit_receive_buffered_hydrogen_fallback(monkeypatch, capsys):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-groq-key")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", None)
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **k: {"choice": "analysis", "confidence": 0.96})
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Note.")

    monkeypatch.setattr(llm_clients, "_groq_completion", lambda prompt, *a, **kw: (
        "result = df['Sales'].sum()" if "code generator" in prompt
        else (_ for _ in ()).throw(llm_clients.ProviderUnavailableError("Groq narration down"))
    ))
    fake = MagicMock()
    fake.__enter__.return_value = fake
    fake.models.generate_content.return_value = SimpleNamespace(
        text="Buffered Hydrogen fallback: Sales sum is 1000.",
        usage_metadata=SimpleNamespace(prompt_token_count=20, candidates_token_count=8, total_token_count=28),
    )
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))

    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    monkeypatch.setattr(app_cli, "DataBuddy", lambda _: buddy)
    monkeypatch.setattr(app_cli.sys, "argv", ["app.py", "sample.csv"])
    answers = iter(["What is total Sales?", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    app_cli.main()
    assert "Buffered Hydrogen fallback: Sales sum is 1000." in capsys.readouterr().out

    root = Path(__file__).resolve().parents[1]
    st_app = AppTest.from_file(str(root / "web_app.py")).run(timeout=15)
    st_app = st_app.get("file_uploader")[0].set_value(("sales.csv", b"region,Sales\nNorth,1000\n", "text/csv")).run(timeout=15)
    st_app.chat_input[0].set_value("What is total Sales?").run(timeout=15)
    assert not st_app.exception
    assert any(item.value == "Buffered Hydrogen fallback: Sales sum is 1000." for item in st_app.markdown)


def test_saved_explanation_and_memory_paths_remain_intact(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "offline-mistral-key")
    monkeypatch.setattr(config, "GEMINI_EXPLANATION_MODEL", "saved-hydrogen")
    monkeypatch.setattr(config, "MEMORY_MODEL", "gemini-3.5-flash-lite")

    gemini = MagicMock(return_value="Saved Hydrogen reply")
    monkeypatch.setattr(llm_clients, "_gemini_generate", gemini)
    assert llm_clients.call_saved_explanation_llm("Explain") == "Saved Hydrogen reply"
    assert gemini.call_args.kwargs["model"] == "saved-hydrogen"

    # Memory still falls back to Mistral on transient Gemini failure.
    gemini_fail = MagicMock(side_effect=llm_clients.ProviderUnavailableError("Gemini memory down"))
    mistral = MagicMock(return_value="Mistral memory note")
    monkeypatch.setattr(llm_clients, "_gemini_completion", gemini_fail)
    monkeypatch.setattr(llm_clients, "_mistral_completion", mistral)
    assert llm_clients.call_memory_llm("exchange") == "Mistral memory note"
    mistral.assert_called_once()
