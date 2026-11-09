from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from chatbot_backend.config import get_settings
from chatbot_backend.errors import (
    LLMError,
    MessageNotFoundError,
    llm_error_handler,
    message_not_found_handler,
)
from chatbot_backend.routers import chat, messages


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()  # fail fast at startup if the API key is missing
    yield


app = FastAPI(
    title="Chatbot Backend",
    description="Chat API with an LLM-backed /chat endpoint.",
    lifespan=lifespan,
)

app.add_exception_handler(MessageNotFoundError, message_not_found_handler)
app.add_exception_handler(LLMError, llm_error_handler)
app.include_router(messages.router)
app.include_router(chat.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": version("chatbot-backend")}
