---
paths:
  - "templates/**/*.html"
  - "static/**/*.js"
  - "static/**/*.css"
  - "scss/**/*.scss"
---

# Frontend guide

## CSS structure
- Runtime CSS is capped at 16 app bundles: 8 global bundles in `templates/base.html` plus 8 route bundles loaded from child templates.
- Global bundles: `tokens.css`, `motion.css`, `base.css`, `layout.css`, `components.css`, `navbar.css`, `theme-dark.css`, `a11y.css`.
- Route bundles: `pages-welcome.css`, `pages-workout-plan.css`, `pages-workout-log.css`, `pages-weekly-summary.css`, `pages-session-summary.css`, `pages-progression.css`, `pages-volume-splitter.css`, `pages-user-profile.css`.
- `bootstrap.custom.min.css` stays separate as the Bootstrap build artifact and is excluded from the 15-file target.
- Do not add new runtime `styles_*.css` files or new direct `<link>` tags for feature CSS in templates. Extend the appropriate global bundle or the matching route bundle instead.

## Adding a JS module + CSS
- Create `static/js/modules/myfeature.js` as ES6 module.
- Import in template:
  ```html
  <script type="module" src="{{ url_for('static', filename='js/modules/myfeature.js') }}"></script>
  ```
- Use `import { apiFetch } from './fetch-wrapper.js'` or `import { api } from './fetch-wrapper.js'` for API calls.
- Use `import { showToast } from './toast.js'` for notifications.
- If the feature needs styling, add it to the appropriate existing bundle instead of creating a new runtime CSS file.

## SCSS / Bootstrap
- Edit `scss/custom-bootstrap.scss`.
- Run `npm run build:css` (one-off) or `npm run watch:css` (watch mode).
- Built output: `static/css/` (check `package.json` for exact target).

## Templates
- All user-facing templates extend `{% extends "base.html" %}`.
- Add nav links in `templates/base.html` navbar.
- Nav flows: Plan (`/workout_plan`) → Log (`/workout_log`) → Analyze (`/weekly_summary`, `/session_summary`) → Progress (`/progression`) → Distribute (`/volume_splitter`).

## API response shape (for JS consumers)
Routes return `{"ok": true, "status": "success", "data": ...}` on success, `{"ok": false, "status": "error", "message": ..., "error": {...}}` on error. The `apiFetch` wrapper and `api` convenience object in `fetch-wrapper.js` normalize this — prefer them over raw `fetch()`.

## Dark mode
Toggle via `localStorage`; persists across pages. Shared dark styling lives in `theme-dark.css`, and the behavior is in the shared dark-mode module — look for `dark-mode` references in `static/js/modules/` before adding new theme code.
