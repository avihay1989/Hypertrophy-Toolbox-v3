// Workout Controls profile-estimate / learned-calibration / fatigue-context /
// trace / nudge cluster. Extracted from workout-plan.js (WP3.4c) as a
// behavior-preserving move: the monolith imports the three entry points
// (applyUserProfileEstimateForSelectedExercise, initializeWeightDirtyTracking,
// bindEstimateTraceToggle) and re-exports the first to preserve its surface.
import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';
import { saveWorkoutControls } from './workout-controls-persistence.js';
import {
    computeNudgedValue,
    estimateProvenanceLabel,
    fatigueChipTitle,
    learnedBadgeText,
    resolveMin,
    resolveProfileEstimate,
    resolveStep,
    traceHeadline,
    traceStepValueText,
} from './workout-plan-helpers.js';

function setWorkoutControlValue(id, value) {
    const field = document.getElementById(id);
    if (!field || value === undefined || value === null) {
        return;
    }
    field.value = String(value);
}

// Tracks whether the user has manually edited the Weight input since the last
// exercise selection. While true, the profile estimate must not overwrite the
// user's value (Issue #5).
let weightUserDirty = false;

export function resetWeightUserDirty() {
    weightUserDirty = false;
}

function markWeightUserDirty() {
    weightUserDirty = true;
}

export function initializeWeightDirtyTracking() {
    const weightInput = document.getElementById('weight');
    if (!weightInput || weightInput.dataset.dirtyTracked === 'true') return;
    weightInput.addEventListener('input', markWeightUserDirty);
    weightInput.dataset.dirtyTracked = 'true';
}

function applyEstimateToWorkoutControls(estimate) {
    const resolved = resolveProfileEstimate(estimate);
    if (!weightUserDirty) {
        setWorkoutControlValue('weight', resolved.weight);
    }
    setWorkoutControlValue('sets', resolved.sets);
    setWorkoutControlValue('min_rep', resolved.min_rep);
    setWorkoutControlValue('max_rep_range', resolved.max_rep);
    setWorkoutControlValue('rir', resolved.rir);
    setWorkoutControlValue('rpe', resolved.rpe);

    const provenance = document.getElementById('workout-estimate-provenance');
    if (provenance) {
        provenance.textContent = estimateProvenanceLabel(resolved.source);
    }

    updateLearnedBadge(resolved);
    updateFatigueContextChip(resolved);

    const handHint = document.getElementById('weight-hand-hint');
    if (handHint) {
        handHint.hidden = !resolved.is_dumbbell;
    }

    updateEstimateTraceUI(resolved);

    // KI-005 / OWNER-9: this is one complete logical control update — ordinary
    // estimate application AND the learned-reset / ignore-transfer re-apply both
    // arrive here. `setWorkoutControlValue()` writes `field.value` directly (no
    // `input` event), so no capture listener runs; persist once, after all six
    // fields are settled, so the stored record matches what is displayed.
    saveWorkoutControls();
}

// KI-005 / OWNER-10 — neutralize the estimate-ONLY UI so it no longer claims or
// acts on an exercise that is no longer the displayed one. Two callers:
//   - empty selection (the exercise dropdown was cleared) — the six controls and
//     their stored record are left untouched (criterion 5), but the stale
//     provenance / badge / chip / hand hint / trace and its action controls must
//     not keep describing (or operating on) the de-selected exercise; and
//   - a successful Add Exercise — Reading A retains the user's own control values
//     (criterion 3), which no longer necessarily match the estimate metadata, so
//     that metadata must not falsely claim to have produced them.
// Display/state cleanup ONLY: it writes NO control value, issues NO estimate
// request, recomputes NO fatigue, and mutates NO calibration (PR-1). If the
// provenance label stays visible it carries neutral wording ("current values") —
// never a false source claim.
export function neutralizeEstimateState() {
    // Forget the remembered estimate so the learned Apply/Keep/Reset actions, the
    // ± nudges, and "Reset to suggestion" — all of which read latestTracePayload —
    // cannot act on the de-selected exercise even if a stray node lingered.
    latestTracePayload = null;

    const provenance = document.getElementById('workout-estimate-provenance');
    if (provenance) {
        provenance.textContent = 'current values';
    }

    const badge = document.getElementById('workout-estimate-learned-badge');
    if (badge) {
        badge.hidden = true;
        badge.dataset.confidence = '';
        badge.removeAttribute('title');
    }

    const chip = document.getElementById('workout-estimate-fatigue-chip');
    if (chip) {
        chip.hidden = true;
        chip.removeAttribute('title');
    }

    const handHint = document.getElementById('weight-hand-hint');
    if (handHint) {
        handHint.hidden = true;
    }

    // The learned Apply/Keep/Reset row and the ± nudge / Reset-to-suggestion row
    // are rendered INSIDE the trace container. Clearing + hiding it (and hiding
    // its toggle) removes those action controls, so none stays rendered and
    // operable against a phantom prior exercise.
    const toggle = document.getElementById('workout-estimate-trace-toggle');
    const container = document.getElementById('workout-estimate-trace');
    if (container) {
        container.innerHTML = '';
        container.hidden = true;
    }
    if (toggle) {
        toggle.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        const labelEl = toggle.querySelector('.workout-estimate-trace-toggle-label');
        if (labelEl) labelEl.textContent = 'Show the math';
    }
}

// Learned Calibration — compact source badge next to the provenance line.
// Shown only when the estimator returned a learned suggestion (settings mode
// `suggest` + usable confidence). The confidence drives the badge tint.
function updateLearnedBadge(estimate) {
    const badge = document.getElementById('workout-estimate-learned-badge');
    if (!badge) return;
    const info = learnedBadgeText(estimate);
    if (!info.isLearned) {
        badge.hidden = true;
        badge.dataset.confidence = '';
        badge.removeAttribute('title');
        return;
    }
    badge.hidden = false;
    badge.dataset.confidence = info.confidence;
    const label = badge.querySelector('.workout-estimate-learned-badge-label');
    if (label) {
        label.textContent = info.label;
    }
    badge.title = info.title;
}

// Fatigue context (Phase 2D-A) — neutral, non-source chip next to the
// provenance line. Shown only when the estimate carries the additive
// `fatigue_context` advisory block (its own default-off Profile toggle). It is
// deliberately NOT confidence-tinted and NEVER implies the number changed.
function updateFatigueContextChip(estimate) {
    const chip = document.getElementById('workout-estimate-fatigue-chip');
    if (!chip) return;
    const fatigue = estimate?.fatigue_context;
    if (!fatigue) {
        chip.hidden = true;
        chip.removeAttribute('title');
        return;
    }
    chip.hidden = false;
    chip.title = fatigueChipTitle(fatigue);
}

// Force the current learned suggestion into the Workout Controls inputs.
// Client-side only — populates inputs, never persists to user_selection
// (plan §"User Actions": Apply suggestion is client-side for the MVP).
function applyLearnedSuggestionToInputs() {
    const estimate = latestTracePayload;
    if (!estimate) return;
    setWorkoutControlValue('weight', estimate.weight);
    setWorkoutControlValue('sets', estimate.sets);
    setWorkoutControlValue('min_rep', estimate.min_rep);
    setWorkoutControlValue('max_rep_range', estimate.max_rep);
    setWorkoutControlValue('rir', estimate.rir);
    setWorkoutControlValue('rpe', estimate.rpe);
    // The user explicitly accepted the suggestion, so the weight is no longer a
    // pending manual edit — let later estimates flow in again.
    resetWeightUserDirty();
    // KI-005 / OWNER-9: persist once, after the complete logical update, so the
    // applied suggestion survives a reload (the writes above fire no `input`).
    saveWorkoutControls();
    showToast('Suggestion applied');
}

async function resetLearnedForCurrentExercise() {
    const exerciseName = document.getElementById('exercise')?.value || '';
    if (!exerciseName) return;
    try {
        await api.post('/api/user_profile/calibration/reset', { exercise: exerciseName });
        showToast('success', 'Learned data reset for this exercise');
        // Re-fetch so the controls fall back to the last-log / Profile estimate.
        await applyUserProfileEstimateForSelectedExercise();
    } catch (error) {
        showToast('error', error?.message || 'Failed to reset learned data', {
            requestId: error?.requestId,
        });
    }
}

async function ignoreRelatedTransferForCurrentExercise() {
    const estimate = latestTracePayload;
    const sourceExercise = estimate?.trace?.source_exercise || '';
    const targetExercise = estimate?.trace?.target_exercise
        || document.getElementById('exercise')?.value
        || '';
    if (!sourceExercise || !targetExercise) return;
    try {
        await api.post('/api/user_profile/calibration/ignore_transfer', {
            source_exercise: sourceExercise,
            target_exercise: targetExercise,
        });
        showToast('success', 'Related suggestion ignored for this exercise');
        await applyUserProfileEstimateForSelectedExercise();
    } catch (error) {
        showToast('error', error?.message || 'Failed to ignore related suggestion', {
            requestId: error?.requestId,
        });
    }
}

// Issue #17 — Plan-page "show the math" trace expander.
// The estimator (utils/profile_estimator.py) is the single source of truth
// for the trace shape. This module just renders it on click — it never
// reconstructs the math.
let latestTracePayload = null;

function updateEstimateTraceUI(estimate) {
    latestTracePayload = estimate || null;
    const toggle = document.getElementById('workout-estimate-trace-toggle');
    const container = document.getElementById('workout-estimate-trace');
    if (!toggle || !container) return;

    const trace = estimate?.trace;
    const hasTrace = Boolean(trace && Array.isArray(trace.steps) && trace.steps.length > 0);
    if (!hasTrace) {
        toggle.hidden = true;
        container.hidden = true;
        container.innerHTML = '';
        toggle.setAttribute('aria-expanded', 'false');
        return;
    }
    toggle.hidden = false;
    // Collapse on each new estimate so the user opts back in for the new exercise.
    toggle.setAttribute('aria-expanded', 'false');
    container.hidden = true;
    container.innerHTML = '';
}

function renderEstimateTrace(estimate) {
    const container = document.getElementById('workout-estimate-trace');
    if (!container) return;
    container.innerHTML = '';
    const trace = estimate?.trace;
    if (!trace) return;

    const headline = document.createElement('p');
    headline.className = 'workout-estimate-trace-headline';
    headline.textContent = traceHeadline(trace.source);
    container.appendChild(headline);

    const list = document.createElement('ul');
    list.className = 'workout-estimate-trace-steps';
    for (const step of trace.steps) {
        const li = document.createElement('li');
        const labelEl = document.createElement('span');
        labelEl.className = 'workout-estimate-trace-step-label';
        labelEl.textContent = step.label;
        li.appendChild(labelEl);

        const valueText = traceStepValueText(step);
        if (valueText) {
            const valueEl = document.createElement('span');
            valueEl.className = 'workout-estimate-trace-step-value';
            valueEl.textContent = valueText;
            li.appendChild(valueEl);
        }

        if (step.detail) {
            const detailEl = document.createElement('small');
            detailEl.className = 'workout-estimate-trace-step-detail';
            detailEl.textContent = step.detail;
            li.appendChild(detailEl);
        }

        list.appendChild(li);
    }
    container.appendChild(list);

    // Phase 2D-A — advisory fatigue context, rendered as its own distinct
    // section BELOW the strength evidence. Never merged into the strength
    // steps; always carries the "does not change your suggestion" line.
    const fatigueSection = buildFatigueContextSection(estimate?.fatigue_context);
    if (fatigueSection) container.appendChild(fatigueSection);

    if (trace.improvement_hint?.copy) {
        const hint = document.createElement('p');
        hint.className = 'workout-estimate-trace-hint';
        const slug = trace.improvement_hint.lift_key;
        const link = document.createElement('a');
        link.href = slug
            ? `/user_profile#lift-${slug}-weight`
            : '/user_profile';
        link.textContent = 'Open Profile →';
        link.setAttribute('data-trace-improvement-link', '');
        hint.appendChild(document.createTextNode(trace.improvement_hint.copy + ' '));
        hint.appendChild(link);
        container.appendChild(hint);
    }

    if (['learned', 'related_learned'].includes(trace.source)) {
        container.appendChild(buildLearnedActions());
    }
}

// Build the advisory "Fatigue context" block for the trace details. Returns
// null when the estimate carries no fatigue_context (toggle off / no muscle).
// Read-only: an eyebrow, a headline, and the mandatory advisory line.
function buildFatigueContextSection(fatigue) {
    if (!fatigue) return null;
    const section = document.createElement('div');
    section.className = 'workout-estimate-fatigue';
    section.setAttribute('data-fatigue-context', '');

    const eyebrow = document.createElement('p');
    eyebrow.className = 'workout-estimate-fatigue-eyebrow';
    eyebrow.textContent = 'Fatigue context';
    section.appendChild(eyebrow);

    if (fatigue.headline) {
        const headline = document.createElement('p');
        headline.className = 'workout-estimate-fatigue-headline';
        headline.textContent = fatigue.headline;
        section.appendChild(headline);
    }

    const advisory = document.createElement('small');
    advisory.className = 'workout-estimate-fatigue-advisory';
    advisory.textContent = fatigue.advisory || 'This does not change your suggestion.';
    section.appendChild(advisory);

    // Phase 2D-C — optional manual-adjustment affordance. Neutral ± steppers for
    // Weight and Sets plus "Reset to suggestion". Client-side only: it edits the
    // Workout Controls inputs and never persists or calls an API (mirrors the MVP
    // `Apply suggestion` contract). It deliberately uses the inputs' own manual
    // step — NOT a fatigue-derived magnitude (that mapping is gated to 2D-D).
    section.appendChild(buildFatigueNudgeControls());

    return section;
}

// Resolve the manual step / floor of a Workout Controls number input from its
// own attributes. `step="any"` (weight) and an absent step (sets) both fall back
// to 1 — i.e. the input's native arrow-key step. No fatigue math here.
function resolveControlStep(input) {
    return resolveStep(input.getAttribute('step'));
}

function resolveControlMin(input) {
    return resolveMin(input.getAttribute('min'));
}

// Step a Workout Controls input up/down by its own manual step, clamped to the
// input's `min`. Client-side only — sets the value directly (no input event, so
// it never marks the weight "user-dirty" or triggers a re-estimate).
function nudgeWorkoutControl(id, direction) {
    const field = document.getElementById(id);
    if (!field) return;
    const step = resolveControlStep(field);
    const min = resolveControlMin(field);
    const current = parseFloat(field.value);
    const next = computeNudgedValue(current, step, min, direction);
    setWorkoutControlValue(id, next);
    // KI-005 / OWNER-9: a nudge is one complete logical control update. It writes
    // `field.value` directly (no `input` event, deliberately), so persist here or
    // the nudged value is lost on reload.
    saveWorkoutControls();
}

// Restore the estimator's original Weight + Sets exactly from the last estimate.
// `latestTracePayload` is the resolved estimate that was applied to the inputs,
// so this re-applies the suggestion the user is choosing to step away from.
function resetWorkoutControlsToSuggestion() {
    const estimate = latestTracePayload;
    if (!estimate) return;
    setWorkoutControlValue('weight', estimate.weight);
    setWorkoutControlValue('sets', estimate.sets);
    // KI-005 / OWNER-9: "Reset to suggestion" is one complete logical control
    // update; persist the reset values so they survive a reload.
    saveWorkoutControls();
}

// Build one labeled ± stepper group for a single Workout Controls input.
function buildFatigueNudgeGroup(id, label) {
    const group = document.createElement('div');
    group.className = 'workout-estimate-fatigue-nudge-group';

    const name = document.createElement('span');
    name.className = 'workout-estimate-fatigue-nudge-name';
    name.textContent = label;
    group.appendChild(name);

    for (const direction of ['down', 'up']) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'workout-estimate-fatigue-nudge-btn';
        btn.setAttribute('data-nudge', id);
        btn.setAttribute('data-nudge-dir', direction);
        btn.setAttribute(
            'aria-label',
            `${direction === 'down' ? 'Decrease' : 'Increase'} ${label.toLowerCase()}`,
        );
        btn.textContent = direction === 'down' ? '−' : '+';
        btn.addEventListener('click', () => nudgeWorkoutControl(id, direction));
        group.appendChild(btn);
    }
    return group;
}

// Build the manual nudge block appended to the fatigue context section. Only
// renders a stepper for a control that actually exists in Workout Controls
// (weight + sets per Phase 2D-C scope; reps deferred to a later slice).
function buildFatigueNudgeControls() {
    const wrap = document.createElement('div');
    wrap.className = 'workout-estimate-fatigue-nudge';
    wrap.setAttribute('data-fatigue-nudge', '');

    const label = document.createElement('p');
    label.className = 'workout-estimate-fatigue-nudge-label';
    label.textContent = 'Adjust manually';
    wrap.appendChild(label);

    const row = document.createElement('div');
    row.className = 'workout-estimate-fatigue-nudge-row';
    for (const spec of [{ id: 'weight', label: 'Weight' }, { id: 'sets', label: 'Sets' }]) {
        if (!document.getElementById(spec.id)) continue;
        row.appendChild(buildFatigueNudgeGroup(spec.id, spec.label));
    }
    wrap.appendChild(row);

    const reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'workout-estimate-trace-action is-reset';
    reset.setAttribute('data-fatigue-nudge-reset', '');
    reset.textContent = 'Reset to suggestion';
    reset.addEventListener('click', resetWorkoutControlsToSuggestion);
    wrap.appendChild(reset);

    return wrap;
}

// Apply / Keep / Reset row shown inside the learned-suggestion details. Apply
// is client-side only; Reset clears the stored row and re-fetches the estimate.
function buildLearnedActions() {
    const actions = document.createElement('div');
    actions.className = 'workout-estimate-trace-actions';

    const apply = document.createElement('button');
    apply.type = 'button';
    apply.className = 'workout-estimate-trace-action is-primary';
    apply.setAttribute('data-learned-apply', '');
    apply.textContent = 'Apply suggestion';
    apply.addEventListener('click', applyLearnedSuggestionToInputs);

    const keep = document.createElement('button');
    keep.type = 'button';
    keep.className = 'workout-estimate-trace-action';
    keep.setAttribute('data-learned-keep', '');
    keep.textContent = 'Keep current';
    keep.addEventListener('click', collapseEstimateTrace);

    const reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'workout-estimate-trace-action is-reset';
    reset.setAttribute('data-learned-reset', '');
    reset.textContent = 'Reset learned data';
    reset.addEventListener('click', resetLearnedForCurrentExercise);

    actions.append(apply, keep, reset);
    if (latestTracePayload?.source === 'related_learned') {
        const ignore = document.createElement('button');
        ignore.type = 'button';
        ignore.className = 'workout-estimate-trace-action is-reset';
        ignore.setAttribute('data-related-ignore', '');
        ignore.textContent = 'Ignore this source';
        ignore.addEventListener('click', ignoreRelatedTransferForCurrentExercise);
        actions.append(ignore);
    }
    return actions;
}

function collapseEstimateTrace() {
    const toggle = document.getElementById('workout-estimate-trace-toggle');
    const container = document.getElementById('workout-estimate-trace');
    if (!toggle || !container) return;
    toggle.setAttribute('aria-expanded', 'false');
    container.hidden = true;
    const labelEl = toggle.querySelector('.workout-estimate-trace-toggle-label');
    if (labelEl) labelEl.textContent = 'Show the math';
}

export function bindEstimateTraceToggle() {
    const toggle = document.getElementById('workout-estimate-trace-toggle');
    const container = document.getElementById('workout-estimate-trace');
    if (!toggle || !container) return;
    toggle.addEventListener('click', () => {
        const expanded = toggle.getAttribute('aria-expanded') === 'true';
        const next = !expanded;
        toggle.setAttribute('aria-expanded', String(next));
        container.hidden = !next;
        if (next && latestTracePayload && container.children.length === 0) {
            renderEstimateTrace(latestTracePayload);
        }
        const labelEl = toggle.querySelector('.workout-estimate-trace-toggle-label');
        if (labelEl) {
            labelEl.textContent = next ? 'Hide the math' : 'Show the math';
        }
    });
}

export async function applyUserProfileEstimateForSelectedExercise() {
    const exerciseName = document.getElementById('exercise')?.value || '';

    try {
        const response = await api.get(
            `/api/user_profile/estimate?exercise=${encodeURIComponent(exerciseName)}`,
            { showLoading: false, showErrorToast: false, retries: 0 }
        );
        applyEstimateToWorkoutControls(response.data || response);
    } catch (error) {
        console.warn('Unable to apply user profile estimate:', error);
        applyEstimateToWorkoutControls(null);
    }
}
