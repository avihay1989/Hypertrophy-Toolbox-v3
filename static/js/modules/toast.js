/**
 * Toast notification functionality with standardized types.
 * 
 * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info'
 * @param {string} message - Message to display
 * @param {Object} options - Optional configuration
 * @param {number} options.duration - Duration in ms (default: 3000)
 * @param {string} options.requestId - Optional request ID for debugging
 * @param {{label: string, onClick: () => void, ariaLabel?: string}} options.action - Optional inline action button
 */
export function showToast(type, message, options = {}) {
    const validTypes = new Set(['success', 'error', 'warning', 'info']);

    // Backward compatibility: detect legacy signature showToast(message, isError?, duration?)
    if (!validTypes.has(type)) {
        const legacyMessage = type;
        const legacyIsError = typeof message === 'boolean' ? message : false;
        const legacyDuration = typeof options === 'number' ? options : undefined;
        const legacyOptions = typeof options === 'object' && options !== null ? { ...options } : {};

        type = legacyIsError ? 'error' : 'success';
        message = legacyMessage;
        options = legacyOptions;

        if (legacyDuration !== undefined) {
            options.duration = legacyDuration;
        }
    } else if (typeof options === 'number') {
        // Support showToast('success', 'Message', 5000)
        options = { duration: options };
    }

    const { duration = 3000, requestId = null, action = null } = options;

    const toastBody = document.getElementById("toast-body");
    if (!toastBody) {
        console.error("Error: toast-body not found in the DOM!");
        return;
    }

    const toastElement = document.getElementById("liveToast");
    if (!toastElement) {
        console.error("Error: liveToast not found in the DOM!");
        return;
    }

    // Ensure message is a readable string
    let displayMessage;
    if (message !== undefined && message !== null) {
        displayMessage = String(message);
    } else {
        displayMessage = type === 'error' ? 'An unexpected error occurred.' : 'Action completed successfully.';
    }

    // Set message with optional request ID for debugging
    if (requestId && type === 'error') {
        displayMessage += ` (Request ID: ${requestId})`;
    }

    toastBody.innerHTML = '';
    const messageSpan = document.createElement('span');
    messageSpan.textContent = displayMessage;
    toastBody.appendChild(messageSpan);

    if (action && typeof action.onClick === 'function' && action.label) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-sm btn-link text-white text-decoration-underline ms-2 p-0 align-baseline';
        button.textContent = String(action.label);
        if (action.ariaLabel) {
            button.setAttribute('aria-label', action.ariaLabel);
        }
        button.addEventListener('click', () => {
            const instance = bootstrap.Toast.getInstance(toastElement);
            if (instance) {
                instance.hide();
            }
            try {
                action.onClick();
            } catch (err) {
                console.error('Toast action handler failed:', err);
            }
        });
        toastBody.appendChild(button);
    }

    // Remove all possible background classes
    toastElement.classList.remove("bg-success", "bg-danger", "bg-warning", "bg-info");
    
    // Map type to Bootstrap background class
    const typeToClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    };
    
    const bgClass = typeToClass[type] || 'bg-success';
    toastElement.classList.add(bgClass);

    // Dispose any existing toast instance to prevent animation conflicts
    // This ensures clean transitions when showing rapid notifications
    const existingToast = bootstrap.Toast.getInstance(toastElement);
    if (existingToast) {
        existingToast.dispose();
    }

    const toast = new bootstrap.Toast(toastElement, { delay: duration });
    toast.show();
}

/**
 * Backward compatibility: Legacy function signature
 * @deprecated Use showToast(type, message, options) instead
 */
export function showToastLegacy(message, isError = false, duration = 3000) {
    showToast(isError ? 'error' : 'success', message, { duration });
}

/**
 * Show inline error message near a form field
 * @param {string} fieldId - ID of the form field
 * @param {string} message - Error message to display
 */
export function showInlineError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (!field) {
        console.warn(`Field with ID '${fieldId}' not found`);
        return;
    }

    // Remove any existing error message
    const existingError = field.parentElement.querySelector('.inline-error');
    if (existingError) {
        existingError.remove();
    }

    // Create and insert error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'inline-error text-danger small mt-1';
    errorDiv.setAttribute('role', 'alert');
    errorDiv.textContent = message;
    
    // Add error styling to field
    field.classList.add('is-invalid');
    
    // Insert after the field
    field.parentElement.insertBefore(errorDiv, field.nextSibling);
}

/**
 * Clear inline error for a form field
 * @param {string} fieldId - ID of the form field
 */
export function clearInlineError(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    field.classList.remove('is-invalid');
    
    const errorDiv = field.parentElement.querySelector('.inline-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

/**
 * Clear all inline errors in a form
 * @param {string} formId - ID of the form
 */
export function clearAllInlineErrors(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const errors = form.querySelectorAll('.inline-error');
    errors.forEach(error => error.remove());
    
    const invalidFields = form.querySelectorAll('.is-invalid');
    invalidFields.forEach(field => field.classList.remove('is-invalid'));
} 