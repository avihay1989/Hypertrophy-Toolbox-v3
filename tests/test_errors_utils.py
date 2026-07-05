"""
Tests for utils/errors.py

Covers API response formatting and error handling with focus on:
- success_response format and fields
- error_response format and fields  
- is_xhr_request header/path detection
- APIError exception class
- Error code constants
"""
import pytest
from flask import Flask, g
from utils.errors import (
    success_response,
    error_response,
    is_xhr_request,
    APIError,
    ERROR_CODES,
    get_request_id,
)
from utils.request_id import get_request_id as canonical_get_request_id


class TestSuccessResponse:
    """Tests for success_response function."""

    def test_basic_success_response(self, app):
        """Should return ok=True and status=success."""
        with app.test_request_context():
            response = success_response()
            assert response["ok"] is True
            assert response["status"] == "success"

    def test_success_response_with_data(self, app):
        """Should include data when provided."""
        with app.test_request_context():
            data = {"user_id": 123, "name": "Test"}
            response = success_response(data=data)
            assert response["ok"] is True
            assert response["data"] == data

    def test_success_response_with_message(self, app):
        """Should include message when provided."""
        with app.test_request_context():
            response = success_response(message="Operation completed")
            assert response["message"] == "Operation completed"

    def test_success_response_with_data_and_message(self, app):
        """Should include both data and message."""
        with app.test_request_context():
            response = success_response(
                data={"id": 1}, 
                message="Created successfully"
            )
            assert response["data"]["id"] == 1
            assert response["message"] == "Created successfully"

    def test_success_response_with_request_id(self, app):
        """Should include requestId when available in g."""
        with app.test_request_context():
            g.request_id = "test-request-123"
            response = success_response()
            assert response["requestId"] == "test-request-123"

    def test_success_response_without_request_id(self, app):
        """Should not include requestId when not in g."""
        with app.test_request_context():
            # Don't set g.request_id
            response = success_response()
            assert "requestId" not in response or response.get("requestId") is None


class TestErrorResponse:
    """Tests for error_response function."""

    def test_basic_error_response_format(self, app):
        """Should return error format with ok=False."""
        with app.test_request_context():
            response, status_code = error_response(
                "VALIDATION_ERROR", 
                "Invalid input", 
                400
            )
            data = response.get_json()
            
            assert data["ok"] is False
            assert data["status"] == "error"
            assert data["message"] == "Invalid input"
            assert status_code == 400

    def test_error_response_error_object(self, app):
        """Should include error object with code and message."""
        with app.test_request_context():
            response, _ = error_response("NOT_FOUND", "Resource not found", 404)
            data = response.get_json()
            
            assert data["error"]["code"] == "NOT_FOUND"
            assert data["error"]["message"] == "Resource not found"

    def test_error_response_with_kwargs(self, app):
        """Should pass through additional kwargs to error object."""
        with app.test_request_context():
            response, _ = error_response(
                "VALIDATION_ERROR",
                "Invalid field",
                400,
                field="email",
                expected="valid email format"
            )
            data = response.get_json()
            
            assert data["error"]["field"] == "email"
            assert data["error"]["expected"] == "valid email format"

    def test_error_response_status_codes(self, app):
        """Should return correct HTTP status codes."""
        with app.test_request_context():
            _, status_400 = error_response("BAD_REQUEST", "Bad", 400)
            _, status_404 = error_response("NOT_FOUND", "Not found", 404)
            _, status_500 = error_response("INTERNAL_ERROR", "Error", 500)
            
            assert status_400 == 400
            assert status_404 == 404
            assert status_500 == 500


class TestIsXhrRequest:
    """Tests for is_xhr_request detection function."""

    def test_xmlhttprequest_header(self, app):
        """Should detect X-Requested-With: XMLHttpRequest."""
        with app.test_request_context(
            headers={"X-Requested-With": "XMLHttpRequest"}
        ):
            assert is_xhr_request() is True

    def test_xmlhttprequest_header_case_insensitive(self, app):
        """Should detect header case-insensitively."""
        with app.test_request_context(
            headers={"X-Requested-With": "xmlhttprequest"}
        ):
            assert is_xhr_request() is True

    def test_accept_json_header(self, app):
        """Should detect Accept: application/json."""
        with app.test_request_context(
            headers={"Accept": "application/json"}
        ):
            assert is_xhr_request() is True

    def test_accept_json_mixed_header(self, app):
        """Should detect JSON in mixed Accept header."""
        with app.test_request_context(
            headers={"Accept": "text/html, application/json, */*"}
        ):
            assert is_xhr_request() is True

    def test_api_path_prefix(self, app):
        """Should detect /api/ path prefix."""
        with app.test_request_context(path="/api/exercises"):
            assert is_xhr_request() is True

    def test_regular_page_request(self, app):
        """Should return False for regular page requests."""
        with app.test_request_context(
            path="/workout_plan",
            headers={"Accept": "text/html"}
        ):
            assert is_xhr_request() is False

    def test_no_request_context(self, app):
        """Should return False outside request context."""
        # Outside of request context
        with app.app_context():
            # is_xhr_request checks 'if not request' but this is tricky to test
            # In practice, outside a request context, request would be None
            pass  # Can't easily test this case


class TestAPIError:
    """Tests for APIError exception class."""

    def test_api_error_attributes(self):
        """Should store code, message, and status_code."""
        error = APIError("VALIDATION_ERROR", "Invalid input", 400)
        
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.status_code == 400

    def test_api_error_default_status_code(self):
        """Should default to 400 status code."""
        error = APIError("VALIDATION_ERROR", "Invalid input")
        assert error.status_code == 400

    def test_api_error_is_exception(self):
        """Should be raiseable as exception."""
        with pytest.raises(APIError) as exc_info:
            raise APIError("NOT_FOUND", "Resource not found", 404)
        
        assert exc_info.value.code == "NOT_FOUND"
        assert exc_info.value.status_code == 404

    def test_api_error_str_representation(self):
        """Should use message in string representation."""
        error = APIError("INTERNAL_ERROR", "Something went wrong", 500)
        assert str(error) == "Something went wrong"


class TestErrorCodes:
    """Tests for ERROR_CODES constant dictionary."""

    def test_validation_error_code(self):
        """VALIDATION_ERROR should map to 400."""
        assert ERROR_CODES["VALIDATION_ERROR"] == 400

    def test_not_found_code(self):
        """NOT_FOUND should map to 404."""
        assert ERROR_CODES["NOT_FOUND"] == 404

    def test_forbidden_code(self):
        """FORBIDDEN should map to 403."""
        assert ERROR_CODES["FORBIDDEN"] == 403

    def test_internal_error_code(self):
        """INTERNAL_ERROR should map to 500."""
        assert ERROR_CODES["INTERNAL_ERROR"] == 500

    def test_bad_request_code(self):
        """BAD_REQUEST should map to 400."""
        assert ERROR_CODES["BAD_REQUEST"] == 400

    def test_unauthorized_code(self):
        """UNAUTHORIZED should map to 401."""
        assert ERROR_CODES["UNAUTHORIZED"] == 401

    def test_unprocessable_entity_code(self):
        """UNPROCESSABLE_ENTITY should map to 422."""
        assert ERROR_CODES["UNPROCESSABLE_ENTITY"] == 422


class TestGetRequestId:
    """Tests for get_request_id function."""

    def test_get_request_id_from_g(self, app):
        """Should return request_id from Flask g object."""
        with app.test_request_context():
            g.request_id = "abc-123-def"
            assert get_request_id() == "abc-123-def"

    def test_get_request_id_not_set(self, app):
        """Should return None when request_id not set."""
        with app.test_request_context():
            # Don't set g.request_id
            assert get_request_id() is None

    def test_errors_reexports_canonical_request_id_helper(self):
        """The legacy errors import path must remain an identity-preserving re-export."""
        assert get_request_id is canonical_get_request_id


# Fixtures for errors tests
@pytest.fixture
def app():
    """Create a Flask app for testing request context."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app
