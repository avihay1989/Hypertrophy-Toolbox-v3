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

function responseMessage(response, fallback) {
    return response && typeof response.message === 'string' && response.message.trim()
        ? response.message
        : fallback;
}

async function saveSection(form, buildPayload, endpoint, fallbackMessage) {
    const submitButton = form.querySelector('button[type="submit"]');
    const originalDisabled = submitButton?.disabled ?? false;
    if (submitButton) {
        submitButton.disabled = true;
    }

    try {
        const response = await api.post(endpoint, buildPayload(form));
        showToast('success', responseMessage(response, fallbackMessage));
    } catch (error) {
        const message = error?.message || 'Unable to save profile section.';
        showToast('error', message, { requestId: error?.requestId });
    } finally {
        if (submitButton) {
            submitButton.disabled = originalDisabled;
        }
    }
}

function bindForm(formId, buildPayload, endpoint, fallbackMessage) {
    const form = document.getElementById(formId);
    if (!form) {
        return;
    }

    form.addEventListener('submit', event => {
        event.preventDefault();
        saveSection(form, buildPayload, endpoint, fallbackMessage);
    });
}

export function initializeUserProfile() {
    bindForm('profile-demographics-form', profilePayload, '/api/user_profile', 'Profile saved');
    bindForm('profile-lifts-form', liftPayload, '/api/user_profile/lifts', 'Reference lifts saved');
    bindForm('profile-preferences-form', preferencesPayload, '/api/user_profile/preferences', 'Preferences saved');
}

document.addEventListener('DOMContentLoaded', initializeUserProfile);
