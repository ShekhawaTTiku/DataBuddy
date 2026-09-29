"""In-memory conversation state — no file persistence, no external LLM for summaries.

Conversation history lives only for the duration of the Streamlit session
(stored in st.session_state.buddy). Add database persistence later when needed.
"""
from dataclasses import dataclass, field

import config


@dataclass
class ConversationState:
    recent_turns: list[dict] = field(default_factory=list)
    last_analysis: dict | None = None

    def to_prompt_text(self) -> str:
        """Full conversation context — sent to router and answer writer."""
        if not self.recent_turns:
            return "None yet."
        return "Recent turns:\n" + "\n".join(
            f"User: {t['question']}\nAssistant: {t['answer']}"
            for t in self.recent_turns
        )

    def to_analysis_prompt_text(self) -> str:
        """Only analysis turns — sent to code generation.

        Excludes casual conversation so remembered facts don't become
        implicit dataset filters.
        """
        turns = [t for t in self.recent_turns if t.get("is_analysis", True)]
        if not turns:
            return "No previous data analysis. Do not infer filters from ordinary conversation."
        header = (
            "Recent data analyses "
            "(use only to resolve clear follow-ups; "
            "do not reuse filters for a new standalone question):\n"
        )
        return header + "\n".join(
            f"User: {t['question']}\nAssistant: {t['answer']}" for t in turns
        )

    def add_turn(self, question: str, answer: str, is_analysis: bool = False) -> None:
        """Append a turn and trim to MAX_RECENT_TURNS (oldest dropped, no summarization)."""
        self.recent_turns.append(
            {"question": question, "answer": answer, "is_analysis": is_analysis}
        )
        limit = max(1, config.MAX_RECENT_TURNS)
        if len(self.recent_turns) > limit:
            self.recent_turns = self.recent_turns[-limit:]

    def clear(self) -> None:
        """Wipe all state (called by the Reset button in the UI)."""
        self.recent_turns.clear()
        self.last_analysis = None
