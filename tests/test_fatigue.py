"""Unit tests for the Phase 1 fatigue-meter math module."""
import logging

import pytest

from utils.fatigue import (
    DEFAULT_INTENSITY_MULTIPLIER,
    DEFAULT_LOAD_MULTIPLIER,
    DEFAULT_PATTERN_WEIGHT,
    INTENSITY_MULTIPLIER_BUCKETS,
    SessionFatigueResult,
    WeeklyFatigueResult,
    aggregate_session_fatigue,
    aggregate_weekly_fatigue,
    calculate_set_fatigue,
    classify_session_fatigue,
    classify_weekly_fatigue,
)


class TestCalculateSetFatigue:
    """Per-single-set fatigue factors and fallback behavior."""

    def test_standard_inputs_match_hand_calculation(self):
        result = calculate_set_fatigue(
            movement_pattern="vertical_push",
            min_reps=8,
            max_reps=12,
            rir=2,
        )

        assert result.pattern_weight == pytest.approx(1.3)
        assert result.load_multiplier == pytest.approx(1.1)
        assert result.intensity_multiplier == pytest.approx(1.25)
        assert result.fatigue == pytest.approx(1.3 * 1.1 * 1.25)
        assert result.pattern_used == "vertical_push"
        assert result.rir_bucket == "2"

    def test_pattern_lookup_is_case_insensitive_and_trimmed(self):
        result = calculate_set_fatigue("  HORIZONTAL_PUSH  ", 8, 12, 2)

        assert result.pattern_weight == pytest.approx(1.2)
        assert result.pattern_used == "horizontal_push"

    @pytest.mark.parametrize(
        ("rir", "bucket", "multiplier"),
        [
            (0, "0", 2.0),
            (1, "1", 1.5),
            (2, "2", 1.25),
            (3, "3-4", 1.05),
            (4, "3-4", 1.05),
            (5, "5+", 1.0),
            (10, "5+", 1.0),
        ],
    )
    def test_rir_buckets(self, rir, bucket, multiplier):
        result = calculate_set_fatigue("upper_isolation", 8, 12, rir)

        assert result.rir_bucket == bucket
        assert result.intensity_multiplier == pytest.approx(multiplier)
        assert INTENSITY_MULTIPLIER_BUCKETS[bucket] == multiplier

    def test_rir_none_uses_neutral_default_and_warns(self, caplog):
        caplog.set_level(logging.WARNING, logger="hypertrophy_toolbox")

        result = calculate_set_fatigue("upper_isolation", 8, 12, None)

        assert result.intensity_multiplier == DEFAULT_INTENSITY_MULTIPLIER
        assert result.rir_bucket == "unknown"
        assert "RIR is NULL" in caplog.text

    def test_negative_rir_uses_neutral_default_and_warns(self, caplog):
        caplog.set_level(logging.WARNING, logger="hypertrophy_toolbox")

        result = calculate_set_fatigue("upper_isolation", 8, 12, -1)

        assert result.intensity_multiplier == DEFAULT_INTENSITY_MULTIPLIER
        assert result.rir_bucket == "unknown"
        assert "negative" in caplog.text

    @pytest.mark.parametrize(
        ("min_reps", "max_reps", "multiplier"),
        [
            (1, 5, 1.3),
            (6, 10, 1.1),
            (11, 15, 1.0),
            (16, 20, 0.95),
            (21, 30, 0.9),
            (None, 8, 1.1),
            (12, None, 1.0),
        ],
    )
    def test_rep_range_proxy_load_buckets(self, min_reps, max_reps, multiplier):
        result = calculate_set_fatigue("upper_isolation", min_reps, max_reps, 5)

        assert result.load_multiplier == pytest.approx(multiplier)

    def test_rep_range_none_uses_neutral_default(self):
        result = calculate_set_fatigue("upper_isolation", None, None, 5)

        assert result.load_multiplier == DEFAULT_LOAD_MULTIPLIER

    def test_pattern_none_uses_neutral_default_and_warns(self, caplog):
        caplog.set_level(logging.WARNING, logger="hypertrophy_toolbox")

        result = calculate_set_fatigue(None, 8, 12, 5)

        assert result.pattern_weight == DEFAULT_PATTERN_WEIGHT
        assert result.pattern_used == "unset"
        assert "movement_pattern is NULL" in caplog.text

    def test_unknown_pattern_uses_neutral_default_and_warns(self, caplog):
        caplog.set_level(logging.WARNING, logger="hypertrophy_toolbox")

        result = calculate_set_fatigue("not_a_pattern", 8, 12, 5)

        assert result.pattern_weight == DEFAULT_PATTERN_WEIGHT
        assert result.pattern_used == "unset"
        assert "unrecognized movement_pattern" in caplog.text


class TestAggregateSessionFatigue:
    """Session aggregation over raw set counts."""

    def test_empty_exercise_list_returns_zero_result(self):
        result = aggregate_session_fatigue([])

        assert result == SessionFatigueResult(
            score=0.0,
            band="light",
            exercise_count=0,
            set_count=0,
        )

    def test_single_exercise_uses_user_selection_rep_range_aliases(self):
        result = aggregate_session_fatigue(
            [
                {
                    "sets": 3,
                    "movement_pattern": "vertical_push",
                    "min_rep_range": 8,
                    "max_rep_range": 12,
                    "rir": 2,
                }
            ]
        )

        assert result.score == pytest.approx(3 * 1.3 * 1.1 * 1.25)
        assert result.exercise_count == 1
        assert result.set_count == 3

    def test_two_exercises_sum_correctly(self):
        result = aggregate_session_fatigue(
            [
                {
                    "sets": 3,
                    "movement_pattern": "vertical_push",
                    "min_reps": 8,
                    "max_reps": 12,
                    "rir": 2,
                },
                {
                    "sets": 2,
                    "movement_pattern": "upper_isolation",
                    "min_reps": 12,
                    "max_reps": 15,
                    "rir": 5,
                },
            ]
        )

        expected = (3 * 1.3 * 1.1 * 1.25) + (2 * 0.8 * 1.0 * 1.0)
        assert result.score == pytest.approx(expected)
        assert result.exercise_count == 2
        assert result.set_count == 5

    def test_same_exercise_listed_twice_is_not_deduplicated(self):
        row = {
            "sets": 3,
            "movement_pattern": "upper_isolation",
            "min_reps": 12,
            "max_reps": 15,
            "rir": 5,
        }

        result = aggregate_session_fatigue([row, row])

        assert result.score == pytest.approx(2 * 3 * 0.8)
        assert result.exercise_count == 2
        assert result.set_count == 6

    @pytest.mark.parametrize("sets", [0, -2, None, "not-a-number"])
    def test_zero_or_invalid_sets_contribute_no_fatigue(self, sets):
        result = aggregate_session_fatigue(
            [
                {
                    "sets": sets,
                    "movement_pattern": "hinge",
                    "min_reps": 1,
                    "max_reps": 5,
                    "rir": 0,
                }
            ]
        )

        assert result.score == 0.0
        assert result.exercise_count == 0
        assert result.set_count == 0

    def test_missing_muscle_keys_do_not_affect_phase1_global_score(self):
        result = aggregate_session_fatigue(
            [
                {
                    "sets": 4,
                    "movement_pattern": "upper_isolation",
                    "min_reps": 12,
                    "max_reps": 15,
                    "rir": 5,
                    "primary_muscle": None,
                    "secondary_muscle": None,
                    "tertiary_muscle": None,
                }
            ]
        )

        assert result.score == pytest.approx(4 * 0.8)
        assert result.exercise_count == 1

    def test_bodyweight_row_without_weight_uses_rep_range_proxy(self):
        result = aggregate_session_fatigue(
            [
                {
                    "sets": 3,
                    "movement_pattern": "vertical_pull",
                    "min_reps": 6,
                    "max_reps": 10,
                    "rir": 1,
                    "weight": None,
                }
            ]
        )

        assert result.score == pytest.approx(3 * 1.2 * 1.1 * 1.5)

    def test_worked_example_vertical_push_path_is_near_32(self):
        exercises = [
            {
                "sets": 3,
                "movement_pattern": "vertical_push",
                "min_reps": 8,
                "max_reps": 12,
                "rir": 2,
            }
            for _ in range(6)
        ]

        result = aggregate_session_fatigue(exercises)

        assert result.score == pytest.approx(32.18, abs=0.01)
        assert result.score == pytest.approx(32.0, abs=1.0)
        assert result.band == "moderate"


class TestAggregateWeeklyFatigue:
    """Weekly aggregation is a simple Phase 1 sum, with no decay."""

    def test_empty_session_list_returns_zero_result(self):
        result = aggregate_weekly_fatigue([])

        assert result == WeeklyFatigueResult(
            score=0,
            band="light",
            session_count=0,
        )

    def test_weekly_fatigue_sums_session_scores(self):
        sessions = [
            SessionFatigueResult(score=32.18, band="moderate", exercise_count=6, set_count=18),
            SessionFatigueResult(score=12.0, band="light", exercise_count=4, set_count=12),
        ]

        result = aggregate_weekly_fatigue(sessions)

        assert result.score == pytest.approx(44.18)
        assert result.band == "light"
        assert result.session_count == 2

    def test_weekly_fatigue_does_not_apply_decay_or_date_bucketing(self):
        sunday = SessionFatigueResult(score=79.0, band="heavy", exercise_count=5, set_count=15)
        monday = SessionFatigueResult(score=81.0, band="very_heavy", exercise_count=5, set_count=15)

        result = aggregate_weekly_fatigue([sunday, monday])

        assert result.score == pytest.approx(160.0)
        assert result.band == "moderate"
        assert result.session_count == 2


class TestFatigueClassification:
    """Band thresholds are lower-inclusive and upper-exclusive."""

    @pytest.mark.parametrize(
        ("score", "band"),
        [
            (0, "light"),
            (19.99, "light"),
            (20.0, "moderate"),
            (35.0, "moderate"),
            (49.99, "moderate"),
            (50.0, "heavy"),
            (65.0, "heavy"),
            (79.99, "heavy"),
            (80.0, "very_heavy"),
            (100.0, "very_heavy"),
        ],
    )
    def test_session_fatigue_bands(self, score, band):
        assert classify_session_fatigue(score) == band

    @pytest.mark.parametrize(
        ("score", "band"),
        [
            (0, "light"),
            (79.99, "light"),
            (80.0, "moderate"),
            (150.0, "moderate"),
            (199.99, "moderate"),
            (200.0, "heavy"),
            (260.0, "heavy"),
            (319.99, "heavy"),
            (320.0, "very_heavy"),
            (400.0, "very_heavy"),
        ],
    )
    def test_weekly_fatigue_bands(self, score, band):
        assert classify_weekly_fatigue(score) == band
