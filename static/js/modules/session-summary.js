// Session summary page entry module.
//
// This is the LIVE render path for /session_summary, extracted verbatim from
// the page-local inline <script> in templates/session_summary.html (Refactor
// Plan v3 WP3.2b). It is intentionally NOT merged into the no-op summary.js
// seam — that module and its app.js / ui-handlers.js callers are rationalized
// later (WP3.2/WP3.5), once their imports are proven gone.
//
// Timing contract preserved from the original classic inline script:
//   * `window.updateSessionSummary` is assigned at module top level (before
//     DOMContentLoaded fires) so the method-selector `onchange` attribute
//     (partials/_volume_controls.html) and summary.js's `pageHasOwnUpdater()`
//     guard both see it — the module is loaded with `type="module"`
//     (deferred), so top-level code runs after parsing but before
//     DOMContentLoaded.
//   * The initial render is driven by this module's own DOMContentLoaded
//     listener, exactly as the inline script did.

import {
    getVolumeDetails,
    isApiFailure,
    unwrapApiPayload,
    getApiErrorMessage,
    getCategoryTooltip,
    getSubcategoryTooltip,
} from './summary-helpers.js';
import { getSessionWarningBadge } from './session-summary-helpers.js';
import { api } from './fetch-wrapper.js';

// Function to update the session summary table based on the selected modes
async function updateSessionSummary() {
    const contributionMode = document.getElementById("contribution-mode").value;
    const tableBody = document.getElementById("session-summary-table");
    const categoryTableBody = document.getElementById("categories-table-body");

    // Update formula text based on counting mode
    const formulaText = document.getElementById('volume-formula-text');
    if (formulaText) {
        formulaText.textContent = 'Total Volume = Effective Sets × Avg Reps × Weight';
    }

    // Display loading spinner
    tableBody.innerHTML = `
        <tr>
            <td colspan="6" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </td>
        </tr>`;

    try {
        const params = new URLSearchParams({
            contribution_mode: contributionMode
        });

        const result = await api.get(`/session_summary?${params.toString()}`, {
            headers: {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            },
            showLoading: false,
            showErrorToast: false,
            useDefaultHeaders: false,
            retries: 0
        });

        if (isApiFailure(result)) {
            throw new Error(getApiErrorMessage(result, "Failed to fetch session summary."));
        }

        const data = unwrapApiPayload(result) || {};
        const sessionSummary = Array.isArray(data.session_summary) ? data.session_summary : [];
        const categories = Array.isArray(data.categories) ? data.categories : [];

        if (sessionSummary.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">No data available.</td>
                </tr>`;
        } else {
            // Populate the table with fetched data
            tableBody.innerHTML = sessionSummary.map(row => {
                const effectiveSets = row.effective_sets ?? row.total_sets ?? 0;
                const rawSets = row.raw_sets ?? row.total_sets ?? 0;
                const effectivePerSession = row.effective_per_session;
                const warningLevel = row.warning_level || 'no_data';
                const volume = getVolumeDetails(effectiveSets);
                const warning = getSessionWarningBadge(warningLevel, effectivePerSession);
                // Transform muscle group name based on view mode
                const muscleDisplay = window.FilterViewMode?.transformMuscleDisplay(row.muscle_group) || row.muscle_group || "N/A";
                const displayVolume = row.total_volume ?? 0;

                return `
                    <tr class="${row.is_excessive ? 'table-danger' : row.is_borderline ? 'table-warning' : ''}">
                        <td data-label="Routine">${row.routine || "N/A"}</td>
                        <td data-label="Muscle Group" data-raw-value="${row.muscle_group || ''}">${muscleDisplay}</td>
                        <td data-label="Effective Sets" class="is-num">${effectiveSets.toFixed(1)}</td>
                        <td data-label="Raw Sets" class="is-num">${rawSets.toFixed(1)}</td>
                        <td data-label="Total Volume" class="is-num">${displayVolume.toFixed(0)}</td>
                        <td data-label="Volume Status">
                            <div class="d-flex flex-column gap-1">
                                <div class="volume-classification"
                                     data-bs-toggle="tooltip"
                                     title="${volume.tooltip}">
                                    <span class="volume-badge ${volume.class}">
                                        ${volume.label}
                                    </span>
                                </div>
                                <span class="badge ${warning.class}"
                                      data-bs-toggle="tooltip"
                                      title="${warning.tooltip}">
                                    ${warning.label}
                                </span>
                            </div>
                        </td>
                    </tr>
                `;
            }).join("");
        }

        // Update categories table
        if (categories.length === 0) {
            categoryTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted">No categories data available.</td>
                </tr>`;
        } else {
            categoryTableBody.innerHTML = categories.map(cat => `
                <tr>
                    <td>
                        <span data-bs-toggle="tooltip"
                              title="${getCategoryTooltip(cat.category)}">
                            ${cat.category}
                        </span>
                    </td>
                    <td>
                        <span data-bs-toggle="tooltip"
                              title="${getSubcategoryTooltip(cat.category, cat.subcategory)}">
                            ${cat.subcategory}
                        </span>
                    </td>
                    <td>${cat.total_exercises}</td>
                </tr>
            `).join('');
        }

        // Initialize tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

    } catch (error) {
        console.error("Error fetching data:", error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-danger">Failed to load data.</td>
            </tr>`;
    }
}

/**
 * Update isolated muscle displays in server-rendered table based on view mode
 */
function updateIsolatedMuscleDisplays() {
    const isolatedCells = document.querySelectorAll('td[data-label="Isolated Muscle"]');
    isolatedCells.forEach(cell => {
        const rawValue = cell.getAttribute('data-raw-value') || cell.textContent.trim();
        if (!cell.getAttribute('data-raw-value')) {
            cell.setAttribute('data-raw-value', rawValue);
        }
        if (window.FilterViewMode) {
            cell.textContent = window.FilterViewMode.transformIsolatedMuscleDisplay(rawValue);
        }
    });
}

// Preserve the global contract: the method-selector `onchange` attribute
// (partials/_volume_controls.html) and summary.js's `pageHasOwnUpdater()`
// guard both look up `window.updateSessionSummary`.
window.updateSessionSummary = updateSessionSummary;

// Initialize table when the page loads
document.addEventListener("DOMContentLoaded", function() {
    // Listen for view mode changes (toggle is in navbar)
    if (window.FilterViewMode) {
        document.addEventListener('filterViewModeChanged', function() {
            // Re-render tables with updated muscle names
            updateSessionSummary();
            // Also update the server-rendered isolated muscles table
            updateIsolatedMuscleDisplays();
        });
    }

    updateSessionSummary();
});
