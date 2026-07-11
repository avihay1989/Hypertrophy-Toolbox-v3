import { escapeHtml } from './exercise-helpers.js';

// Pure helpers for the workout plan page.
//
// Extracted verbatim from the page-local inline script in
// templates/workout_plan.html (Refactor Plan v3 WP3.2c). These are the three
// genuinely-pure computations behind the plan-generator preview UI: the volume
// slider colour class, the plan-preview summary strings, and the per-environment
// equipment list. DOM-free and side-effect-free so they can be unit-tested under
// the node-environment Vitest runner. The DOM wrappers in workout-plan-page.js
// call these and keep their branching byte-identical to the original inline code.
// WP3.3 extends this module with characterized seams from workout-plan.js ahead
// of the later feature split; all helpers remain DOM-free and side-effect-free.

// Temperature colour class for the volume-scale value display.
export function volumeColorClass(value) {
    const v = parseFloat(value);
    if (v <= 0.8) {
        return 'volume-value-blue';
    } else if (v <= 1.1) {
        return 'volume-value-green';
    } else if (v <= 1.5) {
        return 'volume-value-yellow';
    } else if (v <= 1.7) {
        return 'volume-value-orange';
    } else {
        return 'volume-value-red';
    }
}

// Preview summary (routines / rep range / base set count) for the generator form.
export function planPreviewData(trainingDays, goal, volumeScaleVal) {
    let routines = 'Full Body: Workout A';
    if (trainingDays === '2') {
        routines = '2 Days Split: Workout A, Workout B';
    } else if (trainingDays === '3') {
        routines = '3 Days Split: Workout A, Workout B, Workout C';
    } else if (trainingDays === '4') {
        routines = 'Upper Lower: Upper 1, Lower 1, Upper 2, Lower 2';
    } else if (trainingDays === '5') {
        routines = '5 Days Split: Day 1, Day 2, Day 3, Day 4, Day 5';
    }

    let repRange = '6-10, 10-15';
    if (goal === 'strength') {
        repRange = '3-6, 6-10';
    } else if (goal === 'general') {
        repRange = '5-8, 8-12';
    }

    const baseSets = Math.round(18 * parseFloat(volumeScaleVal));

    return { routines, repRange, baseSets };
}

// Equipment available in each training environment.
export function equipmentForEnvironment(environment) {
    const gymEquipment = ['Barbell', 'Dumbbells', 'Cables', 'Machine', 'Bodyweight', 'Kettlebells',
                         'Smith_Machine', 'Trapbar', 'Band', 'Trx', 'Plate', 'Medicine_Ball'];
    const homeEquipment = ['Dumbbells', 'Bodyweight', 'Band', 'Kettlebells', 'Trx', 'Medicine_Ball'];

    return environment === 'gym' ? gymEquipment : homeEquipment;
}

export function parseRoutine(routine) {
    if (!routine) return { env: '', program: '', workout: '' };
    const parts = routine.split(' - ').map(p => p.trim());
    return {
        env: parts[0] || '',
        program: parts[1] || '',
        workout: parts[2] || ''
    };
}

export function formatRoutineForDisplay(routine) {
    if (!routine) return 'N/A';
    const parsed = parseRoutine(routine);
    if (!parsed.env && !parsed.program && !parsed.workout) return 'N/A';
    return `<span class="routine-env">${escapeHtml(parsed.env || '')}</span><span class="routine-program">${escapeHtml(parsed.program || '')}</span><span class="routine-workout">${escapeHtml(parsed.workout || '')}</span>`;
}

export function formatRoutineForTab(routine) {
    if (!routine) return 'N/A';
    const parsed = parseRoutine(routine);
    if (!parsed.env && !parsed.program && !parsed.workout) return escapeHtml(routine);
    return `<span class="tab-env">${escapeHtml(parsed.env || '')}</span><span class="tab-program">${escapeHtml(parsed.program || '')}</span><span class="tab-workout">${escapeHtml(parsed.workout || '')}</span>`;
}

export function compareRoutines(a, b) {
    const parsedA = parseRoutine(a);
    const parsedB = parseRoutine(b);

    if (parsedA.env !== parsedB.env) {
        return parsedA.env.localeCompare(parsedB.env);
    }
    if (parsedA.program !== parsedB.program) {
        return parsedA.program.localeCompare(parsedB.program);
    }
    return parsedA.workout.localeCompare(parsedB.workout);
}

export function applyRoutineTabFilter(exercises, routineFilter) {
    if (routineFilter === 'all') {
        return exercises;
    }
    return exercises.filter(ex => ex.routine === routineFilter);
}

export function renderExecutionStyleBadge(exercise) {
    const style = exercise.execution_style || 'standard';
    const timeCap = exercise.time_cap_seconds;
    const emomInterval = exercise.emom_interval_seconds;
    const emomRounds = exercise.emom_rounds;

    let badgeClass = 'execution-badge';
    let icon = '';
    let label = '';
    let details = '';

    switch (style) {
        case 'amrap':
            badgeClass += ' execution-badge--amrap';
            icon = '<i class="fas fa-stopwatch"></i>';
            label = 'AMRAP';
            if (timeCap) {
                details = `<span class="execution-details">${timeCap}s</span>`;
            }
            break;
        case 'emom':
            badgeClass += ' execution-badge--emom';
            icon = '<i class="fas fa-clock"></i>';
            label = 'EMOM';
            if (emomInterval && emomRounds) {
                details = `<span class="execution-details">${emomRounds}×${emomInterval}s</span>`;
            }
            break;
        default:
            badgeClass += ' execution-badge--standard';
            icon = '<i class="fas fa-dumbbell"></i>';
            label = 'STD';
    }

    return `<button class="btn ${badgeClass}" aria-label="Click to change execution style">
        ${icon} <span class="execution-label">${label}</span>${details}
    </button>`;
}

export function buildExecutionStylePayload(exerciseId, selectedStyle, { timeCap, emomInterval, emomRounds }) {
    const payload = { exercise_id: exerciseId, execution_style: selectedStyle };
    if (selectedStyle === 'amrap') {
        payload.time_cap_seconds = timeCap || 60;
    } else if (selectedStyle === 'emom') {
        payload.emom_interval_seconds = emomInterval || 60;
        payload.emom_rounds = emomRounds || 5;
    }
    return payload;
}

export function buildAddExercisePayload({ exercise, routine, sets, minRepRange, maxRepRange, rir, weight, rpe }) {
    return {
        exercise, routine,
        sets: parseInt(sets),
        min_rep_range: parseInt(minRepRange),
        max_rep_range: parseInt(maxRepRange),
        rir: parseInt(rir || 0),
        weight: parseFloat(weight),
        rpe: rpe ? parseFloat(rpe) : null,
    };
}

export function buildFieldUpdatePayload(exerciseId, fieldName, value) {
    return { id: exerciseId, updates: { [fieldName]: value } };
}

export function buildReplacePayload(exerciseId) { return { id: exerciseId, strategy: 'ai' }; }
export function buildSupersetLinkPayload(exerciseIds) { return { exercise_ids: exerciseIds }; }
export function buildSupersetUnlinkPayload(exerciseId) { return { exercise_id: exerciseId }; }
export function buildExerciseOrderPayload(ids) { return ids.map((id, index) => ({ id, order: index + 1 })); }

export function collectMissingRequiredSelections(routine, exercise) {
    const missing = [];
    if (!routine) missing.push('Routine');
    if (!exercise) missing.push('Exercise');
    return missing;
}

export function collectMissingAddFields({ exercise, routine, sets, minRepRange, maxRepRange, weight }) {
    const missing = [];
    if (!exercise) missing.push('Exercise');
    if (!routine) missing.push('Routine');
    if (!sets) missing.push('Sets');
    if (!minRepRange) missing.push('Min Rep Range');
    if (!maxRepRange) missing.push('Max Rep Range');
    if (!weight) missing.push('Weight');
    return missing;
}

export function clampToAttrRange(parsed, minAttr, maxAttr) {
    const min = minAttr !== null && minAttr !== '' ? parseFloat(minAttr) : -Infinity;
    const max = maxAttr !== null && maxAttr !== '' ? parseFloat(maxAttr) : Infinity;
    return Math.max(min, Math.min(max, parsed));
}

export function resolveSwapErrorToast(reason, message) {
    switch (reason) {
        case 'no_candidates': return { severity: 'warning', message: 'No alternative found for this muscle/equipment.' };
        case 'duplicate': return { severity: 'warning', message: 'All alternatives are already in this routine.' };
        case 'not_found': return { severity: 'error', message: 'Exercise not found in workout plan.' };
        case 'missing_metadata': return { severity: 'warning', message: 'This exercise is missing muscle/equipment data and cannot be replaced.' };
        default: return { severity: 'error', message };
    }
}

export function nextSupersetColorIndex(prev) { return (prev % 4) + 1; }

export function supersetRowClasses(colorNum, posInGroup, groupIndices) {
    let classes = `superset-group superset-group-${colorNum}`;
    const isAdjacentSuperset = groupIndices.length >= 2 && (groupIndices[1] - groupIndices[0] === 1);
    if (isAdjacentSuperset) {
        if (posInGroup === 0) {
            classes += ' superset-first';
        } else if (posInGroup === groupIndices.length - 1) {
            classes += ' superset-last';
        }
    }
    return classes;
}

const DEFAULT_PROFILE_ESTIMATE = {
    weight: 25,
    sets: 3,
    min_rep: 6,
    max_rep: 8,
    rir: 3,
    rpe: 7,
    source: 'default',
    is_dumbbell: false,
};

const ESTIMATE_SOURCE_LABELS = {
    learned: 'learned from your recent logs',
    related_learned: 'learned from a related exercise',
    log: 'from your last set',
    profile: 'from your profile',
    cold_start: 'from population estimate',
    default: 'default values',
};

const CONFIDENCE_LABELS = {
    high: 'high confidence',
    medium: 'medium confidence',
    low: 'low confidence',
};

export function resolveProfileEstimate(estimate) { return { ...DEFAULT_PROFILE_ESTIMATE, ...(estimate || {}) }; }
export function estimateProvenanceLabel(source) { return ESTIMATE_SOURCE_LABELS[source] || ESTIMATE_SOURCE_LABELS.default; }

export function learnedBadgeText(estimate) {
    const isLearned = ['learned', 'related_learned'].includes(estimate?.source);
    if (!isLearned) return { isLearned: false };
    const confidence = estimate?.trace?.confidence || '';
    const sampleCount = estimate?.trace?.sample_count || 0;
    const prefix = estimate?.source === 'related_learned' ? 'Related' : 'Learned';
    const label = confidence ? `${prefix} · ${CONFIDENCE_LABELS[confidence] || confidence}` : prefix;
    let title;
    if (estimate?.source === 'related_learned') {
        const source = estimate?.trace?.source_exercise || 'a related exercise';
        title = sampleCount ? `Suggested from ${sampleCount} scored ${sampleCount === 1 ? 'log' : 'logs'} for ${source}` : `Suggested from ${source}`;
    } else {
        title = sampleCount ? `Suggested from ${sampleCount} scored ${sampleCount === 1 ? 'log' : 'logs'} for this exercise` : 'Suggested from your scored logs';
    }
    return { isLearned: true, confidence, label, title };
}

export function fatigueChipTitle(fatigue) {
    return fatigue.headline ? `${fatigue.headline} ${fatigue.advisory || ''}`.trim() : 'Fatigue context';
}

export function traceHeadline(source) {
    const headlineMap = { learned: 'Learned from your recent logs', related_learned: 'Learned from a related exercise', log: 'From your last logged set', profile: 'From your saved reference lift', cold_start: 'From a population estimate', default: 'Default values' };
    return headlineMap[source] || headlineMap.default;
}

export function traceStepValueText(step) {
    const parts = [];
    if (step.value !== undefined && step.value !== null && step.value !== '') {
        parts.push(`${step.value}${step.unit ? ' ' + step.unit : ''}`);
    }
    if (step.factor !== undefined && step.factor !== null) {
        parts.push(`× ${step.factor}`);
    }
    return parts.join(' ');
}

export function resolveStep(rawStepAttr) { const raw = parseFloat(rawStepAttr); return Number.isFinite(raw) && raw > 0 ? raw : 1; }
export function resolveMin(rawMinAttr) { const raw = parseFloat(rawMinAttr); return Number.isFinite(raw) ? raw : null; }

export function computeNudgedValue(current, step, min, direction) {
    const base = Number.isFinite(current) ? current : (min ?? 0);
    let next = base + (direction === 'down' ? -step : step);
    if (min !== null && next < min) next = min;
    next = Number(next.toFixed(2));
    return next;
}
