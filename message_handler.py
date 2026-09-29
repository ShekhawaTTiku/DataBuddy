"""Routes incoming messages to data analysis, conversation, explanation, or local time."""
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from llm_clients import call_conversation_llm, call_explanation_llm, classify_message

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_TIME_QUERY = re.compile(
    r"\b(what(?:'s| is) the time|what time is it|current time|time right now|"
    r"what(?:'s| is) today's date|what date is it|current date|today's date)\b", re.I)
_EXPLANATION_QUERY = re.compile(
    r"\b(how did you know|how do you know|how was that calculated|show your calculation|"
    r"why did you (?:say|answer|conclude)|why (?:is|was) (?:that|the answer|the result)|"
    r"explain (?:that|your answer|the result))\b", re.I)
_CONVERSATION_EXPLANATION_QUERY = re.compile(
    r"\b(?:why did you say|why did you answer|why do you say|why do you answer|"
    r"how did you know|how do you know)\b", re.I)
_ANALYSIS_TERMS = re.compile(
    r"\b(sum|total|average|mean|median|count|highest|lowest|top|bottom|compare|"
    r"group|grouped|filter|sales|profit|revenue|rows|columns|missing values|"
    r"dataset|data|chart|plot|trend|correlation|outlier|distribution)\b", re.I)
_FOLLOWUP = re.compile(r"\b(what about|second highest|second-highest|same for|and for|why|instead|those|that one)\b", re.I)


def route_message(question: str, columns: list[str], conversation: str,
                  has_analysis_context: bool) -> dict[str, str]:
    """Use the third LLM to classify; fall back to local rules if it is unavailable."""
    if _TIME_QUERY.search(question):
        return {"route": "clock", "reply": ""}

    template = (_PROMPTS_DIR / "request_router.txt").read_text(encoding="utf-8")
    prompt = template.replace("{{columns}}", ", ".join(columns))
    prompt = prompt.replace("{{conversation}}", conversation or "None yet.")
    prompt = prompt.replace("{{question}}", question)
    try:
        result = json.loads(classify_message(prompt))
        route = result.get("route")
        if route in {"analysis", "conversation", "explain_analysis", "clock"}:
            return {"route": route, "reply": str(result.get("reply") or "")}
    except Exception as exc:
        if config.DEBUG:
            print(f"[router] LLM classification unavailable; using local fallback: {exc}")

    lowered = question.casefold()
    if has_analysis_context and _FOLLOWUP.search(question):
        return {"route": "analysis", "reply": ""}
    if _CONVERSATION_EXPLANATION_QUERY.search(question):
        return {"route": "conversation", "reply": ""}
    if _EXPLANATION_QUERY.search(question):
        return {"route": "explain_analysis", "reply": ""}
    if any(str(column).casefold() in lowered for column in columns) or _ANALYSIS_TERMS.search(question):
        return {"route": "analysis", "reply": ""}
    return {"route": "conversation", "reply": ""}


def answer_conversation(question: str, conversation: str) -> str:
    template = (_PROMPTS_DIR / "conversation_response.txt").read_text(encoding="utf-8")
    prompt = template.replace("{{conversation}}", conversation or "None yet.")
    prompt = prompt.replace("{{question}}", question)
    return call_conversation_llm(prompt)


def answer_explanation(question: str, last_analysis: dict | None) -> str:
    if not last_analysis:
        return "I don’t have a previous successful analysis to explain yet. Ask a data question first."
    template = (_PROMPTS_DIR / "analysis_explanation.txt").read_text(encoding="utf-8")
    prompt = template.replace("{{question}}", question)
    prompt = prompt.replace("{{analysis_question}}", str(last_analysis.get("question", "")))
    prompt = prompt.replace("{{code}}", str(last_analysis.get("code", "")))
    prompt = prompt.replace("{{result}}", str(last_analysis.get("result", "")))
    prompt = prompt.replace("{{answer}}", str(last_analysis.get("answer", "")))
    return call_explanation_llm(prompt)


def answer_clock() -> str:
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    return now.strftime("It is %I:%M %p on %A, %B %d, %Y (%Z).")
