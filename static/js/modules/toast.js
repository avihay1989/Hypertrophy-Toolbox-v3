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

