"""Routes incoming messages to data analysis, conversation, explanation, or local time."""
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config
import response_stream
from llm_clients import ProviderError, ProviderUnavailableError, call_conversation_llm, call_explanation_llm, classify_message

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
    r"dataset|data|trend|outlier)\b", re.I)
_VISUALIZATION_TERMS = re.compile(
    r"\b(chart|plot|graph|visuali[sz]e|bar chart|line chart|pie chart|histogram|"
    r"scatter|heatmap|distribution|correlation|dashboard|donut|box plot|"
    r"show me a .*(chart|graph|plot)|draw|diagram)\b", re.I)
_CHART_MODIFY_TERMS = re.compile(
    r"\b(change the (color|chart|type|title|label)|make it (horizontal|vertical)|"
    r"add a trend|switch to (?:a )?(?:bar|line|pie|scatter|area|box)|"
    r"update the (chart|title|axis)|rotate (?:it|the chart)|flip (?:it|the chart))\b", re.I)
_FOLLOWUP = re.compile(r"\b(what about|second highest|second-highest|same for|and for|why|instead|those|that one)\b", re.I)


def _fill(template: str, **values: str) -> str:
    """Replace known fields once, without interpreting placeholder-shaped user data."""
    return re.sub(r"\{\{(\w+)\}\}", lambda match: str(values.get(match.group(1), "")), template)


def route_message(question: str, columns: list[str], conversation: str,
                  has_analysis_context: bool, has_chart_context: bool = False) -> dict[str, str]:
    """Use Mistral to classify; local rules cover outages or malformed replies."""
    if _TIME_QUERY.search(question):
        return {"route": "clock", "reply": ""}
    if has_analysis_context and _EXPLANATION_QUERY.search(question):
        return {"route": "explain_analysis", "reply": ""}

    template = (_PROMPTS_DIR / "request_router.txt").read_text(encoding="utf-8")
    reply_instruction = ("For every route, set reply to an empty string. Classify only; the application will generate the answer separately."
                         if response_stream.current() else
                         "For conversation, write a concise, helpful user-facing answer in reply. Use conversation context and do not invent personal facts. For other routes set reply to an empty string.")
    prompt = _fill(template, reply_instruction=reply_instruction, columns=", ".join(columns)[:config.MAX_CONTEXT_CHARS],
                   conversation=(conversation or "None yet.")[:config.MAX_CONTEXT_CHARS],
                   question=question, has_analysis=str(has_analysis_context), has_chart=str(has_chart_context))
    try:
        result = json.loads(classify_message(prompt))
        route = result.get("route")
        if route in {"analysis", "conversation", "explain_analysis", "clock",
                     "visualization", "modify_chart"}:
            return {"route": route, "reply": "" if response_stream.current() else str(result.get("reply") or "")[:config.MAX_MESSAGE_CHARS]}
    except ProviderError as exc:
        if not isinstance(exc, ProviderUnavailableError):
            raise
    except Exception as exc:
        if config.DEBUG:
            print(f"[router] local_fallback=True; error_type={type(exc).__name__}")

    lowered = question.casefold()

    # Local fallback: chart modification (only if there's a previous chart)
    if has_chart_context and _CHART_MODIFY_TERMS.search(question):
        return {"route": "modify_chart", "reply": ""}

    # Local fallback: visualization request
    if _VISUALIZATION_TERMS.search(question):
        return {"route": "visualization", "reply": ""}

    if _EXPLANATION_QUERY.search(question) and has_analysis_context:
        return {"route": "explain_analysis", "reply": ""}
    if _CONVERSATION_EXPLANATION_QUERY.search(question):
        return {"route": "conversation", "reply": ""}
    if _EXPLANATION_QUERY.search(question):
        return {"route": "explain_analysis", "reply": ""}
    if has_analysis_context and _FOLLOWUP.search(question):
        return {"route": "analysis", "reply": ""}
    if any(str(column).casefold() in lowered for column in columns) or _ANALYSIS_TERMS.search(question):
        return {"route": "analysis", "reply": ""}
    return {"route": "conversation", "reply": ""}


def answer_conversation(question: str, conversation: str, *, dataset_loaded: bool = True) -> str:
    template = (_PROMPTS_DIR / "conversation_response.txt").read_text(encoding="utf-8")
    prompt = _fill(template, conversation=(conversation or "None yet.")[:config.MAX_CONTEXT_CHARS], question=question,
                   dataset_status="A dataset is loaded." if dataset_loaded else "No dataset is loaded. No dataset calculations or charts exist in this session.",
                   clock=answer_clock())
    return call_conversation_llm(prompt)


def answer_explanation(question: str, last_analysis: dict | None) -> str:
    if not last_analysis:
        return "I don’t have a previous successful analysis to explain yet. Ask a data question first."
    template = (_PROMPTS_DIR / "analysis_explanation.txt").read_text(encoding="utf-8")
    prompt = _fill(template, question=question,
                   analysis_question=str(last_analysis.get("question", ""))[:2000],
                   code=str(last_analysis.get("code", ""))[:8000],
                   result=str(last_analysis.get("result", ""))[:config.MAX_RESULT_CHARS],
                   answer=str(last_analysis.get("answer", ""))[:2000])
    return call_explanation_llm(prompt)


def answer_clock() -> str:
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    return now.strftime("It is %I:%M %p on %A, %B %d, %Y (%Z).")
