from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.core.config import get_settings


class ChatRequest(BaseModel):
    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(examples=["Why is separation of concerns useful?"])

    @field_validator("message")
    @classmethod
    def within_input_limit(cls, value: str) -> str:
        limit = get_settings().llm_max_input_chars   # limit comes from settings
        if len(value) > limit:
            raise ValueError(f"message must be at most {limit} characters")
        return value


class Usage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None


class ChatResponse(BaseModel):
    answer: str
    model: str
    usage: Usage