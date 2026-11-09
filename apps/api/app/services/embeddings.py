"""Local embeddings (no API key, no per-call cost): BAAI/bge-small-en-v1.5 via ONNX, 384 dimensions.
The model (~67 MB) downloads once into data/models/. ponytail: one model, no provider abstraction until a second exists."""

from functools import lru_cache

from fastembed import TextEmbedding

from app.core.config import ROOT

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(MODEL_NAME, cache_dir=str(ROOT / "data" / "models"))


def embed_documents(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _model().passage_embed(texts)]


def embed_query(text: str) -> list[float]:
    return next(iter(_model().query_embed(text))).tolist()  # query_embed adds the model's retrieval prefix
