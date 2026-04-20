# CSS Ownership Map

Last updated: 2026-04-09

This document reflects the CSS that is actually loaded by the current templates.

## Current Loading Architecture

The app no longer relies on `static/css/styles.css` as its runtime entry point. The live loading model is:

1. `templates/base.html` loads the always-on core styles directly.
2. Each page template adds its own CSS through `{% block page_css %}`.
3. `static/css/styles.css` remains on disk as a legacy aggregate file, but it is not referenced by the current templates.

## Always-Loaded Core CSS

These styles are linked directly from `templates/base.html` and should be treated as shared app-wide CSS:

| File | Ownership / purpose |
|------|----------------------|
| `bootstrap.custom.min.css` | Bootstrap build |
| `styles_tokens.css` | design tokens and scaling variables |
| `styles_general.css` | base element defaults |
| `styles_utilities.css` | utility classes |
| `styles_layout.css` | shared layout structure |
| `styles_responsive.css` | shared responsive behavior |
| `styles_buttons.css` | shared button system |
| `styles_forms.css` | shared form styling |
| `styles_tables.css` | shared table styling |
| `responsive.css` | responsive table behaviors |
| `styles_cards.css` | shared card styling |
| `styles_navbar.css` | global navbar |
| `styles_notifications.css` | toast notifications |
| `styles_modals.css` | shared modal styling |
| `styles_tooltips.css` | tooltip styling |
| `styles_dark_mode.css` | dark-theme overrides |
| `styles_accessibility.css` | accessibility controls and scale system |
| `styles_error.css` | shared error presentation |

## Page-Specific CSS Loading

The per-page loading strategy is already implemented in the templates below.

| Template | Page-specific CSS |
|----------|-------------------|
| `welcome.html` | `styles_welcome.css` |
| `workout_plan.html` | `styles_filters.css`, `styles_dropdowns.css`, `styles_workout_dropdowns.css`, `styles_workout_plan.css`, `styles_frames.css`, `styles_routine_cascade.css`, `styles_muscle_selector.css` |
| `workout_log.html` | `workout_log.css`, `styles_frames.css` |
| `progression_plan.html` | `styles_progression.css`, `styles_dropdowns.css` |
| `session_summary.html` | `styles_volume.css`, `session_summary.css`, `styles_frames.css` |
| `weekly_summary.html` | `styles_volume.css`, `session_summary.css`, `styles_frames.css`, `styles_muscle_groups.css` |
| `volume_splitter.html` | `styles_volume_splitter.css`, `styles_volume.css`, `styles_muscle_groups.css` |
| `error.html` | `styles_error.css` |

## Shared Component Ownership

These files are not globally loaded from `base.html`, but they are the current source of truth for the named UI areas:

| File | Primary ownership |
|------|-------------------|
| `styles_filters.css` | workout-plan filter panel |
| `styles_dropdowns.css` | reusable dropdown styling |
| `styles_workout_dropdowns.css` | workout-plan and workout-log specific dropdown behavior |
| `styles_frames.css` | framed panels and card-like content shells |
| `styles_routine_cascade.css` | routine cascade control |
| `styles_muscle_selector.css` | body-map muscle selector |
| `styles_muscle_groups.css` | muscle group badges and labels |
| `styles_progression.css` | progression page |
| `styles_volume.css` | shared volume indicators, badges, classification colors, and legend text |
| `styles_volume_splitter.css` | volume splitter page |
| `styles_welcome.css` | landing page |
| `styles_workout_plan.css` | workout plan page |
| `workout_log.css` | workout log page |
| `session_summary.css` | summary-page-specific table fixes and dark-mode summary layout |
| `styles_science.css` | science/research content styling when used |

## Tier 1 Cleanup Status

The following stale files were removed in Tier 1:

| File | Status | Notes |
|------|--------|-------|
| `styles_action_buttons.css` | removed | merged into `styles_buttons.css`; the consolidation note remains in `styles_buttons.css` |
| `styles_chat.css` | removed | unreferenced in templates, JS, and active CSS imports |
| `volume_indicators.css` | removed | duplicate of classes already defined in `styles_volume.css` |

Important naming note:

- The user-facing label is **Excessive Volume**
- The shared CSS class name is still `.ultra-volume`

## Live Follow-Up Work

These items still remain outside the completed Tier 1 and Tier 5a cleanup:

- `styles.css` is still present as a legacy aggregate file and could be retired later if the team wants to remove unused build-era artifacts.

## Maintenance Rules

1. Update this map when template CSS loading changes.
2. Prefer documenting the live template loading model over the legacy aggregate file.
3. Do not mark CSS consolidation as complete unless the stale file is actually removed and template references stay clean.


## Phase 9/10 Target Map

**Target map (≤ 15 CSS files excluding Bootstrap: 8 global + 7 page bundles)**

> The prior ≤10 target was set before the route-scope contract split page CSS into per-route bundles. Preserving route scope is more important than hitting an arbitrary file count; 15 files is still a major improvement from 35.

*GLOBAL targets (linked in `base.html`):*

| Target file after P10 | Load scope | Sources / disposition |
|---|---|---|
| `tokens.css` | GLOBAL | existing `styles_tokens.css` (GLOBAL) + P2 `tokens.css` (GLOBAL) |
| `motion.css` | GLOBAL | P2 `motion.css` (GLOBAL, kept as its own target) |
| `base.css` | GLOBAL | `styles_general.css` (GLOBAL), `styles_utilities.css` (GLOBAL), plus any still-used unique rules from legacy `styles.css` (orphan — see P9i) |
| `layout.css` | GLOBAL | `styles_layout.css` (GLOBAL), `styles_responsive.css` (GLOBAL), `responsive.css` (GLOBAL). **`styles_frames.css` removed from this target** — it is PAGE-scoped (loaded in 4 templates) and belongs in page-level bundles. |
| `components.css` | GLOBAL | `styles_buttons.css` (GLOBAL), `styles_forms.css` (GLOBAL), `styles_tables.css` (GLOBAL), `styles_cards.css` (GLOBAL), `styles_tooltips.css` (GLOBAL), `styles_modals.css` (GLOBAL), `styles_notifications.css` (GLOBAL), `components-overlay.css` (GLOBAL). **`styles_dropdowns.css`, `styles_filters.css`, `styles_routine_cascade.css`, `styles_workout_dropdowns.css`, `styles_muscle_selector.css` removed from this target** — they are PAGE-scoped. |
| `navbar.css` | GLOBAL | `styles_navbar.css` (GLOBAL), `navbar-glass.css` (GLOBAL) |
| `theme-dark.css` | GLOBAL | `styles_dark_mode.css` (GLOBAL), `theme-dark-v2.css` (GLOBAL), plus any dark rules moved out of component/page files during consolidation |
| `a11y.css` | GLOBAL | `styles_accessibility.css` (GLOBAL), `styles_error.css` (GLOBAL) |
| `bootstrap.custom.min.css` | GLOBAL | Keep as Bootstrap build artifact; excluded from file count |

*PAGE-SCOPED targets (loaded via `{% block page_css %}` in child templates — one bundle per route):*

| Target file after P10 | Load scope | Route(s) | Current `{% block page_css %}` sources (verified against templates) |
|---|---|---|---|
| `pages-workout-plan.css` | PAGE | `/workout_plan` | `styles_filters.css`, `styles_dropdowns.css`, `styles_workout_dropdowns.css`, `styles_workout_plan.css`, `styles_frames.css`, `styles_routine_cascade.css`, `styles_muscle_selector.css` |
| `pages-workout-log.css` | PAGE | `/workout_log` | `workout_log.css`, `styles_frames.css` |
| `pages-weekly-summary.css` | PAGE | `/weekly_summary` | `styles_volume.css`, `session_summary.css`, `styles_frames.css`, `styles_muscle_groups.css` |
| `pages-session-summary.css` | PAGE | `/session_summary` | `styles_volume.css`, `session_summary.css`, `styles_frames.css` |
| `pages-welcome.css` | PAGE | `/` | `styles_welcome.css` |
| `pages-progression.css` | PAGE | `/progression` | `styles_progression.css`, `styles_dropdowns.css` |
| `pages-volume-splitter.css` | PAGE | `/volume_splitter` | `styles_volume_splitter.css`, `styles_volume.css`, `styles_muscle_groups.css` |

> **Note:** `styles_frames.css` (37,655 bytes) appears in three page bundles because it is loaded from 4 page templates today. `styles_volume.css` and `styles_muscle_groups.css` appear in multiple bundles for the same reason. Duplicating shared rules across bundles preserves the current route scope. During P9f, if the duplicated content is identical, it can be extracted into a shared page-level partial (e.g., `_frames-common.css`) included by each page bundle — but it must not become globally loaded without explicit reviewer approval.
>
> **Note:** `/weekly_summary` and `/session_summary` share `session_summary.css`, `styles_volume.css`, and `styles_frames.css`. They could share a single `pages-summary.css` bundle because they load nearly identical CSS today (`/weekly_summary` additionally loads `styles_muscle_groups.css`). However, separate bundles are safer and the implementer can merge them during P9f if a reviewer explicitly approves.
