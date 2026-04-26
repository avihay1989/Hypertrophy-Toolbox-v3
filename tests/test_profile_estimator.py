import pytest

from utils.database import upsert_user_profile_lift, upsert_user_profile_preference
from utils.profile_estimator import (
    KEY_LIFTS,
    classify_tier,
    epley_1rm,
    estimate_for_exercise,
    round_weight,
)


def _create_exercise(
    db,
    name,
    *,
    primary="Chest",
    equipment="Barbell",
    mechanic="Compound",
    movement_pattern=None,
):
    db.execute_query(
        """
        INSERT INTO exercises (
            exercise_name,
            primary_muscle_group,
            secondary_muscle_group,
            tertiary_muscle_group,
            force,
            equipment,
            mechanic,
            utility,
            difficulty,
            movement_pattern
        )
        VALUES (?, ?, 'Triceps', 'Front-Shoulder', 'Push', ?, ?, 'Basic', 'Intermediate', ?)
        """,
        (name, primary, equipment, mechanic, movement_pattern),
    )
    return name


def test_key_lifts_match_questionnaire_slugs():
    assert KEY_LIFTS == frozenset(
        {
            "barbell_bench_press",
            "barbell_back_squat",
            "romanian_deadlift",
            "triceps_extension",
            "barbell_bicep_curl",
            "dumbbell_lateral_raise",
            "military_press",
            "leg_curl",
            "leg_extension",
            "weighted_dips",
            "weighted_pullups",
            "bodyweight_pullups",
            "bodyweight_dips",
            "barbell_row",
        }
    )


def test_classify_tier_excludes_equipment_after_normalization():
    assert classify_tier({"exercise_name": "TRX Row", "equipment": "trx"}) == "excluded"


def test_classify_tier_uses_mechanic_and_movement_pattern_for_isolation():
    assert classify_tier({"exercise_name": "Cable Curl", "mechanic": "Isolation"}) == "isolated"
    assert (
        classify_tier({"exercise_name": "Leg Extension", "movement_pattern": "lower_isolation"})
        == "isolated"
    )


def test_classify_tier_uses_complex_allowlist_without_bare_clean_false_positive():
    assert classify_tier({"exercise_name": "Barbell Bench Press", "mechanic": "Compound"}) == "complex"
    assert classify_tier({"exercise_name": "Cable Clean Grip Row", "mechanic": "Compound"}) == "accessory"


def test_epley_1rm_clamps_high_reps_and_rejects_invalid_values():
    assert epley_1rm(100, 5) == pytest.approx(116.6667, rel=0.001)
    assert epley_1rm(100, 20) == pytest.approx(140.0)
    assert epley_1rm(100, 0) == 0.0
    assert epley_1rm(0, 10) == 0.0


def test_round_weight_uses_tier_aware_barbell_floor_and_dumbbell_floor():
    assert round_weight(5, "Barbell", "complex") == 20.0
    assert round_weight(11.526, "Barbell", "isolated") == 11.25
    assert round_weight(0.75, "Dumbbells", "isolated") == 1.0
    assert round_weight(8.24, "Dumbbells", "isolated") == 8.0


def test_estimate_for_exercise_uses_profile_lift_for_isolated_barbell(clean_db):
    _create_exercise(
        clean_db,
        "EZ Bar Preacher Curl",
        primary="Biceps",
        equipment="Barbell",
        mechanic="Isolation",
        movement_pattern="upper_isolation",
    )
    upsert_user_profile_lift("barbell_bicep_curl", 35, 8, db=clean_db)

    estimate = estimate_for_exercise("EZ Bar Preacher Curl", db=clean_db)

    assert estimate == {
        "weight": 11.25,
        "sets": 3,
        "min_rep": 10,
        "max_rep": 15,
        "rir": 2,
        "rpe": 7.5,
        "source": "profile",
        "reason": "profile",
    }


def test_estimate_for_exercise_respects_saved_tier_preference(clean_db):
    _create_exercise(clean_db, "Barbell Bench Press", primary="Chest", equipment="Barbell")
    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)
    upsert_user_profile_preference("complex", "moderate", db=clean_db)

    estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    assert estimate["weight"] == 90.0
    assert estimate["min_rep"] == 6
    assert estimate["max_rep"] == 8
    assert estimate["rir"] == 2
    assert estimate["rpe"] == 8.0
    assert estimate["reason"] == "profile"


def test_estimate_for_exercise_applies_cross_fallback_factor(clean_db):
    _create_exercise(
        clean_db,
        "Cable Tricep Pushdown",
        primary="Triceps",
        equipment="Cables",
        mechanic="Isolation",
        movement_pattern="upper_isolation",
    )
    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)

    estimate = estimate_for_exercise("Cable Tricep Pushdown", db=clean_db)

    assert estimate["weight"] == 18.0
    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile_cross"


def test_estimate_for_exercise_returns_default_for_excluded_equipment(clean_db):
    _create_exercise(clean_db, "TRX Row", primary="Upper Back", equipment="Trx")
    upsert_user_profile_lift("barbell_row", 100, 5, db=clean_db)

    estimate = estimate_for_exercise("TRX Row", db=clean_db)

    assert estimate["source"] == "default"
    assert estimate["reason"] == "default_excluded"
    assert estimate["weight"] == 25.0


def test_estimate_for_exercise_returns_default_when_muscle_has_no_reference(clean_db):
    _create_exercise(clean_db, "Standing Calf Raise", primary="Calves", equipment="Machine")

    estimate = estimate_for_exercise("Standing Calf Raise", db=clean_db)

    assert estimate["source"] == "default"
    assert estimate["reason"] == "default_no_reference"


def test_estimate_for_exercise_returns_default_when_exercise_is_missing(clean_db):
    estimate = estimate_for_exercise("Not A Real Exercise", db=clean_db)

    assert estimate["source"] == "default"
    assert estimate["reason"] == "default_missing"


def test_last_logged_set_wins_over_profile_estimate(
    clean_db, workout_plan_factory, workout_log_factory
):
    exercise = _create_exercise(clean_db, "Barbell Bench Press", primary="Chest")
    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)
    plan_id = workout_plan_factory(exercise_name=exercise, weight=80)
    workout_log_factory(
        plan_id=plan_id,
        exercise=exercise,
        planned_sets=4,
        planned_min_reps=6,
        planned_max_reps=8,
        planned_rir=2,
        planned_rpe=8.0,
        planned_weight=80.0,
        scored_min_reps=7,
        scored_max_reps=9,
        scored_rir=1,
        scored_rpe=9.0,
        scored_weight=82.5,
    )

    estimate = estimate_for_exercise(exercise, db=clean_db)

    assert estimate == {
        "weight": 82.5,
        "sets": 4,
        "min_rep": 7,
        "max_rep": 9,
        "rir": 1,
        "rpe": 9.0,
        "source": "log",
        "reason": "log",
    }


def test_bodyweight_reference_copies_reps_and_zero_weight(clean_db):
    _create_exercise(
        clean_db,
        "Pull Up",
        primary="Latissimus Dorsi",
        equipment="Bodyweight",
        mechanic="Compound",
    )
    upsert_user_profile_lift("bodyweight_pullups", 0, 12, db=clean_db)

    estimate = estimate_for_exercise("Pull Up", db=clean_db)

    assert estimate["weight"] == 0.0
    assert estimate["min_rep"] == 12
    assert estimate["max_rep"] == 12
    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile_cross"
