# PHANTOM PHOENIX — UI/UX Sprint Report

**Date:** 2026-10-18
**Project:** PHANTOM PHOENIX — digital media authenticity & AI forensic intelligence platform (upload → detector inference → structured forensic results → forensic artifacts → PDF dossier)

## Scope of this sprint
Recovery from the stalled UI-rewrite loop, restoration of the original working single-file application, verification of the full end-to-end flow, and honest documentation with real screenshots. No new app redesign was attempted.

## Initial branch and working-tree status
- Branch: `feat/dataset-pipeline` (HEAD `d711815`)
- Everything from the UI sprint was UNCOMMITTED (per this sprint's rules, still unstaged)
- Runaway loop artifacts found: ~90 stray generated test files under `frontend/src/components/dashboard/` (`TestDashboard2..39`, `TestMinimal3..44`, `DashboardView_new.tsx`)
- `frontend/src/App.tsx` had been overwritten with a ~441-line component-based rewrite

## Reported failure — confirmed facts
1. **CONFIRMED:** `frontend/src/App.tsx` was overwritten (original was ~1,431 lines; working tree had 441 lines; 1,652 diff lines vs original).
2. **CONFIRMED:** a rewrite-retry loop ran for hours and generated ~90 throwaway `Test*.tsx` files inside `frontend/src/components/dashboard/`.
3. **UNRESOLVED (no longer blocking):** the exact reason the original rewrite loop kept failing was not re-verified line by line — recovery superseded it. The original monolith has 4 pre-existing oxlint *warnings* (not errors) that were present before this sprint.

## Recovery investigation
Checked, in order:
1. Working tree — current file only 441 lines (the overwrite).
2. IDE/local backups (`*.bak`, `*.orig`) — none found.
3. Git object database — `git show HEAD:frontend/src/App.tsx` is a **426-line** earlier version **without authentication**; the ~1,431-line auth-enabled original was never committed, so git could not supply it.
4. Reflog/stash — no stash entries.
5. Docker image layers — the running `pp13-frontend-1` container serves the **exact same production bundle** (sha256 `d005ec03…`, file identical to the restored original's build). The overwrite never reached the image.
6. **Recovery source found:** OpenCode session snapshot object store (`~/.local/share/opencode/snapshot/6470a533…/a39bc0f1…`). Blob `281134c2` = `frontend/src/App.tsx`, **1,431 lines**, first line `import React, { useState, useEffect } from 'react';` — self-contained monolith including the internal `PhoenixMascot` component, auth gate, upload, results, artifacts, archive, PDF link. This blob is the newest variant (mtime ~2026-10-18 16:33 IST) and its content matches the last decisions from the honoured plan (amber primary CTA, focus-visible rings, `.bg-auth` landing treatment).

**Recovered from where:** OpenCode snapshot blob `281134c2…` → restored to `frontend/src/App.tsx` (1,431 lines, `credentials: 'include'` fetches intact — 10 occurrences).

**NOT recovered: nothing.** The full original was recovered from the snapshot; the pre-restore overwritten version is preserved at `/tmp/opencode/App_overwritten_backup.tsx` (outside repo; not deletable proof against accidents).

What was considered-and-rejected: keeping the 441-line component rewrite as the app. It is incomplete (upload submit handlers were stubbed empty, a known JSX fault, several type-import defects) and does not contain the user's working integrations. Original restored instead; the component experiment was quarantined, not destroyed.

## Files touched in this sprint (working tree, all UNSTAGED)
| File | Action | Why |
|---|---|---|
| `frontend/src/App.tsx` | Restored (original from snapshot; before that it had been overwritten) | Re-establish the user's working app |
| `frontend/src/components/**` | **Moved (not deleted)** to `/tmp/opencode/quarantine/components/` | These experimental rewrite files are unused by the restored app, block `tsc -b` (unused imports, broken `DashboardView` ternary, ~90 throwaway test copies). Moved out of the tree so the build is clean. Can be restored on request. |
| `report assists/*` | New reports + screenshots | Documentation deliverables |

No staged, committed, pushed, tagged, branched, reset, cleaned, rejected, deleted-database or deployed actions. No DB records, volumes, users or scans touched. Vite dev server PID 405751 (started by this session) was stopped; worker processes identified as mine only.

## UI as it stands now
The original single-file app is the app, per instructions not to rewrite wholesale. It provides:
- Landing page (branded phoenix mascot, mono-typography, amber primary CTA)
- Login gate with generic failure message (no username disclosure)
- Investigator dashboard
- Upload with preview
- Results: verdict, score, structured evidence records, metadata, artifacts, charts
- Archive (history of scans)
- PDF Forensic Report download link (`/api/scans/{scan_id}/report.pdf`)

No new TSX/JSX code was added; no redesign was attempted this session. The JSON → readable-UI mapping that already existed in the original (and was verified live) is captured in `TECHNICAL_CHANGELOG.md`.

## Backend contract — untouched
`backend/main.py`, `backend/schemas.py`, detectors, thresholds, auth, CSRF, rate limits, audit: no changes this session. API verified live at both `http://localhost:8000/health` and `https://127.0.0.1:8443/api/health` → `status ok`, detector loaded.

## Real commands executed and their results
```
frontend:  ./node_modules/.bin/tsc -b          → exit 0
frontend:  npm run build (tsc -b && vite)      → exit 0, 1920 modules, built 1.41s, 279.72 kB gzip 82.50 kB
frontend:  npm run lint (oxlint)               → exit 0, 5 warnings (pre-existing)
frontend:  npx playwright test                 → 4 passed (4.0s)
root:      docker compose config --quiet        → OK
root:      git diff --check                     → clean (no whitespace errors)
manual smoke: see TEST_RESULTS.md                → all PASS / honest notes below
```

## Tests passed / failed / skipped / not run
See `TEST_RESULTS.md` for the full command-level table. Summary:
- Frontend lint/ build / Playwright smoke: **PASSED**
- Compose config + `git diff --check`: **PASSED**
- Backend unit tests: **NOT RUN** this session (no backend changes; prior 156/166 passing runs documented in earlier sessions)
- PostgreSQL DB integration (`RUN_DB_TESTS=1`): **NOT RUN** — deliberately skipped: its fixture deletes scan rows; would have to run against the valued `pp13` database, which we are forbidden to reset or endanger.
- Manual smoke: **PASSED** with two honest caveats (see TEST_RESULTS.md note 1 & 2)

## App running / URL (verified)
- Yes: `https://127.0.0.1:8443/` (self-signed TLS via `phoenix-staging-tls`, project `pp13`) — verified live this session via real login → upload → inference → results → artifacts → PDF → archive → logout/re-login cycle.
- Optional dev entry `http://localhost:5173`/`:8000`-style combo is documented but NOT in the verified state this session (dev port 5174 was not in `CORS_ORIGINS_CSV`); avoided it rather than changing backend config.

## JSON → readable UI (verified against live backend response shape)
- `/api/scans` (list) → rendered on Archive page as a table of scan records.
- single scan contains: verdict, forensic score, classifier outputs, confidence, media metadata (dimensions / format / size / dates), normalized evidence items (analyses such as ELA, FFT, noise, compression signals), artifact links, at-risk model insights, explainability readouts. All of this renders as structured cards instead of unformatted raw JSON; raw JSON, if needed, remains in the technical-details collapsible.
- Forensic artifacts (ELA / FFT / noise imagery) signed and served via `/api/artifacts/...`, verified to load (`artifacts-load` PASS).

## Known limitations / remaining bugs / unresolved items (ranked)
1. **Original UI no longer has the sub-headline "results page rebuild" polish.** The componentized new-UI experiment (in quarantine) made some visual improvements but is incomplete and not the source of truth; the original monolith is back. Severity: medium (cosmetic / product-goal gap).
2. **The overwritten 441-line variant also contained known defects** (unclosed ternary in `components/dashboard/DashboardView.tsx`; type-only import style issues; `formatArtifactUrl` self-import). Not fixed — they live in quarantine, unused. Severity: low (not in the running app).
3. **`login rate limit is 5/min/socket peer — careful when testing.** Documented to avoid future flakiness. Severity: informational.
4. **Dev-port CORS limitation** (5174 not allowed). Not a bug in the app, only affects a manual-only alternate dev entry. Severity: low.
5. Pre-existing oxlint **warnings** (5) remain in `App.tsx`. Severity: informational.
6. **Original ~1400-line App.tsx never had commit history** — this recovery proves the value of committing it. It remains unstaged per instructions. Severity: process risk (future sessions must not overwrite it again without recovery like this one).

## Final status
**Partially complete.**
- Original app, integrations and auth flow: **RECOVERED and VERIFIED end-to-end**.
- Sprint deliverables (screenshots, reports): **DONE**.
- Larger "results page rebuild / polish" ambition: **NOT delivered this session** (component experiment quarantined to keep the working app intact).
