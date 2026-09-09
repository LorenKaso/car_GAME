# Phase 1 — platform first

The user's 9 September 2026 instructions supersede the earlier gameplay-first Phase 1.
This milestone builds only the database and account/garage platform. No vehicle physics,
checkpoints, race rules, world generation, simulation, live multiplayer or Unity screens.
Player-to-player car collision is intentionally excluded from the product.

## Final structure

- unity-client/: reserved Unity workspace and client boundary/screen contract.
- backend/app/: api, schemas, services, repositories, models, core, db.
- backend/alembic/: the single authoritative migration chain, with immutable SQL revisions.
- backend/tests/: pure tests and real PostgreSQL/PostGIS integration/security tests.
- database/: schema and database-operation documentation; no second migration system.
- infrastructure/: local Compose, isolated test DB, role provisioning, local setup.
- docs/: API, security, client/lobby future contracts, test report, Git LFS recommendations.

## Decisions

Use PostgreSQL 18 + PostGIS 3.6 for public geographic data. No GPS/profile coordinates.
Use sync SQLAlchemy sessions in FastAPI sync endpoints (worker pool), opaque revocable
access/rotating refresh tokens, Argon2id, encrypted mail outbox, and shared database
rate limits. PostgreSQL is sufficient for this small foundation; Redis can replace the
limiter adapter after measured need. Initialization is one transaction including one
starter car and an immutable zero-value economy opening entry. XP thresholds are
versioned database data; level is derived. Local email goes to Mailpit, never real users.
City catalog includes four cities marked planned, with no fabricated playable tracks.
No new paid services or unresolved architectural approvals are required.

## Milestone commits

1. Repository and local service configuration.
2. Database models, migrations and spatial/catalog/economy invariants.
3. Authentication and player/garage APIs.
4. Automated tests, security review and run instructions.

GitHub returns no accessible repository at inspection. Commit locally; do not assume an
unrelated repository. Deliver source and Git history for later remote attachment.
