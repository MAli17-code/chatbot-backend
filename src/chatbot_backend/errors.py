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