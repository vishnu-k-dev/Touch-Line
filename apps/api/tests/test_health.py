from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "service": "touchline-ai-api", "version": "0.1.0"}


def test_api_root():
    assert client.get("/api/v1").json()["docs"] == "/docs"
