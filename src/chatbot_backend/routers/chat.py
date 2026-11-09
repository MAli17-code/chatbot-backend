from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from chatbot_backend.llm import LLMResult, generate_reply
from chatbot_backend.schemas import ChatRequest, ChatResponse, ErrorResponse, Usage

router = APIRouter(prefix="/api/v1", tags=["chat"])

LLMGenerator = Callable[[str], Awaitable[LLMResult]]


def get_generator() -> LLMGenerator:
    return generate_reply


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a prompt and get an AI answer",
    responses={
        429: {"model": ErrorResponse, "description": "AI provider rate limit reached"},
        503: {"model": ErrorResponse, "description": "AI provider timeout or outage"},
    },
)
async def chat(
    payload: ChatRequest,
    generate: Annotated[LLMGenerator, Depends(get_generator)],
) -> ChatResponse:
    result = await generate(payload.message)
    return ChatResponse(
        answer=result.answer,
        model=result.model,
        usage=Usage(input_tokens=result.input_tokens, output_tokens=result.output_tokens),
    )