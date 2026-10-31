import hashlib
from datetime import datetime, timedelta
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, RevokedSession
from app.services.security import read_token


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    parts = authorization.split()
    payload = read_token(parts[1]) if len(parts) == 2 and parts[0].lower() == "bearer" else None
    if not payload:
        raise HTTPException(401, "登录已失效，请重新登录")
    user = db.get(User, payload["user_id"])
    revoked = db.get(RevokedSession, hashlib.sha256(parts[1].encode()).hexdigest())
    if not user or revoked or payload.get("version") != user.session_version:
        raise HTTPException(401, "登录已失效，请重新登录")
    if not user.last_active_at or datetime.utcnow() - user.last_active_at > timedelta(minutes=1):
        user.last_active_at = datetime.utcnow()
        db.commit()
    return user
