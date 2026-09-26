import os

os.environ.setdefault("JWT_SECRET", "test-only-signing-secret-32-characters-long")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
