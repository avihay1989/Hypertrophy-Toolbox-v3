/**
 * §5 — Exercise reference video modal (Pattern A: single button → modal).
 *
 * Public API:
 *   openExerciseVideoModal(videoId, exerciseName)
 *     - videoId: 11-char YouTube video id, or null/empty to fall back to search
 *     - exerciseName: human-readable name; rendered in title + alt text
 *
 *   buildPlayButton({ videoId, exerciseName }) -> HTMLButtonElement
 *     Convenience helper used by the row renderer to build a row-action play
 *     button. Returns a <button> with the click handler already wired.
 *
 * Behavior:
 *   - Opening sets the iframe src; closing clears it so playback stops.
 *   - 11-char id regex (^[A-Za-z0-9_-]{11}$) is enforced client-side; anything
 *     else (NULL, '', malformed) falls through to the YouTube-search variant.
 *   - On close, focus returns to the trigger button.
 *
 * No network requests are made directly — the modal embeds via the official
 * youtube.com/embed iframe and links out to youtube.com/results for search.
 */

const YOUTUBE_ID_RE = /^[A-Za-z0-9_-]{11}$/;

const SEL = {
    modal: '#exerciseVideoModal',
    title: '#exerciseVideoModalExerciseName',
    embedWrap: '#exerciseVideoEmbedWrap',
    iframe: '#exerciseVideoIframe',
    searchWrap: '#exerciseVideoSearchWrap',
    searchName: '#exerciseVideoSearchExerciseName',
    externalLink: '#exerciseVideoExternalLink',
    externalLabel: '#exerciseVideoExternalLabel',
};

function isValidYoutubeId(value) {
    return typeof value === 'string' && YOUTUBE_ID_RE.test(value);
}

function buildEmbedUrl(videoId) {
    return `https://www.youtube.com/embed/${encodeURIComponent(videoId)}`;
}

function buildWatchUrl(videoId) {
    return `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`;
}

function buildSearchUrl(exerciseName) {
    const q = encodeURIComponent(`${exerciseName || ''} exercise form`.trim());
    return `https://www.youtube.com/results?search_query=${q}`;
}

let lastTriggerEl = null;
let modalInstance = null;

function getBootstrapModal() {
    if (modalInstance) return modalInstance;
    const modalEl = document.querySelector(SEL.modal);
    if (!modalEl) return null;
    if (typeof window.bootstrap === 'undefined' || !window.bootstrap.Modal) {
        return null;
    }
    modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalEl, {
        backdrop: true,
        keyboard: true,
    });

    // On close, blank the iframe so audio/video stops, and return focus.
    modalEl.addEventListener('hidden.bs.modal', () => {
        const iframe = document.querySelector(SEL.iframe);
        if (iframe) {
            iframe.src = '';
        }
        if (lastTriggerEl && typeof lastTriggerEl.focus === 'function') {
            lastTriggerEl.focus();
        }
        lastTriggerEl = null;
    });

    return modalInstance;
}

/**
 * Open the modal for `videoId` (or the search fallback if id is invalid/null).
 * @param {string|null|undefined} videoId
 * @param {string} exerciseName
 * @param {HTMLElement} [trigger] - element to return focus to on close
 */
export function openExerciseVideoModal(videoId, exerciseName, trigger = null) {
    const modal = getBootstrapModal();
    if (!modal) {
        // Bootstrap not loaded; surface the search url externally as a safe
        // fallback so the click is never a no-op.
        const url = isValidYoutubeId(videoId)
            ? buildWatchUrl(videoId)
            : buildSearchUrl(exerciseName);
        window.open(url, '_blank', 'noopener,noreferrer');
        return;
    }

    lastTriggerEl = trigger || document.activeElement;

    const titleEl = document.querySelector(SEL.title);
    const embedWrap = document.querySelector(SEL.embedWrap);
    const iframe = document.querySelector(SEL.iframe);
    const searchWrap = document.querySelector(SEL.searchWrap);
    const searchName = document.querySelector(SEL.searchName);
    const externalLink = document.querySelector(SEL.externalLink);
    const externalLabel = document.querySelector(SEL.externalLabel);

    if (titleEl) {
        titleEl.textContent = exerciseName || 'Reference video';
    }

    const valid = isValidYoutubeId(videoId);

    if (valid) {
        if (iframe) {
            iframe.src = buildEmbedUrl(videoId);
            iframe.title = `${exerciseName || 'Exercise'} reference video`;
        }
        if (embedWrap) embedWrap.hidden = false;
        if (searchWrap) searchWrap.hidden = true;
        if (externalLink) externalLink.href = buildWatchUrl(videoId);
        if (externalLabel) externalLabel.textContent = 'Watch on YouTube';
    } else {
        if (iframe) iframe.src = '';
        if (embedWrap) embedWrap.hidden = true;
        if (searchWrap) searchWrap.hidden = false;
        if (searchName) searchName.textContent = exerciseName || 'this exercise';
        if (externalLink) externalLink.href = buildSearchUrl(exerciseName);
        if (externalLabel) externalLabel.textContent = 'Search YouTube';
    }

    modal.show();
}

/**
 * Build a play-icon button that opens the modal for the given exercise.
 * Caller appends it into the Exercise-cell action cluster.
 *
 * @param {object} opts
 * @param {string|null|undefined} opts.videoId
 * @param {string} opts.exerciseName
 * @returns {HTMLButtonElement}
 */
export function buildPlayButton({ videoId, exerciseName }) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-video btn-calm-ghost';
    btn.dataset.action = 'play-video';
    btn.setAttribute(
        'aria-label',
        `Play reference video for ${exerciseName || 'exercise'}`,
    );
    btn.title = isValidYoutubeId(videoId)
        ? 'Watch reference video'
        : 'Search YouTube for reference video';

    const icon = document.createElement('i');
    icon.className = 'fas fa-play';
    icon.setAttribute('aria-hidden', 'true');
    btn.appendChild(icon);

    if (isValidYoutubeId(videoId)) {
        btn.dataset.videoId = videoId;
    }
    btn.dataset.exerciseName = exerciseName || '';

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        openExerciseVideoModal(videoId, exerciseName, btn);
    });

    return btn;
}

// Expose to globals for inline-onclick / non-module callers (workout-log.html
// is server-rendered Jinja and uses inline handlers in places).
if (typeof window !== 'undefined') {
    window.openExerciseVideoModal = openExerciseVideoModal;
    window.buildExerciseVideoButton = buildPlayButton;
}
