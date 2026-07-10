import { describe, it, expect } from 'vitest';

import { getSessionWarningBadge } from '../session-summary-helpers.js';

describe('getSessionWarningBadge', () => {
    it('returns the ok badge with per-session load appended', () => {
        const result = getSessionWarningBadge('ok', 8.2);
        expect(result.class).toBe('bg-success');
        expect(result.label).toBe('OK');
        expect(result.tooltip).toBe('Session volume within productive limits (8.2 effective sets/session)');
    });

    it('returns the borderline badge with per-session load appended', () => {
        const result = getSessionWarningBadge('borderline', 10.5);
        expect(result.class).toBe('bg-warning text-dark');
        expect(result.label).toBe('Borderline');
        expect(result.tooltip).toBe('Approaching productive limits (10.5 effective sets/session)');
    });

    it('returns the excessive badge with per-session load appended', () => {
        const result = getSessionWarningBadge('excessive', 12);
        expect(result.class).toBe('bg-danger');
        expect(result.label).toBe('Excessive');
        expect(result.tooltip).toBe('May exceed productive stimulus (12.0 effective sets/session)');
    });

    it('returns the no-data badge for the no_data level without appending load', () => {
        const result = getSessionWarningBadge('no_data', 5);
        expect(result.class).toBe('bg-secondary');
        expect(result.label).toBe('No Sessions');
        expect(result.tooltip).toBe('No logged sessions — export your plan to the workout log first');
    });

    it('falls back to the no-data badge when effectivePerSession is null', () => {
        const result = getSessionWarningBadge('ok', null);
        expect(result.label).toBe('No Sessions');
        expect(result.tooltip).toBe('No logged sessions — export your plan to the workout log first');
    });

    it('falls back to the no-data badge when effectivePerSession is undefined', () => {
        const result = getSessionWarningBadge('borderline', undefined);
        expect(result.label).toBe('No Sessions');
    });

    it('falls back to the no-data badge for an unknown warning level', () => {
        const result = getSessionWarningBadge('mystery', 9);
        // Unknown level resolves to no_data, and appends the per-session load.
        expect(result.class).toBe('bg-secondary');
        expect(result.label).toBe('No Sessions');
        expect(result.tooltip).toBe('No logged sessions — export your plan to the workout log first (9.0 effective sets/session)');
    });
});
