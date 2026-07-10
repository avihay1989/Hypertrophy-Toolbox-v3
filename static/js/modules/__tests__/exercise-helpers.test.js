import { describe, it, expect } from 'vitest';

import {
    escapeHtml,
    resolveExerciseMediaSrc,
} from '../exercise-helpers.js';

const VENDOR_BASE_URL = '/static/vendor/free-exercise-db/exercises';

describe('escapeHtml', () => {
    it('returns empty string for null and undefined', () => {
        expect(escapeHtml(null)).toBe('');
        expect(escapeHtml(undefined)).toBe('');
    });

    it('returns empty string unchanged', () => {
        expect(escapeHtml('')).toBe('');
    });

    it('escapes each of the five HTML-sensitive characters', () => {
        expect(escapeHtml('&')).toBe('&amp;');
        expect(escapeHtml('<')).toBe('&lt;');
        expect(escapeHtml('>')).toBe('&gt;');
        expect(escapeHtml('"')).toBe('&quot;');
        expect(escapeHtml("'")).toBe('&#39;');
    });

    it('escapes ampersands before other entities (no double-escaping)', () => {
        expect(escapeHtml('<a href="x">&\'')).toBe(
            '&lt;a href=&quot;x&quot;&gt;&amp;&#39;',
        );
    });

    it('leaves already-safe text untouched', () => {
        expect(escapeHtml('Barbell Bench Press')).toBe('Barbell Bench Press');
    });

    it('coerces non-string values via String()', () => {
        expect(escapeHtml(0)).toBe('0');
        expect(escapeHtml(42)).toBe('42');
        expect(escapeHtml(false)).toBe('false');
        expect(escapeHtml(['<', '>'])).toBe('&lt;,&gt;');
    });
});

describe('resolveExerciseMediaSrc', () => {
    it('prefixes the vendor base URL for a valid relative path', () => {
        expect(resolveExerciseMediaSrc('Bench_Press/0.jpg')).toBe(
            `${VENDOR_BASE_URL}/Bench_Press/0.jpg`,
        );
    });

    it('accepts every allowed extension, case-insensitively', () => {
        for (const ext of ['jpg', 'jpeg', 'png', 'gif', 'webp']) {
            expect(resolveExerciseMediaSrc(`x/0.${ext}`)).toBe(
                `${VENDOR_BASE_URL}/x/0.${ext}`,
            );
        }
        expect(resolveExerciseMediaSrc('x/0.JPG')).toBe(
            `${VENDOR_BASE_URL}/x/0.JPG`,
        );
        expect(resolveExerciseMediaSrc('x/0.WebP')).toBe(
            `${VENDOR_BASE_URL}/x/0.WebP`,
        );
    });

    it('percent-encodes each path segment while preserving slashes', () => {
        expect(resolveExerciseMediaSrc('Front Squat/a b.png')).toBe(
            `${VENDOR_BASE_URL}/Front%20Squat/a%20b.png`,
        );
    });

    it('rejects non-string input', () => {
        expect(resolveExerciseMediaSrc(null)).toBeNull();
        expect(resolveExerciseMediaSrc(undefined)).toBeNull();
        expect(resolveExerciseMediaSrc(123)).toBeNull();
        expect(resolveExerciseMediaSrc({})).toBeNull();
    });

    it('rejects empty strings', () => {
        expect(resolveExerciseMediaSrc('')).toBeNull();
    });

    it('rejects absolute paths (leading slash or backslash)', () => {
        expect(resolveExerciseMediaSrc('/etc/passwd.png')).toBeNull();
        expect(resolveExerciseMediaSrc('\\server\\x.png')).toBeNull();
    });

    it('rejects backslashes and drive-letter colons anywhere', () => {
        expect(resolveExerciseMediaSrc('a\\b.png')).toBeNull();
        expect(resolveExerciseMediaSrc('C:/x.png')).toBeNull();
    });

    it('rejects dot and dot-dot traversal and empty segments', () => {
        expect(resolveExerciseMediaSrc('../x.png')).toBeNull();
        expect(resolveExerciseMediaSrc('a/../b.png')).toBeNull();
        expect(resolveExerciseMediaSrc('a/./b.png')).toBeNull();
        expect(resolveExerciseMediaSrc('a//b.png')).toBeNull();
    });

    it('rejects missing or disallowed extensions', () => {
        expect(resolveExerciseMediaSrc('x/0')).toBeNull();
        expect(resolveExerciseMediaSrc('x/0.svg')).toBeNull();
        expect(resolveExerciseMediaSrc('x/0.txt')).toBeNull();
    });
});
