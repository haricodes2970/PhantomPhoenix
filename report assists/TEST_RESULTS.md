# PHANTOM PHOENIX — Test Results (2026-10-18)

All commands were actually executed. Exit statuses are recorded as run. Nothing is invented; anything not run is marked NOT RUN.

| Decoration | Test | Command | Exit / Result | Notes |
|---|---|---|---|---|
| ☐ | Frontend typecheck | `cd frontend && ./node_modules/.bin/tsc -b` | **exit 0 — PASS** | Ran cleanly after restoring original App.tsx and quarantining experimental components |
| ☐ | Frontend production build | `cd frontend && npm run build` (`tsc -b && vite build`) | **exit 0 — PASS** | 1920 modules, 1.41s, dist `index-D5IEJfm2.js` 279.72 kB (gzip 82.50 kB) |
| ☐ | Bundle equivalence to running stack | `sha256sum` dist bundle vs container's `index-D5IEJfm2.js` | **identical (`d005ec03…`) — PASS** | Proves restored source == what the live frontend proxy serves |
| ☐ | Frontend lint | `cd frontend && npm run lint` (oxlint) | **exit 0 — PASS** | 5 warnings, all pre-existing in original App.tsx (react-hooks/immutability advisories) |
| ☐ | Playwright smoke | `cd frontend && npx playwright test` | **4 passed (4.0s) — PASS** | 1) Landing CTAs gate guests; 2) hash routing back/forward; 3) protected links redirect; 4) invalid sign-in shows generic message |
| ☐ | Docker Compose config validation | `docker compose config --quiet` | **exit 0 — PASS** | Includes `compose.staging.yaml` overlay implicitly intact |
| ☐ | git whitespace check | `git diff --check` | **exit 0 — PASS** | no whitespace errors |
| ☐ | Backend unit tests | `RUN_DB_TESTS=` (unset) pytest | **NOT RUN** | No backend file changed this session; prior sessions verified 156 passing (166 with DB), so re-running adds nothing |
| ☐ | PostgreSQL integration tests | `RUN_DB_TESTS=1 pytest` | **NOT RUN — deliberately skipped** | Fixture DELETES scan rows; would have had to target the valued `pp13` database (10 scans, 5 records confirmed present + audit trail). Forbidden to endanger. Test DB not verified disposinble, so not run. |
| ☐ | Login (manual, real) | Playwright-driven browser session against `https://127.0.0.1:8443/` | **PASS** | Gated landing → Investigator Sign-In → successful sign-in → "Investigator Dashboard" visible. Rate limit 5/min/peer respected (1-2 logins per script run) |
| ☐ | Logout + re-login (manual, real) | same script, button-match sign-out | **PASS** | returns to Sign-In page; re-login works |
| ☐ | Upload real image (manual, real) | `datasets/real/real_000002.jpg` via file input | **PASS** | preview shown in upload view |
| ☐ | Real model inference (manual, real) | after upload → submit | **PASS** | Results appeared with real detector output (no mock). Detector is loaded (`buildborderless/CommunityForensics-DeepfakeDet-ViT`) |
| ☐ | Readable results / structured evidence (manual) | results page | **PASS** | structured evidence cards/metadata visible (see screenshots 05–07) |
| ☐ | Forensic artifacts load (manual, real) | `img[src*="/api/artifacts"]` HTTP GETs | **PASS** | at least one artifact image served 200 OK |
| ☐ | PDF report download (manual, real) | authenticated `GET /api/scans/{scan_id}/report.pdf` | **PASS** | HTTP 200, `application/pdf`, 400,650 bytes, header `%PDF-1.4` (saved at `/tmp/opencode/verify_report.pdf`, not copied into repo) |
| ☐ | Archive (manual, real) | `#history` | **PASS** | renders real scan list; screenshots |
| ☐ | Console errors | collected during Playwright drives | **PASS with note** | one benign 401: `GET /api/auth/me` answered 401 **while logged out** — this is the app's intended auth-state probe and matches M12/M14 design; no other console errors |

## Honest caveats
1. Screenshots were taken in **two runs**. Run 1 completed the app cycle through artifacts and then crashed on a test-side Playwright selector typo (`a[href] | a[href]` — CSS `|` not valid in Playwright; note for future runs — this did **not** affect the app itself). Run 2 completed the remaining steps using the existing scan via `#scan-{id}` instead of re-uploading. All steps were still executed live against the running stack; nothing was simulated.
2. The manual smoke cycle created **one new real scan record** (`datasets/real/real_000002.jpg`) on the `pp13` database, plus its artifacts + audit trail, consistent with normal product usage; nothing was deleted or reset.
3. Backend pytest suites were **not re-executed**; treat "backend tests last passed" as prior-session evidence, not this-session evidence.
4. The `pp13` stack (backend healthy 4h, frontend 6h, postgres 6h, phoenix-staging-tls 6h) was left running; no deploy, restart or rebuild occurred.
