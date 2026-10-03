from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine():
    cfg = get_settings()
    return create_engine(
        cfg.database_url,
        pool_pre_ping=True,
        pool_size=cfg.db_pool_size,
        max_overflow=cfg.db_max_overflow,
        isolation_level="READ COMMITTED",
        connect_args={
            "connect_timeout": 3,
            "options": "-c statement_timeout=10000 -c lock_timeout=5000",
        },
    )


def session_factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db():
    with session_factory()() as db:
        yield db
