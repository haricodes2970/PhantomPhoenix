# PHANTOM PHOENIX — Screenshot Index

Captured 2026-10-18 against the **real running stack** at `https://127.0.0.1:8443/` (self-signed TLS, project `pp13`), via headless Chromium (Playwright), viewport 1280×800. All screenshots are of the actual running application — no mockups. Login credentials are never displayed in any screenshot.

| File | Page / state | Demonstrates | Suitable for research paper |
|---|---|---|---|
| `01-landing.png` | Landing (#landing) | branded hero, phoenix crest, feature framing, gated "Investigator Dashboard" CTA | YES — front/overview shot |
| `02-login.png` | Sign-in (#login) | clean auth screen, empty form, generic labelling | YES — auth/UX section |
| `03-dashboard.png` | Investigator Dashboard (after real login) | authenticated workspace shell | YES — system overview |
| `04-upload.png` | Upload view with real image staged | file thumbnail preview, submit control, from `datasets/real/real_000002.jpg` | YES — workflow step |
| `05-results-overview.png` | Results after real detector inference | verdict band, forensic score, high-level findings (real, no mock data) | YES — core deliverable |
| `06-metadata-evidence.png` | scrolled results — metadata + evidence | media metadata and structured evidence records | YES — evidence section |
| `07-forensic-artifacts.png` | scrolled results — forensic artifacts | ELA/FFT/noise-style forensic imagery (served from `/api/artifacts/...`); NOT claimed as Grad-CAM (method not confirmed as grad-cam) | YES with the caveat as written |
| `08-archive.png` | Archive (#history) | list of scans from `/api/scans` real data | YES — case management |
| `09-pdf-report.png` | results page, PDF download affordance + verified download | **the PDF itself was verified (200 OK, 400,650 bytes, `%PDF-1.4`)**; the screenshot shows the results view with the download control — the `.pdf` itself is not rendered in-browser in headless Chromium | partial; supplement with the real PDF file if paper needs the PDF page layout |

All files exist and are non-empty (sizes verified at capture time, 161 KB–621 KB).

### Honest notes
- Run 1 produced a crash-on-parser-error screenshot `99-fatal.png` (test-script selector bug, not an app bug); it was superseded by the run-2 captures above and is not shipped in this directory.
- `07-forensic-artifacts.png` shows the artifacts the backend actually serves; per rules, we do **not** label it "Grad-CAM" — the generation method is whatever the backend produced (ELA/FFT/noise-compression style derived imagery served from `/api/artifacts/`), which mirrors what these screenshots show.
- `09-pdf-report.png` pairs with the actual generated PDF we captured and verified (kept at `/tmp/opencode/verify_report.pdf`, intentionally not copied into the repo to avoid carrying user-scan artifacts into tracked files).
- No passwords, tokens, cookies, private data or unrelated personal information is visible in any screenshot (log-in screens show empty forms; no browser dev-tools open during capture).
