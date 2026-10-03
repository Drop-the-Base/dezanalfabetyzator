from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def _normalize_url(url: str) -> str:
    # Neon/Vercel podają postgres:// albo postgresql:// — używamy sterownika psycopg 3.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def make_engine(url: str | None = None):
    url = _normalize_url(url or get_settings().database_url)
    if url.startswith("sqlite"):
        path = url.split("sqlite:///", 1)[-1]
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    # Serverless (Vercel): bez własnej puli, pooling robi Neon.
    return create_engine(url, poolclass=NullPool, pool_pre_ping=True)


engine = make_engine()


def init_db() -> None:
    from app import models  # noqa: F401  (rejestracja tabel)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
