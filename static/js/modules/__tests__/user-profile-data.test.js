import { describe, expect, it } from 'vitest';

import {
    bandPillLabel,
    classifyExperienceTier,
    coldStart1rm,
    epley1rm,
    experienceMultiplier,
    isLiftFilled,
    nextTierMultiplier,
} from '../user-profile-data.js';

describe('user-profile estimator seams', () => {
    it.each([
        [null, 'novice'],
        [-1, 'novice'],
        [0, 'novice'],
        [1, 'novice'],
        [1.01, 'intermediate'],
        [3, 'intermediate'],
        [3.01, 'advanced'],
    ])('classifies %s years as %s', (years, expected) => {
        expect(classifyExperienceTier(years)).toBe(expected);
    });

    it('preserves tier and next-tier multipliers', () => {
        expect(experienceMultiplier('novice')).toBe(0.7);
        expect(experienceMultiplier('intermediate')).toBe(1.0);
        expect(experienceMultiplier('advanced')).toBe(1.2);
        expect(nextTierMultiplier('novice')).toBe(1.0);
        expect(nextTierMultiplier('intermediate')).toBe(1.2);
        expect(nextTierMultiplier('advanced')).toBeCloseTo(1.44);
    });

    it('keeps cold-start estimates tied to gender, bodyweight, and experience', () => {
        expect(coldStart1rm('Chest', {
            rawGender: 'M',
            bodyweight: 80,
            experienceYears: 2,
        })).toBe(80);
        expect(coldStart1rm('Chest', {
            rawGender: 'F',
            bodyweight: 60,
            experienceYears: 0,
        })).toBeCloseTo(27.3);
        expect(coldStart1rm('Unknown', {
            rawGender: 'M',
            bodyweight: 80,
            experienceYears: 2,
        })).toBeNull();
    });

    it('caps Epley inputs at 12 reps and rejects non-positive inputs', () => {
        expect(epley1rm(100, 5)).toBeCloseTo(116.6667);
        expect(epley1rm(100, 20)).toBe(140);
        expect(epley1rm(0, 5)).toBe(0);
        expect(epley1rm(100, 0)).toBe(0);
    });

    it('preserves bodyweight and external-load completion rules', () => {
        expect(isLiftFilled({ lift_key: 'barbell_bench_press', weight_kg: 100, reps: 5 })).toBe(true);
        expect(isLiftFilled({ lift_key: 'barbell_bench_press', weight_kg: 0, reps: 5 })).toBe(false);
        expect(isLiftFilled({ lift_key: 'bodyweight_pullups', weight_kg: 0, reps: 5 })).toBe(true);
        expect(isLiftFilled({ lift_key: 'bodyweight_pullups', weight_kg: 0, reps: 0 })).toBe(false);
    });

    it('keeps accuracy-band labels stable', () => {
        expect(bandPillLabel('fully')).toBe('Fully personalised');
        expect(bandPillLabel('mostly')).toBe('Mostly personalised');
        expect(bandPillLabel('partial')).toBe('Partially personalised');
        expect(bandPillLabel('population_only')).toBe('Population estimate only');
    });
});
