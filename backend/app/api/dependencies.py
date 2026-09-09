from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.errors import DomainError
from app.core.security import token_hash, utcnow
from app.models.entities import AuthSession, User

bearer = HTTPBearer(auto_error=False)


def get_db(request: Request):
    with request.app.state.database.sessions() as db:
        yield db


DB = Annotated[object, Depends(get_db)]


@dataclass
class Identity:
    user: User
    session: AuthSession


def current_identity(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    if credentials is None or len(credentials.credentials) > 128:
        raise DomainError(401, "authentication_required")
    now = utcnow()
    row = db.execute(
        select(User, AuthSession)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(
            AuthSession.access_hash == token_hash(credentials.credentials),
            AuthSession.revoked_at.is_(None),
            AuthSession.access_expires_at > now,
            AuthSession.absolute_expires_at > now,
            User.is_active.is_(True),
        )
    ).first()
    if not row:
        raise DomainError(401, "invalid_session")
    return Identity(user=row[0], session=row[1])


Actor = Annotated[Identity, Depends(current_identity)]


def limit(request, scope, identity=None, count=6, seconds=60):
    limiter = request.app.state.limiter
    ip = request.client.host if request.client else "unknown"
    limiter.hit(scope + ":ip", ip, 30, seconds)
    if identity is not None:
        limiter.hit(scope + ":account", identity, count, seconds)
