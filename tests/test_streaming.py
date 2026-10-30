"""Provider-free streaming, interruption, accounting and real HTTP acceptance."""
import json
import socket
import threading
import time
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import httpx
import pytest
import uvicorn

import analyst
import config
import conversation_state
import llm_clients
import message_handler
import response_stream as delivery
import telemetry
from api.main import create_app
from databuddy import AskResult, DataBuddy
from executor import ExecutionResult


def chunk(text=None, finish=None, usage=None):
    return NS(choices=[NS(delta=NS(content=text), finish_reason=finish)], usage=usage)


def usage():
    return NS(prompt_tokens=30, completion_tokens=10, total_tokens=40)


def test_installed_groq_sdk_stream_serialization_and_final_usage(monkeypatch):
    import groq
    real = groq.Groq
    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-placeholder")
    requests, updates, observations = [], [], []
    def respond(request):
        requests.append(json.loads(request.content))
        frames = [
            {"choices": [{"index": 0, "delta": {"content": "Hello "}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {"content": "world"}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}},
        ]
        for item in frames:
            item.update(id="offline", created=1, model="fixture", object="chat.completion.chunk")
        content = "".join("data: " + json.dumps(item) + "\n\n" for item in frames) + "data: [DONE]\n\n"
        return httpx.Response(200, headers={"content-type": "text/event-stream", "x-ratelimit-remaining-tokens": "400"}, content=content)
    def client(**kwargs):
        return real(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(groq, "Groq", client)
    with telemetry.observe(observations), delivery.observe(lambda kind, values: updates.append((kind, values)), threading.Event()):
        assert llm_clients._groq_completion("synthetic", stream=True) == "Hello world"
    assert requests[0]["stream"] is True and requests[0]["stream_options"] == {"include_usage": True}
    assert [v["answer"] for k, v in updates if k == "text"] == ["Hello ", "Hello world"]
    totals = telemetry.summarize(observations)
    assert totals["complete"] and totals["total"] == 40 and totals["attempts"] == 1
    assert totals["limits"][0]["values"]["x-ratelimit-remaining-tokens"] == "400"


def test_mistral_stream_uses_installed_client_path_and_no_sdk_retries(monkeypatch):
    import mistralai.client
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "offline-placeholder")
    fake = MagicMock()
    fake.__enter__.return_value = fake
    fake.chat.stream.return_value = iter([NS(data=chunk("Hi")), NS(data=chunk(finish="stop", usage=usage()))])
    factory = MagicMock(return_value=fake)
    monkeypatch.setattr(mistralai.client, "Mistral", factory)
    # Both import layouts remain supported by the application.
    import mistralai
    monkeypatch.setattr(mistralai, "Mistral", factory, raising=False)
    observations = []
    with telemetry.observe(observations), delivery.observe(lambda *_: None, threading.Event()):
        assert llm_clients.call_conversation_llm("hello") == "Hi"
    assert fake.chat.stream.call_args.kwargs["retries"] is None
    assert factory.call_args.kwargs["retry_config"] is None
    assert telemetry.summarize(observations)["total"] == 40


def test_installed_mistral_sdk_serializes_stream_request_offline(monkeypatch):
    import mistralai
    import mistralai.client
    real = mistralai.client.Mistral
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "offline-placeholder")
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        payload = {"id": "offline", "model": "fixture", "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}}
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content="data: " + json.dumps(payload) + "\n\ndata: [DONE]\n\n")
    def factory(**kwargs):
        return real(**kwargs, client=httpx.Client(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(mistralai, "Mistral", factory, raising=False)
    monkeypatch.setattr(mistralai.client, "Mistral", factory)
    events = []
    with telemetry.observe(events), delivery.observe(lambda *_: None, threading.Event()):
        assert llm_clients.call_conversation_llm("hello") == "Hello"
    assert requests[0]["stream"] is True and telemetry.summarize(events)["complete"]


def test_midstream_fallback_replaces_text_and_records_both_attempts(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "offline-placeholder")
    updates, events = [], []
    def primary(*args, **kwargs):
        telemetry.event("attempt", provider="Groq")
        delivery.text("Unfinished primary")
        raise llm_clients.ProviderUnavailableError("temporary outage")
    def fallback(*args, **kwargs):
        assert delivery.current().answer == ""
        telemetry.event("attempt", provider="Mistral")
        telemetry.record_usage(NS(usage=usage()), "Mistral", "fixture")
        delivery.text("Fresh backup answer")
        return "Fresh backup answer"
    monkeypatch.setattr(llm_clients, "_groq_completion", primary)
    monkeypatch.setattr(llm_clients, "_mistral_completion", fallback)
    with telemetry.observe(events), delivery.observe(lambda k, v: updates.append((k, v)), threading.Event()):
        assert llm_clients.call_narration_llm("computed evidence") == "Fresh backup answer"
    assert [k for k, _ in updates] == ["text", "reset", "text"]
    summary = telemetry.summarize(events)
    assert summary["attempts"] == 2 and summary["fallbacks"] == 1 and not summary["complete"]


@pytest.mark.parametrize("chunks", [[], [chunk("unfinished")]])
def test_stream_without_terminal_finish_is_not_reported_success(chunks):
    with delivery.observe(lambda *_: None, threading.Event()):
        with pytest.raises(llm_clients.ProviderUnavailableError):
            llm_clients._consume_stream(iter(chunks), "Fixture", "fixture")


def test_private_stream_error_is_sanitized_and_content_is_bounded():
    def broken():
        yield chunk("a" * (config.MAX_MESSAGE_CHARS + 100))
        raise RuntimeError("PRIVATE PROVIDER BODY")
    with delivery.observe(lambda *_: None, threading.Event()) as state:
        with pytest.raises(llm_clients.ProviderError) as error:
            llm_clients._consume_stream(broken(), "Fixture", "fixture")
        assert "PRIVATE" not in str(error.value)
        assert len(state.answer) == config.MAX_MESSAGE_CHARS


def test_streaming_router_classifies_only_but_legacy_keeps_single_call_reply(monkeypatch):
    prompts = []
    def classify(prompt):
        prompts.append(prompt)
        return '{"route":"conversation","reply":"buffered answer"}'
    monkeypatch.setattr(message_handler, "classify_message", classify)
    args = dict(question="Hello", columns=["Sales"], conversation="", has_analysis_context=False)
    assert message_handler.route_message(**args)["reply"] == "buffered answer"
    with delivery.observe(lambda *_: None, threading.Event()):
        assert message_handler.route_message(**args)["reply"] == ""
    assert "Classify only" in prompts[-1]


@pytest.mark.parametrize("cancel_at", ["text", "evidence"])
def test_cancellation_keeps_evidence_and_records_one_stopped_exchange(monkeypatch, cancel_at):
    monkeypatch.setattr(message_handler, "route_message", lambda **_: {"route": "analysis"})
    code = MagicMock(return_value="result = 10")
    monkeypatch.setattr(analyst, "generate_code", code)
    monkeypatch.setattr("executor.run_code", lambda *_: ExecutionResult(True, "10", None))
    memory = MagicMock(return_value="Stopped after result 10.")
    monkeypatch.setattr(conversation_state, "call_memory_llm", memory)
    token = threading.Event()
    def answer(*args, **kwargs):
        delivery.text("The total is ")
        token.set()
        delivery.text("10")
    monkeypatch.setattr(analyst, "write_answer", answer)
    buddy = DataBuddy(b"Sales\n4\n6\n", filename="synthetic.csv")
    updates = []
    def receive(kind, values):
        updates.append((kind, values))
        if kind == cancel_at:
            token.set()
    with delivery.observe(receive, token):
        result = buddy.ask("Total sales?")
    assert result.status == "stopped" and result.result_text == "10" and result.code == "result = 10"
    assert buddy.conversation.last_analysis["result"] == "10"
    assert len(buddy.conversation.recent_turns) == len(buddy.conversation.memory_notes) == 1
    assert "stopped" in memory.call_args.args[0]
    assert code.call_count == memory.call_count == 1
    if cancel_at == "text":
        assert [k for k, _ in updates].index("evidence") < [k for k, _ in updates].index("text")


def test_streaming_answer_precedes_memory_and_six_exchange_cycle_is_unchanged(monkeypatch):
    calls, order = [], []
    monkeypatch.setattr(message_handler, "route_message", lambda **_: {"route": "conversation", "reply": ""})
    monkeypatch.setattr(message_handler, "answer_conversation", lambda *_: "A complete answer")
    def memory(prompt):
        order.append("memory")
        calls.append(prompt)
        return "rolling paragraph" if "ONE compact paragraph" in prompt else "brief note"
    monkeypatch.setattr(conversation_state, "call_memory_llm", memory)
    buddy = DataBuddy(b"Sales\n1\n", filename="synthetic.csv")
    for _ in range(12):
        with delivery.observe(lambda k, v: order.append(k), threading.Event()):
            buddy.ask("Hello?")
    assert order.index("answer_done") < order.index("memory")
    assert len(calls) == 12 and sum("ONE compact paragraph" in p for p in calls) == 2
    assert buddy.conversation.memory_summary == "rolling paragraph" and buddy.conversation.memory_notes == []


def test_worker_cancellation_reaps_process_and_does_not_wait_for_timeout(monkeypatch):
    import executor
    import pandas as pd
    from pathlib import Path
    token = threading.Event()
    processes, folders = [], []
    popen = executor.subprocess.Popen
    def start(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        folders.append(Path(kwargs["cwd"]))
        token.set()
        return process
    monkeypatch.setattr(executor.subprocess, "Popen", start)
    started = time.monotonic()
    with delivery.observe(lambda *_: None, token), pytest.raises(delivery.ResponseCancelled):
        executor.run_code("while True:\n    pass", pd.DataFrame({"a": [1]}))
    assert time.monotonic() - started < 3
    assert processes and all(process.poll() is not None for process in processes)
    assert all(not folder.exists() for folder in folders)


def test_real_http_incremental_delivery_reconnect_and_idempotent_cancel(monkeypatch):
    class Buddy(DataBuddy):
        calls = 0
        def _ask(self, question):
            type(self).calls += 1
            telemetry.event("attempt", provider="Fixture")
            delivery.evidence(result_text="10", code="result = 10")
            for word in ["One ", "two ", "three."]:
                delivery.text(word)
                time.sleep(.2)
            telemetry.record_usage(NS(usage=usage()), "Fixture", "fixture")
            return AskResult("One two three.", result_text="10", code="result = 10")
    memory_gate = threading.Event()
    memory_calls = []
    def memory(prompt):
        memory_calls.append(prompt)
        memory_gate.wait(4)
        return "brief note"
    monkeypatch.setattr(conversation_state, "call_memory_llm", memory)
    app = create_app(Buddy)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        for _ in range(300):
            if server.started:
                break
            time.sleep(.01)
        assert server.started
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=8) as client:
            headers = {"Authorization": "Bearer " + client.post("/api/session").json()["token"]}
            assert client.post("/api/sample", headers=headers).status_code == 200
            key = "http-stream-job-01"
            message = {"question": "Total sales?", "request_id": key}
            assert client.post("/api/messages", headers=headers, json=message).status_code == 202
            assert client.get(f"/api/jobs/{key}/events").status_code == 401
            other = {"Authorization": "Bearer " + client.post("/api/session").json()["token"]}
            assert client.get(f"/api/jobs/{key}/events", headers=other).status_code == 404
            # A real socket must expose a partial answer before the job completes.
            with client.stream("GET", f"/api/jobs/{key}/events", headers=headers) as stream:
                assert stream.headers["x-accel-buffering"] == "no"
                for line in stream.iter_lines():
                    if line.startswith("data:"):
                        first = json.loads(line[5:])
                        if first.get("answer"):
                            assert first["answer"] != "One two three." and not first["answer_done"]
                            break
            assert client.post("/api/messages", headers=headers, json=message).status_code == 202
            # Reattachment sees the same result and completed answer during memory.
            with client.stream("GET", f"/api/jobs/{key}/events", headers=headers) as stream:
                for line in stream.iter_lines():
                    if line.startswith("data:"):
                        update = json.loads(line[5:])
                        if update.get("answer_done"):
                            assert update["answer"] == "One two three." and update["job"]["state"] == "running"
                            break
            memory_gate.set()
            for _ in range(300):
                snapshot = client.get("/api/session", headers=headers).json()
                if snapshot["job"]["state"] == "done":
                    break
                time.sleep(.01)
            assert Buddy.calls == len(memory_calls) == 1
            assert len(snapshot["turns"]) == snapshot["usage"]["used"] == 1
            assert snapshot["usage"]["total"] == 40
            assert "event: done" in client.get(f"/api/jobs/{key}/events", headers=headers).text
            # Stop is idempotent, preserves ready results and consumes only one message.
            key = "http-stream-job-02"
            client.post("/api/messages", headers=headers, json={**message, "request_id": key})
            assert client.post(f"/api/jobs/{key}/cancel", headers=headers).status_code == 200
            client.post(f"/api/jobs/{key}/cancel", headers=headers)
            for _ in range(300):
                snapshot = client.get("/api/session", headers=headers).json()
                if snapshot["job"]["state"] == "done":
                    break
                time.sleep(.01)
            assert snapshot["turns"][-1]["status"] == "stopped"
            assert snapshot["usage"]["used"] == len(snapshot["turns"]) == len(memory_calls) == 2
            assert not snapshot["usage"]["complete"]
    finally:
        memory_gate.set()
        server.should_exit = True
        thread.join(8)
        listener.close()
