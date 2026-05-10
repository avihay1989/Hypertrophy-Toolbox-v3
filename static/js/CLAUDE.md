# static/js/ — Orientation

## Purpose
Vanilla ES6 modules, no framework. `modules/` holds feature-scoped modules; the flat files are page-level entry points or shared utilities.

## Key files
| File | Role |
|---|---|
| `app.js` | Top-level entry hooked from `base.html` |
| `darkMode.js` | Theme toggle + `localStorage` persistence |
| `accessibility.js` | Skip-links, keyboard helpers |
| `populateRoutines.js` | Routine cascade entry |
| `table-responsiveness.js` | Mobile table re-layout |
| `modules/fetch-wrapper.js` | **API client.** Exports `apiFetch` (low-level) and `api` (convenience) |
| `modules/toast.js` | `showToast()` notifications |
| `modules/navbar.js`, `modules/navbar-enhancements.js` | Nav UI |
| `modules/workout-plan.js`, `modules/workout-plan-events.js`, `modules/workout-dropdowns.js`, `modules/exercises.js`, `modules/filters.js`, `modules/filter-view-mode.js`, `modules/routine-cascade.js` | Plan-builder pieces |
| `modules/workout-log.js` | Log page |
| `modules/summary.js`, `modules/charts.js` | Weekly/session analyzers |
| `modules/progression-plan.js` | Progression page |
| `modules/volume-splitter.js`, `modules/plan_volume_panel.js` | Distribute |
| `modules/user-profile.js`, `modules/bodymap-svg.js`, `modules/muscle-selector.js` | Profile + body map |
| `modules/program-backup.js`, `modules/backup-center.js` | Backups |
| `modules/exports.js`, `modules/validation.js`, `modules/ui-handlers.js`, `modules/workout-controls-animation.js` | Cross-cutting |

## Conventions
- All JSON calls go through `apiFetch` / `api` from `fetch-wrapper.js` — they normalize the `{ok, status, data, error}` shape and unify error handling. Do **not** call raw `fetch()` for app endpoints.
- User-facing notifications via `showToast()` from `toast.js`.
- Modules are loaded with `<script type="module">` from templates; export named symbols, not defaults.
- Dark-mode behavior is centralized — search `dark-mode` references before adding new theme code.

## Gotchas
- New CSS belongs in an existing global or route bundle (`.claude/rules/frontend.md`), not a new `styles_*.css`.
- The `static/bodymaps/GPT/` directory is gitignored scratch — don't commit reference output there.

## See also
- `.claude/rules/frontend.md` — bundle ownership, SCSS build
- `templates/CLAUDE.md` — which template loads which module
