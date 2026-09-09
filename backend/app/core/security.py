import hashlib
import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

# 64 MiB, three passes: benchmark deployment concurrency before public exposure.
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1, type=Type.ID)
_dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def utcnow():
    return datetime.now(UTC)


def new_token():
    return secrets.token_urlsafe(32)


def token_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def verify_password(password: str, encoded: str | None):
    try:
        valid = password_hasher.verify(encoded or _dummy_hash, password)
        return valid and encoded is not None
    except (VerificationError, InvalidHashError):
        return False
