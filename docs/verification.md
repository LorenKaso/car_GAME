# Verification report — 9 September 2026

**Gate status: incomplete — PostgreSQL/PostGIS runtime unavailable in this environment.**
Do not describe the milestone as verified or move on to the next milestone yet.

| Check | Result |
|---|---|
| Repository inspection | No existing checkout; only earlier architecture document |
| GitHub access | Repository listing returned no accessible repositories; no remote push |
| Python dependencies | Resolved/installed in isolated Python 3.12 environment; lockfiles generated |
| FastAPI application | Real Uvicorn HTTP smoke test: liveness 200, unauthenticated current-user 401, database readiness 503 as expected; 16-path OpenAPI generated |
| Non-database test suite | 37 passed; 20 database tests deselected for this command |
| Ruff | Passed |
| Python compile | Passed |
| Alembic offline generation | Both revisions rendered; 47 PostgreSQL statements parsed |
| PL/pgSQL function syntax | Native parser accepted trigger function source; no database execution claimed |
| Real PostGIS integration suite | Blocked at session fixture: connection refused on separate test DB port 5433 |
| Docker Compose startup/build | Not run: Docker executable/daemon unavailable |
| Compose structure / shell | YAML parsed and runtime/test separation checked; PostgreSQL initialization script passed bash syntax check |
| Secret-file exclusion | Local generated configuration confirmed ignored; archive excludes private env files |
| Native PostgreSQL setup | Unavailable; package-manager attempt failed due runtime permission restrictions |
| SMTP outbox delivery | Not integration-tested; Mailpit+PostGIS needed |
| Unity build/device run | Not in this milestone; no Unity project or gameplay implemented |

Two upstream TestClient deprecation warnings were observed (httpx compatibility and an
AnyIO alias). They did not fail the non-database suite. Do not treat a parsed migration
or an ORM model as proof of executable PostgreSQL privileges or PostGIS behavior.

## Authored integration coverage (20 collected cases)

Registration/default profile/starter/opening ledger; duplicate email/username including
case normalization; invalid password and unknown account; login/current user/logout;
garage listing, owned selection, foreign/missing/catalog IDs; profile privacy and economy
protection; session expiry; refresh rotation/replay; single-use email verification;
password reset/revocation; uniform recovery response; expired/wrong-purpose tokens;
shared rate limits; live PostGIS/metric query/city catalog; runtime role write denial;
ledger idempotency/conflict/overdraft/level projection; concurrent duplicate credit;
registration rollback when the starter catalog is unavailable.

## Required next verification

From the repository root, with Docker running:

```sh
python infrastructure/setup_local.py
```

Run setup only if the ignored configuration does not already exist. Then:

```sh
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml --profile test run --rm --build test-runner
```

Follow README's development startup and manual two-user/garage/recovery flow. Record the
actual database/extension versions, test output, and any fixes in a follow-up verification
commit before treating the milestone as complete. Real PostGIS tests must pass; using
SQLite or returning mock registration data does not satisfy this gate.
