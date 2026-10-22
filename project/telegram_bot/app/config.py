from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", PROJECT_DIR / "telegram_bot" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    backend_url: str = "http://localhost:8000/api/v1"
    bot_internal_secret: str = "change-me"
    bot_mock_mode: bool = False
    app_tz: str = "Europe/Moscow"
    request_timeout: float = Field(default=20.0, gt=0)
    log_level: str = "INFO"

    @property
    def api_base_url(self) -> str:
        return self.backend_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
