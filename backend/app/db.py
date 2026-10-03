from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

# Parametry URL, które rozumie libpq; resztę (np. `supa=base-pooler.x` od Supabase) psycopg odrzuca.
_PG_PARAMS = {"sslmode", "sslrootcert", "connect_timeout", "application_name", "options", "target_session_attrs"}


def _normalize_url(url: str) -> str:
    # Neon/Supabase/Vercel podają postgres:// albo postgresql:// — używamy sterownika psycopg 3.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgresql+psycopg://"):
        parts = urlsplit(url)
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if k in _PG_PARAMS])
        url = urlunsplit(parts._replace(query=query))
    return url


def database_url() -> str:
    """DATABASE_URL, a gdy go nie ustawiono — POSTGRES_URL z integracji Supabase na Vercelu."""
    s = get_settings()
    if s.postgres_url and s.database_url.startswith("sqlite"):
        return s.postgres_url
    return s.database_url


def make_engine(url: str | None = None):
    url = _normalize_url(url or database_url())
    if url.startswith("sqlite"):
        path = url.split("sqlite:///", 1)[-1]
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    # Serverless (Vercel): bez własnej puli, pooling robi Supabase/Neon. Pooler w trybie transakcji
    # (pgbouncer, port 6543) nie obsługuje prepared statements → prepare_threshold=None.
    return create_engine(url, poolclass=NullPool, pool_pre_ping=True, connect_args={"prepare_threshold": None})


engine = make_engine()


_initialized = False


def init_db() -> None:
    global _initialized
    from app import models  # noqa: F401  (rejestracja tabel)

    SQLModel.metadata.create_all(engine)
    _initialized = True


def get_session() -> Iterator[Session]:
    # Serverless może nie odpalić lifespan — tworzymy tabele przy pierwszym zapytaniu.
    if not _initialized:
        init_db()
    with Session(engine) as session:
        yield session
