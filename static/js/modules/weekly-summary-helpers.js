// Pure helpers for the weekly (Plan Volume) summary page.
//
// Extracted verbatim from the page-local inline script in
// templates/weekly_summary.html (Refactor Plan v3 WP3.2a). These are
// DOM-free and side-effect-free so they can be unit-tested under the
// node-environment Vitest runner; the DOM wiring that consumes them lives
// in weekly-summary.js. Behavior is preserved exactly — this is a move,
// not a rewrite.

// Volume classification details based on effective sets.
export function getVolumeDetails(effectiveSets) {
    let volumeClass, volumeLabel;

    if (effectiveSets < 10) {
        volumeClass = 'low-volume';
        volumeLabel = 'Low Volume';
    } else if (effectiveSets < 20) {
        volumeClass = 'medium-volume';
        volumeLabel = 'Medium Volume';
    } else if (effectiveSets < 30) {
        volumeClass = 'high-volume';
        volumeLabel = 'High Volume';
    } else {
        volumeClass = 'ultra-volume';
        volumeLabel = 'Excessive Volume';
    }

    const ranges = {
        'Low Volume': 'Below 10 effective sets',
        'Medium Volume': '10-19 effective sets',
        'High Volume': '20-29 effective sets',
        'Excessive Volume': '30+ effective sets'
    };

    return {
        class: volumeClass,
        label: volumeLabel,
        tooltip: `${volumeLabel}: ${ranges[volumeLabel]} (Current: ${effectiveSets.toFixed(1)} effective sets)`
    };
}

// Movement-pattern display name formatting.
export function formatPatternName(pattern) {
    const nameMap = {
        'squat': 'Squat',
        'hinge': 'Hinge',
        'horizontal_push': 'Horizontal Push',
        'horizontal_pull': 'Horizontal Pull',
        'vertical_push': 'Vertical Push',
        'vertical_pull': 'Vertical Pull',
        'core_static': 'Core (Static)',
        'core_dynamic': 'Core (Dynamic)',
        'upper_isolation': 'Upper Isolation',
        'lower_isolation': 'Lower Isolation',
        'other': 'Other'
    };
    return nameMap[pattern] || pattern.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

export function isWrappedApiResponse(payload) {
    return Boolean(
        payload &&
        typeof payload === 'object' &&
        !Array.isArray(payload) &&
        'data' in payload &&
        (payload.ok === true || payload.status === 'success' || payload.success === true)
    );
}

export function isApiFailure(payload) {
    return Boolean(
        payload &&
        typeof payload === 'object' &&
        (payload.ok === false || payload.success === false)
    );
}

export function unwrapApiPayload(payload) {
    return isWrappedApiResponse(payload) ? payload.data : payload;
}

export function getApiErrorMessage(payload, fallbackMessage) {
    if (!payload || typeof payload !== 'object') {
        return fallbackMessage;
    }

    if (payload.error && typeof payload.error === 'object' && typeof payload.error.message === 'string') {
        return payload.error.message;
    }

    if (typeof payload.error === 'string') {
        return payload.error;
    }

    if (typeof payload.message === 'string' && payload.message.trim()) {
        return payload.message;
    }

    return fallbackMessage;
}

export function getCategoryTooltip(category) {
    const tooltips = {
        'Mechanic': 'Classification based on joint involvement in the exercise',
        'Utility': 'Classification based on exercise role in training',
        'Force': 'Classification based on primary force direction'
    };
    return tooltips[category] || '';
}

export function getSubcategoryTooltip(category, subcategory) {
    const tooltips = {
        'Mechanic': {
            'Compound': 'Multi-joint exercises like squats and bench press',
            'Isolated': 'Single-joint exercises focusing on specific muscles'
        },
        'Utility': {
            'Auxiliary': 'Supportive exercises that complement main lifts',
            'Basic': 'Foundational exercises targeting major muscle groups'
        },
        'Force': {
            'Push': 'Exercises involving pushing motions away from body',
            'Pull': 'Exercises involving pulling motions toward body'
        }
    };
    return tooltips[category]?.[subcategory] || '';
}
