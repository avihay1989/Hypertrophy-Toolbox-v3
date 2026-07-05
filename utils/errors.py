"""
Standardized API error responses and helpers.
"""
from typing import Optional, Dict, Any

from flask import jsonify, request, make_response

from utils.request_id import get_request_id


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def success_response(data: Any = None, message: Optional[str] = None) -> Dict:
    """
    Standard success response format.
    
    Args:
        data: Response data (optional)
        message: Optional success message
    
    Returns:
        Dict with standardized success format
    """
    response = {"ok": True, "status": "success"}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    
    # Add request ID if available
    request_id = get_request_id()
    if request_id:
        response["requestId"] = request_id
    
    return response


def is_xhr_request() -> bool:
    """Determine whether the current request expects a JSON (XHR/API) response."""
    if not request:
        return False

    requested_with = request.headers.get('X-Requested-With', '').lower()
    if requested_with == 'xmlhttprequest':
        return True

    accept_header = request.headers.get('Accept', '')
    if 'application/json' in accept_header.lower():
        return True

    path = getattr(request, 'path', '') or ''
    if path.startswith('/api/'):
        return True

    return False


def error_response(code: str, message: str, status_code: int = 400, **kwargs) -> tuple:
    """
    Standard error response format. Always returns JSON payload expected by API tests.
    
    Args:
        code: Error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        message: Error message
        status_code: HTTP status code
        **kwargs: Additional error details
    
    Returns:
        Tuple of (response, status_code)
    """
    from utils.logger import get_logger
    logger = get_logger()
    
    request_id = get_request_id()
    
    # Add request context to error
    endpoint = request.endpoint if request else None
    method = request.method if request else None
    path = request.path if request else None
    user_agent = request.headers.get('User-Agent', '')[:50] if request else None  # Truncate to 50 chars
    
    error_data = {
        "ok": False,
        "status": "error",
        "message": message,
        "error": {
            "code": code,
            "message": message,
            "requestId": request_id,
            **kwargs
        }
    }
    
    # Log error with full context
    logger.error(
        f"API error: {code} - {message}",
        extra={
            'error_code': code,
            'status_code': status_code,
            'endpoint': endpoint,
            'method': method,
            'path': path,
            'user_agent': user_agent,
            'request_id': request_id
        }
    )
    
    return jsonify(error_data), status_code


# Common error codes
ERROR_CODES = {
    "VALIDATION_ERROR": 400,
    "NOT_FOUND": 404,
    "FORBIDDEN": 403,
    "INTERNAL_ERROR": 500,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "UNPROCESSABLE_ENTITY": 422,
}


def register_error_handlers(app):
    """
    Register standardized error handlers for common HTTP errors.
    
    Args:
        app: Flask application instance
    """
    def _html_error(status_code: int, title: str, message: str):
        html = (
            "<!DOCTYPE html>"
            "<html lang='en'>"
            "<head><meta charset='utf-8'><title>{title}</title></head>"
            "<body>"
            f"<h1>{title}</h1>"
            f"<p>{message}</p>"
            "</body></html>"
        )
        response = make_response(html, status_code)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response

    @app.errorhandler(400)
    def bad_request(e):
        """Handle 400 Bad Request errors."""
        if is_xhr_request():
            return error_response(
                "BAD_REQUEST",
                "The request could not be understood or was missing required parameters.",
                400
            )
        return _html_error(400, "Bad Request", "The request could not be understood or was missing required parameters.")
    
    @app.errorhandler(422)
    def unprocessable_entity(e):
        """Handle 422 Unprocessable Entity errors."""
        if is_xhr_request():
            return error_response(
                "UNPROCESSABLE_ENTITY",
                "The request was well-formed but contained invalid data.",
                422
            )
        return _html_error(422, "Unprocessable Entity", "The request was well-formed but contained invalid data.")
    
    @app.errorhandler(500)
    def internal_error(e):
        """Handle 500 Internal Server errors."""
        # Get request context for logging
        request_id = get_request_id()
        endpoint = request.endpoint if request else None
        method = request.method if request else None
        path = request.path if request else None
        user_agent = request.headers.get('User-Agent', '')[:50] if request else None
        
        # Log the error with full context
        app.logger.exception(
            f"Internal server error",
            extra={
                'status_code': 500,
                'endpoint': endpoint,
                'method': method,
                'path': path,
                'user_agent': user_agent,
                'request_id': request_id
            }
        )
        
        if is_xhr_request():
            return error_response(
                "INTERNAL_ERROR",
                "An internal server error occurred. Please try again later.",
                500
            )
        return _html_error(500, "Internal Server Error", "An internal server error occurred. Please try again later.")
    
    @app.errorhandler(APIError)
    def handle_api_error(e):
        """Handle custom APIError exceptions."""
        return error_response(e.code, e.message, e.status_code)

