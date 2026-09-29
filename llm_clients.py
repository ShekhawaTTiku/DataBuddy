"""The only module that calls external LLM provider SDKs."""
import time

import config

_MAX_RETRIES = 2


class ProviderUnavailableError(RuntimeError):
    """A temporary provider outage or quota limit that permits failover."""


def _is_transient(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status == 429 or (isinstance(status, int) and status >= 500):
        return True
    name = type(exc).__name__.lower()
    return any(part in name for part in (
        "timeout", "ratelimit", "rate_limit", "connection", "internalserver",
        "servererror", "serviceunavailable", "resourceexhausted", "temporarilyunavailable",
    ))


def _retry(call, provider):
    last_error = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return call()
        except Exception as exc:
            last_error = exc
            if not _is_transient(exc):
                raise RuntimeError(f"{provider} API call failed: {type(exc).__name__}: {exc}") from exc
            if attempt < _MAX_RETRIES:
                time.sleep(0.8 * (2 ** attempt))
    raise ProviderUnavailableError(
        f"{provider} is temporarily unavailable or rate-limited after {_MAX_RETRIES + 1} attempts: "
        f"{type(last_error).__name__}: {last_error}"
    ) from last_error


def _text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
            for part in content
        )
    return str(content or "")


def _mistral_completion(prompt: str, model: str, json_mode: bool = False) -> str:
    if not config.MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is not set in the environment or .env file.")
    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import Mistral
    client = Mistral(api_key=config.MISTRAL_API_KEY)

    def request():
        options = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if json_mode:
            options["response_format"] = {"type": "json_object"}
        return client.chat.complete(**options)

    response = _retry(request, "Mistral")
    return _text_content(response.choices[0].message.content)


def call_fallback_llm(prompt: str) -> str:
    """Run an analysis prompt on Mistral Medium after a retryable Groq failure."""
    return _mistral_completion(prompt, config.FALLBACK_MODEL)


def call_conversation_llm(prompt: str) -> str:
    """Answer ordinary conversation with the lightweight Ministral model."""
    return _mistral_completion(prompt, config.CONVERSATION_MODEL)


def call_explanation_llm(prompt: str) -> str:
    """Explain the latest analysis using the more capable Ministral model."""
    return _mistral_completion(prompt, config.EXPLANATION_MODEL)


def classify_message(prompt: str) -> str:
    """Return the Ministral router's JSON classification response."""
    return _mistral_completion(prompt, config.CONVERSATION_MODEL, json_mode=True)


def call_analysis_llm(prompt: str, temperature: float = 0.2) -> str:
    """Prefer Groq; fail over to Mistral only after transient failures/rate limits."""
    try:
        if not config.GROQ_API_KEY:
            raise ProviderUnavailableError("GROQ_API_KEY is not set.")
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)
        response = _retry(lambda: client.chat.completions.create(
            model=config.ANALYSIS_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        ), "Groq")
        return response.choices[0].message.content or ""
    except ProviderUnavailableError as groq_error:
        if config.DEBUG:
            print(f"[fallback] {groq_error}; switching this analysis call to Mistral.")
        try:
            return call_fallback_llm(prompt)
        except Exception as mistral_error:
            raise RuntimeError(
                f"Groq failed and the Mistral fallback could not answer. "
                f"Groq: {groq_error}; Mistral: {mistral_error}"
            ) from mistral_error


def call_memory_llm(prompt: str) -> str:
    """Use Gemini only for compact conversation summaries."""
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment or .env file.")
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    chat = client.chats.create(model=config.MEMORY_MODEL)
    response = _retry(lambda: chat.send_message(prompt), "Gemini")
    return (response.text or "").strip()
