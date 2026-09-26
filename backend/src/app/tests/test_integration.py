"""Runs in CI against pgvector/PostgreSQL and Redis; skipped without test services."""
import os
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import password_hash
from app.main import app
from app.models.identity import User, Workspace

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires PostgreSQL and Redis services")


def test_workspace_document_isolation_and_roles(monkeypatch):
    from app.api.routes import documents as routes
    monkeypatch.setattr(routes, "enqueue_document", lambda _id: None)
    email_a, email_b = f"a-{uuid4()}@example.test", f"b-{uuid4()}@example.test"
    with SessionLocal.begin() as db:
        a, b = Workspace(name="A"), Workspace(name="B")
        db.add_all([a, b]); db.flush()
        db.add_all([User(workspace_id=a.id, email=email_a, password_hash=password_hash.hash("strong-test-password"), role="EDITOR"), User(workspace_id=b.id, email=email_b, password_hash=password_hash.hash("strong-test-password"), role="VIEWER")])
    owner, other = TestClient(app), TestClient(app)
    assert owner.post("/api/v1/auth/login", json={"email": email_a, "password": "strong-test-password"}).status_code == 200
    assert other.post("/api/v1/auth/login", json={"email": email_b, "password": "strong-test-password"}).status_code == 200
    csrf = owner.cookies.get("rag_csrf")
    response = owner.post("/api/v1/documents/upload", files={"file": ("policy.pdf", BytesIO(b"%PDF-1.4\nfixture"), "application/pdf")}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 201, response.text
    doc_id = response.json()["id"]
    assert response.json()["stored_filename"] != "policy.pdf"
    assert other.get("/api/v1/documents").json() == []
    assert other.get(f"/api/v1/documents/{doc_id}").status_code == 404
    assert other.delete(f"/api/v1/documents/{doc_id}", headers={"X-CSRF-Token": other.cookies.get("rag_csrf")}).status_code == 403
    assert owner.delete(f"/api/v1/documents/{doc_id}", headers={"X-CSRF-Token": csrf}).status_code == 204
