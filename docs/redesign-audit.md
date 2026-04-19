# Redesign Audit: P0 Baseline

Captured: 2026-04-19

This audit records the pre-redesign baseline for `docs/neumorphism_glass_2026_redesign_plan.md`.

## Static Baseline

| Check | Result |
| --- | ---: |
| `static/css/*.css` files | 34 |
| `static/css/*.css` total bytes | 671241 |
| `!important` lines in `static/css/styles_dark_mode.css` | 148 |
| `rgba(` or `backdrop-filter` matching lines under `static/css/` | 1785 |
| Visual baseline screenshots | 42 |

## Visual Baseline

The screenshot suite covers 7 pages x 3 viewports x 2 themes:

| Page | Route |
| --- | --- |
| welcome | `/` |
| workout-plan | `/workout_plan` |
| workout-log | `/workout_log` |
| weekly-summary | `/weekly_summary` |
| session-summary | `/session_summary` |
| progression | `/progression` |
| volume-splitter | `/volume_splitter` |

Viewports:

| Name | Size |
| --- | --- |
| mobile | 375 x 812 |
| tablet | 768 x 1024 |
| desktop | 1440 x 900 |

Themes: `light`, `dark`.

Screenshots are stored under `e2e/__screenshots__/visual.spec.ts-snapshots/`.

## Determinism Contract

- `e2e/visual.spec.ts` uses `e2e/strict-fixtures.ts`, not the legacy broad-error fixture.
- Browser state is frozen before navigation with `Date.now()` and no-argument `new Date()` fixed to `2026-04-18T09:00:00Z`.
- Locale is `en-US`, timezone is `UTC`, color scheme starts as `light`, default viewport is `1440 x 900`, and `deviceScaleFactor` is `1`.
- Chromium is launched with `--disable-font-subpixel-positioning` and `--force-color-profile=srgb`.
- Screenshot assertions use `maxDiffPixels: 0` and `threshold: 0`.
- Known volatile regions are masked: auto-backup banner, timestamp/data-volatile nodes, toast container, and animated GIFs.
- Screenshot-only CSS disables animations/transitions, hides carets/scrollbars, and neutralizes native/custom control antialiasing that drifted at strict zero tolerance.
- The navbar scale widget, toggle glyphs, and decorative active indicators are neutralized only inside the screenshot harness.

## Seed Database

Visual runs use a committed seed database:

| File | SHA-256 |
| --- | --- |
| `e2e/fixtures/database.visual.seed.db` | `C4755A592D020A770EB6B197795FC382CF8A41628701F149E2A0815EEEF727B0` |

`e2e/scripts/prepare_visual_db.py` copies that seed into `artifacts/visual/database.visual.db` before visual capture. `scripts/run-playwright.ps1` runs normal E2E specs first, then runs `e2e/visual.spec.ts` separately against a freshly prepared visual DB so mutating specs cannot dirty the screenshot baseline.

## Capture Environment

| Tool | Version |
| --- | --- |
| Playwright | 1.58.1 |
| Chromium | 145.0.7632.6 |
| OS | Microsoft Windows 11 Pro 10.0.26200, 64-bit |

## Validation

| Command | Result |
| --- | --- |
| `npm run build:css` | Passed; Sass emitted existing Bootstrap deprecation warnings |
| `npm run test:py` | 913 passed, 1 skipped |
| `npx playwright test e2e/visual.spec.ts --project=chromium` | 42 passed; repeated twice back-to-back with zero diff |
| `npm run test:e2e` | 314 non-visual tests passed, then 42 visual tests passed |

## Notes

- The baseline was initially unstable around animated GIFs, browser-native controls, and the navbar scale widget. Those are now handled in the screenshot harness without changing production CSS or templates.
- A helper bug in the early `addInitScript` path was caught by the strict page-error fixture and fixed before screenshots were accepted.
- Artifacts under `artifacts/` are generated output. The committed visual contract is the seed DB plus the 42 screenshots under `e2e/__screenshots__/`.
