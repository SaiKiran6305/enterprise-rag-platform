from types import SimpleNamespace
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.services.answer import FALLBACK, validate_answer
from app.services.retrieval import search


def test_retrieval_filters_workspace_before_ranking():
    workspace = uuid4()
    class FakeDB:
        def scalar(self, stmt): return uuid4()
        def execute(self, stmt):
            sql = str(stmt.compile(dialect=postgresql.dialect()))
            assert "documents.workspace_id =" in sql
            assert "documents.status =" in sql
            return []
    class Provider:
        def embed_query(self, _): return [0.0] * 1536
    assert search(FakeDB(), workspace, "travel policy", 5, get_settings(), Provider()) == []


def test_citation_rejects_unmatched_or_missing_source():
    hit = SimpleNamespace(document=SimpleNamespace(id=uuid4(), original_filename="Policy.pdf"), chunk=SimpleNamespace(id=uuid4(), page_number=3, section_title=None, content="Approval is required."))
    assert validate_answer("Approval is required [SOURCE-1].", [hit])[1][0]["page_number"] == 3
    assert validate_answer("Approval is required [SOURCE-2].", [hit]) == (FALLBACK, [])
    assert validate_answer("Approval is required.", [hit]) == (FALLBACK, [])


def test_mutation_requires_csrf_even_with_valid_session():
    uid = uuid4()
    class FakeDB:
        def get(self, model, key): return SimpleNamespace(id=uid, active=True, role="ADMIN", workspace_id=uuid4())
        def close(self): pass
    def fake_db(): yield FakeDB()
    app.dependency_overrides[get_db] = fake_db
    try:
        token = jwt.encode({"sub": str(uid), "iat": 1, "exp": 4102444800}, get_settings().jwt_secret, algorithm="HS256")
        client = TestClient(app, cookies={"rag_session": token, "rag_csrf": "expected"})
        response = client.delete(f"/api/v1/documents/{uuid4()}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
