"""Run migrations and the full suite against the dedicated PostGIS database only."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env.test")
runtime = os.environ.get("TEST_DATABASE_URL")
migration = os.environ.get("TEST_MIGRATION_DATABASE_URL")
if not runtime or not migration:
    raise SystemExit("Dedicated TEST_DATABASE_URL and TEST_MIGRATION_DATABASE_URL are required.")
for url in (runtime, migration):
    if make_url(url).database != "racing_test":
        raise SystemExit("Refusing to touch a database not named racing_test.")
engine = create_engine(migration, hide_parameters=True, connect_args={"connect_timeout": 3})
try:
    with engine.connect() as db:
        version = db.execute(text("SELECT public.PostGIS_Version()")).scalar_one()
        print("PostGIS available:", version)
except Exception:
    raise SystemExit(
        "Test database unavailable. Start db-test before running integration tests."
    ) from None
finally:
    engine.dispose()
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = runtime
os.environ["MIGRATION_DATABASE_URL"] = migration
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, check=True)
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=root))
