"""Offline tests for Gemini Decision 1 routing, validation, cancellation and local fallback."""
import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pandas as pd
import pytest

from backend.core import analyst
from backend.core import config
from backend.core import conversation_state
from backend.core import databuddy
from backend.core import llm_clients
from backend.core import message_handler
from backend.core import response_stream
from backend.core import telemetry


def _load_isolated_config(monkeypatch, **env):
    import importlib.util
    from pathlib import Path

    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: False)
    for key in ("ROUTER_MODEL", "CHAT_MODEL", "MEMORY_MODEL", "MISTRAL_CHAT_MODEL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        if value is not None:
            monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location("_isolated_router_config", Path(config.__file__))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_router_model_default_and_override(monkeypatch):
    default_cfg = _load_isolated_config(monkeypatch)
    assert default_cfg.ROUTER_MODEL == "gemini-decision-1"
    override_cfg = _load_isolated_config(monkeypatch, ROUTER_MODEL="custom-decision-model")
    assert override_cfg.ROUTER_MODEL == "custom-decision-model"


def test_decisions_api_serializes_request_and_records_zero_output_usage(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    captured = []

    def respond(request):
        captured.append(request)
        return httpx.Response(200, json={
            "answers": {
                "route": {
                    "type": "choice",
                    "choice": "visualization",
                    "probabilities": {"analysis": 0.05, "visualization": 0.92, "conversation": 0.03},
                    "confidence": 0.92,
                }
            },
            "usage": {
                "total_input_tokens": 140,
                "total_output_tokens": 0,
                "total_tokens": 140,
            },
        })

    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(respond)))
    events = []
    with telemetry.observe(events):
        result = llm_clients.classify_message(
            "Question: Chart total Sales by Region",
            instructions="Classify route",
            criteria={"analysis": "calc", "visualization": "chart", "conversation": "chat"},
        )
    assert result["choice"] == "visualization"
    assert result["confidence"] == 0.92
    assert len(captured) == 1
    req = captured[0]
    assert req.method == "POST"
    assert str(req.url) == "https://generativelanguage.googleapis.com/v1beta/decisions"
    assert req.headers["x-goog-api-key"] == "offline-gemini-key"
    payload = json.loads(req.content)
    assert payload["model"] == config.ROUTER_MODEL
    assert payload["questions"]["route"]["type"] == "choice"
    assert set(payload["questions"]["route"]["criteria"]) == {"analysis", "visualization", "conversation"}
    summary = telemetry.summarize(events)
    assert summary["complete"] is True
    assert summary["total"] == 140
    assert summary["calls"][0]["provider"] == "Gemini"
    assert summary["calls"][0]["model"] == config.ROUTER_MODEL
    assert summary["calls"][0]["output"] == 0


def test_decisions_api_missing_usage_stays_incomplete(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")

    def respond(request):
        return httpx.Response(200, json={
            "answers": {"route": {"type": "choice", "choice": "analysis", "confidence": 0.9}}
        })

    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(respond)))
    events = []
    with telemetry.observe(events):
        result = llm_clients.classify_message("Total sales?", instructions="Route", criteria={"analysis": "calc", "conversation": "chat"})
    assert result["choice"] == "analysis"
    summary = telemetry.summarize(events)
    assert summary["attempts"] == 1
    assert summary["complete"] is False
    assert summary["calls"][0]["model"] == config.ROUTER_MODEL
    assert summary["calls"][0]["total"] is None


@pytest.mark.parametrize("question,expected_route,has_analysis,has_chart", [
    ("What is total Sales?", "analysis", False, False),
    ("Chart total Sales by Region", "visualization", False, False),
    ("Make it horizontal", "modify_chart", True, True),
    ("How did you calculate that?", "explain_analysis", True, False),
    ("What charts can you make?", "conversation", False, False),
    ("What time is it?", "clock", False, False),
])
def test_route_message_selects_expected_routes_and_excludes_rows(monkeypatch, question, expected_route, has_analysis, has_chart):
    seen = []

    def fake_classify(input_text, *, instructions, criteria):
        seen.append((input_text, instructions, criteria))
        return {"choice": expected_route, "confidence": 0.94}

    monkeypatch.setattr(message_handler, "classify_message", fake_classify)
    result = message_handler.route_message(
        question=question,
        columns=["Month", "Region", "Product", "Sales", "Units"],
        conversation="User: I live in North.\nAssistant: Got it.",
        has_analysis_context=has_analysis,
        has_chart_context=has_chart,
    )
    assert result["route"] == expected_route
    assert result["reply"] == ""
    if expected_route != "clock" and not (has_analysis and expected_route == "explain_analysis"):
        assert len(seen) == 1
        input_text, _, criteria = seen[0]
        assert "Sales" in input_text and "Region" in input_text
        assert "100,2" not in input_text and "Notebook" not in input_text
        assert {"analysis", "visualization", "modify_chart", "explain_analysis", "conversation", "clock", "unclear"} <= set(criteria)


@pytest.mark.parametrize("bad_decision", [
    {"choice": "unclear", "confidence": 0.95},
    {"choice": "analysis", "confidence": 0.25},
    {"choice": "analysis", "confidence": -0.1},
    {"choice": "analysis", "confidence": 1.05},
    {"choice": "analysis", "confidence": float("inf")},
    {"choice": "analysis", "confidence": float("-inf")},
    {"choice": "analysis", "confidence": float("nan")},
    {"choice": "analysis", "confidence": True},
    {"choice": "unknown_route", "confidence": 0.99},
    {"choice": "analysis", "confidence": None},
    "not a dict",
])
def test_uncertain_or_malformed_decision_falls_back_or_clarifies(monkeypatch, bad_decision):
    monkeypatch.setattr(message_handler, "classify_message", lambda *a, **kw: bad_decision)
    assert message_handler.route_message("What is total Sales?", ["Sales", "Region"], "", False)["route"] == "analysis"
    assert message_handler.route_message("Chart total Sales by Region", ["Sales", "Region"], "", False)["route"] == "visualization"
    assert message_handler.route_message("What charts can you make?", ["Sales", "Region"], "", False)["route"] == "conversation"
    assert message_handler.route_message("Hello, my name is Mira", ["A", "B"], "", False)["route"] == "conversation"
    clarify = message_handler.route_message("do that", ["Sales", "Region"], "", False)
    assert clarify["route"] == "clarification"
    assert clarify["reply"]


@pytest.mark.parametrize("mode", ["unavailable", "uncertain"])
def test_local_routing_avoids_substrings_and_generic_data_and_handles_mixed_chart(monkeypatch, mode):
    if mode == "unavailable":
        monkeypatch.setattr(
            message_handler,
            "classify_message",
            MagicMock(side_effect=llm_clients.ProviderUnavailableError("Decision 1 unavailable")),
        )
    else:
        monkeypatch.setattr(
            message_handler,
            "classify_message",
            lambda *a, **kw: {"choice": "unclear", "confidence": 0.9},
        )

    assert message_handler.route_message("Hello, my name is Mira", ["A", "B"], "", False)["route"] == "conversation"
    assert message_handler.route_message("Can you help me upload my data?", ["Data", "Sales"], "", False)["route"] == "conversation"
    assert message_handler.route_message("Is my data saved?", ["Sales", "Region"], "", False)["route"] == "conversation"
    assert message_handler.route_message("Explain wholesale pricing concepts", ["Sales"], "", False)["route"] == "conversation"
    assert message_handler.route_message("What can you do, and chart total Sales by Region?", ["Sales", "Region"], "", False)["route"] == "visualization"
    assert message_handler.route_message("What is average Sales?", ["Sales", "Region"], "", False)["route"] == "analysis"
    assert message_handler.route_message("What is a bar chart, and make a bar chart of Sales by Region?", ["Sales", "Region"], "", False)["route"] == "visualization"
    assert message_handler.route_message("What is a bar chart?", ["Sales", "Region"], "", False)["route"] == "conversation"
    assert message_handler.route_message("What is a bar chart used for?", ["Sales", "Region"], "", False)["route"] == "conversation"
    assert message_handler.route_message("What is total Sales?", ["Sales", "Region"], "", False)["route"] == "analysis"
    assert message_handler.route_message("Make it horizontal", ["Sales", "Region"], "", True, True)["route"] == "modify_chart"


@pytest.mark.parametrize("question", [
    "How do you get started with DataBuddy?",
    "How did you get started with data analysis?",
])
def test_get_started_questions_do_not_trigger_explain_shortcut_with_saved_analysis(monkeypatch, question):
    seen = []

    def fake_classify(input_text, *, instructions, criteria):
        seen.append(input_text)
        return {"choice": "conversation", "confidence": 0.94}

    monkeypatch.setattr(message_handler, "classify_message", fake_classify)
    result = message_handler.route_message(question, ["Sales", "Region"], "", True)
    assert result["route"] == "conversation"
    assert len(seen) == 1

    monkeypatch.setattr(
        message_handler,
        "classify_message",
        MagicMock(side_effect=llm_clients.ProviderUnavailableError("Decision 1 unavailable")),
    )
    assert message_handler.route_message(question, ["Sales", "Region"], "", True)["route"] == "conversation"

    monkeypatch.setattr(
        message_handler,
        "classify_message",
        lambda *a, **kw: {"choice": "unclear", "confidence": 0.9},
    )
    assert message_handler.route_message(question, ["Sales", "Region"], "", True)["route"] == "conversation"
    assert message_handler.route_message("How did you get 1,000?", ["Sales", "Region"], "", True)["route"] == "explain_analysis"


@pytest.mark.parametrize("failure", [
    lambda *a, **kw: (_ for _ in ()).throw(llm_clients.ProviderError("Gemini could not authenticate")),
    lambda *a, **kw: (_ for _ in ()).throw(llm_clients.ProviderUnavailableError("Gemini quota reached")),
    lambda *a, **kw: (_ for _ in ()).throw(httpx.ReadTimeout("timed out")),
    lambda *a, **kw: (_ for _ in ()).throw(ValueError("malformed json")),
])
def test_router_failures_fall_back_so_clear_requests_reach_groq(monkeypatch, failure):
    monkeypatch.setattr(message_handler, "classify_message", failure)
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Computed total Sales = 1000.")
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: "result = df['Sales'].sum()")
    monkeypatch.setattr(analyst, "write_answer", lambda *a, **k: "Total Sales are 1,000.")

    buddy = databuddy.DataBuddy(
        b"Month,Region,Product,Sales,Units\n"
        b"2026-01-01,North,Notebook,100,2\n"
        b"2026-01-01,South,Pen,200,4\n"
        b"2026-02-01,North,Pen,300,6\n"
        b"2026-02-01,South,Notebook,400,8\n",
        filename="sample.csv",
    )
    buddy.conversation.add_turn("I live in North", "Noted.")
    result = buddy.ask("What is total Sales?")
    assert result.status == "success"
    assert result.result_text == "1000"
    assert "North" not in buddy.conversation.to_analysis_prompt_text()


def test_router_failure_allows_sample_chart_and_ambiguous_request_clarifies(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(
        **kw,
        transport=httpx.MockTransport(lambda req: httpx.Response(402, json={"error": {"message": "PRIVATE BILLING"}})),
    ))
    monkeypatch.setattr(conversation_state, "call_memory_llm", lambda *_: "Charted Sales by Region.")
    monkeypatch.setattr(
        analyst,
        "generate_chart_code",
        lambda *a, **k: (
            "result = df.groupby('Region')['Sales'].sum()\n"
            "fig = px.bar(x=result.index, y=result.values)\n"
            "chart_description = 'Total Sales by Region'"
        ),
    )
    monkeypatch.setattr(analyst, "write_chart_insight", lambda *a, **k: "South is 600 and North is 400.")

    buddy = databuddy.DataBuddy(
        b"Month,Region,Product,Sales,Units\n"
        b"2026-01-01,North,Notebook,100,2\n"
        b"2026-01-01,South,Pen,200,4\n"
        b"2026-02-01,North,Pen,300,6\n"
        b"2026-02-01,South,Notebook,400,8\n",
        filename="sample.csv",
    )
    chart_result = buddy.ask("Chart total Sales by Region")
    assert chart_result.status == "success"
    assert chart_result.chart_json
    assert "400" in chart_result.result_text and "600" in chart_result.result_text

    clarification = buddy.ask("do that")
    assert clarification.status == "clarification"


def test_router_propagates_cancellation(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-gemini-key")
    token = threading.Event()

    def slow_or_cancel(request):
        token.set()
        return httpx.Response(200, json={"answers": {"route": {"choice": "analysis", "confidence": 0.9}}})

    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(slow_or_cancel)))
    with response_stream.observe(lambda *_: None, token):
        with pytest.raises(response_stream.ResponseCancelled):
            message_handler.route_message("What is total Sales?", ["Sales"], "", False)
