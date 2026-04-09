"""
Tests for utils/business_logic.py

Tests the core BusinessLogic class which handles weekly summary calculations
using different methods: Total, Fractional, and Direct.
"""
import pytest
import os

# Set testing environment before imports
os.environ['TESTING'] = '1'

from utils.business_logic import BusinessLogic


class TestBusinessLogicInit:
    """Tests for BusinessLogic initialization."""
    
    def test_init_creates_none_db_handler(self):
        """BusinessLogic should initialize with db_handler as None."""
        bl = BusinessLogic()
        assert bl.db_handler is None


class TestGetQueryForMethod:
    """Tests for the _get_query_for_method internal method."""
    
    def test_total_method_returns_query(self):
        """Total method should return a valid SQL query."""
        bl = BusinessLogic()
        query = bl._get_query_for_method("Total")
        
        assert "SELECT" in query
        assert "muscle_group" in query
        assert "total_sets" in query
        assert "primary_muscle_group" in query
        assert "secondary_muscle_group" in query
        assert "tertiary_muscle_group" in query
    
    def test_fractional_method_returns_query(self):
        """Fractional method should return a valid SQL query."""
        bl = BusinessLogic()
        query = bl._get_query_for_method("Fractional")
        
        assert "SELECT" in query
        assert "muscle_group" in query
        assert "0.5" in query  # Primary gets 50%
        assert "0.25" in query  # Secondary gets 25%
    
    def test_direct_method_returns_query(self):
        """Direct method should return a valid SQL query only for primary muscles."""
        bl = BusinessLogic()
        query = bl._get_query_for_method("Direct")
        
        assert "SELECT" in query
        assert "primary_muscle_group" in query
        # Direct method should NOT include secondary/tertiary in the subquery
        # It only queries primary muscle directly
    
    def test_invalid_method_raises_value_error(self):
        """Invalid method should raise ValueError."""
        bl = BusinessLogic()
        
        with pytest.raises(ValueError) as exc_info:
            bl._get_query_for_method("InvalidMethod")
        
        assert "Unknown calculation method" in str(exc_info.value)
        assert "InvalidMethod" in str(exc_info.value)
    
    def test_case_sensitive_method_names(self):
        """Method names should be case-sensitive."""
        bl = BusinessLogic()
        
        # Exact case should work
        bl._get_query_for_method("Total")
        
        # Wrong case should fail
        with pytest.raises(ValueError):
            bl._get_query_for_method("total")
        
        with pytest.raises(ValueError):
            bl._get_query_for_method("TOTAL")


class TestCalculateWeeklySummaryTotal:
    """Tests for calculate_weekly_summary with Total method."""
    
    def test_total_method_with_single_exercise(self, app, exercise_factory, workout_plan_factory):
        """Total method should calculate sets for primary, secondary, tertiary muscles."""
        with app.app_context():
            # Create exercise with all muscle groups
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            
            # Add to workout plan: 4 sets, 8 reps, 100kg
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                min_rep_range=6,
                max_rep_range=8,
                weight=100.0
            )
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            # Convert to dict for easier assertions
            results_dict = {r['muscle_group']: r for r in results}
            
            # Primary (Chest): 4 sets * 1.0 = 4 sets
            assert "Chest" in results_dict
            assert results_dict["Chest"]["total_sets"] == 4.0
            
            # Secondary (Triceps): 4 sets * 0.5 = 2 sets
            assert "Triceps" in results_dict
            assert results_dict["Triceps"]["total_sets"] == 2.0
            
            # Tertiary (Shoulders): 4 sets * 0.33 = 1.32 sets
            assert "Shoulders" in results_dict
            assert abs(results_dict["Shoulders"]["total_sets"] - 1.32) < 0.01
    
    def test_total_method_with_multiple_exercises(self, app, exercise_factory, workout_plan_factory):
        """Total method should aggregate sets across multiple exercises."""
        with app.app_context():
            # Exercise 1: Chest primary
            ex1 = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=ex1, sets=3, weight=100.0)
            
            # Exercise 2: Also Chest primary (different exercise)
            ex2 = exercise_factory(
                "Incline Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Shoulders",
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=ex2, sets=3, weight=80.0)
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Chest should have 6 total sets (3 + 3)
            assert results_dict["Chest"]["total_sets"] == 6.0
            
            # Triceps: 3 * 0.5 = 1.5 sets (from Bench only)
            assert results_dict["Triceps"]["total_sets"] == 1.5
            
            # Shoulders: 3 * 0.5 = 1.5 sets (from Incline only)
            assert results_dict["Shoulders"]["total_sets"] == 1.5
    
    def test_total_method_calculates_reps_correctly(self, app, exercise_factory, workout_plan_factory):
        """Total method should calculate total reps (sets * max_rep_range)."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Squat",
                primary_muscle_group="Quadriceps",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            # 3 sets, 10 max reps = 30 total reps
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=3,
                min_rep_range=8,
                max_rep_range=10,
                weight=120.0
            )
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # 3 sets * 10 reps = 30 total reps
            assert results_dict["Quadriceps"]["total_reps"] == 30.0
    
    def test_total_method_calculates_volume_correctly(self, app, exercise_factory, workout_plan_factory):
        """Total method should calculate total volume (sets * weight)."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Deadlift",
                primary_muscle_group="Back",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            # 4 sets, 150kg = 600 total weight
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=4,
                weight=150.0
            )
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # 4 sets * 150kg = 600 total weight
            assert results_dict["Back"]["total_weight"] == 600.0


class TestCalculateWeeklySummaryFractional:
    """Tests for calculate_weekly_summary with Fractional method."""
    
    def test_fractional_method_applies_correct_multipliers(self, app, exercise_factory, workout_plan_factory):
        """Fractional method should apply 0.5 to primary, 0.25 to secondary."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group=None  # Not used in Fractional
            )
            
            # 4 sets
            workout_plan_factory(exercise_name=exercise_name, sets=4, weight=100.0)
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Fractional")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Primary (Chest): 4 sets * 0.5 = 2 sets
            assert results_dict["Chest"]["total_sets"] == 2.0
            
            # Secondary (Triceps): 4 sets * 0.25 = 1 set
            assert results_dict["Triceps"]["total_sets"] == 1.0
    
    def test_fractional_method_ignores_tertiary(self, app, exercise_factory, workout_plan_factory):
        """Fractional method should not include tertiary muscle contributions."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=4, weight=100.0)
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Fractional")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Tertiary (Shoulders) should NOT appear in Fractional method
            assert "Shoulders" not in results_dict


class TestCalculateWeeklySummaryDirect:
    """Tests for calculate_weekly_summary with Direct method."""
    
    def test_direct_method_only_counts_primary(self, app, exercise_factory, workout_plan_factory):
        """Direct method should only count primary muscle group."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=4, weight=100.0)
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Direct")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Primary (Chest): 4 sets * 1.0 = 4 sets
            assert "Chest" in results_dict
            assert results_dict["Chest"]["total_sets"] == 4.0
            
            # Secondary and Tertiary should NOT appear
            assert "Triceps" not in results_dict
            assert "Shoulders" not in results_dict
    
    def test_direct_method_full_volume_for_primary(self, app, exercise_factory, workout_plan_factory):
        """Direct method should give full credit (1.0x) to primary muscle."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Squat",
                primary_muscle_group="Quadriceps",
                secondary_muscle_group="Glutes",
                tertiary_muscle_group="Hamstrings"
            )
            
            # 5 sets, 12 reps, 100kg
            workout_plan_factory(
                exercise_name=exercise_name,
                sets=5,
                min_rep_range=10,
                max_rep_range=12,
                weight=100.0
            )
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Direct")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Full credit: 5 sets, 60 reps, 500 volume
            assert results_dict["Quadriceps"]["total_sets"] == 5.0
            assert results_dict["Quadriceps"]["total_reps"] == 60.0
            assert results_dict["Quadriceps"]["total_weight"] == 500.0


class TestCalculateWeeklySummaryEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_database_returns_empty_list(self, app, clean_db):
        """Should return empty list when no exercises are in the plan."""
        with app.app_context():
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            assert results == []
    
    def test_default_method_is_total(self, app, exercise_factory, workout_plan_factory):
        """Default method should be 'Total' when not specified."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group=None
            )
            workout_plan_factory(exercise_name=exercise_name, sets=4, weight=100.0)
            
            bl = BusinessLogic()
            
            # Call without method argument
            default_results = bl.calculate_weekly_summary()
            
            # Call with explicit "Total"
            total_results = bl.calculate_weekly_summary(method="Total")
            
            # Results should be identical
            assert len(default_results) == len(total_results)
            
            default_dict = {r['muscle_group']: r for r in default_results}
            total_dict = {r['muscle_group']: r for r in total_results}
            
            for muscle in default_dict:
                assert default_dict[muscle]['total_sets'] == total_dict[muscle]['total_sets']
    
    def test_invalid_method_returns_empty_list(self, app):
        """Invalid method should return empty list (catches ValueError)."""
        with app.app_context():
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="InvalidMethod")
            
            # Should return empty list due to caught ValueError
            assert results == []
    
    def test_null_secondary_muscle_excluded(self, app, exercise_factory, workout_plan_factory):
        """Exercises with NULL secondary muscle should not contribute to secondary totals."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Cable Fly",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,  # Isolation exercise
                tertiary_muscle_group=None
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=20.0)
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Only Chest should appear
            assert len(results_dict) == 1
            assert "Chest" in results_dict
    
    def test_db_handler_closed_after_execution(self, app, exercise_factory, workout_plan_factory):
        """Database handler should be closed after calculate_weekly_summary."""
        with app.app_context():
            exercise_name = exercise_factory("Test Exercise")
            workout_plan_factory(exercise_name=exercise_name)
            
            bl = BusinessLogic()
            bl.calculate_weekly_summary(method="Total")
            
            # After execution, db_handler should be None (closed in finally block)
            assert bl.db_handler is None
    
    def test_multiple_routines_aggregated(self, app, exercise_factory, workout_plan_factory):
        """Sets from different routines should be aggregated together."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group=None
            )
            
            # Workout A: 3 sets
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="GYM - Push - Workout A",
                sets=3,
                weight=100.0
            )
            
            # Workout B: 4 sets
            workout_plan_factory(
                exercise_name=exercise_name,
                routine="GYM - Push - Workout B",
                sets=4,
                weight=90.0
            )
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Total: 3 + 4 = 7 sets
            assert results_dict["Chest"]["total_sets"] == 7.0


class TestCalculateWeeklySummaryRoundingBehavior:
    """Tests for rounding behavior in calculations."""
    
    def test_results_rounded_to_two_decimals(self, app, exercise_factory, workout_plan_factory):
        """Results should be rounded to 2 decimal places."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group=None,
                tertiary_muscle_group="Shoulders"
            )
            
            # 3 sets -> tertiary = 3 * 0.33 = 0.99
            workout_plan_factory(exercise_name=exercise_name, sets=3, weight=100.0)
            
            bl = BusinessLogic()
            results = bl.calculate_weekly_summary(method="Total")
            
            results_dict = {r['muscle_group']: r for r in results}
            
            # Check that values are properly rounded
            assert results_dict["Shoulders"]["total_sets"] == 0.99
            
            # Ensure not more than 2 decimal places
            sets_str = str(results_dict["Shoulders"]["total_sets"])
            if '.' in sets_str:
                decimals = len(sets_str.split('.')[1])
                assert decimals <= 2


class TestMethodComparison:
    """Tests comparing different calculation methods."""
    
    def test_total_produces_more_volume_than_fractional(self, app, exercise_factory, workout_plan_factory):
        """Total method should always produce >= volume compared to Fractional."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=4, weight=100.0)
            
            bl = BusinessLogic()
            
            total_results = bl.calculate_weekly_summary(method="Total")
            fractional_results = bl.calculate_weekly_summary(method="Fractional")
            
            total_dict = {r['muscle_group']: r for r in total_results}
            fractional_dict = {r['muscle_group']: r for r in fractional_results}
            
            # Total should have more chest sets than Fractional
            # Total: 4 sets, Fractional: 2 sets
            assert total_dict["Chest"]["total_sets"] > fractional_dict["Chest"]["total_sets"]
    
    def test_direct_produces_less_volume_than_total(self, app, exercise_factory, workout_plan_factory):
        """Direct method should produce <= total volume compared to Total method."""
        with app.app_context():
            exercise_name = exercise_factory(
                "Bench Press",
                primary_muscle_group="Chest",
                secondary_muscle_group="Triceps",
                tertiary_muscle_group="Shoulders"
            )
            
            workout_plan_factory(exercise_name=exercise_name, sets=4, weight=100.0)
            
            bl = BusinessLogic()
            
            total_results = bl.calculate_weekly_summary(method="Total")
            direct_results = bl.calculate_weekly_summary(method="Direct")
            
            # Total includes secondary/tertiary, Direct does not
            assert len(total_results) > len(direct_results)
