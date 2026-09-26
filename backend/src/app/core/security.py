import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.identity import User

password_hash = PasswordHash.recommended()
COOKIE = "rag_session"
CSRF_COOKIE = "rag_csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(response, user: User, settings: Settings) -> None:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    token = jwt.encode({"sub": str(user.id), "exp": expires, "iat": datetime.now(timezone.utc)}, settings.jwt_secret, algorithm="HS256")
    csrf = secrets.token_urlsafe(32)
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=settings.access_token_minutes * 60, path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=settings.cookie_secure, samesite="strict", max_age=settings.access_token_minutes * 60, path="/")


def current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Cookie(alias=COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> User:
    unauthorized = HTTPException(status_code=401, detail="Sign in required")
    if not token or not settings.jwt_secret:
        raise unauthorized
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], options={"require": ["exp", "iat", "sub"]})
        user = db.get(User, UUID(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise unauthorized from exc
    if user is None or not user.active:
        raise unauthorized
    if request.method not in SAFE_METHODS:
        csrf_cookie = request.cookies.get(CSRF_COOKIE)
        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return user


def editor(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role not in ("ADMIN", "EDITOR"):
        raise HTTPException(status_code=403, detail="Editor access required")
    return user


def admin(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
