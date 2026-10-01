"""Orchestrates DataBuddy's question-to-answer pipeline."""
import re
from dataclasses import dataclass

import config
import analyst
import executor
import message_handler
from dataset_state import load_and_profile
from conversation_state import ConversationState


@dataclass
class AskResult:
    """Holds both text answer and optional chart data from a single ask() call."""
    answer: str
    chart_json: str | None = None
    chart_description: str | None = None
    visualization_suggestion: str | None = None


class DataBuddy:
    def __init__(self, dataset_path: str):
        self.dataset = load_and_profile(dataset_path)
        self.conversation = ConversationState()

    def _run_visualization(self, question: str, analysis_context: str,
                           chart_context: str = "None yet.") -> AskResult:
        """Generate a Plotly chart and a companion text insight.

        This handles both new visualization requests and follow-up chart
        modifications (via chart_context).
        """
        code = analyst.generate_chart_code(
            self.dataset.text, question,
            conversation_text=analysis_context,
            chart_context=chart_context,
        )
        execution = executor.run_code(code, self.dataset.df)

        if config.DEBUG:
            print(f"\n[DEBUG] Chart code:\n{code}\n[DEBUG] Execution ok={execution.ok}; "
                  f"chart_json={'present' if execution.chart_json else 'None'}; "
                  f"error={execution.error!r}")

        # Retry loop for chart generation
        attempts = 0
        while not execution.ok and attempts < config.MAX_CODE_RETRIES:
            attempts += 1
            code = analyst.generate_chart_code(
                self.dataset.text, question,
                previous_attempt={"code": code, "error": execution.error},
                conversation_text=analysis_context,
                chart_context=chart_context,
            )
            execution = executor.run_code(code, self.dataset.df)
            if config.DEBUG:
                print(f"\n[DEBUG] Chart retry {attempts}: ok={execution.ok}; "
                      f"error={execution.error!r}")

        if execution.ok and execution.chart_json:
            # Generate a text insight to accompany the chart (hybrid response)
            insight = analyst.write_chart_insight(
                self.dataset.text, question, code, execution
            )

            # Save to chart memory
            self.conversation.add_chart(
                question=question,
                code=code,
                description=execution.chart_description or "Chart",
                chart_json=execution.chart_json,
            )

            return AskResult(
                answer=insight,
                chart_json=execution.chart_json,
                chart_description=execution.chart_description,
            )
        elif execution.ok:
            # Code ran but no figure was generated
            return AskResult(
                answer="I wasn't able to generate a chart for that request. "
                       "Could you rephrase or be more specific about what "
                       "you'd like to visualize?"
            )
        else:
            return AskResult(
                answer=f"⚠️ I had trouble generating the chart: {execution.error}\n\n"
                       "Try rephrasing your request or being more specific "
                       "about what you'd like to see."
            )

    def ask(self, question: str) -> AskResult:
        """Process a user question and return an AskResult with text and optional chart."""
        context = self.conversation.to_prompt_text()
        if "?" not in question and re.search(r"\b(?:remember|keep in mind)\b", question, re.IGNORECASE):
            answer = ("Got it. I'll keep that in mind for this session. "
                      "I won't apply it as a data filter unless you ask me to.")
            self.conversation.add_turn(question, answer, is_analysis=False)
            return AskResult(answer=answer)

        analysis_context = self.conversation.to_analysis_prompt_text()
        route_result = message_handler.route_message(
            question=question,
            columns=[str(column) for column in self.dataset.df.columns],
            conversation=context,
            has_analysis_context=analysis_context !=
            "No previous data analysis. Do not infer filters from ordinary conversation.",
            has_chart_context=self.conversation.has_chart_context,
        )
        route = route_result["route"]
        if config.DEBUG:
            print(f"[router] Selected route: {route}")

        # --- Clock ---
        if route == "clock":
            answer = message_handler.answer_clock()
            self.conversation.add_turn(question, answer, is_analysis=False)
            return AskResult(answer=answer)

        # --- Explain Analysis ---
        if route == "explain_analysis":
            answer = message_handler.answer_explanation(question, self.conversation.last_analysis)
            self.conversation.add_turn(question, answer, is_analysis=False)
            return AskResult(answer=answer)

        # --- Conversation ---
        if route == "conversation":
            answer = route_result.get("reply") or message_handler.answer_conversation(question, context)
            self.conversation.add_turn(question, answer, is_analysis=False)
            return AskResult(answer=answer)

        # --- Visualization (new chart) ---
        if route == "visualization":
            result = self._run_visualization(question, analysis_context)
            self.conversation.add_turn(question, result.answer, is_analysis=True)
            return result

        # --- Modify Chart (follow-up on existing chart) ---
        if route == "modify_chart":
            chart_context = self.conversation.to_chart_context_text()
            result = self._run_visualization(question, analysis_context, chart_context)
            self.conversation.add_turn(question, result.answer, is_analysis=True)
            return result

        # --- Analysis (text-based, with optional auto-suggest) ---
        if config.DEBUG:
            print(f"\n[DEBUG] Dataset profile (only dataset context sent):\n{self.dataset.text}")
        code = analyst.generate_code(self.dataset.text, question,
                                     conversation_text=analysis_context)
        execution = executor.run_code(code, self.dataset.df)
        if config.DEBUG:
            print(f"\n[DEBUG] Generated code:\n{code}\n[DEBUG] Execution ok={execution.ok}; "
                  f"result={execution.result_text!r}; error={execution.error!r}")
        attempts = 0
        while not execution.ok and attempts < config.MAX_CODE_RETRIES:
            attempts += 1
            code = analyst.generate_code(
                self.dataset.text, question,
                previous_attempt={"code": code, "error": execution.error},
                conversation_text=analysis_context)
            execution = executor.run_code(code, self.dataset.df)
            if config.DEBUG:
                print(f"\n[DEBUG] Retry {attempts}: {code}\n[DEBUG] Execution "
                      f"ok={execution.ok}; result={execution.result_text!r}; error={execution.error!r}")
        answer = analyst.write_answer(self.dataset.text, question, code, execution,
                                      conversation_text=context)
        is_analysis = execution.ok and execution.result_text != "None"

        # Auto-suggest a visualization after text-only analysis
        viz_suggestion = None
        if is_analysis and execution.result_text:
            try:
                viz_suggestion = analyst.suggest_visualization(
                    question, execution.result_text,
                    [str(c) for c in self.dataset.df.columns],
                )
            except Exception:
                pass  # Non-critical — skip suggestion on failure

        if is_analysis:
            self.conversation.last_analysis = {
                "question": question,
                "code": code,
                "result": execution.result_text,
                "answer": answer,
            }
        self.conversation.add_turn(question, answer, is_analysis=is_analysis)
        return AskResult(answer=answer, visualization_suggestion=viz_suggestion)

