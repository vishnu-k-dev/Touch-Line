"""Index the corpus into pgvector and search it.

    cd apps/api && python -m app.services.rag                  # rebuild the index
    cd apps/api && python -m app.services.rag "your question"  # search it
"""

import sys
from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, init_db
from app.models.tables import Document
from app.services.corpus import build_corpus
from app.services.embeddings import embed_documents, embed_query


def rebuild_index(db: Session) -> Counter:
    """Regenerate every document and its embedding. ponytail: full rebuild (seconds at this size); make it incremental past ~10k docs."""
    docs = build_corpus(db)
    vectors = embed_documents([f"{d['title']}\n{d['content']}" for d in docs])
    db.execute(delete(Document))
    db.add_all(Document(**d, embedding=v) for d, v in zip(docs, vectors))
    db.commit()
    return Counter(d["kind"] for d in docs)


FILTER_KEYS = ("team", "player", "outcome", "shot_type", "body_part", "play_pattern")  # sequence-document metadata


def search(
    db: Session, query: str, k: int = 5, kind: str | None = None, match_id: int | None = None,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    """Top-k documents by cosine similarity, optionally narrowed by exact metadata filters.

    Dense retrieval matches meaning well but exact attributes (corner, header, penalty) poorly, so attribute
    constraints go through `filters` (SQL on the document metadata), not through the query text.
    ponytail: exact scan, add an HNSW index when the corpus outgrows a few thousand rows."""
    dist = Document.embedding.cosine_distance(embed_query(query))
    q = select(Document, dist.label("distance")).order_by(dist).limit(k)
    if kind:
        q = q.where(Document.kind == kind)
    if match_id is not None:
        q = q.where(Document.match_id == match_id)
    for key, value in (filters or {}).items():
        if key not in FILTER_KEYS:
            raise ValueError(f"unknown filter {key!r}; allowed: {FILTER_KEYS}")
        field = Document.meta[key].astext
        q = q.where(field.ilike(f"%{value}%") if key == "player" else field == value)  # names: substring, rest: exact
    return [
        {
            "id": d.id, "kind": d.kind, "title": d.title, "content": d.content, "match_id": d.match_id,
            "meta": d.meta, "score": round(1 - float(distance), 4),
        }
        for d, distance in db.execute(q)
    ]


if __name__ == "__main__":
    init_db()
    with SessionLocal() as session:
        if len(sys.argv) > 1:
            for hit in search(session, " ".join(sys.argv[1:])):
                print(f"{hit['score']:.3f} [{hit['kind']}] {hit['title']}")
        else:
            print(dict(rebuild_index(session)))
