// Session-specific pure helper for the session summary page.
//
// Extracted verbatim from the page-local inline script in
// templates/session_summary.html (Refactor Plan v3 WP3.2b). This is the one
// helper unique to the session page — the session warning badge (OK /
// Borderline / Excessive / No Sessions), which has no weekly analogue. The
// remaining pure helpers the page uses (getVolumeDetails, the API-envelope
// helpers, the category/subcategory tooltips) are shared with the weekly page
// and live in summary-helpers.js. DOM-free and side-effect-free so it can be
// unit-tested under the node-environment Vitest runner.

// Session warning badge details based on warning level and per-session load.
export function getSessionWarningBadge(warningLevel, effectivePerSession) {
    const warnings = {
        'ok': { class: 'bg-success', label: 'OK', tooltip: 'Session volume within productive limits' },
        'borderline': { class: 'bg-warning text-dark', label: 'Borderline', tooltip: 'Approaching productive limits' },
        'excessive': { class: 'bg-danger', label: 'Excessive', tooltip: 'May exceed productive stimulus' },
        'no_data': { class: 'bg-secondary', label: 'No Sessions', tooltip: 'No logged sessions — export your plan to the workout log first' }
    };
    const warning = warnings[warningLevel] || warnings['no_data'];
    if (warningLevel === 'no_data' || effectivePerSession == null) {
        return warnings['no_data'];
    }
    return {
        ...warning,
        tooltip: `${warning.tooltip} (${effectivePerSession.toFixed(1)} effective sets/session)`
    };
}
