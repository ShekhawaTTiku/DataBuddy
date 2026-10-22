"""Offline regressions for analysis evidence, partial success and routing."""
from types import SimpleNamespace

import pandas as pd
import pytest

import analyst
import config
import databuddy
import executor
import message_handler
from conversation_state import ConversationState


@pytest.fixture(autouse=True)
def no_provider_calls(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("This offline test must not call a model provider.")
    monkeypatch.setattr(analyst, "call_analysis_llm", fail)
    monkeypatch.setattr(analyst, "call_narration_llm", fail)
    monkeypatch.setattr(message_handler, "classify_message", fail)
    monkeypatch.setattr(message_handler, "call_conversation_llm", fail)
    monkeypatch.setattr(message_handler, "call_explanation_llm", fail)


@pytest.fixture
def buddy():
    obj = databuddy.DataBuddy.__new__(databuddy.DataBuddy)
    obj.dataset = SimpleNamespace(df=pd.DataFrame({"region": ["North", "South", "North"], "sales": [10, 20, 30]}), text="Synthetic sales dataset")
    obj.conversation = ConversationState()
    return obj


def route(monkeypatch, value):
    monkeypatch.setattr(message_handler, "route_message", lambda **kwargs: {"route": value, "reply": ""})


def success(result="60", chart=None):
    return executor.ExecutionResult(True, result, None, chart, "Sales by region" if chart else None)


def test_actual_aggregate_answer_is_backed_by_computation(buddy, monkeypatch):
    route(monkeypatch, "analysis")
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: "result = df.groupby('region')['sales'].sum()")
    seen = []
    def explain(profile, question, code, execution, **kwargs):
        seen.append(execution.result_text)
        return "North has 40 and South has 20."
    monkeypatch.setattr(analyst, "write_answer", explain)
    result = buddy.ask("total sales by region")
    assert result.status == "success"
    assert "40" in result.result_text and "20" in result.result_text
    assert seen == [result.result_text]
    assert buddy.conversation.last_analysis["result"] == result.result_text


@pytest.mark.parametrize("narration", [None, ""])
def test_completed_result_survives_narration_failure(buddy, monkeypatch, narration):
    route(monkeypatch, "analysis")
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: "result = 60")
    monkeypatch.setattr(executor, "run_code", lambda *a: success())
    def explain(*args, **kwargs):
        if narration is None:
            raise RuntimeError("simulated outage")
        return narration
    monkeypatch.setattr(analyst, "write_answer", explain)
    result = buddy.ask("total sales")
    assert result.status == "partial"
    assert result.result_text == "60"
    assert buddy.conversation.last_analysis["result"] == "60"


def test_chart_is_saved_when_insight_fails(buddy, monkeypatch):
    route(monkeypatch, "visualization")
    monkeypatch.setattr(analyst, "generate_chart_code", lambda *a, **k: "fig = px.bar(df)")
    monkeypatch.setattr(executor, "run_code", lambda *a: success("North: 40, South: 20", '{"data": []}'))
    monkeypatch.setattr(analyst, "write_chart_insight", lambda *a: (_ for _ in ()).throw(RuntimeError("offline")))
    result = buddy.ask("chart sales")
    assert result.status == "partial" and result.chart_json
    assert buddy.conversation.last_chart["chart_json"] == result.chart_json
    assert buddy.conversation.last_analysis["result"] == result.result_text


def test_failed_execution_is_not_sent_for_an_answer(buddy, monkeypatch):
    route(monkeypatch, "analysis")
    calls = []
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: calls.append(k.get("previous_attempt")) or "result = bad")
    monkeypatch.setattr(executor, "run_code", lambda *a: executor.ExecutionResult(False, None, "Unknown column"))
    monkeypatch.setattr(analyst, "write_answer", lambda *a, **k: pytest.fail("Failed execution must not be narrated"))
    result = buddy.ask("total missing column")
    assert result.status == "error" and buddy.conversation.last_analysis is None
    assert len(calls) == config.MAX_CODE_RETRIES + 1
    assert calls[-1]["error"] == "Unknown column"


def test_no_figure_is_not_saved_as_success(buddy, monkeypatch):
    route(monkeypatch, "visualization")
    monkeypatch.setattr(analyst, "generate_chart_code", lambda *a, **k: "fig = None")
    monkeypatch.setattr(executor, "run_code", lambda *a: success("None"))
    result = buddy.ask("chart sales")
    assert result.status == "clarification"
    assert not buddy.conversation.has_chart_context
    assert buddy.conversation.last_analysis is None
    assert not buddy.conversation.recent_turns[-1]["is_analysis"]


def test_modify_without_chart_is_a_clarification(buddy, monkeypatch):
    route(monkeypatch, "modify_chart")
    result = buddy.ask("make it horizontal")
    assert result.status == "clarification" and "first" in result.answer


def test_invalid_question_does_not_route(buddy, monkeypatch):
    monkeypatch.setattr(message_handler, "route_message", lambda **k: pytest.fail("No routing for invalid input"))
    assert buddy.ask(" ").status == "clarification"
    assert buddy.ask("x" * (config.MAX_QUESTION_CHARS + 1)).status == "clarification"


def test_suggestions_do_not_spend_an_extra_call_by_default(buddy, monkeypatch):
    route(monkeypatch, "analysis")
    monkeypatch.setattr(config, "ENABLE_VISUALIZATION_SUGGESTIONS", False)
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: "result = 60")
    monkeypatch.setattr(executor, "run_code", lambda *a: success())
    monkeypatch.setattr(analyst, "write_answer", lambda *a, **k: "60")
    monkeypatch.setattr(analyst, "suggest_visualization", lambda *a: pytest.fail("Suggestions disabled"))
    assert buddy.ask("total sales").visualization_suggestion is None


def test_last_successful_result_survives_later_failure(buddy, monkeypatch):
    prior = {"question": "total", "code": "result = 60", "result": "60", "answer": "60"}
    buddy.conversation.last_analysis = prior.copy()
    route(monkeypatch, "analysis")
    monkeypatch.setattr(analyst, "generate_code", lambda *a, **k: "result = bad")
    monkeypatch.setattr(executor, "run_code", lambda *a: executor.ExecutionResult(False, None, "bad"))
    buddy.ask("another calculation")
    assert buddy.conversation.last_analysis == prior


def test_explanation_route_precedes_generic_followup():
    result = message_handler.route_message("how did you know?", ["sales"], "", True)
    assert result["route"] == "explain_analysis"


def test_fallback_chart_modification_and_analysis():
    assert message_handler.route_message("make it horizontal", ["sales"], "", True, True)["route"] == "modify_chart"
    assert message_handler.route_message("what about the second highest?", ["sales"], "", True)["route"] == "analysis"


def test_chart_insight_requires_actual_evidence(monkeypatch):
    called = []
    monkeypatch.setattr(analyst, "call_narration_llm", lambda p: called.append(p) or "North has 40")
    result = success("North: 40, South: 20", '{"data": []}')
    assert analyst.write_chart_insight("secret unused profile", "chart", "code", result) == "North has 40"
    assert "North: 40, South: 20" in called[0]
    assert "secret unused profile" not in called[0]
    called.clear()
    analyst.write_chart_insight("profile", "chart", "code", success("None", '{"data": []}'))
    assert not called


def test_prompt_expansion_does_not_reinterpret_dataset_placeholders():
    prompt = analyst._prompt("code_generation.txt", profile="literal {{question}}", question="actual question")
    assert "literal {{question}}" in prompt
    assert "actual question" in prompt


def test_prompt_budget_preserves_the_question(monkeypatch):
    monkeypatch.setattr(config, "MAX_PROMPT_CHARS", 5000)
    prompt = analyst._prompt("code_generation.txt", profile="x" * 12000, question="actual question", conversation="y" * 12000)
    assert len(prompt) <= 5000 and "actual question" in prompt


def test_debug_metadata_excludes_raw_dataset(monkeypatch, capsys):
    monkeypatch.setattr(config, "DEBUG", True)
    monkeypatch.setattr(analyst, "call_analysis_llm", lambda p: "result = 1")
    analyst.generate_code("private raw row", "private question")
    output = capsys.readouterr().out
    assert "prompt_chars" in output
    assert "private raw row" not in output and "private question" not in output
