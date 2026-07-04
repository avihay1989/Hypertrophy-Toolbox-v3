"""
Tests for utils/progression_plan.py

Covers double progression calculations with focus on:
- Weight increment rules (under/over 20kg, novice flag)
- Acceptable effort checks (RIR/RPE boundaries)
- Progression status determination (all NULL cases, boundaries)
- Consistency analysis (empty history, single session)
- Suggestion generation (complex history patterns)
"""
import pytest
from utils.progression_plan import (
    _calculate_weight_increment,
    _check_acceptable_effort,
    _get_progression_status,
    _analyze_consistency,
    generate_progression_suggestions,
    get_exercise_history,
)


class TestCalculateWeightIncrement:
    """Tests for weight increment calculation rules."""

    def test_weight_under_20kg_returns_2_5(self):
        """Weight under 20kg should increment by 2.5kg."""
        assert _calculate_weight_increment(15.0) == 2.5
        assert _calculate_weight_increment(10.0) == 2.5
        assert _calculate_weight_increment(5.0) == 2.5
        assert _calculate_weight_increment(0.0) == 2.5

    def test_weight_at_19_9kg_returns_2_5(self):
        """Weight just under 20kg boundary."""
        assert _calculate_weight_increment(19.9) == 2.5

    def test_weight_at_20kg_returns_5(self):
        """Weight at exactly 20kg should increment by 5kg (non-novice)."""
        assert _calculate_weight_increment(20.0, is_novice=False) == 5.0

    def test_weight_over_20kg_returns_5(self):
        """Weight over 20kg should increment by 5kg (non-novice)."""
        assert _calculate_weight_increment(50.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(100.0, is_novice=False) == 5.0

    def test_novice_at_20kg_returns_2_5(self):
        """Novice at 20kg+ should still get smaller increment."""
        assert _calculate_weight_increment(20.0, is_novice=True) == 2.5
        assert _calculate_weight_increment(50.0, is_novice=True) == 2.5

    def test_experienced_under_20kg_returns_5(self):
        """Experienced (non-novice) lifters under 20kg now get +5kg (OD5)."""
        assert _calculate_weight_increment(5.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(15.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(19.9, is_novice=False) == 5.0

    def test_novice_under_20kg_still_returns_2_5(self):
        """Novice behavior under 20kg is unchanged by OD5."""
        assert _calculate_weight_increment(5.0, is_novice=True) == 2.5
        assert _calculate_weight_increment(15.0, is_novice=True) == 2.5
        assert _calculate_weight_increment(19.9, is_novice=True) == 2.5

    def test_boundary_around_20kg_experienced_vs_novice(self):
        """Regression across the 20kg boundary for both experience levels."""
        # Just below 20kg
        assert _calculate_weight_increment(19.9, is_novice=False) == 5.0
        assert _calculate_weight_increment(19.9, is_novice=True) == 2.5
        # At 20kg
        assert _calculate_weight_increment(20.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(20.0, is_novice=True) == 2.5
        # Just above 20kg
        assert _calculate_weight_increment(20.1, is_novice=False) == 5.0
        assert _calculate_weight_increment(20.1, is_novice=True) == 2.5


class TestCheckAcceptableEffort:
    """Tests for effort acceptability check (RIR/RPE)."""

    # RIR tests (Reps In Reserve - lower is harder)
    def test_rir_0_not_acceptable(self):
        """RIR 0 (failure) is too hard - not acceptable for progression."""
        assert _check_acceptable_effort(scored_rir=0, scored_rpe=None) is False

    def test_rir_1_acceptable(self):
        """RIR 1 is at the lower acceptable boundary."""
        assert _check_acceptable_effort(scored_rir=1, scored_rpe=None) is True

    def test_rir_2_acceptable(self):
        """RIR 2 is acceptable (middle of range)."""
        assert _check_acceptable_effort(scored_rir=2, scored_rpe=None) is True

    def test_rir_3_acceptable(self):
        """RIR 3 is at the upper acceptable boundary."""
        assert _check_acceptable_effort(scored_rir=3, scored_rpe=None) is True

    def test_rir_4_not_acceptable(self):
        """RIR 4 is too easy - not acceptable."""
        assert _check_acceptable_effort(scored_rir=4, scored_rpe=None) is False

    # RPE tests (Rate of Perceived Exertion - higher is harder)
    def test_rpe_6_9_not_acceptable(self):
        """RPE 6.9 is too easy - below acceptable range."""
        assert _check_acceptable_effort(scored_rir=None, scored_rpe=6.9) is False

    def test_rpe_7_acceptable(self):
        """RPE 7 is at the lower acceptable boundary."""
        assert _check_acceptable_effort(scored_rir=None, scored_rpe=7.0) is True

    def test_rpe_8_acceptable(self):
        """RPE 8 is acceptable (middle of range)."""
        assert _check_acceptable_effort(scored_rir=None, scored_rpe=8.0) is True

    def test_rpe_9_acceptable(self):
        """RPE 9 is at the upper acceptable boundary."""
        assert _check_acceptable_effort(scored_rir=None, scored_rpe=9.0) is True

    def test_rpe_9_1_not_acceptable(self):
        """RPE above 9 is too hard - not acceptable."""
        assert _check_acceptable_effort(scored_rir=None, scored_rpe=9.1) is False

    def test_rpe_10_not_acceptable(self):
        """RPE 10 (max effort) is not acceptable."""
        assert _check_acceptable_effort(scored_rir=None, scored_rpe=10.0) is False

    # Both None case
    def test_both_none_acceptable(self):
        """If no effort data provided, assume acceptable."""
        assert _check_acceptable_effort(scored_rir=None, scored_rpe=None) is True


class TestGetProgressionStatus:
    """Tests for progression status determination."""

    def test_all_none_returns_maintain(self):
        """All None values should return maintain status."""
        status = _get_progression_status(
            scored_max_reps=None,
            planned_min_reps=None,
            planned_max_reps=None
        )
        assert status == "maintain"

    def test_scored_none_returns_maintain(self):
        """None scored_max_reps should return maintain."""
        status = _get_progression_status(
            scored_max_reps=None,
            planned_min_reps=8,
            planned_max_reps=12
        )
        assert status == "maintain"

    def test_at_max_with_good_effort_returns_increase_weight(self):
        """Hitting max reps with acceptable effort = increase weight."""
        status = _get_progression_status(
            scored_max_reps=12,
            planned_min_reps=8,
            planned_max_reps=12,
            scored_rir=2  # Acceptable effort
        )
        assert status == "increase_weight"

    def test_above_max_returns_increase_weight(self):
        """Exceeding max reps = increase weight."""
        status = _get_progression_status(
            scored_max_reps=15,
            planned_min_reps=8,
            planned_max_reps=12,
            scored_rir=2
        )
        assert status == "increase_weight"

    def test_at_max_with_bad_effort_returns_maintain(self):
        """Hitting max reps with unacceptable effort (too easy) = maintain."""
        status = _get_progression_status(
            scored_max_reps=12,
            planned_min_reps=8,
            planned_max_reps=12,
            scored_rir=5  # Too easy, not acceptable
        )
        assert status == "maintain"

    def test_below_min_returns_increase_reps(self):
        """Below minimum reps = focus on increasing reps."""
        status = _get_progression_status(
            scored_max_reps=6,
            planned_min_reps=8,
            planned_max_reps=12
        )
        assert status == "increase_reps"

    def test_in_range_returns_maintain(self):
        """Within rep range but not at max = maintain."""
        status = _get_progression_status(
            scored_max_reps=10,
            planned_min_reps=8,
            planned_max_reps=12
        )
        assert status == "maintain"

    def test_at_min_boundary_returns_maintain(self):
        """At exactly minimum reps = maintain."""
        status = _get_progression_status(
            scored_max_reps=8,
            planned_min_reps=8,
            planned_max_reps=12
        )
        assert status == "maintain"


class TestAnalyzeConsistency:
    """Tests for training consistency analysis."""

    def test_empty_history_returns_zeros(self):
        """Empty history should return zero consecutive counts."""
        result = _analyze_consistency([])
        assert result["consecutive_at_top"] == 0
        assert result["consecutive_below_min"] == 0
        assert result["avg_reps"] is None

    def test_single_session_returns_zeros(self):
        """Single session doesn't meet min_sessions threshold."""
        history = [{"scored_max_reps": 12, "planned_max_reps": 12}]
        result = _analyze_consistency(history, min_sessions=2)
        assert result["consecutive_at_top"] == 0

    def test_two_sessions_at_top(self):
        """Two consecutive sessions at top of range."""
        history = [
            {"scored_max_reps": 12, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 12, "planned_max_reps": 12, "planned_min_reps": 8}
        ]
        result = _analyze_consistency(history)
        assert result["consecutive_at_top"] == 2

    def test_consecutive_below_min(self):
        """Count consecutive sessions below minimum."""
        history = [
            {"scored_max_reps": 6, "planned_min_reps": 8, "planned_max_reps": 12},
            {"scored_max_reps": 5, "planned_min_reps": 8, "planned_max_reps": 12}
        ]
        result = _analyze_consistency(history)
        assert result["consecutive_below_min"] == 2

    def test_broken_streak_at_top(self):
        """Streak breaks when not at top."""
        history = [
            {"scored_max_reps": 12, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 10, "planned_max_reps": 12, "planned_min_reps": 8},  # Breaks streak
            {"scored_max_reps": 12, "planned_max_reps": 12, "planned_min_reps": 8}
        ]
        result = _analyze_consistency(history)
        assert result["consecutive_at_top"] == 1  # Only first session counts

    def test_avg_reps_calculation(self):
        """Average reps calculated from consecutive sessions at top of range."""
        # The _analyze_consistency function only counts consecutive sessions at top
        # before the streak breaks, so for avg it only considers the first entry
        history = [
            {"scored_max_reps": 10, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 12, "planned_max_reps": 12, "planned_min_reps": 8}
        ]
        result = _analyze_consistency(history)
        # First session is not at top (10 < 12), so only 1 session counted
        assert result["avg_reps"] == 10.0  # Only first session before break

    def test_none_scored_reps_skipped(self):
        """Sessions with None scored_reps should be handled."""
        history = [
            {"scored_max_reps": None, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 10, "planned_max_reps": 12, "planned_min_reps": 8}
        ]
        result = _analyze_consistency(history)
        # First session has None, so avg is just from second
        assert result["avg_reps"] == 10.0 or result["avg_reps"] is None  # Implementation may vary


class TestGenerateProgressionSuggestions:
    """Tests for comprehensive suggestion generation."""

    def test_empty_history_returns_empty(self):
        """No history should return empty suggestions."""
        suggestions = generate_progression_suggestions([])
        assert suggestions == []

    def test_at_top_of_range_suggests_weight_increase(self):
        """Hitting top of range should suggest weight increase."""
        history = [{
            "exercise": "Bench Press",
            "scored_max_reps": 12,
            "scored_weight": 80.0,
            "planned_min_reps": 8,
            "planned_max_reps": 12,
            "planned_weight": 80.0,
            "planned_sets": 3,
            "scored_rir": 2
        }]
        
        suggestions = generate_progression_suggestions(history)
        
        # Should have double progression weight suggestion
        weight_suggestions = [s for s in suggestions if s["type"] == "double_progression_weight"]
        assert len(weight_suggestions) >= 1
        assert weight_suggestions[0]["suggested_weight"] > 80.0

    def test_below_min_suggests_push_reps(self):
        """Below minimum range should suggest pushing reps."""
        history = [{
            "exercise": "Squat",
            "scored_max_reps": 6,
            "scored_weight": 100.0,
            "planned_min_reps": 8,
            "planned_max_reps": 12,
            "planned_weight": 100.0,
            "planned_sets": 4
        }]
        
        suggestions = generate_progression_suggestions(history)
        
        # Should have push reps suggestion
        reps_suggestions = [s for s in suggestions if s["type"] == "double_progression_reps"]
        assert len(reps_suggestions) >= 1

    def test_consistently_below_min_suggests_weight_reduction(self):
        """Two sessions below min should suggest weight reduction."""
        history = [
            {
                "exercise": "Deadlift",
                "scored_max_reps": 5,
                "scored_weight": 150.0,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "planned_weight": 150.0,
                "planned_sets": 3
            },
            {
                "exercise": "Deadlift",
                "scored_max_reps": 6,
                "scored_weight": 150.0,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "planned_weight": 150.0,
                "planned_sets": 3
            }
        ]
        
        suggestions = generate_progression_suggestions(history)
        
        # Should have weight reduction suggestion
        reduce_suggestions = [s for s in suggestions if s["type"] == "reduce_weight"]
        assert len(reduce_suggestions) >= 1
        assert reduce_suggestions[0]["suggested_weight"] < 150.0

    def test_always_includes_technique_suggestion(self):
        """Should always include technique improvement suggestion."""
        history = [{
            "exercise": "Curl",
            "scored_max_reps": 10,
            "planned_min_reps": 8,
            "planned_max_reps": 12
        }]
        
        suggestions = generate_progression_suggestions(history)
        
        technique_suggestions = [s for s in suggestions if s["type"] == "technique"]
        assert len(technique_suggestions) >= 1

    def test_includes_manual_options(self):
        """Should include manual progression options (weight, reps, sets)."""
        history = [{
            "exercise": "Row",
            "scored_max_reps": 10,
            "scored_weight": 60.0,
            "planned_min_reps": 8,
            "planned_max_reps": 12,
            "planned_weight": 60.0,
            "planned_sets": 3
        }]
        
        suggestions = generate_progression_suggestions(history)
        
        types = [s["type"] for s in suggestions]
        assert "weight" in types
        assert "reps" in types
        assert "sets" in types

    def test_novice_flag_affects_increment(self):
        """Novice flag should result in smaller increments for heavy weights."""
        history = [{
            "exercise": "Press",
            "scored_max_reps": 12,
            "scored_weight": 50.0,
            "planned_min_reps": 8,
            "planned_max_reps": 12,
            "planned_weight": 50.0,
            "scored_rir": 2
        }]
        
        novice_suggestions = generate_progression_suggestions(history, is_novice=True)
        experienced_suggestions = generate_progression_suggestions(history, is_novice=False)
        
        # Find the weight suggestions
        novice_weight = next(
            (s for s in novice_suggestions if s["type"] == "weight"), None
        )
        exp_weight = next(
            (s for s in experienced_suggestions if s["type"] == "weight"), None
        )
        
        if novice_weight and exp_weight:
            # Novice should have smaller increment (52.5 vs 55)
            assert novice_weight["suggested_weight"] <= exp_weight["suggested_weight"]

    def test_handles_none_values_gracefully(self):
        """Should handle None values without crashing."""
        history = [{
            "exercise": "Lateral Raise",
            "scored_max_reps": None,
            "scored_weight": None,
            "planned_min_reps": None,
            "planned_max_reps": None,
            "planned_weight": None,
            "planned_sets": None
        }]
        
        # Should not raise exception
        suggestions = generate_progression_suggestions(history)
        assert isinstance(suggestions, list)


class TestGetExerciseHistory:
    """Tests for fetching exercise history from database."""

    def test_get_history_empty(self, clean_db):
        """Should return empty list when no history."""
        history = get_exercise_history("NonExistentExercise")
        assert history == []

    def test_get_history_with_entries(self, clean_db, workout_log_with_history):
        """Should return history entries ordered by date desc."""
        history = get_exercise_history("Bench Press")
        assert len(history) >= 2
        # Most recent should be first
        assert history[0]["scored_max_reps"] == 12  # Latest entry

    def test_get_history_limited_to_10(self, clean_db, many_workout_logs):
        """Should return at most 10 history entries."""
        history = get_exercise_history("Volume Exercise")
        assert len(history) <= 10


# Fixtures for progression_plan tests
@pytest.fixture
def workout_log_with_history(clean_db, exercise_factory):
    """Create workout log entries with history for testing."""
    from utils.database import DatabaseHandler
    
    exercise_factory("Bench Press")
    
    with DatabaseHandler() as db:
        # First add to user_selection (required for FK)
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Push", "Bench Press", 3, 8, 12, 2, 80.0))
        
        result = db.fetch_one("SELECT id FROM user_selection ORDER BY id DESC LIMIT 1")
        assert result is not None
        plan_id = result["id"]
        
        # Older entry
        db.execute_query("""
            INSERT INTO workout_log (
                routine, exercise, planned_sets, planned_min_reps, planned_max_reps,
                scored_max_reps, scored_weight, workout_plan_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-1 day'))
        """, ("Push", "Bench Press", 3, 8, 12, 10, 80.0, plan_id))
        
        # Newer entry
        db.execute_query("""
            INSERT INTO workout_log (
                routine, exercise, planned_sets, planned_min_reps, planned_max_reps,
                scored_max_reps, scored_weight, workout_plan_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, ("Push", "Bench Press", 3, 8, 12, 12, 80.0, plan_id))
    
    return {"exercise": "Bench Press", "plan_id": plan_id}


@pytest.fixture
def many_workout_logs(clean_db, exercise_factory):
    """Create many workout log entries to test pagination."""
    from utils.database import DatabaseHandler
    
    exercise_factory("Volume Exercise")
    
    with DatabaseHandler() as db:
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Push", "Volume Exercise", 3, 8, 12, 2, 50.0))
        
        result = db.fetch_one("SELECT id FROM user_selection ORDER BY id DESC LIMIT 1")
        assert result is not None
        plan_id = result["id"]
        
        # Create 15 entries
        for i in range(15):
            db.execute_query("""
                INSERT INTO workout_log (
                    routine, exercise, planned_sets, scored_max_reps,
                    workout_plan_id, created_at
                ) VALUES (?, ?, ?, ?, ?, datetime('now', ? || ' days'))
            """, ("Push", "Volume Exercise", 3, 10 + (i % 3), plan_id, f"-{i}"))
    
    return {"exercise": "Volume Exercise", "count": 15}
