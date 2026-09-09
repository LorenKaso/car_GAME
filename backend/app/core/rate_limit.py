import hashlib
import hmac
import time

from sqlalchemy import text

from app.core.errors import DomainError


class RateLimiter:
    """Shared, atomic PostgreSQL fixed windows; no process-local security state."""

    def __init__(self, database, key):
        self.database = database
        self.key = key.encode()

    def hit(self, scope, identity, limit, seconds=60):
        digest = hmac.new(self.key, f"{scope}:{identity}".encode(), hashlib.sha256).hexdigest()
        window = int(time.time()) // seconds * seconds
        with self.database.sessions.begin() as db:
            hits = db.execute(
                text("""INSERT INTO game.rate_limits(key_hash,window_start,hits)
             VALUES (:key,:window,1) ON CONFLICT(key_hash,window_start)
             DO UPDATE SET hits=game.rate_limits.hits+1 RETURNING hits"""),
                {"key": digest, "window": window},
            ).scalar_one()
        if hits > limit:
            raise DomainError(429, "rate_limit_exceeded")
