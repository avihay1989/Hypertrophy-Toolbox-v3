---
paths:
  - "templates/**/*.html"
  - "static/**/*.js"
  - "static/**/*.css"
  - "scss/**/*.scss"
---

# Frontend guide

## Adding a JS module + CSS
- Create `static/js/modules/myfeature.js` as ES6 module.
- Import in template:
  ```html
  <script type="module" src="{{ url_for('static', filename='js/modules/myfeature.js') }}"></script>
  ```
- Use `import { apiCall } from './fetch-wrapper.js'` for API calls.
- Use `import { showToast } from './toast.js'` for notifications.
- Add CSS file at `static/css/styles_myfeature.css`; link in `templates/base.html` `<head>`.

## SCSS / Bootstrap
- Edit `scss/custom-bootstrap.scss`.
- Run `npm run build:css` (one-off) or `npm run watch:css` (watch mode).
- Built output: `static/css/` (check `package.json` for exact target).

## Templates
- All user-facing templates extend `{% extends "base.html" %}`.
- Add nav links in `templates/base.html` navbar.
- Nav flows: Plan (`/workout_plan`) → Log (`/workout_log`) → Analyze (`/weekly_summary`, `/session_summary`) → Progress (`/progression`) → Distribute (`/volume_splitter`).

## API response shape (for JS consumers)
Routes return `{"ok": true, "status": "success", "data": ...}` on success, `{"ok": false, "status": "error", "message": ..., "error": {...}}` on error. The `apiCall` wrapper in `fetch-wrapper.js` normalizes this — prefer it over raw `fetch()`.

## Dark mode
Toggle via `localStorage`; persists across pages. Implementation is in a shared module — look for `dark-mode` references in `static/js/modules/` before adding new theme code.
