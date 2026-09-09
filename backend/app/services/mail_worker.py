"""Durable SMTP outbox. Local Compose captures mail in Mailpit; no real mail is sent."""

import json
import smtplib
import ssl
import time
from datetime import timedelta
from email.message import EmailMessage

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.security import utcnow
from app.db.session import Database
from app.models.entities import OutboxMessage


def deliver_one(database, settings):
    with database.sessions.begin() as db:
        row = db.scalar(
            select(OutboxMessage)
            .where(
                OutboxMessage.sent_at.is_(None),
                OutboxMessage.payload_encrypted.is_not(None),
                OutboxMessage.available_at <= utcnow(),
            )
            .order_by(OutboxMessage.available_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return False
        if row.expires_at <= utcnow() or row.attempts >= 5:
            row.payload_encrypted = None
            return True
        row.attempts += 1
        try:
            payload = json.loads(
                Fernet(settings.outbox_key.get_secret_value().encode()).decrypt(
                    row.payload_encrypted.encode()
                )
            )
            message = EmailMessage()
            message["From"], message["To"] = settings.smtp_from, payload["recipient"]
            message["Subject"] = (
                "Verify your account" if payload["purpose"] == "verify" else "Reset your password"
            )
            # Codes are consumed by POST. No token in URLs, analytics, GET handlers or logs.
            message.set_content(
                f"Your one-use {payload['purpose']} code:\n\n{payload['token']}\n\n"
                "Enter it in the application. If you did not request this, ignore this message."
            )
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
                smtp.send_message(message)
            row.sent_at = utcnow()
            row.payload_encrypted = None
        except (OSError, smtplib.SMTPException, InvalidToken, ValueError, KeyError):
            row.available_at = utcnow() + timedelta(seconds=min(3600, 30 * 2**row.attempts))
            # Do not log recipient, token, payload, or SMTP exception text.
        return True


def main():
    settings = get_settings()
    database = Database(settings)
    last_cleanup = 0
    try:
        while True:
            if time.monotonic() - last_cleanup > 60:
                with database.sessions.begin() as db:
                    db.execute(
                        text("DELETE FROM game.rate_limits WHERE window_start < :cutoff"),
                        {"cutoff": int(time.time()) - 7200},
                    )
                last_cleanup = time.monotonic()
            if not deliver_one(database, settings):
                time.sleep(1)
    finally:
        database.close()


if __name__ == "__main__":
    main()
