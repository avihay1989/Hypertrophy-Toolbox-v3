# templates/ — Orientation

## Purpose
Server-rendered Jinja templates. Every user-facing page extends `base.html`; partials are prefixed with `_`.

## Key files
| File | Role |
|---|---|
| `base.html` | Master layout: navbar, 8 global CSS bundles, dark-mode toggle, body block |
| `welcome.html` | `/` landing |
| `workout_plan.html` | Plan builder + filter sidebar |
| `workout_log.html` | Log table + import-from-plan |
| `weekly_summary.html`, `session_summary.html` | Volume analyzers (Effective vs Raw) |
| `progression_plan.html` | Double-progression page + goals |
| `volume_splitter.html` | Slider-based weekly allocator |
| `user_profile.html` | Reference-lifts questionnaire + bodymap |
| `backup.html` | `/api/backups` UI |
| `error.html` | Generic error page |
| `_fatigue_badge.html` | Reusable fatigue partial included from summary pages |

## Conventions
- All pages start with `{% extends "base.html" %}`. Add nav links in `base.html` navbar block.
- **8 global CSS bundles** are loaded by `base.html`; **8 route bundles** are loaded by individual templates. Do **not** add new runtime `styles_*.css` files or per-feature `<link>` tags — extend the matching bundle.
- Use `{{ url_for('static', filename='...') }}` for asset URLs and `{{ url_for('blueprint.endpoint') }}` for route URLs.
- Load JS as ES6 modules: `<script type="module" src="{{ url_for('static', filename='js/modules/X.js') }}"></script>`.

## Gotchas
- Nav flow is canonical: Plan → Log → Analyze → Progress → Distribute. New pages slot into this order in `base.html`.
- Dark-mode classes are toggled by the shared dark-mode JS module + `theme-dark.css`. Do not add inline theme styling.
- API responses are normalized via `static/js/modules/fetch-wrapper.js` — don't roll your own JSON-shape handling in inline scripts.

## See also
- `.claude/rules/frontend.md` — bundle inventory, JS module pattern, SCSS build
- [docs/CSS_OWNERSHIP_MAP.md](../docs/CSS_OWNERSHIP_MAP.md) — which bundle owns which selectors
- `static/js/CLAUDE.md` — JS module orientation
