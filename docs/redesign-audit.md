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
- Chromium is launched with `--disable-font-subpixel-positioning`, `--disable-gpu`, and `--force-color-profile=srgb`.
- Screenshot assertions use `maxDiffPixels: 0` and `threshold: 0`.
- Known volatile regions are masked: auto-backup banner, timestamp/data-volatile nodes, toast container, and animated GIFs.
- Screenshot-only CSS disables animations/transitions/backdrop filters, hides carets/scrollbars, and neutralizes native/custom control antialiasing that drifted at strict zero tolerance.
- The navbar scale widget, navbar/toggle glyphs, decorative active indicators, fixed dark canvas, and dark glass/card/table/header surfaces are neutralized only inside the screenshot harness.

## Seed Database

Visual runs use a committed seed database:

| File | SHA-256 |
| --- | --- |
| `e2e/fixtures/database.visual.seed.db` | `C4755A592D020A770EB6B197795FC382CF8A41628701F149E2A0815EEEF727B0` |

`e2e/scripts/prepare_visual_db.py` copies that seed into `artifacts/visual/database.visual.db` before visual capture. `scripts/run-playwright.ps1` runs normal E2E specs first, then runs `e2e/visual.spec.ts` separately against a freshly prepared visual DB so mutating specs cannot dirty the screenshot baseline.

## P9b Additive Base Bundle

Captured: 2026-04-22

- `static/css/base.css` is the additive consolidation target for `styles_general.css` and `styles_utilities.css`.
- `templates/base.html` links `base.css` after the legacy base stylesheets while keeping those legacy source links present.
- Scope remains GLOBAL only; no page-scoped CSS was moved into `base.css`.
- No legacy CSS files were unlinked or deleted in P9b.
- The visual baselines were refreshed after the post-bugfix UI state and screenshot-only harness stabilization. Production CSS and templates are not changed by the harness rules.

## P9c Additive Layout Bundle

Captured: 2026-04-22

- `static/css/layout.css` is the additive consolidation target for `styles_layout.css`, `styles_responsive.css`, and `responsive.css`.
- `layout.css` matches those three GLOBAL source files line-for-line with one blank separator between files: source sum 1,989 lines, target 1,991 lines (+0.10%).
- `styles_frames.css` remains PAGE-scoped and is not included in `layout.css`.
- `templates/base.html` links `layout.css` immediately after `styles_layout.css` and `styles_responsive.css`, while keeping all legacy source links present. `responsive.css` remains in its legacy position after `styles_tables.css` to preserve the existing table/component cascade during the additive period.
- No legacy CSS files were unlinked or deleted in P9c.
- The focused progression spec now uses `.first()` for non-unique suggestion-card goal-type assertions so duplicate valid suggestions do not trip Playwright strict mode.

## P9d Additive Components Bundle

Captured: 2026-04-22

- `static/css/components.css` is the additive consolidation target for the GLOBAL component sources: `styles_buttons.css`, `styles_forms.css`, `styles_tables.css`, `styles_cards.css`, `styles_notifications.css`, `styles_modals.css`, `styles_tooltips.css`, and `components-overlay.css`.
- `components.css` was generated from committed source content to avoid pulling unrelated dirty `components-overlay.css` working-tree changes into the checkpoint.
- `components.css` matches the committed source files line-for-line with one blank separator between files: source sum 4,547 lines, target 4,554 lines (+0.15%).
- PAGE-scoped files remain excluded: `styles_dropdowns.css`, `styles_filters.css`, `styles_routine_cascade.css`, `styles_workout_dropdowns.css`, `styles_muscle_selector.css`, `styles_frames.css`, `workout_log.css`, and volume/page CSS.
- `templates/base.html` links `components.css` additively immediately after `styles_tables.css` and before `responsive.css`. This keeps `responsive.css` and the remaining legacy component links in their existing final cascade positions during the additive period.
- No legacy CSS files were unlinked or deleted in P9d.

## P9e Additive Navbar Bundle

Captured: 2026-04-22

- `static/css/navbar.css` is the additive consolidation target for the GLOBAL navbar sources: `styles_navbar.css` and `navbar-glass.css`.
- `navbar.css` matches those two source files line-for-line with one blank separator between files: source sum 1,428 lines, target 1,429 lines (+0.07%).
- `templates/base.html` links `navbar.css` additively immediately after `styles_navbar.css`. The legacy `navbar-glass.css` source link remains in the redesign overlay block after `motion.css`, preserving the overlay's existing final cascade position during the additive period.
- No legacy CSS files were unlinked or deleted in P9e.

## P9f Additive Workout Plan Page Bundle

Captured: 2026-04-22

- `static/css/pages-workout-plan.css` is the additive route-scoped consolidation target for `/workout_plan`.
- The bundle source list exactly matches the current `templates/workout_plan.html` page CSS block: `styles_filters.css`, `styles_dropdowns.css`, `styles_workout_dropdowns.css`, `styles_workout_plan.css`, `styles_frames.css`, `styles_routine_cascade.css`, and `styles_muscle_selector.css`.
- `pages-workout-plan.css` matches those seven source files line-for-line with one blank separator between files: source sum 7,987 lines, target 7,993 lines (+0.08%).
- `templates/workout_plan.html` links `pages-workout-plan.css` additively after the legacy page CSS links. No legacy page CSS links or files were unlinked or deleted.
- Route scope remains `/workout_plan` only; no PAGE-scoped file was moved to a GLOBAL link.

## P9f Additive Workout Log Page Bundle

Captured: 2026-04-22

- `static/css/pages-workout-log.css` is the additive route-scoped consolidation target for `/workout_log`.
- The bundle source list exactly matches the current `templates/workout_log.html` page CSS block before the additive bundle link: `workout_log.css` and `styles_frames.css`.
- `pages-workout-log.css` matches those two current source files line-for-line with one blank separator between files: source sum 3,335 lines, target 3,336 lines (+0.03%).
- `templates/workout_log.html` links `pages-workout-log.css` additively after the legacy page CSS links. No legacy page CSS links or files were unlinked or deleted.
- Route scope remains `/workout_log` only; no PAGE-scoped file was moved to a GLOBAL link.

## P9f Additive Weekly Summary Page Bundle

Captured: 2026-04-22

- `static/css/pages-weekly-summary.css` is the additive route-scoped consolidation target for `/weekly_summary`.
- The bundle source list exactly matches the current `templates/weekly_summary.html` page CSS block before the additive bundle link: `styles_volume.css`, `session_summary.css`, `styles_frames.css`, and `styles_muscle_groups.css`.
- `pages-weekly-summary.css` matches those four current source files line-for-line with one blank separator between files: source sum 1,672 lines, target 1,675 lines (+0.18%).
- `templates/weekly_summary.html` links `pages-weekly-summary.css` additively after the legacy page CSS links. No legacy page CSS links or files were unlinked or deleted.
- Route scope remains `/weekly_summary` only; no PAGE-scoped file was moved to a GLOBAL link.

## P9f Additive Session Summary Page Bundle

Captured: 2026-04-22

- `static/css/pages-session-summary.css` is the additive route-scoped consolidation target for `/session_summary`.
- The bundle source list exactly matches the current `templates/session_summary.html` page CSS block before the additive bundle link: `styles_volume.css`, `session_summary.css`, and `styles_frames.css`.
- `pages-session-summary.css` matches those three current source files line-for-line with one blank separator between files: source sum 1,624 lines, target 1,626 lines (+0.12%).
- `templates/session_summary.html` links `pages-session-summary.css` additively after the legacy page CSS links. No legacy page CSS links or files were unlinked or deleted.
- Route scope remains `/session_summary` only; no PAGE-scoped file was moved to a GLOBAL link.

## P9f Additive Welcome Page Bundle

Captured: 2026-04-22

- `static/css/pages-welcome.css` is the additive route-scoped consolidation target for `/`.
- The bundle source list exactly matches the current `templates/welcome.html` page CSS block before the additive bundle link: `styles_welcome.css`.
- `pages-welcome.css` matches that current source file line-for-line: source sum 1,082 lines, target 1,082 lines (+0.00%).
- `templates/welcome.html` links `pages-welcome.css` additively after the legacy page CSS link. No legacy page CSS links or files were unlinked or deleted.
- Route scope remains `/` only; no PAGE-scoped file was moved to a GLOBAL link.

## P9f Additive Progression Page Bundle

Captured: 2026-04-22

- `static/css/pages-progression.css` is the additive route-scoped consolidation target for `/progression`.
- The bundle source list exactly matches the current `templates/progression_plan.html` page CSS block before the additive bundle link: `styles_progression.css` and `styles_dropdowns.css`. The external Flatpickr stylesheet remains linked separately and is not bundled.
- `pages-progression.css` matches those two current source files line-for-line with one blank separator between files: source sum 365 lines, target 366 lines (+0.27%).
- `templates/progression_plan.html` links `pages-progression.css` additively at the end of the page CSS block. No legacy page CSS links or files were unlinked or deleted.
- Route scope remains `/progression` only; no PAGE-scoped file was moved to a GLOBAL link.

## P9f Additive Volume Splitter Page Bundle

Captured: 2026-04-23

- `static/css/pages-volume-splitter.css` is the additive route-scoped consolidation target for `/volume_splitter`.
- The bundle source list exactly matches the current `templates/volume_splitter.html` page CSS block before the additive bundle link: `styles_volume_splitter.css`, `styles_volume.css`, and `styles_muscle_groups.css`.
- `pages-volume-splitter.css` matches those three current source files line-for-line with one blank separator between files: source sum 1,112 lines, target 1,114 lines (+0.18%).
- `templates/volume_splitter.html` links `pages-volume-splitter.css` additively at the end of the page CSS block. No legacy page CSS links or files were unlinked or deleted.
- Route scope remains `/volume_splitter` only; no PAGE-scoped file was moved to a GLOBAL link.

## Capture Environment

| Tool | Version |
| --- | --- |
| Playwright | 1.58.1 |
| Chromium | 145.0.7632.6 |
| OS | Microsoft Windows 11 Pro 10.0.26200, 64-bit |

## Validation

| Command | Result |
| --- | --- |
| `npm run build:css` | Passed after P9f volume-splitter page bundle; Sass emitted existing Bootstrap deprecation warnings |
| `npm run test:py` | 913 passed, 1 skipped after P9f volume-splitter page bundle |
| Selector audit commands from §3.0 | Passed after P9f volume-splitter template touch: 248 ID hits, 228 selector hits, 40 `data-testid` hits, 597 Playwright locator hits reviewed for no affected selector rename/removal |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/progression.spec.ts --project=chromium` | 25 passed after P9f progression bundle |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/workout-plan.spec.ts --project=chromium` | 17 passed after P9f workout-plan bundle |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/workout-log.spec.ts --project=chromium` | 19 passed after P9f workout-log bundle; rerun also passed after an unrelated full-suite workout-log visibility timeout during P9f welcome validation |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/volume-splitter.spec.ts --project=chromium` | 27 passed after P9f volume-splitter bundle |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/smoke-navigation.spec.ts --project=chromium` | 10 passed after P9f volume-splitter bundle |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/summary-pages.spec.ts --project=chromium` | 20 passed after P9f session-summary bundle |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/nav-dropdown.spec.ts --project=chromium` | 6 passed after adding Bootstrap `shown.bs.modal` / `hidden.bs.modal` waits around Program Library close assertions |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/visual.spec.ts --project=chromium` | 42 passed after P9f volume-splitter page bundle; no snapshot refresh needed |
| `npm run test:e2e` | Passed after P9f volume-splitter page bundle: 320 non-visual tests passed, then 42 visual tests passed |

## Notes

- The baseline was initially unstable around animated GIFs, browser-native controls, and the navbar scale widget. Those are now handled in the screenshot harness without changing production CSS or templates.
- A helper bug in the early `addInitScript` path was caught by the strict page-error fixture and fixed before screenshots were accepted.
- Playwright web-server output still includes intermittent Windows log rollover `PermissionError` noise for `logs/app.log`, but the affected validation commands exit successfully.
- Artifacts under `artifacts/` are generated output. The committed visual contract is the seed DB plus the 42 screenshots under `e2e/__screenshots__/`.
- The nav dropdown route-loop test now waits for Bootstrap modal shown/hidden events so it does not click the Program Library close button while the show transition is still in progress.
- During P9f welcome validation, the first full E2E run hit one unrelated `workout-log.spec.ts` weight-input visibility timeout. The focused workout-log rerun passed 19/19, and the full `npm run test:e2e` rerun passed.
