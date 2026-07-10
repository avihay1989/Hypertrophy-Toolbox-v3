import { describe, it, expect } from 'vitest';

import {
    getVolumeDetails,
    formatPatternName,
    isWrappedApiResponse,
    isApiFailure,
    unwrapApiPayload,
    getApiErrorMessage,
    getCategoryTooltip,
    getSubcategoryTooltip,
} from '../summary-helpers.js';

describe('getVolumeDetails', () => {
    it('classifies below 10 as low volume', () => {
        const result = getVolumeDetails(0);
        expect(result.class).toBe('low-volume');
        expect(result.label).toBe('Low Volume');
        expect(result.tooltip).toBe('Low Volume: Below 10 effective sets (Current: 0.0 effective sets)');
    });

    it('classifies 10 to 19 as medium volume', () => {
        const result = getVolumeDetails(10);
        expect(result.class).toBe('medium-volume');
        expect(result.label).toBe('Medium Volume');
        expect(result.tooltip).toBe('Medium Volume: 10-19 effective sets (Current: 10.0 effective sets)');
    });

    it('classifies 20 to 29 as high volume', () => {
        const result = getVolumeDetails(25.5);
        expect(result.class).toBe('high-volume');
        expect(result.label).toBe('High Volume');
        expect(result.tooltip).toBe('High Volume: 20-29 effective sets (Current: 25.5 effective sets)');
    });

    it('classifies 30 and above as excessive volume', () => {
        const result = getVolumeDetails(30);
        expect(result.class).toBe('ultra-volume');
        expect(result.label).toBe('Excessive Volume');
        expect(result.tooltip).toBe('Excessive Volume: 30+ effective sets (Current: 30.0 effective sets)');
    });

    it('uses the boundary values (<10, <20, <30) inclusively on the upper side', () => {
        expect(getVolumeDetails(9.99).class).toBe('low-volume');
        expect(getVolumeDetails(19.99).class).toBe('medium-volume');
        expect(getVolumeDetails(29.99).class).toBe('high-volume');
    });
});

describe('formatPatternName', () => {
    it('maps known patterns to their display names', () => {
        expect(formatPatternName('horizontal_push')).toBe('Horizontal Push');
        expect(formatPatternName('core_static')).toBe('Core (Static)');
        expect(formatPatternName('squat')).toBe('Squat');
    });

    it('title-cases unknown snake_case patterns', () => {
        expect(formatPatternName('some_new_pattern')).toBe('Some New Pattern');
    });

    it('title-cases a single unknown word', () => {
        expect(formatPatternName('carry')).toBe('Carry');
    });
});

describe('isWrappedApiResponse', () => {
    it('recognizes a success-wrapped envelope', () => {
        expect(isWrappedApiResponse({ ok: true, data: {} })).toBe(true);
        expect(isWrappedApiResponse({ status: 'success', data: [] })).toBe(true);
        expect(isWrappedApiResponse({ success: true, data: 1 })).toBe(true);
    });

    it('rejects payloads without a data key or success flag', () => {
        expect(isWrappedApiResponse({ ok: true })).toBe(false);
        expect(isWrappedApiResponse({ data: {} })).toBe(false);
        expect(isWrappedApiResponse(null)).toBe(false);
        expect(isWrappedApiResponse([1, 2])).toBe(false);
        expect(isWrappedApiResponse('x')).toBe(false);
    });
});

describe('isApiFailure', () => {
    it('recognizes explicit failure flags', () => {
        expect(isApiFailure({ ok: false })).toBe(true);
        expect(isApiFailure({ success: false })).toBe(true);
    });

    it('returns false for success or non-objects', () => {
        expect(isApiFailure({ ok: true })).toBe(false);
        expect(isApiFailure({})).toBe(false);
        expect(isApiFailure(null)).toBe(false);
        expect(isApiFailure('nope')).toBe(false);
    });
});

describe('unwrapApiPayload', () => {
    it('unwraps a wrapped envelope to its data', () => {
        expect(unwrapApiPayload({ ok: true, data: { a: 1 } })).toEqual({ a: 1 });
    });

    it('returns the payload unchanged when not wrapped', () => {
        const raw = { weekly_summary: [] };
        expect(unwrapApiPayload(raw)).toBe(raw);
        expect(unwrapApiPayload(null)).toBeNull();
    });
});

describe('getApiErrorMessage', () => {
    it('prefers a nested error.message string', () => {
        expect(getApiErrorMessage({ error: { message: 'boom' } }, 'fb')).toBe('boom');
    });

    it('falls back to a string error field', () => {
        expect(getApiErrorMessage({ error: 'bad' }, 'fb')).toBe('bad');
    });

    it('falls back to a non-blank message field', () => {
        expect(getApiErrorMessage({ message: 'why' }, 'fb')).toBe('why');
        expect(getApiErrorMessage({ message: '   ' }, 'fb')).toBe('fb');
    });

    it('returns the fallback for non-objects or empty payloads', () => {
        expect(getApiErrorMessage(null, 'fb')).toBe('fb');
        expect(getApiErrorMessage('x', 'fb')).toBe('fb');
        expect(getApiErrorMessage({}, 'fb')).toBe('fb');
    });
});

describe('getCategoryTooltip', () => {
    it('returns tooltips for known categories', () => {
        expect(getCategoryTooltip('Mechanic')).toBe('Classification based on joint involvement in the exercise');
        expect(getCategoryTooltip('Force')).toBe('Classification based on primary force direction');
    });

    it('returns empty string for unknown categories', () => {
        expect(getCategoryTooltip('Nope')).toBe('');
    });
});

describe('getSubcategoryTooltip', () => {
    it('returns tooltips for known category/subcategory pairs', () => {
        expect(getSubcategoryTooltip('Mechanic', 'Compound')).toBe('Multi-joint exercises like squats and bench press');
        expect(getSubcategoryTooltip('Force', 'Pull')).toBe('Exercises involving pulling motions toward body');
    });

    it('returns empty string for unknown pairs', () => {
        expect(getSubcategoryTooltip('Mechanic', 'Nope')).toBe('');
        expect(getSubcategoryTooltip('Nope', 'Compound')).toBe('');
    });
});
