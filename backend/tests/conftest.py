import os
import secrets
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Importing the application never needs a live database. These are ephemeral test values.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://racing_app:unused@127.0.0.1:1/racing_test"
)
os.environ.setdefault("OUTBOX_KEY", Fernet.generate_key().decode())
os.environ.setdefault("RATE_LIMIT_KEY", secrets.token_hex(32))
os.environ.setdefault("APP_ENV", "test")
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def unit_client():
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://racing_app:unused@127.0.0.1:1/racing_test",
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture(scope="session")
def integration_config():
    config = {**dotenv_values(Path(__file__).parents[1] / ".env.test"), **os.environ}
    # Environment is authoritative for explicit TEST_* URLs; never reuse DATABASE_URL.
    url, migration = config.get("TEST_DATABASE_URL"), config.get("TEST_MIGRATION_DATABASE_URL")
    if not url or not migration:
        pytest.fail(
            "Set dedicated TEST_DATABASE_URL and TEST_MIGRATION_DATABASE_URL. No SQLite fallback."
        )
    for value in (url, migration):
        if make_url(value).database != "racing_test":
            pytest.fail(
                "Refusing destructive integration tests: database must be named racing_test"
            )
    if make_url(url).username != "racing_app" or make_url(migration).username != "racing_owner":
        pytest.fail("Tests require separate runtime and migration roles")
    engine = create_engine(migration, hide_parameters=True, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as db:
            db.execute(text("SELECT public.PostGIS_Version()"))
    except Exception:
        engine.dispose()
        pytest.fail(
            "PostgreSQL/PostGIS test service unavailable. Start db-test; no integration assertion has run.",
            pytrace=False,
        )
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=url,
        outbox_key=config["OUTBOX_KEY"],
        rate_limit_key=config["RATE_LIMIT_KEY"],
    )
    yield settings, engine
    engine.dispose()


@pytest.fixture
def integration_client(integration_config):
    settings, engine = integration_config
    with engine.begin() as db:
        db.execute(text("TRUNCATE game.users, game.rate_limits, game.outbox_messages CASCADE"))
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def owner_db(integration_config):
    with integration_config[1].connect() as db:
        yield db
        db.rollback()


def account_payload(suffix="one"):
    return {
        "email": f"{suffix}@example.com",
        "username": f"player_{suffix}",
        "display_name": f"Player {suffix}",
        "password": "long test passphrase 2026",
        "country": "US",
    }


@pytest.fixture
def account(integration_client):
    def create(suffix="one"):
        data = account_payload(suffix)
        response = integration_client.post("/v1/auth/register", json=data)
        assert response.status_code == 201, response.text
        tokens = integration_client.post(
            "/v1/auth/login", json={"email": data["email"], "password": data["password"]}
        )
        assert tokens.status_code == 200, tokens.text
        return (
            data,
            response.json(),
            tokens.json(),
            {"Authorization": "Bearer " + tokens.json()["access_token"]},
        )

    return create
