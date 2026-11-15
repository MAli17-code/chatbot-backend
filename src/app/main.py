from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.api.v1.routers import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()   # fail fast at startup if required config is missing
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Chatbot Backend",
        description="Chat API with an LLM-backed /chat endpoint.",
        lifespan=lifespan,
    )
    application.add_middleware(RequestIDMiddleware)
    register_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(api_router)
    return application


app = create_app()