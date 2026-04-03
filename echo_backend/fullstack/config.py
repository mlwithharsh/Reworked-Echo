from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Echo Adaptive FastAPI"
    api_token: str = Field(default="dev-token", alias="ECHO_API_TOKEN")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    model_name: str = Field(default="distilgpt2", alias="ECHO_MODEL_NAME")
    active_model_version: str = Field(default="baseline-distilgpt2", alias="ECHO_MODEL_VERSION")
    adapter_root: str = Field(default="model_store/adapters", alias="ECHO_ADAPTER_ROOT")
    cache_ttl_seconds: int = Field(default=300, alias="ECHO_CACHE_TTL_SECONDS")
    rate_limit_requests: int = Field(default=30, alias="ECHO_RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="ECHO_RATE_LIMIT_WINDOW_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
