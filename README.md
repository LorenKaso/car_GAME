# Racing Platform — first backend milestone

Foundation for a future Unity Android/iOS game, using Python/FastAPI, SQLAlchemy,
PostgreSQL 18 and PostGIS 3.6. No racing physics, rules, world rendering or live multiplayer.

**Verification status:** implementation and local Git commits are delivered. Non-database
checks pass; real PostgreSQL/PostGIS integration and Docker startup could not run in the
build environment. This milestone is **not yet verified complete**. See
[verification report](docs/verification.md). Do not advance to the next milestone until
`test-runner` passes against real PostGIS and the manual flow below works.

## What is included

- Registration, login, logout, refresh rotation, expiry, revocation, protected current user.
- Profile with username/display name/avatar reference/country and derived level.
- Exactly one starter car per account; garage listing and owned-car selection.
- Coins=0, XP=0 and level=1 at registration; append-only opening ledger entry.
- Database-enforced balance updates through ledger inserts; no public economy write API.
- Single-use email verification/reset tokens and encrypted, retryable SMTP outbox.
- Four planned cities and empty PostGIS race-zone/track-version tables.
- Two immutable Alembic revisions, separate runtime/migration roles, isolated test DB.
- Temporary starter-car metadata is explicitly marked `placeholder/car/origin-one`.
  No 3D car model or Unity project/build is included in this milestone.

## Repository

| Directory | Purpose |
|---|---|
| unity-client/ | Reserved client workspace and screen/networking contracts |
| backend/app/ | api, schemas, services, repositories, models, core, db |
| backend/alembic/ | Sole migration history |
| backend/tests/ | Non-database and real PostGIS integration tests |
| backend/scripts/ | Guarded test migration/runner |
| database/ | Schema and database operations |
| infrastructure/ | Local Compose, role initialization, ignored-secret setup |
| docs/ | API contract, security, scope, future lobby design, verification |

## Quick start — Windows PowerShell or macOS/Linux

Prerequisites: Docker Desktop with Linux containers (or Docker Engine + Compose v2),
Git, and Python 3.12. Start Docker before the commands. Run commands from the repository
root. On Windows, replace `python` with `py -3.12` if needed.

```sh
python infrastructure/setup_local.py
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml up -d db mailpit
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml run --rm --build migrate
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml up -d --build api mail-worker
```

The setup script creates random ignored credentials and refuses to overwrite existing
configuration. Keep them private. Initial PostGIS provisioning uses the DBA account;
Alembic uses `racing_owner`; the API uses restricted `racing_app`. Do not run Alembic as
the API user. PostGIS extension setup is not granted to the API.

Open [Swagger UI](http://localhost:8000/docs), [liveness](http://localhost:8000/health/live),
[database readiness](http://localhost:8000/health/ready), and
[local email inbox](http://localhost:8025). No public email is sent: Mailpit captures it locally.
The browser-based Swagger UI is a development API tester, not the Unity application shell.

The PostGIS image is explicitly `linux/amd64`; Apple Silicon may run it via emulation.
It uses the PostgreSQL 18 data mount `/var/lib/postgresql`. Tags are bounded release
families; resolve immutable image digests in a later deployment review.

## Run all tests with the real test database

```sh
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml --profile test run --rm --build test-runner
```

This starts isolated `db-test`, verifies PostGIS, applies Alembic migrations to
`racing_test`, and runs the complete suite. Integration fixtures clear the dedicated
test database's application data between tests. They refuse any database name other
than `racing_test`. The development database `racing` is not used by tests.

The test DB uses temporary storage. Do not give the test process production credentials.
A failed database preflight means the suite has not passed; there is no SQLite substitute.

## Optional host-Python workflow

```sh
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```sh
source .venv/bin/activate
```

Then:

```sh
python -m pip install -r backend/requirements-dev.txt
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
```

Run the database first using Compose. Stop the Compose `api` if port 8000 is occupied.
In another activated terminal, run `python -m app.services.mail_worker` from `backend/`.
For host tests, start `db-test` with Compose's test profile, then run
`python scripts/run_tests.py` from `backend/`. This reads `.env.test`, migrates only the
separate test database, then runs pytest. Pure checks alone are:

```sh
python -m pytest -m "not integration" -q
python -m ruff check .
```

## Manual acceptance flow

1. In Swagger, `POST /v1/auth/register` with the example below; expect 201, profile,
   coins 0, XP 0, level 1. Duplicate email/username returns a generic 409.
2. `POST /v1/auth/login` using email/password; copy `access_token` into Swagger's
   **Authorize** bearer field. Do not paste tokens into logs, Git, or shared screenshots.
3. `GET /v1/me`, `/v1/me/profile`, `/v1/me/garage` and `/v1/me/garage/selected`.
   Garage must contain exactly one selected starter.
4. `POST /v1/me/garage/select` with the **owned-car record's** `id`, not the catalog car ID.
   Create a second user and attempt to select their owned-car ID: expect 404.
5. Open Mailpit; copy the one-use verification code into
   `POST /v1/auth/verify-email` as `token`; `GET /v1/me` now shows email verified.
6. `POST /v1/auth/refresh`; replace both client tokens. Old access becomes invalid.
   Reusing the consumed refresh token revokes that session family and requires login.
7. `POST /v1/auth/logout`; subsequent `GET /v1/me` using that token must return 401.
8. Request `/forgot-password`, read local mail, submit `/reset-password` with the code
   and a new password; old sessions/password and a second use of the code must fail.
9. `GET /v1/locations` lists four cities with `planned` status. No playable zone exists.
10. Restart the API; log in again and verify ownership/progress survived in PostgreSQL.

Registration example:

```json
{
  "email": "driver@example.com",
  "username": "driver_one",
  "display_name": "Driver One",
  "password": "a unique long test passphrase",
  "country": "US"
}
```

No endpoint allows editing coins, XP, level or granting owned cars. Passwords require
15–128 characters. City selections never request GPS. Do not use a real personal password
in development samples.

## Stop and preserve local data

```sh
docker compose --env-file infrastructure/.env -f infrastructure/compose.yaml --profile test down
```

The development volume remains. **Do not add `--volumes` unless deliberately deleting
all local accounts and economy history.** If you regenerate env passwords after the
volume exists, PostgreSQL does not automatically change stored role passwords; preserve
configuration or rotate credentials explicitly.

## Source control and next gate

See [Git LFS recommendations](docs/git-lfs.md). A local repository and logical commits
were created; no remote was added because the GitHub integration returned no accessible
repositories. The source archive includes `racing-platform.bundle` with committed history.
To restore it into a new folder:

```sh
git clone /path/to/racing-platform.bundle racing-platform
```

After making the intended GitHub repository accessible, add its exact URL as `origin`
and push the reviewed local branch. Do not infer a repository from another project.

Production deployment, real email delivery, HTTPS edge configuration, account deletion,
operational monitoring and a Unity client are subsequent work, not completed by this
local foundation. The [security review](docs/security.md) lists release gates.
