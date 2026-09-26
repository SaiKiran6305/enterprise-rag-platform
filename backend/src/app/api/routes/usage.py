from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import admin
from app.models.identity import User
from app.models.usage import UsageEvent

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("")
def usage(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(admin)]):
    since = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = (select(UsageEvent.model, UsageEvent.operation, func.sum(UsageEvent.input_tokens), func.sum(UsageEvent.output_tokens))
            .where(UsageEvent.workspace_id == user.workspace_id, UsageEvent.created_at >= since)
            .group_by(UsageEvent.model, UsageEvent.operation))
    return {"period_days": 30, "models": [{"model": model, "operation": operation, "input_tokens": int(input_tokens), "output_tokens": int(output_tokens)} for model, operation, input_tokens, output_tokens in db.execute(stmt)]}
