from importlib.metadata import version

from fastapi import FastAPI

from chatbot_backend.errors import MessageNotFoundError, message_not_found_handler
from chatbot_backend.routers import messages

app = FastAPI(
    title="Chatbot Backend",
    description="Chat messages API (in-memory storage for now).",
)

app.add_exception_handler(MessageNotFoundError, message_not_found_handler)
app.include_router(messages.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": version("chatbot-backend")}