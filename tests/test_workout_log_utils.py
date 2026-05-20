"""
Tests for utils/workout_log.py

Covers workout log data fetching and progression checking with focus on:
- Empty results handling
- All 5 progression conditions (RIR, RPE, min_reps, max_reps, weight)
- NULL value handling in comparisons
"""
import pytest
from utils.workout_log import (
    check_progression,
    get_weight_progression_indicator,
    get_workout_logs,
    is_assisted_bodyweight_exercise,
)


class TestGetWorkoutLogs:
    """Tests for get_workout_logs function."""

    def test_get_workout_logs_empty_db(self, clean_db):
        """Should return empty list when no logs exist."""
        result = get_workout_logs()
        assert result == []

    def test_get_workout_logs_returns_list(self, clean_db):
        """Should always return a list."""
        result = get_workout_logs()
        assert isinstance(result, list)

    def test_get_workout_logs_with_entries(self, clean_db, workout_log_fixture):
        """Should return workout log entries when they exist."""
        result = get_workout_logs()
        assert len(result) >= 1

    def test_get_workout_logs_ordered_by_routine_exercise(self, clean_db, multiple_workout_logs):
        """Should return logs ordered by routine, then exercise."""
        result = get_workout_logs()
        assert len(result) >= 2
        # Results should be ordered by routine, exercise


class TestCheckProgression:
    """Tests for check_progression function - all 5 conditions."""

    # Condition 1: RIR decreased (scored_rir < planned_rir = HARDER)
    def test_progression_rir_decreased(self):
        """Progress achieved when scored RIR < planned RIR."""
        log_entry = {
            'scored_rir': 1,
            'planned_rir': 3,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is True

    def test_no_progression_rir_same(self):
        """No progress when RIR unchanged."""
        log_entry = {
            'scored_rir': 2,
            'planned_rir': 2,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is False

    def test_no_progression_rir_increased(self):
        """No progress when RIR increased (easier)."""
        log_entry = {
            'scored_rir': 3,
            'planned_rir': 2,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is False

    # Condition 2: RPE increased (scored_rpe > planned_rpe = HARDER)
    def test_progression_rpe_increased(self):
        """Progress achieved when scored RPE > planned RPE."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': 9.0,
            'planned_rpe': 7.0,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is True

    def test_no_progression_rpe_same(self):
        """No progress when RPE unchanged."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': 8.0,
            'planned_rpe': 8.0,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is False

    # Condition 3: Min reps increased
    def test_progression_min_reps_increased(self):
        """Progress achieved when scored min reps > planned min reps."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': 10,
            'planned_min_reps': 8,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is True

    # Condition 4: Max reps increased
    def test_progression_max_reps_increased(self):
        """Progress achieved when scored max reps > planned max reps."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': 14,
            'planned_max_reps': 12,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is True

    # Condition 5: Weight increased
    def test_progression_weight_increased(self):
        """Progress achieved when scored weight > planned weight."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': 85.0,
            'planned_weight': 80.0
        }
        assert check_progression(log_entry) is True

    def test_progression_assisted_bodyweight_weight_decreased(self):
        """Progress achieved when machine assistance decreases."""
        log_entry = {
            'exercise': 'Machine Assisted Chin Up',
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': 60.0,
            'planned_weight': 65.0
        }
        assert check_progression(log_entry) is True

    def test_no_progression_assisted_bodyweight_weight_increased(self):
        """More machine assistance is below target, not progress."""
        log_entry = {
            'exercise': 'Machine Assisted Parallel Bar Dips',
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': 70.0,
            'planned_weight': 65.0
        }
        assert check_progression(log_entry) is False

    def test_no_progression_weight_same(self):
        """No progress when weight unchanged."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': 80.0,
            'planned_weight': 80.0
        }
        assert check_progression(log_entry) is False

    # NULL value handling
    def test_all_null_no_progression(self):
        """No progress when all values are NULL."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': None,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is False

    def test_scored_null_no_progression(self):
        """No progress when scored value is NULL but planned exists."""
        log_entry = {
            'scored_rir': None,
            'planned_rir': 2,
            'scored_rpe': None,
            'planned_rpe': 7.0,
            'scored_min_reps': None,
            'planned_min_reps': 8,
            'scored_max_reps': None,
            'planned_max_reps': 12,
            'scored_weight': None,
            'planned_weight': 80.0
        }
        assert check_progression(log_entry) is False

    def test_planned_null_no_progression(self):
        """No progress when planned value is NULL but scored exists."""
        log_entry = {
            'scored_rir': 2,
            'planned_rir': None,
            'scored_rpe': 8.0,
            'planned_rpe': None,
            'scored_min_reps': 10,
            'planned_min_reps': None,
            'scored_max_reps': 12,
            'planned_max_reps': None,
            'scored_weight': 80.0,
            'planned_weight': None
        }
        assert check_progression(log_entry) is False

    # Multiple conditions
    def test_multiple_progressions_any_true(self):
        """Progress achieved if ANY condition is met."""
        log_entry = {
            'scored_rir': 3,  # No progress (same)
            'planned_rir': 3,
            'scored_rpe': 7.0,  # No progress (same)
            'planned_rpe': 7.0,
            'scored_min_reps': 8,  # No progress (same)
            'planned_min_reps': 8,
            'scored_max_reps': 14,  # PROGRESS! (increased)
            'planned_max_reps': 12,
            'scored_weight': 80.0,  # No progress (same)
            'planned_weight': 80.0
        }
        assert check_progression(log_entry) is True

    def test_edge_case_zero_rir(self):
        """Progress when RIR goes from non-zero to zero (failure)."""
        log_entry = {
            'scored_rir': 0,
            'planned_rir': 1,
            'scored_rpe': None,
            'planned_rpe': None,
            'scored_min_reps': None,
            'planned_min_reps': None,
            'scored_max_reps': None,
            'planned_max_reps': None,
            'scored_weight': None,
            'planned_weight': None
        }
        assert check_progression(log_entry) is True


class TestAssistedBodyweightHelpers:
    """Tests for assisted-machine weight semantics."""

    @pytest.mark.parametrize("exercise_name", [
        "Machine Assisted Chin Up",
        "Machine Assisted Narrow Pull Up",
        "Machine Assisted Neutral Chin Up",
        "Machine Assisted Parallel Bar Dips",
        "Machine Assisted Pull Up",
        "Smith Machine Assisted Pullup",
    ])
    def test_detects_assisted_bodyweight_exercises(self, exercise_name):
        assert is_assisted_bodyweight_exercise(exercise_name) is True

    def test_regular_machine_weight_is_not_assistance(self):
        assert is_assisted_bodyweight_exercise("Machine Chest Press") is False

    def test_assisted_indicator_treats_lower_weight_as_improved(self):
        indicator = get_weight_progression_indicator(
            "Machine Assisted Chin Up",
            planned_weight=65.0,
            scored_weight=60.0,
        )
        assert indicator["icon"] == "fa-arrow-up"
        assert indicator["class"] == "text-success"
        assert "Assistance decreased" in indicator["title"]

    def test_assisted_indicator_treats_zero_assistance_as_improved(self):
        indicator = get_weight_progression_indicator(
            "Machine Assisted Pull Up",
            planned_weight=5.0,
            scored_weight=0.0,
        )
        assert indicator["icon"] == "fa-arrow-up"
        assert indicator["class"] == "text-success"

    def test_assisted_indicator_treats_higher_weight_as_below_target(self):
        indicator = get_weight_progression_indicator(
            "Machine Assisted Chin Up",
            planned_weight=65.0,
            scored_weight=70.0,
        )
        assert indicator["icon"] == "fa-arrow-down"
        assert indicator["class"] == "text-danger"
        assert "Assistance increased" in indicator["title"]


# Fixtures for workout_log utils tests
@pytest.fixture
def workout_log_fixture(clean_db, exercise_factory):
    """Create a workout log entry for testing."""
    from utils.database import DatabaseHandler
    
    exercise_factory("Test Exercise")
    
    with DatabaseHandler() as db:
        # Create user_selection first (FK requirement)
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Push", "Test Exercise", 3, 8, 12, 2, 80.0))
        
        result = db.fetch_one("SELECT id FROM user_selection ORDER BY id DESC LIMIT 1")
        assert result is not None
        plan_id = result["id"]
        
        # Create workout log
        db.execute_query("""
            INSERT INTO workout_log (
                routine, exercise, planned_sets, planned_min_reps, planned_max_reps,
                planned_rir, planned_weight, workout_plan_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, ("Push", "Test Exercise", 3, 8, 12, 2, 80.0, plan_id))
        
        result = db.fetch_one("SELECT id FROM workout_log ORDER BY id DESC LIMIT 1")
        assert result is not None
        
        return {"id": result["id"], "plan_id": plan_id}


@pytest.fixture
def multiple_workout_logs(clean_db, exercise_factory):
    """Create multiple workout log entries for ordering tests."""
    from utils.database import DatabaseHandler
    
    exercise_factory("Exercise A")
    exercise_factory("Exercise B")
    
    with DatabaseHandler() as db:
        # Create user_selections
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Push", "Exercise A", 3, 8, 12, 2, 80.0))
        result_a = db.fetch_one("SELECT id FROM user_selection ORDER BY id DESC LIMIT 1")
        assert result_a is not None
        
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Pull", "Exercise B", 3, 8, 12, 2, 60.0))
        result_b = db.fetch_one("SELECT id FROM user_selection ORDER BY id DESC LIMIT 1")
        assert result_b is not None
        
        # Create workout logs
        db.execute_query("""
            INSERT INTO workout_log (
                routine, exercise, planned_sets, workout_plan_id, created_at
            ) VALUES (?, ?, ?, ?, datetime('now'))
        """, ("Push", "Exercise A", 3, result_a["id"]))
        
        db.execute_query("""
            INSERT INTO workout_log (
                routine, exercise, planned_sets, workout_plan_id, created_at
            ) VALUES (?, ?, ?, ?, datetime('now'))
        """, ("Pull", "Exercise B", 3, result_b["id"]))
        
        return {"exercise_a_plan_id": result_a["id"], "exercise_b_plan_id": result_b["id"]}
