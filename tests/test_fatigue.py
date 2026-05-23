"""Unit tests for the Phase 1 + Phase 2 fatigue-meter math module."""
import logging
from datetime import date

import pytest

from utils.fatigue import (
    DEFAULT_INTENSITY_MULTIPLIER,
    DEFAULT_LOAD_MULTIPLIER,
    DEFAULT_PATTERN_WEIGHT,
    DEFAULT_PERIOD,
    INTENSITY_MULTIPLIER_BUCKETS,
    MUSCLE_CONTRIBUTION_WEIGHTS,
    MUSCLE_VOLUME_LANDMARKS,
    PERIOD_LABELS,
    SFR_FATIGUE_ZERO_SENTINEL,
    SessionFatigueResult,
    UNASSIGNED_MUSCLE_BUCKET,
    VALID_PERIODS,
    WeeklyFatigueResult,
    adapt_logged_row,
    aggregate_logged_muscles,
    aggregate_muscles_for_session,
    aggregate_session_fatigue,
    aggregate_weekly_fatigue,
    calculate_set_fatigue,
    canonicalize_muscle_for_fatigue,
    classify_muscle_fatigue,
    classify_session_fatigue,
    classify_weekly_fatigue,
    compute_period_window,
    compute_sfr,
    filter_rows_by_date_window,
    muscle_percent_of_mrv,
    normalize_period,
    summarize_muscle_bars,
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


# =============================================================================
# Phase 2 — per-muscle / period / SFR
# =============================================================================


class TestCanonicalizeMuscleForFatigue:
    """Re-uses volume_taxonomy.COARSE_TO_BASIC except for the Unassigned override."""

    def test_unassigned_stays_its_own_bucket(self):
        # The load-bearing invariant: Stage 1 cleanup routed Unassigned to
        # Abdominals in volume_taxonomy ONLY to keep the volume-rollup
        # invariant satisfied; fatigue must not follow that mapping.
        assert canonicalize_muscle_for_fatigue("Unassigned") == "Unassigned"
        assert canonicalize_muscle_for_fatigue("Unassigned") != "Abdominals"

    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("Chest", "Chest"),
            ("Gluteus Maximus", "Glutes"),
            ("Latissimus Dorsi", "Latissimus-Dorsi"),
            ("Rectus Abdominis", "Abdominals"),
            ("External Obliques", "Abdominals"),
            ("Abs/Core", "Abdominals"),
            ("Trapezius", "Traps"),
            ("Upper Traps", "Traps"),
            ("Upper Back", "Middle-Traps"),
            ("Back", "Latissimus-Dorsi"),
            ("Shoulders", "Front-Shoulder"),
            ("Front-Shoulder", "Front-Shoulder"),
            ("Rear-Shoulder", "Rear-Shoulder"),
            ("Middle-Shoulder", "Middle-Shoulder"),
        ],
    )
    def test_alias_mapping_matches_volume_taxonomy(self, raw, canonical):
        assert canonicalize_muscle_for_fatigue(raw) == canonical

    def test_unknown_label_passes_through_verbatim(self):
        # Unknown labels surface as their own bars rather than being silently
        # absorbed into something else.
        assert canonicalize_muscle_for_fatigue("Hypothetical-Future-Muscle") == "Hypothetical-Future-Muscle"

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_null_and_empty_return_none(self, value):
        assert canonicalize_muscle_for_fatigue(value) is None


class TestAggregateMusclesForSession:
    """Planned-side per-muscle fatigue accumulator."""

    def test_single_exercise_primary_only(self):
        exercises = [{
            "sets": 3,
            "movement_pattern": "horizontal_push",
            "min_reps": 8,
            "max_reps": 12,
            "rir": 2,
            "primary_muscle_group": "Chest",
            "secondary_muscle_group": None,
            "tertiary_muscle_group": None,
        }]

        totals = aggregate_muscles_for_session(exercises)

        # set_fatigue = 1.2 (h_push) * 1.1 (avg 10 reps) * 1.25 (RIR 2) = 1.65
        # exercise_fatigue = 1.65 * 3 sets = 4.95
        # Chest gets primary weight 1.0 → 4.95
        assert totals == {"Chest": pytest.approx(4.95)}

    def test_primary_secondary_tertiary_weighting(self):
        exercises = [{
            "sets": 2,
            "movement_pattern": "vertical_push",
            "min_reps": 6,
            "max_reps": 8,
            "rir": 0,
            "primary_muscle_group": "Middle-Shoulder",
            "secondary_muscle_group": "Triceps",
            "tertiary_muscle_group": "Chest",
        }]

        totals = aggregate_muscles_for_session(exercises)

        # set_fatigue = 1.3 (vertical_push) * 1.1 (avg 7 reps) * 2.0 (RIR 0) = 2.86
        # exercise_fatigue = 2.86 * 2 sets = 5.72
        per_set = 1.3 * 1.1 * 2.0
        exercise_fatigue = per_set * 2
        assert totals["Middle-Shoulder"] == pytest.approx(exercise_fatigue * 1.0)
        assert totals["Triceps"] == pytest.approx(exercise_fatigue * 0.5)
        assert totals["Chest"] == pytest.approx(exercise_fatigue * 0.25)

    def test_overlapping_muscles_sum_across_exercises(self):
        exercises = [
            {
                "sets": 3, "movement_pattern": "horizontal_push",
                "min_reps": 8, "max_reps": 12, "rir": 2,
                "primary_muscle_group": "Chest",
            },
            {
                "sets": 2, "movement_pattern": "upper_isolation",
                "min_reps": 12, "max_reps": 15, "rir": 1,
                "primary_muscle_group": "Triceps",
                "secondary_muscle_group": "Chest",
            },
        ]

        totals = aggregate_muscles_for_session(exercises)

        # Exercise 1: 1.2 * 1.1 * 1.25 = 1.65/set * 3 = 4.95 → Chest +4.95
        # Exercise 2: 0.8 * 1.0 * 1.5 = 1.2/set * 2 = 2.4 → Triceps +2.4,
        #             Chest +2.4*0.5 = +1.2
        assert totals["Chest"] == pytest.approx(4.95 + 1.2)
        assert totals["Triceps"] == pytest.approx(2.4)

    def test_alias_normalization_folds_through(self):
        # Two exercises whose raw labels resolve to the same canonical bucket
        # via canonicalize_muscle_for_fatigue must sum.
        exercises = [
            {
                "sets": 2, "movement_pattern": "lower_isolation",
                "min_reps": 8, "max_reps": 10, "rir": 2,
                "primary_muscle_group": "Gluteus Maximus",
            },
            {
                "sets": 2, "movement_pattern": "lower_isolation",
                "min_reps": 8, "max_reps": 10, "rir": 2,
                "primary_muscle_group": "Glutes",
            },
        ]
        totals = aggregate_muscles_for_session(exercises)
        # Both Gluteus Maximus and Glutes canonicalize to "Glutes".
        assert "Gluteus Maximus" not in totals
        assert "Glutes" in totals

    def test_zero_sets_skipped(self):
        exercises = [{
            "sets": 0,
            "movement_pattern": "horizontal_push",
            "min_reps": 8, "max_reps": 12, "rir": 2,
            "primary_muscle_group": "Chest",
        }]
        assert aggregate_muscles_for_session(exercises) == {}

    def test_null_secondary_and_tertiary_contribute_nothing(self):
        exercises = [{
            "sets": 1, "movement_pattern": "upper_isolation",
            "min_reps": 10, "max_reps": 10, "rir": 2,
            "primary_muscle_group": "Biceps",
            "secondary_muscle_group": None,
            "tertiary_muscle_group": "",
        }]
        totals = aggregate_muscles_for_session(exercises)
        assert list(totals) == ["Biceps"]

    def test_empty_input_returns_empty_dict(self):
        assert aggregate_muscles_for_session([]) == {}

    def test_aliased_column_names(self):
        # The aggregator accepts user_selection's `min_rep_range` /
        # `max_rep_range` aliases used by Phase 1 fatigue_data.
        exercises = [{
            "sets": 3,
            "movement_pattern": "horizontal_push",
            "min_rep_range": 8, "max_rep_range": 12, "rir": 2,
            "primary_muscle_group": "Chest",
        }]
        totals = aggregate_muscles_for_session(exercises)
        assert totals == {"Chest": pytest.approx(4.95)}


class TestUnassignedIsItsOwnBucket:
    """The load-bearing Stage 2 invariant — guarded by an explicit test class."""

    def test_unassigned_primary_routes_to_unassigned_not_abdominals(self):
        exercises = [{
            "sets": 3, "movement_pattern": "core_static",
            "min_reps": 10, "max_reps": 10, "rir": 3,
            "primary_muscle_group": "Unassigned",
        }]
        totals = aggregate_muscles_for_session(exercises)
        assert "Unassigned" in totals
        assert totals.get("Abdominals", 0.0) == 0.0
        assert totals.get(UNASSIGNED_MUSCLE_BUCKET) == totals["Unassigned"]

    def test_unassigned_and_real_abdominals_remain_separate(self):
        exercises = [
            {
                "sets": 3, "movement_pattern": "core_static",
                "min_reps": 10, "max_reps": 10, "rir": 3,
                "primary_muscle_group": "Unassigned",
            },
            {
                "sets": 3, "movement_pattern": "core_static",
                "min_reps": 10, "max_reps": 10, "rir": 3,
                "primary_muscle_group": "Rectus Abdominis",
            },
        ]
        totals = aggregate_muscles_for_session(exercises)
        assert "Unassigned" in totals
        assert "Abdominals" in totals
        # Identical inputs → identical bucket scores; if Unassigned was being
        # folded into Abdominals we would see Abdominals == 2x the per-row score.
        assert totals["Unassigned"] == pytest.approx(totals["Abdominals"])

    def test_null_primary_routes_to_unassigned_and_warns(self, caplog):
        caplog.set_level(logging.WARNING, logger="hypertrophy_toolbox")

        exercises = [{
            "sets": 1, "movement_pattern": "upper_isolation",
            "min_reps": 10, "max_reps": 10, "rir": 2,
            "primary_muscle_group": None,
        }]
        totals = aggregate_muscles_for_session(exercises)

        assert "Unassigned" in totals
        assert totals.get("Abdominals", 0.0) == 0.0
        assert "NULL/empty primary_muscle_group" in caplog.text


class TestClassifyMuscleFatigue:
    """Per-muscle bands use §5 landmarks (12 muscles) with upper-exclusive boundaries."""

    @pytest.mark.parametrize(
        ("score", "band"),
        [
            (0.0, "light"),       # Chest MEV is 8 → below = light
            (7.99, "light"),
            (8.0, "moderate"),    # at MEV → moderate
            (12.0, "moderate"),   # in MAV
            (15.99, "moderate"),
            (16.0, "heavy"),      # at MAV_high → heavy
            (21.99, "heavy"),
            (22.0, "very_heavy"), # at MRV → very_heavy
            (40.0, "very_heavy"),
        ],
    )
    def test_chest_bands(self, score, band):
        assert classify_muscle_fatigue("Chest", score) == band

    def test_muscles_without_landmarks_return_none(self):
        # The six catalog labels deliberately left out of §5 (per Stage 2 plan).
        for muscle in ("Front-Shoulder", "Rear-Shoulder", "Lower Back",
                       "Hip-Adductors", "Middle-Traps", "Neck",
                       UNASSIGNED_MUSCLE_BUCKET):
            assert classify_muscle_fatigue(muscle, 50.0) is None

    def test_all_twelve_landmarked_muscles_classify(self):
        # Every landmarked muscle classifies above MRV as very_heavy. Muscles
        # with MEV == 0 (Glutes, Abdominals, Traps, Forearms) classify a
        # zero score as "moderate" (at MEV), not "light" — there's no room
        # below MEV to be light. That's intentional per the §5 table.
        for muscle, (mev, _mav_lo, _mav_hi, mrv) in MUSCLE_VOLUME_LANDMARKS.items():
            assert classify_muscle_fatigue(muscle, mrv + 1) == "very_heavy"
            if mev > 0:
                assert classify_muscle_fatigue(muscle, 0.0) == "light"
            else:
                assert classify_muscle_fatigue(muscle, 0.0) == "moderate"


class TestMusclePercentOfMRV:
    def test_landmarked_muscle_returns_percentage(self):
        # Chest MRV is 22 → 11/22 = 50%.
        assert muscle_percent_of_mrv("Chest", 11.0) == pytest.approx(50.0)

    def test_no_landmarks_returns_none(self):
        assert muscle_percent_of_mrv(UNASSIGNED_MUSCLE_BUCKET, 50.0) is None
        assert muscle_percent_of_mrv("Lower Back", 50.0) is None

    def test_percentages_can_exceed_one_hundred(self):
        # Very_heavy muscles legitimately exceed 100% of MRV.
        assert muscle_percent_of_mrv("Chest", 33.0) == pytest.approx(150.0)


class TestSummarizeMuscleBars:
    def test_landmarked_muscles_sorted_by_percent_of_mrv_desc(self):
        # Chest MRV 22, Biceps MRV 26: 11/22=50%, 13/26=50%, but Chest comes
        # first alphabetically when ties.
        rows = summarize_muscle_bars({"Biceps": 6.5, "Chest": 11.0, "Triceps": 9.0})
        # Triceps MRV 18 → 9/18 = 50%; ties broken by score (Chest 11 > Triceps 9 > Biceps 6.5).
        names = [r.muscle for r in rows]
        # All three are 50% so score-descending: Chest 11, Triceps 9, Biceps 6.5
        assert names == ["Chest", "Triceps", "Biceps"]

    def test_unassigned_sorted_to_bottom_alongside_other_no_landmark(self):
        rows = summarize_muscle_bars({
            "Chest": 5.0,                       # 23% MRV
            UNASSIGNED_MUSCLE_BUCKET: 9999.0,   # no landmarks → bottom
            "Lower Back": 9999.0,               # no landmarks → bottom
            "Biceps": 13.0,                     # 50% MRV
        })
        names = [r.muscle for r in rows]
        # Landmarked first by %MRV desc: Biceps (50%), Chest (23%).
        # Then no-landmark by score desc, alphabetical tiebreak: Lower Back, Unassigned (both 9999).
        assert names[:2] == ["Biceps", "Chest"]
        assert set(names[2:]) == {"Lower Back", UNASSIGNED_MUSCLE_BUCKET}
        # Verify no-landmark rows carry None for band + percent.
        for row in rows[2:]:
            assert row.band is None
            assert row.percent_of_mrv is None
            assert row.has_landmarks is False

    def test_empty_input_returns_empty_list(self):
        assert summarize_muscle_bars({}) == []


class TestNormalizePeriod:
    @pytest.mark.parametrize("value", VALID_PERIODS)
    def test_valid_periods_pass_through(self, value):
        assert normalize_period(value) == value

    @pytest.mark.parametrize("value", [None, "", "garbage", "1month", "WEEK"])
    def test_invalid_fallback_to_default(self, value):
        # "WEEK" is uppercase — only the exact lowercase tokens are accepted.
        assert normalize_period(value) == DEFAULT_PERIOD

    def test_default_period_is_this_week(self):
        assert DEFAULT_PERIOD == "this_week"

    def test_period_labels_cover_all_valid_periods(self):
        assert set(PERIOD_LABELS) == set(VALID_PERIODS)


class TestComputePeriodWindow:
    def test_this_week_returns_monday_through_sunday(self):
        # 2026-05-23 is a Saturday → ISO week starts Mon 2026-05-18.
        start, end = compute_period_window("this_week", date(2026, 5, 23))
        assert start == date(2026, 5, 18)
        assert end == date(2026, 5, 24)

    def test_this_week_on_monday(self):
        start, end = compute_period_window("this_week", date(2026, 5, 18))
        assert start == date(2026, 5, 18)
        assert end == date(2026, 5, 24)

    def test_last_4_weeks_returns_trailing_28_days_inclusive(self):
        start, end = compute_period_window("last_4_weeks", date(2026, 5, 23))
        assert start == date(2026, 4, 26)
        assert end == date(2026, 5, 23)
        assert (end - start).days == 27

    def test_this_session_uses_most_recent_logged_date(self):
        logged = ["2026-05-20 09:00:00", "2026-05-22 18:30:00", "2026-05-18"]
        start, end = compute_period_window("this_session", date(2026, 5, 23), logged)
        assert start == end == date(2026, 5, 22)

    def test_this_session_empty_logs_returns_none_pair(self):
        assert compute_period_window("this_session", date(2026, 5, 23), []) == (None, None)
        assert compute_period_window("this_session", date(2026, 5, 23), None) == (None, None)

    def test_unknown_period_falls_back_to_this_week(self):
        start, end = compute_period_window("garbage", date(2026, 5, 23))
        assert start == date(2026, 5, 18)
        assert end == date(2026, 5, 24)


class TestFilterRowsByDateWindow:
    def test_inclusive_bounds(self):
        rows = [
            {"created_at": "2026-05-17", "id": 1},
            {"created_at": "2026-05-18", "id": 2},
            {"created_at": "2026-05-24", "id": 3},
            {"created_at": "2026-05-25", "id": 4},
        ]
        kept = filter_rows_by_date_window(rows, date(2026, 5, 18), date(2026, 5, 24))
        assert [r["id"] for r in kept] == [2, 3]

    def test_null_dates_dropped(self):
        rows = [
            {"created_at": None},
            {"created_at": "garbage"},
            {"created_at": "2026-05-20 12:00:00"},
        ]
        kept = filter_rows_by_date_window(rows, date(2026, 5, 18), date(2026, 5, 24))
        assert len(kept) == 1

    def test_both_bounds_none_returns_empty(self):
        # Caller convention: (None, None) means "no window" → no rows.
        rows = [{"created_at": "2026-05-20"}]
        assert filter_rows_by_date_window(rows, None, None) == []


class TestAdaptLoggedRow:
    def _row(self, **overrides):
        defaults = {
            "planned_sets": 3,
            "planned_min_reps": 6, "planned_max_reps": 8, "planned_rir": 3,
            "scored_min_reps": 7, "scored_max_reps": 8, "scored_rir": 2,
            "scored_weight": 100.0,
            "movement_pattern": "horizontal_push",
            "primary_muscle_group": "Chest",
            "secondary_muscle_group": "Triceps",
            "tertiary_muscle_group": "Front-Shoulder",
        }
        defaults.update(overrides)
        return defaults

    def test_scored_values_take_precedence(self):
        adapted = adapt_logged_row(self._row())
        assert adapted["sets"] == 3
        assert adapted["rir"] == 2          # scored
        assert adapted["min_reps"] == 7     # scored
        assert adapted["max_reps"] == 8     # scored

    def test_falls_back_to_planned_for_missing_scored(self):
        adapted = adapt_logged_row(self._row(
            scored_rir=None, scored_min_reps=None, scored_max_reps=None,
            scored_weight=100.0,  # row still counts as logged
        ))
        assert adapted["rir"] == 3          # planned
        assert adapted["min_reps"] == 6
        assert adapted["max_reps"] == 8

    def test_all_scored_null_treats_as_skipped(self):
        adapted = adapt_logged_row(self._row(
            scored_rir=None, scored_min_reps=None,
            scored_max_reps=None, scored_weight=None,
        ))
        assert adapted["sets"] == 0

    def test_passes_through_muscle_columns(self):
        adapted = adapt_logged_row(self._row())
        assert adapted["primary_muscle_group"] == "Chest"
        assert adapted["secondary_muscle_group"] == "Triceps"
        assert adapted["tertiary_muscle_group"] == "Front-Shoulder"


class TestAggregateLoggedMuscles:
    def test_logged_rows_aggregate_per_muscle(self):
        rows = [{
            "planned_sets": 3,
            "scored_rir": 2, "scored_min_reps": 8, "scored_max_reps": 12,
            "scored_weight": 100.0,
            "movement_pattern": "horizontal_push",
            "primary_muscle_group": "Chest",
        }]
        totals = aggregate_logged_muscles(rows)
        # set_fatigue = 1.2 * 1.1 * 1.25 = 1.65; * 3 sets = 4.95
        assert totals == {"Chest": pytest.approx(4.95)}

    def test_skipped_row_contributes_zero(self):
        rows = [{
            "planned_sets": 3, "planned_rir": 2,
            "planned_min_reps": 8, "planned_max_reps": 12,
            "scored_rir": None, "scored_min_reps": None,
            "scored_max_reps": None, "scored_weight": None,
            "movement_pattern": "horizontal_push",
            "primary_muscle_group": "Chest",
        }]
        assert aggregate_logged_muscles(rows) == {}

    def test_empty_input_returns_empty(self):
        assert aggregate_logged_muscles([]) == {}

    def test_unassigned_in_logged_rows_stays_separate(self):
        # Belt-and-braces of TestUnassignedIsItsOwnBucket: confirm the
        # invariant also holds on the logged path.
        rows = [{
            "planned_sets": 2, "scored_rir": 2,
            "scored_min_reps": 10, "scored_max_reps": 10,
            "scored_weight": 0.0,
            "movement_pattern": "core_static",
            "primary_muscle_group": "Unassigned",
        }]
        totals = aggregate_logged_muscles(rows)
        assert "Unassigned" in totals
        assert totals.get("Abdominals", 0.0) == 0.0


class TestComputeSFR:
    def test_both_positive(self):
        assert compute_sfr(10.0, 5.0) == pytest.approx(2.0)

    def test_fatigue_zero_returns_sentinel(self):
        # §16.1 — never returns inf; sentinel is None so template renders "—".
        assert compute_sfr(10.0, 0.0) is SFR_FATIGUE_ZERO_SENTINEL
        assert compute_sfr(10.0, None) is SFR_FATIGUE_ZERO_SENTINEL

    def test_stimulus_zero_returns_zero(self):
        assert compute_sfr(0.0, 5.0) == 0.0
        assert compute_sfr(None, 5.0) == 0.0

    def test_negative_fatigue_treated_as_zero(self):
        # Defensive — negative fatigue shouldn't happen but must never explode.
        assert compute_sfr(10.0, -1.0) is SFR_FATIGUE_ZERO_SENTINEL


class TestMuscleContributionWeightsMirror:
    """Per-D2.9 / D2.4, fatigue per-muscle weights match effective_sets."""

    def test_ladder_matches_effective_sets(self):
        from utils.effective_sets import (
            MUSCLE_CONTRIBUTION_WEIGHTS as ES_WEIGHTS,
        )
        assert MUSCLE_CONTRIBUTION_WEIGHTS == ES_WEIGHTS
