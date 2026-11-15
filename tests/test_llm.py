import asyncio
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from app.core.config import Settings
from app.core.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.services.llm import GeminiLLMService

REQUEST = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models")


def api_error(cls, code, message="boom", status="ERROR"):
    return cls(code, {"error": {"code": code, "message": message, "status": status}})


class FakeClient:
    """Mimics genai.Client: client.aio.models.generate_content(...)."""

    def __init__(self, exc=None, response=None):
        self.aio = SimpleNamespace(models=self)
        self._exc, self._response = exc, response

    async def generate_content(self, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


def make_service(client) -> GeminiLLMService:
    return GeminiLLMService(Settings(_env_file=None), client=client)  # fake env from conftest


@pytest.mark.parametrize(
    "sdk_error, expected",
    [
        (httpx.ReadTimeout("slow", request=REQUEST), LLMTimeoutError),
        (api_error(errors.ClientError, 403, status="PERMISSION_DENIED"), LLMConfigurationError),
        (api_error(errors.ClientError, 400, "API key not valid."), LLMConfigurationError),
        (api_error(errors.ClientError, 429, status="RESOURCE_EXHAUSTED"), LLMRateLimitError),
        (httpx.ConnectError("down", request=REQUEST), LLMUnavailableError),
        (api_error(errors.ClientError, 404, status="NOT_FOUND"), LLMUnavailableError),
        (api_error(errors.ServerError, 500), LLMUnavailableError),
        (api_error(errors.ServerError, 503, status="UNAVAILABLE"), LLMUnavailableError),
    ],
)
def test_sdk_errors_become_app_errors(sdk_error, expected):
    service = make_service(FakeClient(exc=sdk_error))
    with pytest.raises(expected):
        asyncio.run(service.generate_reply("hi"))


def test_provider_error_text_is_not_exposed():
    err = api_error(errors.ClientError, 403, "invalid key AIza-secret-123")
    service = make_service(FakeClient(exc=err))
    with pytest.raises(LLMConfigurationError) as info:
        asyncio.run(service.generate_reply("hi"))
    assert "AIza-secret" not in str(info.value)
    assert "AIza-secret" not in info.value.message


def test_response_is_mapped_to_result():
    response = SimpleNamespace(
        text=" Hello ",
        model_version="gemini-test",
        usage_metadata=SimpleNamespace(prompt_token_count=3, candidates_token_count=5),
    )
    result = asyncio.run(make_service(FakeClient(response=response)).generate_reply("hi"))
    assert (result.answer, result.model, result.input_tokens, result.output_tokens) == (
        "Hello",
        "gemini-test",
        3,
        5,
    )


def test_empty_answer_is_unavailable():
    response = SimpleNamespace(text=None, model_version="m", usage_metadata=None)
    with pytest.raises(LLMUnavailableError):
        asyncio.run(make_service(FakeClient(response=response)).generate_reply("hi"))
