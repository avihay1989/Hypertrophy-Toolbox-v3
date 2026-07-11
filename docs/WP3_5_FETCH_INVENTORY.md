# WP3.5 raw-fetch inventory

This is the repository-wide before/after inventory for WP3.5. It covers tracked
files under `static/`, `templates/`, `tests/`, and `e2e/` after the WP3.2 inline
script extraction and WP3.4 workout-plan split. The inventory command was:

```powershell
git grep -n -E "\bfetch[[:space:]]*\(" -- static templates tests e2e
```

Two textual mentions (`static/js/CLAUDE.md` and a comment in
`workout-plan-state.js`) were excluded from invocation counts. The ignored
`static/bodymaps/GPT/_preview.html` scratch preview is not a tracked repository
caller; its raw fetch also reads a local SVG as text and was not modified.

## Before WP3.5

There were 23 tracked raw-fetch invocations: 20 in production JavaScript and
three in direct browser/Puppeteer harnesses.

| Classification | Count | Callers | WP3.5 disposition |
|---|---:|---|---|
| JSON application endpoint | 14 | `app.js` (1), `welcome.js` (1), `exercises.js` (2), `filters.js` (1), `session-summary.js` (1), `weekly-summary.js` (2), `volume-splitter.js` (6) | Migrated to `api.get` / `api.post` / `api.delete` |
| Intentional static-asset text | 2 | `bodymap-svg.js` (1), `muscle-selector.js` (1) | Retained raw; both require SVG text rather than the JSON contract |
| Intentional blob/download | 3 | `exports.js` (2), `volume-splitter.js` (1) | Retained raw; callers require blobs and response headers/filenames |
| Shared transport implementation | 1 | `fetch-wrapper.js` | Retained raw; this is the single underlying network boundary |
| Direct test/harness transport probe | 3 | `error-handling.spec.ts` (2), `puppeteer_mcp_summary_regression.py` (1) | Retained raw; these execute in the browser to test endpoints independently of application transport |
| Dead or unreachable tracked code | 0 | None | No deletion proposed |

No raw-fetch invocation existed in a Jinja template or pytest file. The
classic `welcome.js` script remains classic and uses a click-time dynamic import
of the shared transport; this preserves template script type, order, and
DOMContentLoaded listener timing without adding a `window` bridge.

## Shared transport caller audit

Before WP3.5, 15 production modules made 46 `api.*` calls. Callers consume the
full parsed response envelope: feature modules read `response.data` for payloads
and top-level `message` where required. HTTP/network failures are thrown as the
wrapper's normalized `{code, message, requestId}` object. Existing callers vary
deliberately between wrapper-owned and feature-owned UI behavior:

- `showLoading` defaults to `true`; feature-owned spinners pass `false`.
- `showErrorToast` defaults to `true`; callers with an existing toast/error UI
  pass `false`.
- GET retries default to two; migrated raw GETs pass `retries: 0` to retain
  their original single-attempt behavior.
- Methods and object bodies flow through `api.get/post/patch/delete`; the
  wrapper JSON-stringifies object bodies. Fetch-native options, including
  credentials and abort signals, continue through `...fetchOptions`.
- Default JSON/request-ID headers remain unchanged for existing callers. WP3.5
  adds the opt-out `useDefaultHeaders: false` so migrated calls retain their
  exact pre-WP3.5 header sets.
- Public exports remain `apiFetch`, `api`, helper named exports, and the default
  `apiFetch` export. There was no `window.api` or `window.apiFetch` bridge, and
  WP3.5 adds none.

The migrated calls explicitly disable wrapper loading/error toasts where the
feature already owns those states. `volume-splitter.js` now consumes the shared
envelope directly (`response.data`); its local wrapped-response detector,
unwrapper, error-message extractor, and `parseJsonResponse` wrapper were
removed.

## After WP3.5

Nine tracked raw-fetch invocations remain and every one is intentional:

| File | Calls | Justification |
|---|---:|---|
| `static/js/modules/fetch-wrapper.js` | 1 | The shared transport must ultimately call the browser Fetch API. |
| `static/js/modules/bodymap-svg.js` | 1 | Loads a static SVG and consumes `response.text()`; the JSON wrapper has no text-asset contract. |
| `static/js/modules/muscle-selector.js` | 1 | Loads/caches a static SVG and consumes `response.text()`; bodymap behavior is unchanged. |
| `static/js/modules/exports.js` | 2 | Downloads Excel workbooks via `response.blob()` and, for plan export, preserves the server `Content-Disposition` filename. `exportSummary` has no current template caller but remains reachable through the preserved public `window.exportSummary` bridge, so it is not deleted or rewritten opportunistically. |
| `static/js/modules/volume-splitter.js` | 1 | Downloads an Excel workbook via `response.blob()` and preserves the existing `volume_plan_YYYY-MM-DD.xlsx` filename. |
| `e2e/error-handling.spec.ts` | 2 | Browser-context direct-fetch probes assert malformed/error endpoint behavior without coupling the test to production transport. |
| `e2e/puppeteer_mcp_summary_regression.py` | 1 | Browser-context regression harness directly requests the summary JSON contract; importing app transport would weaken the independent contract probe. |

All 14 production JSON application calls were removed from the raw-fetch
inventory. The shared transport now has 60 production calls across 21 caller
files. There is no dead/unreachable fetch code awaiting deletion, and no
binary/static-resource path was forced through the JSON-only transport.
