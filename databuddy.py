"""Orchestrates DataBuddy's question-to-answer pipeline."""
import re

import config
import analyst
import executor
import message_handler
from dataset_state import load_and_profile
from conversation_state import ConversationState


class DataBuddy:
    def __init__(self, dataset_path: str):
        self.dataset = load_and_profile(dataset_path)
        self.conversation = ConversationState()

    def ask(self, question: str) -> str:
        context = self.conversation.to_prompt_text()
        if "?" not in question and re.search(r"\b(?:remember|keep in mind)\b", question, re.IGNORECASE):
            answer = ("Got it. I’ll keep that in mind for this session. "
                      "I won’t apply it as a data filter unless you ask me to.")
            self.conversation.add_turn(question, answer, is_analysis=False)
            return answer

        analysis_context = self.conversation.to_analysis_prompt_text()
        route_result = message_handler.route_message(
            question=question,
            columns=[str(column) for column in self.dataset.df.columns],
            conversation=context,
            has_analysis_context=analysis_context !=
            "No previous data analysis. Do not infer filters from ordinary conversation.",
        )
        route = route_result["route"]
        if config.DEBUG:
            print(f"[router] Selected route: {route}")
        if route == "clock":
            answer = message_handler.answer_clock()
            self.conversation.add_turn(question, answer, is_analysis=False)
            return answer
        if route == "explain_analysis":
            answer = message_handler.answer_explanation(question, self.conversation.last_analysis)
            self.conversation.add_turn(question, answer, is_analysis=False)
            return answer
        if route == "conversation":
            answer = route_result.get("reply") or message_handler.answer_conversation(question, context)
            self.conversation.add_turn(question, answer, is_analysis=False)
            return answer

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
        if is_analysis:
            self.conversation.last_analysis = {
                "question": question,
                "code": code,
                "result": execution.result_text,
                "answer": answer,
            }
        self.conversation.add_turn(question, answer, is_analysis=is_analysis)
        return answer
