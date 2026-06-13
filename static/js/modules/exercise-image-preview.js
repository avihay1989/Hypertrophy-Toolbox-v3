const PREVIEW_SELECTOR = 'img.exercise-thumbnail, img.reference-lift-icon';
const EDGE_GAP = 14;

let preview;
let previewImage;
let previewCaption;
let activeTarget = null;
const initializedRoots = new WeakSet();

function ensurePreview() {
    if (preview) return preview;

    preview = document.createElement('div');
    preview.className = 'exercise-image-preview';
    preview.hidden = true;
    preview.setAttribute('role', 'tooltip');

    previewImage = document.createElement('img');
    previewImage.className = 'exercise-image-preview__img';
    previewImage.alt = '';

    previewCaption = document.createElement('div');
    previewCaption.className = 'exercise-image-preview__caption';

    preview.append(previewImage, previewCaption);
    document.body.appendChild(preview);
    return preview;
}

function previewLabelFor(target) {
    return (
        target.dataset.previewLabel
        || target.getAttribute('alt')
        || target.closest('[data-lift-key]')?.querySelector('.exercise-name, .reference-lift-label-text span')?.textContent
        || 'Exercise reference'
    ).trim();
}

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

function positionPreview(target) {
    if (!preview || !target) return;

    const targetRect = target.getBoundingClientRect();
    const previewRect = preview.getBoundingClientRect();
    const width = previewRect.width || 280;
    const height = previewRect.height || 300;

    let left = targetRect.right + EDGE_GAP;
    if (left + width > window.innerWidth - EDGE_GAP) {
        left = targetRect.left - width - EDGE_GAP;
    }
    left = clamp(left, EDGE_GAP, Math.max(EDGE_GAP, window.innerWidth - width - EDGE_GAP));

    let top = targetRect.top + (targetRect.height / 2) - (height / 2);
    top = clamp(top, EDGE_GAP, Math.max(EDGE_GAP, window.innerHeight - height - EDGE_GAP));

    preview.style.left = `${Math.round(left)}px`;
    preview.style.top = `${Math.round(top)}px`;
}

function showPreview(target) {
    if (!target?.src) return;

    ensurePreview();
    activeTarget = target;
    previewImage.src = target.currentSrc || target.src;
    previewCaption.textContent = previewLabelFor(target);
    preview.hidden = false;
    preview.dataset.visible = 'true';
    target.setAttribute('aria-describedby', 'exercise-image-preview');
    preview.id = 'exercise-image-preview';

    window.requestAnimationFrame(() => positionPreview(target));
}

function hidePreview(target = activeTarget) {
    if (target) {
        const describedBy = target.getAttribute('aria-describedby');
        if (describedBy === 'exercise-image-preview') {
            target.removeAttribute('aria-describedby');
        }
    }
    activeTarget = null;
    if (preview) {
        preview.dataset.visible = 'false';
        preview.hidden = true;
        previewImage.removeAttribute('src');
    }
}

function targetFromEvent(event) {
    return event.target instanceof Element
        ? event.target.closest(PREVIEW_SELECTOR)
        : null;
}

export function initializeExerciseImagePreview(root = document) {
    if (initializedRoots.has(root)) return;
    initializedRoots.add(root);

    root.addEventListener('mouseover', (event) => {
        const target = targetFromEvent(event);
        if (!target || target === activeTarget) return;
        showPreview(target);
    });

    root.addEventListener('mouseout', (event) => {
        const target = targetFromEvent(event);
        if (!target || target !== activeTarget) return;
        hidePreview(target);
    });

    root.addEventListener('focusin', (event) => {
        const target = targetFromEvent(event);
        if (target) showPreview(target);
    });

    root.addEventListener('focusout', (event) => {
        const target = targetFromEvent(event);
        if (target && target === activeTarget) hidePreview(target);
    });

    window.addEventListener('scroll', () => positionPreview(activeTarget), true);
    window.addEventListener('resize', () => positionPreview(activeTarget));
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && activeTarget) hidePreview();
    });
}
