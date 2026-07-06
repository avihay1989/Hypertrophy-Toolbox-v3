"""
Tests for the Replace/Swap Exercise feature.
Tests the POST /replace_exercise endpoint functionality.
"""
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "imports",
    [
        "import routes.workout_plan; import utils.exercise_replacement",
        "import utils.exercise_replacement; import routes.workout_plan",
    ],
)
def test_replacement_modules_import_in_either_order(imports):
    """The extracted service and compatibility route have no import cycle."""
    completed = subprocess.run(
        [sys.executable, "-c", imports],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_route_helper_imports_remain_compatible():
    """The pre-extraction route helper paths remain valid aliases."""
    from routes import workout_plan
    from utils import exercise_replacement

    assert (
        workout_plan.suggest_replacement_exercise
        is exercise_replacement.suggest_replacement_exercise
    )
    assert (
        workout_plan._fetch_current_exercise_details
        is exercise_replacement._fetch_current_exercise_details
    )
    assert (
        workout_plan._build_replacement_candidates
        is exercise_replacement._build_replacement_candidates
    )
    assert (
        workout_plan._perform_exercise_swap
        is exercise_replacement._perform_exercise_swap
    )


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

    def test_replace_exercise_missing_metadata(
        self, client, exercise_factory, workout_plan_factory
    ):
        """Missing catalog metadata keeps its exact validation contract."""
        exercise = exercise_factory(
            "Incomplete Exercise",
            primary_muscle_group=None,
            equipment="Barbell",
        )
        plan_id = workout_plan_factory(
            exercise_name=exercise, routine="Test Routine"
        )

        response = client.post('/replace_exercise', json={"id": plan_id})

        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert data['error']['reason'] == 'missing_metadata'
        assert data['error']['message'] == (
            "Exercise is missing muscle group or equipment metadata"
        )

    def test_replace_exercise_selection_failed_stays_http_200(
        self,
        client,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """Selection failure is a processable user outcome, not an HTTP error."""
        from utils import exercise_replacement

        current = exercise_factory(
            "Current Press", primary_muscle_group="Chest", equipment="Barbell"
        )
        exercise_factory(
            "Alternative Press",
            primary_muscle_group="Chest",
            equipment="Barbell",
        )
        plan_id = workout_plan_factory(exercise_name=current, routine="Press Day")
        monkeypatch.setattr(
            exercise_replacement,
            "suggest_replacement_exercise",
            lambda *args, **kwargs: None,
        )

        response = client.post('/replace_exercise', json={"id": plan_id})

        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'SELECTION_FAILED'
        assert data['error']['reason'] == 'selection_failed'
        assert data['error']['message'] == "Failed to select replacement exercise"

    def test_replace_exercise_duplicate_stays_http_200(
        self,
        client,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """The defensive post-selection duplicate outcome remains HTTP 200."""
        from utils import exercise_replacement

        current = exercise_factory(
            "Current Row", primary_muscle_group="Chest", equipment="Barbell"
        )
        duplicate = exercise_factory(
            "Existing Row", primary_muscle_group="Chest", equipment="Barbell"
        )
        routine = "Duplicate Routine"
        plan_id = workout_plan_factory(exercise_name=current, routine=routine)
        workout_plan_factory(exercise_name=duplicate, routine=routine)
        monkeypatch.setattr(
            exercise_replacement,
            "_build_replacement_candidates",
            lambda *args, **kwargs: [duplicate],
        )
        monkeypatch.setattr(
            exercise_replacement,
            "suggest_replacement_exercise",
            lambda *args, **kwargs: duplicate,
        )

        response = client.post('/replace_exercise', json={"id": plan_id})

        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'DUPLICATE'
        assert data['error']['reason'] == 'duplicate'
        assert data['error']['message'] == (
            "All candidate exercises are already in this routine"
        )
    
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
    
    def test_replace_exercise_preserves_exercise_order_zero(self, client, exercise_factory, workout_plan_factory):
        """exercise_order=0 (the first position) must survive a replace/swap, not be dropped as missing."""
        from utils.database import DatabaseHandler

        exercise1 = exercise_factory(
            "Deadlift",
            primary_muscle_group="Back",
            equipment="Barbell"
        )
        exercise_factory(
            "Romanian Deadlift",
            primary_muscle_group="Back",
            equipment="Barbell"
        )

        plan_id = workout_plan_factory(exercise_name=exercise1, routine="Pull Day")

        with DatabaseHandler() as db:
            db.execute_query(
                "UPDATE user_selection SET exercise_order = 0 WHERE id = ?",
                (plan_id,)
            )

        response = client.post('/replace_exercise', json={
            "id": plan_id
        })

        assert response.status_code == 200
        data = response.get_json()

        assert data['ok'] is True
        updated_row = data['data']['updated_row']
        assert updated_row['exercise_order'] == 0

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
