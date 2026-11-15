from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.services.llm import GeminiLLMService, LLMService


@lru_cache
def get_llm_service() -> LLMService:
    # The ONE place that knows which provider class is used.
    return GeminiLLMService(get_settings())


LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]