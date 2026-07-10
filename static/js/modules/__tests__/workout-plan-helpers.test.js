import { describe, it, expect } from 'vitest';

import { volumeColorClass, planPreviewData, equipmentForEnvironment } from '../workout-plan-helpers.js';

describe('volumeColorClass', () => {
    it('returns blue at or below 0.8', () => {
        expect(volumeColorClass('0.5')).toBe('volume-value-blue');
        expect(volumeColorClass('0.8')).toBe('volume-value-blue');
    });

    it('returns green above 0.8 up to 1.1', () => {
        expect(volumeColorClass('0.9')).toBe('volume-value-green');
        expect(volumeColorClass('1.1')).toBe('volume-value-green');
    });

    it('returns yellow above 1.1 up to 1.5', () => {
        expect(volumeColorClass('1.2')).toBe('volume-value-yellow');
        expect(volumeColorClass('1.5')).toBe('volume-value-yellow');
    });

    it('returns orange above 1.5 up to 1.7', () => {
        expect(volumeColorClass('1.6')).toBe('volume-value-orange');
        expect(volumeColorClass('1.7')).toBe('volume-value-orange');
    });

    it('returns red above 1.7', () => {
        expect(volumeColorClass('1.8')).toBe('volume-value-red');
        expect(volumeColorClass('2.0')).toBe('volume-value-red');
    });

    it('falls through to red for non-numeric input (NaN comparisons are false)', () => {
        expect(volumeColorClass('abc')).toBe('volume-value-red');
    });
});

describe('planPreviewData', () => {
    it('defaults to full body / hypertrophy rep range', () => {
        const result = planPreviewData('1', 'hypertrophy', '1.0');
        expect(result.routines).toBe('Full Body: Workout A');
        expect(result.repRange).toBe('6-10, 10-15');
        expect(result.baseSets).toBe(18);
    });

    it('maps each training-day split', () => {
        expect(planPreviewData('2', 'hypertrophy', '1.0').routines).toBe('2 Days Split: Workout A, Workout B');
        expect(planPreviewData('3', 'hypertrophy', '1.0').routines).toBe('3 Days Split: Workout A, Workout B, Workout C');
        expect(planPreviewData('4', 'hypertrophy', '1.0').routines).toBe('Upper Lower: Upper 1, Lower 1, Upper 2, Lower 2');
        expect(planPreviewData('5', 'hypertrophy', '1.0').routines).toBe('5 Days Split: Day 1, Day 2, Day 3, Day 4, Day 5');
    });

    it('maps goal to rep range', () => {
        expect(planPreviewData('3', 'strength', '1.0').repRange).toBe('3-6, 6-10');
        expect(planPreviewData('3', 'general', '1.0').repRange).toBe('5-8, 8-12');
        expect(planPreviewData('3', 'hypertrophy', '1.0').repRange).toBe('6-10, 10-15');
    });

    it('scales base sets by the volume factor and rounds', () => {
        expect(planPreviewData('3', 'hypertrophy', '0.5').baseSets).toBe(9);
        expect(planPreviewData('3', 'hypertrophy', '1.5').baseSets).toBe(27);
        // 18 * 1.7 = 30.6 -> rounds to 31
        expect(planPreviewData('3', 'hypertrophy', '1.7').baseSets).toBe(31);
    });
});

describe('equipmentForEnvironment', () => {
    it('returns the full gym equipment list for gym', () => {
        expect(equipmentForEnvironment('gym')).toEqual([
            'Barbell', 'Dumbbells', 'Cables', 'Machine', 'Bodyweight', 'Kettlebells',
            'Smith_Machine', 'Trapbar', 'Band', 'Trx', 'Plate', 'Medicine_Ball'
        ]);
    });

    it('returns the reduced home equipment list for non-gym', () => {
        expect(equipmentForEnvironment('home')).toEqual([
            'Dumbbells', 'Bodyweight', 'Band', 'Kettlebells', 'Trx', 'Medicine_Ball'
        ]);
    });

    it('treats any non-gym value as home', () => {
        expect(equipmentForEnvironment('anything')).toEqual([
            'Dumbbells', 'Bodyweight', 'Band', 'Kettlebells', 'Trx', 'Medicine_Ball'
        ]);
    });
});
