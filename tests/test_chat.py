import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_llm_service
from app.core.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.main import app
from app.services.llm import LLMResult

URL = "/api/v1/chat"


class FakeLLMService:
    async def generate_reply(self, message: str) -> LLMResult:
        return LLMResult(f"echo: {message}", "fake-model", 12, 48)


class FailingLLMService:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def generate_reply(self, message: str) -> LLMResult:
        raise self._error


def use(service) -> None:
    app.dependency_overrides[get_llm_service] = lambda: service


def test_chat_success_with_fake_service(client):
    use(FakeLLMService())
    response = client.post(URL, json={"message": "  Explain DI  "})
    assert response.status_code == 200
    assert response.json() == {
        "answer": "echo: Explain DI",
        "model": "fake-model",
        "usage": {"input_tokens": 12, "output_tokens": 48},
    }
    assert response.headers["X-Request-ID"]


@pytest.mark.parametrize("message", ["", "   "])
def test_empty_message_rejected(client, message):
    use(FakeLLMService())
    assert client.post(URL, json={"message": message}).status_code == 422


def test_oversized_message_rejected(client):
    use(FakeLLMService())
    assert client.post(URL, json={"message": "x" * 4001}).status_code == 422


@pytest.mark.parametrize(
    "error, status, code",
    [
        (LLMTimeoutError(), 503, "llm_timeout"),
        (LLMRateLimitError(), 429, "llm_rate_limited"),
        (LLMConfigurationError(), 503, "llm_unavailable"),   # auth detail hidden
        (LLMUnavailableError(), 503, "llm_unavailable"),
    ],
)
def test_provider_failures_map_to_safe_errors(client, error, status, code):
    use(FailingLLMService(error))
    response = client.post(URL, json={"message": "hi"}, headers={"X-Request-ID": "req-1"})
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == code
    assert body["error"]["request_id"] == "req-1"
    assert response.headers["X-Request-ID"] == "req-1"


def test_unexpected_exception_is_a_safe_500():
    use(FailingLLMService(RuntimeError("sk-secret-123 leaked internals")))
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.post(URL, json={"message": "hi"})
    assert response.status_code == 500
    assert "sk-secret" not in response.text
    assert response.headers["X-Request-ID"]
    assert response.json()["error"]["code"] == "internal_error"