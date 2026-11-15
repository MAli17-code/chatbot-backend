from fastapi import APIRouter

from app.api.dependencies import LLMServiceDep
from app.schemas.chat import ChatRequest, ChatResponse, Usage
from app.schemas.errors import ErrorResponse

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a prompt and get an AI answer",
    responses={
        429: {"model": ErrorResponse, "description": "Provider rate limit reached"},
        503: {"model": ErrorResponse, "description": "Provider timeout or outage"},
    },
)
async def chat(payload: ChatRequest, llm: LLMServiceDep) -> ChatResponse:
    result = await llm.generate_reply(payload.message)
    return ChatResponse(
        answer=result.answer,
        model=result.model,
        usage=Usage(input_tokens=result.input_tokens, output_tokens=result.output_tokens),
    )