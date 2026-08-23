from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "PPP Intelligence"
    database_url: str = f"sqlite:///{BASE_DIR / 'storage' / 'ppp.db'}"

    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "ppp-intelligence"

    max_retrieval_chunks: int = 8
    chunk_size: int = 1200
    chunk_overlap: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
