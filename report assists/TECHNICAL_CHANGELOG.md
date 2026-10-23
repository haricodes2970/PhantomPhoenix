# PHANTOM PHOENIX — Technical Changelog (this sprint)

## Before / after file-change summary

**Working-tree state before this session:**
- `frontend/src/App.tsx` — 441 lines (overwritten experimental rewrite; original was ~1,431 lines and uncommitted)
- `frontend/src/components/**` — ~200+ files including ~90 throwaway `TestDashboard*` / `TestMinimal*` files, a `DashboardView_new.tsx`, a syntactically broken `DashboardView.tsx` (unclosed JSX ternary near `</CardContent>`), and several `verbatimModuleSyntax` type-import violations

**Working-tree state after this session:**
- `frontend/src/App.tsx` — **1,431 lines, byte-for-byte the recovered original** (snapshot blob `281134c29045a8bad2d34efbc751ce0c56129c71`), verified against a fresh production build
- `frontend/src/components/**` — removed from the working tree and **moved (not deleted)** to `/tmp/opencode/quarantine/components/`
- New directory `report assists/` (reports + screenshots)

## Recovery — root statement
- Source of the recovered file: OpenCode session snapshot git object store `~/.local/share/opencode/snapshot/6470a53370537b843f5ef8cd30a5a26d9af37edd/a39bc0f14a58d519180a7bdab2cec8c649454bfa` (mtime 2026-10-18 16:33 IST — the latest snapshot containing App.tsx).
- Chosen blob: `281134c29045a8bad2d34efbc751ce0c56129c71` (1,431 lines) vs its parent variants (`4c94c43b`, `190d26e9`, `62b17900` — 1,430 lines; earlier still: 1,408/1,403/1,402-line versions). The chosen blob is the newest and differences are exactly the "amber-CTA + focus-visible + bg-auth landing" polish that had been agreed pre-overwrite — proof it is the latest intended state, not an intermediate.
- Independent corroboration: the running container `pp13-frontend-1` serves a production bundle whose sha256 (`d005ec03be95d184cf98cea24308c109203b414f3f0112a91f5ace848137f66e`) is **byte-identical** to the bundle rebuilt from the restored original — the overwrite never got built into an image. This validates both the recovery and the build determinism.
- The pre-restore overwritten version is kept at `/tmp/opencode/App_overwritten_backup.tsx` (outside repo).

## Root cause and minimal fix (verified defects found in quarantined files)
These files are **not in the live app** (quarantined). The diagnosis stands from the pre-recovery state:
1. `components/dashboard/DashboardView.tsx` — compiler cascade `TS1005: ')' expected` at hooks after a malformed JSX ternary where the `) : (` branch was never closed with `)` before `</CardContent>` (~line 155-156). Fix would have been one `)` — never applied because recovery superseded it.
2. Multiple `verbatimModuleSyntax` type-only import errors across `components/` (Card, Collapsible, Input, DropZone, ArchiveView, LoginView, DashboardView, LandingView, Header) — several already had fixes in the snapshot history; remaining unused-import / self-import (`formatArtifactUrl`) issues were left as found, since the whole tree was unused.

## API fields the (running, original) results UI actually consumes — verified live
- `GET /api/scans` → `{ scans: [...] }` — rows shown on the Archive page; verified with 5 real records present.
- `GET /api/scans/{scan_id}` → structured record with verdict/score/confidence, evidence items, metadata, artifact paths, model outputs — shown as structured cards/tables; raw JSON kept inside collapsible technical-details.
- Forensic artifacts: URLs resolved via `formatArtifactUrl` → `/api/artifacts/{path}` — verified all serve HTTP 200.
- `GET /api/scans/{scan_id}/report.pdf` → `application/pdf` — verified with a real download (400,650 bytes, header `%PDF-1.4`).
- Auth: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` — all exercised live; the guest-state boot `GET /api/auth/me` answering 401 while logged out is by design (auth gate behaviour; not an app bug).

## Compatibility decisions
- **No backend/api/schema/auth changes.** Detector, thresholds, audit, CSRF, rate limits untouched.
- **No new dependencies.** `react-router-dom` (previously installed, unnecessary — app uses hash routing) was NOT removed to avoid touching `package-lock.json`; it is inert.
- **Component experiment quarantined, not deleted,** so nothing is lost if the user later wants the componentised UI finished.
- **`phoenix-staging-tls` / `pp13` compose stack** left running exactly as-is; no rebuild or restart performed.

## Tests used to verify each important change
| Change | Verification |
|---|---|
| Restored `frontend/src/App.tsx` | `./node_modules/.bin/tsc -b` exit 0; `npm run build` exit 0; bundle hash identical to the running container's production bundle |
| Build reproducibility | `sha256sum` frontend/dist bundle vs container bundle → identical |
| Runtime integration | Playwright-driven manual smoke: login → dashboard → upload real image (`datasets/real/real_000002.jpg`) → real inference → results → artifact images load → PDF 200 → archive → logout/login (full detail in TEST_RESULTS.md) |

## Recovery limitations
- The ~1,400-line original had **never been committed**; git could only supply a 426-line unauthentic-prototype variant. Recovery depended entirely on the session snapshot object store; future users should commit this file.
- No other file was recovered this way; everything else in the working tree was either fine or (components) unused.
