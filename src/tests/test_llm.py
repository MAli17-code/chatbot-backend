import asyncio
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.services.llm import AnthropicLLMService

REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def status_error(cls, code, message="boom"):
    return cls(message, response=httpx.Response(code, request=REQUEST), body=None)


class FakeClient:
    def __init__(self, exc=None, response=None):
        self.messages = self
        self._exc, self._response = exc, response

    async def create(self, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


def make_service(client) -> AnthropicLLMService:
    return AnthropicLLMService(Settings(_env_file=None), client=client)  # fake env from conftest


@pytest.mark.parametrize(
    "sdk_error, expected",
    [
        (anthropic.APITimeoutError(request=REQUEST), LLMTimeoutError),
        (status_error(anthropic.AuthenticationError, 401), LLMConfigurationError),
        (status_error(anthropic.RateLimitError, 429), LLMRateLimitError),
        (anthropic.APIConnectionError(request=REQUEST), LLMUnavailableError),
        (status_error(anthropic.InternalServerError, 500), LLMUnavailableError),
    ],
)
def test_sdk_errors_become_app_errors(sdk_error, expected):
    service = make_service(FakeClient(exc=sdk_error))
    with pytest.raises(expected):
        asyncio.run(service.generate_reply("hi"))


def test_provider_error_text_is_not_exposed():
    err = status_error(anthropic.AuthenticationError, 401, "invalid key sk-secret-123")
    service = make_service(FakeClient(exc=err))
    with pytest.raises(LLMConfigurationError) as info:
        asyncio.run(service.generate_reply("hi"))
    assert "sk-secret" not in str(info.value)
    assert "sk-secret" not in info.value.message


def test_response_is_mapped_to_result():
    response = SimpleNamespace(
        model="m",
        content=[SimpleNamespace(type="text", text="Hello")],
        usage=SimpleNamespace(input_tokens=3, output_tokens=5),
    )
    result = asyncio.run(make_service(FakeClient(response=response)).generate_reply("hi"))
    assert (result.answer, result.input_tokens, result.output_tokens) == ("Hello", 3, 5)