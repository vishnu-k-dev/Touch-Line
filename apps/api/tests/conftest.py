import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.models.tables import Document
from app.services.ingest import ingest_selected
from app.services.rag import rebuild_index


@pytest.fixture(scope="session")
def db():
    """Session over the dev database, loading the sample matches first if they are missing."""
    try:
        ingest_selected(force=False)
    except OperationalError:
        pytest.skip("Postgres is not reachable: docker compose -f infra/docker-compose.yml up -d")
    with SessionLocal() as session:
        yield session


@pytest.fixture(scope="session")
def indexed(db):
    """The db session, with the document index built if it is empty."""
    if not db.scalar(select(func.count()).select_from(Document)):
        rebuild_index(db)
    return db
