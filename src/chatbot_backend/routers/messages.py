from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from chatbot_backend.schemas import (
    ErrorResponse,
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    Role,
)
from chatbot_backend.store import store

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Message not found"}}


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a message",
    description="Creates a message with a generated ID and timestamp.",
)
def create_message(payload: MessageCreate):
    return store.create(payload.role, payload.content)


@router.get(
    "",
    response_model=list[MessageResponse],
    summary="List messages",
    description="Returns messages in creation order, with pagination and optional role filter.",
)
def list_messages(
    limit: Annotated[
        int, Query(ge=1, le=100, description="Max messages to return (1-100)")
    ] = 20,
    offset: Annotated[int, Query(ge=0, description="Messages to skip")] = 0,
    role: Annotated[Role | None, Query(description="Filter by role")] = None,
):
    return store.list_messages(limit, offset, role)


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
    responses=NOT_FOUND,
    summary="Get one message",
)
def get_message(message_id: int):
    return store.get(message_id)


@router.patch(
    "/{message_id}",
    response_model=MessageResponse,
    responses=NOT_FOUND,
    summary="Update message content",
)
def update_message(message_id: int, payload: MessageUpdate):
    return store.update(message_id, payload.content)


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=NOT_FOUND,
    summary="Delete a message",
)
def delete_message(message_id: int):
    store.delete(message_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)