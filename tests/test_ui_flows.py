"""
UI Flow Tests - Simulating Complete User Workflows

These tests simulate real user interactions through the application API,
testing common flows that a typical user would perform.

Note: Template-rendering endpoints are skipped in the test environment
as templates are not loaded for unit tests. These should be tested manually.
"""
import pytest


class TestWorkoutPlanningFlow:
    """Test complete workout planning user flow."""
    
    def test_full_workout_plan_creation_flow(self, client, exercise_factory):
        """
        User Flow: Create a complete workout plan from scratch.
        
        Steps:
        1. Get available exercises
        2. Add multiple exercises to plan
        3. Verify plan contents
        4. Update exercise sets/reps
        5. Remove one exercise
        6. Verify final plan
        """
        # Step 1: Create exercises and get all available
        exercise_factory("Bench Press", primary_muscle_group="Chest", equipment="Barbell")
        exercise_factory("Squat", primary_muscle_group="Quadriceps", equipment="Barbell")
        exercise_factory("Deadlift", primary_muscle_group="Back", equipment="Barbell")
        
        response = client.get('/get_all_exercises')
        assert response.status_code == 200
        exercises = response.get_json()['data']
        assert len(exercises) >= 3
        
        # Step 2: Add exercises to plan
        exercises_to_add = ["Bench Press", "Squat", "Deadlift"]
        
        for i, ex in enumerate(exercises_to_add):
            response = client.post('/add_exercise', json={
                "routine": "GYM - Full Body - Workout A",
                "exercise": ex,
                "sets": 3 + i,
                "min_rep_range": 6,
                "max_rep_range": 8,
                "rir": 2,
                "weight": 50.0 + (i * 20)
            })
            assert response.status_code == 200
            assert response.get_json()['ok'] is True
        
        # Step 3: Verify plan contents
        response = client.get('/get_workout_plan')
        assert response.status_code == 200
        plan = response.get_json()['data']
        assert len(plan) == 3
        
        plan_exercises = [p['exercise'] for p in plan]
        for ex in exercises_to_add:
            assert ex in plan_exercises
        
        # Step 4: Update exercise sets/reps
        exercise_id = plan[0]['id']
        response = client.post('/update_exercise', json={
            "id": exercise_id,
            "updates": {
                "sets": 5,
                "min_rep_range": 8,
                "max_rep_range": 12
            }
        })
        assert response.status_code == 200
        
        # Verify update
        response = client.get('/get_workout_plan')
        plan = response.get_json()['data']
        updated_ex = next(p for p in plan if p['id'] == exercise_id)
        assert updated_ex['sets'] == 5
        assert updated_ex['min_rep_range'] == 8
        
        # Step 5: Remove one exercise
        exercise_to_remove = plan[1]['id']
        response = client.post('/remove_exercise', json={
            "id": exercise_to_remove
        })
        assert response.status_code == 200
        
        # Step 6: Verify final plan
        response = client.get('/get_workout_plan')
        final_plan = response.get_json()['data']
        assert len(final_plan) == 2
        assert exercise_to_remove not in [p['id'] for p in final_plan]
    
    def test_add_exercise_to_different_routines_works(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Add same exercise to different routines (allowed).
        """
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        workout_plan_factory(exercise_name="Bench Press", routine="Routine A")
        
        # Adding same exercise to different routine should work
        response = client.post('/add_exercise', json={
            "routine": "Routine B",
            "exercise": "Bench Press",
            "sets": 3,
            "min_rep_range": 6,
            "max_rep_range": 8,
            "rir": 2,
            "weight": 50.0
        })
        
        assert response.status_code == 200


class TestFilterAndSearchFlow:
    """Test filter and search user flows."""
    
    def test_filter_exercises_by_muscle_group(self, client, exercise_factory):
        """
        User Flow: Filter exercises by muscle group.
        
        Steps:
        1. Create exercises for different muscle groups
        2. Filter by Chest
        3. Verify only chest exercises returned
        """
        # Create varied exercises
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        exercise_factory("Incline Press", primary_muscle_group="Chest")
        exercise_factory("Lat Pulldown", primary_muscle_group="Back")
        exercise_factory("Barbell Row", primary_muscle_group="Back")
        exercise_factory("Squat", primary_muscle_group="Quadriceps")
        
        # Filter by Chest
        response = client.post('/filter_exercises', json={
            "Primary Muscle Group": "Chest"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        # Filter returns exercise names as strings in the data list
        chest_exercises = data['data']
        assert len(chest_exercises) == 2
    
    def test_multi_filter_flow(self, client, exercise_factory):
        """
        User Flow: Apply multiple filters simultaneously.
        """
        exercise_factory("Barbell Bench", primary_muscle_group="Chest", equipment="Barbell")
        exercise_factory("Dumbbell Bench", primary_muscle_group="Chest", equipment="Dumbbell")
        exercise_factory("Machine Press", primary_muscle_group="Chest", equipment="Machine")
        exercise_factory("Barbell Row", primary_muscle_group="Back", equipment="Barbell")
        
        # Filter by Chest AND Barbell
        response = client.post('/filter_exercises', json={
            "Primary Muscle Group": "Chest",
            "Equipment": "Barbell"
        })
        assert response.status_code == 200
        filtered = response.get_json()['data']
        assert len(filtered) == 1
        # The API returns exercise names as strings
        assert "Barbell Bench" in filtered


class TestSupersetWorkflow:
    """Test superset creation and management flows."""
    
    def test_create_and_use_superset_flow(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Create a superset, verify, then unlink.
        """
        # Setup exercises
        exercise_factory("Bicep Curl", primary_muscle_group="Biceps")
        exercise_factory("Tricep Extension", primary_muscle_group="Triceps")
        
        id1 = workout_plan_factory(exercise_name="Bicep Curl", routine="ArmDay")
        id2 = workout_plan_factory(exercise_name="Tricep Extension", routine="ArmDay")
        
        # Link as superset
        response = client.post('/api/superset/link', json={
            'exercise_ids': [id1, id2]
        })
        assert response.status_code == 200
        link_data = response.get_json()['data']
        assert 'superset_group' in link_data
        superset_group = link_data['superset_group']
        
        # Verify in workout plan
        response = client.get('/get_workout_plan')
        plan = response.get_json()['data']
        linked_exercises = [p for p in plan if p.get('superset_group') == superset_group]
        assert len(linked_exercises) == 2
        
        # Unlink superset
        response = client.post('/api/superset/unlink', json={
            'exercise_id': id1
        })
        assert response.status_code == 200
        
        # Verify unlinked
        response = client.get('/get_workout_plan')
        plan = response.get_json()['data']
        for p in plan:
            assert p.get('superset_group') is None


class TestWorkoutLogFlow:
    """Test workout logging user flows."""
    
    def test_export_to_workout_log_and_query(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Export plan to workout log and query logs.
        """
        # Create plan
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        exercise_factory("Squat", primary_muscle_group="Quadriceps")
        
        workout_plan_factory(exercise_name="Bench Press", routine="A", sets=3, weight=60.0)
        workout_plan_factory(exercise_name="Squat", routine="A", sets=4, weight=100.0)
        
        # Export to workout log
        response = client.post('/export_to_workout_log')
        assert response.status_code == 200
        
        # Get workout logs via API
        response = client.get('/get_workout_logs')
        assert response.status_code == 200
        logs = response.get_json()['data']
        assert len(logs) >= 2


class TestBackupAndRestoreFlow:
    """Test backup and restore user flows."""
    
    def test_full_backup_restore_flow(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Create backup, modify data, restore backup.
        """
        # Setup initial data
        exercise_factory("Original Exercise 1", primary_muscle_group="Chest")
        exercise_factory("Original Exercise 2", primary_muscle_group="Back")
        exercise_factory("New Exercise", primary_muscle_group="Arms")
        
        workout_plan_factory(exercise_name="Original Exercise 1", routine="A")
        workout_plan_factory(exercise_name="Original Exercise 2", routine="A")
        
        # Get initial state
        response = client.get('/get_workout_plan')
        initial_plan = response.get_json()['data']
        initial_count = len(initial_plan)
        assert initial_count == 2
        
        # Create backup
        response = client.post('/api/backups', json={
            "name": "Before Adding New Exercise"
        })
        assert response.status_code in [200, 201]
        backup_data = response.get_json()['data']
        backup_id = backup_data['id']
        
        # Modify data - add new exercise
        response = client.post('/add_exercise', json={
            "routine": "A",
            "exercise": "New Exercise",
            "sets": 3,
            "min_rep_range": 10,
            "max_rep_range": 12,
            "rir": 2,
            "weight": 30.0
        })
        assert response.status_code == 200
        
        # Verify new exercise exists
        response = client.get('/get_workout_plan')
        modified_plan = response.get_json()['data']
        assert len(modified_plan) == 3
        
        # Restore from backup
        response = client.post(f'/api/backups/{backup_id}/restore')
        assert response.status_code == 200
        
        # Verify data is restored
        response = client.get('/get_workout_plan')
        restored_plan = response.get_json()['data']
        assert len(restored_plan) == initial_count


class TestReplaceExerciseFlow:
    """Test exercise replacement user flows."""
    
    def test_replace_exercise_api_call(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Call replace exercise API.
        """
        # Create exercises (need alternatives in same muscle group)
        exercise_factory("Barbell Bench Press", primary_muscle_group="Chest", equipment="Barbell")
        exercise_factory("Dumbbell Bench Press", primary_muscle_group="Chest", equipment="Dumbbell")
        exercise_factory("Machine Chest Press", primary_muscle_group="Chest", equipment="Machine")
        
        plan_id = workout_plan_factory(
            exercise_name="Barbell Bench Press", 
            routine="A",
            sets=3
        )
        
        # Request replacement
        response = client.post('/replace_exercise', json={
            "id": plan_id,
            "muscle": "Chest"
        })
        
        # API may return 200 (success) or 400 (no alternatives found)
        assert response.status_code in [200, 400]


class TestExportFlow:
    """Test data export user flows."""
    
    def test_export_to_excel_flow(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Export workout plan to Excel.
        """
        # Create plan
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        exercise_factory("Squat", primary_muscle_group="Quadriceps")
        
        workout_plan_factory(exercise_name="Bench Press", routine="A")
        workout_plan_factory(exercise_name="Squat", routine="A")
        
        # Export to Excel
        response = client.get('/export_to_excel')
        assert response.status_code == 200
        assert response.content_type in [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ]


class TestClearAndResetFlow:
    """Test data clearing user flows."""
    
    def test_clear_workout_plan_flow(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Clear all exercises from workout plan.
        """
        # Create plan
        exercise_factory("Ex1", primary_muscle_group="Chest")
        exercise_factory("Ex2", primary_muscle_group="Back")
        
        workout_plan_factory(exercise_name="Ex1", routine="A")
        workout_plan_factory(exercise_name="Ex2", routine="A")
        
        # Verify plan has exercises
        response = client.get('/get_workout_plan')
        assert len(response.get_json()['data']) == 2
        
        # Clear plan
        response = client.post('/clear_workout_plan')
        assert response.status_code == 200
        
        # Verify plan is empty
        response = client.get('/get_workout_plan')
        assert len(response.get_json()['data']) == 0


class TestErrorRecoveryFlow:
    """Test error recovery in user flows."""
    
    def test_remove_nonexistent_exercise(self, client):
        """Try to remove non-existent exercise returns 404."""
        response = client.post('/remove_exercise', json={
            "id": 99999
        })
        assert response.status_code == 404
    
    def test_update_nonexistent_exercise(self, client):
        """Try to update non-existent exercise returns success (no-op for SQLite UPDATE)."""
        response = client.post('/update_exercise', json={
            "id": 99999,
            "updates": {"sets": 5}
        })
        # SQLite UPDATE on non-existent row succeeds as a no-op
        assert response.status_code == 200
    
    def test_add_exercise_missing_data(self, client):
        """Try to add exercise with missing data returns 400."""
        response = client.post('/add_exercise', json={
            "routine": "A"
            # Missing required fields
        })
        assert response.status_code == 400
    
    def test_invalid_json_handling(self, client):
        """App handles malformed JSON gracefully."""
        response = client.post('/add_exercise', 
                               data="this is not json",
                               content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
    
    def test_app_usable_after_errors(self, client, exercise_factory):
        """Verify app still works after error conditions."""
        # Trigger some errors first
        client.post('/remove_exercise', json={"id": 99999})
        client.post('/add_exercise', json={"routine": "A"})
        
        # Verify app still works
        exercise_factory("Test Exercise", primary_muscle_group="Chest")
        response = client.post('/add_exercise', json={
            "routine": "A",
            "exercise": "Test Exercise",
            "sets": 3,
            "min_rep_range": 6,
            "max_rep_range": 8,
            "rir": 2,
            "weight": 50.0
        })
        assert response.status_code == 200


class TestMultiRoutineFlow:
    """Test multi-routine management flows."""
    
    def test_manage_exercises_across_routines(self, client, exercise_factory, workout_plan_factory):
        """
        User Flow: Manage exercises across multiple routines.
        """
        # Create exercises
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        exercise_factory("Squat", primary_muscle_group="Quadriceps")
        exercise_factory("Overhead Press", primary_muscle_group="Shoulders")
        
        # Add to different routines
        id_a = workout_plan_factory(exercise_name="Bench Press", routine="Routine A")
        id_b = workout_plan_factory(exercise_name="Squat", routine="Routine B")
        id_c = workout_plan_factory(exercise_name="Overhead Press", routine="Routine C")
        
        # Get full plan
        response = client.get('/get_workout_plan')
        plan = response.get_json()['data']
        
        # Verify all routines present
        routines = set(p['routine'] for p in plan)
        assert "Routine A" in routines
        assert "Routine B" in routines
        assert "Routine C" in routines
        
        # Update one exercise
        response = client.post('/update_exercise', json={
            "id": id_a,
            "updates": {
                "sets": 5,
                "min_rep_range": 6,
                "max_rep_range": 8
            }
        })
        assert response.status_code == 200
        
        # Verify others unchanged
        response = client.get('/get_workout_plan')
        plan = response.get_json()['data']
        ex_b = next(p for p in plan if p['id'] == id_b)
        assert ex_b['sets'] == 3  # Original value


class TestVolumeCalculationFlow:
    """Test volume calculation API flows."""
    
    def test_calculate_volume_api(self, client):
        """Test volume calculation API endpoint."""
        response = client.post('/api/calculate_volume', json={
            "mode": "basic",
            "training_days": 2,
            "volumes": {
                "Chest": 20
            },
            "ranges": {
                "Chest": {
                    "min": 12,
                    "max": 18
                }
            }
        })
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["ok"] is True
        assert payload["status"] == "success"
        assert set(payload["data"].keys()) == {"results", "suggestions", "ranges"}
        assert payload["data"]["results"]["Chest"]["weekly_sets"] == 20.0
        assert payload["data"]["results"]["Chest"]["sets_per_session"] == 10.0
        assert payload["data"]["results"]["Chest"]["status"] == "high"
        assert payload["data"]["ranges"]["Chest"]["min"] == 12
        assert payload["data"]["ranges"]["Chest"]["max"] == 18
        assert isinstance(payload["data"]["suggestions"], list)
