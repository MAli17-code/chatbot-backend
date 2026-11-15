import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.request_id import REQUEST_ID_HEADER

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base for errors whose message is SAFE to show to API clients."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class MessageNotFoundError(AppError):
    status_code = 404
    code = "message_not_found"

    def __init__(self, message_id: int) -> None:
        super().__init__(f"Message with id {message_id} was not found.")


class LLMUnavailableError(AppError):
    status_code = 503
    code = "llm_unavailable"
    message = "The chatbot service is temporarily unavailable."


class LLMTimeoutError(LLMUnavailableError):
    code = "llm_timeout"
    message = "The chatbot service took too long to respond. Please try again."


class LLMRateLimitError(AppError):
    status_code = 429
    code = "llm_rate_limited"
    message = "Too many requests to the chatbot service. Please retry shortly."


class LLMConfigurationError(LLMUnavailableError):
    """Bad/missing provider credentials. Clients only see the generic 503."""


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers={REQUEST_ID_HEADER: request_id} if request_id else None,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    # Internal diagnostics go to the LOG (with the request id), never to the client.
    cause = type(exc.__cause__).__name__ if exc.__cause__ else None
    logger.warning("%s request_id=%s cause=%s", exc.code, _request_id(request), cause)
    return _error_response(request, exc.status_code, exc.code, exc.message)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error request_id=%s", _request_id(request))
    return _error_response(request, 500, AppError.code, AppError.message)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)       # also catches subclasses
    app.add_exception_handler(Exception, unhandled_error_handler)