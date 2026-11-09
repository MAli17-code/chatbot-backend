from fastapi import Request
from fastapi.responses import JSONResponse


class MessageNotFoundError(Exception):
    def __init__(self, message_id: int) -> None:
        self.message_id = message_id


async def message_not_found_handler(
    request: Request, exc: MessageNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": "message_not_found",
            "detail": f"Message with id {exc.message_id} was not found.",
        },
    )
    
    
class LLMError(Exception):
    """Safe application error. Messages here are shown to API clients."""

    status_code = 503
    error = "llm_unavailable"
    detail = "The AI service is temporarily unavailable. Please try again later."


class LLMTimeoutError(LLMError):
    error = "llm_timeout"
    detail = "The AI service took too long to respond. Please try again."


class LLMRateLimitError(LLMError):
    status_code = 429
    error = "llm_rate_limited"
    detail = "Too many requests to the AI service. Please retry shortly."


class LLMAuthError(LLMError):
    """Our API key is bad. The client can't fix it, so it only sees a generic 503."""


class LLMUnavailableError(LLMError):
    pass


async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "detail": exc.detail},
    )