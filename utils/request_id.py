"""
Request ID middleware for request tracking and log correlation.
"""
import uuid
from flask import request, g


def generate_request_id():
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:16]}"


def get_request_id():
    """Get the current request ID from Flask g object."""
    return getattr(g, 'request_id', None)


def add_request_id_middleware(app):
    """
    Add middleware to generate and track request IDs.
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request():
        """Generate or extract request ID before each request."""
        # Try to get request ID from header (sent by client)
        request_id = request.headers.get('X-Request-ID')
        
        # If not provided, generate one
        if not request_id:
            request_id = generate_request_id()
        
        # Store in Flask g object for access throughout request
        g.request_id = request_id
    
    @app.after_request
    def after_request(response):
        """Add request ID to response headers."""
        request_id = get_request_id()
        if request_id:
            response.headers['X-Request-ID'] = request_id
        return response

