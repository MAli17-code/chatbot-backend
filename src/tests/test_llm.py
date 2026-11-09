import asyncio
from types import SimpleNamespace

import httpx2
import pytest
from google.genai import errors

from chatbot_backend import llm
from chatbot_backend.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)

REQUEST = httpx2.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models")


def api_error(cls, code, status, message="boom"):
    body = {"error": {"code": code, "message": message, "status": status}}
    return cls(code, body)


class FakeClient:
    """Mimics genai.Client: client.aio.models.generate_content(...)."""

    def __init__(self, exc=None, response=None):
        self.aio = SimpleNamespace(models=self)
        self._exc, self._response = exc, response

    async def generate_content(self, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


@pytest.mark.parametrize(
    "sdk_error, expected",
    [
        (httpx2.ReadTimeout("slow", request=REQUEST), LLMTimeoutError),
        (api_error(errors.ServerError, 504, "DEADLINE_EXCEEDED"), LLMTimeoutError),
        (api_error(errors.ClientError, 403, "PERMISSION_DENIED"), LLMAuthError),
        (
            api_error(errors.ClientError, 400, "INVALID_ARGUMENT", "API key not valid."),
            LLMAuthError,
        ),
        (api_error(errors.ClientError, 429, "RESOURCE_EXHAUSTED"), LLMRateLimitError),
        (httpx2.ConnectError("down", request=REQUEST), LLMUnavailableError),
        (api_error(errors.ClientError, 404, "NOT_FOUND"), LLMUnavailableError),
        (api_error(errors.ServerError, 500, "INTERNAL"), LLMUnavailableError),
    ],
)
def test_sdk_errors_become_safe_errors(monkeypatch, sdk_error, expected):
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClient(exc=sdk_error))
    with pytest.raises(expected):
        asyncio.run(llm.generate_reply("hi"))


def test_response_is_mapped_to_result(monkeypatch):
    response = SimpleNamespace(
        text=" Hello ",
        model_version="gemini-test",
        usage_metadata=SimpleNamespace(prompt_token_count=3, candidates_token_count=5),
    )
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClient(response=response))
    result = asyncio.run(llm.generate_reply("hi"))
    assert (result.answer, result.model, result.input_tokens, result.output_tokens) == (
        "Hello",
        "gemini-test",
        3,
        5,
    )


def test_empty_reply_is_unavailable(monkeypatch):
    response = SimpleNamespace(text=None, model_version="m", usage_metadata=None)
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClient(response=response))
    with pytest.raises(LLMUnavailableError):
        asyncio.run(llm.generate_reply("hi"))

