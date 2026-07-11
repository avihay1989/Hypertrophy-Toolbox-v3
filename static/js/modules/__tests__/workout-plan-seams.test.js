import { describe, expect, it } from 'vitest';

import {
    applyRoutineTabFilter,
    buildAddExercisePayload,
    buildExecutionStylePayload,
    buildExerciseOrderPayload,
    buildFieldUpdatePayload,
    buildReplacePayload,
    buildSupersetLinkPayload,
    buildSupersetUnlinkPayload,
    clampToAttrRange,
    collectMissingAddFields,
    collectMissingRequiredSelections,
    compareRoutines,
    computeNudgedValue,
    estimateProvenanceLabel,
    fatigueChipTitle,
    formatRoutineForDisplay,
    formatRoutineForTab,
    learnedBadgeText,
    nextSupersetColorIndex,
    parseRoutine,
    renderExecutionStyleBadge,
    resolveMin,
    resolveProfileEstimate,
    resolveStep,
    resolveSwapErrorToast,
    supersetRowClasses,
    traceHeadline,
    traceStepValueText,
} from '../workout-plan-helpers.js';

describe('routine formatting seams', () => {
    it('parses empty, complete, and missing routine parts', () => {
        expect(parseRoutine('')).toEqual({ env: '', program: '', workout: '' });
        expect(parseRoutine(' GYM - PPL - Push ')).toEqual({ env: 'GYM', program: 'PPL', workout: 'Push' });
        expect(parseRoutine('HOME - Upper')).toEqual({ env: 'HOME', program: 'Upper', workout: '' });
    });

    it('formats display routines and escapes each part', () => {
        expect(formatRoutineForDisplay('')).toBe('N/A');
        expect(formatRoutineForDisplay(' -  - ')).toBe('N/A');
        expect(formatRoutineForDisplay('<Gym> - A&B - Push')).toBe(
            '<span class="routine-env">&lt;Gym&gt;</span><span class="routine-program">A&amp;B</span><span class="routine-workout">Push</span>'
        );
    });

    it('formats tab routines, including blank parsed parts and escaping', () => {
        expect(formatRoutineForTab(null)).toBe('N/A');
        expect(formatRoutineForTab(' -  - ')).toBe(' -  - ');
        expect(formatRoutineForTab('GYM - <PPL> - Push & Pull')).toContain('&lt;PPL&gt;');
        expect(formatRoutineForTab('GYM - <PPL> - Push & Pull')).toContain('Push &amp; Pull');
    });

    it('compares environment, then program, then workout', () => {
        expect(compareRoutines('HOME - A - A', 'GYM - Z - Z')).toBeGreaterThan(0);
        expect(compareRoutines('GYM - A - Z', 'GYM - B - A')).toBeLessThan(0);
        expect(compareRoutines('GYM - A - A', 'GYM - A - B')).toBeLessThan(0);
        expect(compareRoutines('', null)).toBe(0);
    });

    it('returns the original list for all and filters an exact routine', () => {
        const exercises = [{ routine: 'A' }, { routine: 'B' }];
        expect(applyRoutineTabFilter(exercises, 'all')).toBe(exercises);
        expect(applyRoutineTabFilter(exercises, 'A')).toEqual([{ routine: 'A' }]);
    });
});

describe('execution style seams', () => {
    it('renders standard, AMRAP, and EMOM badge branches', () => {
        expect(renderExecutionStyleBadge({})).toContain('execution-badge--standard');
        expect(renderExecutionStyleBadge({ execution_style: 'amrap', time_cap_seconds: 90 })).toContain('90s');
        expect(renderExecutionStyleBadge({ execution_style: 'amrap', time_cap_seconds: 0 })).not.toContain('execution-details');
        expect(renderExecutionStyleBadge({ execution_style: 'emom', emom_interval_seconds: 45, emom_rounds: 8 })).toContain('8×45s');
        expect(renderExecutionStyleBadge({ execution_style: 'emom', emom_interval_seconds: 45 })).not.toContain('execution-details');
    });

    it('builds standard, AMRAP, and EMOM payloads with falsy fallbacks', () => {
        expect(buildExecutionStylePayload(4, 'standard', {})).toEqual({ exercise_id: 4, execution_style: 'standard' });
        expect(buildExecutionStylePayload(4, 'amrap', { timeCap: 120 })).toEqual({ exercise_id: 4, execution_style: 'amrap', time_cap_seconds: 120 });
        expect(buildExecutionStylePayload(4, 'amrap', { timeCap: NaN })).toEqual({ exercise_id: 4, execution_style: 'amrap', time_cap_seconds: 60 });
        expect(buildExecutionStylePayload(4, 'emom', { emomInterval: 30, emomRounds: 10 })).toEqual({ exercise_id: 4, execution_style: 'emom', emom_interval_seconds: 30, emom_rounds: 10 });
        expect(buildExecutionStylePayload(4, 'emom', { emomInterval: 0, emomRounds: undefined })).toEqual({ exercise_id: 4, execution_style: 'emom', emom_interval_seconds: 60, emom_rounds: 5 });
    });
});

describe('payload builders', () => {
    it('coerces add-exercise fields and applies RIR/RPE empty semantics', () => {
        const base = { exercise: 'Squat', routine: 'GYM - A - 1', sets: '3', minRepRange: '6', maxRepRange: '10', weight: '82.5' };
        expect(buildAddExercisePayload({ ...base, rir: '', rpe: '' })).toEqual({
            exercise: 'Squat', routine: 'GYM - A - 1', sets: 3, min_rep_range: 6,
            max_rep_range: 10, rir: 0, weight: 82.5, rpe: null,
        });
        expect(buildAddExercisePayload({ ...base, rir: '2', rpe: '8.5' })).toMatchObject({ rir: 2, rpe: 8.5 });
    });

    it('builds field, replacement, superset, and ordering payloads', () => {
        expect(buildFieldUpdatePayload(7, 'sets', '4')).toEqual({ id: 7, updates: { sets: '4' } });
        expect(buildReplacePayload(7)).toEqual({ id: 7, strategy: 'ai' });
        const ids = [7, 9];
        expect(buildSupersetLinkPayload(ids)).toEqual({ exercise_ids: ids });
        expect(buildSupersetUnlinkPayload(7)).toEqual({ exercise_id: 7 });
        expect(buildExerciseOrderPayload([9, 7])).toEqual([{ id: 9, order: 1 }, { id: 7, order: 2 }]);
        expect(buildExerciseOrderPayload([])).toEqual([]);
    });
});

describe('add-exercise validation seams', () => {
    it('collects required selections in UI order', () => {
        expect(collectMissingRequiredSelections('', '')).toEqual(['Routine', 'Exercise']);
        expect(collectMissingRequiredSelections('A', '')).toEqual(['Exercise']);
        expect(collectMissingRequiredSelections('', 'Squat')).toEqual(['Routine']);
        expect(collectMissingRequiredSelections('A', 'Squat')).toEqual([]);
    });

    it('collects detailed missing fields in UI order and preserves truthiness rules', () => {
        expect(collectMissingAddFields({})).toEqual(['Exercise', 'Routine', 'Sets', 'Min Rep Range', 'Max Rep Range', 'Weight']);
        expect(collectMissingAddFields({ exercise: 'Squat', routine: 'A', sets: '3', minRepRange: '6', maxRepRange: '10', weight: '0' })).toEqual([]);
        expect(collectMissingAddFields({ exercise: 'Squat', routine: 'A', sets: '', minRepRange: '6', maxRepRange: '', weight: '20' })).toEqual(['Sets', 'Max Rep Range']);
    });

    it('clamps against present bounds and treats null/empty attributes as infinite', () => {
        expect(clampToAttrRange(5, null, '')).toBe(5);
        expect(clampToAttrRange(-1, '0', '10')).toBe(0);
        expect(clampToAttrRange(11, '0', '10')).toBe(10);
        expect(clampToAttrRange(4.5, '0', '10')).toBe(4.5);
    });
});

describe('replacement and superset seams', () => {
    it.each([
        ['no_candidates', 'warning', 'No alternative found for this muscle/equipment.'],
        ['duplicate', 'warning', 'All alternatives are already in this routine.'],
        ['not_found', 'error', 'Exercise not found in workout plan.'],
        ['missing_metadata', 'warning', 'This exercise is missing muscle/equipment data and cannot be replaced.'],
        ['unknown', 'error', 'fallback'],
    ])('maps %s to its toast decision', (reason, severity, message) => {
        expect(resolveSwapErrorToast(reason, 'fallback')).toEqual({ severity, message });
    });

    it('cycles superset colors from 0 through 4 and back to 1', () => {
        expect([0, 1, 2, 3, 4].map(nextSupersetColorIndex)).toEqual([1, 2, 3, 4, 1]);
    });

    it('adds connector classes only to adjacent first/last rows', () => {
        expect(supersetRowClasses(2, 0, [3, 4])).toBe('superset-group superset-group-2 superset-first');
        expect(supersetRowClasses(2, 1, [3, 4])).toBe('superset-group superset-group-2 superset-last');
        expect(supersetRowClasses(2, 1, [3, 4, 5])).toBe('superset-group superset-group-2');
        expect(supersetRowClasses(2, 0, [3, 5])).toBe('superset-group superset-group-2');
        expect(supersetRowClasses(2, 0, [3])).toBe('superset-group superset-group-2');
    });
});

describe('estimate rendering data seams', () => {
    it('resolves profile defaults and lets estimates override them', () => {
        expect(resolveProfileEstimate(null)).toEqual({ weight: 25, sets: 3, min_rep: 6, max_rep: 8, rir: 3, rpe: 7, source: 'default', is_dumbbell: false });
        expect(resolveProfileEstimate({ weight: 40, source: 'profile' })).toMatchObject({ weight: 40, sets: 3, source: 'profile' });
    });

    it('maps estimate provenance and falls back to default', () => {
        expect(estimateProvenanceLabel('learned')).toBe('learned from your recent logs');
        expect(estimateProvenanceLabel('related_learned')).toBe('learned from a related exercise');
        expect(estimateProvenanceLabel('log')).toBe('from your last set');
        expect(estimateProvenanceLabel('profile')).toBe('from your profile');
        expect(estimateProvenanceLabel('cold_start')).toBe('from population estimate');
        expect(estimateProvenanceLabel('unknown')).toBe('default values');
    });

    it('hides the learned badge for non-learned sources', () => {
        expect(learnedBadgeText({ source: 'profile' })).toEqual({ isLearned: false });
    });

    it('describes learned samples for zero, one, and many logs', () => {
        expect(learnedBadgeText({ source: 'learned', trace: {} })).toEqual({ isLearned: true, confidence: '', label: 'Learned', title: 'Suggested from your scored logs' });
        expect(learnedBadgeText({ source: 'learned', trace: { confidence: 'high', sample_count: 1 } })).toMatchObject({ label: 'Learned · high confidence', title: 'Suggested from 1 scored log for this exercise' });
        expect(learnedBadgeText({ source: 'learned', trace: { confidence: 'custom', sample_count: 3 } })).toMatchObject({ label: 'Learned · custom', title: 'Suggested from 3 scored logs for this exercise' });
    });

    it('describes related learned samples and source fallbacks', () => {
        expect(learnedBadgeText({ source: 'related_learned', trace: {} })).toMatchObject({ label: 'Related', title: 'Suggested from a related exercise' });
        expect(learnedBadgeText({ source: 'related_learned', trace: { source_exercise: 'Front Squat', sample_count: 1 } })).toMatchObject({ title: 'Suggested from 1 scored log for Front Squat' });
        expect(learnedBadgeText({ source: 'related_learned', trace: { source_exercise: 'Front Squat', sample_count: 4 } })).toMatchObject({ title: 'Suggested from 4 scored logs for Front Squat' });
    });

    it('builds fatigue titles with headline/advisory fallbacks', () => {
        expect(fatigueChipTitle({ headline: 'High fatigue', advisory: 'Take care.' })).toBe('High fatigue Take care.');
        expect(fatigueChipTitle({ headline: 'High fatigue' })).toBe('High fatigue');
        expect(fatigueChipTitle({ advisory: 'Take care.' })).toBe('Fatigue context');
    });

    it('maps every trace headline and falls back to default', () => {
        expect(traceHeadline('learned')).toBe('Learned from your recent logs');
        expect(traceHeadline('related_learned')).toBe('Learned from a related exercise');
        expect(traceHeadline('log')).toBe('From your last logged set');
        expect(traceHeadline('profile')).toBe('From your saved reference lift');
        expect(traceHeadline('cold_start')).toBe('From a population estimate');
        expect(traceHeadline('unknown')).toBe('Default values');
    });

    it('formats trace values, units, factors, and empty steps', () => {
        expect(traceStepValueText({ value: 80, unit: 'kg', factor: 0.9 })).toBe('80 kg × 0.9');
        expect(traceStepValueText({ value: 0 })).toBe('0');
        expect(traceStepValueText({ factor: 0 })).toBe('× 0');
        expect(traceStepValueText({ value: '', factor: null })).toBe('');
    });

    it('resolves valid steps/minimums and their fallbacks', () => {
        expect(resolveStep('0.5')).toBe(0.5);
        expect(resolveStep('any')).toBe(1);
        expect(resolveStep('0')).toBe(1);
        expect(resolveStep(null)).toBe(1);
        expect(resolveMin('0')).toBe(0);
        expect(resolveMin('-5')).toBe(-5);
        expect(resolveMin(null)).toBeNull();
    });

    it('nudges up/down, chooses a base for NaN, clamps, and rounds to two decimals', () => {
        expect(computeNudgedValue(10, 2, 0, 'up')).toBe(12);
        expect(computeNudgedValue(10, 2, 0, 'down')).toBe(8);
        expect(computeNudgedValue(NaN, 2, 5, 'up')).toBe(7);
        expect(computeNudgedValue(NaN, 2, null, 'down')).toBe(-2);
        expect(computeNudgedValue(1, 2, 0, 'down')).toBe(0);
        expect(computeNudgedValue(1.005, 0.111, null, 'up')).toBe(1.12);
    });
});
