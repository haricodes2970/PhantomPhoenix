# PHANTOM PHOENIX — Frontend Pre-Implementation Audit

**Date:** 2026-10-17  
**Auditor:** repository audit (no page implementation)  
**Scope:** baseline only. No frontend pages redesigned. No application source modified.

This document records facts verified from the working tree, source, and commands actually run. Inferences and unknowns are labeled.

---

## 1. Executive summary

The repository is the PHANTOM PHOENIX platform. Current branch is **`feat/dataset-pipeline`**, not `main`. HEAD is `d71181561f179d34f6f0f951e52509aeec7abc32` (`docs+scripts(benchmark): add alternative detector benchmark script and verified checkpoint equivalence report`).

The frontend is a **single-file, tab-based React app** (`frontend/src/App.tsx`) already wired to the live scan API. It is functional in source (upload, results, archive, PDF link, forensic artifact images). It is **not** a routed multi-page product. There is no landing page, sign-in, registration, settings, admin, inventory, or dedicated reports page.

UI state classification: **partially functional, API-connected prototype in one component.** Not mock data. Not a design-only prototype. Not verified against a running backend in this audit (no browser or API calls were made).

The six supplied backgrounds exist only outside the repo, in `/home/hari007/Downloads/ww/`. They were **not copied**. Empty destination directories were created under the documented asset root.

Frontend checks that were run: oxlint (pass, 1 warning), `tsc -b` (pass), `npm run build` (pass). No frontend test runner exists.

**Do not start page implementation until Hari approves image copy and the first vertical slice.**

---

## 2. Repository and Git baseline

Verified 2026-10-17 from this working directory (`/home/hari007/Projects/Academics/MainProject/PP`).

| Item | Value |
|---|---|
| Root | `/home/hari007/Projects/Academics/MainProject/PP` |
| Current branch | `feat/dataset-pipeline` |
| HEAD | `d71181561f179d34f6f0f951e52509aeec7abc32` |
| HEAD subject | docs+scripts(benchmark): add alternative detector benchmark script and verified checkpoint equivalence report |
| Author / date | Hari, 2026-10-17 08:51:23 +0530 |

`git status --short` at audit start (untracked; nothing staged, no modified tracked files):

```
?? docs/FRONTEND_IMPLEMENTATION_PLAN.md
?? docs/PHOENIX_ASSET_MANIFEST.md
?? frontend/public/assets/
?? opencode.json
?? rep/
```

Local branches: `chore/demo-readiness`, `chore/pilot-error-analysis`, `feat/dataset-pipeline` (current), `feat/ml-env`, `fix/attention-and-health`, `fix/e2e-forensic-pipeline`, `main`.

Remote branches: `origin/main`, `origin/chore/pilot-error-analysis`, `origin/feat/ml-env`. No dedicated frontend feature branch exists.

This audit did **not** switch branches, stage, commit, or clean the tree. Untracked `rep/`, `opencode.json`, and the two planning docs were left untouched.

### Top-level layout (observed)

`alembic/`, `backend/`, `datasets/` (gitignored), `docs/`, `frontend/`, `rep/` (untracked), `scripts/`, `tests/`, `uploads/` (gitignored), `.venv/`, `compose.yaml`, `Makefile`, `pyproject.toml`, `requirements-api.txt`, `requirements-ml.txt`, `README.md`, `alembic.ini`, `.env.example`.

Frontend and backend are sibling directories at the repo root. There is no monorepo package manager at the root.

### Documentation relevant to frontend

| Path | Status |
|---|---|
| `docs/FRONTEND_IMPLEMENTATION_PLAN.md` | Untracked. High-level pixel-art rollout order. Does **not** name the six supplied background filenames. Claims no new auth endpoints are required. |
| `docs/PHOENIX_ASSET_MANIFEST.md` | Untracked. Lists **different** planned filenames (`landing-backdrop.png`, `upload-console.png`, `results-backdrop.png`, mascot and badge PNGs). All marked `planned`. None of those files exist. |
| `frontend/public/assets/phantom-phoenix/README.md` | Untracked. Describes intended folders (`brand/`, `backgrounds/`, `phoenix/`, `illustrations/`, `ui/`). Says components must reference `/assets/phantom-phoenix/...` and must not reference a file before it exists. |
| `frontend/README.md` | Stock Vite + React + Oxlint template text. Not product documentation. |
| Root `README.md` | Backend/API quick start. Frontend is not documented there. PDF route is also missing from the README endpoint table (it exists in code). |

Older docs were **not** treated as the current Git baseline. Current branch and HEAD above are the source of truth.

---

## 3. Frontend architecture and dependency versions

### Stack (declared vs installed)

`frontend/package.json` ranges vs lockfile / `node_modules` versions read during this audit:

| Package | package.json | Lockfile | Installed |
|---|---|---|---|
| react | ^19.2.8 | 19.3.0 | 19.3.0 |
| react-dom | ^19.2.8 | 19.3.0 | 19.3.0 |
| vite | ^8.3.0 | 8.3.4 | 8.3.4 |
| typescript | ~6.0.2 | 6.0.3 | 6.0.3 |
| tailwindcss | ^3.4.19 | 3.4.19 | 3.4.19 |
| lucide-react | ^1.57.0 | 1.57.0 | 1.57.0 |
| @vitejs/plugin-react | ^6.1.1 | 6.1.2 | (present via lock; not separately printed) |
| autoprefixer | ^10.6.1 | 10.6.1 | lock only verified |
| postcss | ^8.5.30 | 8.5.30 | lock only verified |
| oxlint | ^1.81.0 | 1.88.0 | 1.88.0 |
| @types/node | ^24.13.3 | (lock) | not printed |
| @types/react | ^19.2.18 | (lock) | not printed |
| @types/react-dom | ^19.2.7 | (lock) | not printed |

`node_modules` was already installed. No install or lockfile change was made.

### What is absent

| Concern | Finding |
|---|---|
| Router | None. No `react-router`. `vercel.json` rewrites all paths to `index.html`, but the app has no client routes. |
| State library | None. Local `useState` / `useEffect` only. |
| UI kit | None (no shadcn, Radix, MUI, Headless UI). |
| Charts | None. |
| HTTP client | Native `fetch` only. No axios. |
| API module | None. Calls are inline in `App.tsx`. Base URL: `import.meta.env.VITE_API_BASE` or `http://localhost:8000`. |
| Tests | No Vitest, Jest, Playwright, or Cypress. No `*.test.*` / `*.spec.*` under `frontend/` (excluding `node_modules`). No `test` script. |
| Env example for frontend | No `frontend/.env` or `frontend/.env.example` found. |
| Strict TS | `tsconfig.app.json` has unused-local checks and `verbatimModuleSyntax`. It does **not** set `strict: true`. |

### Config files

- `frontend/vite.config.ts` — React plugin only. No proxy, alias, or `envDir`.
- `frontend/tailwind.config.js` — content globs for `index.html` and `src/**`. Custom colors: `slate.850` `#151c2c`, `slate.900` `#0f172a`, `slate.950` `#090d16`. No font family, no pixel-art tokens, no screens override (Tailwind 3 defaults).
- `frontend/postcss.config.js` — `tailwindcss` + `autoprefixer`.
- `frontend/tsconfig.json` — project references to `tsconfig.app.json` and `tsconfig.node.json`.
- `frontend/.oxlintrc.json` — plugins `react`, `typescript`, `oxc`. Rules: `react/rules-of-hooks` error, `react/only-export-components` warn.
- `frontend/index.html` — title is still the template string `frontend`. Viewport meta is present. Favicon is `/favicon.svg`.

### Source tree (application code only)

```
frontend/src/main.tsx      # StrictMode root
frontend/src/App.tsx       # entire UI + API calls (~426 lines)
frontend/src/types.ts      # scan/verdict types
frontend/src/index.css     # Tailwind directives + body slate theme
frontend/src/App.css       # unused Vite template CSS (not imported)
frontend/src/assets/       # vite.svg, react.svg, hero.png (template leftovers)
frontend/public/favicon.svg
frontend/public/icons.svg
frontend/public/assets/phantom-phoenix/README.md
```

`App.css` is not imported by `main.tsx` or `App.tsx`. Dead template CSS.

---

## 4. Actual route and page inventory

There are **no URL routes**. Navigation is `activeTab: 'upload' | 'history'` plus `currentScan` presence. Opening `/`, `/login`, or anything else renders the same app (SPA rewrite only).

| Page or route | Exists? | Current functionality | Missing work |
|---|---|---|---|
| Landing | No | App opens directly on the upload workstation. | New view. Needs sunset background after copy. No product hero today. |
| Sign in | No | — | Backend has no login. Do not build until an auth contract exists. |
| Registration | No | — | Same. |
| Dashboard | No | Archive tab is the closest analogue, not a dashboard. | New view or a deliberate decision that archive **is** the dashboard. |
| New Scan / Upload | Yes (default tab, not a URL) | Drag/drop and click-to-select. `accept` JPEG/PNG/WEBP. Shows name and KB. POST `multipart` field `file`. Button disabled while loading. Error banner from `error.message`. | Client-side size/dimension checks. Image preview. Progress beyond a spinner. Pixel-art console. |
| Scan Results | Yes (in-place, not a URL) | Verdict, risk, model fake probability, logit, device, duration, rationale, `not_claimed`, evidence cards, artifact `<img>`, PDF link. | Does not render `explainability`. Does not render raw `indicators`. No friendly vs warning background. No dedicated route or shareable scan URL. |
| Scan History | Yes (Archive tab) | GET list `limit=20`. Click loads full scan. Empty state. Refresh. | Ignores `next_cursor`. Load failure is `console.error` only. No filters. |
| Reports | Partial | PDF is a link on the results panel only. No report library. | List/view of reports separate from a scan is not implemented. Backend generates PDF on demand; it does not store a report catalog. |
| Inventory / Saved Evidence | No | Evidence is per-scan cards, not a saved inventory. | No backend "saved evidence" resource found. |
| Settings / Profile | No | — | No user model. |
| Admin | No | — | No admin API. |

### In-app views that do exist (verified in `App.tsx`)

1. **Upload** — `activeTab === 'upload' && !currentScan`.
2. **Archive** — `activeTab === 'history' && !currentScan`.
3. **Result** — `currentScan` set (from POST body `data.result` or from GET by id). "New Scan" clears `currentScan` but does not force `activeTab` back to upload if the user came from history (button only calls `setCurrentScan(null)`).

---

## 5. Existing reusable components

There is **no component library**. Everything is inline in `App.tsx`.

| Kind | What exists | Reuse / later |
|---|---|---|
| Layout | Sticky header (shield icon, wordmark, two tabs) + `<main>` max-w-7xl + footer disclaimer. | Extract a shell later. Do not throw away the disclaimer copy. |
| Navigation | Two buttons, local state. | Not a router. Improve only after route decision. |
| Buttons | Tailwind class strings, not components. | Extract if a second page needs the same control. |
| Cards | Result panels and evidence cards are duplicated class strings. | Extract `EvidenceCard` when redesigning results. |
| Forms | One file input. No text fields. | — |
| Tables | None. Archive is a clickable list. | — |
| Dialogs | None. | — |
| Alerts | One error `<div>` on upload. | History and GET-by-id errors are weaker. |
| Upload | Drop zone in `App`. | Reuse behavior; restyle later. |
| Image preview of upload | **Missing.** | Create later. |
| Analysis progress | Spinner + "Executing Forensic Pipeline...". No stages. Scan API is synchronous. | Do not invent staged progress the API does not emit. |
| Verdict | `getVerdictBadge`, `getRiskBadge`. | Reuse labels. Visual language is monochrome, not emerald/crimson. |
| Metadata | Shown as SHA, size, dimensions, media type, plus raw JSON of `evidence.result`. | No structured EXIF inspector. |
| Forensic evidence | Maps `evidence_items`. Renders artifact image when `artifact` is set. | Keep. Wire explainability separately. |
| Report download | `<a href="{API}/api/scans/{id}/report.pdf" target="_blank">`. | Keep the URL. `target=_blank` fights `Content-Disposition: attachment`. |
| Global styles | `index.css` body uses slate; `App.tsx` overrides with `bg-black`. Tailwind slate extensions unused by current UI. | Token work should reconcile this split. |
| Fonts | Tailwind `font-sans` / `font-mono`. No custom font files. | Pixel-art type is not installed. |
| Breakpoints | `md:grid-cols-2`, `flex-wrap`, `max-w-*`. Header is `px-8` with no mobile nav collapse. | Header will overflow on small screens. |
| Accessibility | One `alt` on artifact images. Upload control is a transparent `<input>` over a div. No `aria-*`, no focus trap, no skip link. Buttons are real `<button>`s. | Needs a pass after layout exists, not before API slice is stable. |

**Preserve:** upload POST, history GET, scan GET, PDF URL, artifact URL rewrite, verdict label set, disclaimer footer.

**Dead / do not treat as product UI:** `App.css`, `src/assets/vite.svg`, `react.svg`, `hero.png`.

---

## 6. Backend API integration and contract findings

Source of truth: `backend/main.py`, `backend/schemas.py`, `backend/models.py`, `backend/detector.py`, `backend/image_utils.py`, `backend/config.py`. Frontend caller: `frontend/src/App.tsx`, `frontend/src/types.ts`.

CORS (`backend/main.py`): origins `http://localhost:5173` and `http://127.0.0.1:5173` only. Methods `GET`, `POST`. Credentials allowed. A deployed frontend on another origin will be blocked until CORS is changed. That is a backend change and was **not** made here.

### Endpoints that exist

| Method | Path | Request | Response (verified) | Frontend status |
|---|---|---|---|---|
| GET | `/api/health` and `/health` | none | `HealthResponse`: `status`, `api_version`, `detector_loaded`, `detector_model_id`, `cuda_available`, `gpu_name` | **Not called.** |
| POST | `/api/scans` | `multipart/form-data` file field `file`. JPEG/PNG/WEBP by decode. Max 15 MiB (`max_image_size_mb`), max 8192 px/side. | `201` `ScanCreateResponse`: `{ scan_id, status, result }` where `result` is full `ScanResult`. Errors: `400` `{ error: { code, message, detail } }` for image validation. | **Used.** Reads `data.result`. Error path reads `errData.error.message`. Does not check `status === "failed"`. |
| GET | `/api/scans` | query `limit` (1–100, default 20), optional `cursor` (ISO timestamp) | `{ scans, next_cursor, limit }`. Each scan is `Scan.to_scan_result()` — the **full** stored result when `full_result` is present, not a summary DTO. | **Used** with `limit=20` only. Ignores `next_cursor`. Treats items as summaries (`filename`, `verdict`, dimensions). That works because full results still contain those fields. |
| GET | `/api/scans/{scan_id}` | UUID path | Stored `full_result` JSON, or a column fallback **without** `evidence_items`. `404` `{ error: { code: "NOT_FOUND", ... } }`. | **Used.** Expects the body itself to be the scan (`setCurrentScan(data)`), which matches `to_scan_result()`. `404` message is a generic `throw`, not the API `error.message` (non-OK without parse). |
| GET | `/api/scans/{scan_id}/report.pdf` | UUID | `application/pdf` attachment `phantom_phoenix_report_{id}.pdf`, or `404` / `500` JSON. | **Linked.** Not fetched via XHR. |
| GET | `/api/artifacts/{path}` | static files under `uploads/artifacts` | Image bytes (ELA / noise / FFT JPEGs). | **Used** via string split on `artifacts/`. |

No other HTTP routes were found on the FastAPI app.

### Feature support (frontend vs backend)

| Capability | Backend | Frontend |
|---|---|---|
| Image upload and validation | Yes. Decode-based. Codes include `FILE_TOO_LARGE`, `EMPTY_FILE`, plus later format/dimension errors in `image_utils.py`. | Sends the file. Browser `accept` only. No pre-check of 15 MiB or 8192 px. |
| Scan creation and retrieval | Yes, synchronous create + persist. | Yes, if API is up. DB persist failure is swallowed in `create_scan` (`pass`) and the computed result is still returned. **Not verified live.** |
| Authenticity verdicts and detector output | `LIKELY_AI` / `LIKELY_REAL` / `INCONCLUSIVE` / `ANALYSIS_FAILED` with risk, rationale, `not_claimed`. Thresholds 0.80 / 0.20. Model is CommunityForensics ViT (`buildborderless/CommunityForensics-DeepfakeDet-ViT`). | Renders label, risk, fake probability, logit, device, duration. Hardcodes the subtitle "ViT-Small" instead of `model_id`. |
| Metadata, ELA, noise, frequency | Analyzers run in `create_scan`. Evidence categories include those sources. Artifacts saved under `uploads/artifacts/{scan_id}/`. | Renders `evidence_items` and artifact images. Does not special-case analyzer ids. |
| Explainability | `ScanResult.explainability`: `status`, `kind`, `artifact`, `metrics`. Detector sets `kind: "attention_rollout"`. Metrics (when tensors exist): `num_layers`, `num_heads`, `num_patches`, `mean_cls_attention`, `max_cls_attention`, `attention_entropy`. **`artifact` is always `None` in `detector.py`.** No heatmap image is produced. | **Not in `types.ts`. Not rendered.** |
| Generator attribution | Explicitly in `not_claimed` ("generator identity"). README: image-level only, no attribution. | Must not invent attribution UI. |
| Scan history | Cursor pagination. | First page only. |
| PDF download | ReportLab via `generate_scan_pdf`. | Link only. |
| Authentication | **Not implemented.** | **Not implemented.** |

### Contract mismatches (do not invent endpoints to paper over these)

1. **POST vs GET shape.** Create returns `{ scan_id, status, result }`. Get-by-id returns the scan object itself. The UI handles both. Easy to break if someone "normalizes" one path.
2. **List payload is full results**, not the narrower `ScanItem` type. Frontend type is a subset, so it type-checks, but it also means list responses can be large.
3. **`explainability` dropped** on the client. Top-level field exists. Nested `models[].explainability` also exists in the schema and is not typed on the client.
4. **`indicators` typed but unused.** UI prefers `evidence_items`.
5. **Column-fallback scans omit `evidence_items`.** UI uses `currentScan.evidence_items \|\| []`, so it will not crash. Those old rows would show no forensic cards.
6. **`formatArtifactUrl` depends on the substring `artifacts/`.** Backend stores a relative path from `ForensicAnalyzer._save_artifact` (`uploads/artifacts/{scan_id}/...` style, via `os.path.relpath`). If that prefix is absent, the client prepends `/api/artifacts/` to the whole string and the image 404s. **Exact stored string was not re-verified against a live scan in this audit.**
7. **Health unused.** UI cannot show detector/DB degraded state.
8. **Pagination unused.** `next_cursor` ignored.
9. **Failed analysis still `201`.** `status: "failed"` with `error` set can arrive as a normal result. UI still renders it if `result` is present. Verdict should be `ANALYSIS_FAILED`. Not exercised here.
10. **DB write errors are swallowed** (`backend/main.py` create path). Client can show a result that was not persisted. Refresh of history would not include it. Frontend cannot detect this.
11. **Asset manifest names ≠ supplied background names.** Manifest: `landing-backdrop.png`, `upload-console.png`, `results-backdrop.png`. Supplied files: `landing-sunset-background.png`, `upload-console-background.png`, `results-friendly-background.png`, `results-warning-background.png`, plus authentication and dashboard. Do not treat the manifest as proof those files exist.
12. **README omits** `report.pdf` and `/api/artifacts`. Code is ahead of the README.

---

## 7. Authentication status

**Not implemented** on either side.

Searched backend Python for login, register, JWT, OAuth, OTP, and Google auth. Matches are unrelated (`AsyncSession`, "authenticity" in prose, SQLAlchemy sessions).

No user table, password hashing, session cookie, bearer token, or auth dependency was found on the FastAPI routes. All scan routes are unauthenticated.

Frontend has no login form, token storage, or auth header.

Google login and OTP are **not** implemented. Do not add authentication UI in the visual milestone unless a backend contract is added first. This matches `docs/FRONTEND_IMPLEMENTATION_PLAN.md` ("no new authentication systems are required") as a product choice, not as a hidden existing feature.

---

## 8. Background asset directory structure

Documented asset root matches the tree that already existed:

`frontend/public/assets/phantom-phoenix/`

Before this audit that directory contained only `README.md`. No `backgrounds/` folder.

Created with `mkdir -p` (no files written, nothing deleted):

- `frontend/public/assets/phantom-phoenix/backgrounds/landing/`
- `frontend/public/assets/phantom-phoenix/backgrounds/authentication/`
- `frontend/public/assets/phantom-phoenix/backgrounds/upload/`
- `frontend/public/assets/phantom-phoenix/backgrounds/results/`
- `frontend/public/assets/phantom-phoenix/backgrounds/dashboard/`

Listing after creation:

```
frontend/public/assets
frontend/public/assets/phantom-phoenix
frontend/public/assets/phantom-phoenix/README.md
frontend/public/assets/phantom-phoenix/backgrounds
frontend/public/assets/phantom-phoenix/backgrounds/authentication
frontend/public/assets/phantom-phoenix/backgrounds/dashboard
frontend/public/assets/phantom-phoenix/backgrounds/landing
frontend/public/assets/phantom-phoenix/backgrounds/results
frontend/public/assets/phantom-phoenix/backgrounds/upload
```

Only file under the asset root: `README.md`.

The README also names `brand/`, `phoenix/`, `illustrations/`, and `ui/`. Those were **not** created. They are out of scope for this task.

`frontend/public/assets/` is untracked. `frontend/.gitignore` does not ignore it. Root `.gitignore` does not ignore `frontend/public`. Directories can be committed later; they were not staged here.

Intended public URLs once files are copied (not wired in code yet):

- `/assets/phantom-phoenix/backgrounds/landing/landing-sunset-background.png`
- `/assets/phantom-phoenix/backgrounds/authentication/authentication-background.png`
- `/assets/phantom-phoenix/backgrounds/upload/upload-console-background.png`
- `/assets/phantom-phoenix/backgrounds/results/results-friendly-background.png`
- `/assets/phantom-phoenix/backgrounds/results/results-warning-background.png`
- `/assets/phantom-phoenix/backgrounds/dashboard/dashboard-background.png`

---

## 9. Six-image availability matrix

Searched the repo (excluding `node_modules`, `.venv`, `.git`) and the home directory (Downloads, Pictures, Desktop, `/tmp`). **No copies inside the repository.** Exactly one copy of each file, all in Downloads. Not in the intended destination. Not copied.

| File | In repo? | In destination? | Current path | Size | Dimensions | Mode | Copies |
|---|---|---|---|---|---|---|---|
| `landing-sunset-background.png` | No | No | `/home/hari007/Downloads/ww/landing-sunset-background.png` | 2,488,642 B | 1672×941 | RGB | 1 |
| `authentication-background.png` | No | No | `/home/hari007/Downloads/ww/authentication-background.png` | 2,415,830 B | 1672×941 | RGB | 1 |
| `upload-console-background.png` | No | No | `/home/hari007/Downloads/ww/upload-console-background.png` | 2,147,359 B | 1672×941 | RGB | 1 |
| `results-friendly-background.png` | No | No | `/home/hari007/Downloads/ww/results-friendly-background.png` | 2,808,265 B | 1672×941 | RGB | 1 |
| `results-warning-background.png` | No | No | `/home/hari007/Downloads/ww/results-warning-background.png` | 2,404,328 B | 1672×941 | RGB | 1 |
| `dashboard-background.png` | No | No | `/home/hari007/Downloads/ww/dashboard-background.png` | 2,730,045 B | 1672×941 | RGB | 1 |

Dimensions come from Pillow `Image.open` on those paths. They are **not** 1920×1080 (the size the asset README/manifest assumes for backdrops).

None of these filenames appear in `docs/PHOENIX_ASSET_MANIFEST.md` or in frontend source.

**Blocker for visual landing/upload/results/dashboard work:** Hari must approve copying these six files into the directories above. This audit did not copy them.

Authentication background has no screen to attach to until auth exists or Hari decides to drop that screen.

---

## 10. Existing tests and build results

Dependencies were already installed. No `npm install`. No lockfile edits.

| Check | Command | Result |
|---|---|---|
| Unit / E2E tests | none configured | **Not run.** No runner, no frontend tests. |
| Lint | `npm run lint` (`oxlint`) in `frontend/` | **Exit 0.** One warning: `src/App.tsx:22:7` `react(immutability)` — `loadHistory` is referenced from `useEffect` before its `const` initialization. Runtime order is actually safe today because the effect runs after render, but the rule is correct that the closure is fragile. |
| Typecheck | `npx tsc -b --pretty false` in `frontend/` | **Exit 0.** No diagnostics. |
| Production build | `npm run build` (`tsc -b && vite build`) | **Exit 0.** Vite 8.3.4. Output: `dist/index.html` 0.45 kB, `dist/assets/index-Ca-FY1Os.css` 11.14 kB, `dist/assets/index-CvB10-Ii.js` 241.78 kB (gzip 75.14 kB). Built in 605 ms. |

`frontend/dist/` is gitignored. Build refreshed existing dist artifacts. That is a generated output, not an application source change.

Backend pytest was **not** run. Database and API server were **not** started. No live upload was performed. "API-connected" means the source calls those endpoints, not that a scan succeeded during this audit.

---

## 11. Missing work and integration risks

### Must preserve

- POST `/api/scans` multipart field name `file`.
- Verdict vocabulary and the "not legal proof" disclaimer (footer and backend `not_claimed`).
- Evidence artifact images and PDF URL.
- Untracked user files: `rep/`, `opencode.json`, planning docs, datasets, model weights, `.env`.
- No fabricated heatmaps, statistics, or generator attribution.

### Missing pages / components

Landing, auth, dashboard (as its own view), upload preview, explainability panel, cursor pagination, health indicator, report archive, settings, admin, inventory, shared layout components, design tokens actually used by the UI, phoenix sprites (manifest says planned; do not generate them in the first slice).

### Missing assets

All six backgrounds (on disk in Downloads only). Entire manifest set (`phoenix-*.png`, badges, `landing-backdrop.png`, etc.) is absent. `brand/`, `phoenix/`, `illustrations/`, `ui/` directories do not exist.

### API gaps

Health not shown. Explainability not shown and has **no image artifact**. Pagination stopped at 20. Persist failure invisible. CORS locked to Vite dev origins. No auth.

### Accessibility / responsive (from source, not from a browser pass)

- Header does not collapse.
- File input is visually hidden (`opacity-0`) rather than a labeled control.
- No focus outlines beyond browser default (Tailwind preflight).
- Color is almost entirely white/neutral. Verdicts are not distinguishable by more than icon plus text (text is present, so not color-only).
- `index.html` title is `frontend`.
- Contrast of `text-neutral-500` on black was not measured.

### Build / config

Build is green. No test gate. `strict` TypeScript is off. `App.css` and template SVGs are leftover. Tailwind slate tokens disagree with the black UI.

### Breaking-change risks

- Splitting `App.tsx` into routes can drop scan state if it stays in component state. A scan id in the URL would match GET `/api/scans/{id}`.
- Changing list parsing to require a summary shape would break, because the API returns full results.
- Copying ~15 MB of PNGs into git will dominate the frontend. Confirm Git LFS vs normal commit before adding them.
- Redesign that drops `evidence_items` or the PDF link regresses the only working vertical slice.
- Pointing backgrounds at manifest filenames that do not exist would 404. Asset README forbids referencing missing files.

### Frontend work that depends on backend

| UI idea | Backend today |
|---|---|
| Auth screens | No. |
| Heatmap / attention image | Metrics only. `artifact` is null. |
| Generator attribution | Explicitly not claimed. |
| Saved evidence library | No resource. |
| Admin | No. |
| Live progress steps | Scan is one synchronous POST. |
| PDF library | PDF is generated per scan id, not stored as a list. |

---

## 12. Recommended implementation sequence

Adjusted from the suggested list to match this repo. Do not build disconnected mock pages.

1. **Asset decision (Hari).** Approve copy of the six PNGs into the directories in section 8, or supply different files. Do not reference them in code before the files are in `frontend/public`. Note 1672×941 vs 1920×1080.
2. **Do not start with a new landing page.** First protect the working slice: extract API calls from `App.tsx` into a small client that matches the real JSON (`result` wrapper vs bare scan, `error.message`, `next_cursor`). Add the oxlint `loadHistory` fix while touching that file. No visual rewrite required for this step.
3. **Shared shell only after the client is stable.** Tokens must replace the black-vs-slate split. Keep disclaimer and verdict labels.
4. **Landing** once `landing-sunset-background.png` is in tree. It should navigate into the existing upload flow, not replace it.
5. **Dashboard / archive.** Either restyle the existing archive or add a dashboard that links to it. Wire `next_cursor`. Use `dashboard-background.png` only after copy.
6. **Upload.** Keep current POST. Add preview and client-side 15 MiB / type checks that match the API. Background only after copy.
7. **Results.** Keep evidence cards and PDF. Render `explainability.metrics` only when `status === "available"`. Do not draw a fake heatmap. Choose friendly vs warning background from verdict label after files exist.
8. **Reports.** Keep the existing PDF link. A separate reports page is only a filter of scan history unless the API grows.
9. **Auth UI: skip.** No backend. `authentication-background.png` stays unused until a decision.
10. **Responsive / a11y pass** on the shell that already works.
11. **Then** add a real frontend test (none exist) and re-run `npm run lint`, `tsc -b`, and `npm run build`.

Phoenix sprite generation stays out of this sequence.

---

## 13. Proposed ownership and dependencies

| Work | Depends on | Suggested owner |
|---|---|---|
| Copy six PNGs into `frontend/public/assets/phantom-phoenix/backgrounds/...` | Hari approval. Files already in `~/Downloads/ww/`. | Hari or frontend after approval |
| API client extraction + pagination + explainability field | None. Backend already returns the data. | Frontend |
| Preserve upload → result → PDF → archive | Running API + Postgres (not required to compile UI) | Frontend, do not break |
| Landing / upload / results / dashboard visuals | Step "copy PNGs" | Frontend |
| Auth, inventory, admin, settings | New backend contracts | Backend first |
| Attention heatmap image | Detector change (`artifact` is null) | ML/backend, not UI fiction |
| CORS for non-localhost deploy | Backend `CORSMiddleware` | Backend when a real origin exists |
| Git history of large PNGs | Hari: commit vs LFS | Hari |
| This audit's untracked dirs | None | Leave unstaged until Hari asks |

---

## 14. Explicit blockers and questions for Hari

1. **Copy the six PNGs** from `/home/hari007/Downloads/ww/` into the new background folders? They are not in the repo. This audit did not copy them.
2. **Authentication screen:** build nothing (recommended; no API), or is auth a later backend project? The authentication background has no page.
3. **Is "dashboard" a new page or the existing Scan Archive?** Building both without a decision duplicates the only list endpoint.
4. **Asset names:** implementation plan/manifest use `landing-backdrop.png` / `upload-console.png` / `results-backdrop.png`. Supplied files use different names. Which set is canonical?
5. **Image size:** all six are 1672×941 RGB, not 1920×1080. Accept as-is?
6. **Large binaries in git:** about 15 MB total. Commit as normal blobs or use Git LFS?
7. **Stay on `feat/dataset-pipeline`** for frontend work, or cut a frontend branch later? This audit did not branch.
8. **Explainability UI:** show numeric attention metrics when present, or hide until a real artifact image exists?
9. **Deploy origin:** CORS allows only Vite localhost. Is production origin in scope now?
10. **`rep/` and `opencode.json`** are untracked. Confirm they must stay untracked and out of frontend commits.

---

## Verification legend

| Label | Meaning |
|---|---|
| Verified | Read from source, `git`, filesystem listing, Pillow, or a command exit code in this session. |
| Not run | Backend server, database, browser, pytest, live upload. |
| Unknown | Exact artifact path string produced by a real scan; whether `full_result` rows in the current database include `evidence_items`; visual contrast in a browser. |
