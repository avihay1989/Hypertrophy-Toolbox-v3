// KI-005 — Workout Controls persistence across reload.
//
// Persists the six Workout Controls (weight, sets, RIR, RPE, min-rep, max-rep)
// for the current tab so a page refresh mid-entry does not discard them.
//
// Contract (owner rulings recorded in docs/ki005_controls_persistence/PLANNING.md):
//   - Storage (OWNER-3): ONE JSON record under the single namespaced, versioned
//     key `hypertrophy_workout_controls_v1`. Never six keys, never an
//     unversioned name. `sessionStorage` only — never `localStorage`, so the
//     values die with the tab (criterion 6).
//   - Hydration guard (OWNER-1): every save path — listener or programmatic —
//     is a no-op while hydration is active, so initial default population can
//     never overwrite an existing stored record before restore has run.
//   - Fallback (TS-7): a missing / malformed / non-numeric / out-of-range
//     stored value falls back to the pinned template default for that field —
//     never to a per-exercise recommendation.
//
// Storage failures (private mode, quota, disabled storage) degrade silently to
// the pre-KI-005 behavior (reset-on-reload); they never throw into the caller.

const STORAGE_KEY = 'hypertrophy_workout_controls_v1';

/** The six controls — exactly these, no others (criterion 2). */
export const WORKOUT_CONTROL_IDS = ['weight', 'sets', 'rir', 'rpe', 'min_rep', 'max_rep_range'];

/**
 * The pinned template defaults (TS-7 ruling). Also the values
 * `initializeDefaultValues()` populates, so the defaults live in one place.
 */
export const WORKOUT_CONTROL_DEFAULTS = {
    weight: '25',
    sets: '3',
    rir: '3',
    rpe: '7',
    min_rep: '6',
    max_rep_range: '8',
};

let hydrating = false;

export function beginHydration() {
    hydrating = true;
}

export function endHydration() {
    hydrating = false;
}

/**
 * Run `fn` with every save path suppressed (OWNER-1). Used by hydration and by
 * the Clear Plan reset, which must repopulate the DOM without re-saving.
 */
export function withHydrationSuppressed(fn) {
    const previous = hydrating;
    hydrating = true;
    try {
        return fn();
    } finally {
        hydrating = previous;
    }
}

/** sessionStorage, or null when it is unavailable (private mode / disabled). */
function getStore() {
    try {
        return window.sessionStorage;
    } catch {
        return null;
    }
}

function readRecord() {
    const store = getStore();
    if (!store) return null;
    let raw;
    try {
        raw = store.getItem(STORAGE_KEY);
    } catch {
        return null;
    }
    if (!raw) return null;
    try {
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch {
        // Malformed record: present but unusable — every field falls back.
        return {};
    }
}

/**
 * The field's declared bounds — and ONLY those (OWNER-5). "Out of range" is
 * whatever the input's own `min` / `max` attributes say, so it bites on `#rir`
 * / `#rpe` (max 10) and on every field's `min`. Fields the template leaves
 * unbounded above (weight, sets, min-rep, max-rep) have NO upper bound here:
 * inventing one would be an implementer-authored product rule, and a reload
 * must be a no-op. `utils/workout_validation.py:65-71` still rejects an absurd
 * value server-side at add time — exactly as it would if the user typed it
 * without ever reloading.
 */
function declaredRange(input) {
    const minAttr = parseFloat(input?.getAttribute('min'));
    const maxAttr = parseFloat(input?.getAttribute('max'));
    return {
        min: Number.isFinite(minAttr) ? minAttr : undefined,
        max: Number.isFinite(maxAttr) ? maxAttr : undefined,
    };
}

/**
 * Validate one stored value against its field. Returns the value to apply as a
 * string, or null when the stored value must be ignored (criterion 9).
 */
function validateStoredValue(stored, input) {
    if (stored === undefined || stored === null) return null;
    if (typeof stored !== 'string' && typeof stored !== 'number') return null;

    const text = String(stored).trim();
    if (text === '') return null;

    const parsed = Number(text);
    if (!Number.isFinite(parsed)) return null;

    const { min, max } = declaredRange(input);
    if (min !== undefined && parsed < min) return null;
    if (max !== undefined && parsed > max) return null;

    return text;
}

/**
 * Write the six currently-displayed control values as one JSON record.
 * No-op while hydration is active (OWNER-1) and on any storage failure.
 */
export function saveWorkoutControls() {
    if (hydrating) return;
    const store = getStore();
    if (!store) return;

    const record = {};
    let found = false;
    for (const field of WORKOUT_CONTROL_IDS) {
        const input = document.getElementById(field);
        if (!input) continue;
        record[field] = input.value;
        found = true;
    }
    if (!found) return;

    try {
        store.setItem(STORAGE_KEY, JSON.stringify(record));
    } catch {
        // Quota / disabled storage — degrade to reset-on-reload.
    }
}

/**
 * Apply the pinned template defaults to the six fields. Plain value writes —
 * no estimate, no fatigue-context recompute (PR-1).
 */
export function applyWorkoutControlDefaults() {
    for (const field of WORKOUT_CONTROL_IDS) {
        const input = document.getElementById(field);
        if (input) {
            input.value = WORKOUT_CONTROL_DEFAULTS[field];
        }
    }
}

/**
 * Restore the stored record into the six fields, saved-wins over the
 * server-rendered defaults (criterion 8). Invalid fields fall back to the
 * pinned defaults (criterion 9). Never writes to storage — the caller runs this
 * under the hydration guard, so a pre-existing record survives init untouched
 * (OWNER-1.1/.2).
 *
 * @returns {{restored: string[]}} the fields that took a valid stored value.
 */
export function restoreWorkoutControls() {
    const record = readRecord();
    if (record === null) return { restored: [] };

    const restored = [];
    for (const field of WORKOUT_CONTROL_IDS) {
        const input = document.getElementById(field);
        if (!input) continue;
        const value = validateStoredValue(record[field], input);
        if (value === null) {
            input.value = WORKOUT_CONTROL_DEFAULTS[field];
        } else {
            input.value = value;
            restored.push(field);
        }
    }
    return { restored };
}

/** Remove the stored record, leaving the key ABSENT (OWNER-1.4). */
export function clearWorkoutControls() {
    const store = getStore();
    if (!store) return;
    try {
        store.removeItem(STORAGE_KEY);
    } catch {
        // Nothing to do — storage is unavailable.
    }
}
