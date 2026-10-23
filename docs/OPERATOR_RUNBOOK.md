# PHANTOM PHOENIX — Operator Runbook

This runbook defines operational procedures for deploying, maintaining, monitoring, and troubleshooting **PHANTOM PHOENIX** in a local containerized or staging environment.

---

## 1. Environment Configuration & Secrets

Copy `.env` (from `.env.example`) and configure required variables:
- `POSTGRES_USER`: Database username (default: `phantom`)
- `POSTGRES_PASSWORD`: Database password (default: `phantom`)
- `POSTGRES_DB`: Database name (default: `phantom_phoenix`)
- `DATABASE_URL`: SQLAlchemy async connection string (`postgresql+asyncpg://...`)
- `MODEL_ID`: Hugging Face model identifier

**Authentication (Milestone 12 — required):**
- `AUTH_SECRET`: HS256 signing secret, minimum 32 chars. Generate with
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`. The backend
  FAILS CLOSED (login → 503) when this is missing or insecurely short.
  Rotate by replacing the value — every existing session is invalidated
  immediately (old signature no longer validates).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: session TTL (default 30).
- `COOKIE_SECURE`: MUST be `true` whenever the API is served over HTTPS.
- Rate limits: `RATE_LIMIT_LOGIN_PER_MINUTE` (5), `RATE_LIMIT_SCAN_PER_MINUTE`
  (10), `RATE_LIMIT_DEFAULT_PER_MINUTE` (120).

**Security Note:** Never commit `.env` containing production secrets to version control.

---

## 2. Docker Compose Startup & Shutdown

### Starting Services
```bash
docker compose build
docker compose up -d
```
This builds and starts `postgres`, `backend`, and `frontend` in an isolated Docker bridge network.

### Verifying Service Status
```bash
docker compose ps
```

### Stopping Services (Preserving Persistent Volumes)
```bash
docker compose down
```
*Warning:* Do not run `docker compose down -v` as this deletes the persistent PostgreSQL data volume (`postgres_data`).

---

## 3. Database Initialization & Alembic Migrations
Database migrations (`alembic upgrade head`) execute automatically upon backend container startup.
The Milestone 12 migration (`b1f84cad2d90_add_users_table_and_scan_ownership`) creates the
`users` table and the nullable `scans.owner_user_id` column. The Milestone 14 migration
(`c3a91ffd8e42_add_audit_events_table`) creates the `audit_events` table. **Existing scan records,
reports, and artifacts are preserved untouched**; scans created before the migration
remain with `owner_user_id IS NULL` (legacy — see access policy below).

To run migrations manually against a running container:
```bash
docker compose exec backend python -m alembic upgrade head
```
Rollback one revision: `docker compose exec backend python -m alembic downgrade -1`
(drops the newest table first; do not run casually).

---

## 3a. Administrator Bootstrap (one-time, interactive)

No default admin password exists. Create the first account interactively:
```bash
docker compose exec backend python -m backend.bootstrap_admin
```
The command prompts (hidden input) for username and password (min 12 chars,
hashed with Argon2id, never echoed or logged). Password reset for an existing
account: replace the row's `password_hash` via the same CLI flow on a second
admin, or re-run bootstrap after deleting the row deliberately.

Account disablement: set `users.is_enabled=false` (active sessions still pass
token validation until expiry ≤ 30 min — stateless JWT limitation).
Password rotation: see above; invalidates nothing else.

---

## 4. Health, Liveness, and Readiness Semantics (explicit)

**Protected endpoint inventory (Milestone 12):**

| Route | Access | Notes |
|---|---|---|
| `POST /api/auth/login` | public | rate-limited 5/min/IP; generic failure messages; Origin-allowlisted when sent |
| `POST /api/auth/logout` | public | clears session cookie; **CSRF guard active for cookie requests** |
| `GET /api/auth/me` | authenticated | identity from validated token |
| `POST /api/scans` | authenticated | rate-limited 10/min/process; sets owner; **CSRF guard active for cookie requests** |
| `GET /api/scans` | authenticated | ordinary users: own scans; admin: all |
| `GET /api/scans/{id}` | owner or admin | 404 otherwise (no existence disclosure); admin cross-user access audited |
| `GET /api/scans/{id}/report.pdf` | owner or admin | same policy + audit |
| `GET /api/artifacts/{scan_id}/{file}` | owner or admin | path-traversal-safe; admin access audited |
| `GET /api/metrics` | admin only | monitoring boundary documented below; denials audited |
| `GET /api/admin/audit` | admin only | read-only security audit trail inspection |
| `GET /api/liveness` | public | process check only |
| `GET /api/readiness` | public | DB reachable + detector config |
| `GET /api/health` | public | operational summary (model id, GPU name) |

**Legacy (NULL-owner) scan policy:** readable only by administrators, for
report and artifact downloads too. Ordinary users receive the uniform 404.
Legacy records are never reassigned automatically.

**Monitoring boundary:** `/api/metrics` requires an admin session/bearer
token. For a Prometheus server, either run an internal scraper with an admin
token or front the endpoint with an authenticated reverse proxy. Do NOT
route `/api/metrics` through the public frontend.

**Rate limiting deployment scope:** the limiter is IN-MEMORY per process.
`WORKERS=1` today, so counters are global for the deployment. Anything other
than a single process (multiple workers, replicas, load balancer) makes each
process count independently — a shared backend (e.g. Redis) is required
BEFORE distributed enforcement can be claimed. **Client-IP identity:** the
limiter keys on the actual socket peer address ONLY — it does NOT read
`X-Forwarded-For`, `X-Real-IP`, or any client-supplied header, so header
spoofing cannot bypass or poison limits. The cost of that hardening: behind
a reverse proxy all external clients share ONE aggregate bucket (per proxy
IP). This is the explicit tradeoff; reconfigure only after verifying the
proxy overwrites (not appends) forwarded headers. Counters reset on process
restart (in-memory) — a restart opens a fresh login-attempt window; the
window is ≤ 60 s, so the exposure is bounded.

| Endpoint | Meaning | Response |
|---|---|---|
| `GET /api/liveness` | API process is running. No dependency checks. Always 200 while the process answers. | 200 `{"status": "alive"}` |
| `GET /api/readiness` | Service can safely accept a scan workload: database reachable AND detector configured (model config valid, no load error). | 200 ready / **503 not_ready** |
| `GET /api/health` (alias `/health`) | Human/tooling-facing summary: detector load state, model ID, CUDA availability, DB reachability. Returns `ok` or `degraded`. | 200 with details either way |
| `POST /api/scans` | Triggers detector on demand. | 201 / 413 / 415 / 500 |

**Detector semantics:** the model loads **lazily** on the first inference
request (`detector_loaded=false` at startup is truthful, not a fault).
Readiness deliberately does **NOT** force model loading — probes stay fast and
no weight download occurs per health request. `detector_configured=true` means
"configured and able to accept a scan request"; `detector_loaded=true` means
weights are resident after a first scan. No GPU claims are made: the container
builds use CPU-only PyTorch wheels.

## 5. Prometheus Metrics (validated against real exposition)

Exposed at `GET /api/metrics`, content type `text/plain; version=0.0.4`.
Validated live: names/types correct, buckets cumulative, labels bounded, no
scan IDs / filenames / hashes in any label.

| Metric | Type | Labels (bounded) |
|---|---|---|
| `http_requests_total` | counter | `method`, `route` (path template), `status_class` (2xx/4xx/5xx) |
| `http_request_duration_seconds` | histogram | `method`, `route` |
| `database_connectivity_up` | gauge | none (refreshed per readiness check) |
| `scan_outcomes_total` | counter | `outcome` (LIKELY_AI / LIKELY_REAL / INCONCLUSIVE / ANALYSIS_FAILED) |
| `detector_inference_total` | counter | `status` (success/failure) |
| `detector_inference_duration_seconds` | histogram | none |

**Process-local semantics:** all metrics are cumulative within a single API
process. With multiple replicas, each exposes its own values; aggregation is
the Prometheus server's job (`sum by (...)`), NOT the application's. There is
no shared cross-process metric store. Alert rules in
`docs/prometheus/alert_rules.yml` are written for multi-replica aggregation.
**Alerting is NOT live**: no Prometheus or Alertmanager server is configured
in this repository, so rule delivery is unverified — the rule file is
version-controlled definition only.

## 6. Structured Logging and Request-ID Troubleshooting

Example sanitized access-log line (stdout, one JSON object per request):

```json
{"timestamp": "2026-10-17T19:19:35.437238+00:00", "severity": "INFO", "request_id": "c6176995-fec6-4e98-adb8-90653117e6fd", "method": "GET", "route": "/api/readiness", "status_code": 200, "status_class": "2xx", "duration_ms": 230.61}
```

- Client-supplied `X-Request-ID` values are validated (`[A-Za-z0-9_-]{1,64}`);
  anything else is replaced with a server UUID and never echoed back.
- Never logged: request bodies, image bytes, credentials, authorization
  headers, query strings, filenames, hashes, stack traces, filesystem paths.
- Exceptions appear once, as `exception_category` (class name only).
- **Troubleshooting:** grep container logs for a request ID:
  ```bash
  docker compose logs backend | grep "REQUEST_ID_FROM_RESPONSE_HEADER"
  ```

---

## 7. Smoke Testing (scan & report)
1. Open the frontend at `http://localhost:5173`.
2. Investigator Dashboard (`/#dashboard`) shows health.
3. Upload a valid JPEG/PNG/WEBP at `/#upload`; verify verdict view.
4. Download PDF at `/api/scans/{id}/report.pdf`; verify artifact images load.

---

## 8. Database Backup & Recovery (executed & verified M14)

**DB backup** (logical, compressed, custom format):
```bash
umask 077
docker compose exec postgres pg_dump -U "$POSTGRES_USER" -Fc phantom_phoenix \
  > backups/db/phoenix_$(date -u +%Y%m%dT%H%MZ).dump
chmod 600 backups/db/phoenix_*.dump
sha256sum backups/db/phoenix_*.dump > backups/db/phoenix_*.dump.sha256
```
- Write TO THE HOST (`> redirects on the host side of `docker compose exec`),
  into a directory OUTSIDE the server's public/document roots, with mode 0600.
- Integrity check (must return the table list, exit 0):
  ```bash
  docker run --rm -v "$PWD/backups/db:/bk:ro,z" postgres:17-alpine \
    pg_restore --list /bk/phoenix_<TS>.dump
  ```
- Retention: keep ≥ 1 dump per week + ≥ 2 recent dailies, delete older dumps
  after the next verified restore test; store off-site copies for DR.

**DB restore** — ONLY into a fresh, disposable database (never a live one):
```bash
docker run -d --name restore_pg -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD='<disposable-password>' -e POSTGRES_DB="$POSTGRES_DB" postgres:17-alpine
docker cp backup.dump restore_pg:/tmp/backup.dump
docker exec restore_pg pg_restore -U phoenix_ops -d phantom_phoenix /tmp/backup.dump
# verify: row counts + users/scans/audit_events present, alembic_version at head
docker exec restore_pg psql -U phoenix_ops -d phantom_phoenix -c '\dt'
```
Recovery ordering: (1) restore DB into fresh container, verify counts;
(2) restore artifacts (below); (3) point the stack at the restored volume;
(4) run `alembic upgrade head` once more to confirm the restored
`alembic_version` is current.

**Artifact backup (SEPARATE from the DB dump):**
```bash
docker run --rm -v uploads_data:/src:ro,z -v "$PWD/backups/db:/bk:z" alpine \
  tar czf /bk/artifacts_$(date -u +%Y%m%dT%H%MZ).tar.gz -C /src .
```
- A database backup does NOT include uploaded files/artifacts — they live in
  the separate `uploads_data` volume at `uploads/artifacts/{scan_uuid}/`.
- **Consistency requirement:** take the artifact tar and the DB dump at the
  SAME maintenance point (scans stop accepting new uploads ideally). A
  mismatched snapshot (DB row without artifact file, or vice versa) yields
  scan metadata with missing forensic images until re-analysis.
- Verified byte-identical restore: sha256sum every
  `artifacts/{scan_id}/*.jpg` file from the volume vs the extracted tar.

**Verified live (M14, disposable project):** `pg_dump -Fc` (13299 B), 
`pg_restore --list` integrity OK, restore into a fresh `postgres:17-alpine`
container returned identical row counts + hash-identical table contents
(users/scans/audit_events), `alembic_version` intact; artifact tar gzip-OK
and sha256-identical vs the volume contents.

---

## 9. Failure Recovery
| Failure | Symptom | Action |
|---|---|---|
| DB unreachable | `/api/readiness` → 503; `database_connectivity_up 0` | `docker compose up -d postgres`; check `docker compose logs postgres` |
| Detector load failure | scans → `ANALYSIS_FAILED`; `detector_inference_total{status="failure"}` rises | Check `MODEL_ID` + weights; `/api/health` shows `detector_configured=false` |
| Backend restart loop | unhealthy in `docker compose ps` | `docker compose logs backend`; check migration logs |
| Frontend down | port 5173 dead | `docker compose restart frontend` |

**Safe shutdown:** `docker compose down` (keeps volumes). NEVER `down -v`
unless total data loss intended — deletes `postgres_data` + `uploads_data`.

**Database outage behavior (M14, verified live):** any connectivity-class DB
failure (SQLAlchemy `OperationalError`/`InterfaceError`, raw
`socket.gaierror`, `ConnectionError`, asyncpg connection errors) returns a
generic **503** with
`{"error": {"code": "SERVICE_UNAVAILABLE", ...}}` on ALL DB-backed routes
(login, scans, reports, artifacts, metrics, audit). Invalid credentials
still return 401 — the two failure modes are distinguishable. Programming
errors (e.g. SQL/ORM bugs) still yield 500, deliberately NOT hidden as
503. Sanitized single-line log per failure (category `database_unavailable`
+ request ID; never SQL/DSN/connection details). Sessions are always rolled
back and closed by the `get_session` dependency. Test users seeded via SQL
(not through the app) generate no audit events, by design.

---

## 10. Security Gate (Milestone 12 status)

Implemented:
- Real backend authentication: Argon2id password hashes, HS256 signed
  HttpOnly session cookie (SameSite=Lax), strict algorithm/issuer/claims
  validation, fail-closed when `AUTH_SECRET` is absent.
- Authorization: owner-scoped scans, uniform 404 for others' and legacy
  records, admin-only metrics. Bearer header accepted for machine clients.
- Rate limiting: login 5/min/IP, scans 10/min/process (429 + `Retry-After`);
  socket-peer key only (no header spoofing), 1-worker topology explicit.
- CSRF: SameSite=Lax cookie + strict CORS origin allowlist + **origin guard
  on cookie-authenticated state changes** (see §12).
- Frontend: real login form, session-aware navigation, 401/403/429 handling.
  No credentials in source or storage.
- **Administrative audit trail (M14):** `audit_events` table + admin-only
  read endpoint; see §13.
- **DB-outage handling (M14):** generic 503 on all DB-backed routes; see §9.

Remaining limitations (explicit, do NOT treat as "no auth" anymore):
1. **DB-outage login** now returns 503 (fixed in M14; verified live).
2. **No server-side session store** — no token revocation/denylist; disablement
   takes effect at token expiry (≤ 30 min).
3. **Rate limiter scope is per-process** — multi-replica deployments need a
   shared backend before claiming distributed enforcement.
4. **No user-management UI/API** (deliberately out of scope).
5. **Audit table is application-audited, NOT tamper-proof** — a database
   administrator can modify/delete rows; treat DB access itself as the
   security boundary.
6. **Login Origin is presence-optional** — browser POSTs always carry Origin,
   so browser clients are validated; non-browser clients without Origin are
   accepted by design (tests/CLI), which is safe because login needs no
   ambient cookie authority.

Platform remains a **staging candidate**, not production-ready until HTTPS,
secret management, and rate-limit scope are resolved for the target deployment.

## 12. CSRF Policy Inventory (Milestone 14)

| Route | State change | Auth | CSRF mechanism | Origin policy | Tests |
|---|---|---|---|---|---|
| `POST /api/auth/login` | session issuance | public | SameSite=Lax + CORS + Origin check | if Origin sent → must be in allowlist (browser POSTs always send it); missing → allowed (non-browser clients have no cookie authority) | unit + live TLS |
| `POST /api/auth/logout` | clears cookie | public | SameSite=Lax + origin guard when session cookie present | cookie-authenticated request without allowed Origin → 403 | unit + live TLS |
| `POST /api/scans` | creates scan | cookie OR bearer | SameSite=Lax + origin guard (cookie path) | cookie-authenticated request without allowed Origin → 403; bearer requests bypass (compromised pages cannot forge custom Authorization headers cross-site without a CORS grant) | unit + live TLS |

False-positive avoidance: test/probe clients using TestClient/curl with no
origin receive 403 on cookie-authenticated POSTs; use a Bearer header for
non-browser tooling, or send the exact allowlisted Origin header. Do NOT
weaken cookie flags or the allowlist to make tooling pass.

Forwarded `Host`/`X-Forwarded-*` headers are NOT trusted anywhere in the
origin/CSRF/rate-limit logic.

## 13. Security Audit Trail (Milestone 14)

`audit_events` table (migration `c3a91ffd8e42`): `id`, `created_at` (UTC),
`actor_user_id` (FK→users, SET NULL on user deletion), `actor_role`,
`event_type`, `outcome` (success/failure/denied), `resource_type`,
`resource_id`, `request_id`, bounded `detail` (≤255 chars, charset-normalized).

Recorded events:
- `login_success` / `login_failure` — actor when account is known (unknown
  probes recorded with actor NULL, detail holds the sanitized username).
- `logout`
- `admin_bootstrap`
- `admin_legacy_scan_access` / `admin_cross_user_access` — when an
  administrator reads another user's (or a legacy NULL-owner) scan, report,
  or artifacts; admins' own scans are deliberately not audited (noise).
- `role_access_denied` — insufficient-permission attempts (e.g. non-admin
  hitting `/api/metrics`).

Properties:
- Never stores passwords, tokens, cookies, image bytes, raw bodies, EXIF.
- Anonymous 401s are intentionally NOT audited (unbounded noise); documented.
- Writes go through a dedicated session and never break the request path
  (availability over forced atomicity — explicit tradeoff).
- No recursive logging; no update/delete application routes.
- **Trust boundary:** a DB administrator can modify/trim this table — this
  is NOT a tamper-proof ledger; DB access itself is the boundary of trust.
- Retention: none implemented — operators should archive/trim `audit_events`
  during their backup maintenance windows.

Inspection:
```bash
curl -sk -b admin.jar https://<host>/api/admin/audit?limit=50 \
  # optional: &event_type=admin_cross_user_access
```
Ordinary users receive 403. The read path is admin-session-only; there is no
public endpoint, no tooling token, and no log-metric duplication of payloads.

---

## 11. Runbook validation status

---

**Executed successfully against a live stack (Milestone 13, disposable project
`pp13`, Postgres 17 containers):**
- `docker compose -p <proj> build backend frontend` — images built
- `docker compose -p <proj> -f compose.yaml -f compose.staging.yaml up -d` —
  stack healthy; `alembic upgrade head` ran automatically in the backend
  container (both revisions applied)
- `docker compose exec backend python -m backend.bootstrap_admin` — admin
  created interactively
- Login over `https://127.0.0.1:8443` → 200, **Set-Cookie verified**:
  `HttpOnly; Secure; SameSite=lax; Path=/; Max-Age=1799`
- Unauthenticated `/api/scans`, `/api/metrics` → 401; cross-user scan/report/
  artifact → uniform 404; admin access → 200
- Real image upload → **real (unmocked) inference completed** (real HF weights
  downloaded on first scan), SHA-256/dimensions/byte-size matched the upload,
  all four forensic analyzers returned real outputs, PDF downloaded (valid
  `%PDF-` header), authenticated artifact images matched upload dimensions
- Rate limiting over real TLS connections: scans 10→429, login 5→429 with
  `Retry-After` (per-IP, counts all attempts)
- Backend traversal layer → 404 (`--path-as-is` on the backend port);
  through the TLS+frontend chain nginx normalizes away from `/api` and serves
  only the benign SPA shell (nothing exposed)
- Forbidden Origin login → blocked (403/429 depending on limiter state)
- Readiness 503 with Postgres stopped → 200 after recovery
- Auth fail-closed re-verified in an isolated container: empty & short
  `AUTH_SECRET` → `AuthUnavailableError` (login would 503)
- Restart persistence: scan detail/PDF/artifacts all 200 after `restart`
- Compose without `AUTH_SECRET` in `.env` refuses to build/start
  (`:?` interpolation error) — verified
- Request-ID propagation verified live (client header → structured JSON log
  line); logs contain no passwords/auth-secret/tokens (grep-verified)

**Executed successfully against a live stack (Milestone 14, disposable project
`pp13`, Postgres 17 containers, over real TLS at 8443):**
- Migration `c3a91ffd8e42` (audit_events) applied, downgraded and re-applied —
  existing `users`/`scans` rows preserved; table live-verified (`\d audit_events`).
- Audit events written live for `admin_bootstrap`, `login_success`,
  `login_failure`, `logout`, `admin_cross_user_access` (admin reading another
  user's scan); own-scan access audited NO event (by design).
- `GET /api/admin/audit` over TLS → 200 with real events; ordinary-user 403 is
  covered by route tests (no non-admin password available live).
- Cookie-CSRF guard live: cookie `POST /api/scans` without Origin → **403**;
  evil Origin → **403**; allowed Origin → proceeds; bearer without Origin →
  reaches validation (422) — bypass confirmed live.
- Admin cross-user scan access over TLS → 200 + audit row; own scan → 200,
  no audit row.
- **DB-outage (postgres stop)**: login, scan list, scan detail, admin audit →
  all **503** with generic body; readiness → 503; recovery after `start
  postgres` → 200 with data intact. Structured log lines contain
  `exception_category: database_unavailable` + request ID only (grep found
  no DSN/credentials). Unit tests additionally cover `gaierror`
  (raw asyncpg connect failure), `TimeoutError`, recovery login, and
  invalid-creds-vs-infra separation.
- Rate limits re-verified on M14 build: scans 10×422 → 429, login
  5×401 → 429, `Retry-After: 53` observed; limiter keyed on socket peer only.
- **Backup/restore EXECUTED:** `pg_dump -Fc` → 13299-byte dump (mode 600,
  sha256 sidecar), `pg_restore --list` integrity OK, restored into a fresh
  `postgres:17-alpine` container: identical row counts and hash-identical
  contents for users/scans/audit_events; FK/ownership intact;
  artifact tar verified sha256-identical against the source volume.
- Playwright E2E (4 tests) and frontend lint/build, compose config (both)
  valid; `git diff --check` clean.

**Documented but NOT executed:**
- CA-signed HTTPS with a real hostname; HSTS with long max-age
  (M13 + M14 same blocker)
- Alerting delivery (no Prometheus server configured)
- Multi-replica rate limiting (requires shared backend — not deployable today)
- `audit_events` archival/retention automation

**Host-specific note:** SELinuxEnforcing hosts (Fedora) need `:z` labels on
bind mounts (already in `compose.staging.yaml`), and host port 443 may be
occupied by local tooling — staging TLS binds 8443 with HTTP 8080 redirect.

---

## 12a. Final integration sprint (addendum)

**Frontend API base policy (release-fix):** production builds default the
SPA to SAME-ORIGIN requests (`/api/...` — the frontend nginx container
proxies `/api` → `backend:8000`). Absolute API URLs must be provided at
build time via `VITE_API_BASE`; runtime user input is never used. Dev keeps
the `localhost:8000` fallback. No backend secrets are ever embedded in
`VITE_*` variables or the bundle.

**Visual completion:** `PhoenixMascot` is an original pixel-art phoenix
(crest, spread red/orange plumage, gold belly, flame tail, blue/cyan magic
diamond + aura in the investigating state), grid-drawn as crisp-edge SVG
rects with per-state palettes; `prefers-reduced-motion` disables the
animation classes. Login screen uses the dedicated celestial
authentication background. Landing primary CTA uses the brand amber with
visible focus rings. No new dependencies were added this sprint — `motion`
was evaluated and rejected: existing CSS keyframes already cover state
transitions (CSS/SVG chosen as the smallest implementation per plan).

**Test-suite isolation warning (honest incident log):** running the backend
DB integration suite (`RUN_DB_TESTS=1`) deletes all `scans` rows
(`tests/test_database.py` clean-slate fixture) in whatever database
`DATABASE_URL` points to. During M14 validation this wiped sample scan rows
in the DISPOSABLE `pp13` database (no production data involved — volumes
preserved, scans recreated live afterwards). NEVER point `RUN_DB_TESTS=1`
at a database containing records you care about.

**Executed this sprint (all over real TLS `https://127.0.0.1:8443`):**
- Frontend served via nginx SPA + same-origin `/api` proxy → 200
- Login (bootstrap admin) → 200; `Set-Cookie`: `HttpOnly; Secure;
  SameSite=lax; Path=/; Max-Age=1799`
- Real image upload → **real inference** (CommunityForensics-DeepfakeDet-ViT,
  18.08 s wall incl. weight load; CPU container): SHA-256 bit-match with the
  uploaded file, verdict `LIKELY_REAL` with rationale + explicit
  `not_claimed` list, 5 evidence items, attention-rollout explainability
  available. No values fabricated.
- PDF report → 200, 851,600 bytes, valid `%PDF-` header
- Artifact (`ela.jpg`) authorized → 200
- Anonymous `/api/scans`, anonymous PDF → 401
- Admin legacy NULL-owner scan access → 200 **+ `admin_legacy_scan_access`
  audit row** (bug found & fixed this sprint: legacy path was previously
  unaudited)
- Cross-user denial live: not re-executable without a second known-password
  non-admin account (no registration/seed app flow exists by design);
  uniformly 404 for others'/legacy records is covered by the backend route
  test suite (M12/M14)
- Playground gates: 156 pytest (+1 DB suite to 166 documented M14), 5
  pre-existing lint warnings, build ✓, Playwright 4 ✓, compose config ✓,
  `git diff --check` ✓
