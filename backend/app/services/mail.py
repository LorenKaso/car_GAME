import json
from datetime import timedelta
from uuid import uuid4

from cryptography.fernet import Fernet

from app.core.security import new_token, token_hash, utcnow
from app.models.entities import AccountToken, OutboxMessage


def queue_account_message(db, user, purpose, settings):
    token = new_token()
    expires = utcnow() + (timedelta(hours=24) if purpose == "verify" else timedelta(minutes=30))
    db.add(
        AccountToken(
            id=uuid4(),
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash(token),
            expires_at=expires,
        )
    )
    payload = json.dumps({"recipient": user.email, "purpose": purpose, "token": token})
    ciphertext = (
        Fernet(settings.outbox_key.get_secret_value().encode()).encrypt(payload.encode()).decode()
    )
    db.add(
        OutboxMessage(
            id=uuid4(),
            payload_encrypted=ciphertext,
            attempts=0,
            available_at=utcnow(),
            expires_at=expires,
        )
    )
