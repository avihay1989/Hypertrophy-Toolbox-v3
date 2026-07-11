import { describe, expect, it } from 'vitest';

import { workoutPlanState } from '../workout-plan-state.js';

describe('workoutPlanState', () => {
    it('has the characterized initial shape', () => {
        expect(Object.keys(workoutPlanState)).toEqual([
            'currentRoutineTabFilter',
            'allExercisesCache',
            'selectedExerciseIds',
            'supersetColorMap',
        ]);
        expect(workoutPlanState.currentRoutineTabFilter).toBe('all');
        expect(workoutPlanState.allExercisesCache).toEqual([]);
        expect(workoutPlanState.selectedExerciseIds).toBeInstanceOf(Set);
        expect(workoutPlanState.supersetColorMap).toBeInstanceOf(Map);
    });

    it('is the same singleton across imports', async () => {
        const secondImport = await import('../workout-plan-state.js');
        expect(secondImport.workoutPlanState).toBe(workoutPlanState);
    });
});
