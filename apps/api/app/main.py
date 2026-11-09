import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from app.api.routes import router
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.tables import Document, Match

logging.basicConfig(level=logging.INFO, format="%(message)s")  # request and agent events are logged as JSON lines
logger = logging.getLogger("touchline.api")

app = FastAPI(
    title="Touchline AI API",
    description="Evidence-backed football intelligence",
    version="0.1.0",
)


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    """Give every request an id (echoed in X-Request-ID), log one line per request, and turn crashes into a clean 500."""
    rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex[:12]
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(json.dumps({"event": "unhandled", "id": rid, "path": request.url.path}))
        response = JSONResponse({"detail": "Internal server error", "request_id": rid}, status_code=500)
    response.headers["X-Request-ID"] = rid
    logger.info(json.dumps({"event": "request", "id": rid, "method": request.method, "path": request.url.path,
                            "status": response.status_code, "ms": int((time.perf_counter() - t0) * 1000)}))
    return response


# added after the tracing middleware so CORS is outermost and also decorates error responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Request-ID", "X-Visitor-Id"],
    expose_headers=["X-Request-ID", "Retry-After"],
)
app.include_router(router)


@app.get("/health")
async def health():
    """Liveness: the process is up."""
    return {"status": "healthy", "service": "touchline-ai-api", "version": "0.1.0"}


@app.get("/health/ready")
def ready():
    """Readiness: the database answers and holds the data and search index the app needs."""
    problems, matches, documents = [], 0, 0
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
            matches = db.scalar(select(func.count()).select_from(Match))
            documents = db.scalar(select(func.count()).select_from(Document))
    except Exception as e:  # any DB failure means not ready
        problems.append(f"database: {type(e).__name__}")
    else:
        if not matches:
            problems.append("no matches loaded: run `python -m app.services.ingest`")
        if not documents:
            problems.append("search index is empty: run `python -m app.services.rag`")
    body = {"status": "ready" if not problems else "not_ready", "matches": matches, "documents": documents, "problems": problems}
    return JSONResponse(body, status_code=200 if not problems else 503)


@app.get("/api/v1")
async def api_root():
    return {
        "message": "Touchline AI API",
        "docs": "/docs",
    }
