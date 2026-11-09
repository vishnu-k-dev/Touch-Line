from sqlalchemy import func, select

from app.models.tables import Document, Event
from app.services.bootstrap import bootstrap


def test_bootstrap_is_idempotent_and_does_not_reload_existing_data(db):
    events_before = db.scalar(select(func.count()).select_from(Event))
    docs_before = db.scalar(select(func.count()).select_from(Document))
    first = bootstrap(wait_seconds=5)
    second = bootstrap(wait_seconds=5)
    assert first == second == {"matches": 5, "documents": docs_before, "loaded_data": False, "built_index": False}
    assert db.scalar(select(func.count()).select_from(Event)) == events_before  # nothing was re-ingested
