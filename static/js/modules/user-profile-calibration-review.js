import { api } from './fetch-wrapper.js';
import { showToast } from './toast.js';

// =============================================================================
// Phase 2B — Learned calibration review/control surface
// =============================================================================
// Read/control-only: lists are populated from
// /api/user_profile/calibration/dashboard and the controls call the
// unignore/clear/reset_all endpoints. No estimator math is touched here.

const CONFIDENCE_LABELS = { high: 'High', medium: 'Medium', low: 'Low', none: 'None' };

function formatObservedDate(value) {
    if (!value) return '—';
    // Stored as "YYYY-MM-DD HH:MM:SS" (or ISO); show the date portion only.
    const text = String(value).trim();
    const datePart = text.split(/[ T]/)[0];
    return datePart || '—';
}

function formatSuggestion(row) {
    const weight = row.suggested_weight;
    const minReps = row.suggested_min_reps;
    const maxReps = row.suggested_max_reps;
    if (weight === null || weight === undefined) return '—';
    const weightText = `${Number(weight)} kg`;
    if (minReps == null && maxReps == null) return weightText;
    const reps = minReps != null && maxReps != null && minReps !== maxReps
        ? `${minReps}–${maxReps}`
        : `${maxReps ?? minReps}`;
    return `${weightText} × ${reps}`;
}

function renderLearnedCalibrations(review, rows) {
    const table = review.querySelector('[data-learned-table]');
    const body = review.querySelector('[data-learned-rows]');
    const empty = review.querySelector('[data-learned-empty]');
    const resetAll = review.querySelector('[data-reset-all-calibration]');
    if (!table || !body || !empty) return;

    body.innerHTML = '';
    const hasRows = rows.length > 0;
    table.hidden = !hasRows;
    empty.hidden = hasRows;
    if (resetAll) resetAll.hidden = !hasRows;

    for (const row of rows) {
        const tr = document.createElement('tr');
        const cells = [
            row.exercise_name || '—',
            CONFIDENCE_LABELS[row.confidence] || row.confidence || '—',
            row.sample_count != null ? String(row.sample_count) : '—',
            row.estimated_1rm != null ? `${Number(row.estimated_1rm)} kg` : '—',
            formatSuggestion(row),
            formatObservedDate(row.last_observed_at),
        ];
        for (const text of cells) {
            const td = document.createElement('td');
            td.textContent = text;
            tr.appendChild(td);
        }
        tr.appendChild(buildPromoteCell(row));
        body.appendChild(tr);
    }
}

// Phase 2C — per-row "Promote to reference lift". Promotable rows carry the
// proposed (basis-converted) weight/reps and any existing reference value as
// data-* attributes so the click handler can build the confirm copy without a
// per-click round-trip. Non-promotable rows show a disabled button + tooltip.
function buildPromoteCell(row) {
    const td = document.createElement('td');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-outline-primary btn-sm';
    button.textContent = 'Promote to reference lift';

    if (!row.promotable) {
        button.disabled = true;
        button.title = 'No matching Profile reference lift for this exercise';
        td.appendChild(button);
        return td;
    }

    button.dataset.promoteExercise = row.exercise_name || '';
    button.dataset.promoteLiftLabel = row.lift_label || row.lift_key || 'this lift';
    button.dataset.promoteWeight = row.promote_weight_kg != null ? String(row.promote_weight_kg) : '';
    button.dataset.promoteReps = row.promote_reps != null ? String(row.promote_reps) : '';
    if (row.existing_reference) {
        button.dataset.promoteHasExisting = '1';
        button.dataset.promoteExistingWeight =
            row.existing_reference.weight_kg != null ? String(row.existing_reference.weight_kg) : '—';
        button.dataset.promoteExistingReps =
            row.existing_reference.reps != null ? String(row.existing_reference.reps) : '—';
    }
    td.appendChild(button);
    return td;
}

function renderIgnoredTransfers(review, rows) {
    const list = review.querySelector('[data-ignored-list]');
    const empty = review.querySelector('[data-ignored-empty]');
    const clearAll = review.querySelector('[data-clear-ignored-transfers]');
    if (!list || !empty) return;

    list.innerHTML = '';
    const hasRows = rows.length > 0;
    list.hidden = !hasRows;
    empty.hidden = hasRows;
    if (clearAll) clearAll.hidden = !hasRows;

    for (const row of rows) {
        const li = document.createElement('li');
        li.className = 'profile-calibration-ignored-row';

        const text = document.createElement('span');
        text.className = 'profile-calibration-ignored-pair';
        const source = document.createElement('strong');
        source.textContent = row.source_exercise_name || '—';
        const target = document.createElement('strong');
        target.textContent = row.target_exercise_name || '—';
        text.appendChild(source);
        text.appendChild(document.createTextNode(' → '));
        text.appendChild(target);

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-outline-secondary btn-sm';
        button.textContent = 'Remove';
        button.dataset.unignoreSource = row.source_exercise_name || '';
        button.dataset.unignoreTarget = row.target_exercise_name || '';

        li.appendChild(text);
        li.appendChild(button);
        list.appendChild(li);
    }
}

async function refreshCalibrationReview(review) {
    try {
        const response = await api.get('/api/user_profile/calibration/dashboard', {
            showLoading: false,
            showErrorToast: false,
        });
        const data = response?.data || {};
        renderLearnedCalibrations(review, data.learned || []);
        renderIgnoredTransfers(review, data.ignored_transfers || []);
    } catch (error) {
        showToast('error', error?.message || 'Failed to load calibration review', {
            requestId: error?.requestId,
        });
    }
}

function bindCalibrationReview() {
    const review = document.querySelector('[data-calibration-review]');
    if (!review) return;

    const runAction = async (endpoint, body, successMessage) => {
        try {
            await api.post(endpoint, body, { showLoading: false, showErrorToast: false });
            showToast('success', successMessage);
            await refreshCalibrationReview(review);
        } catch (error) {
            showToast('error', error?.message || 'Action failed', {
                requestId: error?.requestId,
            });
        }
    };

    review.addEventListener('click', (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const promote = target.closest('[data-promote-exercise]');
        if (promote) {
            const label = promote.dataset.promoteLiftLabel || 'this lift';
            const weight = promote.dataset.promoteWeight;
            const reps = promote.dataset.promoteReps;
            let overwrite = false;
            if (promote.dataset.promoteHasExisting === '1') {
                const ok = window.confirm(
                    `Replace your declared Profile reference lift for ${label}? `
                    + 'This changes your saved baseline.\n\n'
                    + `Current: ${promote.dataset.promoteExistingWeight} kg × ${promote.dataset.promoteExistingReps}\n`
                    + `New (from your logged set): ${weight} kg × ${reps}\n\n`
                    + 'Your learned suggestion already drives Workout Controls — this only '
                    + 'updates the baseline used when learned data is unavailable.',
                );
                if (!ok) return;
                overwrite = true;
            } else if (!window.confirm(
                `Save ${weight} kg × ${reps} as your declared Profile reference lift for ${label}? `
                + 'This sets your saved baseline (separate from the live learned suggestion).',
            )) {
                return;
            }
            runAction(
                '/api/user_profile/calibration/promote',
                { exercise: promote.dataset.promoteExercise, overwrite },
                `Promoted to Profile reference lift: ${label} ${weight} kg × ${reps}`,
            );
            return;
        }

        const unignore = target.closest('[data-unignore-source]');
        if (unignore) {
            runAction(
                '/api/user_profile/calibration/unignore_transfer',
                {
                    source_exercise: unignore.dataset.unignoreSource,
                    target_exercise: unignore.dataset.unignoreTarget,
                },
                'Related calibration restored',
            );
            return;
        }

        if (target.closest('[data-clear-ignored-transfers]')) {
            if (!window.confirm('Clear all ignored related transfers? They will become eligible again.')) return;
            runAction('/api/user_profile/calibration/clear_ignored_transfers', {}, 'Cleared all ignored transfers');
            return;
        }

        if (target.closest('[data-reset-all-calibration]')) {
            if (!window.confirm('Reset all learned calibration? This clears every learned row; they rebuild as you log scored sets.')) return;
            runAction('/api/user_profile/calibration/reset_all', {}, 'Reset all learned calibration');
        }
    });

    refreshCalibrationReview(review);
}

export { bindCalibrationReview };
