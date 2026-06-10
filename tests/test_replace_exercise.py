"""
Tests for the Replace/Swap Exercise feature.
Tests the POST /replace_exercise endpoint functionality.
"""


class TestReplaceExerciseEndpoint:
    """Test the /replace_exercise endpoint."""
    
    def test_replace_exercise_success(self, client, exercise_factory, workout_plan_factory):
        """Test successful exercise replacement."""
        # Create two exercises with same muscle and equipment
        exercise1 = exercise_factory(
            "Bench Press",
            primary_muscle_group="Chest",
            equipment="Barbell"
        )
        exercise2 = exercise_factory(
            "Barbell Floor Press",
            primary_muscle_group="Chest",
            equipment="Barbell"
        )
        
        # Create a workout plan entry with exercise1
        plan_id = workout_plan_factory(exercise_name=exercise1, routine="Test Routine A")
        
        # Replace the exercise
        response = client.post('/replace_exercise', json={
            "id": plan_id
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['ok'] is True
        assert 'data' in data
        assert 'updated_row' in data['data']
        assert data['data']['old_exercise'] == "Bench Press"
        assert data['data']['new_exercise'] == "Barbell Floor Press"
        assert data['data']['updated_row']['exercise'] == "Barbell Floor Press"
    
    def test_replace_exercise_no_candidates(self, client, exercise_factory, workout_plan_factory):
        """Test replacement when no valid candidates exist."""
        # Create a unique exercise (no others with same muscle/equipment)
        exercise = exercise_factory(
            "Unique Exercise",
            primary_muscle_group="UniqueMuscleThatDoesNotExist",
            equipment="UniqueEquipmentThatDoesNotExist"
        )
        
        plan_id = workout_plan_factory(exercise_name=exercise, routine="Test Routine")
        
        response = client.post('/replace_exercise', json={
            "id": plan_id
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['ok'] is False
        assert 'error' in data
        assert data['error']['reason'] == 'no_candidates'
    
    def test_replace_exercise_avoids_duplicates(self, client, exercise_factory, workout_plan_factory):
        """Test that replacement avoids exercises already in routine."""
        # Create three exercises with same muscle and equipment
        exercise1 = exercise_factory(
            "Chest Exercise 1",
            primary_muscle_group="Chest",
            equipment="Dumbbells"
        )
        exercise2 = exercise_factory(
            "Chest Exercise 2",
            primary_muscle_group="Chest",
            equipment="Dumbbells"
        )
        exercise3 = exercise_factory(
            "Chest Exercise 3",
            primary_muscle_group="Chest",
            equipment="Dumbbells"
        )
        
        routine = "Test Routine B"
        
        # Add exercise1 and exercise2 to the same routine
        plan_id_1 = workout_plan_factory(exercise_name=exercise1, routine=routine)
        plan_id_2 = workout_plan_factory(exercise_name=exercise2, routine=routine)
        
        # Replace exercise1 - should get exercise3 (not exercise2 since it's already in routine)
        response = client.post('/replace_exercise', json={
            "id": plan_id_1
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['ok'] is True
        assert data['data']['new_exercise'] == "Chest Exercise 3"
    
    def test_replace_exercise_not_found(self, client):
        """Test replacement with non-existent exercise ID."""
        response = client.post('/replace_exercise', json={
            "id": 99999
        })
        
        assert response.status_code == 404
        data = response.get_json()
        
        assert data['ok'] is False
        assert data['error']['reason'] == 'not_found'
    
    def test_replace_exercise_invalid_id(self, client):
        """Test replacement with invalid exercise ID."""
        response = client.post('/replace_exercise', json={
            "id": "not-a-number"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
    
    def test_replace_exercise_missing_id(self, client):
        """Test replacement with missing exercise ID."""
        response = client.post('/replace_exercise', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
    
    def test_replace_exercise_preserves_sets_reps_weight(self, client, exercise_factory, workout_plan_factory):
        """Test that replacement preserves sets, reps, RIR, RPE, and weight."""
        exercise1 = exercise_factory(
            "Squat",
            primary_muscle_group="Quadriceps",
            equipment="Barbell"
        )
        exercise2 = exercise_factory(
            "Front Squat",
            primary_muscle_group="Quadriceps",
            equipment="Barbell"
        )
        
        # Create plan with specific values
        plan_id = workout_plan_factory(
            exercise_name=exercise1,
            routine="Leg Day",
            sets=5,
            min_rep_range=3,
            max_rep_range=5,
            rir=2,
            rpe=8.5,
            weight=100.0
        )
        
        response = client.post('/replace_exercise', json={
            "id": plan_id
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['ok'] is True
        updated_row = data['data']['updated_row']
        
        # All values should be preserved
        assert updated_row['sets'] == 5
        assert updated_row['min_rep_range'] == 3
        assert updated_row['max_rep_range'] == 5
        assert updated_row['rir'] == 2
        assert updated_row['rpe'] == 8.5
        assert updated_row['weight'] == 100.0
        
        # Only exercise name should change
        assert updated_row['exercise'] == "Front Squat"
        assert updated_row['routine'] == "Leg Day"
    
    def test_replace_exercise_ai_strategy(self, client, exercise_factory, workout_plan_factory):
        """Test replacement with AI strategy specified."""
        exercise1 = exercise_factory(
            "Pull Up",
            primary_muscle_group="Latissimus-Dorsi",
            equipment="Bodyweight"
        )
        exercise2 = exercise_factory(
            "Chin Up",
            primary_muscle_group="Latissimus-Dorsi",
            equipment="Bodyweight"
        )
        
        plan_id = workout_plan_factory(exercise_name=exercise1, routine="Pull Day")
        
        response = client.post('/replace_exercise', json={
            "id": plan_id,
            "strategy": "ai"
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['ok'] is True
        assert data['data']['new_exercise'] == "Chin Up"
    
    def test_replace_exercise_case_insensitive_matching(self, client, exercise_factory, workout_plan_factory):
        """Test that muscle and equipment matching is case-insensitive."""
        # Create exercises with different case
        exercise1 = exercise_factory(
            "Cable Fly",
            primary_muscle_group="CHEST",  # Upper case
            equipment="CABLES"
        )
        exercise2 = exercise_factory(
            "Cable Crossover",
            primary_muscle_group="chest",  # Lower case
            equipment="cables"
        )
        
        plan_id = workout_plan_factory(exercise_name=exercise1, routine="Upper Body")
        
        response = client.post('/replace_exercise', json={
            "id": plan_id
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should find the match despite case differences
        assert data['ok'] is True
        assert data['data']['new_exercise'] == "Cable Crossover"


class TestReplaceExerciseResponseFormat:
    """Test the response format matches get_workout_plan format."""
    
    def test_response_contains_all_metadata(self, client, exercise_factory, workout_plan_factory):
        """Test that updated_row contains full exercise metadata."""
        exercise1 = exercise_factory(
            "Romanian Deadlift",
            primary_muscle_group="Hamstrings",
            secondary_muscle_group="Glutes",
            tertiary_muscle_group="Lower Back",
            equipment="Barbell",
            utility="Auxiliary"
        )
        exercise2 = exercise_factory(
            "Stiff Leg Deadlift",
            primary_muscle_group="Hamstrings",
            secondary_muscle_group="Glutes",
            tertiary_muscle_group="Lower Back",
            equipment="Barbell",
            utility="Auxiliary"
        )
        
        plan_id = workout_plan_factory(exercise_name=exercise1, routine="Posterior Chain")
        
        response = client.post('/replace_exercise', json={
            "id": plan_id
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        updated_row = data['data']['updated_row']
        
        # Should have all the metadata fields
        expected_fields = [
            'id', 'routine', 'exercise', 'sets', 'min_rep_range', 'max_rep_range',
            'rir', 'rpe', 'weight', 'primary_muscle_group', 'secondary_muscle_group',
            'tertiary_muscle_group', 'utility'
        ]
        
        for field in expected_fields:
            assert field in updated_row, f"Missing field: {field}"
