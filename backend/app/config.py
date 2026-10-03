import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]

APP_NAME = "Sztafeta Słów"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", BACKEND / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: str = "mock"  # groq | mock
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_moderation_model: str = ""
    llm_timeout_s: float = 20.0

    # Na Vercelu bez DATABASE_URL i POSTGRES_URL: SQLite w /tmp (dane ulotne — docelowo Supabase Postgres).
    database_url: str = (
        "sqlite:////tmp/app.db" if os.environ.get("VERCEL") else f"sqlite:///{(BACKEND / 'data' / 'app.db').as_posix()}"
    )
    postgres_url: str = ""  # ustawia integracja Supabase na Vercelu; używane, gdy DATABASE_URL to SQLite
    cors_origins: str = "http://localhost:5173"
    reset_pin: str = ""  # PIN do POST /api/admin/reset (tryb jury); puste = reset wyłączony


@lru_cache
def get_settings() -> Settings:
    return Settings()
