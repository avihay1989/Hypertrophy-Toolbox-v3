"""Tests for double progression logic in progression_plan.py."""
from utils.progression_plan import (
    generate_progression_suggestions,
    _calculate_weight_increment,
    _check_acceptable_effort,
    _get_progression_status,
    _analyze_consistency,
)


class TestWeightIncrement:
    """Tests for weight increment calculation."""
    
    def test_light_weight_increment(self):
        """Under 20kg should get 2.5kg increment."""
        assert _calculate_weight_increment(15.0) == 2.5
        assert _calculate_weight_increment(10.0) == 2.5
        assert _calculate_weight_increment(19.9) == 2.5
    
    def test_heavy_weight_increment_non_novice(self):
        """20kg+ should get 5kg for non-novice."""
        assert _calculate_weight_increment(20.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(50.0, is_novice=False) == 5.0
    
    def test_heavy_weight_increment_novice(self):
        """Novices get conservative 2.5kg even for heavy weights."""
        assert _calculate_weight_increment(20.0, is_novice=True) == 2.5
        assert _calculate_weight_increment(50.0, is_novice=True) == 2.5

    def test_light_weight_increment_experienced(self):
        """Experienced lifters get +5kg below 20kg too (OD5)."""
        assert _calculate_weight_increment(15.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(10.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(19.9, is_novice=False) == 5.0

    def test_light_weight_increment_novice_unchanged(self):
        """Novice behavior below 20kg is unchanged by OD5."""
        assert _calculate_weight_increment(15.0, is_novice=True) == 2.5
        assert _calculate_weight_increment(19.9, is_novice=True) == 2.5

    def test_weight_increment_boundary_20kg_both_experience_levels(self):
        """At the 20kg boundary, both experience levels keep existing behavior."""
        assert _calculate_weight_increment(20.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(20.0, is_novice=True) == 2.5

    def test_weight_increment_just_below_and_above_20kg_experienced(self):
        """Experienced lifters get 5kg on both sides of the 20kg boundary now."""
        assert _calculate_weight_increment(19.9, is_novice=False) == 5.0
        assert _calculate_weight_increment(20.0, is_novice=False) == 5.0
        assert _calculate_weight_increment(20.1, is_novice=False) == 5.0


class TestAcceptableEffort:
    """Tests for effort acceptability check."""
    
    def test_acceptable_rir(self):
        """RIR 1-3 is acceptable."""
        assert _check_acceptable_effort(1, None) is True
        assert _check_acceptable_effort(2, None) is True
        assert _check_acceptable_effort(3, None) is True
    
    def test_unacceptable_rir_too_easy(self):
        """RIR > 3 (too easy) is not acceptable for progression."""
        assert _check_acceptable_effort(4, None) is False
        assert _check_acceptable_effort(5, None) is False
    
    def test_unacceptable_rir_grinding(self):
        """RIR 0 (grinding) is not acceptable."""
        assert _check_acceptable_effort(0, None) is False
    
    def test_acceptable_rpe(self):
        """RPE 7-9 is acceptable."""
        assert _check_acceptable_effort(None, 7.0) is True
        assert _check_acceptable_effort(None, 8.0) is True
        assert _check_acceptable_effort(None, 9.0) is True
    
    def test_unacceptable_rpe(self):
        """RPE outside 7-9 is not acceptable."""
        assert _check_acceptable_effort(None, 6.0) is False
        assert _check_acceptable_effort(None, 10.0) is False
    
    def test_no_effort_data_acceptable(self):
        """No effort data defaults to acceptable."""
        assert _check_acceptable_effort(None, None) is True


class TestProgressionStatus:
    """Tests for progression status determination."""
    
    def test_increase_weight_when_at_top(self):
        """Should suggest weight increase when at top of rep range."""
        status = _get_progression_status(
            scored_max_reps=12,
            planned_min_reps=8,
            planned_max_reps=12,
            scored_rir=2,
        )
        assert status == "increase_weight"
    
    def test_increase_weight_above_top(self):
        """Should suggest weight increase when exceeding top of rep range."""
        status = _get_progression_status(
            scored_max_reps=14,
            planned_min_reps=8,
            planned_max_reps=12,
            scored_rir=2,
        )
        assert status == "increase_weight"
    
    def test_increase_reps_when_below_min(self):
        """Should suggest pushing reps when below minimum."""
        status = _get_progression_status(
            scored_max_reps=6,
            planned_min_reps=8,
            planned_max_reps=12,
        )
        assert status == "increase_reps"
    
    def test_maintain_when_in_range(self):
        """Should maintain when in range but not at top."""
        status = _get_progression_status(
            scored_max_reps=10,
            planned_min_reps=8,
            planned_max_reps=12,
        )
        assert status == "maintain"
    
    def test_maintain_when_effort_unacceptable(self):
        """Should not suggest weight increase if effort was too easy."""
        status = _get_progression_status(
            scored_max_reps=12,
            planned_min_reps=8,
            planned_max_reps=12,
            scored_rir=5,  # Too easy
        )
        assert status == "maintain"  # Not increase_weight because effort wasn't hard enough
    
    def test_missing_data_returns_maintain(self):
        """Missing data should default to maintain."""
        assert _get_progression_status(None, 8, 12) == "maintain"
        assert _get_progression_status(10, None, 12) == "maintain"
        assert _get_progression_status(10, 8, None) == "maintain"


class TestConsistencyAnalysis:
    """Tests for training consistency analysis."""
    
    def test_consecutive_at_top(self):
        """Should count consecutive sessions at top of range."""
        history = [
            {"scored_max_reps": 12, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 12, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 10, "planned_max_reps": 12, "planned_min_reps": 8},
        ]
        result = _analyze_consistency(history)
        assert result["consecutive_at_top"] == 2
    
    def test_consecutive_below_min(self):
        """Should count consecutive sessions below minimum."""
        history = [
            {"scored_max_reps": 5, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 6, "planned_max_reps": 12, "planned_min_reps": 8},
            {"scored_max_reps": 10, "planned_max_reps": 12, "planned_min_reps": 8},
        ]
        result = _analyze_consistency(history)
        assert result["consecutive_below_min"] == 2
    
    def test_insufficient_history(self):
        """Should return zeros for insufficient history."""
        result = _analyze_consistency([{"scored_max_reps": 10}])
        assert result["consecutive_at_top"] == 0
        assert result["consecutive_below_min"] == 0


class TestProgressionSuggestions:
    """Integration tests for suggestion generation."""
    
    def test_weight_increase_suggestion(self):
        """Should suggest weight increase when hitting top of range."""
        history = [
            {
                "exercise": "Bench Press",
                "scored_max_reps": 12,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "scored_weight": 60.0,
                "scored_rir": 2,
                "planned_sets": 3,
            }
        ]
        
        suggestions = generate_progression_suggestions(history, is_novice=False)
        
        # Should have a double_progression_weight suggestion
        weight_suggestions = [s for s in suggestions if s["type"] == "double_progression_weight"]
        assert len(weight_suggestions) == 1
        assert "65" in weight_suggestions[0]["description"]  # 60 + 5kg
    
    def test_push_reps_suggestion(self):
        """Should suggest pushing reps when below minimum."""
        history = [
            {
                "exercise": "Squat",
                "scored_max_reps": 6,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "scored_weight": 80.0,
                "planned_sets": 3,
            }
        ]
        
        suggestions = generate_progression_suggestions(history)
        
        # Should have a push reps suggestion
        reps_suggestions = [s for s in suggestions if s["type"] == "double_progression_reps"]
        assert len(reps_suggestions) == 1
        assert "below" in reps_suggestions[0]["description"].lower()
    
    def test_maintain_suggestion(self):
        """Should suggest maintaining when in range but not at top."""
        history = [
            {
                "exercise": "Deadlift",
                "scored_max_reps": 10,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "scored_weight": 100.0,
                "planned_sets": 3,
            }
        ]
        
        suggestions = generate_progression_suggestions(history)
        
        # Should have a maintain_progress suggestion
        maintain_suggestions = [s for s in suggestions if s["type"] == "maintain_progress"]
        assert len(maintain_suggestions) == 1
    
    def test_reduce_weight_suggestion_repeated_failure(self):
        """Should suggest weight reduction after consecutive failures."""
        history = [
            {
                "exercise": "OHP",
                "scored_max_reps": 5,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "scored_weight": 50.0,
                "planned_sets": 3,
            },
            {
                "exercise": "OHP",
                "scored_max_reps": 5,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "scored_weight": 50.0,
                "planned_sets": 3,
            },
        ]
        
        suggestions = generate_progression_suggestions(history)

        # Should have a reduce_weight suggestion
        reduce_suggestions = [s for s in suggestions if s["type"] == "reduce_weight"]
        assert len(reduce_suggestions) == 1

    def test_reduce_weight_decrement_experienced_below_20kg(self):
        """OD5 side effect: the reduce-weight DECREMENT is also 5kg for
        experienced lifters below 20kg (novice stays 2.5kg)."""
        def make_history():
            return [
                {
                    "exercise": "Lateral Raise",
                    "scored_max_reps": 5,
                    "planned_min_reps": 8,
                    "planned_max_reps": 12,
                    "scored_weight": 10.0,
                    "planned_sets": 3,
                }
                for _ in range(2)
            ]

        experienced = generate_progression_suggestions(make_history(), is_novice=False)
        reduce_exp = [s for s in experienced if s["type"] == "reduce_weight"]
        assert len(reduce_exp) == 1
        assert reduce_exp[0]["suggested_weight"] == 5.0  # 10 - 5.0 (was 7.5 pre-OD5)

        novice = generate_progression_suggestions(make_history(), is_novice=True)
        reduce_nov = [s for s in novice if s["type"] == "reduce_weight"]
        assert len(reduce_nov) == 1
        assert reduce_nov[0]["suggested_weight"] == 7.5  # 10 - 2.5, unchanged

    def test_empty_history(self):
        """Should return empty list for empty history."""
        suggestions = generate_progression_suggestions([])
        assert suggestions == []
    
    def test_technique_suggestion_always_present(self):
        """Technique suggestion should always be included."""
        history = [
            {
                "exercise": "Pull-up",
                "scored_max_reps": 10,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "scored_weight": 0.0,
                "planned_sets": 3,
            }
        ]
        
        suggestions = generate_progression_suggestions(history)
        
        technique_suggestions = [s for s in suggestions if s["type"] == "technique"]
        assert len(technique_suggestions) == 1
    
    def test_suggestions_have_priority(self):
        """All suggestions should have a priority field."""
        history = [
            {
                "exercise": "Row",
                "scored_max_reps": 12,
                "planned_min_reps": 8,
                "planned_max_reps": 12,
                "scored_weight": 40.0,
                "planned_sets": 3,
            }
        ]
        
        suggestions = generate_progression_suggestions(history)
        
        for suggestion in suggestions:
            assert "priority" in suggestion
            assert suggestion["priority"] in ("low", "medium", "high")
