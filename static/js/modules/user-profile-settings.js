import { api } from './fetch-wrapper.js';
import { showToast } from './toast.js';

const CALIBRATION_MODE_TEXT = {
    off: 'Off — learned suggestions are disabled',
    suggest: 'On — Workout Controls learns from your recent scored logs',
};

function updateCalibrationStatusText(mode, allowRelated = false) {
    const text = document.querySelector('[data-calibration-text]');
    if (text) {
        if (mode === 'suggest' && allowRelated) {
            text.textContent = 'On — exact and related learned suggestions are enabled';
        } else {
            text.textContent = CALIBRATION_MODE_TEXT[mode] || CALIBRATION_MODE_TEXT.off;
        }
    }
}

function readCalibrationForm(form) {
    const checkedMode = form.querySelector('input[name="calibration_mode"]:checked');
    const related = form.querySelector('input[name="allow_related_exercise_learning"]');
    const mode = checkedMode ? checkedMode.value : 'off';
    return {
        mode,
        allow_related_exercise_learning: mode === 'suggest' && Boolean(related?.checked),
    };
}

function syncRelatedCalibrationControl(form, settings) {
    const related = form.querySelector('input[name="allow_related_exercise_learning"]');
    if (!related) return;
    related.disabled = settings.mode !== 'suggest';
    if (settings.mode !== 'suggest') {
        related.checked = false;
    }
}

function bindCalibrationSettings() {
    const form = document.getElementById('profile-calibration-form');
    if (!form) return;
    let currentSettings = readCalibrationForm(form);
    syncRelatedCalibrationControl(form, currentSettings);
    updateCalibrationStatusText(
        currentSettings.mode,
        currentSettings.allow_related_exercise_learning,
    );

    form.addEventListener('change', async (event) => {
        const input = event.target;
        if (
            !input
            || !['calibration_mode', 'allow_related_exercise_learning'].includes(input.name)
        ) return;
        const previousSettings = currentSettings;
        const settings = readCalibrationForm(form);
        syncRelatedCalibrationControl(form, settings);
        try {
            const response = await api.post(
                '/api/user_profile/calibration_settings',
                settings,
            );
            const saved = {
                ...settings,
                ...(response?.data || {}),
            };
            currentSettings = saved;
            syncRelatedCalibrationControl(form, saved);
            updateCalibrationStatusText(saved.mode, saved.allow_related_exercise_learning);
            showToast(
                'success',
                saved.mode === 'suggest'
                    ? 'Learned suggestions enabled'
                    : 'Learned suggestions turned off',
            );
        } catch (error) {
            const modeInput = form.querySelector(
                `input[name="calibration_mode"][value="${previousSettings.mode}"]`,
            );
            if (modeInput) modeInput.checked = true;
            const related = form.querySelector('input[name="allow_related_exercise_learning"]');
            if (related) related.checked = previousSettings.allow_related_exercise_learning;
            syncRelatedCalibrationControl(form, previousSettings);
            updateCalibrationStatusText(
                previousSettings.mode,
                previousSettings.allow_related_exercise_learning,
            );
            showToast('error', error?.message || 'Failed to save calibration settings', {
                requestId: error?.requestId,
            });
        }
    });
}

// =============================================================================
// Phase 2D-A — Fatigue context settings (independent of learned calibration)
// =============================================================================
// Advisory-only toggle. Persists to /api/user_profile/fatigue_context_settings;
// the estimate response then carries an additive `fatigue_context` block the
// Plan page renders inside "show the math". No estimator math is touched here.

function readFatigueContextForm(form) {
    const enabled = Boolean(
        form.querySelector('input[name="fatigue_context_enabled"]')?.checked,
    );
    const source = form.querySelector('select[name="fatigue_context_source"]')?.value || 'both';
    const period = form.querySelector('select[name="fatigue_context_period"]')?.value || 'this_week';
    return { enabled, context_source: source, context_period: period };
}

function syncFatigueContextControls(form, settings) {
    const source = form.querySelector('select[name="fatigue_context_source"]');
    const period = form.querySelector('select[name="fatigue_context_period"]');
    if (source) source.disabled = !settings.enabled;
    if (period) period.disabled = !settings.enabled;
}

function updateFatigueContextStatusText(settings) {
    const text = document.querySelector('[data-fatigue-context-text]');
    if (!text) return;
    text.textContent = settings.enabled
        ? 'On — fatigue context shown in Workout Controls details'
        : 'Off — fatigue context is hidden';
}

function bindFatigueContextSettings() {
    const form = document.getElementById('profile-fatigue-context-form');
    if (!form) return;
    let currentSettings = readFatigueContextForm(form);
    syncFatigueContextControls(form, currentSettings);
    updateFatigueContextStatusText(currentSettings);

    form.addEventListener('change', async (event) => {
        const input = event.target;
        if (
            !input
            || ![
                'fatigue_context_enabled',
                'fatigue_context_source',
                'fatigue_context_period',
            ].includes(input.name)
        ) return;
        const previousSettings = currentSettings;
        const settings = readFatigueContextForm(form);
        syncFatigueContextControls(form, settings);
        try {
            const response = await api.post(
                '/api/user_profile/fatigue_context_settings',
                settings,
            );
            const saved = { ...settings, ...(response?.data || {}) };
            currentSettings = saved;
            syncFatigueContextControls(form, saved);
            updateFatigueContextStatusText(saved);
            showToast(
                'success',
                saved.enabled ? 'Fatigue context enabled' : 'Fatigue context turned off',
            );
        } catch (error) {
            const enabledInput = form.querySelector('input[name="fatigue_context_enabled"]');
            if (enabledInput) enabledInput.checked = previousSettings.enabled;
            const sourceSel = form.querySelector('select[name="fatigue_context_source"]');
            if (sourceSel) sourceSel.value = previousSettings.context_source;
            const periodSel = form.querySelector('select[name="fatigue_context_period"]');
            if (periodSel) periodSel.value = previousSettings.context_period;
            syncFatigueContextControls(form, previousSettings);
            updateFatigueContextStatusText(previousSettings);
            showToast('error', error?.message || 'Failed to save fatigue context settings', {
                requestId: error?.requestId,
            });
        }
    });
}

export {
    bindCalibrationSettings,
    bindFatigueContextSettings,
};
