import getpass
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import password_hash
from app.models.identity import User, Workspace


def main():
    if sys.argv[1:] != ["create-admin"]:
        raise SystemExit("Usage: python -m app.cli create-admin")
    email = input("Admin email: ").strip().lower()
    workspace_name = input("Workspace name: ").strip()
    password = getpass.getpass("Password (12+ characters): ")
    if not email or not workspace_name or len(password) < 12:
        raise SystemExit("Email, workspace and a 12+ character password are required")
    with SessionLocal.begin() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("User already exists")
        workspace = Workspace(name=workspace_name)
        db.add(workspace)
        db.flush()
        db.add(User(workspace_id=workspace.id, email=email, role="ADMIN", password_hash=password_hash.hash(password)))
    print("Admin created")


if __name__ == "__main__":
    main()
