"""Generate ignored local-only credentials without printing them or replacing existing files."""
from pathlib import Path
import base64
import secrets

root = Path(__file__).resolve().parents[1]
paths = [root / 'infrastructure/.env', root / 'backend/.env', root / 'backend/.env.test']
if any(p.exists() for p in paths):
    raise SystemExit('Configuration already exists. Preserve its database passwords; edit explicitly.')
app, owner, admin = (secrets.token_hex(24) for _ in range(3))
key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
rate_key = secrets.token_hex(32)
paths[0].write_text(f'POSTGRES_PASSWORD={admin}\nAPP_DB_PASSWORD={app}\nOWNER_DB_PASSWORD={owner}\n')
paths[1].write_text(
    f'APP_ENV=development\nDATABASE_URL=postgresql+psycopg://racing_app:{app}@localhost:5432/racing\n'
    f'MIGRATION_DATABASE_URL=postgresql+psycopg://racing_owner:{owner}@localhost:5432/racing\n'
    f'OUTBOX_KEY={key}\nRATE_LIMIT_KEY={rate_key}\nPUBLIC_APP_URL=http://localhost:8000\n'
    'SMTP_HOST=localhost\nSMTP_PORT=1025\nSMTP_STARTTLS=false\nSMTP_FROM=no-reply@example.test\n')
paths[2].write_text(
    f'APP_ENV=test\nTEST_DATABASE_URL=postgresql+psycopg://racing_app:{app}@localhost:5433/racing_test\n'
    f'TEST_MIGRATION_DATABASE_URL=postgresql+psycopg://racing_owner:{owner}@localhost:5433/racing_test\n'
    f'OUTBOX_KEY={key}\nRATE_LIMIT_KEY={rate_key}\n')
for p in paths:
    p.chmod(0o600)
print('Created infrastructure/.env, backend/.env and backend/.env.test. Keep them out of Git.')
