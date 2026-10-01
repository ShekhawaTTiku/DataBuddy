"""In-memory conversation state — no file persistence, no external LLM for summaries.

Conversation history lives only for the duration of the Streamlit session
(stored in st.session_state.buddy). Add database persistence later when needed.
"""
from dataclasses import dataclass, field

import config

# Maximum number of charts to remember for follow-up modifications
_MAX_CHART_HISTORY = 5


@dataclass
class ConversationState:
    recent_turns: list[dict] = field(default_factory=list)
    last_analysis: dict | None = None
    chart_history: list[dict] = field(default_factory=list)

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

    def to_chart_context_text(self) -> str:
        """Chart-specific context for follow-up chart modifications."""
        if not self.chart_history:
            return "None yet."
        parts = []
        for i, chart in enumerate(self.chart_history[-3:], 1):
            parts.append(
                f"Chart {i}:\n"
                f"  Question: {chart.get('question', 'N/A')}\n"
                f"  Description: {chart.get('description', 'N/A')}\n"
                f"  Code:\n{chart.get('code', 'N/A')}"
            )
        return "\n\n".join(parts)

    @property
    def has_chart_context(self) -> bool:
        """Whether there are any charts in history."""
        return len(self.chart_history) > 0

    @property
    def last_chart(self) -> dict | None:
        """Return the most recent chart entry, or None."""
        return self.chart_history[-1] if self.chart_history else None

    def add_chart(self, question: str, code: str, description: str,
                  chart_json: str) -> None:
        """Record a generated chart for follow-up modifications and memory."""
        self.chart_history.append({
            "question": question,
            "code": code,
            "description": description,
            "chart_json": chart_json,
        })
        if len(self.chart_history) > _MAX_CHART_HISTORY:
            self.chart_history = self.chart_history[-_MAX_CHART_HISTORY:]

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
        self.chart_history.clear()

