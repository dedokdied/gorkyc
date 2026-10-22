
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    app_tz: str = "Europe/Moscow"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/assistant"
    enable_vector_search: bool = False
    enable_rerank: bool = False
    embeddings_provider: str = "off"

    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None


settings = Settings()
