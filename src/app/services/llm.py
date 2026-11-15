import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

import httpx
import httpx2
from google import genai
from google.genai import errors, types

from app.core.config import Settings
from app.core.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

# google-genai may use either httpx or its fork httpx2 under the hood.
_TIMEOUT_ERRORS = (httpx.TimeoutException, httpx2.TimeoutException, asyncio.TimeoutError)
_CONNECTION_ERRORS = (httpx.TransportError, httpx2.TransportError)


@dataclass(frozen=True)
class LLMResult:
    answer: str
    model: str
    input_tokens: int | None
    output_tokens: int | None


class LLMService(Protocol):
    """What the route depends on. Any provider can implement this."""

    async def generate_reply(self, message: str) -> LLMResult: ...


class GeminiLLMService:
    def __init__(self, settings: Settings, client: genai.Client | None = None) -> None:
        self._model = settings.llm_model
        self._config = types.GenerateContentConfig(
            max_output_tokens=settings.llm_max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=settings.llm_thinking_budget),
        )
        self._client = client or genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=int(settings.llm_timeout_seconds * 1000),  # SDK expects ms
                retry_options=types.HttpRetryOptions(attempts=2),
            ),
        )

    async def generate_reply(self, message: str) -> LLMResult:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=message,
                config=self._config,
            )
        # Order matters: timeouts are a subclass of TransportError.
        except _TIMEOUT_ERRORS as exc:
            raise LLMTimeoutError() from exc
        except _CONNECTION_ERRORS as exc:
            raise LLMUnavailableError() from exc
        except errors.ClientError as exc:
            if exc.code == 429:
                raise LLMRateLimitError() from exc
            if exc.code in (401, 403) or (exc.code == 400 and "API key" in str(exc)):
                logger.error("LLM auth/permission failure: check the server API key")
                raise LLMConfigurationError() from exc
            logger.error("LLM returned HTTP %s (%s)", exc.code, exc.status)
            raise LLMUnavailableError() from exc
        except errors.APIError as exc:
            logger.error("LLM returned HTTP %s (%s)", exc.code, exc.status)
            raise LLMUnavailableError() from exc

        answer = (response.text or "").strip()
        if not answer:
            logger.error("LLM returned no text")
            raise LLMUnavailableError()

        usage = response.usage_metadata
        return LLMResult(
            answer=answer,
            model=response.model_version or self._model,
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
