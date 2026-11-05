"""Session history bounds, privacy separation and reset behavior."""
from backend.core import config
from backend.core.conversation_state import ConversationState, NO_ANALYSIS_CONTEXT


def test_conversations_do_not_share_state():
    first, second = ConversationState(), ConversationState()
    first.add_turn("hello", "hi")
    first.add_chart("plot", "fig = None", "chart", "{}")
    assert not second.recent_turns and not second.chart_history


def test_history_bounds_and_newest_turns(monkeypatch):
    monkeypatch.setattr(config, "MAX_RECENT_TURNS", 3)
    monkeypatch.setattr(config, "MAX_MESSAGE_CHARS", 20)
    state = ConversationState()
    for n in range(10):
        state.add_turn(str(n), "a" * 100)
    assert [t["question"] for t in state.recent_turns] == ["7", "8", "9"]
    assert all(len(t["answer"]) <= 20 for t in state.recent_turns)


def test_casual_facts_do_not_become_analysis_context():
    state = ConversationState()
    state.add_turn("I live in North", "noted")
    assert state.to_analysis_prompt_text() == NO_ANALYSIS_CONTEXT
    state.add_turn("total sales", "60", True)
    assert "I live in North" not in state.to_analysis_prompt_text()
    assert "total sales" in state.to_analysis_prompt_text()


def test_context_budget_keeps_newest_and_instructions(monkeypatch):
    monkeypatch.setattr(config, "MAX_CONTEXT_CHARS", 300)
    state = ConversationState()
    for n in range(6):
        state.add_turn(f"question {n}", "x" * 300, True)
    prompt = state.to_analysis_prompt_text()
    assert len(prompt) <= 300 and "Do not reuse filters" in prompt
    assert "question 5" in prompt


def test_chart_history_is_bounded_and_reset_clears_everything():
    state = ConversationState()
    for n in range(8):
        state.add_chart(str(n), "fig = None", "chart", "{}")
    state.add_turn("hello", "hi")
    state.last_analysis = {"result": "60"}
    assert len(state.chart_history) == 5 and state.last_chart["question"] == "7"
    state.clear()
    assert not state.recent_turns and not state.chart_history and state.last_analysis is None


def test_history_has_no_persistence_api():
    state = ConversationState()
    assert not hasattr(state, "save") and not hasattr(state, "storage_path")
