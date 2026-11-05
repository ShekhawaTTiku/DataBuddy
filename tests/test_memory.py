"""Offline coverage of six-note memory, outages, evidence separation and sessions."""
from unittest.mock import MagicMock

import pytest

from backend.core import config
from backend.core import conversation_state as memory
from backend.core import databuddy
from backend.core.llm_clients import ProviderError, ProviderUnavailableError
from backend.legacy.ui_state import initialize_session, replace_dataset, reset_conversation


def test_six_notes_roll_into_one_paragraph_and_next_batch_merges(monkeypatch):
    calls = []
    def summarize(prompt):
        calls.append(prompt)
        if '"new_notes"' in prompt:
            return "summary one" if len(calls) == 6 else "summary two"
        return f"brief {len(calls)}"
    monkeypatch.setattr(memory, "call_memory_llm", summarize)
    state = memory.ConversationState()
    for n in range(5):
        state.update_memory(f"q{n}", f"a{n}")
    assert len(state.memory_notes) == 5 and state.memory_summary == ""
    state.update_memory("q5", "a5")
    assert state.memory_summary == "summary one" and state.memory_notes == []
    for n in range(6):
        state.update_memory(f"next{n}", "answer")
    assert state.memory_summary == "summary two" and state.memory_notes == []
    assert '"older_summary": "summary one"' in calls[-1]
    assert len(calls) == 12  # sixth note and merge share one request


def test_notes_and_summary_are_clipped_and_plain_text(monkeypatch):
    monkeypatch.setattr(memory, "call_memory_llm", lambda _: "word\n" * 2000)
    state = memory.ConversationState()
    state.update_memory("q", "a")
    assert len(state.memory_notes[0]) <= config.MAX_MEMORY_NOTE_CHARS
    for _ in range(5):
        state.update_memory("q", "a")
    assert len(state.memory_summary) <= config.MAX_MEMORY_SUMMARY_CHARS
    assert "\n" not in state.memory_summary


def test_repeated_outages_preserve_summary_and_bound_local_notes(monkeypatch):
    monkeypatch.setattr(memory, "call_memory_llm", MagicMock(side_effect=ProviderUnavailableError("Temporary outage.")))
    state = memory.ConversationState(memory_summary="older valid memory")
    for n in range(15):
        state.add_turn(str(n), "answer")
        state.update_memory(str(n), "answer")
    assert state.memory_summary == "older valid memory"
    assert len(state.memory_notes) == 6 and len(state.recent_turns) == 6
    assert "User: 14" in state.memory_notes[-1]
    assert state.memory_notice and "Temporary outage" in state.memory_notice


def test_failed_compression_keeps_notes_and_retries_on_next_exchange(monkeypatch):
    calls = []
    def summarize(prompt):
        calls.append(prompt)
        if '"new_notes"' in prompt and len(calls) == 6:
            raise ProviderUnavailableError("temporary")
        return "merged" if '"new_notes"' in prompt else "brief"
    monkeypatch.setattr(memory, "call_memory_llm", summarize)
    state = memory.ConversationState(memory_summary="old")
    for _ in range(6): state.update_memory("q", "a")
    assert state.memory_summary == "old" and len(state.memory_notes) == 6
    state.update_memory("next", "answer")
    assert state.memory_summary == "merged" and state.memory_notes == []
    assert state.memory_notice is None


@pytest.mark.parametrize("response", ["", None])
def test_empty_memory_does_not_erase_previous_state(monkeypatch, response):
    monkeypatch.setattr(memory, "call_memory_llm", lambda _: response)
    state = memory.ConversationState(memory_summary="keep")
    state.update_memory("question", "answer")
    assert state.memory_summary == "keep" and state.memory_notice
    assert "uncompressed" in state.memory_notes[0]


def test_summary_context_is_not_used_as_calculation_evidence():
    state = memory.ConversationState(memory_summary="I live in North. Invented total: 999.", memory_notes=["personal preference"])
    state.add_turn("total sales", "60", is_analysis=True)
    state.last_analysis = {"question": "total sales", "result": "60"}
    assert "I live in North" in state.to_prompt_text()
    assert "999" not in state.to_analysis_prompt_text()
    assert "personal preference" not in state.to_analysis_prompt_text()
    assert "Computed result: 60" in state.to_analysis_prompt_text()


def test_memory_context_respects_global_bound():
    state = memory.ConversationState(memory_summary="s" * config.MAX_MEMORY_SUMMARY_CHARS,
                                     memory_notes=["n" * 400] * 6)
    for n in range(6): state.add_turn(f"newest {n}", "a" * 6000)
    assert len(state.to_prompt_text()) <= config.MAX_CONTEXT_CHARS
    assert "newest 5" in state.to_prompt_text()


def test_failed_task_note_is_given_status_and_computed_evidence(monkeypatch):
    call = MagicMock(return_value="Calculation failed; no result.")
    monkeypatch.setattr(memory, "call_memory_llm", call)
    state = memory.ConversationState()
    state.update_memory("question", "could not calculate", status="error")
    prompt = call.call_args.args[0]
    assert '"status": "error"' in prompt and '"computed_evidence": ""' in prompt
    assert "Do not invent values" in prompt


def test_reset_and_dataset_replacement_clear_memory():
    state = {}; initialize_session(state)
    replace_dataset(state, "demo.csv", b"sales\n10\n")
    old = state["buddy"].conversation
    old.memory_summary = "prior"; old.memory_notes = ["note"]; old.memory_notice = "outage"
    reset_conversation(state)
    assert old.memory_summary == "" and old.memory_notes == [] and old.memory_notice is None
    old.memory_summary = "another"
    replace_dataset(state, "demo.csv", b"sales\n20\n")
    assert state["buddy"].conversation.memory_summary == ""
    assert memory.ConversationState().memory_notes == []


def test_actual_answers_survive_memory_failure_and_turns_record_once(monkeypatch):
    monkeypatch.setattr(databuddy.message_handler, "route_message", lambda **_: {"route": "conversation", "reply": "Hello"})
    monkeypatch.setattr(memory, "call_memory_llm", MagicMock(side_effect=RuntimeError("PRIVATE BODY")))
    buddy = databuddy.DataBuddy(b"sales\n10\n", filename="demo.csv")
    for _ in range(12):
        result = buddy.ask("hello")
        assert result.answer == "Hello" and result.status == "success"
        assert "PRIVATE" not in result.memory_notice
    assert len(buddy.conversation.recent_turns) == 6
    assert len(buddy.conversation.memory_notes) == 6


def test_six_exchange_pipeline_includes_evidence_and_clears_notes(monkeypatch):
    prompts = []
    def summarize(prompt):
        prompts.append(prompt)
        return "Sales total 10." if '"new_notes"' in prompt else "Asked total sales; computed result 10."
    monkeypatch.setattr(memory, "call_memory_llm", summarize)
    monkeypatch.setattr(databuddy.message_handler, "route_message", lambda **_: {"route": "analysis", "reply": ""})
    monkeypatch.setattr(databuddy.analyst, "generate_code", lambda *a, **k: "result = 10")
    monkeypatch.setattr(databuddy.executor, "run_code", lambda *a: databuddy.executor.ExecutionResult(True, "10", None))
    monkeypatch.setattr(databuddy.analyst, "write_answer", lambda *a, **k: "Total is 10.")
    buddy = databuddy.DataBuddy(b"sales\n10\n", filename="demo.csv")
    for _ in range(6): assert buddy.ask("total sales").result_text == "10"
    assert len(prompts) == 6 and '"computed_evidence": "10"' in prompts[0]
    assert buddy.conversation.memory_summary == "Sales total 10."
    assert buddy.conversation.memory_notes == [] and len(buddy.conversation.recent_turns) == 6


def test_permanent_routing_errors_are_visible(monkeypatch):
    monkeypatch.setattr(databuddy.message_handler, "classify_message", MagicMock(side_effect=ProviderError("Check model access.")))
    with pytest.raises(ProviderError, match="model access"):
        databuddy.message_handler.route_message("hello", ["sales"], "", False)


def test_sixth_note_and_compression_share_one_request_and_deadline(monkeypatch):
    from backend.core import llm_clients
    clock = [100.0]
    monkeypatch.setattr(llm_clients.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(config, "MEMORY_TIMEOUT_SECONDS", 10)
    observed = []
    def summarize(prompt):
        observed.append(llm_clients._deadline.get())
        clock[0] += 4
        return "merged" if '"new_notes"' in prompt else "brief"
    monkeypatch.setattr(memory, "call_memory_llm", summarize)
    state = memory.ConversationState(memory_notes=["earlier"] * 5)
    with llm_clients.request_budget(seconds=30):
        state.update_memory("q", "a")
        assert llm_clients._deadline.get() == 130
    assert observed == [110]  # one combined request, not a second compression call


def test_global_deadline_prevents_memory_network_requests(monkeypatch):
    from backend.core import llm_clients
    from google import genai
    monkeypatch.setattr(config, "GEMINI_API_KEY", "dummy")
    factory = MagicMock(); monkeypatch.setattr(genai, "Client", factory)
    token = llm_clients._deadline.set(llm_clients.time.monotonic() - 1)
    try:
        state = memory.ConversationState()
        state.update_memory("q", "a")
        assert state.memory_notice and len(state.memory_notes) == 1
    finally:
        llm_clients._deadline.reset(token)
    factory.assert_not_called()
