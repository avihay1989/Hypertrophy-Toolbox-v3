// Weekly / session summary fetch entry points.
//
// The LIVE rendering path for both summary pages is the page-local inline
// updater — `window.updateWeeklySummary` (templates/weekly_summary.html) and
// `window.updateSessionSummary` (templates/session_summary.html). Both summary
// pages define their inline updater unconditionally, and these exported
// functions are only ever called on those two pages (from app.js init and the
// ui-handlers method-change handler). `pageHasOwnUpdater()` is therefore always
// true at every call site, so these functions short-circuit and never render.
//
// WP0.4 removed the module's fallback rendering path (updateSummaryUI + the
// table builders + volume-class helpers), which was proven unreachable. The
// guarded fetch stubs and their call sites are intentionally retained: removing
// them means rationalizing the app.js / ui-handlers callers, which is WP3.2's
// job (extract the inline summary scripts, then delete this module + its
// callers together). Do not merge the inline updaters into this module.

// Check if the page already has its own summary updater defined (inline).
function pageHasOwnUpdater() {
    return typeof window.updateWeeklySummary === 'function' ||
           typeof window.updateSessionSummary === 'function';
}

export async function fetchWeeklySummary(method = 'Total') {
    // The live weekly-summary UI (inline updateWeeklySummary) owns rendering.
    if (pageHasOwnUpdater()) {
        return;
    }
}

export async function fetchSessionSummary(method = 'Total') {
    // The live session-summary UI (inline updateSessionSummary) owns rendering.
    if (pageHasOwnUpdater()) {
        return;
    }
}
