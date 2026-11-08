from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Role = Literal["user", "assistant"]

Content = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


class MessageCreate(BaseModel):
    role: Role
    content: Content = Field(examples=["What is FastAPI?"])


class MessageUpdate(BaseModel):
    content: Content = Field(examples=["Explain FastAPI in detail"])


class MessageResponse(BaseModel):
    id: int
    role: Role
    content: str
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: str
