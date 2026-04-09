"""
Tests for utils/session_summary.py

Tests the session-level analytics including:
- Effective and raw set counting modes
- Contribution modes (total vs direct-only)
- Routine filtering
- Time window filtering
- Volume warnings and classifications
"""
import pytest
import os
from datetime import datetime, timedelta

# Set testing environment before imports
os.environ['TESTING'] = '1'

from utils.session_summary import calculate_session_summary
from utils.effective_sets import CountingMode, ContributionMode, VolumeWarningLevel


class TestCalculateSessionSummaryBasic:
    """Basic tests for calculate_session_summary function."""
    
    def test_empty_database_returns_empty_dict(self, app, clean_db):
        """Should return empty dict when no exercises in plan."""
        with app.app_context():
            result = calculate_session_summary()
            assert result == {}
    
    def test_returns_nested_dict_structure(self, app, exercise_factory, workout_plan_factory):
        """Should return nested dict: {routine: {muscle: {stats}}}."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            result = calculate_session_summary()
            
            # Check structure
            assert isinstance(result, dict)
            assert len(result) > 0
            
            for routine_name, muscles in result.items():
                assert isinstance(muscles, dict)
                for muscle_name, stats in muscles.items():
                    assert isinstance(stats, dict)
                    assert 'weekly_sets' in stats
                    assert 'effective_sets' in stats
                    assert 'raw_sets' in stats
    
    def test_single_exercise_single_routine(self, app, exercise_factory, workout_plan_factory):
        """Should correctly aggregate a single exercise."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Squat",
                primary_muscle_group="Quadriceps",
                secondary_muscle_group="Glutes",
                tertiary_muscle_group="Hamstrings"
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="Workout A",
                sets=4,
                min_rep_range=8,
                max_rep_range=10,
                rir=2,
                weight=100.0
            )
            
            result = calculate_session_summary()
            
            assert "Workout A" in result
            assert "Quadriceps" in result["Workout A"]
            
            # Check that primary muscle gets contribution
            stats = result["Workout A"]["Quadriceps"]
            assert stats['raw_sets'] > 0
            assert stats['effective_sets'] > 0


class TestCountingModes:
    """Tests for RAW and EFFECTIVE counting modes."""
    
    def test_effective_mode_applies_effort_factor(self, app, exercise_factory, workout_plan_factory):
        """EFFECTIVE mode should reduce sets based on RIR/RPE."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            # High RIR = lower effort factor
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                rir=5,  # High RIR = lower effort
                weight=100.0
            )
            
            result = calculate_session_summary(counting_mode=CountingMode.EFFECTIVE)
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            # Effective sets should be less than raw sets due to effort factor
            assert stats['effective_sets'] < stats['raw_sets']
    
    def test_raw_mode_ignores_effort_factor(self, app, exercise_factory, workout_plan_factory):
        """RAW mode should return sets without effort adjustment."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                rir=5,
                weight=100.0
            )
            
            result = calculate_session_summary(counting_mode=CountingMode.RAW)
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            # In RAW mode, weekly_sets should equal raw_sets
            assert stats['weekly_sets'] == stats['raw_sets']
            # Raw sets for primary should be 4 (full credit)
            assert stats['raw_sets'] == 4.0
    
    def test_effective_mode_reports_weekly_sets_as_effective(self, app, exercise_factory, workout_plan_factory):
        """EFFECTIVE mode should report weekly_sets as effective value."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Squat",
                primary_muscle_group="Quadriceps",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                rir=0,  # Max effort
                weight=100.0
            )
            
            result = calculate_session_summary(counting_mode=CountingMode.EFFECTIVE)
            
            routine = list(result.keys())[0]
            stats = result[routine]["Quadriceps"]
            
            # weekly_sets should match effective_sets in EFFECTIVE mode
            assert stats['weekly_sets'] == stats['effective_sets']
            assert stats['counting_mode'] == 'effective'

    def test_effective_sets_invariant_across_counting_modes(self, app, exercise_factory, workout_plan_factory):
        """effective_sets should remain weighted even when counting_mode is RAW."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Incline Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )

            workout_plan_factory(
                exercise_name=exercise_name,
                routine="Seed Routine",
                sets=12,
                min_rep_range=8,
                max_rep_range=10,
                rir=2,
                weight=100.0
            )

            eff_mode = calculate_session_summary(counting_mode=CountingMode.EFFECTIVE)
            raw_mode = calculate_session_summary(counting_mode=CountingMode.RAW)

            eff_sets = eff_mode["Seed Routine"]["Chest"]["effective_sets"]
            raw_sets = raw_mode["Seed Routine"]["Chest"]["effective_sets"]
            expected = 12 * 0.85 * 1.0
            assert eff_sets == pytest.approx(expected)
            assert raw_sets == pytest.approx(expected)


class TestContributionModes:
    """Tests for TOTAL and DIRECT_ONLY contribution modes."""
    
    def test_total_mode_includes_all_muscles(self, app, exercise_factory, workout_plan_factory):
        """TOTAL mode should include primary, secondary, and tertiary muscles."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                rir=2,
                weight=100.0
            )
            
            result = calculate_session_summary(contribution_mode=ContributionMode.TOTAL)
            
            routine = list(result.keys())[0]
            
            # All three muscles should be present
            assert "Chest" in result[routine]
            assert "Triceps" in result[routine]
            assert "Shoulders" in result[routine]
    
    def test_direct_only_mode_excludes_secondary_tertiary(self, app, exercise_factory, workout_plan_factory):
        """DIRECT_ONLY mode should only include primary muscle."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                rir=2,
                weight=100.0
            )
            
            result = calculate_session_summary(contribution_mode=ContributionMode.DIRECT_ONLY)
            
            routine = list(result.keys())[0]
            
            # Only primary muscle should be present
            assert "Chest" in result[routine]
            assert "Triceps" not in result[routine]
            assert "Shoulders" not in result[routine]
    
    def test_direct_only_gives_full_credit_to_primary(self, app, exercise_factory, workout_plan_factory):
        """DIRECT_ONLY mode should give 1.0 weight factor to primary."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Squat",
                primary_muscle_group="Quadriceps",
                secondary_muscle_group="Glutes",
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                rir=0,  # Max effort for simplicity
                weight=100.0
            )
            
            result = calculate_session_summary(
                counting_mode=CountingMode.RAW,
                contribution_mode=ContributionMode.DIRECT_ONLY
            )
            
            routine = list(result.keys())[0]
            stats = result[routine]["Quadriceps"]
            
            # In DIRECT_ONLY + RAW mode, should get full 4 raw sets
            assert stats['raw_sets'] == 4.0


class TestRoutineFiltering:
    """Tests for routine filtering parameter."""
    
    def test_filter_by_routine_single_match(self, app, exercise_factory, workout_plan_factory):
        """Should only return data for the specified routine."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="Workout A",
                sets=3,
                weight=100.0
            )
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="Workout B",
                sets=4,
                weight=100.0
            )
            
            result = calculate_session_summary(routine="Workout A")
            
            # Only Workout A should be present
            assert "Workout A" in result
            assert "Workout B" not in result
    
    def test_filter_by_routine_no_match(self, app, exercise_factory, workout_plan_factory):
        """Should return empty when no routine matches."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="Workout A",
                sets=3,
                weight=100.0
            )
            
            result = calculate_session_summary(routine="NonExistent Routine")
            
            assert result == {}
    
    def test_no_routine_filter_returns_all(self, app, exercise_factory, workout_plan_factory):
        """Should return all routines when no filter is specified."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="Workout A",
                sets=3,
                weight=100.0
            )
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="Workout B",
                sets=4,
                weight=100.0
            )
            
            result = calculate_session_summary(routine=None)
            
            assert "Workout A" in result
            assert "Workout B" in result


class TestVolumeWarnings:
    """Tests for volume warning levels."""
    
    def test_low_volume_no_data_warning_without_logs(self, app, exercise_factory, workout_plan_factory):
        """Without logged sessions, warning_level should be 'no_data'."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Curl",
                primary_muscle_group="Biceps",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )

            # Low volume: 2 sets, but no logged sessions
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=2,
                rir=2,
                weight=20.0
            )

            result = calculate_session_summary()

            routine = list(result.keys())[0]
            stats = result[routine]["Biceps"]

            # No logged sessions → no_data state
            assert stats['warning_level'] == 'no_data'
            assert stats['has_logged_sessions'] is False
            assert stats['sets_per_session'] is None
            assert stats['effective_per_session'] is None
            assert stats['is_borderline'] is False
            assert stats['is_excessive'] is False

    def test_warning_level_in_response(self, app, exercise_factory, workout_plan_factory):
        """Warning level should always be present in response."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )

            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)

            result = calculate_session_summary()

            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]

            assert 'warning_level' in stats
            assert stats['warning_level'] in ['ok', 'borderline', 'excessive', 'no_data']


class TestSessionLogAggregation:
    """Regression tests for workout_log join behavior."""

    def test_workout_log_rows_do_not_multiply_plan_totals(
        self,
        app,
        exercise_factory,
        workout_plan_factory,
        db_handler,
    ):
        """Adding multiple logs should only affect session_count metrics, not totals."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Seed Bench",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None,
            )
            plan_id = workout_plan_factory(
                exercise_name=exercise_name,
                routine="Seed Routine",
                sets=12,
                min_rep_range=8,
                max_rep_range=10,
                rir=2,
                weight=100.0,
            )

            baseline = calculate_session_summary(counting_mode=CountingMode.EFFECTIVE)
            baseline_stats = baseline["Seed Routine"]["Chest"]
            assert baseline_stats["effective_sets"] == pytest.approx(10.2)
            assert baseline_stats["session_count"] == 0

            session_dates = (
                "2026-02-01 09:00:00",
                "2026-02-03 09:00:00",
                "2026-02-05 09:00:00",
                "2026-02-07 09:00:00",
            )
            for created_at in session_dates:
                db_handler.execute_query(
                    """
                    INSERT INTO workout_log (
                        workout_plan_id,
                        routine,
                        exercise,
                        planned_sets,
                        planned_min_reps,
                        planned_max_reps,
                        planned_rir,
                        planned_rpe,
                        planned_weight,
                        scored_weight,
                        scored_min_reps,
                        scored_max_reps,
                        scored_rir,
                        scored_rpe,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id,
                        "Seed Routine",
                        "Seed Bench",
                        12,
                        8,
                        10,
                        2,
                        8.0,
                        100.0,
                        100.0,
                        8,
                        10,
                        2,
                        8.0,
                        created_at,
                    ),
                )

            with_logs = calculate_session_summary(counting_mode=CountingMode.EFFECTIVE)
            stats = with_logs["Seed Routine"]["Chest"]

            assert stats["effective_sets"] == pytest.approx(10.2)
            assert stats["session_count"] == 4
            assert stats["effective_per_session"] == pytest.approx(2.55)


class TestVolumeClassification:
    """Tests for volume classification."""
    
    def test_volume_class_present(self, app, exercise_factory, workout_plan_factory):
        """Volume class should be present in response."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Squat",
                primary_muscle_group="Quadriceps",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=4, weight=100.0)
            
            result = calculate_session_summary()
            
            routine = list(result.keys())[0]
            stats = result[routine]["Quadriceps"]
            
            assert 'volume_class' in stats
            assert 'status' in stats
    
    def test_status_map_values(self, app, exercise_factory, workout_plan_factory):
        """Status should be a recognized classification."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Deadlift",
                primary_muscle_group="Back",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=5, weight=150.0)
            
            result = calculate_session_summary()
            
            routine = list(result.keys())[0]
            stats = result[routine]["Back"]
            
            # Status should be one of the expected values
            assert stats['status'] in ['low', 'medium', 'high', 'excessive']


class TestResponseStructure:
    """Tests for response structure completeness."""
    
    def test_all_required_fields_present(self, app, exercise_factory, workout_plan_factory):
        """All required fields should be present in response."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                min_rep_range=6,
                max_rep_range=10,
                rir=2,
                weight=100.0
            )
            
            result = calculate_session_summary()
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            required_fields = [
                'weekly_sets',
                'sets_per_session',
                'status',
                'volume_class',
                'raw_sets',
                'effective_sets',
                'effective_per_session',
                'session_count',
                'has_logged_sessions',
                'warning_level',
                'is_borderline',
                'is_excessive',
                'total_reps',
                'total_volume',
                'raw_total_reps',
                'raw_total_volume',
                'counting_mode',
                'contribution_mode',
            ]
            
            for field in required_fields:
                assert field in stats, f"Missing field: {field}"
    
    def test_values_are_rounded(self, app, exercise_factory, workout_plan_factory):
        """Numeric values should be rounded to 2 decimal places."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=3,
                min_rep_range=8,
                max_rep_range=12,
                rir=3,
                weight=77.5
            )
            
            result = calculate_session_summary()
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            # Check rounding - values should not have more than 2 decimal places
            for key in ['weekly_sets', 'effective_sets', 'raw_sets', 'total_reps', 'total_volume']:
                value = stats[key]
                if isinstance(value, float):
                    str_val = str(value)
                    if '.' in str_val:
                        decimals = len(str_val.split('.')[1])
                        assert decimals <= 2, f"{key} has too many decimal places: {value}"


class TestMultipleExercises:
    """Tests for aggregation of multiple exercises."""
    
    def test_multiple_exercises_same_muscle_aggregated(self, app, exercise_factory, workout_plan_factory):
        """Multiple exercises targeting same muscle should be aggregated."""
        with app.app_context():
            # Two exercises targeting Chest
            ex1 = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            ex2 = exercise_factory(
                "Dumbbell Fly",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(exercise_name=ex1, sets=3, weight=100.0, rir=2)
            workout_plan_factory(exercise_name=ex2, sets=3, weight=20.0, rir=2)
            
            result = calculate_session_summary(counting_mode=CountingMode.RAW)
            
            routine = list(result.keys())[0]
            
            # Chest should have aggregated sets (3 + 3 = 6)
            assert result[routine]["Chest"]["raw_sets"] == 6.0
    
    def test_different_muscles_tracked_separately(self, app, exercise_factory, workout_plan_factory):
        """Different primary muscles should be tracked separately."""
        with app.app_context():
            ex1 = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            ex2 = exercise_factory(
                "Squat",
                primary_muscle_group="Quadriceps",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(exercise_name=ex1, routine="Workout A", sets=3, weight=100.0)
            workout_plan_factory(exercise_name=ex2, routine="Workout A", sets=4, weight=120.0)
            
            result = calculate_session_summary(counting_mode=CountingMode.RAW)
            
            # Both muscles should be present with correct sets
            assert result["Workout A"]["Chest"]["raw_sets"] == 3.0
            assert result["Workout A"]["Quadriceps"]["raw_sets"] == 4.0


class TestModeIndicators:
    """Tests for mode indicators in response."""
    
    def test_counting_mode_indicator_effective(self, app, exercise_factory, workout_plan_factory):
        """Response should include counting mode indicator for EFFECTIVE."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            result = calculate_session_summary(counting_mode=CountingMode.EFFECTIVE)
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            assert stats['counting_mode'] == 'effective'
    
    def test_counting_mode_indicator_raw(self, app, exercise_factory, workout_plan_factory):
        """Response should include counting mode indicator for RAW."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            result = calculate_session_summary(counting_mode=CountingMode.RAW)
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            assert stats['counting_mode'] == 'raw'
    
    def test_contribution_mode_indicator_total(self, app, exercise_factory, workout_plan_factory):
        """Response should include contribution mode indicator for TOTAL."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            result = calculate_session_summary(contribution_mode=ContributionMode.TOTAL)
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            assert stats['contribution_mode'] == 'total'
    
    def test_contribution_mode_indicator_direct(self, app, exercise_factory, workout_plan_factory):
        """Response should include contribution mode indicator for DIRECT_ONLY."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            result = calculate_session_summary(contribution_mode=ContributionMode.DIRECT_ONLY)
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            assert stats['contribution_mode'] == 'direct'


class TestNullMuscleGroups:
    """Tests for handling null/missing muscle groups."""
    
    def test_null_secondary_excluded(self, app, exercise_factory, workout_plan_factory):
        """Exercises with NULL secondary should not have secondary entry."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Cable Fly",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=20.0)
            
            result = calculate_session_summary(contribution_mode=ContributionMode.TOTAL)
            
            routine = list(result.keys())[0]
            
            # Only primary should be present
            assert "Chest" in result[routine]
            assert len(result[routine]) == 1
    
    def test_null_tertiary_excluded(self, app, exercise_factory, workout_plan_factory):
        """Exercises with NULL tertiary should not have tertiary entry."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            result = calculate_session_summary(contribution_mode=ContributionMode.TOTAL)
            
            routine = list(result.keys())[0]
            
            # Primary and secondary should be present, but no tertiary
            assert "Chest" in result[routine]
            assert "Triceps" in result[routine]
            assert len(result[routine]) == 2


class TestDefaultParameters:
    """Tests for default parameter values."""
    
    def test_default_counting_mode_is_effective(self, app, exercise_factory, workout_plan_factory):
        """Default counting mode should be EFFECTIVE."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=exercise_name, sets=3, rir=5, weight=100.0)
            
            # Call without specifying counting_mode
            result = calculate_session_summary()
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            # Default should be effective
            assert stats['counting_mode'] == 'effective'
            # weekly_sets should be reduced due to high RIR
            assert stats['weekly_sets'] == stats['effective_sets']
    
    def test_default_contribution_mode_is_total(self, app, exercise_factory, workout_plan_factory):
        """Default contribution mode should be TOTAL."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            # Call without specifying contribution_mode
            result = calculate_session_summary()
            
            routine = list(result.keys())[0]
            stats = result[routine]["Chest"]
            
            # Default should be total
            assert stats['contribution_mode'] == 'total'
