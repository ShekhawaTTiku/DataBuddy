"""Provider boundary with bounded requests and safe, actionable errors."""
from contextlib import contextmanager
from contextvars import ContextVar
import random
import time

from backend.core import config
from backend.core import telemetry
from backend.core import response_stream
_deadline = ContextVar("databuddy_provider_deadline", default=None)


class ProviderError(RuntimeError):
    """Safe to show to a user; never includes raw provider response bodies."""


class ProviderUnavailableError(ProviderError):
    """A temporary failure permits analysis failover."""


@contextmanager
def request_budget(seconds: float | None = None):
    """Share one elapsed-time budget across routing, analysis and explanation."""
    parent = _deadline.get()
    if parent is not None and seconds is None:
        yield
        return
    deadline = time.monotonic() + (config.REQUEST_TIMEOUT_SECONDS if seconds is None else seconds)
    token = _deadline.set(min(parent, deadline) if parent is not None else deadline)
    try:
        yield
    finally:
        _deadline.reset(token)


def _status(exc: Exception):
    # Google Gen AI uses .code; Groq/Mistral use .status_code.
    return getattr(exc, "status_code", None) or getattr(exc, "code", None)


def _is_transient(exc: Exception) -> bool:
    status = _status(exc)
    if status in (408, 429) or (isinstance(status, int) and 500 <= status <= 599):
        return True
    return any(part in type(exc).__name__.lower() for part in (
        "timeout", "ratelimit", "connection", "internalserver", "serviceunavailable",
    ))


def _safe_error(exc: Exception, provider: str) -> str:
    status = _status(exc)
    if status in (401, 403):
        return f"{provider} could not authenticate or access the configured model. Check its API key and model access."
    if status == 429:
        return f"{provider}'s request or free-quota limit was reached. Wait and try again; no paid upgrade is required by this app."
    if status in (400, 404, 422):
        return f"{provider} rejected the request or configured model. Check the model setting and try a smaller question."
    if "timeout" in type(exc).__name__.lower() or status == 408:
        return f"{provider} took too long to respond. Try again later."
    return f"{provider} is unavailable or could not finish the request. Try again later."


def _validate_prompt(prompt: str) -> None:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ProviderError("The model request was empty. Try asking the question again.")
    if len(prompt) > config.MAX_PROMPT_CHARS:
        raise ProviderError("This question needs too much context. Reset the conversation or use a dataset with fewer columns.")


def _retry(call, provider: str):
    """The callable receives its remaining per-attempt timeout in seconds."""
    deadline = _deadline.get() or (time.monotonic() + config.REQUEST_TIMEOUT_SECONDS)
    for attempt in range(config.PROVIDER_MAX_RETRIES + 1):
        response_stream.check_cancelled()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProviderUnavailableError("The request time limit was reached. Try a simpler question.")
        try:
            telemetry.event("attempt", provider=provider)
            result = call(min(config.PROVIDER_TIMEOUT_SECONDS, remaining))
            response_stream.check_cancelled()
            return result
        except (ProviderError, response_stream.ResponseCancelled):
            raise
        except Exception as exc:
            response_stream.check_cancelled()
            telemetry.record_limits(getattr(getattr(exc, "response", None), "headers", None), provider)
            if not _is_transient(exc):
                raise ProviderError(_safe_error(exc, provider)) from None
            if attempt >= config.PROVIDER_MAX_RETRIES:
                raise ProviderUnavailableError(_safe_error(exc, provider)) from None
            delay = min(0.6 * (2 ** attempt) + random.uniform(0, 0.2), max(0, deadline - time.monotonic()))
            if delay:
                time.sleep(delay)
    raise ProviderUnavailableError(f"{provider} could not complete the request.")


def _text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "") for part in content)
    return ""


def _consume_stream(chunks, provider, model):
    """Deliver only answer content; retain a single usage report per attempt."""
    text = ""
    usage_response = None
    finished = False
    deadline = _deadline.get()
    delivery = response_stream.current()
    bind = getattr(delivery.cancelled, "bind", None) if delivery else None
    if bind:
        bind(getattr(chunks, "close", None))
    try:
        for chunk in chunks:
            response_stream.check_cancelled()
            if deadline and time.monotonic() >= deadline:
                raise ProviderUnavailableError("The response time limit was reached.")
            data = getattr(chunk, "data", chunk)
            if getattr(data, "usage", None) is not None:
                usage_response = data
            elif getattr(getattr(data, "x_groq", None), "usage", None) is not None:
                usage_response = data.x_groq
            choices = getattr(data, "choices", None) or []
            for choice in choices[:1]:
                delta = getattr(choice, "delta", None)
                value = _text_content(getattr(delta, "content", None))
                if value:
                    value = value[:max(0, config.MAX_MESSAGE_CHARS - len(text))]
                    text += value
                    response_stream.text(value)
                if getattr(choice, "finish_reason", None) is not None:
                    finished = True
    except response_stream.ResponseCancelled:
        raise
    except Exception as exc:
        response_stream.check_cancelled()
        if text:
            error = ProviderUnavailableError if isinstance(exc, ProviderUnavailableError) or _is_transient(exc) else ProviderError
            raise error(_safe_error(exc, provider)) from None
        raise
    finally:
        if bind:
            bind(None)
        if usage_response is not None:
            telemetry.record_usage(usage_response, provider, model)
        close = getattr(chunks, "close", None)
        if close:
            try:
                close()
            except Exception:
                pass
    response_stream.check_cancelled()
    if not finished or not text.strip():
        raise ProviderUnavailableError(f"{provider} did not finish the answer. Please try again later.")
    return text.strip()


def _mistral_completion(prompt: str, model: str, json_mode: bool = False,
                        max_tokens: int | None = None, stream: bool = False) -> str:
    _validate_prompt(prompt)
    if not config.MISTRAL_API_KEY:
        raise ProviderUnavailableError("MISTRAL_API_KEY is missing. Configure it to use chat, routing and provider fallback.")
    if not model.strip():
        raise ProviderError("The Mistral model setting is empty. Set a model available to your account.")
    try:
        from mistralai import Mistral
    except ImportError:
        # SDK 2.10.1 exposes Mistral here; keep compatibility with both layouts.
        from mistralai.client import Mistral

    def request(timeout):
        with Mistral(api_key=config.MISTRAL_API_KEY, timeout_ms=max(1, int(timeout * 1000)), retry_config=None) as client, response_stream.connection(client):
            options = dict(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens or config.MAX_RESPONSE_TOKENS, temperature=0.2, retries=None)
            if json_mode:
                options["response_format"] = {"type": "json_object"}
            if stream:
                return _consume_stream(client.chat.stream(**options), "Mistral", model)
            response = client.chat.complete(**options)
            telemetry.record_usage(response, "Mistral", model)
            return _text_content(response.choices[0].message.content).strip()
    return _retry(request, "Mistral")


def call_fallback_llm(prompt: str) -> str:
    return _mistral_completion(prompt, config.FALLBACK_MODEL)


def call_conversation_llm(prompt: str) -> str:
    if response_stream.current():
        return _mistral_completion(prompt, config.CONVERSATION_MODEL, stream=True)
    return _mistral_completion(prompt, config.CONVERSATION_MODEL)


def call_explanation_llm(prompt: str) -> str:
    if response_stream.current() and not response_stream.current().finalizing:
        return _mistral_completion(prompt, config.EXPLANATION_MODEL, stream=True)
    return _mistral_completion(prompt, config.EXPLANATION_MODEL)


def classify_message(prompt: str) -> str:
    return _mistral_completion(prompt, config.CONVERSATION_MODEL, json_mode=True)


def _groq_completion(prompt: str, temperature: float = 0.2, stream: bool = False) -> str:
    _validate_prompt(prompt)
    if not config.GROQ_API_KEY:
        raise ProviderUnavailableError("GROQ_API_KEY is missing.")
    if not config.ANALYSIS_MODEL.strip():
        raise ProviderError("ANALYSIS_MODEL is empty. Set a Groq model available to your account.")
    from groq import Groq

    def request(timeout):
        with Groq(api_key=config.GROQ_API_KEY, timeout=timeout, max_retries=0) as client, response_stream.connection(client):
            options = dict(model=config.ANALYSIS_MODEL, messages=[{"role": "user", "content": prompt}], temperature=temperature, max_completion_tokens=config.MAX_RESPONSE_TOKENS)
            if stream:
                options["stream"] = True
                # SDK 1.7.0 exposes this API option through extra_body.
                options["extra_body"] = {"stream_options": {"include_usage": True}}
            if telemetry.enabled():
                raw = client.chat.completions.with_raw_response.create(**options)
                telemetry.record_limits(raw.headers, "Groq")
                response = raw.parse()
            else:
                response = client.chat.completions.create(**options)
            if stream:
                return _consume_stream(response, "Groq", config.ANALYSIS_MODEL)
            telemetry.record_usage(response, "Groq", config.ANALYSIS_MODEL)
            text = (response.choices[0].message.content or "").strip()
            if not text:
                raise ProviderUnavailableError("Groq returned no answer. Try again later.")
            return text
    return _retry(request, "Groq")


def _failover(primary, fallback, minimum_primary_seconds: float = 0):
    """Reserve part of the shared deadline for Mistral; never mask config errors."""
    with request_budget():
        try:
            remaining = max(0, _deadline.get() - time.monotonic())
            primary_seconds = min(remaining, max(remaining * 0.6, minimum_primary_seconds)) if config.MISTRAL_API_KEY else remaining
            with request_budget(seconds=primary_seconds):
                return primary()
        except ProviderUnavailableError as error:
            if not config.MISTRAL_API_KEY:
                raise ProviderUnavailableError(f"{error} Mistral fallback is not configured.") from None
            telemetry.event("fallback")
            if response_stream.current() and not response_stream.current().finalizing and response_stream.current().answer:
                response_stream.reset_answer("The explanation was interrupted. Restarting with the backup provider.")
            return fallback()


def call_analysis_llm(prompt: str, temperature: float = 0.2) -> str:
    _validate_prompt(prompt)
    return _failover(lambda: _groq_completion(prompt, temperature), lambda: call_fallback_llm(prompt))


def call_narration_llm(prompt: str) -> str:
    _validate_prompt(prompt)
    if response_stream.current():
        return _failover(lambda: _groq_completion(prompt, stream=True), lambda: call_explanation_llm(prompt))
    return _failover(lambda: _groq_completion(prompt), lambda: call_explanation_llm(prompt))


def _gemini_completion(prompt: str) -> str:
    _validate_prompt(prompt)
    if not config.GEMINI_API_KEY:
        raise ProviderUnavailableError("GEMINI_API_KEY is missing.")
    if not config.MEMORY_MODEL.strip():
        raise ProviderError("MEMORY_MODEL is empty. Set a Gemini model available to your account.")
    from google import genai
    from google.genai import types

    def request(timeout):
        # Gemini rejects deadlines shorter than ten seconds. Do not exceed the
        # shared budget to satisfy that constraint: let Mistral use the remainder.
        if timeout < 10:
            raise ProviderUnavailableError("Too little request time remains for Gemini; using memory fallback if available.")
        options = types.HttpOptions(timeout=max(1, int(timeout * 1000)),
                                    retry_options=types.HttpRetryOptions(attempts=1))
        with genai.Client(api_key=config.GEMINI_API_KEY, vertexai=False, http_options=options) as client:
            response = client.models.generate_content(
                model=config.MEMORY_MODEL, contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=config.MAX_MEMORY_RESPONSE_TOKENS,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    thinking_config=(types.ThinkingConfig(thinking_level="minimal")
                                     if config.MEMORY_MODEL.startswith(("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")) else None),
                ),
            )
            telemetry.record_usage(response, "Gemini", config.MEMORY_MODEL)
            text = (response.text or "").strip()
            if not text:
                raise ProviderUnavailableError("Gemini returned no memory note. Recent conversation is still available.")
            return text
    return _retry(request, "Gemini")


def call_memory_llm(prompt: str) -> str:
    _validate_prompt(prompt)
    return _failover(lambda: _gemini_completion(prompt), lambda: _mistral_completion(
        prompt, config.EXPLANATION_MODEL, max_tokens=config.MAX_MEMORY_RESPONSE_TOKENS),
        minimum_primary_seconds=10.1)
