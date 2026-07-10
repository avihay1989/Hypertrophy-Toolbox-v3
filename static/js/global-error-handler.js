/**
 * Global Error Handler
 * Hides the error placeholder on load and logs (only) uncaught errors and
 * unhandled promise rejections. Loaded as a classic parse-time script on every
 * page so the window listeners register before the app modules run.
 */
(function () {
    'use strict';

    // Ensure error container is hidden on page load
    document.addEventListener('DOMContentLoaded', function() {
        const errorContainer = document.getElementById('error-message-container');
        if (errorContainer) {
            errorContainer.classList.add('d-none');
            errorContainer.classList.remove('show-error');
            errorContainer.style.display = 'none';
        }
    });

    // Global error handler - only log, don't show UI
    window.addEventListener('error', function(e) {
        console.error('Global error caught:', {
            message: e.error?.message || e.message,
            filename: e.filename,
            line: e.lineno,
            column: e.colno,
            error: e.error
        });
    });

    // Handle unhandled promise rejections - only log
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
    });
})();
