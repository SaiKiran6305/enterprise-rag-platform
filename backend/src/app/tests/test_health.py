from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["application"] == "Enterprise Knowledge AI Assistant"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"