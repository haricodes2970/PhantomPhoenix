# PHANTOM PHOENIX — Frontend Implementation Plan

This implementation plan outlines the rollout of the pixel-art UI/UX vision for PHANTOM PHOENIX, built on top of the existing React, TypeScript, Vite, and Tailwind frontend.

## Priority Order

1. **Design Tokens & Typography:** Establish pixel-art color palettes (deep slate navy, cyber accents, emerald/crimson status colors) and retro/clean monospace typography.
2. **Shared Navigation & Layout:** Responsive shell with retro branding, status bar, and tab navigation.
3. **Landing Page:** Immersive pixel-art hero introduction with system capabilities overview.
4. **Image Upload Workstation:** Drag-and-drop console supporting JPEG, PNG, WEBP with validation feedback.
5. **Results & Forensic Evidence Dashboard:** Display detector inference probabilities, metadata inspector, ELA, noise, and frequency visualization cards.
6. **Scan History View:** Paginated archive of previously persisted scans retrieved from PostgreSQL.
7. **PDF Report Downloader:** Direct link to generate and download ReportLab PDF forensic reports.
8. **Phoenix Mascot Integration:** Responsive mascot states reacting to scan progress and verdicts.
9. **Accessibility & Responsive Testing:** Ensuring mobile and desktop usability.

## Backend Dependencies

- Relies on existing API routes: `/api/health`, `/api/scans`, `/api/scans/{id}`, `/api/scans/{id}/report.pdf`, and `/api/artifacts/{path}`.
- No new backend endpoints or authentication systems are required for this frontend-focused milestone.
