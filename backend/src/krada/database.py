from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from krada.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by persistence adapters."""


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped unit of work and roll back every unfinished transaction."""
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            # Service methods commit complete business transactions. Any exception before that
            # boundary must leave the pooled connection clean for the next tenant request.
            session.rollback()
            raise
