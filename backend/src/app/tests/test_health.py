from fastapi.testclient import TestClient
from app.main import app


def test_health_and_docs():
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/docs").status_code == 200


def test_documents_requires_authentication():
    assert TestClient(app).get("/api/v1/documents").status_code == 401
