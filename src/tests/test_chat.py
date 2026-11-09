import pytest

from chatbot_backend.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from chatbot_backend.llm import LLMResult
from chatbot_backend.main import app
from chatbot_backend.routers.chat import get_generator

URL = "/api/v1/chat"


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def use_fake(fn):
    app.dependency_overrides[get_generator] = lambda: fn


def raising(exc):
    async def fake(message):
        raise exc

    return fake


def test_chat_success_with_fake_llm(client):
    async def fake(message):
        return LLMResult(f"echo: {message}", "fake-model", 12, 48)

    use_fake(fake)
    response = client.post(URL, json={"message": "  Explain DI  "})
    assert response.status_code == 200
    assert response.json() == {
        "answer": "echo: Explain DI",   # also proves trimming
        "model": "fake-model",
        "usage": {"input_tokens": 12, "output_tokens": 48},
    }


@pytest.mark.parametrize("message", ["", "   "])
def test_empty_message_rejected(client, message):
    assert client.post(URL, json={"message": message}).status_code == 422


def test_oversized_message_rejected(client):
    assert client.post(URL, json={"message": "x" * 4001}).status_code == 422


@pytest.mark.parametrize(
    "exc, status, code",
    [
        (LLMTimeoutError(), 503, "llm_timeout"),
        (LLMAuthError(), 503, "llm_unavailable"),
        (LLMRateLimitError(), 429, "llm_rate_limited"),
        (LLMUnavailableError(), 503, "llm_unavailable"),
    ],
)
def test_provider_failures_return_safe_errors(client, exc, status, code):
    use_fake(raising(exc))
    response = client.post(URL, json={"message": "hi"})
    assert response.status_code == status
    body = response.json()
    assert body["error"] == code
    assert set(body) == {"error", "detail"}   # nothing else leaks