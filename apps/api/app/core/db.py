from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import API_DIR, settings

engine = create_engine(settings.database_url, pool_pre_ping=True)  # lazy: no connection until first use
SessionLocal = sessionmaker(engine, expire_on_commit=False)

BASELINE_REVISION = "0001"


def init_db() -> None:
    """Bring the database to the latest schema: enable pgvector, then run Alembic migrations (apps/api/migrations).

    Databases created by the pre-migration `create_all` already contain the baseline tables but no
    alembic_version table; they are stamped at the baseline instead of re-creating tables."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    cfg = Config()
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    tables = inspect(engine)
    if tables.has_table("matches") and not tables.has_table("alembic_version"):
        command.stamp(cfg, BASELINE_REVISION)
    command.upgrade(cfg, "head")


def get_db():
    with SessionLocal() as session:
        yield session
