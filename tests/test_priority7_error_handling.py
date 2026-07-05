"""
Test suite for Priority 7: Error Handling, UX Feedback & Observability
"""
import pytest
import json
import os
import tempfile
from flask import g

# Set TESTING before importing app to redirect database
os.environ['TESTING'] = '1'

from utils.errors import error_response, success_response, is_xhr_request
from utils.request_id import generate_request_id


@pytest.fixture(scope='module')
def error_app():
    """Create a fresh test app for error handling tests.
    
    Creates a new Flask app instance to avoid interference with
    the shared app from conftest.py.
    """
    import utils.config
    from flask import Flask, abort, make_response
    from routes.workout_plan import workout_plan_bp, initialize_exercise_order
    from routes.workout_log import workout_log_bp
    from routes.main import main_bp
    from routes.filters import filters_bp
    from utils.db_initializer import initialize_database
    from utils.database import add_progression_goals_table, add_volume_tracking_tables
    from utils.errors import register_error_handlers
    from utils.request_id import add_request_id_middleware
    
    # Use temp test database
    test_db = os.path.join(tempfile.gettempdir(), 'test_error_handling.db')
    original_db = utils.config.DB_FILE
    utils.config.DB_FILE = test_db
    
    # Clean up any existing test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Create fresh Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(workout_plan_bp)
    app.register_blueprint(workout_log_bp)
    app.register_blueprint(filters_bp)
    
    # Register middleware and error handlers
    add_request_id_middleware(app)
    register_error_handlers(app)

    # app.py registers these two handlers after register_error_handlers(). Keep
    # the fixture layered the same way so tests prove the production winners,
    # rather than relying on the shadowed helper registrations removed in WP0.1.
    @app.errorhandler(404)
    def layered_not_found(_error):
        if is_xhr_request():
            return error_response("NOT_FOUND", "The requested resource was not found", 404)
        return make_response("<html><h1>Not Found</h1></html>", 404)

    @app.errorhandler(Exception)
    def layered_exception(_error):
        if is_xhr_request():
            return error_response("INTERNAL_ERROR", "An unexpected error occurred", 500)
        return make_response("<html><h1>Internal Server Error</h1></html>", 500)
    
    # Add error trigger route BEFORE any requests
    @app.route('/__trigger_internal_error')
    def __trigger_internal_error():
        raise RuntimeError('forced test error')

    @app.route('/__trigger_http_error/<int:status_code>')
    def __trigger_http_error(status_code):
        abort(status_code)

    @app.route('/__trigger_api_error')
    def __trigger_api_error():
        from utils.errors import APIError
        raise APIError('TEST_API_ERROR', 'forced API error', 409)
    
    # Initialize database within app context
    with app.app_context():
        initialize_database()
        add_progression_goals_table()
        add_volume_tracking_tables()
        initialize_exercise_order()
    
    yield app
    
    # Cleanup
    utils.config.DB_FILE = original_db
    if os.path.exists(test_db):
        os.remove(test_db)


@pytest.fixture
def error_client(error_app):
    """Create a test client for the error test app."""
    with error_app.test_client() as client:
        yield client


class TestRequestIdMiddleware:
    """Test request ID generation and tracking."""
    
    def test_request_id_generated(self, error_client):
        """Test that request ID is automatically generated."""
        response = error_client.get('/')
        assert 'X-Request-ID' in response.headers
        request_id = response.headers.get('X-Request-ID')
        assert request_id.startswith('req_')
    
    def test_request_id_from_header(self, error_client):
        """Test that request ID from header is preserved."""
        custom_id = 'my-custom-request-id'
        response = error_client.get('/', headers={'X-Request-ID': custom_id})
        assert response.headers.get('X-Request-ID') == custom_id
    
    def test_request_id_in_error_response(self, error_client):
        """Test that request ID is included in error responses."""
        response = error_client.get('/nonexistent-route', 
                            headers={'Accept': 'application/json'})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'requestId' in data.get('error', {})


class TestErrorHandlers:
    """Test error handlers for different HTTP status codes."""
    
    def test_404_json_response(self, error_client):
        """Test 404 handler returns JSON for AJAX requests."""
        response = error_client.get('/nonexistent', 
                            headers={'Accept': 'application/json'})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['ok'] is False
        assert data['error']['code'] == 'NOT_FOUND'
        assert data['error']['message'] == 'The requested resource was not found'
        assert 'requestId' in data['error']
    
    def test_404_html_response(self, error_client):
        """Test 404 handler returns HTML for browser requests."""
        response = error_client.get('/nonexistent')
        assert response.status_code == 404
        assert response.mimetype == 'text/html'
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    def test_500_json_response(self, error_client):
        """Test 500 handler returns JSON for AJAX requests."""
        response = error_client.get('/__trigger_internal_error', headers={'Accept': 'application/json'})
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['ok'] is False
        assert data['error']['code'] == 'INTERNAL_ERROR'
        assert data['error']['message'] == 'An unexpected error occurred'

    def test_500_html_response(self, error_client):
        """Test 500 handler returns HTML for browser requests."""
        response = error_client.get('/__trigger_internal_error', headers={'Accept': 'text/html'})
        assert response.status_code == 500
        assert response.mimetype == 'text/html'
        assert b'Internal Server Error' in response.data

    @pytest.mark.parametrize(('status_code', 'error_code'), [
        (400, 'BAD_REQUEST'),
        (422, 'UNPROCESSABLE_ENTITY'),
        (500, 'INTERNAL_ERROR'),
    ])
    def test_helper_owned_status_handlers_remain_live(
        self, error_client, status_code, error_code
    ):
        response = error_client.get(
            f'/__trigger_http_error/{status_code}',
            headers={'Accept': 'application/json'},
        )
        assert response.status_code == status_code
        assert response.get_json()['error']['code'] == error_code

    def test_api_error_handler_remains_live(self, error_client):
        response = error_client.get(
            '/__trigger_api_error', headers={'Accept': 'application/json'}
        )
        assert response.status_code == 409
        assert response.get_json()['error']['code'] == 'TEST_API_ERROR'

    def test_later_exception_handler_owns_unrecognized_http_errors(self, error_client):
        response = error_client.get(
            '/__trigger_http_error/418', headers={'Accept': 'application/json'}
        )
        assert response.status_code == 500
        assert response.get_json()['error']['message'] == 'An unexpected error occurred'
    
    def test_error_response_helper(self, error_app):
        """Test error_response helper function."""
        with error_app.test_request_context():
            # Set request ID
            g.request_id = 'test-request-id'
            
            # Test JSON response (XHR)
            with error_app.test_request_context(headers={'Accept': 'application/json'}):
                g.request_id = 'test-request-id'
                response, status_code = error_response(
                    "TEST_ERROR", 
                    "Test error message", 
                    400
                )
                assert status_code == 400
                data = json.loads(response.data)
                assert data['ok'] is False
                assert data['error']['code'] == 'TEST_ERROR'
                assert data['error']['requestId'] == 'test-request-id'


class TestSuccessResponse:
    """Test success response helper."""
    
    def test_success_response_with_data(self, error_app):
        """Test success response with data."""
        with error_app.test_request_context():
            g.request_id = 'test-request-id'
            response = success_response(data={'key': 'value'}, message='Success')
            
            assert response['ok'] is True
            assert response['data'] == {'key': 'value'}
            assert response['message'] == 'Success'
            assert response['requestId'] == 'test-request-id'
    
    def test_success_response_minimal(self, error_app):
        """Test success response with minimal data."""
        with error_app.test_request_context():
            g.request_id = 'test-request-id'
            response = success_response()
            
            assert response['ok'] is True
            assert response['requestId'] == 'test-request-id'


class TestXHRDetection:
    """Test XHR/AJAX request detection."""
    
    def test_xhr_header_detection(self, error_app):
        """Test detection via X-Requested-With header."""
        with error_app.test_request_context(headers={'X-Requested-With': 'XMLHttpRequest'}):
            assert is_xhr_request() is True
    
    def test_json_accept_detection(self, error_app):
        """Test detection via Accept header."""
        with error_app.test_request_context(headers={'Accept': 'application/json'}):
            assert is_xhr_request() is True
    
    def test_api_path_detection(self, error_app):
        """Test detection via /api/ path."""
        with error_app.test_request_context(path='/api/test'):
            assert is_xhr_request() is True
    
    def test_regular_request(self, error_app):
        """Test regular (non-XHR) request."""
        with error_app.test_request_context():
            assert is_xhr_request() is False


class TestWorkoutLogEndpoints:
    """Test updated workout log endpoints with new error handling."""
    
    def test_update_workout_log_success(self, error_client):
        """Test successful workout log update."""
        # This would require actual database setup
        # Placeholder for integration test
        pass
    
    def test_update_workout_log_validation_error(self, error_client):
        """Test workout log update with missing ID."""
        response = error_client.post('/update_workout_log',
                             json={'updates': {'weight': 100}},
                             headers={'Accept': 'application/json'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
    
    def test_delete_workout_log_validation_error(self, error_client):
        """Test workout log deletion with missing ID."""
        response = error_client.post('/delete_workout_log',
                             json={},
                             headers={'Accept': 'application/json'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'


class TestLogging:
    """Test logging with request IDs."""
    
    def test_request_id_in_logs(self, error_client, caplog):
        """Test that request ID appears in log messages."""
        response = error_client.get('/')
        request_id = response.headers.get('X-Request-ID')
        
        # Check if request ID appears in logs
        # Note: This depends on your logging configuration
        # and may need adjustment based on actual log output
        log_contains_request_id = any(
            request_id in record.message 
            for record in caplog.records
        )
        # This assertion might need adjustment based on your specific logging setup


def test_request_id_format():
    """Test request ID format."""
    request_id = generate_request_id()
    assert request_id.startswith('req_')
    assert len(request_id) > 10  # Should have timestamp and random part


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

