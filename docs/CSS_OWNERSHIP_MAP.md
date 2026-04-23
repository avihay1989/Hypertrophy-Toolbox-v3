# CSS Ownership Map

Last updated: 2026-04-23

This document reflects the active CSS loading model after P10 cleanup.

## Current Loading Architecture

1. `templates/base.html` loads the 8 global application bundles directly.
2. Each page template adds exactly one route bundle through `{% block page_css %}`.
3. The steady-state app surface is 15 CSS files total: 8 global bundles plus 7 page bundles, excluding `bootstrap.custom.min.css`.
4. Legacy aggregate and per-feature source files from the P9 map are no longer part of the runtime loading graph.

## Always-Loaded Core CSS

These styles are linked directly from `templates/base.html` and should be treated as shared app-wide CSS:

| File | Ownership / purpose |
|------|----------------------|
| `bootstrap.custom.min.css` | Bootstrap build artifact |
| `tokens.css` | design tokens, spacing, and responsive scale variables |
| `motion.css` | shared animations and reduced-motion behavior |
| `base.css` | element defaults, app background, and baseline typography |
| `layout.css` | shared layout structure and responsive shell behavior |
| `components.css` | buttons, forms, tables, cards, modals, tooltips, toasts, and calm overlay primitives |
| `navbar.css` | global navbar layout and calm glass navbar presentation |
| `theme-dark.css` | dark-theme tokens and shared dark overrides |
| `a11y.css` | accessibility controls, scale system, focus fixes, and Firefox fallbacks |

## Page-Specific CSS Loading

The per-page loading strategy is implemented in the templates below.

| Template | Page-specific CSS |
|----------|-------------------|
| `welcome.html` | `pages-welcome.css` |
| `workout_plan.html` | `pages-workout-plan.css` |
| `workout_log.html` | `pages-workout-log.css` |
| `weekly_summary.html` | `pages-weekly-summary.css` |
| `session_summary.html` | `pages-session-summary.css` |
| `progression_plan.html` | `pages-progression.css` |
| `volume_splitter.html` | `pages-volume-splitter.css` |

## Active Bundle Responsibilities

The runtime CSS surface is organized around the target bundles below.

| File | Primary ownership |
|------|-------------------|
| `tokens.css` | responsive tokens, spacing scale, input/button/table sizes, and calm color tokens |
| `motion.css` | transitions, skeleton states, and motion preferences |
| `base.css` | body backdrop, shared text defaults, and fluid baseline typography |
| `layout.css` | containers, shell spacing, responsive tables, and grid/layout utilities |
| `components.css` | reusable interactive surfaces and component-level UI patterns |
| `navbar.css` | navigation layout, pills, dropdown presentation, and mobile navbar behavior |
| `theme-dark.css` | shared dark theme token overrides and dark component styling |
| `a11y.css` | UI scaling, focus states, and browser-specific accessibility fallbacks |
| `pages-welcome.css` | landing page presentation |
| `pages-workout-plan.css` | workout plan route-specific controls and views |
| `pages-workout-log.css` | workout log route-specific layouts and table behavior |
| `pages-weekly-summary.css` | weekly summary route visuals |
| `pages-session-summary.css` | session summary route visuals |
| `pages-progression.css` | progression route visuals |
| `pages-volume-splitter.css` | volume splitter route visuals |

## Maintenance Rules

1. Update this map when template CSS loading changes.
2. Add shared rules to an existing global bundle unless the behavior is route-specific.
3. Keep route-specific CSS inside the route bundle; do not reintroduce feature-level runtime files or aggregate `@import` chains.
4. Keep the runtime target at 15 app CSS files plus Bootstrap unless a reviewer explicitly approves a structural change.
