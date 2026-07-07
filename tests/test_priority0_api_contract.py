"""
Priority 0 Tests: Standardized API Error/Success Response Format
"""
import pytest


class TestSuccessResponseFormat:
    """Test standardized success response format."""
    
    def test_get_workout_plan_success_format(self, client, exercise_factory, workout_plan_factory):
        """Test that get_workout_plan returns standardized success format."""
        exercise_name = exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name=exercise_name)
        
        response = client.get('/get_workout_plan')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Standardized format: {"ok": true, "data": [...]}
        assert data['ok'] is True
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert len(data['data']) > 0
    
    def test_get_all_exercises_success_format(self, client, exercise_factory):
        """Test that get_all_exercises returns standardized success format."""
        exercise_factory("Test Exercise 1")
        exercise_factory("Test Exercise 2")
        
        response = client.get('/get_all_exercises')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Standardized format: {"ok": true, "data": [...]}
        assert data['ok'] is True
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert "Test Exercise 1" in data['data']
        assert "Test Exercise 2" in data['data']
    
    def test_add_exercise_success_format(self, client, exercise_factory):
        """Test that add_exercise returns standardized success format."""
        exercise_factory("Bench Press")
        
        response = client.post('/add_exercise', json={
            "routine": "GYM - Full Body - Workout A",
            "exercise": "Bench Press",
            "sets": 3,
            "min_rep_range": 6,
            "max_rep_range": 8,
            "rir": 3,
            "weight": 50.0,
            "rpe": 7.0
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Standardized format: {"ok": true, "message": "..."}
        assert data['ok'] is True
        assert 'message' in data
        assert 'Exercise added successfully' in data['message']
    
    def test_filter_exercises_success_format(self, client, exercise_factory):
        """Test that filter_exercises returns standardized success format."""
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        
        response = client.post('/filter_exercises', json={
            "Primary Muscle Group": "Chest"
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Standardized format: {"ok": true, "data": [...]}
        assert data['ok'] is True
        assert 'data' in data
        assert isinstance(data['data'], list)


class TestErrorResponseFormat:
    """Test standardized error response format."""
    
    def test_validation_error_format(self, client):
        """Test that validation errors return standardized format."""
        response = client.post('/filter_exercises', json={
            "Invalid Column': DROP TABLE exercises; --": "value"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        
        # Standardized format: {"ok": false, "error": {"code": "...", "message": "..."}}
        assert data['ok'] is False
        assert 'error' in data
        assert 'code' in data['error']
        assert 'message' in data['error']
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert isinstance(data['error']['message'], str)
        assert len(data['error']['message']) > 0
    
    def test_not_found_error_format(self, client):
        """Test that not found errors return standardized format."""
        response = client.get('/get_exercise_info/NonExistentExercise')
        
        assert response.status_code == 404
        data = response.get_json()
        
        # Standardized format: {"ok": false, "error": {"code": "NOT_FOUND", "message": "..."}}
        assert data['ok'] is False
        assert 'error' in data
        assert data['error']['code'] == 'NOT_FOUND'
        assert 'message' in data['error']
    
    def test_internal_error_format(self, client):
        """Test that internal errors return standardized format."""
        # Try to add exercise with invalid data to trigger error
        response = client.post('/add_exercise', json={
            "routine": None,  # Invalid data
            "exercise": None,
            "sets": "invalid",
            "min_rep_range": "invalid",
            "max_rep_range": "invalid",
            "weight": "invalid"
        })
        
        # Should return 400 or 500
        assert response.status_code in [400, 500]
        data = response.get_json()
        
        # Standardized format
        assert data['ok'] is False
        assert 'error' in data
        assert 'code' in data['error']
        assert 'message' in data['error']
    
    def test_error_status_codes_match_error_type(self, client):
        """Test that HTTP status codes match error types."""
        # Validation error → 400
        response = client.post('/filter_exercises', json={"Invalid": "value"})
        assert response.status_code == 400
        
        # Not found → 404
        response = client.get('/get_exercise_info/NonExistentExercise')
        assert response.status_code == 404


class TestAllEndpointsStandardized:
    """Test that all Priority 0 endpoints use standardized format."""
    
    @pytest.mark.parametrize("endpoint,method,payload", [
        ('/get_workout_plan', 'GET', None),
        ('/get_all_exercises', 'GET', None),
        ('/filter_exercises', 'POST', {"Primary Muscle Group": "Chest"}),
    ])
    def test_endpoints_return_standardized_format(self, client, endpoint, method, payload, exercise_factory):
        """Test that all Priority 0 endpoints return standardized format."""
        # Setup test data
        exercise_factory("Test Exercise", equipment="Barbell", primary_muscle_group="Chest")
        
        if method == 'GET':
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json=payload)
        
        assert response.status_code in [200, 400, 404, 500]
        data = response.get_json()
        
        # Must have 'ok' field
        assert 'ok' in data
        
        if data['ok'] is True:
            # Success: must have 'data' or 'message'
            assert 'data' in data or 'message' in data
        else:
            # Error: must have 'error' with 'code' and 'message'
            assert 'error' in data
            assert 'code' in data['error']
            assert 'message' in data['error']

