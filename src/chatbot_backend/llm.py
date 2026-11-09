import logging
from dataclasses import dataclass
from functools import lru_cache

import httpx2
from google import genai
from google.genai import errors, types

from chatbot_backend.config import get_settings
from chatbot_backend.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResult:
    answer: str
    model: str
    input_tokens: int | None
    output_tokens: int | None


@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        # The SDK takes the timeout in milliseconds.
        http_options=types.HttpOptions(timeout=int(settings.llm_timeout_seconds * 1000)),
    )


def _is_auth_error(exc: errors.APIError) -> bool:
    # Gemini reports a bad key as 400 INVALID_ARGUMENT ("API key not valid"),
    # not only as 401/403.
    if exc.code in (401, 403):
        return True
    return exc.code == 400 and "api key" in (exc.message or "").lower()


async def generate_reply(message: str) -> LLMResult:
    settings = get_settings()
    try:
        response = await _get_client().aio.models.generate_content(
            model=settings.llm_model,
            contents=message,
            config=types.GenerateContentConfig(
                max_output_tokens=settings.llm_max_output_tokens,
            ),
        )
    # TimeoutException is a subclass of TransportError, so it must come first.
    except httpx2.TimeoutException as exc:
        logger.warning("LLM call timed out")
        raise LLMTimeoutError() from exc
    except httpx2.TransportError as exc:
        logger.warning("LLM connection error")
        raise LLMUnavailableError() from exc
    except errors.APIError as exc:
        if _is_auth_error(exc):
            logger.error("LLM authentication/permission failure (check the server API key)")
            raise LLMAuthError() from exc
        if exc.code == 429:
            logger.warning("LLM rate limited (Gemini quota exhausted)")
            raise LLMRateLimitError() from exc
        if exc.code == 504:
            logger.warning("LLM deadline exceeded")
            raise LLMTimeoutError() from exc
        logger.error("LLM returned HTTP %s %s (model=%s)", exc.code, exc.status, settings.llm_model)
        raise LLMUnavailableError() from exc

    # .text is None when Gemini returns no text (e.g. the reply was blocked).
    answer = (response.text or "").strip()
    if not answer:
        logger.error("LLM returned no text")
        raise LLMUnavailableError()

    usage = response.usage_metadata
    return LLMResult(
        answer=answer,
        model=response.model_version or settings.llm_model,
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
    )
