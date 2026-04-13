from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(ROOT_DIR / ".env"),
            str(ROOT_DIR / "helix_backend" / ".env"),
            str(ROOT_DIR / "helix-frontend" / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Helix Adaptive FastAPI"
    api_token: str = Field(default="dev-token", alias="HELIX_API_TOKEN")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    model_name: str = Field(default="distilgpt2", alias="HELIX_MODEL_NAME")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model_name: str = Field(default="llama-3.1-8b-instant", alias="HELIX_GROQ_MODEL_NAME")
    active_model_version: str = Field(default="baseline-distilgpt2", alias="HELIX_MODEL_VERSION")
    adapter_root: str = Field(default="model_store/adapters", alias="HELIX_ADAPTER_ROOT")
    marketing_db_path: str = Field(default="memory/helix_marketing.db", alias="HELIX_MARKETING_DB_PATH")
    smart_parks_db_path: str = Field(default="memory/helix_smart_parks.db", alias="HELIX_SMART_PARKS_DB_PATH")
    cache_ttl_seconds: int = Field(default=300, alias="HELIX_CACHE_TTL_SECONDS")
    use_local_llm: bool = Field(default=True, alias="HELIX_USE_LOCAL_LLM")
    rate_limit_requests: int = Field(default=100, alias="HELIX_RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="HELIX_RATE_LIMIT_WINDOW_SECONDS")
    marketing_webhook_url: str | None = Field(default=None, alias="HELIX_MARKETING_WEBHOOK_URL")
    telegram_bot_token: str | None = Field(default=None, alias="HELIX_TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(default=None, alias="HELIX_TELEGRAM_CHAT_ID")
    x_access_token: str | None = Field(default=None, alias="HELIX_X_ACCESS_TOKEN")
    linkedin_access_token: str | None = Field(default=None, alias="HELIX_LINKEDIN_ACCESS_TOKEN")
    linkedin_author_urn: str | None = Field(default=None, alias="HELIX_LINKEDIN_AUTHOR_URN")
    discord_webhook_url: str | None = Field(default=None, alias="HELIX_DISCORD_WEBHOOK_URL")
    discord_bot_token: str | None = Field(default=None, alias="HELIX_DISCORD_BOT_TOKEN")
    discord_channel_id: str | None = Field(default=None, alias="HELIX_DISCORD_CHANNEL_ID")
    reddit_client_id: str | None = Field(default=None, alias="HELIX_REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = Field(default=None, alias="HELIX_REDDIT_CLIENT_SECRET")
    reddit_username: str | None = Field(default=None, alias="HELIX_REDDIT_USERNAME")
    reddit_password: str | None = Field(default=None, alias="HELIX_REDDIT_PASSWORD")
    reddit_user_agent: str = Field(default="helix-local-marketing/1.0", alias="HELIX_REDDIT_USER_AGENT")
    reddit_default_subreddit: str | None = Field(default=None, alias="HELIX_REDDIT_SUBREDDIT")
    credential_secret: str | None = Field(default=None, alias="HELIX_CREDENTIAL_SECRET")
    marketing_max_retries: int = Field(default=3, alias="HELIX_MARKETING_MAX_RETRIES")
    root_dir: str = str(ROOT_DIR)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
