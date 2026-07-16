// Weekly (Plan Volume) summary page entry module.
//
// This is the LIVE render path for /weekly_summary, extracted verbatim from
// the page-local inline <script> in templates/weekly_summary.html (Refactor
// Plan v3 WP3.2a). It is intentionally NOT merged into the no-op summary.js
// seam — that module and its app.js / ui-handlers.js callers are rationalized
// later (WP3.2/WP3.5), once their imports are proven gone.
//
// Timing contract preserved from the original classic inline script:
//   * `window.updateWeeklySummary` is assigned at module top level (before
//     DOMContentLoaded fires) so the method-selector `onchange` attribute and
//     summary.js's `pageHasOwnUpdater()` guard both see it — the module is
//     loaded with `type="module"` (deferred), so top-level code runs after
//     parsing but before DOMContentLoaded.
//   * The initial render is driven by this module's own DOMContentLoaded
//     listener, exactly as the inline script did.

import {
    getVolumeDetails,
    formatPatternName,
    isApiFailure,
    unwrapApiPayload,
    getApiErrorMessage,
    getCategoryTooltip,
    getSubcategoryTooltip,
} from './summary-helpers.js';
import { api } from './fetch-wrapper.js';

// Function to fetch and display pattern coverage
async function updatePatternCoverage() {
    const container = document.getElementById('pattern-coverage-container');

    try {
        const result = await api.get('/api/pattern_coverage', {
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
            throw new Error(getApiErrorMessage(result, 'Failed to fetch pattern coverage'));
        }

        const data = unwrapApiPayload(result);
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response');
        }
        const hasData = Object.keys(data.total || {}).length > 0;

        if (!hasData) {
            container.innerHTML = `
                <div class="alert alert-secondary text-center">
                    <i class="fas fa-info-circle me-2"></i>
                    No exercises in your workout plan yet. Add exercises to see pattern coverage analysis.
                </div>`;
            return;
        }

        // Build the pattern coverage display
        let html = '';

        // Warnings section
        if (data.warnings && data.warnings.length > 0) {
            html += `<div class="mb-4">`;
            data.warnings.forEach(warning => {
                const alertClass = warning.level === 'high' ? 'danger' :
                                   warning.level === 'medium' ? 'warning' : 'info';
                const icon = warning.level === 'high' ? 'exclamation-circle' :
                             warning.level === 'medium' ? 'exclamation-triangle' : 'info-circle';
                html += `
                    <div class="alert alert-${alertClass} d-flex align-items-start mb-2">
                        <i class="fas fa-${icon} me-2 mt-1"></i>
                        <div>
                            <strong>${warning.message}</strong><br>
                            <small>${warning.description}</small>
                        </div>
                    </div>`;
            });
            html += `</div>`;
        }

        // Total pattern coverage
        html += `
            <div class="row g-3 mb-4">
                <div class="col-12">
                    <h5 class="mb-3">Total Sets by Movement Pattern</h5>
                    <div class="d-flex flex-wrap gap-2">`;

        // Core patterns first, then others
        const corePatterns = ['squat', 'hinge', 'horizontal_push', 'horizontal_pull', 'vertical_push', 'vertical_pull'];
        const otherPatterns = Object.keys(data.total).filter(p => !corePatterns.includes(p));
        const allPatterns = [...corePatterns, ...otherPatterns];

        allPatterns.forEach(pattern => {
            const sets = data.total[pattern] || 0;
            if (sets > 0 || corePatterns.includes(pattern)) {
                const isCore = corePatterns.includes(pattern);
                const btnClass = sets === 0 ? 'outline-danger' :
                                 sets < 3 ? 'outline-warning' : 'outline-success';
                html += `
                    <span class="badge bg-${btnClass} text-dark border" style="font-size: 0.9rem; padding: 8px 12px;">
                        ${isCore ? '<i class="fas fa-check-circle me-1"></i>' : ''}
                        ${formatPatternName(pattern)}: <strong>${sets}</strong>
                    </span>`;
            }
        });

        html += `</div></div></div>`;

        // Sets per routine
        if (Object.keys(data.sets_per_routine || {}).length > 0) {
            html += `
                <div class="row g-3">
                    <div class="col-12">
                        <h5 class="mb-3">Sets per Routine</h5>
                        <div class="d-flex flex-wrap gap-3">`;

            const idealMin = data.ideal_sets_range?.min || 15;
            const idealMax = data.ideal_sets_range?.max || 24;

            Object.entries(data.sets_per_routine).forEach(([routine, sets]) => {
                const status = sets < idealMin ? 'warning' :
                               sets > idealMax ? 'danger' : 'success';
                const icon = sets < idealMin ? 'arrow-down' :
                             sets > idealMax ? 'arrow-up' : 'check';
                html += `
                    <div class="card glass-neumorph-card border-${status}" data-visual-surface style="min-width: 150px;">
                        <div class="card-body text-center py-2">
                            <h6 class="card-title mb-1">Routine ${routine}</h6>
                            <p class="card-text mb-0">
                                <span class="text-${status}">
                                    <i class="fas fa-${icon} me-1"></i>
                                    <strong>${sets}</strong> sets
                                </span>
                            </p>
                            <small class="text-muted">Target: ${idealMin}-${idealMax}</small>
                        </div>
                    </div>`;
            });

            html += `</div></div></div>`;
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Error fetching pattern coverage:', error);
        container.innerHTML = `
            <div class="alert alert-warning text-center">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Unable to load pattern coverage analysis.
            </div>`;
    }
}

// Function to update the weekly summary table based on the selected modes
async function updateWeeklySummary() {
    const contributionMode = document.getElementById("contribution-mode").value;
    const tableBody = document.getElementById("weekly-summary-table");
    const categoryTableBody = document.getElementById("categories-table-body");

    // Display loading spinner
    tableBody.innerHTML = `
        <tr>
            <td colspan="6">
                <div class="skeleton" style="height: 150px; width: 100%;"></div>
            </td>
        </tr>`;

    // Update formula text based on counting mode
    const formulaText = document.getElementById('volume-formula-text');
    if (formulaText) {
        formulaText.textContent = 'Total Volume = Effective Sets × Avg Reps × Weight';
    }

    try {
        const result = await api.get(`/weekly_summary?contribution_mode=${contributionMode}`, {
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
            throw new Error(getApiErrorMessage(result, "Failed to fetch weekly summary."));
        }

        const data = unwrapApiPayload(result) || {};
        const weeklySummary = Array.isArray(data.weekly_summary) ? data.weekly_summary : [];
        const categories = Array.isArray(data.categories) ? data.categories : [];

        // Update weekly summary table
        if (weeklySummary.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">No data available.</td>
                </tr>`;
        } else {
            // Populate the table with fetched data
            tableBody.innerHTML = weeklySummary.map(row => {
                const effectiveSets = row.effective_sets ?? row.total_sets ?? 0;
                const rawSets = row.raw_sets ?? row.total_sets ?? 0;
                const routines = row.frequency || 0;
                const volume = getVolumeDetails(effectiveSets);
                // Transform muscle group name based on view mode
                const muscleDisplay = window.FilterViewMode?.transformMuscleDisplay(row.muscle_group) || row.muscle_group || "N/A";
                const displayVolume = row.total_volume ?? row.total_weight ?? 0;
                return `
                    <tr>
                        <td data-label="Muscle Group" data-raw-value="${row.muscle_group || ''}">${muscleDisplay}</td>
                        <td data-label="Effective Sets" class="is-num">${effectiveSets.toFixed(1)}</td>
                        <td data-label="Raw Sets" class="is-num">${rawSets.toFixed(1)}</td>
                        <td data-label="Routines" class="is-num">${routines}</td>
                        <td data-label="Total Volume" class="is-num">${displayVolume.toFixed(0)}</td>
                        <td data-label="Volume Classification">
                            <div class="volume-classification"
                                 data-bs-toggle="tooltip"
                                 title="${volume.tooltip}">
                                <span class="volume-badge ${volume.class}">
                                    ${volume.label}
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
// guard both look up `window.updateWeeklySummary`.
window.updateWeeklySummary = updateWeeklySummary;

// Initialize table when the page loads
document.addEventListener("DOMContentLoaded", function() {
    // Listen for view mode changes (toggle is in navbar)
    if (window.FilterViewMode) {
        document.addEventListener('filterViewModeChanged', function() {
            // Re-render tables with updated muscle names
            updateWeeklySummary();
            // Also update the server-rendered isolated muscles table
            updateIsolatedMuscleDisplays();
        });
    }

    updateWeeklySummary();
    updatePatternCoverage();
});
