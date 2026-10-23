# PHANTOM PHOENIX Report QA

**Generated:** 2026-10-23  
**Deliverables:** `PhantomReport.docx`, `PhantomReport.pdf`

## Source-template inspection

All eight supplied source files were inspected without modification:

1. `1.TITLE SHEET and Cover Page.docx`
2. `2.CERTIFICATE.docx`
3. `3.DECLARATION.docx`
4. `4.ACKNOWLEDGEMENT.docx`
5. `5.ABSTRACT.docx`
6. `6. CONTENT.docx`
7. `7.REPORT.doc`
8. `8.REFERENCES.docx`

The legacy `.doc` was converted only to `/tmp/opencode/phantom-inspect/7.REPORT.docx` for inspection. Institutional logo/image assets were extracted to the same temporary inspection directory. Original templates remain in place.

## Document validation

- One continuous editable DOCX generated.
- DOCX reopened with `python-docx`: 227 paragraphs, 15 tables, 12 embedded images, 1 section.
- Required front matter present: title, certificate, declaration, acknowledgement, abstract, contents placeholder, lists, nomenclature.
- Chapters 1–8, references and Appendix A present.
- Placeholder/sample-content scan found no `<TNR`, `Author1`, `wireless`, `NAME1`, or `TITLE` remnants.
- LibreOffice PDF conversion succeeded.
- PDF metadata verified with `pdfinfo`; page count: **30**; unencrypted; no JavaScript.
- PDF text extraction verified chapter openings, references and appendix.
- Representative PDF pages rendered to PNG for visual inspection in `/tmp/opencode/phantom-inspect/pdf-pages/`.

## Technical verification

- Fresh backend test run: **206 passed, 11 skipped, 14 warnings**.
- Skips are environment/optional-flag dependent tests, primarily database/E2E paths.
- Fresh frontend production build: **exit 0**; TypeScript build and Vite build completed; 1,920 modules transformed.
- Existing repository evidence additionally documents live authenticated workflow, real upload, real detector inference, forensic artifact retrieval, archive rendering and PDF download.

## Evidence and metrics sources

- Detector/model implementation: `backend/detector.py`.
- Forensic pipeline: `backend/forensics/`, `backend/forensics/runner.py`.
- Aggregation/verdict: `backend/aggregator.py`, `backend/verdict.py`.
- API and routes: `backend/main.py`.
- Persistence: `backend/models.py`, Alembic migrations.
- Baseline metrics: `datasets/manifests/experiment_baseline_eval/evaluation_summary.json` and `docs/BASELINE_EVALUATION_REPORT.md`.
- Calibration metrics: `datasets/manifests/experiment_threshold_calibration/calibration_summary.json` and `docs/THRESHOLD_CALIBRATION_REPORT.md`.
- Release/test record: `docs/PHASE_2_6_RELEASE_VALIDATION.md`, `report assists/TEST_RESULTS.md`.
- Dataset/protocol caveats: `datasets/manifests/`, `docs/` evaluation reports.

## Screenshot inventory

All screenshots are existing captures indexed by `report assists/SCREENSHOT_INDEX.md`, recorded as actual running-stack captures at `https://127.0.0.1:8443/` using headless Chromium at 1280×800:

- `01-landing.png` — landing page.
- `02-login.png` — sign-in page (not embedded in final report; available in source evidence directory).
- `03-dashboard.png` — authenticated dashboard.
- `04-upload.png` — upload view with `datasets/real/real_000002.jpg` staged.
- `05-results-overview.png` — real detector result.
- `06-metadata-evidence.png` — metadata/evidence cards.
- `07-forensic-artifacts.png` — forensic artifacts; caption deliberately does not call this Grad-CAM.
- `08-archive.png` — scan history.
- `09-pdf-report.png` — PDF download affordance; actual PDF response was separately verified.

## Missing institutional details requiring human completion

- Student USNs.
- Guide name, designation and credentials.
- Academic year.
- Approval dates and place fields.
- Student signatures.
- Examiner names and signatures.
- Final verification of principal/HOD wording and designations.
- Institutional approval/certificate dates.

These are marked `TO BE COMPLETED` in administrative pages. No official identity, signature, approval or date was fabricated.

## Known limitations

- Report uses editable heading structure; Word/LibreOffice may require updating the table of contents field after final pagination edits.
- Current output uses the generated report’s Letter page geometry; confirm department-specific paper-size requirement before submission.
- Baseline metrics come from explicit repository evaluation manifests and are not universal performance claims.
- Generator attribution, source discovery, publisher intelligence, external investigation evidence, video/audio analysis and C2PA verification are not claimed as implemented.
- Exact minimum deployment hardware, production throughput and retention policy remain unmeasured or institution-dependent.
- Final human review is required for administrative fields, signatures, institutional wording and submission formatting.
