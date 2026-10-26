"""Request-local, content-free usage and progress observations."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

_observer = ContextVar("databuddy_observer", default=None)


def enabled():
    return _observer.get() is not None


def record_limits(headers, provider):
    if provider != "Groq" or headers is None:
        return
    values = {}
    for key in ("x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens",
                "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens", "retry-after"):
        value = headers.get(key)
        # Only numeric quota counts or duration expressions; no raw headers/bodies.
        if isinstance(value, str) and len(value) < 50 and all(c in "0123456789.dhms " for c in value):
            values[key] = value
    if values:
        event("limits", provider=provider, values=values, at=datetime.now(timezone.utc).isoformat())


@contextmanager
def observe(events, progress=lambda stage: None):
    token = _observer.set((events, progress))
    try:
        yield
    finally:
        _observer.reset(token)


def stage(value):
    current = _observer.get()
    if current:
        current[1](value)


def event(kind, **values):
    current = _observer.get()
    if current:
        current[0].append({"kind": kind, **values})


def _number(obj, name):
    value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    return value if type(value) is int and value >= 0 else None


def record_usage(response, provider, model):
    """Allowlist numeric metadata only; never retain the response or prompt."""
    usage = getattr(response, "usage_metadata" if provider == "Gemini" else "usage", None)
    gemini = provider == "Gemini"
    input_tokens = _number(usage, "prompt_token_count" if gemini else "prompt_tokens")
    output_tokens = _number(usage, "candidates_token_count" if gemini else "completion_tokens")
    total = _number(usage, "total_token_count" if gemini else "total_tokens")
    details = getattr(usage, "completion_tokens_details", None)
    cached = getattr(usage, "prompt_tokens_details", None)
    event("usage", provider=provider, model=model, input=input_tokens, output=output_tokens,
          total=total, reasoning=_number(usage, "thoughts_token_count") if gemini else _number(details, "reasoning_tokens"),
          cached=_number(usage, "cached_content_token_count") if gemini else _number(cached, "cached_tokens"),
          at=datetime.now(timezone.utc).isoformat())


def summarize(events):
    calls = [e for e in events if e["kind"] == "usage"]
    attempts = sum(e["kind"] == "attempt" for e in events)
    reported = [c for c in calls if c["total"] is not None]
    return {"calls": calls, "attempts": attempts, "limits": [e for e in events if e["kind"] == "limits"],
            "fallbacks": sum(e["kind"] == "fallback" for e in events),
            "total": sum(c["total"] for c in reported),
            "complete": bool(attempts) and len(reported) == attempts}
