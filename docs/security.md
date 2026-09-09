# Security review — first milestone

Reviewed source on 9 September 2026. This is a scoped engineering review, not an external
penetration test or a production-ready certification. Real DB authorization/concurrency
checks remain blocked in the current execution environment.

| Area | Implemented control | Verification / remaining gate |
|---|---|---|
| Password storage | Argon2id, 64 MiB/3 iterations/one lane, per-hash salt; password bounds | Unit test passed; benchmark deployment concurrency |
| Authentication | Random 256-bit opaque credentials, hashed at rest; generic failed login | Positive login/persistence needs PostGIS integration |
| Sessions | Access 10m, refresh idle 7d, absolute 30d; expiry, rotation, consumed-token detection, revoke | Integration tests authored; logout/reset deny stored sessions |
| Authorization | Actor from access token; user-scoped garage queries; no arbitrary profile read | Unauthenticated unit tests passed; two-user tests await DB |
| Ownership | One starter and one selection via partial unique indexes; user lock for swaps | Real DB concurrent/foreign-ID checks required |
| Economy | Server-only ledger service; unique references; AFTER INSERT balance trigger; runtime denies direct balance/history updates | SQL syntax parsed; privilege/idempotency/concurrency tests await DB |
| Validation | Extra fields forbidden, bounded identifiers/passwords, max actual body 16 KiB, redacted errors | Unit tests passed; edge timeouts/flood limits before public hosting |
| Geographic privacy | No player GPS/address columns or endpoints; only planned public city data | Schema/source review; no mobile permission code |
| Database roles | DBA enables PostGIS; owner migrates; API role has limited DML and no catalog/DDL writes | Provisioning and grant behavior await actual PostGIS |
| Secrets | Random ignored local env files; encrypted outbox; no committed private values | Git candidate file scan; encrypted outbox delivery awaits SMTP+DB |
| Rate limits | Atomic PostgreSQL per-IP and hashed-identifier windows; DB outage fails closed | Database integration required; move adapter to Redis if measured load warrants |
| Email recovery | One-use hashed purpose-bound tokens; 24h verify/30m reset; reset revokes all sessions; outbox encrypted | Real mail transport code present; provider/UX not deployed |
| Admin operations | No public admin or role-grant API | Add separate MFA/restricted admin surface only when needed |

## Security semantics and remaining work

- Registration reports generic 409 for duplicate identifiers, which still reveals that
  some identifier is unavailable. Login and recovery avoid distinguishing missing emails
  in their response body. Email queuing paths may have timing differences; rate limits
  mitigate abuse but do not prove resistance to statistical enumeration.
- Refresh requests are serialized by the client. Reusing a consumed token revokes that
  session even if reuse came from a lost network response. The safe recovery is login.
  Retain consumed hashes until their session can no longer be refreshed.
- Already-authorized requests in flight may complete around logout. Future long-lived
  lobby/game sessions require their own revocation propagation; none exist today.
- No authentication internals are part of profile output. Tokens are intentionally part
  of login/refresh protocol. A mobile client must store refresh credentials securely;
  this milestone has not implemented a Unity secure-storage adapter.
- A compromised API workload can use its ledger INSERT privilege to create audited
  changes. There is no client path to this operation. Before real rewards, separate
  settlement identity/permissions and verify provenance; audit alone is not anti-cheat.
- The runtime role can insert ownership rows because registration needs it; arbitrary
  car grants are not exposed. Before purchases add an audited grant ledger and purchase
  idempotency, not a direct public ownership INSERT endpoint.
- The mail worker and API share a limited role in local development. Separate mail
  secrets/worker DB rights before public hosting. Successful registration means durable
  enqueue, not delivered email. SMTP retry may duplicate mail after a crash; token use
  remains single-use. Configure monitoring for retry exhaustion before external users.
- No raw reset tokens appear in links or GET requests; minimal mails contain one-use
  codes for a future app form. External email-provider configuration, TLS, deep links,
  password-reset notifications and product UX remain launch work.
- Local HTTP binds to loopback. Production config requires an HTTPS application URL,
  verified DB TLS and SMTP STARTTLS, but does not itself provision a HTTPS reverse proxy.
  Add a trusted edge with TLS, request timeouts, connection caps, and restricted forwarded
  headers. Access logging is disabled locally to avoid accidental sensitive URL logging.
- No CORS wildcard or cookie auth is enabled. A future web/admin cookie surface requires
  its own CSRF, origin and cookie controls.
- Add retention/backup/restore/deletion processes, security event telemetry with redaction,
  account abuse controls and dependency vulnerability scanning before external release.
  Lint/syntax tests are not a dependency vulnerability audit.

Guidance used: [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[FastAPI security tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[SQLAlchemy transaction guidance](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html),
[PostGIS setup](https://postgis.net/documentation/getting_started/).
