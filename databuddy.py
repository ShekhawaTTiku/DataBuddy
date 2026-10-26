"""UI-independent, session-only question-to-answer pipeline."""
import re
from dataclasses import dataclass

import analyst
import config
import executor
import message_handler
import telemetry
from conversation_state import ConversationState
from dataset_state import load_and_profile
from llm_clients import ProviderError, request_budget


@dataclass
class AskResult:
    """A response with optional computed evidence, independent of Streamlit."""
    answer: str
    chart_json: str | None = None
    chart_description: str | None = None
    visualization_suggestion: str | None = None
    result_text: str | None = None
    code: str | None = None
    status: str = "success"
    memory_notice: str | None = None
    result_table: dict | None = None


def _nonempty(text: str) -> str:
    value = (text or "").strip()
    if not value:
        raise ValueError("The explanation provider returned an empty response.")
    return value[:config.MAX_MESSAGE_CHARS]


class DataBuddy:
    def __init__(self, dataset_source, filename: str | None = None):
        self.dataset = load_and_profile(dataset_source, filename=filename)
        self.conversation = ConversationState()

    def _remember_analysis(self, question: str, code: str, execution, answer: str) -> None:
        self.conversation.last_analysis = {
            "question": question, "code": code,
            "result": execution.result_text or "", "answer": answer,
        }

    def _run_visualization(self, question: str, analysis_context: str,
                           chart_context: str = "None yet.") -> AskResult:
        previous = None
        for _ in range(config.MAX_CODE_RETRIES + 1):
            telemetry.stage("Preparing chart")
            code = analyst.generate_chart_code(
                self.dataset.text, question, previous_attempt=previous,
                conversation_text=analysis_context, chart_context=chart_context,
            )
            telemetry.stage("Running calculation")
            execution = executor.run_code(code, self.dataset.df)
            if execution.ok:
                break
            previous = {"code": code, "error": execution.error}

        if not execution.ok:
            return AskResult(
                answer="I couldn't generate that chart. " + (execution.error or "Please try a more specific question."),
                code=code, status="error",
            )
        if not execution.chart_json:
            return AskResult(
                answer=execution.chart_description or "No chart was produced. Please specify what to plot.",
                code=code, status="clarification",
            )

        # Keep successful work before asking for optional narration.
        self.conversation.add_chart(question, code, execution.chart_description or "Chart", execution.chart_json)
        status = "success"
        try:
            telemetry.stage("Writing answer")
            insight = _nonempty(analyst.write_chart_insight(self.dataset.text, question, code, execution))
        except Exception as error:
            status = "partial"
            insight = "Your chart is ready. The written explanation is unavailable right now."
            if isinstance(error, ProviderError):
                insight += " " + str(error)
        self._remember_analysis(question, code, execution, insight)
        return AskResult(
            answer=insight, chart_json=execution.chart_json,
            chart_description=execution.chart_description, result_text=execution.result_text,
            code=code, status=status,
            result_table=execution.result_table,
        )

    def ask(self, question: str) -> AskResult:
        """Share one provider deadline across routing, generation and narration."""
        with request_budget():
            result = self._ask(question)
            if question.strip() and len(question.strip()) <= config.MAX_QUESTION_CHARS:
                is_analysis = bool(result.code and result.result_text and result.status in {"success", "partial"})
                self.conversation.add_turn(question.strip(), result.answer, is_analysis=is_analysis)
                telemetry.stage("Updating session memory")
                self.conversation.update_memory(question.strip(), result.answer,
                                                result_text=result.result_text, status=result.status)
                result.memory_notice = self.conversation.memory_notice
            return result

    def _ask(self, question: str) -> AskResult:
        question = question.strip()
        if not question:
            return AskResult(answer="Please enter a question about your data.", status="clarification")
        if len(question) > config.MAX_QUESTION_CHARS:
            return AskResult(
                answer=f"Please keep your question within {config.MAX_QUESTION_CHARS:,} characters.",
                status="clarification",
            )
        context = self.conversation.to_prompt_text()
        if "?" not in question and re.search(r"\b(?:remember|keep in mind)\b", question, re.IGNORECASE):
            answer = "Got it. I'll keep that in mind for this session without applying it as a data filter."
            return AskResult(answer=answer)

        analysis_context = self.conversation.to_analysis_prompt_text()
        telemetry.stage("Understanding question")
        route_result = message_handler.route_message(
            question=question, columns=[str(c) for c in self.dataset.df.columns],
            conversation=context, has_analysis_context=bool(self.conversation.last_analysis),
            has_chart_context=self.conversation.has_chart_context,
        )
        route = route_result["route"]
        if config.DEBUG:
            print(f"[router] route={route}")

        if route == "clock":
            answer = message_handler.answer_clock()
        elif route == "explain_analysis":
            try:
                answer = _nonempty(message_handler.answer_explanation(question, self.conversation.last_analysis))
            except Exception as error:
                if not self.conversation.last_analysis:
                    raise
                return AskResult(
                    answer="The written explanation is unavailable. You can still inspect the previous computed result."
                           + (" " + str(error) if isinstance(error, ProviderError) else ""),
                    result_text=self.conversation.last_analysis["result"],
                    code=self.conversation.last_analysis["code"], status="partial",
                )
        elif route == "conversation":
            answer = _nonempty(route_result.get("reply") or message_handler.answer_conversation(question, context))
        elif route in {"visualization", "modify_chart"}:
            if route == "modify_chart" and not self.conversation.has_chart_context:
                return AskResult(answer="Create a chart first, then ask me to change it.", status="clarification")
            result = self._run_visualization(
                question, analysis_context,
                self.conversation.to_chart_context_text() if route == "modify_chart" else "None yet.",
            )
            return result
        else:
            previous = None
            for _ in range(config.MAX_CODE_RETRIES + 1):
                telemetry.stage("Preparing calculation")
                code = analyst.generate_code(
                    self.dataset.text, question, previous_attempt=previous, conversation_text=analysis_context,
                )
                telemetry.stage("Running calculation")
                execution = executor.run_code(code, self.dataset.df)
                if execution.ok:
                    break
                previous = {"code": code, "error": execution.error}
            if not execution.ok:
                result = AskResult(
                    answer="I couldn't calculate that result. " + (execution.error or "Please rephrase the question."),
                    code=code, status="error",
                )
                return result
            if execution.result_text in {None, "None", ""}:
                result = AskResult(
                    answer="No computed result was produced. Please clarify the calculation or columns you mean.",
                    code=code, status="clarification",
                )
                return result
            status = "success"
            try:
                telemetry.stage("Writing answer")
                answer = _nonempty(analyst.write_answer(self.dataset.text, question, code, execution, conversation_text=context))
            except Exception as error:
                status = "partial"
                answer = "The calculation completed. The written explanation is unavailable; inspect the computed result below."
                if isinstance(error, ProviderError):
                    answer += " " + str(error)
            self._remember_analysis(question, code, execution, answer)
            suggestion = None
            if config.ENABLE_VISUALIZATION_SUGGESTIONS:
                try:
                    suggestion = analyst.suggest_visualization(question, execution.result_text, list(map(str, self.dataset.df.columns)))
                except Exception:
                    pass
            return AskResult(answer=answer, result_text=execution.result_text, code=code,
                             result_table=execution.result_table,
                             visualization_suggestion=suggestion, status=status)

        return AskResult(answer=answer)
