import { showToast } from './toast.js';

let volumeConfig = null;
let currentMode = 'basic';
let calculateDebounceId = null;
const modeVolumeState = {
    basic: {},
    advanced: {}
};
const modeRangeState = {
    basic: {},
    advanced: {}
};

const DEFAULT_SLIDER_MAX = 60;
const JSON_REQUEST_HEADERS = {
    'Accept': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
};

const deepClone = (value) => JSON.parse(JSON.stringify(value || {}));

const isWrappedApiResponse = (payload) => Boolean(
    payload &&
    typeof payload === 'object' &&
    !Array.isArray(payload) &&
    'data' in payload &&
    (payload.ok === true || payload.status === 'success' || payload.success === true)
);

const isApiFailure = (payload) => Boolean(
    payload &&
    typeof payload === 'object' &&
    (payload.ok === false || payload.success === false)
);

const unwrapApiPayload = (payload) => (isWrappedApiResponse(payload) ? payload.data : payload);

const getApiErrorMessage = (payload, fallbackMessage) => {
    if (!payload || typeof payload !== 'object') {
        return fallbackMessage;
    }

    if (payload.error && typeof payload.error === 'object' && typeof payload.error.message === 'string') {
        return payload.error.message;
    }

    if (typeof payload.error === 'string') {
        return payload.error;
    }

    if (typeof payload.message === 'string' && payload.message.trim()) {
        return payload.message;
    }

    return fallbackMessage;
};

async function parseJsonResponse(response, fallbackMessage) {
    const payload = await response.json();

    if (!response.ok || isApiFailure(payload)) {
        throw new Error(getApiErrorMessage(payload, fallbackMessage));
    }

    return unwrapApiPayload(payload);
}

const toNumericRange = (range) => {
    const fallback = { min: 12, max: 20 };
    if (!range || typeof range !== 'object') {
        return { ...fallback };
    }
    const min = Number(range.min);
    const max = Number(range.max);
    const safeMin = Number.isFinite(min) && min >= 0 ? min : fallback.min;
    const safeMaxCandidate = Number.isFinite(max) && max >= 0 ? max : fallback.max;
    const safeMax = safeMaxCandidate < safeMin ? safeMin : safeMaxCandidate;
    return { min: safeMin, max: safeMax };
};

const normalizeRangeMap = (ranges) => {
    const result = {};
    Object.entries(deepClone(ranges)).forEach(([muscle, range]) => {
        result[muscle] = toNumericRange(range);
    });
    return result;
};

const sanitizeRangePair = (pair) => toNumericRange(pair);

export function initializeVolumeSplitter() {
    const root = document.getElementById('volume-splitter-app');
    if (!root) {
        return;
    }

    volumeConfig = parseConfig(root);
    modeRangeState.basic = normalizeRangeMap(volumeConfig.basicRanges);
    modeRangeState.advanced = normalizeRangeMap(volumeConfig.advancedRanges);
    currentMode = volumeConfig.defaultMode;

    initializeModeToggle(root);
    initializePageTooltips();

    const calculateBtn = document.getElementById('calculate-volume');
    if (calculateBtn) {
        calculateBtn.addEventListener('click', () => calculateVolume());
    }

    const resetBtn = document.getElementById('reset-volume');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetValues);
    }

    const exportBtn = document.getElementById('export-volume');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportVolumePlan);
    }

    const exportExcelBtn = document.getElementById('export-to-excel-btn');
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', exportToExcel);
    }

    const historyBody = document.getElementById('history-body');
    if (historyBody) {
        historyBody.addEventListener('click', handleHistoryClick);
    }

    initDeleteModal();

    renderSliders();
    modeVolumeState[currentMode] = collectVolumes();
    modeRangeState[currentMode] = collectRanges();
    loadVolumeHistory();
}

function initializePageTooltips() {
    if (typeof tippy !== 'function') {
        return;
    }

    tippy('#training-days', {
        content: 'Choose a realistic frequency that you can maintain consistently. More training days allow for better volume distribution.',
        placement: 'right'
    });
}

function calculateVolume() {
    const trainingSelect = document.getElementById('training-days');
    const trainingDays = Math.max(parseInt(trainingSelect?.value, 10) || 3, 1);
    const volumes = collectVolumes();
    const ranges = collectRanges();

    modeVolumeState[currentMode] = volumes;
    modeRangeState[currentMode] = ranges;

    fetch('/api/calculate_volume', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...JSON_REQUEST_HEADERS
        },
        body: JSON.stringify({
            mode: currentMode,
            training_days: trainingDays,
            volumes,
            ranges
        })
    })
        .then(response => parseJsonResponse(response, 'Failed to calculate volume.'))
        .then(handleCalculateResponse)
        .catch(error => {
            console.error('Error calculating volume:', error);
        });
}

function displayResults(results) {
    const tbody = document.getElementById('results-body');
    if (!tbody) {
        return;
    }

    tbody.innerHTML = '';
    const entries = Object.entries(results || {});

    if (!entries.length) {
        const section = document.querySelector('.results-section');
        section?.classList.add('d-none');
        return;
    }

    entries.forEach(([muscle, data]) => {
        const row = document.createElement('tr');
        const statusLabel = (data.status || 'optimal');
        row.innerHTML = `
            <td>${muscle}</td>
            <td>${data.weekly_sets}</td>
            <td>${data.sets_per_session}</td>
            <td class="status-${statusLabel}">
                ${statusLabel.charAt(0).toUpperCase() + statusLabel.slice(1)}
            </td>
        `;
        tbody.appendChild(row);
    });

    document.querySelector('.results-section')?.classList.remove('d-none');

    const ranges = getCurrentRanges();
    entries.forEach(([muscle, data]) => {
        applyStatusToRow(muscle, data, ranges[muscle]);
    });
}

function resetValues() {
    document.querySelectorAll('.volume-slider').forEach(slider => {
        slider.value = 0;
        updateValueDisplay(slider);
    });
    modeVolumeState[currentMode] = collectVolumes();
    clearResults();
}

function loadPlan(planId) {
    fetch(`/api/volume_plan/${planId}`, {
        headers: JSON_REQUEST_HEADERS
    })
        .then(response => parseJsonResponse(response, 'Failed to load plan.'))
        .then(plan => {
            const trainingSelect = document.getElementById('training-days');
            if (trainingSelect) {
                trainingSelect.value = plan.training_days;
            }

            const planVolumes = plan.volumes || {};
            const numericVolumes = Object.entries(planVolumes).reduce((acc, [muscle, data]) => {
                acc[muscle] = data?.weekly_sets || 0;
                return acc;
            }, {});

            const advancedLabels = new Set(volumeConfig.advancedMuscles);
            const hasAdvancedLabels = Object.keys(numericVolumes).some(label => advancedLabels.has(label));
            const targetMode = hasAdvancedLabels ? 'advanced' : 'basic';

            setMode(targetMode, numericVolumes, { skipCalculate: true });
            calculateVolume();
        })
        .catch(error => {
            console.error('Error loading plan:', error);
            showToast('error', 'Failed to load plan. Please try again.');
        });
}

let pendingDeletePlanId = null;
let deleteModal = null;

function initDeleteModal() {
    const modalElement = document.getElementById('deleteVolumePlanModal');
    if (modalElement && typeof bootstrap !== 'undefined') {
        deleteModal = new bootstrap.Modal(modalElement);
        
        document.getElementById('confirmDeleteVolumePlan')?.addEventListener('click', () => {
            if (pendingDeletePlanId) {
                executeDeletePlan(pendingDeletePlanId);
            }
        });
    }
}

function deletePlan(planId) {
    pendingDeletePlanId = planId;
    if (deleteModal) {
        deleteModal.show();
    } else {
        // Fallback if modal not initialized
        executeDeletePlan(planId);
    }
}

function executeDeletePlan(planId) {
    fetch(`/api/volume_plan/${planId}`, {
        method: 'DELETE',
        headers: JSON_REQUEST_HEADERS
    })
    .then(response => parseJsonResponse(response, 'Failed to delete volume plan.'))
    .then(result => {
        if (deleteModal) deleteModal.hide();
        showToast('success', result?.message || 'Volume plan deleted successfully!');
        loadVolumeHistory();
    })
    .catch(error => {
        if (deleteModal) deleteModal.hide();
        console.error('Error deleting plan:', error);
        showToast('error', 'Failed to delete plan. Please try again.');
    })
    .finally(() => {
        pendingDeletePlanId = null;
    });
}

function exportVolumePlan() {
    const trainingSelect = document.getElementById('training-days');
    const trainingDays = Math.max(parseInt(trainingSelect?.value, 10) || 3, 1);
    const volumes = collectVolumes();

    const data = {
        mode: currentMode,
        training_days: trainingDays,
        volumes
    };
    
    fetch('/api/save_volume_plan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...JSON_REQUEST_HEADERS
        },
        body: JSON.stringify(data)
    })
    .then(response => parseJsonResponse(response, 'Failed to save volume plan.'))
    .then(result => {
        showToast('success', result?.message || 'Volume plan saved successfully!');
        loadVolumeHistory();
    })
    .catch(error => {
        console.error('Error saving plan:', error);
        showToast('error', 'Failed to save plan. Please try again.');
    });
}

function displaySuggestions(suggestions) {
    const container = document.querySelector('.suggestions-container');
    const section = document.querySelector('.ai-suggestions-section');
    if (!container || !section) {
        return;
    }

    container.innerHTML = '';
    const list = Array.isArray(suggestions) ? suggestions : [];

    if (!list.length) {
        section.classList.add('d-none');
        return;
    }

    list.forEach(suggestion => {
        const card = document.createElement('div');
        card.className = `suggestion-card suggestion-${suggestion.type}`;
        card.innerHTML = `
            <p class="mb-0">${suggestion.message}</p>
        `;
        container.appendChild(card);
    });

    section.classList.remove('d-none');
}

function loadVolumeHistory() {
    fetch('/api/volume_history', {
        headers: JSON_REQUEST_HEADERS
    })
        .then(response => parseJsonResponse(response, 'Failed to load volume history.'))
        .then(history => {
            const tbody = document.getElementById('history-body');
            tbody.innerHTML = '';

            const entries = Object.entries(history || {}).sort(([, a], [, b]) => {
                const left = Date.parse(a?.created_at || '') || 0;
                const right = Date.parse(b?.created_at || '') || 0;
                return right - left;
            });

            entries.forEach(([id, data]) => {
                const row = document.createElement('tr');
                const totalVolume = Object.values(data.muscles)
                    .reduce((sum, muscle) => sum + muscle.weekly_sets, 0);
                
                row.innerHTML = `
                    <td>${new Date(data.created_at).toLocaleDateString()}</td>
                    <td>${data.training_days} days</td>
                    <td>${totalVolume} sets</td>
                    <td>
                        <button class="btn btn-sm btn-primary load-plan" 
                                data-plan-id="${id}">Load</button>
                        <button class="btn btn-sm btn-danger delete-plan ms-1" 
                                data-plan-id="${id}">Delete</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
            if (!entries.length) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-muted">No saved volume plans yet.</td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading volume history:', error);
            const tbody = document.getElementById('history-body');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-danger">Failed to load volume history.</td>
                    </tr>
                `;
            }
            showToast('error', 'Failed to load saved volume plans. Please try again.');
        });
}

function exportToExcel() {
    const trainingSelect = document.getElementById('training-days');
    const trainingDays = Math.max(parseInt(trainingSelect?.value, 10) || 3, 1);
    const volumes = collectVolumes();

    const data = {
        mode: currentMode,
        training_days: trainingDays,
        volumes
    };
    
    fetch('/api/export_volume_excel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `volume_plan_${new Date().toISOString().slice(0,10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    })
    .catch(error => {
        console.error('Error exporting to Excel:', error);
        showToast('error', 'Failed to export plan. Please try again.');
    });
} 

function parseConfig(root) {
    const safeParse = (value, fallback) => {
        try {
            return value ? JSON.parse(value) : fallback;
        } catch (error) {
            console.error('Failed to parse volume splitter config value:', error);
            return fallback;
        }
    };

    const defaultMode = (root.dataset.defaultMode || 'basic').toLowerCase() === 'advanced' ? 'advanced' : 'basic';

    return {
        basicMuscles: safeParse(root.dataset.basicMuscles, []),
        advancedMuscles: safeParse(root.dataset.advancedMuscles, []),
        basicRanges: safeParse(root.dataset.basicRanges, {}),
        advancedRanges: safeParse(root.dataset.advancedRanges, {}),
        defaultMode
    };
}

function initializeModeToggle(root) {
    const radios = root.querySelectorAll('input[name="volume-mode"]');
    radios.forEach(radio => {
        radio.checked = radio.value === currentMode;
        radio.addEventListener('change', event => {
            if (event.target.checked) {
                setMode(event.target.value);
            }
        });
    });
}

function setMode(newMode, prefillVolumes = null, options = {}) {
    const normalized = (newMode || 'basic').toLowerCase() === 'advanced' ? 'advanced' : 'basic';
    const previousMode = currentMode;

    if (document.querySelector('.volume-slider')) {
        modeVolumeState[previousMode] = collectVolumes();
        modeRangeState[previousMode] = collectRanges();
    }

    currentMode = normalized;

    const radios = document.querySelectorAll('input[name="volume-mode"]');
    radios.forEach(radio => {
        radio.checked = radio.value === normalized;
    });

    const volumesToApply = prefillVolumes || modeVolumeState[currentMode] || {};
    renderSliders(volumesToApply);
    modeVolumeState[currentMode] = collectVolumes();
    modeRangeState[currentMode] = collectRanges();

    if (!options.skipCalculate) {
        calculateVolume();
    }
}

function renderSliders(prefillVolumes = {}) {
    const container = document.getElementById('sliders');
    if (!container) {
        return;
    }

    const muscles = getCurrentMuscles();
    const ranges = getCurrentRanges();
    container.innerHTML = '';

    muscles.forEach(muscle => {
        const value = prefillVolumes[muscle] ?? 0;
        const range = ranges[muscle] || toNumericRange();
        const row = createSliderRow(muscle, range, value);
        container.appendChild(row);
    });

    attachSliderListeners();
    attachSliderTooltips();
    updateAllSliderTracks();
}

function getCurrentMuscles() {
    return currentMode === 'advanced' ? volumeConfig.advancedMuscles : volumeConfig.basicMuscles;
}

function getCurrentRanges() {
    const state = currentMode === 'advanced' ? modeRangeState.advanced : modeRangeState.basic;
    const defaults = currentMode === 'advanced' ? volumeConfig.advancedRanges : volumeConfig.basicRanges;
    const muscles = getCurrentMuscles();
    const ranges = {};
    muscles.forEach(muscle => {
        if (state && state[muscle]) {
            ranges[muscle] = toNumericRange(state[muscle]);
        } else if (defaults && defaults[muscle]) {
            ranges[muscle] = toNumericRange(defaults[muscle]);
        } else {
            ranges[muscle] = toNumericRange();
        }
    });
    return ranges;
}

function createSliderRow(muscle, range, value) {
    const row = document.createElement('div');
    row.className = 'muscle-row mb-3';
    row.dataset.muscle = muscle;

    const initialValue = Number.isFinite(value) ? Math.max(0, Number(value)) : 0;

    row.innerHTML = `
        <label class="form-label d-flex justify-content-between align-items-center">
            <span class="muscle-name">${muscle}</span>
            <span class="current-value volume-value-pill" data-muscle="${muscle}">${initialValue}</span>
        </label>
        <div class="d-flex flex-column flex-md-row gap-3 align-items-stretch align-items-md-center">
            <div class="slider-stack flex-fill d-flex align-items-center gap-3">
                <input type="range"
                       class="form-range volume-slider"
                       min="0"
                       max="${DEFAULT_SLIDER_MAX}"
                       step="1"
                       value="${initialValue}"
                       data-muscle="${muscle}" />
            </div>
        </div>
    `;

    return row;
}

function attachSliderListeners() {
    document.querySelectorAll('.volume-slider').forEach(slider => {
        slider.addEventListener('input', event => {
            updateValueDisplay(event.target);
            const muscle = event.target.dataset.muscle;
            if (!modeVolumeState[currentMode]) {
                modeVolumeState[currentMode] = {};
            }
            modeVolumeState[currentMode][muscle] = parseInt(event.target.value, 10) || 0;
            updateSliderTrack(event.target, getRangeForMuscle(muscle));
            scheduleCalculate();
        });

        slider.addEventListener('change', () => {
            modeVolumeState[currentMode] = { ...collectVolumes() };
            updateSliderTrack(slider, getRangeForMuscle(slider.dataset.muscle));
            calculateVolume();
        });
    });
}

function getRangeForMuscle(muscle) {
    const ranges = getCurrentRanges();
    return ranges[muscle] || toNumericRange();
}

function updateSliderTrack(slider, range) {
    if (!slider) {
        return;
    }
    const sliderMax = Number(slider.max) || DEFAULT_SLIDER_MAX;
    const safeRange = toNumericRange(range);
    const minPercent = Math.max(0, Math.min(100, (safeRange.min / sliderMax) * 100));
    const maxPercent = Math.max(minPercent, Math.min(100, (safeRange.max / sliderMax) * 100));

    const baseColor = getComputedStyle(document.documentElement).getPropertyValue('--volume-track-bg').trim() || '#e9ecef';
    const highlightColor = getComputedStyle(document.documentElement).getPropertyValue('--volume-track-optimal').trim() || '#0d6efd';

    slider.style.background = `linear-gradient(90deg, ${baseColor} 0%, ${baseColor} ${minPercent}%, ${highlightColor} ${minPercent}%, ${highlightColor} ${maxPercent}%, ${baseColor} ${maxPercent}%, ${baseColor} 100%)`;
}

function updateAllSliderTracks() {
    document.querySelectorAll('.volume-slider').forEach(slider => {
        updateSliderTrack(slider, getRangeForMuscle(slider.dataset.muscle));
    });
}

function attachSliderTooltips() {
    if (typeof tippy !== 'function') {
        return;
    }

    const ranges = getCurrentRanges();
    document.querySelectorAll('.volume-slider').forEach(slider => {
        const muscle = slider.dataset.muscle;
        const range = ranges[muscle] || { min: 12, max: 20 };

        if (slider._tippy) {
            slider._tippy.destroy();
        }

        tippy(slider, {
            content: `
                <div class="tooltip-content">
                    <h6>${muscle}</h6>
                    <ul class="mb-0 ps-3">
                        <li>Recommended weekly sets: ${range.min}-${range.max}</li>
                        <li>Adjust slider to match your plan</li>
                    </ul>
                </div>
            `,
            allowHTML: true,
            placement: 'top'
        });
    });
}

function updateValueDisplay(slider) {
    const muscle = slider.dataset.muscle;
    const valueDisplay = document.querySelector(`.current-value[data-muscle="${escapeForSelector(muscle)}"]`);
    if (valueDisplay) {
        valueDisplay.textContent = slider.value;
    }
}

function collectVolumes() {
    const volumes = {};
    document.querySelectorAll('.volume-slider').forEach(slider => {
        const muscle = slider.dataset.muscle;
        if (!muscle) {
            return;
        }
        volumes[muscle] = parseInt(slider.value, 10) || 0;
    });
    return volumes;
}

function collectRanges() {
    return getCurrentRanges();
}

function applyServerRanges(rangeMap) {
    if (!rangeMap || typeof rangeMap !== 'object') {
        return;
    }

    const state = { ...(modeRangeState[currentMode] || {}) };
    let updatedAny = false;

    Object.entries(rangeMap).forEach(([muscle, rawRange]) => {
        const range = sanitizeRangePair(rawRange);
        state[muscle] = range;
        updatedAny = true;

        const row = document.querySelector(`.muscle-row[data-muscle="${escapeForSelector(muscle)}"]`);
        if (!row) {
            return;
        }

        const slider = row.querySelector('.volume-slider');
        if (slider) {
            updateSliderTrack(slider, range);
        }
    });

    if (updatedAny) {
        modeRangeState[currentMode] = state;
        updateAllSliderTracks();
    }
}

function handleCalculateResponse(data) {
    const payload = data || {};
    const normalizedRanges = normalizeRangeMap(payload.ranges || {});
    applyServerRanges(normalizedRanges);

    const results = payload.results || {};

    displayResults(results);
    displaySuggestions(payload.suggestions || []);

    if (!Object.keys(results).length) {
        clearResults();
    }
}

function applyStatusToRow(muscle, result, range) {
    const row = document.querySelector(`.muscle-row[data-muscle="${escapeForSelector(muscle)}"]`);
    if (!row) {
        return;
    }

    const status = result?.status || 'optimal';
    const statusClasses = ['status-low', 'status-optimal', 'status-high', 'status-excessive'];
    statusClasses.forEach(cls => row.classList.remove(cls));
    row.classList.add(`status-${status}`);

    const badge = row.querySelector('.current-value');
    if (badge) {
        const modifierMap = {
            low: 'volume-value-pill--low',
            optimal: 'volume-value-pill--optimal',
            high: 'volume-value-pill--high',
            excessive: 'volume-value-pill--excessive'
        };
        badge.classList.remove(
            'volume-value-pill--low',
            'volume-value-pill--optimal',
            'volume-value-pill--high',
            'volume-value-pill--excessive'
        );
        const modifier = modifierMap[status];
        if (modifier) {
            badge.classList.add(modifier);
        }
    }
}

function handleHistoryClick(event) {
    const loadBtn = event.target.closest('.load-plan');
    if (loadBtn) {
        const planId = loadBtn.dataset.planId;
        if (planId) {
            loadPlan(planId);
        }
        return;
    }
    
    const deleteBtn = event.target.closest('.delete-plan');
    if (deleteBtn) {
        const planId = deleteBtn.dataset.planId;
        if (planId) {
            deletePlan(planId);
        }
    }
}

function scheduleCalculate() {
    if (calculateDebounceId) {
        clearTimeout(calculateDebounceId);
    }
    calculateDebounceId = window.setTimeout(() => calculateVolume(), 300);
}

function clearResults() {
    const resultsSection = document.querySelector('.results-section');
    const suggestionsSection = document.querySelector('.ai-suggestions-section');
    const resultsBody = document.getElementById('results-body');
    const suggestionsContainer = document.querySelector('.suggestions-container');

    resultsSection?.classList.add('d-none');
    suggestionsSection?.classList.add('d-none');

    if (resultsBody) {
        resultsBody.innerHTML = '';
    }

    if (suggestionsContainer) {
        suggestionsContainer.innerHTML = '';
    }

    document.querySelectorAll('.muscle-row').forEach(row => {
        row.classList.remove('status-low', 'status-optimal', 'status-high', 'status-excessive');
        const badge = row.querySelector('.current-value');
        if (badge) {
            badge.classList.remove(
                'volume-value-pill--low',
                'volume-value-pill--optimal',
                'volume-value-pill--high',
                'volume-value-pill--excessive'
            );
        }
    });
}

function escapeForSelector(value) {
    if (window.CSS && typeof window.CSS.escape === 'function') {
        return window.CSS.escape(value);
    }
    return value.replace(/"/g, '\\"');
}
