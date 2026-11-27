"""Offline tests for Gemini 3.1 Flash-Lite ordinary chat, streaming, CLI and Streamlit."""
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from google import genai
from google.genai.errors import APIError

from backend import cli as app_cli
from backend.api.main import create_app
from backend.core import analyst
from backend.core import config
from backend.core import conversation_state
from backend.core import databuddy
from backend.core import llm_clients
from backend.core import message_handler
from backend.core import response_stream as delivery
from backend.core import telemetry
from backend.legacy import streamlit_support


def _load_isolated_config(monkeypatch, **env):
    import importlib.util
    from pathlib import Path

    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: False)
    for key in ("ROUTER_MODEL", "CHAT_MODEL", "MEMORY_MODEL", "MISTRAL_CHAT_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        if value is not None:
            monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("_isolated_chat_config", Path(config.__file__))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_chat_model_default_override_and_isolation_from_memory_and_mistral(monkeypatch):
    assert "CHAT_MODEL" in streamlit_support._SECRET_KEYS
    default_cfg = _load_isolated_config(monkeypatch)
    assert default_cfg.CHAT_MODEL == "gemini-3.1-flash-lite"
    assert default_cfg.MEMORY_MODEL == "gemini-3.5-flash-lite"

    mistral_only_cfg = _load_isolated_config(monkeypatch, MISTRAL_CHAT_MODEL="ministral-8b-latest")
    assert mistral_only_cfg.CHAT_MODEL == "gemini-3.1-flash-lite"

    override_cfg = _load_isolated_config(
        monkeypatch,
        CHAT_MODEL="custom-chat-gemini",
        MEMORY_MODEL="custom-memory-gemini",
    )
    assert override_cfg.CHAT_MODEL == "custom-chat-gemini"
    assert override_cfg.MEMORY_MODEL == "custom-memory-gemini"


def test_installed_gemini_chat_stream_serializes_and_records_single_usage(monkeypatch):
    real_client = genai.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    requests, updates, events = [], [], []

    def respond(request):
        requests.append(request)
        frames = [
            {
                "candidates": [{"content": {"role": "model", "parts": [{"text": "Hello ", "thought": False}]}}],
                "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 2, "totalTokenCount": 52},
            },
            {
                "candidates": [{"content": {"role": "model", "parts": [{"text": "thinking", "thought": True}, {"text": "world!"}]}}],
            },
            {
                "candidates": [{"content": {"role": "model", "parts": []}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 6, "totalTokenCount": 56},
            },
        ]
        body = "".join("data: " + json.dumps(frame) + "\n\n" for frame in frames)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    def make_client(**kwargs):
        kwargs["http_options"].httpx_client = httpx.Client(transport=httpx.MockTransport(respond))
        return real_client(**kwargs)

    monkeypatch.setattr(genai, "Client", make_client)
    with telemetry.observe(events), delivery.observe(lambda k, v: updates.append((k, v)), threading.Event()):
        result = llm_clients.call_conversation_llm("Say hello")
    assert result == "Hello world!"
    assert [v["answer"] for k, v in updates if k == "text"] == ["Hello ", "Hello world!"]
    assert len(requests) == 1
    assert config.CHAT_MODEL in str(requests[0].url)
    assert "streamGenerateContent" in str(requests[0].url)
    payload = json.loads(requests[0].content)
    assert payload["generationConfig"]["maxOutputTokens"] == config.MAX_RESPONSE_TOKENS
    assert payload["generationConfig"]["thinkingConfig"]["thinking_level"] == "MINIMAL"
    summary = telemetry.summarize(events)
    assert summary["attempts"] == 1
    assert summary["complete"] is True
    assert summary["total"] == 56
    assert len(summary["calls"]) == 1
    assert summary["calls"][0]["provider"] == "Gemini"
    assert summary["calls"][0]["model"] == config.CHAT_MODEL


def test_gemini_chat_stream_omitted_usage_remains_incomplete(monkeypatch):
    real_client = genai.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")

    def respond(request):
        frame = {"candidates": [{"content": {"role": "model", "parts": [{"text": "Complete reply."}]}, "finishReason": "STOP"}]}
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content="data: " + json.dumps(frame) + "\n\n")

    monkeypatch.setattr(genai, "Client", lambda **kw: real_client(**{
        **kw,
        "http_options": kw["http_options"].model_copy(update={"httpx_client": httpx.Client(transport=httpx.MockTransport(respond))}),
    }))
    events = []
    with telemetry.observe(events), delivery.observe(lambda *_: None, threading.Event()):
        assert llm_clients.call_conversation_llm("Hi") == "Complete reply."
    summary = telemetry.summarize(events)
    assert summary["attempts"] == 1
    assert summary["complete"] is False
    assert len(summary["calls"]) == 1
    assert summary["calls"][0]["model"] == config.CHAT_MODEL
    assert summary["calls"][0]["total"] is None


def test_gemini_chat_non_stream_and_error_sanitization(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    fake = MagicMock()
    fake.__enter__.return_value = fake
    fake.models.generate_content.return_value = SimpleNamespace(
        text="Hi from Gemini!",
        usage_metadata=SimpleNamespace(prompt_token_count=20, candidates_token_count=5, total_token_count=25),
    )
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))
    events = []
    with telemetry.observe(events):
        assert llm_clients.call_conversation_llm("Hello") == "Hi from Gemini!"
    assert telemetry.summarize(events)["total"] == 25

    fake.models.generate_content.side_effect = APIError(403, {"error": {"message": "PRIVATE SECRET BODY", "code": 403}})
    with pytest.raises(llm_clients.ProviderError) as exc:
        llm_clients.call_conversation_llm("Hello")
    assert "PRIVATE" not in str(exc.value)
    assert "authenticate" in str(exc.value)


def test_gemini_chat_stream_cancellation_and_incomplete_stream(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    token = delivery.Cancellation()
    fake = MagicMock()
    fake.__enter__.return_value = fake

    def gen():
        yield SimpleNamespace(text="First ", candidates=[SimpleNamespace(finish_reason=None)], usage_metadata=None)
        token.set()
        yield SimpleNamespace(text="Second", candidates=[SimpleNamespace(finish_reason="STOP")], usage_metadata=None)

    fake.models.generate_content_stream.return_value = gen()
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))
    with delivery.observe(lambda *_: None, token):
        with pytest.raises(delivery.ResponseCancelled):
            llm_clients.call_conversation_llm("Hello")
    fake.close.assert_called()

    fake.models.generate_content_stream.return_value = iter([
        SimpleNamespace(text="Truncated", candidates=[SimpleNamespace(finish_reason=None)], usage_metadata=None)
    ])
    with delivery.observe(lambda *_: None, threading.Event()):
        with pytest.raises(llm_clients.ProviderUnavailableError):
            llm_clients.call_conversation_llm("Hello")


def test_web_flow_dataset_free_and_dataset_loaded_ordinary_chat_and_sample(monkeypatch):
    real_genai_client = genai.Client
    real_httpx_client = httpx.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    decision_calls, generate_calls = [], []

    def respond_decisions(request):
        decision_calls.append(json.loads(request.content))
        q = decision_calls[-1]["input"]
        choice = "visualization" if "Chart total Sales" in q else ("analysis" if "total Sales" in q else "conversation")
        return httpx.Response(200, json={
            "answers": {"route": {"type": "choice", "choice": choice, "confidence": 0.96}},
            "usage": {"total_input_tokens": 30, "total_output_tokens": 0, "total_tokens": 30},
        })

    def respond_gemini(request):
        body = json.loads(request.content)
        generate_calls.append((str(request.url), body))
        if config.MEMORY_MODEL in str(request.url):
            return httpx.Response(200, json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": "User greeted and discussed sales."}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 25, "candidatesTokenCount": 5, "totalTokenCount": 30},
            })
        frames = [
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "Hello "}]}}]},
            {
                "candidates": [{"content": {"role": "model", "parts": [{"text": "from Flash-Lite!"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 40, "candidatesTokenCount": 10, "totalTokenCount": 50},
            },
        ]
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content="".join("data: " + json.dumps(f) + "\n\n" for f in frames))

    monkeypatch.setattr(httpx, "Client", lambda **kw: real_httpx_client(**kw, transport=httpx.MockTransport(respond_decisions)))
    monkeypatch.setattr(genai, "Client", lambda **kw: real_genai_client(**{
        **kw,
        "http_options": kw["http_options"].model_copy(update={"httpx_client": real_httpx_client(transport=httpx.MockTransport(respond_gemini))}),
    }))
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: "result = df['Sales'].sum()")
    monkeypatch.setattr(analyst, "write_answer", lambda *a, **k: "Total Sales are 1,000.")
    monkeypatch.setattr(
        analyst,
        "generate_chart_code",
        lambda *a, **k: "result = df.groupby('Region')['Sales'].sum()\nfig = px.bar(x=result.index, y=result.values)\nchart_description = 'Sales by Region'",
    )
    monkeypatch.setattr(analyst, "write_chart_insight", lambda *a, **k: "North is 400 and South is 600.")

    def wait_done(client, headers):
        for _ in range(400):
            state = client.get("/api/session", headers=headers).json()
            if state["job"]["state"] == "done":
                return state
            time.sleep(0.01)
        raise AssertionError("Job timed out")

    with TestClient(create_app()) as client:
        headers = {"Authorization": "Bearer " + client.post("/api/session").json()["token"]}
        # 1. No-dataset chat calls Gemini directly (0 decision calls, 1 chat + 1 memory).
        assert client.post("/api/messages", headers=headers, json={"question": "Hi, my name is Mira", "request_id": "a" * 16}).status_code == 202
        state = wait_done(client, headers)
        assert len(decision_calls) == 0
        assert len(generate_calls) == 2
        assert config.CHAT_MODEL in generate_calls[0][0]
        assert config.MEMORY_MODEL in generate_calls[1][0]
        assert state["turns"][0]["answer"] == "Hello from Flash-Lite!"
        assert state["usage"]["used"] == 1
        assert state["usage"]["total"] == 80

        # 2. First sample upload preserves prior chat.
        uploaded = client.post("/api/sample", headers=headers).json()
        assert len(uploaded["turns"]) == 1
        assert uploaded["dataset"]["rows"] == 4

        # 3. Dataset-loaded ordinary message gets 1 classification + 1 chat reply + 1 memory.
        assert client.post("/api/messages", headers=headers, json={"question": "What charts can you make?", "request_id": "b" * 16}).status_code == 202
        state = wait_done(client, headers)
        assert len(decision_calls) == 1
        assert len(generate_calls) == 4
        assert state["turns"][1]["answer"] == "Hello from Flash-Lite!"
        assert state["usage"]["used"] == 2

        # 4. Sample calculation and chart still produce 1000 and North 400 / South 600.
        assert client.post("/api/messages", headers=headers, json={"question": "What is total Sales?", "request_id": "c" * 16}).status_code == 202
        state = wait_done(client, headers)
        assert state["turns"][2]["result_text"] == "1000"
        assert client.post("/api/messages", headers=headers, json={"question": "Chart total Sales by Region", "request_id": "d" * 16}).status_code == 202
        state = wait_done(client, headers)
        assert state["turns"][3]["chart_json"]
        assert "400" in state["turns"][3]["result_text"] and "600" in state["turns"][3]["result_text"]


def test_cli_and_streamlit_produce_complete_ordinary_chat_with_gemini_only(monkeypatch, capsys):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "GROQ_API_KEY", None)
    monkeypatch.setattr(config, "MISTRAL_API_KEY", None)
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **kw: {"choice": "conversation", "confidence": 0.95})
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Brief note.")

    fake = MagicMock()
    fake.__enter__.return_value = fake
    fake.models.generate_content.return_value = SimpleNamespace(
        text="Hello from Gemini chat!",
        usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5, total_token_count=15),
    )
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))

    # CLI check
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo_sales.csv"
    monkeypatch.setattr(app_cli.sys, "argv", ["app.py", str(demo)])
    answers = iter(["Hello!", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    app_cli.main()
    assert "Hello from Gemini chat!" in capsys.readouterr().out

    # Streamlit check
    root = Path(__file__).resolve().parents[1]
    st_app = AppTest.from_file(str(root / "web_app.py")).run(timeout=15)
    st_app = st_app.get("file_uploader")[0].set_value(("sales.csv", b"region,sales\nNorth,10\n", "text/csv")).run(timeout=15)
    assert not st_app.chat_input[0].disabled
    st_app.chat_input[0].set_value("Hello!").run(timeout=15)
    assert not st_app.exception
    assert any(item.value == "Hello from Gemini chat!" for item in st_app.markdown)


def test_web_gemini_chat_sse_and_stop_preserves_single_turn_charge_and_memory(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    memory_calls = []
    stream_gate = threading.Event()
    fake = MagicMock()
    fake.__enter__.return_value = fake

    def stream_chat(**kwargs):
        yield SimpleNamespace(
            text="Partial ",
            candidates=[SimpleNamespace(finish_reason=None)],
            usage_metadata=None,
        )
        stream_gate.wait(3)
        yield SimpleNamespace(
            text="tail",
            candidates=[SimpleNamespace(finish_reason="STOP")],
            usage_metadata=SimpleNamespace(prompt_token_count=20, candidates_token_count=5, total_token_count=25),
        )

    def complete_memory(**kwargs):
        memory_calls.append(kwargs)
        return SimpleNamespace(
            text="Stopped partial chat note.",
            usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5, total_token_count=15),
        )

    fake.models.generate_content_stream.side_effect = stream_chat
    fake.models.generate_content.side_effect = complete_memory
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))

    with TestClient(create_app()) as client:
        headers = {"Authorization": "Bearer " + client.post("/api/session").json()["token"]}
        key = "gemini-stop-test01"
        assert client.post("/api/messages", headers=headers, json={"question": "Hello Gemini", "request_id": key}).status_code == 202
        session = client.app.state.sessions[headers["Authorization"].split()[1]]
        for _ in range(300):
            if session.delivery and "Partial " in session.delivery.answer:
                break
            time.sleep(0.01)
        assert session.delivery and "Partial " in session.delivery.answer
        cancel = client.post(f"/api/jobs/{key}/cancel", headers=headers)
        assert cancel.status_code == 200
        stream_gate.set()
        for _ in range(300):
            state = client.get("/api/session", headers=headers).json()
            if state["job"]["state"] == "done":
                break
            time.sleep(0.01)
        assert len(state["turns"]) == 1
        assert state["usage"]["used"] == 1
        assert state["turns"][0]["status"] == "stopped"
        assert "Partial" in state["turns"][0]["answer"]
        assert len(memory_calls) == 1
