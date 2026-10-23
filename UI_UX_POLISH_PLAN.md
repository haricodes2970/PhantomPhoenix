# UI/UX Polish Sprint — Implementation Plan

## Current State Analysis
- Single-file React app (App.tsx ~74k chars) with hash routing
- Types well-defined in types.ts
- Background images per view (landing, auth, upload, dashboard, results-friendly/warning)
- PhoenixMascot SVG with state-driven animations
- Results view currently renders raw JSON via `JSON.stringify(ev.result, null, 2)`
- All API contracts understood from types.ts

## Phase 1: Shared Design System (Week 1 - Foundation)

### 1.1 Create reusable component library
```
frontend/src/components/
├── ui/
│   ├── Button.tsx           # Primary, secondary, ghost, danger variants
│   ├── Card.tsx             # Consistent card wrapper
│   ├── Badge.tsx            # Verdict, risk, status badges
│   ├── Input.tsx            # Form input with label, error, help text
│   ├── Select.tsx           # Filter/sort dropdowns
│   ├── Table.tsx            # Sortable, paginated data table
│   ├── Collapsible.tsx      # Technical details disclosure
│   ├── Toast.tsx            # Non-blocking notifications
│   ├── Spinner.tsx          # Loading states
│   └── Icon.tsx             # Lucide wrapper with consistent sizing
├── layout/
│   ├── Header.tsx           # Navigation, auth state, phoenix logo
│   ├── Footer.tsx           # Disclaimer
│   └── PageLayout.tsx       # Consistent page container
├── phoenix/
│   └── PhoenixMascot.tsx    # Extracted from App.tsx
├── results/
│   ├── CaseHeader.tsx       # Scan ID, filename, metadata, download
│   ├── AssessmentSummary.tsx # Verdict, risk, model score, rationale
│   ├── EvidenceCard.tsx     # Formatted evidence with interpretation
│   ├── ArtifactViewer.tsx   # ELA/Noise/FFT with captions
│   ├── MetadataTable.tsx    # Key-value EXIF/XMP display
│   ├── ModelDetails.tsx     # Technical model info
│   ├── Explainability.tsx   # Attention rollout or unavailable
│   ├── TechnicalDetails.tsx # Collapsible raw JSON
│   └── ResultsView.tsx      # Orchestrates all above
├── upload/
│   ├── DropZone.tsx         # Drag-drop, preview, validation
│   ├── UploadProgress.tsx   # Progress bar, status
│   └── UploadView.tsx
├── dashboard/
│   ├── StatsCard.tsx        # Summary counts
│   ├── RecentScans.tsx      # List with links
│   └── DashboardView.tsx
├── archive/
│   ├── ScanTable.tsx        # Sortable, filterable, paginated
│   └── ArchiveView.tsx
└── auth/
    ├── LoginForm.tsx        # Refined sign-in
    └── AuthGuard.tsx        # Route protection
```

### 1.2 Design tokens (extend index.css)
- Consistent spacing scale (already in CSS vars)
- Typography scale (already in CSS vars)
- Color palette refinement (midnight navy, charcoal, muted blue, cyan, amber)
- Focus rings, transitions, reduced-motion support

### 1.3 Navigation & Layout
- Sticky header with: Phoenix logo (small), nav links, auth state chip
- Active route indication
- Responsive breakpoints: mobile (< 640), tablet (640-1024), desktop (> 1024)

## Phase 2: Results Page Redesign (Highest Priority)

### 2.1 CaseHeader
- Scan ID, filename, timestamp, dimensions, format, SHA-256 (copyable)
- Primary CTA: Download PDF Report
- Secondary: New Scan
- Verdict & Risk badges inline

### 2.2 AssessmentSummary
- Large verdict display with color coding
- Risk level badge
- Model fake probability as percentage with clear label
- Rationale list (from `verdict.rationale`)
- "Explicitly Not Claimed" section (from `verdict.not_claimed`)

### 2.3 EvidenceCard (replaces raw JSON)
- Evidence ID + category badge
- Method label
- Human-readable interpretation (from `ev.interpretation`)
- Key metrics extracted from `ev.result` as formatted key-value pairs
- Limitations array as muted footnotes
- No raw JSON in primary view

### 2.4 ArtifactViewer
- Title, method, limitations caption
- Responsive image with fallback
- ELA: "Error Level Analysis — highlights compression inconsistencies"
- Noise: "Wavelet Noise Residuals — reveals sensor-pattern anomalies"
- FFT: "2D Frequency Spectrum — detects periodic artifacts"

### 2.5 MetadataTable
- Group EXIF/XMP fields logically (Camera, Exposure, GPS, Software, Timestamps)
- Hide empty/unknown fields by default
- "Show all" toggle for completeness

### 2.6 TechnicalDetails (collapsible)
- Raw scan result JSON for debugging/research
- Default collapsed, labeled "Advanced / Raw Payload"

## Phase 3: Upload Redesign

### 3.1 DropZone
- Visual drag-over state
- File preview thumbnail
- Size/type validation with clear messages (from config)
- Remove/retry actions
- "What happens next" explanation

### 3.2 UploadProgress
- Indeterminate → determinate when possible
- Step indicators: Uploading → Queued → Analyzing → Complete
- Cancel option (if feasible)

## Phase 4: Dashboard & Archive Polish

### 4.1 Dashboard
- Stats cards: Total scans, Likely AI, Likely Real, Inconclusive (from API)
- Recent scans table (top 5) with quick links
- Empty state: "No scans yet — start your first investigation"
- Loading skeleton

### 4.2 Archive
- Full-width table: Filename, Date, Verdict, Risk, SHA-256 (truncated)
- Filters: Verdict (All/AI/Real/Inconclusive/Failed), Date range
- Sortable columns
- Pagination or infinite scroll
- Row click → navigate to results

## Phase 5: Landing & Sign-In Polish

### 5.1 Landing
- Hero: Product name, tagline, workflow steps (4-5)
- Primary CTA: Start Investigation → #upload
- Secondary: View Archive → #history
- Capability list with icons
- Phoenix mascot (idle or investigating)

### 5.2 Sign-In
- Compact centered panel on auth background
- Improved labels, focus states, loading spinner
- Generic error message (no account enumeration)
- Rate-limit feedback with Retry-After
- Disabled states during submission

## Phase 6: Accessibility & Responsive Audit

- Semantic HTML (main, section, article, header, footer, nav)
- ARIA labels on icon-only buttons
- Focus visible outlines
- Color contrast (WCAG AA minimum)
- Reduced motion: disable phoenix animations, transitions
- Keyboard navigation: tab order, skip links
- Screen reader: verdict announced, loading states

## Phase 7: Verification Gates

1. `npm run lint` — no new errors
2. `npm run build` — production build succeeds
3. `npx playwright test` — smoke tests pass
4. `docker compose config` — valid
5. `git diff --check` — clean

## Dependencies
- No new dependencies unless absolutely justified
- Reuse: lucide-react, react (hooks), tailwind
- Avoid: motion, GSAP, heavy animation libs

## Risk Mitigation
- Work in branches/components, not overwriting App.tsx directly
- Test each view against real API responses
- Keep hash routing intact
- Preserve auth flow exactly