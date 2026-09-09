# API endpoints — milestone 1

`docs/openapi.json` is the generated contract. All JSON request models reject extra
properties. Tokens and password hashes never appear in profile/garage output. Protected
routes use `Authorization: Bearer <access_token>`. No cookies or browser session storage
are required. HTTPS is mandatory beyond the local loopback development environment.

| Method | Path | Access | Result |
|---|---|---|---|
| GET | /health/live | Public | Process liveness |
| GET | /health/ready | Public | Migration, PostGIS and starter readiness; generic 503 on failure |
| POST | /v1/auth/register | Public, limited | 201 account/profile; no automatic authenticated session |
| POST | /v1/auth/login | Public, limited | Access and refresh tokens |
| POST | /v1/auth/refresh | Refresh token, limited | Rotates both tokens; invalidates old access |
| POST | /v1/auth/logout | Access token | 204; revoke current session |
| POST | /v1/auth/forgot-password | Public, limited | Uniform 202; enqueue if eligible |
| POST | /v1/auth/reset-password | One-use reset token, limited | 204; revoke all sessions |
| POST | /v1/auth/resend-verification | Public, limited | Uniform 202; enqueue if eligible |
| POST | /v1/auth/verify-email | One-use verification token, limited | 204 |
| GET | /v1/me | Access token | Current user and authoritative profile |
| GET | /v1/me/profile | Access token | Profile, coins, XP, derived level |
| GET | /v1/me/garage | Access token | Owned-car records with catalog statistics |
| GET | /v1/me/garage/selected | Access token | Selected owned car |
| POST | /v1/me/garage/select | Access token | Select owned enabled car; 404 for foreign/missing/catalog ID |
| GET | /v1/locations | Access token | Four planned cities, no player location |

Login: `{"email":"driver@example.com","password":"a unique long test passphrase"}`.
Refresh: `{"refresh_token":"<opaque token>"}`.
Verify: `{"token":"<one-use mail code>"}`.
Reset: `{"token":"<one-use mail code>","password":"a new unique long passphrase"}`.
Select: `{"user_car_id":"<owned-car record UUID>"}`.

Status conventions: 400 invalid/expired account challenge; 401 unauthenticated/invalid
session; 404 missing/foreign owned car; 409 unavailable identifier or internal idempotency
conflict; 422 input validation; 429 rate limit; 503 DB/catalog unavailable. Error responses
include a stable error code. Validation errors include field paths/types, not submitted
values. Authentication responses are non-cacheable. No privilege-granting admin route,
economy write route, profile update route, lobby route or gameplay route exists.

Car speed is provisional km/h metadata; acceleration/handling/braking/boost are provisional
0–100 catalog ratings, not measured vehicle physics. The starter's asset reference is a
placeholder, not a downloadable car. Profile country is optional, user-declared two-letter
uppercase metadata, not verified residency or GPS.

Email codes are delivered by the SMTP worker, not returned by API. A Unity verification/
reset screen will consume them later; Swagger supports development testing now. External
email templates, delivery monitoring and platform deep links are release work.
