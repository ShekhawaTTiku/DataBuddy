"""Construct bounded analysis prompts; provider calls live in llm_clients."""
import re
from pathlib import Path

import config
from llm_clients import call_analysis_llm, call_narration_llm
from executor import ExecutionResult

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def _load_template(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _prompt(filename: str, **values: str) -> str:
    # Substitute the template once, so placeholder-shaped dataset text remains data.
    template = _load_template(filename)
    remaining = max(0, config.MAX_PROMPT_CHARS - len(template))
    bounded: dict[str, str] = {}
    priority = ("question", "result", "execution_status", "chart_description", "profile",
                "code", "previous_attempt", "conversation", "chart_context", "columns")
    for key in priority:
        if key not in values:
            continue
        count = max(1, len(re.findall(r"\{\{" + key + r"\}\}", template)))
        text = str(values[key])
        allowed = remaining // count
        bounded[key] = text if len(text) <= allowed else text[:max(0, allowed - 15)] + "... [truncated]"[:allowed]
        remaining -= len(bounded[key]) * count
    return _PLACEHOLDER.sub(lambda m: bounded.get(m.group(1), ""), template)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"\A\x60{3}(?:\w*)\s*\n(.*?)\n?\x60{3}\s*\Z", text, re.DOTALL)
    return match.group(1).strip() if match else text


def _previous(previous_attempt: dict | None) -> str:
    if not previous_attempt:
        return ""
    return (f"Code:\n{previous_attempt.get('code', '')[:config.MAX_CODE_CHARS]}\n\n"
            f"Error:\n{str(previous_attempt.get('error', ''))[:1000]}")


def _complete(prompt: str, label: str) -> str:
    if config.DEBUG:
        print(f"[analysis] operation={label}; prompt_chars={len(prompt)}")
    return (call_analysis_llm if label in {"generate_code", "generate_chart"} else call_narration_llm)(prompt)


def generate_code(profile: str, question: str, previous_attempt: dict | None = None,
                  conversation_text: str = "None yet.") -> str:
    prompt = _prompt("code_generation.txt", profile=profile, question=question,
                     conversation=conversation_text[:config.MAX_CONTEXT_CHARS],
                     previous_attempt=_previous(previous_attempt))
    return _strip_code_fences(_complete(prompt, "generate_code"))


def generate_chart_code(profile: str, question: str, previous_attempt: dict | None = None,
                        conversation_text: str = "None yet.",
                        chart_context: str = "None yet.") -> str:
    prompt = _prompt("chart_generation.txt", profile=profile, question=question,
                     conversation=conversation_text[:config.MAX_CONTEXT_CHARS // 2],
                     chart_context=chart_context[:config.MAX_CONTEXT_CHARS // 2],
                     previous_attempt=_previous(previous_attempt))
    return _strip_code_fences(_complete(prompt, "generate_chart"))


def write_answer(profile: str, question: str, code: str, execution: ExecutionResult,
                 conversation_text: str = "None yet.") -> str:
    if not execution.ok:
        raise ValueError("Failed execution cannot be described as a completed analysis.")
    prompt = _prompt("final_response.txt", question=question, profile=profile,
                     conversation=conversation_text[:config.MAX_CONTEXT_CHARS // 2],
                     code=code[:config.MAX_CODE_CHARS], execution_status="Success",
                     result=execution.result_text or "No computed result.")
    return _complete(prompt, "write_answer")


def write_chart_insight(profile: str, question: str, code: str, execution: ExecutionResult) -> str:
    if not execution.ok or not execution.chart_json:
        raise ValueError("A chart insight requires a successfully generated chart.")
    # The runner supplies a bounded summary of actual plotted values.
    if execution.result_text in {None, "", "None"}:
        return "The chart is ready. No numerical summary was available for a reliable written interpretation."
    prompt = _prompt("chart_insight.txt", question=question,
                     chart_description=execution.chart_description or "Chart",
                     result=execution.result_text)
    return _complete(prompt, "chart_insight")


def suggest_visualization(question: str, result_text: str, columns: list[str]) -> str | None:
    prompt = _prompt("chart_suggestion.txt", question=question, result=result_text or "",
                     columns=", ".join(columns)[:config.MAX_CONTEXT_CHARS])
    try:
        response = _complete(prompt, "suggest_chart").strip()
        return response if response and response != "NO_SUGGESTION" else None
    except Exception:
        return None
