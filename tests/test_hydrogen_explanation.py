"""Offline tests for saved-result explanations using Gemini 4 Hydrogen."""
import importlib.util
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from google import genai
import httpx
import pytest

from backend import cli as app_cli
from backend.api.main import create_app
from backend.core import analyst
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
    for key in ("GEMINI_EXPLANATION_MODEL", "MISTRAL_EXPLANATION_MODEL", "CHAT_MODEL", "MEMORY_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        if value is not None:
            monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("_isolated_explain_config", Path(config.__file__))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gemini_explanation_model_default_override_and_isolation(monkeypatch):
    assert "GEMINI_EXPLANATION_MODEL" in streamlit_support._SECRET_KEYS
    default_cfg = _load_isolated_config(monkeypatch)
    assert default_cfg.GEMINI_EXPLANATION_MODEL == "gemini-4-hydrogen"
    assert not hasattr(default_cfg, "EXPLANATION_MODEL")

    mistral_env_cfg = _load_isolated_config(monkeypatch, MISTRAL_EXPLANATION_MODEL="custom-mistral-exp")
    assert mistral_env_cfg.GEMINI_EXPLANATION_MODEL == "gemini-4-hydrogen"
    assert not hasattr(mistral_env_cfg, "EXPLANATION_MODEL")

    override_cfg = _load_isolated_config(monkeypatch, GEMINI_EXPLANATION_MODEL="custom-hydrogen")
    assert override_cfg.GEMINI_EXPLANATION_MODEL == "custom-hydrogen"


def test_installed_hydrogen_sdk_serializes_stream_and_nonstream_with_low_thinking(monkeypatch):
    real_client = genai.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    requests, updates, events = [], [], []

    def respond_stream(request):
        requests.append(request)
        frames = [
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "Summed ", "thought": False}]}}]},
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "internal", "thought": True}, {"text": "Sales."}]}}]},
            {
                "candidates": [{"content": {"role": "model", "parts": []}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 60, "candidatesTokenCount": 8, "thoughtsTokenCount": 4, "totalTokenCount": 72},
            },
        ]
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content="".join("data: " + json.dumps(f) + "\n\n" for f in frames))

    monkeypatch.setattr(genai, "Client", lambda **kw: real_client(**{
        **kw,
        "http_options": kw["http_options"].model_copy(update={"httpx_client": httpx.Client(transport=httpx.MockTransport(respond_stream))}),
    }))
    with telemetry.observe(events), delivery.observe(lambda k, v: updates.append((k, v)), threading.Event()):
        assert llm_clients.call_saved_explanation_llm("Explain sum") == "Summed Sales."
    assert [v["answer"] for k, v in updates if k == "text"] == ["Summed ", "Summed Sales."]
    assert config.GEMINI_EXPLANATION_MODEL in str(requests[0].url)
    assert "streamGenerateContent" in str(requests[0].url)
    payload = json.loads(requests[0].content)
    assert payload["generationConfig"]["maxOutputTokens"] == config.MAX_RESPONSE_TOKENS
    assert payload["generationConfig"]["thinkingConfig"]["thinking_level"] == "LOW"
    summary = telemetry.summarize(events)
    assert summary["complete"] is True and summary["total"] == 72
    assert summary["calls"][0]["provider"] == "Gemini"
    assert summary["calls"][0]["model"] == config.GEMINI_EXPLANATION_MODEL
    assert summary["calls"][0]["reasoning"] == 4

    # Non-streamed CLI/Streamlit path
    requests.clear()
    events.clear()
    monkeypatch.setattr(genai, "Client", lambda **kw: real_client(**{
        **kw,
        "http_options": kw["http_options"].model_copy(update={
            "httpx_client": httpx.Client(transport=httpx.MockTransport(lambda req: (
                requests.append(req),
                httpx.Response(200, json={
                    "candidates": [{"content": {"role": "model", "parts": [{"text": "Buffered Hydrogen explanation."}]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 40, "candidatesTokenCount": 6, "totalTokenCount": 46},
                }),
            )[1]))
        }),
    }))
    with telemetry.observe(events):
        assert llm_clients.call_saved_explanation_llm("Explain sum") == "Buffered Hydrogen explanation."
    assert "generateContent" in str(requests[0].url) and "streamGenerateContent" not in str(requests[0].url)
    assert telemetry.summarize(events)["total"] == 46


def test_saved_calculation_followup_calls_hydrogen_without_code_or_worker(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **k: {"choice": "analysis", "confidence": 0.96})
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: "result = df['Sales'].sum()")
    monkeypatch.setattr(analyst, "write_answer", lambda *a, **k: "Total Sales are 1,000.")
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Note.")

    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    calc = buddy.ask("What is total Sales?")
    assert calc.result_text == "1000"

    seen_prompts = []
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: pytest.fail("Explain must not generate code"))
    monkeypatch.setattr(analyst, "generate_chart_code", lambda *a, **k: pytest.fail("Explain must not generate chart code"))
    monkeypatch.setattr(executor, "run_code", lambda *a, **k: pytest.fail("Explain must not execute Python"))

    fake = MagicMock()
    fake.__enter__.return_value = fake

    def fake_generate(*, model, contents, config):
        seen_prompts.append((model, contents))
        return SimpleNamespace(
            text="I summed the Sales column across all four rows using df['Sales'].sum(), giving 1000.",
            usage_metadata=SimpleNamespace(prompt_token_count=50, candidates_token_count=15, total_token_count=65),
        )

    fake.models.generate_content.side_effect = fake_generate
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))

    explained = buddy.ask("How did you get 1,000?")
    assert explained.status == "success"
    assert "df['Sales'].sum()" in explained.answer
    assert len(seen_prompts) == 1
    model, prompt = seen_prompts[0]
    assert model == config.GEMINI_EXPLANATION_MODEL
    assert "What is total Sales?" in prompt
    assert "df['Sales'].sum()" in prompt
    assert "1000" in prompt
    assert "How did you get 1,000?" in prompt


def test_saved_chart_followup_calls_hydrogen_without_regenerating_chart(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **k: {"choice": "visualization", "confidence": 0.96})
    monkeypatch.setattr(
        analyst,
        "generate_chart_code",
        lambda *a, **k: "result = df.groupby('Region')['Sales'].sum()\nfig = px.bar(x=result.index, y=result.values)\nchart_description = 'Sales by Region'",
    )
    monkeypatch.setattr(analyst, "write_chart_insight", lambda *a, **k: "North is 400 and South is 600.")
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Chart note.")

    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    chart = buddy.ask("Chart total Sales by Region")
    assert chart.chart_json

    seen_prompts = []
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **k: {"choice": "explain_analysis", "confidence": 0.95})
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: pytest.fail("Explain must not generate code"))
    monkeypatch.setattr(analyst, "generate_chart_code", lambda *a, **k: pytest.fail("Explain must not regenerate chart"))
    monkeypatch.setattr(executor, "run_code", lambda *a, **k: pytest.fail("Explain must not run worker"))

    fake = MagicMock()
    fake.__enter__.return_value = fake

    def fake_generate(*, model, contents, config):
        seen_prompts.append((model, contents))
        return SimpleNamespace(
            text="The bar chart grouped Sales by Region, producing North 400 and South 600.",
            usage_metadata=SimpleNamespace(prompt_token_count=60, candidates_token_count=15, total_token_count=75),
        )

    fake.models.generate_content.side_effect = fake_generate
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))

    explained = buddy.ask("Explain how that chart was calculated")
    assert explained.status == "success"
    assert explained.chart_json is None
    assert len(seen_prompts) == 1
    assert "groupby('Region')['Sales'].sum()" in seen_prompts[0][1]
    assert "400" in seen_prompts[0][1] and "600" in seen_prompts[0][1]


def test_explanation_prompt_bounds_prioritize_computed_evidence_over_narration(monkeypatch):
    monkeypatch.setattr(config, "MAX_PROMPT_CHARS", 1200)
    captured = []
    monkeypatch.setattr(message_handler, "call_saved_explanation_llm", lambda p: captured.append(p) or "Explained.")
    last = {
        "question": "Total Sales?",
        "code": "result = df['Sales'].sum()",
        "result": "EVIDENCE_1000",
        "answer": "PRIOR_NARRATION " + ("X" * 5000),
    }
    assert message_handler.answer_explanation("How did you get 1,000?", last) == "Explained."
    prompt = captured[0]
    assert len(prompt) <= 1200
    assert "EVIDENCE_1000" in prompt
    assert "result = df['Sales'].sum()" in prompt
    assert "How did you get 1,000?" in prompt


def test_explanation_without_prior_result_does_not_call_model(monkeypatch):
    monkeypatch.setattr(message_handler, "call_saved_explanation_llm", lambda *_: pytest.fail("Must not call model"))
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: pytest.fail("Must not generate code"))
    monkeypatch.setattr(executor, "run_code", lambda *a, **k: pytest.fail("Must not run worker"))
    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    result = buddy.ask("How was that calculated?")
    assert "don’t have a previous successful analysis" in result.answer
    assert result.result_text is None and result.code is None


def test_explanation_failure_preserves_evidence_and_partial_text_while_cancellation_stays_stopped(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Note.")

    # 1. Provider failure before any streamed text preserves saved result and code.
    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    buddy.conversation.last_analysis = {
        "question": "Total Sales?",
        "code": "result = df['Sales'].sum()",
        "result": "1000",
        "answer": "Total Sales are 1,000.",
    }
    monkeypatch.setattr(
        message_handler,
        "call_saved_explanation_llm",
        MagicMock(side_effect=llm_clients.ProviderError("Gemini rejected the request.")),
    )
    failed = buddy.ask("How did you calculate that?")
    assert failed.status == "partial"
    assert "unavailable" in failed.answer
    assert failed.result_text == "1000"
    assert failed.code == "result = df['Sales'].sum()"

    # 2. Mid-stream failure preserves delivered partial text and saved evidence.
    def midstream_fail(_prompt):
        delivery.text("I summed the Sales column ")
        raise llm_clients.ProviderUnavailableError("Gemini took too long to respond.")

    monkeypatch.setattr(message_handler, "call_saved_explanation_llm", midstream_fail)
    with delivery.observe(lambda *_: None, delivery.Cancellation()):
        partial = buddy.ask("How did you calculate that?")
    assert partial.status == "partial"
    assert partial.answer.startswith("I summed the Sales column ")
    assert "unavailable" in partial.answer
    assert partial.result_text == "1000"
    assert partial.code == "result = df['Sales'].sum()"

    # 3. Cancellation stays distinct as stopped (not provider failure).
    token = delivery.Cancellation()

    def cancelled_stream(_prompt):
        delivery.text("First part ")
        token.set()
        delivery.check_cancelled()
        return "First part second"

    monkeypatch.setattr(message_handler, "call_saved_explanation_llm", cancelled_stream)
    with delivery.observe(lambda *_: None, token):
        stopped = buddy.ask("How did you calculate that?")
    assert stopped.status == "stopped"
    assert "First part " in stopped.answer
    assert "Response stopped." in stopped.answer
    assert "unavailable" not in stopped.answer


def test_web_sse_cli_and_streamlit_explain_with_hydrogen(monkeypatch, capsys):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "GROQ_API_KEY", None)
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Explained saved total.")

    fake = MagicMock()
    fake.__enter__.return_value = fake

    def stream_explain(**kwargs):
        assert kwargs["model"] == config.GEMINI_EXPLANATION_MODEL
        yield SimpleNamespace(text="Summed ", candidates=[SimpleNamespace(finish_reason=None)], usage_metadata=None)
        time.sleep(0.06)
        yield SimpleNamespace(
            text="Sales = 1000.",
            candidates=[SimpleNamespace(finish_reason="STOP")],
            usage_metadata=SimpleNamespace(prompt_token_count=35, candidates_token_count=7, total_token_count=42),
        )

    fake.models.generate_content_stream.side_effect = stream_explain
    fake.models.generate_content.side_effect = lambda **kwargs: SimpleNamespace(
        text="Buffered explanation: Sales summed to 1000.",
        usage_metadata=SimpleNamespace(prompt_token_count=35, candidates_token_count=7, total_token_count=42),
    )
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))

    # Web API streaming + single turn/charge/memory + usage attribution
    with TestClient(create_app()) as client:
        headers = {"Authorization": "Bearer " + client.post("/api/session").json()["token"]}
        assert client.post("/api/sample", headers=headers).status_code == 200
        token = headers["Authorization"].split()[1]
        session = client.app.state.sessions[token]
        session.buddy.conversation.last_analysis = {
            "question": "Total Sales?",
            "code": "result = df['Sales'].sum()",
            "result": "1000",
            "answer": "Total Sales are 1,000.",
        }
        key = "explain-hyd-0001"
        assert client.post("/api/messages", headers=headers, json={"question": "How did you get 1,000?", "request_id": key}).status_code == 202
        seen_answers = []
        with client.stream("GET", f"/api/jobs/{key}/events", headers=headers) as stream:
            for line in stream.iter_lines():
                if line.startswith("data:"):
                    payload = json.loads(line[5:])
                    if payload.get("answer"):
                        seen_answers.append(payload["answer"])
        for _ in range(300):
            state = client.get("/api/session", headers=headers).json()
            if state["job"]["state"] == "done":
                break
            time.sleep(0.01)
        assert len(seen_answers) >= 2 and seen_answers[0] == "Summed "
        assert seen_answers[-1] == "Summed Sales = 1000."
        assert len(state["turns"]) == 1
        assert state["turns"][0]["answer"] == "Summed Sales = 1000."
        assert state["usage"]["used"] == 1
        assert state["usage"]["total"] == 42
        assert state["usage"]["calls"][0]["provider"] == "Gemini"
        assert state["usage"]["calls"][0]["model"] == config.GEMINI_EXPLANATION_MODEL

    # CLI complete reply
    buddy = databuddy.DataBuddy(SAMPLE_CSV, filename="sample.csv")
    buddy.conversation.last_analysis = {
        "question": "Total Sales?",
        "code": "result = df['Sales'].sum()",
        "result": "1000",
        "answer": "1000",
    }
    monkeypatch.setattr(app_cli, "DataBuddy", lambda _: buddy)
    monkeypatch.setattr(app_cli.sys, "argv", ["app.py", "sample.csv"])
    answers = iter(["How did you get 1,000?", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    app_cli.main()
    assert "Buffered explanation: Sales summed to 1000." in capsys.readouterr().out

    # Streamlit complete reply
    root = Path(__file__).resolve().parents[1]
    st_app = AppTest.from_file(str(root / "web_app.py")).run(timeout=15)
    st_app = st_app.get("file_uploader")[0].set_value(("sales.csv", b"region,sales\nNorth,10\n", "text/csv")).run(timeout=15)
    st_app.session_state["buddy"].conversation.last_analysis = {
        "question": "Total Sales?",
        "code": "result = df['Sales'].sum()",
        "result": "10",
        "answer": "10",
    }
    st_app.chat_input[0].set_value("How did you calculate that?").run(timeout=15)
    assert not st_app.exception
    assert any(item.value == "Buffered explanation: Sales summed to 1000." for item in st_app.markdown)


def test_groq_narration_fallback_uses_hydrogen_without_mistral_settings(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODEL", "gemini-4-hydrogen")
    monkeypatch.setattr(llm_clients, "_groq_completion", MagicMock(side_effect=llm_clients.ProviderUnavailableError("Groq down")))
    gemini = MagicMock(return_value="Hydrogen narration fallback")
    monkeypatch.setattr(llm_clients, "_gemini_generate", gemini)
    assert llm_clients.call_narration_llm("computed evidence") == "Hydrogen narration fallback"
    assert gemini.call_args.kwargs["model"] == "gemini-4-hydrogen"
    assert not hasattr(config, "EXPLANATION_MODEL")
    assert not hasattr(llm_clients, "call_explanation_llm")
