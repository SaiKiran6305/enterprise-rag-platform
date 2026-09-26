from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Enterprise Knowledge AI Assistant"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+psycopg://rag_user:change-me@localhost:5432/enterprise_rag"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4.1-mini"
    jwt_secret: str = ""
    cookie_secure: bool = False
    access_token_minutes: int = 60
    frontend_origin: str = "http://localhost:5173"
    retrieval_threshold: float = 0.30
    max_context_chunks: int = 8

    upload_directory: Path = BACKEND_DIR / "storage" / "uploads"
    max_upload_size_bytes: int = 20 * 1024 * 1024
    max_documents_per_workspace: int = 500

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
