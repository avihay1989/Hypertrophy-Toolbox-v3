import { api } from './fetch-wrapper.js';
import { showToast } from './toast.js';

function nullableValue(value) {
    const trimmed = String(value ?? '').trim();
    return trimmed === '' ? null : trimmed;
}

function profilePayload(form) {
    const formData = new FormData(form);
    return {
        gender: nullableValue(formData.get('gender')),
        age: nullableValue(formData.get('age')),
        height_cm: nullableValue(formData.get('height_cm')),
        weight_kg: nullableValue(formData.get('weight_kg')),
        experience_years: nullableValue(formData.get('experience_years')),
    };
}

function liftPayload(form) {
    return Array.from(form.querySelectorAll('.reference-lift-row')).map(row => ({
        lift_key: row.dataset.liftKey,
        weight_kg: nullableValue(row.querySelector('[name="weight_kg"]')?.value),
        reps: nullableValue(row.querySelector('[name="reps"]')?.value),
    }));
}

function preferencesPayload(form) {
    return Array.from(form.querySelectorAll('.preference-group')).reduce((payload, group) => {
        const checked = group.querySelector('input[type="radio"]:checked');
        if (checked) {
            payload[group.dataset.tier] = checked.value;
        }
        return payload;
    }, {});
}

const AUTOSAVE_DEBOUNCE_MS = 700;

function formatTimeHHMM(date) {
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
}

function setAutosaveStatus(form, state, options = {}) {
    const pill = form.querySelector('[data-autosave-status]');
    if (!pill) return;
    const text = pill.querySelector('[data-autosave-text]');
    const retry = pill.querySelector('[data-autosave-retry]');
    pill.dataset.autosaveStatus = state;
    if (retry) retry.hidden = state !== 'error';
    if (!text) return;
    if (state === 'idle') {
        text.textContent = options.message || 'Changes save automatically';
    } else if (state === 'pending') {
        text.textContent = 'Unsaved changes…';
    } else if (state === 'saving') {
        text.textContent = 'Saving…';
    } else if (state === 'saved') {
        text.textContent = `Saved · ${formatTimeHHMM(options.savedAt || new Date())}`;
    } else if (state === 'error') {
        text.textContent = options.message || 'Save failed';
    }
}

async function performSave(form, buildPayload, endpoint) {
    setAutosaveStatus(form, 'saving');
    try {
        const response = await api.post(endpoint, buildPayload(form), {
            showLoading: false,
            showErrorToast: false,
        });
        setAutosaveStatus(form, 'saved', { savedAt: new Date() });
        return response;
    } catch (error) {
        const message = error?.message || 'Unable to save profile section.';
        setAutosaveStatus(form, 'error', { message: `Save failed — ${message}` });
        showToast('error', message, { requestId: error?.requestId });
        throw error;
    }
}

function bindAutosaveForm(formId, buildPayload, endpoint, options = {}) {
    const form = document.getElementById(formId);
    if (!form) {
        return;
    }

    const debounceMs = options.debounceMs ?? AUTOSAVE_DEBOUNCE_MS;
    let timer = null;
    let inFlight = null;
    let pendingAfterFlight = false;

    const flush = async () => {
        if (inFlight) {
            pendingAfterFlight = true;
            return;
        }
        inFlight = performSave(form, buildPayload, endpoint)
            .catch(() => {})
            .finally(() => {
                inFlight = null;
                if (pendingAfterFlight) {
                    pendingAfterFlight = false;
                    schedule(0);
                }
            });
    };

    const schedule = (delay = debounceMs) => {
        if (timer) clearTimeout(timer);
        setAutosaveStatus(form, 'pending');
        timer = setTimeout(() => {
            timer = null;
            flush();
        }, delay);
    };

    form.addEventListener('submit', event => {
        event.preventDefault();
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
        flush();
    });

    const inputDelay = options.inputImmediate ? 0 : debounceMs;
    form.addEventListener('input', () => schedule(inputDelay));
    form.addEventListener('change', () => schedule(options.changeImmediate ? 0 : inputDelay));

    form.querySelector('[data-autosave-retry]')?.addEventListener('click', () => {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
        flush();
    });
}

function initializeCollapseToggles() {
    const toggleButtons = document.querySelectorAll('.user-profile-page .collapse-toggle');
    toggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            const frame = button.closest('.collapsible-frame');
            if (!frame) return;
            const wasExpanded = button.getAttribute('aria-expanded') === 'true';
            const nowExpanded = !wasExpanded;
            frame.classList.toggle('collapsed', !nowExpanded);
            button.setAttribute('aria-expanded', String(nowExpanded));
            const icon = button.querySelector('.toggle-icon');
            if (icon) {
                icon.classList.toggle('fa-chevron-up', nowExpanded);
                icon.classList.toggle('fa-chevron-down', !nowExpanded);
            }
            const text = button.querySelector('.toggle-text');
            if (text) {
                text.textContent = nowExpanded ? 'Hide' : 'Show';
            }
        });
    });
}

export function initializeProfileForms() {
    bindAutosaveForm('profile-demographics-form', profilePayload, '/api/user_profile');
    bindAutosaveForm('profile-lifts-form', liftPayload, '/api/user_profile/lifts');
    bindAutosaveForm(
        'profile-preferences-form',
        preferencesPayload,
        '/api/user_profile/preferences',
        { changeImmediate: true },
    );
    initializeCollapseToggles();
}
