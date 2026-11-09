"""Make a database ready to serve: wait for it, migrate, load the sample matches and build the search index, each
only if missing. Safe to run on every container start.

    cd apps/api && python -m app.services.bootstrap"""

import logging
import time

from sqlalchemy import func, select, text

from app.core.db import SessionLocal, engine, init_db
from app.models.tables import Document, Match
from app.services.ingest import ingest_selected
from app.services.rag import rebuild_index

logger = logging.getLogger("touchline.bootstrap")


def wait_for_db(seconds: int = 60) -> None:
    deadline = time.time() + seconds
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("select 1"))
            return
        except Exception as e:
            if time.time() > deadline:
                raise RuntimeError(f"database not reachable after {seconds}s: {type(e).__name__}") from e
            time.sleep(2)


def bootstrap(wait_seconds: int = 60) -> dict:
    wait_for_db(wait_seconds)
    init_db()
    with SessionLocal() as db:
        had_matches = bool(db.scalar(select(func.count()).select_from(Match)))
    if not had_matches:
        logger.info("loading sample matches (downloads StatsBomb files on first run)")
        ingest_selected(force=False)
    with SessionLocal() as db:
        had_docs = bool(db.scalar(select(func.count()).select_from(Document)))
        if not had_docs:
            logger.info("building the search index (downloads the embedding model on first run)")
            rebuild_index(db)
        return {
            "matches": db.scalar(select(func.count()).select_from(Match)),
            "documents": db.scalar(select(func.count()).select_from(Document)),
            "loaded_data": not had_matches,
            "built_index": not had_docs,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(bootstrap())
