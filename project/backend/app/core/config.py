from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# project/.env — единый файл для backend, bot и docker-compose.
PROJECT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", PROJECT_DIR / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    app_tz: str = "Europe/Moscow"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/assistant"
    bot_internal_secret: str = "change-me"
    telegram_bot_token: str | None = None
    reminders_enabled: bool = True
    reminders_interval_seconds: float = 30.0
    web_origin: str = "http://localhost:5173"
    web_auth_secret: str = "dev-only-change-me"
    web_token_ttl_seconds: int = 604800
    allow_demo_auth: bool = True
    enable_vector_search: bool = False
    enable_rerank: bool = False
    embeddings_provider: str = "off"

    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_timeout: float = 60.0

    stt_provider: str = "api"
    stt_api_key: str | None = None
    stt_model: str = "whisper-1"
    stt_base_url: str = "https://api.openai.com/v1"
    stt_timeout: float = 60.0
    stt_language: str = "ru"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"


settings = Settings()
