from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # hide_input_in_errors: a startup error must never print (part of) the API key.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    gemini_api_key: SecretStr      # no default -> required
    # Free-tier Gemini model. Override with LLM_MODEL in .env
    # (e.g. gemini-3.5-flash-lite for higher free-tier limits).
    llm_model: str = "gemini-3.5-flash"
    llm_timeout_seconds: float = 30.0
    llm_max_output_tokens: int = 512


@lru_cache
def get_settings() -> Settings:
    return Settings()