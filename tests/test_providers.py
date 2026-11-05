import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from backend.core import config
from backend.core import llm_clients as clients
class FakeError(Exception):
    def __init__(self, status):
        self.status_code = status
        super().__init__("PRIVATE_PROVIDER_BODY sk-never-display-this")


@pytest.mark.parametrize("status, phrase", [(401,"authenticate"),(403,"authenticate"),(404,"configured model"),(429,"quota"),(503,"unavailable")])
def test_errors_are_safe_and_actionable(monkeypatch, status, phrase):
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    def fail(timeout):
        raise FakeError(status)
    with pytest.raises(clients.ProviderError) as caught:
        clients._retry(fail, "Test provider")
    assert phrase in str(caught.value)
    assert "PRIVATE" not in str(caught.value)
    assert "sk-" not in str(caught.value)


def test_retries_are_bounded_and_timeout_is_passed(monkeypatch):
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 1)
    monkeypatch.setattr(clients.time, "sleep", lambda _: None)
    attempts=[]
    def call(timeout):
        attempts.append(timeout)
        if len(attempts)==1:
            raise FakeError(503)
        return "ok"
    assert clients._retry(call,"Test") == "ok"
    assert len(attempts)==2
    assert all(0 < t <= config.PROVIDER_TIMEOUT_SECONDS for t in attempts)


def test_permanent_failure_is_not_retried(monkeypatch):
    call=MagicMock(side_effect=FakeError(401))
    with pytest.raises(clients.ProviderError): clients._retry(call,"Test")
    assert call.call_count==1


def test_expired_shared_budget_makes_no_request():
    call=MagicMock()
    token=clients._deadline.set(time.monotonic()-1)
    try:
        with pytest.raises(clients.ProviderUnavailableError,match="time limit"):
            clients._retry(call,"Test")
    finally: clients._deadline.reset(token)
    call.assert_not_called()


def test_prompt_size_rejected_before_provider(monkeypatch):
    monkeypatch.setattr(config,"MAX_PROMPT_CHARS",10)
    with pytest.raises(clients.ProviderError,match="too much context"):
        clients.call_analysis_llm("x"*11)


def test_missing_keys_are_clear():
    with pytest.raises(clients.ProviderError,match="fallback is not configured"):
        clients.call_analysis_llm("question")
    with pytest.raises(clients.ProviderError,match="MISTRAL_API_KEY"):
        clients.call_conversation_llm("question")


def test_groq_timeout_tokens_and_no_sdk_retries(monkeypatch):
    import groq
    monkeypatch.setattr(config,"GROQ_API_KEY","dummy")
    fake=MagicMock()
    fake.__enter__.return_value=fake
    fake.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))])
    factory=MagicMock(return_value=fake)
    monkeypatch.setattr(groq,"Groq",factory)
    assert clients.call_analysis_llm("question")=="answer"
    assert factory.call_args.kwargs["max_retries"]==0
    assert factory.call_args.kwargs["timeout"]<=config.PROVIDER_TIMEOUT_SECONDS
    assert fake.chat.completions.create.call_args.kwargs["max_completion_tokens"]==config.MAX_RESPONSE_TOKENS


def test_transient_groq_failure_uses_mistral(monkeypatch):
    import groq
    monkeypatch.setattr(config,"GROQ_API_KEY","dummy")
    monkeypatch.setattr(config,"MISTRAL_API_KEY","dummy")
    monkeypatch.setattr(config,"PROVIDER_MAX_RETRIES",0)
    fake=MagicMock(); fake.__enter__.return_value=fake
    fake.chat.completions.create.side_effect=FakeError(503)
    monkeypatch.setattr(groq,"Groq",MagicMock(return_value=fake))
    fallback=MagicMock(return_value="fallback")
    monkeypatch.setattr(clients,"call_fallback_llm",fallback)
    assert clients.call_analysis_llm("question")=="fallback"
    fallback.assert_called_once_with("question")


def test_bad_groq_key_does_not_silently_switch_provider(monkeypatch):
    import groq
    monkeypatch.setattr(config,"GROQ_API_KEY","dummy")
    monkeypatch.setattr(config,"MISTRAL_API_KEY","dummy")
    fake=MagicMock(); fake.__enter__.return_value=fake
    fake.chat.completions.create.side_effect=FakeError(401)
    monkeypatch.setattr(groq,"Groq",MagicMock(return_value=fake))
    fallback=MagicMock(); monkeypatch.setattr(clients,"call_fallback_llm",fallback)
    with pytest.raises(clients.ProviderError,match="authenticate"):
        clients.call_analysis_llm("question")
    fallback.assert_not_called()


def test_mistral_timeout_and_retries(monkeypatch):
    from mistralai import client as sdk
    monkeypatch.setattr(config,"MISTRAL_API_KEY","dummy")
    fake=MagicMock(); fake.__enter__.return_value=fake
    fake.chat.complete.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))])
    factory=MagicMock(return_value=fake); monkeypatch.setattr(sdk,"Mistral",factory)
    assert clients.call_conversation_llm("question")=="answer"
    assert factory.call_args.kwargs["retry_config"] is None
    assert factory.call_args.kwargs["timeout_ms"]<=config.PROVIDER_TIMEOUT_SECONDS*1000
    assert fake.chat.complete.call_args.kwargs["retries"] is None
    assert fake.chat.complete.call_args.kwargs["max_tokens"]==config.MAX_RESPONSE_TOKENS


def test_narration_and_code_use_their_configured_fallback_roles(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    monkeypatch.setattr(config, "FALLBACK_MODEL", "configured-code-model")
    monkeypatch.setattr(config, "EXPLANATION_MODEL", "configured-explainer")
    monkeypatch.setattr(clients, "_groq_completion", MagicMock(side_effect=clients.ProviderUnavailableError("quota")))
    mistral = MagicMock(return_value="answer")
    monkeypatch.setattr(clients, "_mistral_completion", mistral)
    assert clients.call_narration_llm("evidence") == "answer"
    mistral.assert_called_once_with("evidence", config.EXPLANATION_MODEL)
    mistral.reset_mock()
    assert clients.call_analysis_llm("code question") == "answer"
    mistral.assert_called_once_with("code question", config.FALLBACK_MODEL)


def test_gemini_sdk_options_and_no_sdk_retries(monkeypatch):
    from google import genai
    monkeypatch.setattr(config, "GEMINI_API_KEY", "dummy")
    fake = MagicMock(); fake.__enter__.return_value = fake
    fake.models.generate_content.return_value = SimpleNamespace(text="brief")
    factory = MagicMock(return_value=fake); monkeypatch.setattr(genai, "Client", factory)
    assert clients.call_memory_llm("exchange") == "brief"
    options = factory.call_args.kwargs
    assert options["vertexai"] is False
    assert options["http_options"].timeout <= config.PROVIDER_TIMEOUT_SECONDS * 1000
    assert options["http_options"].retry_options.attempts == 1
    request = fake.models.generate_content.call_args.kwargs
    assert request["model"] == config.MEMORY_MODEL
    assert request["config"].max_output_tokens == config.MAX_MEMORY_RESPONSE_TOKENS
    assert request["config"].tools is None
    assert request["config"].automatic_function_calling.disable is True
    assert request["config"].thinking_config.thinking_level == "MINIMAL"
    fake.__exit__.assert_called_once()


@pytest.mark.parametrize("status", [408, 429, 503])
def test_real_gemini_transient_errors_use_mistral(monkeypatch, status):
    from google import genai
    from google.genai.errors import APIError
    monkeypatch.setattr(config, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    monkeypatch.setattr(config, "PROVIDER_MAX_RETRIES", 0)
    fake = MagicMock(); fake.__enter__.return_value = fake
    fake.models.generate_content.side_effect = APIError(status, {"error": {"message": "PRIVATE BODY", "code": status}})
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))
    fallback = MagicMock(return_value="Mistral note"); monkeypatch.setattr(clients, "_mistral_completion", fallback)
    assert clients.call_memory_llm("exchange") == "Mistral note"
    fallback.assert_called_once_with("exchange", config.EXPLANATION_MODEL, max_tokens=config.MAX_MEMORY_RESPONSE_TOKENS)


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_real_gemini_configuration_errors_do_not_silently_failover(monkeypatch, status):
    from google import genai
    from google.genai.errors import APIError
    monkeypatch.setattr(config, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    fake = MagicMock(); fake.__enter__.return_value = fake
    fake.models.generate_content.side_effect = APIError(status, {"error": {"message": "PRIVATE BODY", "code": status}})
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))
    fallback = MagicMock(); monkeypatch.setattr(clients, "_mistral_completion", fallback)
    with pytest.raises(clients.ProviderError) as caught: clients.call_memory_llm("exchange")
    assert "PRIVATE" not in str(caught.value)
    fallback.assert_not_called()


def test_missing_gemini_key_uses_mistral(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    fallback = MagicMock(return_value="brief"); monkeypatch.setattr(clients, "_mistral_completion", fallback)
    assert clients.call_memory_llm("exchange") == "brief"
    fallback.assert_called_once()


def test_empty_gemini_response_uses_mistral(monkeypatch):
    from google import genai
    monkeypatch.setattr(config, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    fake = MagicMock(); fake.__enter__.return_value = fake
    fake.models.generate_content.return_value = SimpleNamespace(text="")
    monkeypatch.setattr(genai, "Client", MagicMock(return_value=fake))
    fallback = MagicMock(return_value="brief"); monkeypatch.setattr(clients, "_mistral_completion", fallback)
    assert clients.call_memory_llm("exchange") == "brief"
    fallback.assert_called_once()


def test_installed_gemini_sdk_serializes_real_request_offline(monkeypatch):
    import json
    import httpx
    from google import genai
    real_client = genai.Client
    monkeypatch.setattr(config, "GEMINI_API_KEY", "offline-placeholder")
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"candidates": [{
            "content": {"role": "model", "parts": [{"text": "Brief memory."}]},
            "finishReason": "STOP",
        }]})
    def make_client(**kwargs):
        kwargs["http_options"].httpx_client = httpx.Client(transport=httpx.MockTransport(respond))
        return real_client(**kwargs)
    monkeypatch.setattr(genai, "Client", make_client)
    assert clients.call_memory_llm("synthetic exchange") == "Brief memory."
    assert len(requests) == 1
    assert config.MEMORY_MODEL in str(requests[0].url)
    payload = json.loads(requests[0].content)
    assert payload["generationConfig"]["maxOutputTokens"] == config.MAX_MEMORY_RESPONSE_TOKENS
    assert "tools" not in payload


def test_fallback_keeps_time_after_primary_exhausts_its_slice(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(clients.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    def primary():
        clock[0] = clients._deadline.get() + 0.01
        raise clients.ProviderUnavailableError("primary timed out")
    def fallback():
        assert clients._deadline.get() > clock[0]
        return "saved"
    with clients.request_budget(seconds=10):
        assert clients._failover(primary, fallback) == "saved"
        assert clients._deadline.get() == 110
    assert clients._deadline.get() is None


@pytest.mark.parametrize("seconds", [1, 6, 9, 9.9])
def test_short_memory_budget_skips_gemini_minimum_deadline(monkeypatch, seconds):
    from google import genai
    monkeypatch.setattr(config, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    factory = MagicMock(); monkeypatch.setattr(genai, "Client", factory)
    fallback = MagicMock(return_value="brief"); monkeypatch.setattr(clients, "_mistral_completion", fallback)
    with clients.request_budget(seconds=seconds):
        assert clients.call_memory_llm("exchange") == "brief"
    factory.assert_not_called()
    fallback.assert_called_once()


def test_gemini_gets_valid_deadline_when_remaining_budget_allows(monkeypatch):
    from google import genai
    monkeypatch.setattr(config, "GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "dummy")
    fake = MagicMock(); fake.__enter__.return_value = fake
    fake.models.generate_content.return_value = SimpleNamespace(text="brief")
    factory = MagicMock(return_value=fake); monkeypatch.setattr(genai, "Client", factory)
    with clients.request_budget(seconds=15):
        assert clients.call_memory_llm("exchange") == "brief"
    assert 10000 <= factory.call_args.kwargs["http_options"].timeout < 15000
