from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_is_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": "0.1.0"}


def test_health_is_read_only():
    assert client.post("/api/health").status_code == 405
