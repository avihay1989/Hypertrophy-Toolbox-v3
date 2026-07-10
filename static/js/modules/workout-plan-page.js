// Page-entry module for the workout plan page.
//
// Extracted verbatim from the two page-local inline <script> blocks in
// templates/workout_plan.html (Refactor Plan v3 WP3.2c), behaviour-preserving:
//   Block 1 (formerly a classic script) — muscle-selector instance, the
//     view-mode filter dropdown rebuild, and the plan-generator form wiring
//     (volume-scale colour, environment→equipment, live plan preview).
//   Block 2 (already a module) — the collapsible-frame toggle UI.
//
// Timing/global contract preserved: this module is deferred and sits at the same
// template position as the original scripts, before app.js in document order, so
// it assigns the window.muscleSelector global (consumed by app.js:105-106) and
// registers its DOMContentLoaded listeners before app.js runs — identical
// ordering to the original classic inline script. The classic muscle-selector.js
// above it still runs during parse, so the global MuscleSelector class exists
// before this deferred module's DOMContentLoaded news one up.
//
// updateMuscleFilterDropdowns is kept module-internal: it had no external callers
// (only its own DOMContentLoaded listener and initMuscleFilters reference it).

import { volumeColorClass, planPreviewData, equipmentForEnvironment } from './workout-plan-helpers.js';

// Muscle Selector Instance (global for access from app.js)
window.muscleSelector = null;

/**
 * Update muscle-related filter dropdowns based on view mode
 * @param {'simple' | 'advanced'} mode - The current view mode
 */
function updateMuscleFilterDropdowns(mode) {
    if (!window.FilterViewMode) {
        console.warn('FilterViewMode not loaded yet');
        return;
    }

    const muscleFilterIds = [
        'primary_muscle_group',
        'secondary_muscle_group',
        'tertiary_muscle_group',
        'advanced_isolated_muscles'
    ];

    const changedSelections = [];

    muscleFilterIds.forEach(filterId => {
        const select = document.getElementById(filterId);
        if (!select) return;

        // Store current selection
        const currentValue = select.value;

        // Determine muscle type from filter id
        let muscleType = 'primary';
        if (filterId.includes('secondary')) muscleType = 'secondary';
        else if (filterId.includes('tertiary')) muscleType = 'tertiary';
        else if (filterId.includes('isolated')) muscleType = 'isolated';

        const resolvedSelection = currentValue
            ? window.FilterViewMode.resolveFilterSelection(currentValue, muscleType, mode)
            : null;

        // Get new options from FilterViewMode
        const options = window.FilterViewMode.getMuscleFilterOptions(muscleType, mode);

        // Clear existing options (except "All")
        while (select.options.length > 1) {
            select.remove(1);
        }

        if (resolvedSelection?.isSynthetic) {
            const preservedOption = document.createElement('option');
            preservedOption.value = resolvedSelection.value;
            preservedOption.textContent = resolvedSelection.label;
            preservedOption.dataset.syntheticGroup = 'true';
            select.appendChild(preservedOption);
        }

        // Add new options
        options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.label;
            select.appendChild(option);
        });

        // Restore translated selection if it exists in the new option set
        const nextValue = resolvedSelection?.value || '';
        const optionExists = Array.from(select.options).some(opt => opt.value === nextValue);
        if (optionExists) {
            select.value = nextValue;
        } else {
            select.value = '';  // Reset to "All"
        }

        if (currentValue && select.value !== currentValue) {
            changedSelections.push(select);
        }
    });

    // Re-run filtering only when a mode switch changes the underlying filter value.
    changedSelections.forEach(select => {
        select.dispatchEvent(new Event('change', { bubbles: true }));
    });

    // Dispatch event so other components can react (e.g., table display)
    document.dispatchEvent(new CustomEvent('muscleFilterOptionsUpdated', { detail: { mode } }));
}

// Plan Generator Preview Update
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Muscle Selector
    window.muscleSelector = new MuscleSelector('muscle-selector-container');

    // Listen for view mode changes and update filters
    document.addEventListener('filterViewModeChanged', function(e) {
        updateMuscleFilterDropdowns(e.detail.mode);
    });

    // Apply initial mode to filter dropdowns (with retry for race conditions)
    function initMuscleFilters() {
        if (window.FilterViewMode) {
            updateMuscleFilterDropdowns(window.FilterViewMode.getViewMode());
        } else {
            // FilterViewMode not ready yet, retry in 50ms
            setTimeout(initMuscleFilters, 50);
        }
    }
    initMuscleFilters();

    // Volume scale display update with temperature colors
    const volumeScale = document.getElementById('gen-volume-scale');
    const volumeScaleValue = document.getElementById('volume-scale-value');

    function updateVolumeColor(value) {
        if (!volumeScaleValue) return;
        // Remove all color classes
        volumeScaleValue.classList.remove('volume-value-blue', 'volume-value-green',
            'volume-value-yellow', 'volume-value-orange', 'volume-value-red');
        // Add appropriate color class based on value
        volumeScaleValue.classList.add(volumeColorClass(value));
    }

    if (volumeScale && volumeScaleValue) {
        // Add temperature class to slider
        volumeScale.classList.add('volume-temp');
        // Set initial color
        updateVolumeColor(volumeScale.value);

        volumeScale.addEventListener('input', function() {
            volumeScaleValue.textContent = this.value + 'x';
            updateVolumeColor(this.value);
            updatePlanPreview();
        });
    }

    // Environment change - auto-select equipment
    const envSelect = document.getElementById('gen-environment');
    if (envSelect) {
        envSelect.addEventListener('change', function() {
            updateEquipmentForEnvironment(this.value);
            updatePlanPreview();
        });
    }

    // Update preview when form changes
    const formInputs = document.querySelectorAll('#generatePlanForm select, #generatePlanForm input');
    formInputs.forEach(input => {
        input.addEventListener('change', updatePlanPreview);
    });

    function updateEquipmentForEnvironment(environment) {
        const selectedEquipment = equipmentForEnvironment(environment);

        // Update all equipment checkboxes
        document.querySelectorAll('.equipment-check').forEach(checkbox => {
            checkbox.checked = selectedEquipment.includes(checkbox.value);
        });
    }

    function updatePlanPreview() {
        const trainingDays = document.getElementById('gen-training-days')?.value || '3';
        const goal = document.getElementById('gen-goal')?.value || 'hypertrophy';
        const volumeScaleVal = document.getElementById('gen-volume-scale')?.value || '1.0';

        const { routines, repRange, baseSets } = planPreviewData(trainingDays, goal, volumeScaleVal);

        const previewContent = document.getElementById('plan-preview-content');
        if (previewContent) {
            previewContent.innerHTML = `
                <span class="preview-badge badge-routines"><i class="fas fa-calendar-alt me-1"></i><span class="badge-value">${routines}</span></span>
                <span class="preview-badge badge-exercises"><i class="fas fa-dumbbell me-1"></i><span class="badge-value">~7</span> exercises</span>
                <span class="preview-badge badge-sets"><i class="fas fa-layer-group me-1"></i><span class="badge-value">${baseSets}</span> sets</span>
                <span class="preview-badge badge-reps"><i class="fas fa-redo me-1"></i><span class="badge-value">${repRange}</span> reps</span>
            `;
        }
    }
});

// Collapsible-frame toggle UI
document.addEventListener('DOMContentLoaded', function() {
    // Initialize collapse toggles
    const toggleButtons = document.querySelectorAll('.collapse-toggle');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const frame = this.closest('.collapsible-frame');
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            const toggleText = this.querySelector('.toggle-text');
            const allFrames = document.querySelectorAll('.collapsible-frame');

            // Toggle collapsed state
            frame.classList.toggle('collapsed');

            // Update aria-expanded
            this.setAttribute('aria-expanded', !isExpanded);

            // Update button text
            toggleText.textContent = isExpanded ? 'Show' : 'Hide';

            // Update title attribute for tooltip
            const sectionName = frame.getAttribute('data-section');
            const titleText = isExpanded ? `Expand ${sectionName}` : `Collapse ${sectionName}`;
            this.setAttribute('title', titleText);

            // CSS handles icon rotation via .collapsed class
            // No need for inline styles

            // Adjust spacing
            setTimeout(() => {
                // Recalculate positions after collapse/expand
                window.dispatchEvent(new Event('resize'));

                // Adjust margins for subsequent frames
                let previousFrame = frame;
                allFrames.forEach(currentFrame => {
                    if (currentFrame === frame) return;

                    if (previousFrame.classList.contains('collapsed')) {
                        currentFrame.style.marginTop = '1rem';
                    } else {
                        currentFrame.style.marginTop = '2rem';
                    }
                    previousFrame = currentFrame;
                });

                // Adjust table margin
                const table = document.querySelector('.workout-plan.table-container');
                if (table) {
                    const lastFrame = Array.from(allFrames).pop();
                    table.style.marginTop = lastFrame.classList.contains('collapsed') ? '2rem' : '3rem';
                }
            }, 300); // Wait for collapse animation to complete
        });
    });
});
