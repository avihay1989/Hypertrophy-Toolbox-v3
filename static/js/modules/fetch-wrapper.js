/**
 * Global fetch wrapper with error handling, loading indicators, and retry logic.
 * Provides consistent error handling and logging across all API calls.
 */

import { showToast } from './toast.js';

const HANDLED_UI_ERROR_CODES = new Set(['VALIDATION_ERROR', 'NOT_FOUND', 'NO_DATA']);

/**
 * Global loading indicator counter
 */
let activeRequests = 0;

/**
 * Show/hide global loading indicator
 */
function updateLoadingIndicator() {
    let indicator = document.getElementById('global-loading-indicator');
    
    if (!indicator) {
        // Create indicator if it doesn't exist
        indicator = document.createElement('div');
        indicator.id = 'global-loading-indicator';
        indicator.className = 'global-loading-indicator';
        indicator.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        `;
        document.body.appendChild(indicator);
    }
    
    if (activeRequests > 0) {
        indicator.classList.add('active');
    } else {
        indicator.classList.remove('active');
    }
}

/**
 * Generate a unique request ID for tracking
 */
function generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Normalize error response to a consistent format
 */
function normalizeError(error, requestId) {
    // Already normalized (has code + message) — return as-is to prevent double-normalization
    if (error && error.code && error.message && !(error instanceof Error)) {
        return error;
    }

    // Check if error response has our standard format
    if (error.ok === false && error.error) {
        return {
            code: error.error.code || 'UNKNOWN_ERROR',
            message: error.error.message || 'An unexpected error occurred',
            requestId: error.error.requestId || requestId
        };
    }

    // Handle network errors or non-JSON responses
    if (error instanceof Error) {
        return {
            code: 'NETWORK_ERROR',
            message: error.message || 'Network error occurred',
            requestId: requestId
        };
    }

    // Fallback for unexpected error formats
    return {
        code: 'UNKNOWN_ERROR',
        message: typeof error === 'string' ? error : 'An unexpected error occurred',
        requestId: requestId
    };
}

/**
 * Errors that map to an expected user-facing flow should not be treated like
 * uncaught runtime failures in the browser console.
 */
export function isHandledApiError(error) {
    return Boolean(error && typeof error === 'object' && HANDLED_UI_ERROR_CODES.has(error.code));
}

/**
 * Keep unexpected failures loud while downgrading handled validation/no-data
 * responses to warnings.
 */
export function logApiError(context, error) {
    const logger = isHandledApiError(error) ? console.warn : console.error;
    logger(context, error);
}

/**
 * Delay helper for retry logic
 */
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Global fetch wrapper with enhanced features
 * 
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @param {string} options.method - HTTP method (default: 'GET')
 * @param {Object} options.headers - Additional headers
 * @param {any} options.body - Request body
 * @param {boolean} options.showLoading - Show loading indicator (default: true)
 * @param {boolean} options.showErrorToast - Show error toast on failure (default: true)
 * @param {number} options.retries - Number of retries for idempotent requests (default: 2 for GET, 0 for others)
 * @param {number} options.retryDelay - Delay between retries in ms (default: 1000)
 * @returns {Promise<Object>} Response data
 */
export async function apiFetch(url, options = {}) {
    const {
        method = 'GET',
        headers = {},
        body = null,
        showLoading = true,
        showErrorToast = true,
        retries = method === 'GET' ? 2 : 0,
        retryDelay = 1000,
        ...fetchOptions
    } = options;

    const requestId = generateRequestId();
    let attempt = 0;
    
    // Default headers
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Request-ID': requestId,
    };
    
    const mergedHeaders = { ...defaultHeaders, ...headers };
    
    // If body is an object, stringify it
    const processedBody = body && typeof body === 'object' ? JSON.stringify(body) : body;
    
    const fetchConfig = {
        method,
        headers: mergedHeaders,
        ...fetchOptions
    };
    
    if (processedBody) {
        fetchConfig.body = processedBody;
    }

    // Show loading indicator
    if (showLoading) {
        activeRequests++;
        updateLoadingIndicator();
    }

    try {
        while (attempt <= retries) {
            try {
                const response = await fetch(url, fetchConfig);
                
                // Parse JSON response
                let data;
                const contentType = response.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                    data = await response.json();
                } else {
                    // Preserve the real HTTP success state even for legacy HTML/redirect responses.
                    const text = await response.text();
                    data = { ok: response.ok, data: text };
                }
                
                // Add request ID to response
                if (data && typeof data === 'object') {
                    data.requestId = data.requestId || requestId;
                }
                
                // Handle HTTP errors
                if (!response.ok) {
                    const errorInfo = normalizeError(data, requestId);
                    
                    // Log error with request ID
                    console.error(`[${requestId}] API Error:`, {
                        url,
                        method,
                        status: response.status,
                        error: errorInfo
                    });
                    
                    // Show error toast if enabled
                    if (showErrorToast) {
                        showToast('error', errorInfo.message, { requestId: errorInfo.requestId });
                    }
                    
                    throw errorInfo;
                }
                
                // Success
                console.log(`[${requestId}] API Success:`, { url, method });
                return data;
                
            } catch (error) {
                // Determine if we should retry
                const isRetryable = method === 'GET' && attempt < retries;
                
                if (isRetryable) {
                    attempt++;
                    console.warn(`[${requestId}] Retrying request (${attempt}/${retries})...`);
                    await delay(retryDelay * attempt); // Exponential backoff
                    continue;
                }
                
                // No more retries, throw the error
                const errorInfo = normalizeError(error, requestId);
                
                // Log error
                console.error(`[${requestId}] API Error (final):`, {
                    url,
                    method,
                    error: errorInfo
                });
                
                // Show error toast if enabled and not already shown
                if (showErrorToast && !(error.code)) {
                    showToast('error', errorInfo.message, { requestId: errorInfo.requestId });
                }
                
                throw errorInfo;
            }
        }
    } finally {
        // Hide loading indicator
        if (showLoading) {
            activeRequests--;
            updateLoadingIndicator();
        }
    }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const api = {
    get: (url, options = {}) => apiFetch(url, { ...options, method: 'GET' }),
    post: (url, body, options = {}) => apiFetch(url, { ...options, method: 'POST', body }),
    put: (url, body, options = {}) => apiFetch(url, { ...options, method: 'PUT', body }),
    patch: (url, body, options = {}) => apiFetch(url, { ...options, method: 'PATCH', body }),
    delete: (url, options = {}) => apiFetch(url, { ...options, method: 'DELETE' }),
};

/**
 * Export for direct fetch wrapper usage
 */
export default apiFetch;
