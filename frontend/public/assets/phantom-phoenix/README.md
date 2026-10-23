# PHANTOM PHOENIX — Asset Workspace

This directory contains the structured asset workspace for PHANTOM PHOENIX pixel-art UI/UX implementation.

## Directory Structure & Purpose

- `brand/`: Logo assets, wordmarks, and application iconography.
- `backgrounds/`: Screen-specific pixel art background scenes (landing, authentication, dashboard, upload workstation, results view).
- `phoenix/`: Phoenix mascot sprite sheets and emotional states (friendly, investigative, warning, animation frames).
- `illustrations/`: Feature illustrations for AI detection, metadata extraction, visual forensics (ELA, noise, frequency), and PDF reports.
- `ui/`: Inventory frames, badge components, status icons, and decorative pixel-art UI framing elements.

## Specifications & Guidelines

- **Formats:** PNG (lossless) for sprites/graphics; SVG for scalable icons.
- **Transparency:** All sprite sheets, logos, and UI inventory items must have transparent backgrounds.
- **Dimensions:** Designed on pixel grids (e.g. 16x16, 32x32, 64x64 for icons; 256x256+ for mascot sprites; 1920x1080 for backdrop scenes).
- **Referencing:** Components must reference assets via `/assets/phantom-phoenix/...`. No image file may be referenced before its actual file exists.
