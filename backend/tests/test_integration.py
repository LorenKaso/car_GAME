import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from conftest import account_payload
from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.errors import DomainError
from app.core.security import utcnow
from app.services.economy import append_entry

pytestmark = pytest.mark.integration


def test_registration_profile_starter_and_ledger(integration_client, owner_db):
    response = integration_client.post("/v1/auth/register", json=account_payload())
    assert response.status_code == 201
    user = response.json()
    assert (user["profile"]["coins"], user["profile"]["xp"], user["profile"]["level"]) == (0, 0, 1)
    assert user["email_verified"] is False
    assert (
        owner_db.execute(
            text("SELECT count(*) FROM game.user_cars WHERE user_id=:id"), {"id": UUID(user["id"])}
        ).scalar()
        == 1
    )
    assert (
        owner_db.execute(
            text(
                "SELECT count(*) FROM game.economy_transactions WHERE user_id=:id AND kind='account_opened'"
            ),
            {"id": UUID(user["id"])},
        ).scalar()
        == 1
    )
    stored = owner_db.execute(
        text("SELECT password_hash FROM game.users WHERE id=:id"), {"id": UUID(user["id"])}
    ).scalar()
    assert stored.startswith("$argon2id$")
    assert "password_hash" not in response.text and "token_hash" not in response.text


@pytest.mark.parametrize("field", ["email", "username"])
def test_duplicate_identifiers_case_insensitive(integration_client, owner_db, field):
    data = account_payload()
    assert integration_client.post("/v1/auth/register", json=data).status_code == 201
    second = account_payload("two")
    second[field] = data[field].upper()
    assert integration_client.post("/v1/auth/register", json=second).status_code == 409
    assert owner_db.execute(text("SELECT count(*) FROM game.users")).scalar() == 1
    assert owner_db.execute(text("SELECT count(*) FROM game.user_cars")).scalar() == 1


@pytest.mark.parametrize(
    "email,password", [("one@example.com", "incorrect"), ("missing@example.com", "incorrect")]
)
def test_bad_credentials(integration_client, account, email, password):
    account()
    response = integration_client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 401 and response.json()["error"] == "invalid_credentials"


def test_login_me_logout_revokes_refresh(integration_client, account):
    _, user, tokens, headers = account()
    assert integration_client.get("/v1/me", headers=headers).json()["id"] == user["id"]
    assert integration_client.post("/v1/auth/logout", headers=headers).status_code == 204
    assert integration_client.get("/v1/me", headers=headers).status_code == 401
    assert (
        integration_client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )


def test_garage_selection_and_foreign_ownership(integration_client, account):
    _, _, _, headers = account()
    _, _, _, other = account("two")
    own = integration_client.get("/v1/me/garage", headers=headers).json()
    foreign = integration_client.get("/v1/me/garage", headers=other).json()[0]
    assert len(own) == 1 and own[0]["is_selected"]
    assert (
        integration_client.post(
            "/v1/me/garage/select", headers=headers, json={"user_car_id": own[0]["id"]}
        ).status_code
        == 200
    )
    for invalid in (foreign["id"], str(uuid4()), own[0]["car"]["id"]):
        assert (
            integration_client.post(
                "/v1/me/garage/select", headers=headers, json={"user_car_id": invalid}
            ).status_code
            == 404
        )
    assert (
        integration_client.get("/v1/me/garage/selected", headers=headers).json()["id"]
        == own[0]["id"]
    )


def test_profile_privacy_and_economy_protection(integration_client, account):
    _, _, _, headers = account()
    profile = integration_client.get("/v1/me/profile", headers=headers).json()
    assert not {"latitude", "longitude", "password_hash", "email", "home_address"}.intersection(
        profile
    )
    for key in ("coins", "xp", "level", "user_cars"):
        assert (
            integration_client.patch(
                "/v1/me/profile", headers=headers, json={key: 9999}
            ).status_code
            == 405
        )
    assert integration_client.get("/v1/me/profile", headers=headers).json()["coins"] == 0


def test_access_expiration(integration_client, account, owner_db):
    _, user, tokens, headers = account()
    owner_db.execute(
        text("UPDATE game.sessions SET access_expires_at=:past WHERE user_id=:id"),
        {"past": utcnow() - timedelta(seconds=1), "id": UUID(user["id"])},
    )
    owner_db.commit()
    assert integration_client.get("/v1/me", headers=headers).status_code == 401
    assert (
        integration_client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 200
    )


def test_refresh_rotation_replay_revokes_family(integration_client, account):
    _, _, first, headers = account()
    response = integration_client.post(
        "/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert integration_client.get("/v1/me", headers=headers).status_code == 401
    assert (
        integration_client.post(
            "/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        integration_client.get(
            "/v1/me", headers={"Authorization": "Bearer " + second["access_token"]}
        ).status_code
        == 401
    )


def outbox_token(owner_db, settings, purpose):
    rows = owner_db.execute(
        text("SELECT payload_encrypted FROM game.outbox_messages ORDER BY available_at DESC")
    ).scalars()
    cipher = Fernet(settings.outbox_key.get_secret_value().encode())
    for row in rows:
        payload = json.loads(cipher.decrypt(row.encode()))
        if payload["purpose"] == purpose:
            return payload["token"]
    raise AssertionError("Missing mail")


def test_email_verification_one_use(integration_client, account, owner_db, integration_config):
    _, _, _, headers = account()
    token = outbox_token(owner_db, integration_config[0], "verify")
    assert (
        integration_client.post("/v1/auth/verify-email", json={"token": token}).status_code == 204
    )
    assert integration_client.get("/v1/me", headers=headers).json()["email_verified"] is True
    assert (
        integration_client.post("/v1/auth/verify-email", json={"token": token}).status_code == 400
    )


def test_reset_revokes_all_sessions_and_token(
    integration_client, account, owner_db, integration_config
):
    data, _, tokens, headers = account()
    assert (
        integration_client.post(
            "/v1/auth/forgot-password", json={"email": data["email"]}
        ).status_code
        == 202
    )
    token = outbox_token(owner_db, integration_config[0], "reset")
    new_password = "replacement long passphrase"
    assert (
        integration_client.post(
            "/v1/auth/reset-password", json={"token": token, "password": new_password}
        ).status_code
        == 204
    )
    assert integration_client.get("/v1/me", headers=headers).status_code == 401
    assert (
        integration_client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        integration_client.post(
            "/v1/auth/login", json={"email": data["email"], "password": data["password"]}
        ).status_code
        == 401
    )
    assert (
        integration_client.post(
            "/v1/auth/login", json={"email": data["email"], "password": new_password}
        ).status_code
        == 200
    )
    assert (
        integration_client.post(
            "/v1/auth/reset-password", json={"token": token, "password": new_password}
        ).status_code
        == 400
    )


def test_unknown_reset_uniform_response(integration_client, account):
    data, _, _, _ = account()
    one = integration_client.post("/v1/auth/forgot-password", json={"email": data["email"]})
    two = integration_client.post("/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert one.status_code == two.status_code == 202 and one.json() == two.json()


def test_expired_and_wrong_purpose_tokens(
    integration_client, account, owner_db, integration_config
):
    account()
    token = outbox_token(owner_db, integration_config[0], "verify")
    assert (
        integration_client.post(
            "/v1/auth/reset-password", json={"token": token, "password": "replacement passphrase"}
        ).status_code
        == 400
    )
    owner_db.execute(
        text("UPDATE game.account_tokens SET expires_at=:past"),
        {"past": utcnow() - timedelta(seconds=1)},
    )
    owner_db.commit()
    assert (
        integration_client.post("/v1/auth/verify-email", json={"token": token}).status_code == 400
    )


def test_shared_rate_limit(integration_client, account):
    data, _, _, _ = account()
    statuses = [
        integration_client.post(
            "/v1/auth/login", json={"email": data["email"], "password": "wrong"}
        ).status_code
        for _ in range(7)
    ]
    assert statuses[-1] == 429


def test_postgis_and_planned_locations(integration_client, account, owner_db):
    _, _, _, headers = account()
    assert integration_client.get("/health/ready").status_code == 200
    locations = integration_client.get("/v1/locations", headers=headers).json()
    assert {v["slug"] for v in locations} == {"miami", "las-vegas", "washington-dc", "new-york"}
    assert all(v["status"] == "planned" for v in locations)
    assert owner_db.execute(text("SELECT count(*) FROM game.race_zones")).scalar() == 0
    # Real metric-distance geospatial query, independent of player location.
    distance = owner_db.execute(
        text(
            "SELECT public.ST_Distance(center, public.ST_GeogFromText('SRID=4326;POINT(-80.19 25.76)')) FROM game.locations WHERE slug='miami'"
        )
    ).scalar()
    assert distance == 0


def test_runtime_role_cannot_overwrite_balances_or_ledger(integration_client, account):
    _, user, _, _ = account()
    statements = [
        "UPDATE game.player_state SET coins=100000 WHERE user_id=:id",
        "UPDATE game.economy_transactions SET coins_delta=100000 WHERE user_id=:id",
        "DELETE FROM game.economy_transactions WHERE user_id=:id",
        "UPDATE game.cars SET base_top_speed_kph=999",
        "CREATE TABLE game.unauthorized(id integer)",
    ]
    for stmt in statements:
        with pytest.raises(DBAPIError):
            with integration_client.app.state.database.sessions.begin() as db:
                db.execute(text(stmt), {"id": UUID(user["id"])})


def test_internal_ledger_idempotency_and_level(integration_client, account):
    _, user, _, headers = account()
    params = dict(
        user_id=UUID(user["id"]),
        kind="test_credit",
        coins_delta=500,
        xp_delta=1000,
        reference_type="test",
        reference_id=uuid4(),
    )
    for _ in range(2):
        with integration_client.app.state.database.sessions.begin() as db:
            append_entry(db, **params)
    profile = integration_client.get("/v1/me/profile", headers=headers).json()
    assert (profile["coins"], profile["xp"], profile["level"]) == (500, 1000, 2)
    with pytest.raises(DomainError):
        with integration_client.app.state.database.sessions.begin() as db:
            append_entry(db, **{**params, "coins_delta": 999})
    with pytest.raises(DBAPIError):
        with integration_client.app.state.database.sessions.begin() as db:
            append_entry(db, **{**params, "coins_delta": -9999, "reference_id": uuid4()})
    assert integration_client.get("/v1/me/profile", headers=headers).json()["coins"] == 500


def test_concurrent_ledger_duplicate_is_applied_once(integration_client, account):
    _, user, _, headers = account()
    params = dict(
        user_id=UUID(user["id"]),
        kind="concurrent",
        coins_delta=50,
        xp_delta=0,
        reference_type="test",
        reference_id=uuid4(),
    )

    def apply(_):
        with integration_client.app.state.database.sessions.begin() as db:
            append_entry(db, **params)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(apply, range(2)))
    assert integration_client.get("/v1/me/profile", headers=headers).json()["coins"] == 50


def test_registration_rolls_back_if_starter_missing(integration_client, owner_db):
    owner_db.execute(text("UPDATE game.cars SET enabled=false WHERE is_starter"))
    owner_db.commit()
    try:
        assert (
            integration_client.post("/v1/auth/register", json=account_payload()).status_code == 503
        )
        assert owner_db.execute(text("SELECT count(*) FROM game.users")).scalar() == 0
    finally:
        owner_db.execute(text("UPDATE game.cars SET enabled=true WHERE is_starter"))
        owner_db.commit()
