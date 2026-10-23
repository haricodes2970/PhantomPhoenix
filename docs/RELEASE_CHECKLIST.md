# PHANTOM PHOENIX — Release Checklist

Use this checklist for validating staging release candidates.

## 1. Code Quality & Automated Tests (VERIFIED, M14)
- [x] Backend tests pass (`PYTHONPATH=. .venv/bin/pytest`; 166 passed incl. 33
      DB integration tests with `RUN_DB_TESTS=1` vs real PostgreSQL 17, M14)
- [x] Frontend linter passes (`cd frontend && npm run lint` — 5 pre-existing
      non-blocking warnings, no errors)
- [x] Frontend production build succeeds (`cd frontend && npm run build`)
- [x] Playwright E2E smoke tests pass (`npx playwright test` — 4 tests, M14
      updated for the cookie-auth UX)
- [x] `git diff --check` clean (M14)

## 2. Database & Migrations (VERIFIED live, M13+M14)
- [x] PostgreSQL container health check passes (`pg_isready`)
- [x] Alembic migrations apply cleanly on a live DB (`upgrade head` executed
      for all three revisions; M14 `audit_events` also down/up round-tripped
      with existing data preserved)
- [x] Backup/restore: `pg_dump -Fc` → `pg_restore --list` integrity → fresh
      container restore → identical counts + hash-identical rows (M14)

## 3. Containerization & Startup (VERIFIED live, M13)
- [x] Docker images build successfully (`docker compose build` — executed)
- [x] Services start healthy; Alembic migrations apply in-container (executed)
- [x] Liveness/Readiness/Health return expected codes (executed)
- [x] TLS proxy (`compose.staging.yaml`): HTTPS on 8443, HTTP→HTTPS 301 (executed, self-signed staging cert)
- [ ] CA-signed certificate + real hostname + HSTS long max-age (BLOCKED: no domain/cert)

## 4. Functional Smoke Tests (VERIFIED live, M13)
- [x] Unauthenticated access rejected on all protected endpoints (401, executed)
- [x] Authenticated login sets HttpOnly+Secure+SameSite cookie (executed)
- [x] Real scan completes with unmocked inference; SHA/dim match upload (executed)
- [x] PDF report downloads (valid PDF header, executed)
- [x] Artifacts retrievable with owning session (executed)
- [x] Cross-user scan/report/artifact → uniform 404 (executed)
- [x] Rate limiting: scans 10→429, login 5→429 + Retry-After (executed;
      re-verified on the M14 build)
- [x] Artifact traversal → 404 at backend (executed); upstream serves benign SPA shell only
- [x] Restart persistence verified (executed; audit rows also survive)
- [x] Database-down → readiness 503, recovery → 200 (executed)
- [x] Logs: structured JSON, request-ID propagated, no secrets grep-hit (executed)

## 5. Security (M14 status)
- [x] No secrets in tracked files (`.env` gitignored; untracked local `.env`
      generated with `python -c "import secrets"`)
- [x] Compose fails closed without `AUTH_SECRET` (executed) / `COOKIE_SECURE=true` in staging (executed)
- [x] Administrator bootstrapped via `python -m backend.bootstrap_admin` (executed, no default password)
- [x] DB-outage auth paths return generic 503, not 500; invalid credentials
      remain generic 401 (M14: unit tests + live TLS verification)
- [x] CSRF policy implemented + tested per state-changing route inventory
      (runbook §12: login / logout / scans; cookie requests require
      allowlisted Origin; bearer bypass documented)
- [x] Security audit trail live: writes + admin-only read endpoint verified
      (M14); sensitive fields never stored
- [x] Rate-limit keys: socket peer only; header spoofing not possible
      (documented aggregate-bucket tradeoff behind the TLS proxy)
- [ ] HTTPS with real CA-signed cert (BLOCKED: no public domain — staging TLS is self-signed)
- [ ] Cloud secret-manager integration (none configured — not invented)
- [ ] Shared-backend rate limiter for multi-replica deployments (not
      deployable today — single-process topology documented)
- [ ] `audit_events` retention/archival automation

## 6. Observability Verification
- [x] `/api/metrics` exposition validated (types, buckets, bounded labels; M10A)
- [x] `/api/liveness` and `/api/readiness` (200/503 semantics) verified
- [x] Structured JSON logs contain request IDs; no sensitive values
      (M14: DB-outage logs carry only `database_unavailable` + request ID)
- [ ] Alert rules present (`docs/prometheus/alert_rules.yml`) — NOTE: rule definitions only; live Prometheus/Alertmanager delivery NOT verified

## 7. Sign-off
- [x] Known limitations reviewed (see `docs/OPERATOR_RUNBOOK.md` §10–§13)
- [ ] Release owner approval
- [ ] No release tag pushed without explicit authorization

**Current classification (M14): staging-validated** (self-signed TLS, single
replica, disposable-project verified). Remaining blockers to production:
CA-signed HTTPS + real hostname, secret management, shared-backend rate
limiting before replicas, audit-retention automation.
