import pytest

from utils.database import (
    upsert_user_profile_demographics,
    upsert_user_profile_lift,
    upsert_user_profile_preference,
)
from utils.profile_estimator import (
    KEY_LIFT_LABELS,
    KEY_LIFT_SIDE,
    KEY_LIFT_TIER,
    KEY_LIFTS,
    classify_tier,
    cold_start_1rm,
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


def test_key_lifts_includes_split_and_added_questionnaire_slugs():
    # The original 14 slugs must all still be present (#9 keeps the
    # combined-half slug names; #6 and #9 add new ones beside them).
    legacy = {
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
    assert legacy.issubset(KEY_LIFTS)
    # Issue #9 splits.
    assert "conventional_deadlift" in KEY_LIFTS
    assert "dumbbell_bench_press" in KEY_LIFTS
    # A representative sampling of Issue #6 additions across muscle groups.
    for slug in (
        "incline_bench_press",
        "smith_machine_bench_press",
        "machine_chest_press",
        "dumbbell_fly",
        "machine_row",
        "bodyweight_chinups",
        "dumbbell_shoulder_press",
        "machine_shoulder_press",
        "arnold_press",
        "face_pulls",
        "barbell_shrugs",
        "dumbbell_curl",
        "preacher_curl",
        "incline_dumbbell_curl",
        "skull_crusher",
        "jm_press",
        "leg_press",
        "dumbbell_squat",
        "dumbbell_lunge",
        "dumbbell_step_up",
        "hip_thrust",
        "stiff_leg_deadlift",
        "good_morning",
        "single_leg_rdl",
        "standing_calf_raise",
        "machine_hip_abduction",
        "cable_crunch",
        "machine_crunch",
        "weighted_crunch",
        "cable_woodchop",
        "side_bend",
        "back_extension",
    ):
        assert slug in KEY_LIFTS


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
    # Issue #6 split preacher curl into its own slug; the old behavior of
    # routing "preacher curl" → barbell_bicep_curl is preserved as cross-
    # fallback, but the direct-match path now uses preacher_curl.
    upsert_user_profile_lift("preacher_curl", 35, 8, db=clean_db)

    estimate = estimate_for_exercise("EZ Bar Preacher Curl", db=clean_db)

    # Issue #14: iso→iso direct match no longer double-discounts via the
    # isolated tier ratio. Epley(35,8) ≈ 44.33; iso→iso multiplier = 1.0,
    # light pct_1rm = 0.65 → 28.82; barbell isolated rounding → 28.75.
    assert {k: v for k, v in estimate.items() if k != "trace"} == {
        "weight": 28.75,
        "sets": 3,
        "min_rep": 10,
        "max_rep": 15,
        "rir": 2,
        "rpe": 7.5,
        "source": "profile",
        "reason": "profile",
        "is_dumbbell": False,
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

    assert {k: v for k, v in estimate.items() if k != "trace"} == {
        "weight": 82.5,
        "sets": 4,
        "min_rep": 7,
        "max_rep": 9,
        "rir": 1,
        "rpe": 9.0,
        "source": "log",
        "reason": "log",
        "is_dumbbell": False,
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
    assert estimate["reason"] == "profile"


def test_direct_match_bypasses_cross_factor_for_romanian_deadlift(clean_db):
    _create_exercise(
        clean_db,
        "Barbell Romanian Deadlift",
        primary="Hamstrings",
        equipment="Barbell",
        mechanic="Compound",
        movement_pattern="hinge",
    )
    upsert_user_profile_lift("leg_curl", 60, 7, db=clean_db)
    upsert_user_profile_lift("romanian_deadlift", 120, 6, db=clean_db)

    estimate = estimate_for_exercise("Barbell Romanian Deadlift", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    assert estimate["weight"] == pytest.approx(122.5)


def test_conventional_deadlift_uses_dedicated_slug_not_romanian(clean_db):
    """Issue #9: Conventional Deadlift must use its own reference, not RDL.

    Both lifts are stored at different weights — the route should pick the
    conventional one without applying the cross-fallback factor.
    """
    _create_exercise(
        clean_db,
        "Conventional Deadlift",
        primary="Hamstrings",
        equipment="Barbell",
        mechanic="Compound",
        movement_pattern="hinge",
    )
    upsert_user_profile_lift("romanian_deadlift", 100, 5, db=clean_db)
    upsert_user_profile_lift("conventional_deadlift", 160, 5, db=clean_db)

    estimate = estimate_for_exercise("Conventional Deadlift", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    # Epley(160, 5) ≈ 186.67; complex tier × heavy preset (0.85) ≈ 158.67
    assert estimate["weight"] == pytest.approx(158.75, rel=0.01)


def test_dumbbell_bench_press_uses_dedicated_slug_not_barbell(clean_db):
    """Issue #9: Dumbbell Bench Press now has its own direct-match slug."""
    _create_exercise(
        clean_db,
        "Flat Dumbbell Bench Press",
        primary="Chest",
        equipment="Dumbbells",
        mechanic="Compound",
    )
    upsert_user_profile_lift("barbell_bench_press", 120, 5, db=clean_db)
    upsert_user_profile_lift("dumbbell_bench_press", 40, 8, db=clean_db)

    estimate = estimate_for_exercise("Flat Dumbbell Bench Press", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    # Epley(40, 8) ≈ 50.67; complex × heavy (0.85) ≈ 43.07 → dumbbell rounding
    # increment 1.0 (weight ≥ 10) → ~43.0
    assert estimate["weight"] == pytest.approx(43.0, abs=1.0)


def test_machine_chest_press_falls_back_to_barbell_with_cross_factor(clean_db):
    """Issue #6: machine variants without a stored reference fall through to
    barbell_bench_press (chain order) and get cross-factored."""
    _create_exercise(
        clean_db,
        "Machine Chest Press",
        primary="Chest",
        equipment="Machine",
        mechanic="Compound",
    )
    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)

    estimate = estimate_for_exercise("Machine Chest Press", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile_cross"
    # direct_lift_key = machine_chest_press (empty), chain falls to
    # barbell_bench_press cross-factored. Epley(100,5)≈116.67; tier
    # accessory (0.70) × 0.6 × moderate-default 0.77 ≈ 37.73 → machine
    # increment 1.0 → ~38 kg.
    assert estimate["weight"] == pytest.approx(38.0, abs=1.5)


def test_leg_press_direct_match_no_cross_factor(clean_db):
    _create_exercise(
        clean_db,
        "Leg Press",
        primary="Quadriceps",
        equipment="Machine",
        mechanic="Compound",
        movement_pattern="squat",
    )
    upsert_user_profile_lift("leg_press", 200, 8, db=clean_db)

    estimate = estimate_for_exercise("Leg Press", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"


def test_bodyweight_chinups_direct_match(clean_db):
    """Issue #6: 'Chin Up' bare names now route to bodyweight_chinups."""
    _create_exercise(
        clean_db,
        "Chin Up",
        primary="Latissimus Dorsi",
        equipment="Bodyweight",
        mechanic="Compound",
    )
    upsert_user_profile_lift("bodyweight_chinups", 0, 10, db=clean_db)

    estimate = estimate_for_exercise("Chin Up", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    assert estimate["weight"] == 0.0
    assert estimate["min_rep"] == 10
    assert estimate["max_rep"] == 10


def test_skull_crusher_direct_match_uses_complex_tier(clean_db):
    """Issue #6: skull crusher routes to its own slug, not triceps_extension.

    Skull Crusher is not in COMPLEX_ALLOWLIST so it stays accessory tier — but
    the direct-match means no cross_factor penalty.
    """
    _create_exercise(
        clean_db,
        "EZ Bar Skull Crusher",
        primary="Triceps",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_lift("triceps_extension", 30, 10, db=clean_db)
    upsert_user_profile_lift("skull_crusher", 50, 8, db=clean_db)

    estimate = estimate_for_exercise("EZ Bar Skull Crusher", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"


def test_stiff_leg_deadlift_classified_as_complex(clean_db):
    assert classify_tier(
        {"exercise_name": "Stiff-Leg Deadlift", "mechanic": "Compound"}
    ) == "complex"


def test_good_morning_classified_as_complex(clean_db):
    assert classify_tier(
        {"exercise_name": "Good Morning", "mechanic": "Compound"}
    ) == "complex"


def test_weighted_pull_ups_classified_as_complex(clean_db):
    _create_exercise(
        clean_db,
        "Weighted Pull Ups",
        primary="Latissimus Dorsi",
        equipment="Plate",
        mechanic="Compound",
        movement_pattern="vertical_pull",
    )
    upsert_user_profile_lift("weighted_pullups", 25, 6, db=clean_db)

    assert classify_tier(
        {"exercise_name": "Weighted Pull Ups", "mechanic": "Compound"}
    ) == "complex"

    estimate = estimate_for_exercise("Weighted Pull Ups", db=clean_db)
    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    assert estimate["min_rep"] == 4
    assert estimate["max_rep"] == 6
    assert estimate["rir"] == 1
    assert estimate["rpe"] == 9.0
    assert estimate["weight"] == pytest.approx(25.0)


def test_dumbbell_estimate_is_per_hand_and_flags_is_dumbbell(clean_db):
    """Issue #10: dumbbell weight convention is per hand.

    Inputs to the estimator are per-hand and outputs stay per-hand — the
    math chain is unit-agnostic, so a 40 kg-per-hand reference at 8 reps
    on dumbbell bench press should produce a per-hand working weight in
    the same scale (not doubled to total-load). Also asserts that the
    estimator flags ``is_dumbbell`` so the UI can surface the per-hand
    hint next to the Workout Controls weight field.
    """
    _create_exercise(
        clean_db,
        "Flat Dumbbell Bench Press",
        primary="Chest",
        equipment="Dumbbells",
        mechanic="Compound",
    )
    upsert_user_profile_lift("dumbbell_bench_press", 40, 8, db=clean_db)

    estimate = estimate_for_exercise("Flat Dumbbell Bench Press", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    assert estimate["is_dumbbell"] is True
    # Per-hand sanity: a 40 kg-per-hand reference must NOT come back as
    # ~80 kg+ (which is what'd happen if the estimator silently doubled
    # for total-load output). Allow a wide band so the assertion stays
    # robust to tier-ratio / pct_1rm tuning, but well below any doubling.
    assert estimate["weight"] < 60.0
    # Epley(40, 8) ≈ 50.67 → complex × heavy (0.85) ≈ 43.07 → dumbbell
    # round to nearest 1 kg → ~43.0.
    assert estimate["weight"] == pytest.approx(43.0, abs=1.0)


def test_key_lift_tier_covers_every_key_lift():
    """Issue #14: every reference lift slug must declare an implied tier so the
    normalised tier multiplier in `_estimate_from_profile` can resolve it.
    Missing entries silently default to ``"complex"`` (preserving the legacy
    behaviour) — this test prevents that drift from going unnoticed."""
    missing = KEY_LIFTS - set(KEY_LIFT_TIER.keys())
    assert not missing, f"KEY_LIFT_TIER missing tier for: {sorted(missing)}"


def test_key_lift_side_partitions_every_slug():
    """Issue #24: every slug in `KEY_LIFT_LABELS` must declare a side
    ("anterior" | "posterior") so the Profile-page questionnaire can
    render it on exactly one of the two side-by-side cards. Drift guard
    against future Issue #6-style additions silently being hidden from
    the questionnaire when an Issue #24-style refactor ships."""
    missing = set(KEY_LIFT_LABELS) - set(KEY_LIFT_SIDE)
    assert not missing, f"KEY_LIFT_SIDE missing side for: {sorted(missing)}"
    extra = set(KEY_LIFT_SIDE) - set(KEY_LIFT_LABELS)
    assert not extra, (
        f"KEY_LIFT_SIDE has slugs not in KEY_LIFT_LABELS: {sorted(extra)}"
    )
    invalid = {
        slug: side
        for slug, side in KEY_LIFT_SIDE.items()
        if side not in {"anterior", "posterior"}
    }
    assert not invalid, f"KEY_LIFT_SIDE has invalid sides: {invalid}"

    # Spot-check anatomically obvious anchors.
    assert KEY_LIFT_SIDE["barbell_bench_press"] == "anterior"
    assert KEY_LIFT_SIDE["barbell_back_squat"] == "anterior"
    assert KEY_LIFT_SIDE["dumbbell_curl"] == "anterior"
    assert KEY_LIFT_SIDE["barbell_row"] == "posterior"
    assert KEY_LIFT_SIDE["romanian_deadlift"] == "posterior"
    assert KEY_LIFT_SIDE["triceps_extension"] == "posterior"
    assert KEY_LIFT_SIDE["hip_thrust"] == "posterior"
    assert KEY_LIFT_SIDE["standing_calf_raise"] == "posterior"


def test_iso_to_iso_direct_match_no_longer_double_discounts(clean_db):
    """Issue #14 user reproduction: Dumbbell Incline Curl with a direct-match
    `incline_dumbbell_curl = 20 kg × 7` reference must NOT double-apply the
    isolated tier ratio.

    Before fix: 24.67 × 0.40 (iso) × 1.0 × 0.65 (light) = 6.41 → 6.5 kg.
    After fix:  24.67 × 1.00 (iso/iso) × 1.0 × 0.65 = 16.03 → 16.0 kg.
    """
    _create_exercise(
        clean_db,
        "Dumbbell Incline Curl",
        primary="Biceps",
        equipment="Dumbbells",
        mechanic="Isolation",
        movement_pattern="upper_isolation",
    )
    upsert_user_profile_lift("incline_dumbbell_curl", 20, 7, db=clean_db)

    estimate = estimate_for_exercise("Dumbbell Incline Curl", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    assert estimate["weight"] == pytest.approx(16.0, abs=1.0)


def test_iso_to_iso_cross_fallback_no_longer_double_discounts(clean_db):
    """Issue #14: same bug, cross-fallback path. The user's first
    reproduction had only `dumbbell_curl = 20 × 6` saved (no
    incline_dumbbell_curl), so the chain falls to dumbbell_curl with
    cross_factor=0.6.

    Before fix: 24 × 0.40 (iso) × 0.6 × 0.65 = 3.74 → 3.5 kg.
    After fix:  24 × 1.00 (iso/iso) × 0.6 × 0.65 = 9.36 → 9.0 kg.
    """
    _create_exercise(
        clean_db,
        "Dumbbell Incline Curl",
        primary="Biceps",
        equipment="Dumbbells",
        mechanic="Isolation",
        movement_pattern="upper_isolation",
    )
    upsert_user_profile_lift("dumbbell_curl", 20, 6, db=clean_db)

    estimate = estimate_for_exercise("Dumbbell Incline Curl", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile_cross"
    assert estimate["weight"] == pytest.approx(9.0, abs=1.0)


def test_complex_to_iso_cross_path_still_downscales(clean_db):
    """Issue #14 regression guard: cross-tier paths (e.g. iso target with
    a complex reference) must still downscale. Multiplier =
    min(0.40 / 1.00, 1.0) = 0.40 — unchanged from before the fix.
    """
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

    # Same expected weight as test_estimate_for_exercise_applies_cross_fallback_factor
    # — proves complex→iso cross paths are unchanged after the fix.
    assert estimate["weight"] == pytest.approx(18.0, abs=0.5)
    assert estimate["reason"] == "profile_cross"


@pytest.mark.parametrize(
    "name",
    [
        "Pull Ups",
        "Pull-Ups",
        "Pullup",
        "Pullups",
        "Chin Ups",
        "Chin-Ups",
        "Chinups",
        "Weighted Pull-Ups",
        "Weighted Pullups",
        "Weighted Chin Ups",
        "Hip Thrusts",
        "Stiff-Leg Deadlifts",
    ],
)
def test_complex_allowlist_matches_plural_and_hyphen_variants(name):
    """Issue #13: plural / hyphen variants of allowlist entries must classify
    as complex via name normalisation, without needing redundant per-variant
    entries in COMPLEX_ALLOWLIST."""
    assert (
        classify_tier({"exercise_name": name, "mechanic": "Compound"}) == "complex"
    )


def test_bodyweight_pull_up_uses_heavy_preset_rir_and_rpe(clean_db):
    """Issue #13: a bodyweight pull-up classified as complex must use the
    Heavy preset's RIR / RPE (1 / 9.0), not Moderate (2 / 8.0)."""
    _create_exercise(
        clean_db,
        "Pull Ups",
        primary="Latissimus Dorsi",
        equipment="Bodyweight",
        mechanic="Compound",
    )
    upsert_user_profile_lift("bodyweight_pullups", 0, 8, db=clean_db)

    estimate = estimate_for_exercise("Pull Ups", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    assert estimate["rir"] == 1
    assert estimate["rpe"] == 9.0


def test_non_dumbbell_estimate_does_not_flag_is_dumbbell(clean_db):
    """Issue #10: only Dumbbells-equipment exercises set is_dumbbell=True."""
    _create_exercise(
        clean_db,
        "Barbell Back Squat",
        primary="Quadriceps",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_lift("barbell_back_squat", 130, 6, db=clean_db)

    estimate = estimate_for_exercise("Barbell Back Squat", db=clean_db)

    assert estimate["is_dumbbell"] is False


# Issue #16 — cold-start 1RM seeding from demographics. The cold-start path
# fires only as a last-resort fallback after the user_profile_lifts chain
# returns nothing for the target muscle.


def test_cold_start_used_only_when_chain_is_empty(clean_db):
    """Demographics-only profile produces a non-zero cold-start estimate
    tagged with `reason="profile_cold_start"` and `source="cold_start"`."""
    _create_exercise(
        clean_db,
        "Barbell Bench Press",
        primary="Chest",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_demographics(
        gender="M",
        age=30,
        height_cm=180,
        weight_kg=80,
        experience_years=3,
        db=clean_db,
    )

    estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    assert estimate["source"] == "cold_start"
    assert estimate["reason"] == "profile_cold_start"
    assert estimate["weight"] > 0
    # Forced Light preset for cold-start safety regardless of complex tier.
    assert estimate["min_rep"] == 10
    assert estimate["max_rep"] == 15
    assert estimate["rir"] == 2
    assert estimate["rpe"] == 7.5
    # 80 kg × 1.00 (Chest M) × 1.0 (intermediate) × 1.0 (complex/complex)
    # × 0.65 (light) = 52.0 → barbell complex rounding stays 52.0.
    assert estimate["weight"] == pytest.approx(52.0, abs=0.5)


def test_cold_start_does_not_override_filled_reference_lift(clean_db):
    """A measured reference lift always wins; demographics must not modify
    the chain-derived suggestion."""
    _create_exercise(
        clean_db,
        "Barbell Bench Press",
        primary="Chest",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)
    upsert_user_profile_demographics(
        gender="M",
        age=30,
        height_cm=180,
        weight_kg=80,
        experience_years=3,
        db=clean_db,
    )

    estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    # Existing chain result (Issue #14): Epley(100,5) ≈ 116.67 × heavy 0.85
    # ≈ 99.17 → barbell complex rounding → 99.0. Cold-start would have
    # produced 52.0 with these demographics; the filled reference must
    # win regardless.
    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    assert estimate["weight"] == pytest.approx(99.0, abs=1.0)


def test_cold_start_gender_factor(clean_db):
    """Male and female demographics produce different cold-start weights
    for the same compound."""
    _create_exercise(
        clean_db,
        "Barbell Bench Press",
        primary="Chest",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_demographics(
        gender="M",
        age=30,
        height_cm=180,
        weight_kg=80,
        experience_years=3,
        db=clean_db,
    )
    male_estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    upsert_user_profile_demographics(
        gender="F",
        age=30,
        height_cm=170,
        weight_kg=80,
        experience_years=3,
        db=clean_db,
    )
    female_estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    assert male_estimate["source"] == "cold_start"
    assert female_estimate["source"] == "cold_start"
    assert male_estimate["weight"] > female_estimate["weight"]


def test_cold_start_experience_factor(clean_db):
    """Novice and advanced experience produce different cold-start weights."""
    _create_exercise(
        clean_db,
        "Barbell Bench Press",
        primary="Chest",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_demographics(
        gender="M",
        age=22,
        height_cm=180,
        weight_kg=80,
        experience_years=0.5,
        db=clean_db,
    )
    novice_estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    upsert_user_profile_demographics(
        gender="M",
        age=35,
        height_cm=180,
        weight_kg=80,
        experience_years=5,
        db=clean_db,
    )
    advanced_estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    assert novice_estimate["source"] == "cold_start"
    assert advanced_estimate["source"] == "cold_start"
    assert advanced_estimate["weight"] > novice_estimate["weight"]


def test_cold_start_returns_none_for_obscure_exercise(clean_db):
    """Exercises whose primary muscle is outside COLD_START_RATIOS must NOT
    invent a population number — they fall through to the existing generic
    default (`default_no_reference`) instead.
    """
    _create_exercise(
        clean_db,
        "Barbell Wrist Curl",
        primary="Forearms",
        equipment="Barbell",
        mechanic="Isolation",
        movement_pattern="upper_isolation",
    )
    upsert_user_profile_demographics(
        gender="M",
        age=30,
        height_cm=180,
        weight_kg=80,
        experience_years=3,
        db=clean_db,
    )

    helper_result = cold_start_1rm(
        {"primary_muscle_group": "Forearms", "equipment": "Barbell"},
        {"gender": "M", "weight_kg": 80, "experience_years": 3},
    )
    assert helper_result is None

    estimate = estimate_for_exercise("Barbell Wrist Curl", db=clean_db)

    assert estimate["source"] == "default"
    assert estimate["reason"] == "default_no_reference"


# Issue #17 — every estimate path must surface a structured `trace` so the
# Plan-page "show the math" expander can render the explanation without
# reconstructing the math.


def _trace_step_labels(estimate):
    return [step["label"] for step in estimate["trace"]["steps"]]


def test_estimate_response_includes_trace(
    clean_db, workout_plan_factory, workout_log_factory
):
    """Direct match, cross-muscle, cold-start, log, and generic-default paths
    each return a populated `trace` with the expected step labels (Issue #17)."""
    # 1) Direct match — Barbell Bench Press with a saved bench reference.
    _create_exercise(clean_db, "Barbell Bench Press", primary="Chest", equipment="Barbell")
    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)
    direct = estimate_for_exercise("Barbell Bench Press", db=clean_db)
    assert direct["source"] == "profile"
    assert direct["reason"] == "profile"
    direct_labels = _trace_step_labels(direct)
    assert direct["trace"]["source"] == "profile"
    assert any("Reference lift" in label for label in direct_labels)
    assert any("Estimated 1RM" in label for label in direct_labels)
    assert any("Tier scaling" in label for label in direct_labels)
    assert any("Working weight" in label for label in direct_labels)
    assert any("Rounding" in label for label in direct_labels)
    assert all("Cross-muscle factor" not in label for label in direct_labels)

    # 2) Cross-muscle — Cable Tricep Pushdown using bench as fallback.
    _create_exercise(
        clean_db,
        "Cable Tricep Pushdown",
        primary="Triceps",
        equipment="Cables",
        mechanic="Isolation",
        movement_pattern="upper_isolation",
    )
    cross = estimate_for_exercise("Cable Tricep Pushdown", db=clean_db)
    assert cross["reason"] == "profile_cross"
    cross_labels = _trace_step_labels(cross)
    assert any("Cross-muscle factor" in label for label in cross_labels)

    # 3) Log — last-logged set wins, simple trace.
    plan_id = workout_plan_factory(exercise_name="Barbell Bench Press", weight=80)
    workout_log_factory(
        plan_id=plan_id,
        exercise="Barbell Bench Press",
        planned_sets=4,
        planned_weight=80.0,
        scored_weight=82.5,
    )
    log_estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)
    assert log_estimate["source"] == "log"
    assert log_estimate["trace"]["source"] == "log"
    assert any("Most recent logged set" in step["label"] for step in log_estimate["trace"]["steps"])

    # 4) Cold-start — drop the saved bench AND wipe the log so neither path
    # fires; only demographics remain.
    clean_db.execute_query("DELETE FROM workout_log")
    clean_db.execute_query("DELETE FROM user_profile_lifts")
    upsert_user_profile_demographics(
        gender="M",
        age=30,
        height_cm=180,
        weight_kg=80,
        experience_years=3,
        db=clean_db,
    )
    cold = estimate_for_exercise("Barbell Bench Press", db=clean_db)
    assert cold["source"] == "cold_start"
    assert cold["trace"]["source"] == "cold_start"
    cold_labels = _trace_step_labels(cold)
    assert any("Bodyweight ratio" in label for label in cold_labels)
    assert any("Cold-start 1RM" in label for label in cold_labels)
    assert any("Experience tier" in label for label in cold_labels)
    assert any("Light" in label for label in cold_labels)

    # 5) Generic default — Forearms exercise (outside COLD_START_RATIOS) with
    # no log/lift entries triggers the default_no_reference fallback.
    _create_exercise(
        clean_db,
        "Barbell Wrist Curl",
        primary="Forearms",
        equipment="Barbell",
        mechanic="Isolation",
        movement_pattern="upper_isolation",
    )
    default_estimate = estimate_for_exercise("Barbell Wrist Curl", db=clean_db)
    assert default_estimate["source"] == "default"
    assert default_estimate["trace"]["source"] == "default"
    assert default_estimate["trace"]["steps"]


def test_trace_improvement_hint_for_cross_muscle(clean_db):
    """Cross-muscle path's improvement hint suggests entering the direct
    lift slug for the target exercise."""
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

    assert estimate["reason"] == "profile_cross"
    hint = estimate["trace"]["improvement_hint"]
    assert hint["action"] == "enter_reference_lift"
    # The pushdown matches the `triceps_extension` direct-lift keyword, so
    # the hint should point at the user's triceps_extension slug (skipping
    # the cross-muscle factor).
    assert hint["lift_key"] == "triceps_extension"
    assert "Triceps Extension" in hint["copy"]


def test_trace_improvement_hint_for_cold_start(clean_db):
    """Cold-start path suggests entering the canonical complex compound for
    the target muscle."""
    _create_exercise(
        clean_db,
        "Barbell Bench Press",
        primary="Chest",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_demographics(
        gender="M",
        age=30,
        height_cm=180,
        weight_kg=80,
        experience_years=3,
        db=clean_db,
    )

    estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    assert estimate["source"] == "cold_start"
    hint = estimate["trace"]["improvement_hint"]
    assert hint["action"] == "enter_reference_lift"
    assert hint["lift_key"] == "barbell_bench_press"
    assert "Barbell Bench Press" in hint["copy"]


def test_trace_improvement_hint_absent_for_direct_match(clean_db):
    """Direct match has no improvement hint — the suggestion is already
    using the user's measured data."""
    _create_exercise(
        clean_db,
        "Barbell Bench Press",
        primary="Chest",
        equipment="Barbell",
        mechanic="Compound",
    )
    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)

    estimate = estimate_for_exercise("Barbell Bench Press", db=clean_db)

    assert estimate["reason"] == "profile"
    assert "improvement_hint" not in estimate["trace"]


# Issue #18 — cohort_ranges + cohort_bars + coverage_donut.


def test_cohort_ranges_shape_and_used_flags():
    """cohort_ranges exposes 4 tiles with explicit used/unused flags.
    Height + age must be flagged unused since the estimator does not yet
    consume them — the UI relies on this to de-emphasise those tiles."""
    from utils.profile_estimator import cohort_ranges

    result = cohort_ranges(
        {
            "gender": "M",
            "age": 34,
            "height_cm": 178,
            "weight_kg": 75,
            "experience_years": 3,
        }
    )
    tiles = result["tiles"]
    assert set(tiles.keys()) == {"bodyweight", "height", "age", "experience"}
    assert tiles["bodyweight"]["used"] is True
    assert tiles["experience"]["used"] is True
    assert tiles["height"]["used"] is False
    assert tiles["age"]["used"] is False
    assert tiles["height"]["unused_reason"]
    assert tiles["age"]["unused_reason"]

    # Tier classification + multipliers come straight from EXPERIENCE_MULTIPLIERS.
    assert result["tier"] == "intermediate"
    assert result["tier_multiplier"] == 1.0
    assert result["next_tier"] == "advanced"
    assert result["next_tier_multiplier"] == 1.2

    # Cohort range strings are populated from the static buckets.
    assert "70" in tiles["bodyweight"]["cohort_text"]
    assert "kg" in tiles["bodyweight"]["cohort_text"]
    assert "intermediate" in tiles["bodyweight"]["cohort_text"]
    assert "Estimator cohort: male" in result["summary"]
    assert "intermediate" in result["summary"]


def test_cohort_ranges_advanced_tier_extrapolates_next_multiplier():
    """At advanced tier there is no higher tier in the table; the next-tier
    multiplier extrapolates so the cohort bar's right anchor still sits
    above the user's marker."""
    from utils.profile_estimator import (
        ADVANCED_COHORT_REACH,
        EXPERIENCE_MULTIPLIERS,
        cohort_ranges,
    )

    result = cohort_ranges(
        {"gender": "M", "weight_kg": 80, "experience_years": 10}
    )
    assert result["tier"] == "advanced"
    expected = EXPERIENCE_MULTIPLIERS["advanced"] * ADVANCED_COHORT_REACH
    assert result["next_tier_multiplier"] == pytest.approx(expected)


def test_cohort_ranges_empty_demographics():
    """With no demographics every tile is empty and the summary asks the
    user to fill the inputs. No exceptions, no leaked None into the
    cohort_text strings."""
    from utils.profile_estimator import cohort_ranges

    result = cohort_ranges(None)
    tiles = result["tiles"]
    for key in ("bodyweight", "height", "age", "experience"):
        assert tiles[key]["empty"] is True
    assert result["tier"] is None
    assert result["tier_multiplier"] is None
    assert "fill these to calibrate" in result["summary"]


def test_cohort_bars_skips_when_demographics_incomplete(clean_db):
    """Cohort bars require gender + bodyweight to compute the cold-start
    anchor. Without them the helper returns an empty list — never raises."""
    from utils.profile_estimator import cohort_bars

    result = cohort_bars(
        [{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        {"gender": None, "weight_kg": None, "experience_years": 3},
    )
    assert result == []


def test_cohort_bars_filled_canonical_compound():
    """A filled canonical compound surfaces a row with cold-start, user
    1RM, cohort upper, and a max anchor at least 5 % above the highest
    of the three so the user marker never clips the right edge."""
    from utils.profile_estimator import cohort_bars

    bars = cohort_bars(
        [{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        {"gender": "M", "weight_kg": 75, "experience_years": 3},
    )
    assert len(bars) == 1
    row = bars[0]
    assert row["lift_key"] == "barbell_bench_press"
    assert row["muscle"] == "Chest"
    # Epley(100, 5) = 100 × (1 + 5/30) ≈ 116.67 → rounded to 116.7.
    assert row["user_1rm_kg"] == pytest.approx(116.7, abs=0.1)
    # cold-start = 75 × 1.00 (Chest male ratio) × 1.0 (intermediate) = 75.
    assert row["cold_start_1rm_kg"] == pytest.approx(75.0, abs=0.1)
    # cohort upper = cold_start × (advanced/intermediate) = 75 × 1.2 = 90.
    assert row["cohort_upper_kg"] == pytest.approx(90.0, abs=0.1)
    # max axis must include all markers with headroom.
    assert row["max_kg"] >= max(
        row["user_1rm_kg"], row["cold_start_1rm_kg"], row["cohort_upper_kg"]
    )


def test_coverage_donut_counts_filled_lifts():
    """The donut payload is the same metric as the accuracy band's
    filled_count / total_count — just expressed as a percent for the
    circular progress."""
    from utils.profile_estimator import KEY_LIFTS, coverage_donut

    empty = coverage_donut([])
    assert empty["filled_count"] == 0
    assert empty["total_count"] == len(KEY_LIFTS)
    assert empty["percent"] == 0.0

    filled = coverage_donut(
        [
            {"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5},
            {"lift_key": "barbell_back_squat", "weight_kg": 130, "reps": 5},
        ]
    )
    assert filled["filled_count"] == 2
    assert filled["percent"] > 0.0


# Issue #19 — bodymap coverage state.


def test_muscle_coverage_state_marks_first_chain_lift_as_measured():
    """Saving the first lift in `MUSCLE_TO_KEY_LIFT[muscle]` flips that
    muscle to 'measured'. Chest's primary slug is barbell_bench_press."""
    from utils.profile_estimator import muscle_coverage_state

    coverage = muscle_coverage_state(
        [{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}]
    )

    chest = coverage["Chest"]
    assert chest["state"] == "measured"
    assert chest["primary_lift_key"] == "barbell_bench_press"
    assert len(chest["filled"]) == 1
    assert chest["filled"][0]["lift_key"] == "barbell_bench_press"
    assert chest["filled"][0]["estimated_1rm"] == pytest.approx(116.7, abs=0.1)
    # Triceps' chain has triceps_extension first; bench press is at the
    # end as a cross-fallback so saving bench should mark Triceps as
    # cross-muscle, not measured.
    triceps = coverage["Triceps"]
    assert triceps["state"] == "cross_muscle"
    assert triceps["filled"][0]["lift_key"] == "barbell_bench_press"


def test_muscle_coverage_state_distinguishes_cross_muscle_from_cold_start():
    """When only a non-primary chain entry is filled, the muscle is
    flagged 'cross_muscle' (estimator borrows with the 0.6 factor).
    Hamstrings' chain leads with leg_curl; saving romanian_deadlift
    (chain idx 1) yields cross_muscle."""
    from utils.profile_estimator import muscle_coverage_state

    coverage = muscle_coverage_state(
        [{"lift_key": "romanian_deadlift", "weight_kg": 120, "reps": 5}]
    )

    hams = coverage["Hamstrings"]
    assert hams["state"] == "cross_muscle"
    # Improvement hint should point at the unfilled primary slot.
    assert hams["improvement_lift_key"] == "leg_curl"

    # Calves' chain is a single slug (standing_calf_raise) and shares
    # no lifts with the deadlift family, so it must stay cold_start_only.
    calves = coverage["Calves"]
    assert calves["state"] == "cold_start_only"
    assert calves["improvement_lift_key"] == "standing_calf_raise"


def test_muscle_coverage_state_returns_states_for_every_bodymap_muscle():
    """Empty profile: every muscle in BODYMAP_MUSCLE_KEYS still resolves
    to a state. Muscles with non-empty chains start as cold_start_only."""
    from utils.profile_estimator import (
        BODYMAP_MUSCLE_KEYS,
        muscle_coverage_state,
    )

    coverage = muscle_coverage_state([])

    for muscle in BODYMAP_MUSCLE_KEYS:
        assert muscle in coverage, f"missing coverage for {muscle!r}"
        # No bodymap muscle should be 'not_assessed' — every entry in
        # BODYMAP_MUSCLE_KEYS has at least one chain lift in
        # MUSCLE_TO_KEY_LIFT (otherwise it shouldn't be on the bodymap).
        assert coverage[muscle]["state"] == "cold_start_only"


def test_bodymap_canonical_in_sync():
    """Drift guard: every backend muscle key referenced by the JS
    `COVERAGE_MUSCLE_CHAIN` (bodymap-svg.js) must also appear in
    `BODYMAP_MUSCLE_KEYS`. This catches the case where someone edits
    one side of the Python ↔ JS mirror without the other."""
    from pathlib import Path
    import re

    from utils.profile_estimator import BODYMAP_MUSCLE_KEYS

    js_path = Path(__file__).resolve().parents[1] / "static" / "js" / "modules" / "bodymap-svg.js"
    js_text = js_path.read_text(encoding="utf-8")
    # Match any quoted muscle key on a line of the COVERAGE_MUSCLE_CHAIN block.
    chain_block_match = re.search(
        r"COVERAGE_MUSCLE_CHAIN\s*=\s*\{(.+?)\};",
        js_text,
        re.DOTALL,
    )
    assert chain_block_match, "COVERAGE_MUSCLE_CHAIN block not found in bodymap-svg.js"
    js_keys = set(re.findall(r"'([^']+)':\s*\[", chain_block_match.group(1)))
    py_keys = set(BODYMAP_MUSCLE_KEYS)
    assert js_keys == py_keys, (
        f"bodymap-svg.js COVERAGE_MUSCLE_CHAIN keys diverge from BODYMAP_MUSCLE_KEYS: "
        f"only-in-JS={js_keys - py_keys}, only-in-PY={py_keys - js_keys}"
    )


# ---------------------------------------------------------------------------
# Issue #20 — broaden Calves / Glutes-Hips / Lower-Back direct-entry options.
# Each new slug must have a label, a tier, and at least one MUSCLE_TO_KEY_LIFT
# chain. Glute / hip compound additions must also slot into the existing
# "Legs" major muscle group so the accuracy band picks them up. Calves and
# lower-back-isolation slugs intentionally stay out of accuracy groups,
# matching the precedent set for `standing_calf_raise` and `back_extension`.
# ---------------------------------------------------------------------------

ISSUE_20_NEW_SLUGS = (
    # Calves
    "seated_calf_raise",
    "leg_press_calf_raise",
    "smith_machine_calf_raise",
    "single_leg_standing_calf_raise",
    "donkey_calf_raise",
    # Glutes / Hips
    "barbell_glute_bridge",
    "cable_pull_through",
    "bulgarian_split_squat",
    "b_stance_hip_thrust",
    "reverse_lunge",
    "sumo_deadlift",
    "cable_kickback",
    # Lower back
    "loaded_back_extension",
    "reverse_hyperextension",
    "seated_good_morning",
    "jefferson_curl",
)

ISSUE_20_LEG_GROUP_SLUGS = (
    "barbell_glute_bridge",
    "cable_pull_through",
    "bulgarian_split_squat",
    "b_stance_hip_thrust",
    "reverse_lunge",
    "sumo_deadlift",
)


@pytest.mark.parametrize("slug", ISSUE_20_NEW_SLUGS)
def test_issue_20_slug_has_label_tier_and_chain(slug):
    """Issue #20: every new slug must register a label, a tier, and live in
    at least one `MUSCLE_TO_KEY_LIFT` chain. Without these the questionnaire
    can't render it, the estimator can't classify it, and cross-muscle
    fallback can't reach it."""
    from utils.profile_estimator import (
        KEY_LIFT_LABELS,
        KEY_LIFTS,
        KEY_LIFT_TIER,
        MUSCLE_TO_KEY_LIFT,
    )

    assert slug in KEY_LIFTS, f"{slug} missing from KEY_LIFTS"
    assert slug in KEY_LIFT_LABELS, f"{slug} missing label"
    assert slug in KEY_LIFT_TIER, f"{slug} missing tier"
    chains_with_slug = [
        muscle for muscle, chain in MUSCLE_TO_KEY_LIFT.items() if slug in chain
    ]
    assert chains_with_slug, f"{slug} not in any MUSCLE_TO_KEY_LIFT chain"


@pytest.mark.parametrize("slug", ISSUE_20_LEG_GROUP_SLUGS)
def test_issue_20_leg_compounds_in_accuracy_band(slug):
    """Issue #20: leg / glute / hip compound additions must slot into the
    existing "Legs" major muscle group so the Issue #17C accuracy band
    counts them toward "mostly personalised" coverage."""
    from utils.profile_estimator import ACCURACY_MAJOR_MUSCLE_GROUPS

    legs_entry = next(
        (slugs for label, slugs in ACCURACY_MAJOR_MUSCLE_GROUPS if label == "Legs"),
        None,
    )
    assert legs_entry is not None, "Legs major group missing from ACCURACY_MAJOR_MUSCLE_GROUPS"
    assert slug in legs_entry, f"{slug} missing from Legs major group"


def test_issue_20_accuracy_band_threshold_unchanged():
    """Issue #20 acceptance gate: adding more slugs to existing groups must
    NOT raise the threshold for "mostly" / "fully" — the band counts
    *categories*, not slug count. Same six categories pre and post."""
    from utils.profile_estimator import ACCURACY_MAJOR_MUSCLE_GROUPS

    labels = [label for label, _ in ACCURACY_MAJOR_MUSCLE_GROUPS]
    assert labels == ["Chest", "Back", "Legs", "Shoulders", "Biceps", "Triceps"]


def test_seated_calf_raise_routes_directly_without_cross_factor(clean_db):
    """Issue #20 acceptance gate: an exercise named "Seated Calf Raise"
    routes through `DIRECT_LIFT_MATCHERS` to the new `seated_calf_raise`
    slug — no cross-muscle factor — once the user has saved that lift.
    This verifies the new direct keyword precedes the bare "calf raise"
    fallback that would otherwise route to `standing_calf_raise`."""
    _create_exercise(
        clean_db,
        "Seated Calf Raise",
        primary="Calves",
        equipment="Machine",
        mechanic="Isolation",
        movement_pattern="lower_isolation",
    )
    upsert_user_profile_lift("standing_calf_raise", 80, 8, db=clean_db)
    upsert_user_profile_lift("seated_calf_raise", 60, 10, db=clean_db)

    estimate = estimate_for_exercise("Seated Calf Raise", db=clean_db)

    assert estimate["source"] == "profile"
    # Direct match — must NOT be `profile_cross`. Picking the seated slug
    # over the standing one proves the new keyword took precedence.
    assert estimate["reason"] == "profile"
    # Epley(60, 10) ≈ 80; iso/iso multiplier 1.00; light preset 0.65 →
    # ~52 → machine rounding (1.0 kg increments) → ~52.0 kg. Loose tol
    # so future preset-tuning doesn't break this gate; the asserts above
    # are the ones that pin the routing fix.
    assert estimate["weight"] == pytest.approx(52.0, abs=2.0)


def test_sumo_deadlift_now_routes_to_dedicated_slug(clean_db):
    """Issue #20: `sumo_deadlift` previously aliased to `conventional_deadlift`
    in `DIRECT_LIFT_MATCHERS`. With its own slug, an exercise named "Sumo
    Deadlift" must pick the user's saved sumo number — not the conventional
    one — when both are entered."""
    _create_exercise(
        clean_db,
        "Sumo Deadlift",
        primary="Hamstrings",
        equipment="Barbell",
        mechanic="Compound",
        movement_pattern="hinge",
    )
    upsert_user_profile_lift("conventional_deadlift", 200, 5, db=clean_db)
    upsert_user_profile_lift("sumo_deadlift", 140, 5, db=clean_db)

    estimate = estimate_for_exercise("Sumo Deadlift", db=clean_db)

    assert estimate["source"] == "profile"
    assert estimate["reason"] == "profile"
    # Epley(140, 5) ≈ 163.33; complex/complex 1.00 × heavy 0.85 ≈ 138.83
    # → barbell rounding 1.25 kg → ~138.75 kg. If routing fell back to
    # conventional_deadlift this would be ~198 kg — the assertion below
    # would fail loudly.
    assert estimate["weight"] < 160.0
    assert estimate["weight"] == pytest.approx(138.75, abs=1.5)


def test_bodymap_coverage_lift_labels_cover_every_chain_slug():
    """Issue #20: the JS popover renders friendly labels via
    `COVERAGE_LIFT_LABELS` in `bodymap-svg.js`. Every slug that appears in
    a `COVERAGE_MUSCLE_CHAIN` chain must have a matching label entry, or
    the popover falls back to the raw slug."""
    from pathlib import Path
    import re

    js_path = Path(__file__).resolve().parents[1] / "static" / "js" / "modules" / "bodymap-svg.js"
    js_text = js_path.read_text(encoding="utf-8")

    chain_match = re.search(
        r"COVERAGE_MUSCLE_CHAIN\s*=\s*\{(.+?)\};",
        js_text,
        re.DOTALL,
    )
    labels_match = re.search(
        r"COVERAGE_LIFT_LABELS\s*=\s*\{(.+?)\};",
        js_text,
        re.DOTALL,
    )
    assert chain_match and labels_match

    chain_slugs = set(re.findall(r"'([a-z_0-9]+)'", chain_match.group(1)))
    # Strip the muscle-key keys (uppercase first letter or contains hyphen
    # with capital, e.g. 'Lower Back', 'Front-Shoulder').
    chain_lift_slugs = {s for s in chain_slugs if "_" in s or s.islower()}
    label_slugs = set(re.findall(r"^\s*([a-z_0-9]+):\s*'", labels_match.group(1), re.MULTILINE))

    missing_labels = chain_lift_slugs - label_slugs
    assert not missing_labels, (
        f"COVERAGE_LIFT_LABELS missing entries for: {sorted(missing_labels)}"
    )
