// Shared helpers for rendering exercise rows.
//
// `escapeHtml(s)` mirrors the contract documented in
// docs/workout_cool_integration/PLANNING.md §4.4 Option A: every value
// interpolated into a workout-plan row template-literal must pass through
// it before reaching `innerHTML`.
//
// `resolveExerciseMediaSrc(mediaPath)` mirrors the §4.3 path-shape rules
// implemented in utils/media_path.py::is_valid_media_path_shape. The
// rules MUST be kept in sync with that file; see the docstring there for
// authoritative wording.

const ALLOWED_MEDIA_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
const MEDIA_EXTENSION_RE = new RegExp(
    `^\\.(?:${ALLOWED_MEDIA_EXTENSIONS.join('|')})$`,
    'i',
);
const VENDOR_BASE_URL = '/static/vendor/free-exercise-db/exercises';

export function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export function isValidMediaPathShape(value) {
    if (typeof value !== 'string') return false;
    if (value === '') return false;
    if (value.startsWith('/') || value.startsWith('\\')) return false;
    if (value.includes('\\')) return false;
    if (value.includes(':')) return false;
    const parts = value.split('/');
    if (parts.some((p) => p === '..' || p === '.' || p === '')) return false;
    const lastDot = value.lastIndexOf('.');
    const suffix = lastDot >= 0 ? value.slice(lastDot) : '';
    if (!MEDIA_EXTENSION_RE.test(suffix)) return false;
    return true;
}

export function resolveExerciseMediaSrc(mediaPath) {
    if (!isValidMediaPathShape(mediaPath)) return null;
    const encoded = mediaPath.split('/').map(encodeURIComponent).join('/');
    return `${VENDOR_BASE_URL}/${encoded}`;
}
