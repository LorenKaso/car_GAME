import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import new_token, password_hasher, token_hash, verify_password
from app.models.entities import AuthSession
from app.schemas.requests import RegisterRequest
from app.services.auth import issue_tokens


@pytest.mark.parametrize(
    "path", ["/v1/me", "/v1/me/profile", "/v1/me/garage", "/v1/me/garage/selected", "/v1/locations"]
)
def test_protected_reads_require_authentication(unit_client, path):
    response = unit_client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["cache-control"] == "no-store"


def test_liveness_needs_no_database(unit_client):
    assert unit_client.get("/health/live").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("coins", 100000),
        ("xp", 999),
        ("level", 99),
        ("owned_cars", []),
        ("is_admin", True),
        ("latitude", 32.0),
        ("longitude", 34.0),
    ],
)
def test_registration_rejects_server_owned_and_location_fields(unit_client, field, value):
    body = dict(
        email="one@example.com",
        username="player_one",
        display_name="Player",
        password="sensitive passphrase",
        **{field: value},
    )
    response = unit_client.post("/v1/auth/register", json=body)
    assert response.status_code == 422
    assert "sensitive passphrase" not in response.text


@pytest.mark.parametrize(
    "path", ["/v1/me/economy", "/v1/me/coins", "/v1/me/xp", "/v1/me/level", "/v1/me/garage/grant"]
)
def test_no_public_economy_or_car_grant_route(unit_client, path):
    assert unit_client.post(path, json={"amount": 100000}).status_code == 404


def test_profile_is_read_only(unit_client):
    assert unit_client.patch("/v1/me/profile", json={"coins": 999}).status_code == 405


@pytest.mark.parametrize("username", ["x", "1player", "bad-name", "<script>", "אבי", "a" * 31])
def test_bad_username(username):
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="one@example.com",
            username=username,
            display_name="Player",
            password="long enough password",
        )


def test_normalization():
    value = RegisterRequest(
        email="ONE@EXAMPLE.COM",
        username="Player_One",
        display_name="  Player  ",
        password="long enough password",
    )
    assert value.email == "one@example.com"
    assert value.username == "player_one"
    assert value.display_name == "Player"


@pytest.mark.parametrize("password", ["short", "p" * 129])
def test_password_boundaries(password):
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="one@example.com", username="player", display_name="Player", password=password
        )


def test_argon2id_and_salt():
    first = password_hasher.hash("a long test password")
    second = password_hasher.hash("a long test password")
    assert first.startswith("$argon2id$") and first != second
    assert verify_password("a long test password", first)
    assert not verify_password("incorrect", first)
    assert not verify_password("incorrect", None)


def test_random_tokens_and_hashes():
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 43 and len(token_hash(a)) == 64
    assert token_hash(a) != a


def test_token_lifetimes_are_capped():
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://racing_app:x@localhost/racing_test"
    )
    session = AuthSession(
        id=uuid4(), user_id=uuid4(), absolute_expires_at=datetime.now(UTC) + timedelta(seconds=90)
    )
    result = issue_tokens(session, settings)
    assert 0 < result.expires_in <= 90
    assert session.refresh_expires_at == session.absolute_expires_at
    assert session.access_hash == token_hash(result.access_token)
    assert session.refresh_hash == token_hash(result.refresh_token)
    assert not hasattr(result, "password_hash")


def test_oversized_body_rejected(unit_client):
    response = unit_client.post(
        "/v1/auth/login", content=b"x" * 20000, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_error_does_not_echo_password(unit_client):
    response = unit_client.post(
        "/v1/auth/login", json={"email": "not-email", "password": "my-secret"}
    )
    assert response.status_code == 422 and "my-secret" not in response.text


def test_production_rejects_insecure_config():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://racing_app:x@localhost/racing",
            app_env="production",
        )


def test_runtime_rejects_owner_role():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None, database_url="postgresql+psycopg://racing_owner:x@localhost/racing"
        )


def test_outbox_encryption_hides_tokens():
    cipher = Fernet(Fernet.generate_key())
    data = json.dumps({"token": new_token()}).encode()
    encrypted = cipher.encrypt(data)
    assert data not in encrypted and cipher.decrypt(encrypted) == data


def test_migration_sql_parses_with_postgresql_parser():
    from pathlib import Path

    from pglast import parse_sql
    from pglast.parser import parse_plpgsql_json

    sql = (Path(__file__).parents[1] / "alembic/versions/0001_foundation.sql").read_text()
    assert len(parse_sql(sql)) > 30
    # Parse the actual PL/pgSQL function bodies too; this is syntax, not database execution.
    # Use the native parser directly: pglast's Python JSON decoder fails on trigger datums.
    # Syntax errors still raise from the native parser. This does not execute any function.
    parse_plpgsql_json(sql)
