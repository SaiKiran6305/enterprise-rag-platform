import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import CSRF_COOKIE, COOKIE, admin, current_user, hash_token, issue_session, password_hash
from app.models.identity import Invitation, User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Login(BaseModel):
    email: EmailStr
    password: str


class InvitationRequest(BaseModel):
    email: EmailStr
    role: Literal["ADMIN", "EDITOR", "VIEWER"] = "VIEWER"


class AcceptInvitation(BaseModel):
    token: str
    password: str = Field(min_length=12, max_length=128)


def profile(user: User) -> dict:
    return {"id": str(user.id), "email": user.email, "role": user.role, "workspace_id": str(user.workspace_id)}


@router.post("/login")
def login(payload: Login, response: Response, db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.active or not password_hash.verify(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    issue_session(response, user, settings)
    return profile(user)


@router.get("/me")
def me(user: Annotated[User, Depends(current_user)]):
    return profile(user)


@router.post("/logout")
def logout(response: Response, _user: Annotated[User, Depends(current_user)]):
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@router.post("/invitations")
def invite(payload: InvitationRequest, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(admin)]):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "User already exists")
    token = secrets.token_urlsafe(32)
    invitation = Invitation(workspace_id=user.workspace_id, email=payload.email.lower(), role=payload.role, token_hash=hash_token(token), expires_at=datetime.now(timezone.utc) + timedelta(hours=48))
    db.add(invitation)
    db.commit()
    # The token is shown once to the admin; no email service is assumed.
    return {"token": token, "expires_at": invitation.expires_at.isoformat(), "email": invitation.email}


@router.post("/accept")
def accept(payload: AcceptInvitation, db: Annotated[Session, Depends(get_db)]):
    invitation = db.scalar(select(Invitation).where(Invitation.token_hash == hash_token(payload.token)).with_for_update())
    if invitation is None or invitation.used_at or invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Invitation is invalid or expired")
    if db.scalar(select(User).where(User.email == invitation.email)):
        raise HTTPException(409, "User already exists")
    user = User(workspace_id=invitation.workspace_id, email=invitation.email, role=invitation.role, password_hash=password_hash.hash(payload.password))
    invitation.used_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    return {"created": True}


@router.get("/users")
def users(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(admin)]):
    return [profile(u) for u in db.scalars(select(User).where(User.workspace_id == user.workspace_id).order_by(User.email))]
