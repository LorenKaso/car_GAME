from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.errors import DomainError
from app.core.security import new_token, password_hasher, token_hash, utcnow, verify_password
from app.models.entities import (
    AccountToken,
    AuthSession,
    Car,
    PlayerState,
    Profile,
    UsedRefreshToken,
    User,
    UserCar,
)
from app.repositories.players import lock_user
from app.schemas.responses import TokenOutput
from app.services.economy import append_entry
from app.services.mail import queue_account_message


def register(db, data, settings):
    now = utcnow()
    user = User(
        id=uuid4(),
        email=str(data.email),
        password_hash=password_hasher.hash(data.password),
        is_active=True,
        created_at=now,
    )
    try:
        starter = db.scalar(select(Car).where(Car.is_starter.is_(True), Car.enabled.is_(True)))
        if starter is None:
            raise DomainError(503, "starter_catalog_unavailable")
        db.add(user)
        db.flush()
        db.add(
            Profile(
                id=uuid4(),
                user_id=user.id,
                username=data.username,
                display_name=data.display_name,
                country=data.country,
                created_at=now,
                updated_at=now,
            )
        )
        db.add(PlayerState(user_id=user.id, coins=0, xp=0, curve_version=1, updated_at=now))
        db.add(
            UserCar(
                id=uuid4(),
                user_id=user.id,
                car_id=starter.id,
                grant_type="starter",
                is_selected=True,
                created_at=now,
            )
        )
        db.flush()
        append_entry(
            db,
            user_id=user.id,
            kind="account_opened",
            coins_delta=0,
            xp_delta=0,
            reference_type="registration",
            reference_id=user.id,
        )
        queue_account_message(db, user, "verify", settings)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise DomainError(409, "account_identifier_unavailable") from None
        raise
    return user


def issue_tokens(session, settings):
    access, refresh = new_token(), new_token()
    now = utcnow()
    session.access_hash, session.refresh_hash = token_hash(access), token_hash(refresh)
    session.access_expires_at = min(
        now + timedelta(minutes=settings.access_minutes), session.absolute_expires_at
    )
    session.refresh_expires_at = min(
        now + timedelta(days=settings.refresh_days), session.absolute_expires_at
    )
    return TokenOutput(
        access_token=access,
        refresh_token=refresh,
        expires_in=max(0, int((session.access_expires_at - now).total_seconds())),
    )


def login(db, data, settings):
    user = db.scalar(select(User).where(User.email == str(data.email)))
    # Serialize login with password reset so a stale password cannot create a post-reset session.
    if user is not None:
        user = lock_user(db, user.id)
    if (
        not verify_password(data.password, user.password_hash if user else None)
        or not user.is_active
    ):
        raise DomainError(401, "invalid_credentials")
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(data.password)
    now = utcnow()
    session = AuthSession(
        id=uuid4(),
        user_id=user.id,
        created_at=now,
        absolute_expires_at=now + timedelta(days=settings.session_days),
    )
    tokens = issue_tokens(session, settings)
    db.add(session)
    db.commit()
    return tokens


def refresh(db, raw, settings):
    digest = token_hash(raw)
    candidate = db.scalar(select(AuthSession).where(AuthSession.refresh_hash == digest))
    used = db.get(UsedRefreshToken, digest) if candidate is None else None
    if candidate is None and used is not None:
        candidate = db.get(AuthSession, used.session_id)
    if candidate is None:
        raise DomainError(401, "invalid_session")
    user = lock_user(db, candidate.user_id)
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.id == candidate.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    now = utcnow()
    if session.refresh_hash != digest:
        # Includes a concurrent rotation that completed while waiting for the user lock.
        session.revoked_at = now
        db.commit()
        raise DomainError(401, "invalid_session")
    if (
        not user.is_active
        or session.revoked_at is not None
        or session.refresh_expires_at <= now
        or session.absolute_expires_at <= now
    ):
        raise DomainError(401, "invalid_session")
    db.add(UsedRefreshToken(token_hash=digest, session_id=session.id, used_at=now))
    tokens = issue_tokens(session, settings)
    db.commit()
    return tokens


def revoke_session(db, session):
    lock_user(db, session.user_id)
    db.execute(update(AuthSession).where(AuthSession.id == session.id).values(revoked_at=utcnow()))
    db.commit()


def request_message(db, email, purpose, settings):
    user = db.scalar(select(User).where(User.email == str(email), User.is_active.is_(True)))
    if user:
        user = lock_user(db, user.id)
        if purpose == "reset" or user.email_verified_at is None:
            # Invalidate older same-purpose tokens before enqueueing a fresh one.
            db.execute(
                update(AccountToken)
                .where(
                    AccountToken.user_id == user.id,
                    AccountToken.purpose == purpose,
                    AccountToken.used_at.is_(None),
                )
                .values(used_at=utcnow())
            )
            queue_account_message(db, user, purpose, settings)
    db.commit()


def consume_account_token(db, raw, purpose, password=None):
    candidate = db.scalar(
        select(AccountToken).where(
            AccountToken.token_hash == token_hash(raw), AccountToken.purpose == purpose
        )
    )
    if not candidate:
        raise DomainError(400, "invalid_or_expired_token")
    user = lock_user(db, candidate.user_id)
    token = db.scalar(
        select(AccountToken)
        .where(AccountToken.id == candidate.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    now = utcnow()
    if not user.is_active or token.used_at is not None or token.expires_at <= now:
        raise DomainError(400, "invalid_or_expired_token")
    token.used_at = now
    if purpose == "verify":
        user.email_verified_at = now
    else:
        user.password_hash = password_hasher.hash(password)
        db.execute(update(AuthSession).where(AuthSession.user_id == user.id).values(revoked_at=now))
        db.execute(
            update(AccountToken)
            .where(AccountToken.user_id == user.id, AccountToken.purpose == "reset")
            .values(used_at=now)
        )
    db.commit()
