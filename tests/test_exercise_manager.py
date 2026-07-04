"""
Tests for utils/exercise_manager.py

Tests the ExerciseManager class which handles:
- Exercise CRUD operations
- User selection management
- Exercise catalogue maintenance
- Duplicate prevention
"""
import pytest
import os

# Set testing environment before imports
os.environ['TESTING'] = '1'

from utils.exercise_manager import (
    ExerciseManager,
    get_exercises,
    add_exercise,
    delete_exercise,
    fetch_unique_values,
    save_exercise,
    remove_exercise_by_name,
)


class TestGetExercises:
    """Tests for ExerciseManager.get_exercises()."""
    
    def test_get_exercises_without_filters(self, app, exercise_factory):
        """Should return all exercise names when no filters provided."""
        with app.app_context():
            exercise_factory("Bench Press", primary_muscle_group="Chest")
            exercise_factory("Squat", primary_muscle_group="Quadriceps")
            exercise_factory("Deadlift", primary_muscle_group="Back")
            
            result = ExerciseManager.get_exercises()
            
            # Returns list of exercise names (strings)
            assert len(result) >= 3
            assert "Bench Press" in result
            assert "Squat" in result
            assert "Deadlift" in result
    
    def test_get_exercises_with_filter(self, app, exercise_factory):
        """Should return filtered exercise names when filter provided."""
        with app.app_context():
            exercise_factory("Bench Press", primary_muscle_group="Chest")
            exercise_factory("Incline Press", primary_muscle_group="Chest")
            exercise_factory("Squat", primary_muscle_group="Quadriceps")
            
            result = ExerciseManager.get_exercises({"primary_muscle_group": "Chest"})
            
            # Returns list of exercise names
            assert len(result) == 2
            assert "Bench Press" in result
            assert "Incline Press" in result
            assert "Squat" not in result
    
    def test_get_exercises_empty_database(self, app, clean_db):
        """Should return empty list when no exercises exist."""
        with app.app_context():
            result = ExerciseManager.get_exercises()
            assert result == []
    
    def test_get_exercises_with_none_filters(self, app, exercise_factory):
        """Should handle None filters gracefully."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result = ExerciseManager.get_exercises(None)
            
            assert len(result) >= 1


class TestAddExercise:
    """Tests for ExerciseManager.add_exercise()."""
    
    def test_add_exercise_success(self, app, exercise_factory, clean_db):
        """Should successfully add exercise to user_selection."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0,
                rpe=8.0
            )
            
            assert result == "Exercise added successfully."
    
    def test_add_exercise_prevents_duplicates(self, app, exercise_factory, clean_db):
        """Should prevent duplicate routine/exercise combinations."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            # Add first time
            result1 = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0
            )
            assert result1 == "Exercise added successfully."
            
            # Try to add duplicate
            result2 = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=4,  # Different sets
                min_rep_range=8,
                max_rep_range=10,
                rir=3,
                weight=110.0
            )
            assert result2 == "Exercise already exists in this routine."
    
    def test_add_exercise_allows_same_exercise_different_routine(self, app, exercise_factory, clean_db):
        """Should allow same exercise in different routines."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result1 = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0
            )
            
            result2 = ExerciseManager.add_exercise(
                routine="Workout B",
                exercise="Bench Press",
                sets=4,
                min_rep_range=8,
                max_rep_range=10,
                rir=3,
                weight=110.0
            )
            
            assert result1 == "Exercise added successfully."
            assert result2 == "Exercise added successfully."
    
    def test_add_exercise_missing_routine(self, app, exercise_factory):
        """Should return error when routine is missing."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result = ExerciseManager.add_exercise(
                routine="",  # Missing
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0
            )
            
            assert "Error" in result
            assert "Missing required fields" in result
    
    def test_add_exercise_missing_exercise_name(self, app):
        """Should return error when exercise name is missing."""
        with app.app_context():
            result = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="",  # Missing
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0
            )
            
            assert "Error" in result
            assert "Missing required fields" in result
    
    def test_add_exercise_missing_sets(self, app, exercise_factory):
        """Should return error when sets is missing/zero."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=0,  # Missing/zero
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0
            )
            
            assert "Error" in result
    
    def test_add_exercise_accepts_zero_weight(self, app, exercise_factory, clean_db):
        """weight=0 is valid for bodyweight/assisted exercises and must be accepted."""
        with app.app_context():
            exercise_factory("Pull Up")

            result = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Pull Up",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=0
            )

            assert result == "Exercise added successfully."

    def test_add_exercise_missing_weight(self, app, exercise_factory):
        """Should return error when weight is None (missing/absent)."""
        with app.app_context():
            exercise_factory("Bench Press")

            result = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=None  # Missing/absent
            )

            assert "Error" in result
    
    def test_add_exercise_optional_rir(self, app, exercise_factory, clean_db):
        """Should allow None for optional RIR field."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=None,  # Optional
                weight=100.0
            )
            
            assert result == "Exercise added successfully."
    
    def test_add_exercise_optional_rpe(self, app, exercise_factory, clean_db):
        """Should allow None for optional RPE field."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result = ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0,
                rpe=None  # Optional
            )
            
            assert result == "Exercise added successfully."
    
    def test_add_exercise_increments_order(self, app, exercise_factory, clean_db):
        """Should assign incrementing exercise_order values."""
        with app.app_context():
            exercise_factory("Bench Press")
            exercise_factory("Squat")
            
            ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0
            )
            
            ExerciseManager.add_exercise(
                routine="Workout A",
                exercise="Squat",
                sets=4,
                min_rep_range=8,
                max_rep_range=10,
                rir=3,
                weight=120.0
            )
            
            # Verify order by querying the database
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                rows = db.fetch_all(
                    "SELECT exercise, exercise_order FROM user_selection ORDER BY exercise_order"
                )
            
            assert len(rows) == 2
            assert rows[0]['exercise_order'] < rows[1]['exercise_order']


class TestDeleteExercise:
    """Tests for ExerciseManager.delete_exercise()."""
    
    def test_delete_exercise_success(self, app, exercise_factory, workout_plan_factory):
        """Should successfully delete exercise from user_selection."""
        with app.app_context():
            exercise_name = exercise_factory("Bench Press")
            plan_id = workout_plan_factory(exercise_name=exercise_name)
            
            # Verify it exists
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                before = db.fetch_one("SELECT COUNT(*) as cnt FROM user_selection WHERE id = ?", (plan_id,))
            assert before['cnt'] == 1
            
            # Delete
            ExerciseManager.delete_exercise(plan_id)
            
            # Verify deleted
            with DatabaseHandler() as db:
                after = db.fetch_one("SELECT COUNT(*) as cnt FROM user_selection WHERE id = ?", (plan_id,))
            assert after['cnt'] == 0
    
    def test_delete_nonexistent_exercise(self, app, clean_db):
        """Should handle deletion of non-existent ID gracefully."""
        with app.app_context():
            # Should not raise an error
            ExerciseManager.delete_exercise(99999)
            # No assertion needed - just verifying no exception


class TestSaveExercise:
    """Tests for ExerciseManager.save_exercise()."""
    
    def test_save_exercise_insert_new(self, app, clean_db):
        """Should insert a new exercise."""
        with app.app_context():
            # Must provide all columns for the SQL binding
            exercise_data = {
                'exercise_name': 'New Exercise',
                'primary_muscle_group': 'Chest',
                'secondary_muscle_group': 'Triceps',
                'tertiary_muscle_group': None,
                'advanced_isolated_muscles': None,
                'utility': 'Basic',
                'grips': None,
                'stabilizers': None,
                'synergists': None,
                'force': 'Push',
                'equipment': 'Barbell',
                'mechanic': 'Compound',
                'difficulty': 'Intermediate',
            }
            
            result = ExerciseManager.save_exercise(exercise_data)
            
            assert result['exercise_name'] == 'New Exercise'
            
            # Verify in database
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                row = db.fetch_one("SELECT * FROM exercises WHERE exercise_name = ?", ('New Exercise',))
            
            assert row is not None
            assert row['primary_muscle_group'] == 'Chest'
    
    def test_save_exercise_update_existing(self, app, exercise_factory):
        """Should update an existing exercise."""
        with app.app_context():
            exercise_factory("Bench Press", primary_muscle_group="Chest")
            
            # Update with new data - must provide all columns
            updated_data = {
                'exercise_name': 'Bench Press',
                'primary_muscle_group': 'Chest',
                'secondary_muscle_group': 'Shoulders',  # Changed
                'tertiary_muscle_group': None,
                'advanced_isolated_muscles': None,
                'utility': 'Basic',
                'grips': None,
                'stabilizers': None,
                'synergists': None,
                'force': 'Push',
                'equipment': 'Dumbbell',  # Changed - will be normalized to 'Dumbbells'
                'mechanic': 'Compound',
                'difficulty': 'Intermediate',
            }
            
            result = ExerciseManager.save_exercise(updated_data)
            
            assert result['exercise_name'] == 'Bench Press'
            
            # Verify update
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                row = db.fetch_one("SELECT * FROM exercises WHERE exercise_name = ?", ('Bench Press',))
            
            # Equipment gets normalized to 'Dumbbells' (plural) by normalize_exercise_row
            assert row['equipment'] == 'Dumbbells'
    
    def test_save_exercise_missing_name_raises_error(self, app):
        """Should raise ValueError when exercise_name is missing."""
        with app.app_context():
            exercise_data = {
                'primary_muscle_group': 'Chest',
            }
            
            with pytest.raises(ValueError) as exc_info:
                ExerciseManager.save_exercise(exercise_data)
            
            assert "exercise_name is required" in str(exc_info.value)
    
    def test_save_exercise_empty_name_raises_error(self, app):
        """Should raise ValueError when exercise_name is empty."""
        with app.app_context():
            exercise_data = {
                'exercise_name': '',
                'primary_muscle_group': 'Chest',
            }
            
            with pytest.raises(ValueError) as exc_info:
                ExerciseManager.save_exercise(exercise_data)
            
            assert "exercise_name is required" in str(exc_info.value)
    
    def test_save_exercise_syncs_isolated_muscles(self, app, clean_db):
        """Should sync isolated muscles to mapping table."""
        with app.app_context():
            exercise_data = {
                'exercise_name': 'Cable Fly',
                'primary_muscle_group': 'Chest',
                'secondary_muscle_group': None,
                'tertiary_muscle_group': None,
                'advanced_isolated_muscles': 'upper-pectoralis, mid-lower-pectoralis',
                'utility': 'Auxiliary',
                'grips': None,
                'stabilizers': None,
                'synergists': None,
                'force': 'Push',
                'equipment': 'Cable',
                'mechanic': 'Isolated',
                'difficulty': 'Beginner',
            }
            
            ExerciseManager.save_exercise(exercise_data)
            
            # Verify isolated muscles were synced
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                muscles = db.fetch_all(
                    "SELECT muscle FROM exercise_isolated_muscles WHERE exercise_name = ?",
                    ('Cable Fly',)
                )
            
            muscle_list = [m['muscle'] for m in muscles]
            assert len(muscle_list) >= 1


class TestRemoveExerciseByName:
    """Tests for ExerciseManager.remove_exercise_by_name()."""
    
    def test_remove_exercise_deletes_from_exercises_table(self, app, exercise_factory):
        """Should delete exercise from exercises table."""
        with app.app_context():
            exercise_factory("To Be Deleted")
            
            # Verify exists
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                before = db.fetch_one("SELECT COUNT(*) as cnt FROM exercises WHERE exercise_name = ?", ('To Be Deleted',))
            assert before['cnt'] == 1
            
            # Remove
            ExerciseManager.remove_exercise_by_name("To Be Deleted")
            
            # Verify deleted
            with DatabaseHandler() as db:
                after = db.fetch_one("SELECT COUNT(*) as cnt FROM exercises WHERE exercise_name = ?", ('To Be Deleted',))
            assert after['cnt'] == 0
    
    def test_remove_exercise_deletes_isolated_muscle_mappings(self, app, clean_db):
        """Should delete associated isolated muscle mappings."""
        with app.app_context():
            # Create exercise with isolated muscles using all required fields
            exercise_data = {
                'exercise_name': 'Mapped Exercise',
                'primary_muscle_group': 'Chest',
                'secondary_muscle_group': None,
                'tertiary_muscle_group': None,
                'advanced_isolated_muscles': 'upper-pectoralis, mid-lower-pectoralis',
                'utility': 'Basic',
                'grips': None,
                'stabilizers': None,
                'synergists': None,
                'force': 'Push',
                'equipment': 'Cable',
                'mechanic': 'Isolated',
                'difficulty': 'Beginner',
            }
            ExerciseManager.save_exercise(exercise_data)
            
            # Verify mapping exists
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                before = db.fetch_one(
                    "SELECT COUNT(*) as cnt FROM exercise_isolated_muscles WHERE exercise_name = ?",
                    ('Mapped Exercise',)
                )
            assert before['cnt'] >= 1
            
            # Remove
            ExerciseManager.remove_exercise_by_name("Mapped Exercise")
            
            # Verify mapping deleted
            with DatabaseHandler() as db:
                after = db.fetch_one(
                    "SELECT COUNT(*) as cnt FROM exercise_isolated_muscles WHERE exercise_name = ?",
                    ('Mapped Exercise',)
                )
            assert after['cnt'] == 0
    
    def test_remove_nonexistent_exercise(self, app, clean_db):
        """Should handle removal of non-existent exercise gracefully."""
        with app.app_context():
            # Should not raise an error
            ExerciseManager.remove_exercise_by_name("NonExistent Exercise")


class TestFetchUniqueValues:
    """Tests for ExerciseManager.fetch_unique_values()."""
    
    def test_fetch_unique_values_returns_distinct(self, app, exercise_factory):
        """Should return distinct values for column."""
        with app.app_context():
            exercise_factory("Exercise 1", equipment="Barbell")
            exercise_factory("Exercise 2", equipment="Dumbbell")
            exercise_factory("Exercise 3", equipment="Barbell")  # Duplicate
            
            result = ExerciseManager.fetch_unique_values("exercises", "equipment")
            
            assert "Barbell" in result
            assert "Dumbbell" in result
            assert len(result) >= 2
    
    def test_fetch_unique_values_excludes_null(self, app, exercise_factory):
        """Should exclude NULL values."""
        with app.app_context():
            exercise_factory("Exercise 1", tertiary_muscle_group="Shoulders")
            exercise_factory("Exercise 2", tertiary_muscle_group=None)  # NULL
            
            result = ExerciseManager.fetch_unique_values("exercises", "tertiary_muscle_group")
            
            assert None not in result
    
    def test_fetch_unique_values_ordered_alphabetically(self, app, exercise_factory):
        """Should return values in alphabetical order."""
        with app.app_context():
            exercise_factory("Exercise 1", primary_muscle_group="Chest")
            exercise_factory("Exercise 2", primary_muscle_group="Back")
            exercise_factory("Exercise 3", primary_muscle_group="Arms")
            
            result = ExerciseManager.fetch_unique_values("exercises", "primary_muscle_group")
            
            # Check ordering
            sorted_result = sorted(result)
            assert result == sorted_result
    
    def test_fetch_unique_values_empty_table(self, app, clean_db):
        """Should return empty list for empty table."""
        with app.app_context():
            result = ExerciseManager.fetch_unique_values("exercises", "equipment")
            assert result == []


class TestPublicInterfaceShortcuts:
    """Tests for the public interface shortcut functions."""
    
    def test_get_exercises_shortcut(self, app, exercise_factory):
        """get_exercises should be equivalent to ExerciseManager.get_exercises."""
        with app.app_context():
            exercise_factory("Test Exercise")
            
            result1 = get_exercises()
            result2 = ExerciseManager.get_exercises()
            
            assert len(result1) == len(result2)
    
    def test_add_exercise_shortcut(self, app, exercise_factory, clean_db):
        """add_exercise should be equivalent to ExerciseManager.add_exercise."""
        with app.app_context():
            exercise_factory("Bench Press")
            
            result = add_exercise(
                routine="Workout A",
                exercise="Bench Press",
                sets=3,
                min_rep_range=6,
                max_rep_range=8,
                rir=2,
                weight=100.0
            )
            
            assert result == "Exercise added successfully."
    
    def test_delete_exercise_shortcut_exists(self):
        """delete_exercise shortcut should exist and be callable."""
        assert callable(delete_exercise)
    
    def test_fetch_unique_values_shortcut_exists(self):
        """fetch_unique_values shortcut should exist and be callable."""
        assert callable(fetch_unique_values)
    
    def test_save_exercise_shortcut_exists(self):
        """save_exercise shortcut should exist and be callable."""
        assert callable(save_exercise)
    
    def test_remove_exercise_by_name_shortcut_exists(self):
        """remove_exercise_by_name shortcut should exist and be callable."""
        assert callable(remove_exercise_by_name)


class TestSyncIsolatedMuscles:
    """Tests for the internal _sync_isolated_muscles helper."""
    
    def test_sync_clears_existing_mappings(self, app, clean_db):
        """Should clear existing mappings before adding new ones."""
        with app.app_context():
            # First save with muscles - must provide all columns
            exercise_data = {
                'exercise_name': 'Test Exercise',
                'primary_muscle_group': 'Chest',
                'secondary_muscle_group': None,
                'tertiary_muscle_group': None,
                'advanced_isolated_muscles': 'muscle-a, muscle-b',
                'utility': 'Basic',
                'grips': None,
                'stabilizers': None,
                'synergists': None,
                'force': 'Push',
                'equipment': 'Barbell',
                'mechanic': 'Compound',
                'difficulty': 'Intermediate',
            }
            ExerciseManager.save_exercise(exercise_data)
            
            # Update with different muscles
            updated_data = {
                'exercise_name': 'Test Exercise',
                'primary_muscle_group': 'Chest',
                'secondary_muscle_group': None,
                'tertiary_muscle_group': None,
                'advanced_isolated_muscles': 'muscle-c',  # Different
                'utility': 'Basic',
                'grips': None,
                'stabilizers': None,
                'synergists': None,
                'force': 'Push',
                'equipment': 'Barbell',
                'mechanic': 'Compound',
                'difficulty': 'Intermediate',
            }
            ExerciseManager.save_exercise(updated_data)
            
            # Verify only new muscles exist
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                muscles = db.fetch_all(
                    "SELECT muscle FROM exercise_isolated_muscles WHERE exercise_name = ?",
                    ('Test Exercise',)
                )
            
            muscle_list = [m['muscle'] for m in muscles]
            assert 'muscle-a' not in muscle_list
            assert 'muscle-b' not in muscle_list
    
    def test_sync_handles_empty_muscles(self, app, clean_db):
        """Should handle empty/None isolated muscles."""
        with app.app_context():
            # Save with no isolated muscles - must provide all columns
            exercise_data = {
                'exercise_name': 'Simple Exercise',
                'primary_muscle_group': 'Chest',
                'secondary_muscle_group': None,
                'tertiary_muscle_group': None,
                'advanced_isolated_muscles': None,
                'utility': 'Basic',
                'grips': None,
                'stabilizers': None,
                'synergists': None,
                'force': 'Push',
                'equipment': 'Barbell',
                'mechanic': 'Compound',
                'difficulty': 'Beginner',
            }
            ExerciseManager.save_exercise(exercise_data)
            
            # Verify no mappings created
            from utils.database import DatabaseHandler
            with DatabaseHandler() as db:
                muscles = db.fetch_all(
                    "SELECT muscle FROM exercise_isolated_muscles WHERE exercise_name = ?",
                    ('Simple Exercise',)
                )
            
            assert len(muscles) == 0
