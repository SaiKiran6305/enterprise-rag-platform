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

    database_url: str

    upload_directory: Path = BACKEND_DIR / "storage" / "uploads"
    max_upload_size_bytes: int = 20 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()