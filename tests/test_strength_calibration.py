"""Backend tests for learned strength calibration (MVP — exact-exercise only).

Covers the pure decision/confidence logic, the recompute-on-write /
invalidate-on-delete lifecycle, the settings default-off guard, and the
``/update_workout_log`` + ``/delete_workout_log`` route hooks. See
``docs/user_profile/LEARNED_CALIBRATION_PLAN.md``.
"""
from datetime import timedelta

from utils.profile_estimator import epley_1rm
from utils.progression_plan import decide_progression_target
from utils.strength_calibration import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    DEFAULT_CALIBRATION_MODE,
    _classify_confidence,
    _utcnow,
    _variance_within_high_band,
    clear_ignored_transfers,
    get_calibration_dashboard,
    get_calibration_mode,
    ignore_calibration_transfer,
    list_ignored_transfers,
    list_learned_calibrations,
    promote_calibration_to_profile,
    reset_all_calibrations,
    reset_calibration_for_exercise,
    resolve_promotion_target,
    unignore_calibration_transfer,
    update_calibration_for_exercise,
)


# --------------------------------------------------------------------------- #
# Pure logic — no DB
# --------------------------------------------------------------------------- #

def test_decide_progression_increase_weight_at_top_with_good_effort():
    result = decide_progression_target(
        weight=100.0, reps=8, planned_min_reps=6, planned_max_reps=8, rir=2
    )
    assert result["status"] == "increase_weight"
    # Novice increment at >=20kg is +2.5kg (mirrors _calculate_weight_increment).
    assert result["suggested_weight"] == 102.5
    assert result["suggested_min_reps"] == 6
    assert result["suggested_max_reps"] == 8


def test_decide_progression_below_min_holds_weight():
    result = decide_progression_target(
        weight=100.0, reps=4, planned_min_reps=6, planned_max_reps=8, rir=2
    )
    assert result["status"] == "increase_reps"
    assert result["suggested_weight"] == 100.0


def test_decide_progression_in_range_maintains():
    result = decide_progression_target(
        weight=100.0, reps=7, planned_min_reps=6, planned_max_reps=8, rir=2
    )
    assert result["status"] == "maintain"
    assert result["suggested_weight"] == 100.0


def test_decide_progression_top_of_range_but_grinding_does_not_add_weight():
    # RIR 5 is outside the 1-3 effort window — too easy to be sure top set is real.
    result = decide_progression_target(
        weight=100.0, reps=8, planned_min_reps=6, planned_max_reps=8, rir=5
    )
    assert result["status"] == "maintain"
    assert result["suggested_weight"] == 100.0


def test_variance_within_high_band():
    assert _variance_within_high_band([150.0, 150.0, 150.0]) is True
    assert _variance_within_high_band([150.0, 155.0, 152.0]) is True   # ~3% spread
    assert _variance_within_high_band([150.0, 185.0, 150.0]) is False  # ~21% spread
    assert _variance_within_high_band([150.0]) is True                 # trivially consistent


def test_classify_confidence_bands():
    # >=3 recent low-variance logs, latest recent -> high
    assert _classify_confidence(
        sample_count=3, latest_age=5, recent_e1rms=[150.0, 150.0, 150.0]
    ) == CONFIDENCE_HIGH
    # single recent log -> medium
    assert _classify_confidence(
        sample_count=1, latest_age=5, recent_e1rms=[150.0]
    ) == CONFIDENCE_MEDIUM
    # latest log stale (>180d) -> low
    assert _classify_confidence(
        sample_count=3, latest_age=200, recent_e1rms=[]
    ) == CONFIDENCE_LOW
    # recent but high-variance and sparse -> falls back to medium, not high
    assert _classify_confidence(
        sample_count=2, latest_age=5, recent_e1rms=[150.0, 200.0]
    ) == CONFIDENCE_MEDIUM


# --------------------------------------------------------------------------- #
# Settings default-off guard
# --------------------------------------------------------------------------- #

def test_missing_settings_row_behaves_as_off(db_handler):
    assert get_calibration_mode(db=db_handler) == DEFAULT_CALIBRATION_MODE == "off"


def test_settings_mode_suggest_is_returned(db_handler):
    db_handler.execute_query(
        "INSERT INTO user_calibration_settings (id, mode) VALUES (1, 'suggest')"
    )
    assert get_calibration_mode(db=db_handler) == "suggest"


# --------------------------------------------------------------------------- #
# Calibration lifecycle — DB
# --------------------------------------------------------------------------- #

def _log(clean_db, plan_id, exercise, **scored):
    query = """
        INSERT INTO workout_log (
            workout_plan_id, routine, exercise, planned_sets, planned_min_reps,
            planned_max_reps, planned_rir, planned_rpe, planned_weight,
            scored_min_reps, scored_max_reps, scored_rir, scored_rpe, scored_weight
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    defaults = dict(
        scored_min_reps=6, scored_max_reps=8, scored_rir=2, scored_rpe=8.0,
        scored_weight=100.0,
    )
    defaults.update(scored)
    clean_db.execute_query(query, (
        plan_id, "GYM - Full Body - Workout A", exercise, 3, 6, 8, 3, 7.0, 100.0,
        defaults["scored_min_reps"], defaults["scored_max_reps"],
        defaults["scored_rir"], defaults["scored_rpe"], defaults["scored_weight"],
    ))
    row = clean_db.fetch_one("SELECT last_insert_rowid() AS id")
    return row["id"]


def _calibration_row(db, exercise):
    return db.fetch_one(
        "SELECT * FROM learned_strength_calibrations WHERE exercise_name = ?",
        (exercise,),
    )


def test_update_calibration_creates_row_with_canonical_e1rm(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8, scored_rir=2)

    result = update_calibration_for_exercise(ex, db=clean_db)
    assert result is not None
    assert result["estimated_1rm"] == round(epley_1rm(100.0, 8), 2)
    assert result["source"] == "exact_logs"
    assert result["sample_count"] == 1

    row = _calibration_row(clean_db, ex)
    assert row is not None
    assert row["confidence"] == CONFIDENCE_MEDIUM  # single recent log
    assert row["lift_key"] == "barbell_bench_press"


def test_rir_does_not_inflate_e1rm(clean_db, exercise_factory, workout_plan_factory):
    # Canonical Epley uses weight+reps only; RIR/RPE must not enter the formula.
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=120.0, scored_max_reps=8, scored_rir=2)
    result = update_calibration_for_exercise(ex, db=clean_db)
    assert result["estimated_1rm"] == round(120.0 * (1 + 8 / 30), 2)


def test_incomplete_logs_are_ignored(clean_db, exercise_factory, workout_plan_factory):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    # No scored weight / no scored reps -> not usable for learning.
    _log(clean_db, plan, ex, scored_weight=None, scored_max_reps=8)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=None)
    result = update_calibration_for_exercise(ex, db=clean_db)
    assert result is None
    assert _calibration_row(clean_db, ex) is None


def test_recent_logs_outrank_old_logs(clean_db, exercise_factory, workout_plan_factory):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    old_id = _log(clean_db, plan, ex, scored_weight=80.0, scored_max_reps=8)
    new_id = _log(clean_db, plan, ex, scored_weight=120.0, scored_max_reps=8)
    clean_db.execute_query(
        "UPDATE workout_log SET created_at = ? WHERE id = ?",
        ("2020-01-01 00:00:00", old_id),
    )

    result = update_calibration_for_exercise(ex, db=clean_db, now=_utcnow())
    assert result["last_log_id"] == new_id
    assert result["estimated_1rm"] == round(epley_1rm(120.0, 8), 2)


def test_high_confidence_with_three_consistent_recent_logs(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    for _ in range(3):
        _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8, scored_rir=2)
    result = update_calibration_for_exercise(ex, db=clean_db, now=_utcnow())
    assert result["confidence"] == CONFIDENCE_HIGH
    assert result["sample_count"] == 3


def test_stale_logs_yield_low_confidence(clean_db, exercise_factory, workout_plan_factory):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    # Evaluate as if 200 days have passed since the log.
    future = _utcnow() + timedelta(days=200)
    result = update_calibration_for_exercise(ex, db=clean_db, now=future)
    assert result["confidence"] == CONFIDENCE_LOW


def test_update_is_idempotent_upsert(clean_db, exercise_factory, workout_plan_factory):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)
    update_calibration_for_exercise(ex, db=clean_db)
    rows = clean_db.fetch_all(
        "SELECT id FROM learned_strength_calibrations WHERE exercise_name = ?", (ex,)
    )
    assert len(rows) == 1


def test_excluded_equipment_is_not_calibrated(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Yoga Flow", equipment="Yoga")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    result = update_calibration_for_exercise(ex, db=clean_db)
    assert result is None
    assert _calibration_row(clean_db, ex) is None


def test_unknown_exercise_returns_none(clean_db):
    assert update_calibration_for_exercise("Nonexistent Lift", db=clean_db) is None


def test_reset_removes_calibration(clean_db, exercise_factory, workout_plan_factory):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)
    assert _calibration_row(clean_db, ex) is not None

    reset_calibration_for_exercise(ex, db=clean_db)
    assert _calibration_row(clean_db, ex) is None


def test_deleting_last_usable_log_clears_calibration(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    log_id = _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)
    assert _calibration_row(clean_db, ex) is not None

    clean_db.execute_query("DELETE FROM workout_log WHERE id = ?", (log_id,))
    update_calibration_for_exercise(ex, db=clean_db)
    assert _calibration_row(clean_db, ex) is None


# --------------------------------------------------------------------------- #
# Route hooks
# --------------------------------------------------------------------------- #

def test_update_workout_log_route_creates_calibration(
    client, clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    log_id = _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)

    resp = client.post(
        "/update_workout_log",
        json={"id": log_id, "updates": {"scored_weight": 110.0, "scored_max_reps": 8}},
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True

    row = _calibration_row(clean_db, ex)
    assert row is not None
    assert row["estimated_1rm"] == round(epley_1rm(110.0, 8), 2)


def test_delete_workout_log_route_invalidates_calibration(
    client, clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    log_id = _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)
    assert _calibration_row(clean_db, ex) is not None

    resp = client.post("/delete_workout_log", json={"id": log_id})
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert _calibration_row(clean_db, ex) is None


# --------------------------------------------------------------------------- #
# Phase 2B — review/control helpers
# --------------------------------------------------------------------------- #

def test_list_learned_calibrations_returns_all_recent_first(
    clean_db, exercise_factory, workout_plan_factory
):
    older = exercise_factory("Barbell Bench Press", equipment="Barbell")
    newer = exercise_factory("Barbell Back Squat", equipment="Barbell")
    for ex in (older, newer):
        plan = workout_plan_factory(exercise_name=ex)
        _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
        update_calibration_for_exercise(ex, db=clean_db)
    # Force a stale observed date on the bench row so ordering is deterministic.
    clean_db.execute_query(
        "UPDATE learned_strength_calibrations SET last_observed_at = ? WHERE exercise_name = ?",
        ("2000-01-01 00:00:00", older),
    )

    rows = list_learned_calibrations(db=clean_db)
    names = [r["exercise_name"] for r in rows]
    assert names == [newer, older]
    # Read-only shape: never leaks internal transfer-ratio columns.
    assert "ratio" not in rows[0]
    assert {"exercise_name", "confidence", "sample_count", "estimated_1rm",
            "suggested_weight", "last_observed_at"} <= set(rows[0])


def test_list_learned_calibrations_empty(clean_db):
    assert list_learned_calibrations(db=clean_db) == []


def test_list_and_unignore_transfers(clean_db):
    ignore_calibration_transfer("Barbell Bench Press", "Incline Dumbbell Bench Press", db=clean_db)
    ignore_calibration_transfer("Barbell Back Squat", "Leg Press", db=clean_db)
    assert len(list_ignored_transfers(db=clean_db)) == 2

    unignore_calibration_transfer(
        "Barbell Bench Press", "Incline Dumbbell Bench Press", db=clean_db
    )
    remaining = list_ignored_transfers(db=clean_db)
    assert len(remaining) == 1
    assert remaining[0]["source_exercise_name"] == "Barbell Back Squat"


def test_unignore_transfer_is_case_insensitive(clean_db):
    ignore_calibration_transfer("Barbell Bench Press", "Incline Dumbbell Bench Press", db=clean_db)
    unignore_calibration_transfer(
        "barbell bench press", "incline dumbbell bench press", db=clean_db
    )
    assert list_ignored_transfers(db=clean_db) == []


def test_clear_ignored_transfers_removes_all(clean_db):
    ignore_calibration_transfer("A", "B", db=clean_db)
    ignore_calibration_transfer("C", "D", db=clean_db)
    clear_ignored_transfers(db=clean_db)
    assert list_ignored_transfers(db=clean_db) == []


def test_reset_all_calibrations_clears_rows_only(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)
    ignore_calibration_transfer("Barbell Bench Press", "Incline Dumbbell Bench Press", db=clean_db)
    assert _calibration_row(clean_db, ex) is not None

    reset_all_calibrations(db=clean_db)
    assert list_learned_calibrations(db=clean_db) == []
    # Ignored transfers are a separate concern — left untouched by reset-all.
    assert len(list_ignored_transfers(db=clean_db)) == 1


# --------------------------------------------------------------------------- #
# Phase 2C — promote learned calibration to Profile reference lift
# --------------------------------------------------------------------------- #

def test_resolve_promotion_target_uses_measured_top_set(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=14)
    update_calibration_for_exercise(ex, db=clean_db)

    target = resolve_promotion_target(ex, db=clean_db)
    assert target["lift_key"] == "barbell_bench_press"
    assert target["weight_kg"] == 100.0
    assert target["reps"] == 14
    assert target["existing_reference"] is None


def test_resolve_promotion_target_converts_dumbbell_to_total_lift_basis(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Incline Dumbbell Bench Press", equipment="Dumbbells")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=36.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)

    target = resolve_promotion_target(ex, db=clean_db)
    assert target["lift_key"] == "incline_bench_press"
    assert target["weight_kg"] == 72.0
    assert target["reps"] == 8


def test_resolve_promotion_target_converts_total_to_dumbbell_lift_basis(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Machine Dumbbell Bench Press", equipment="Machine")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=80.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)

    target = resolve_promotion_target(ex, db=clean_db)
    assert target["lift_key"] == "dumbbell_bench_press"
    assert target["weight_kg"] == 40.0
    assert target["reps"] == 8


def test_resolve_promotion_target_blocks_low_confidence_and_unmapped_exercises(
    clean_db, exercise_factory, workout_plan_factory
):
    low = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=low)
    _log(clean_db, plan, low, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(low, db=clean_db)
    clean_db.execute_query(
        "UPDATE learned_strength_calibrations SET confidence = 'low' WHERE exercise_name = ?",
        (low,),
    )
    assert resolve_promotion_target(low, db=clean_db) is None

    unmapped = exercise_factory("Pec Deck", equipment="Machine")
    unmapped_plan = workout_plan_factory(exercise_name=unmapped)
    _log(clean_db, unmapped_plan, unmapped, scored_weight=60.0, scored_max_reps=10)
    update_calibration_for_exercise(unmapped, db=clean_db)
    assert resolve_promotion_target(unmapped, db=clean_db) is None


def test_resolve_promotion_target_blocks_excluded_exercise_even_with_lift_key(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Weighted Pull-Up With Band", equipment="Band")
    plan = workout_plan_factory(exercise_name=ex)
    log_id = _log(clean_db, plan, ex, scored_weight=20.0, scored_max_reps=6)
    clean_db.execute_query(
        """
        INSERT INTO learned_strength_calibrations (
            exercise_name, lift_key, estimated_1rm, suggested_weight,
            confidence, sample_count, last_log_id, source, created_at, updated_at
        ) VALUES (?, 'weighted_pullups', 24.0, 20.0, 'medium', 1, ?,
                  'exact_logs', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (ex, log_id),
    )

    assert resolve_promotion_target(ex, db=clean_db) is None


def test_resolve_promotion_target_requires_source_log(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    log_id = _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)
    clean_db.execute_query("DELETE FROM workout_log WHERE id = ?", (log_id,))

    assert resolve_promotion_target(ex, db=clean_db) is None


def test_promote_calibration_to_profile_writes_reference_and_keeps_learned_row(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=102.5, scored_max_reps=7)
    update_calibration_for_exercise(ex, db=clean_db)

    result = promote_calibration_to_profile(ex, db=clean_db)
    assert result["status"] == "promoted"
    assert result["lift_key"] == "barbell_bench_press"
    assert result["weight_kg"] == 102.5
    assert result["reps"] == 7
    assert result["overwrote"] is False
    assert _calibration_row(clean_db, ex) is not None
    saved = clean_db.fetch_one(
        "SELECT weight_kg, reps FROM user_profile_lifts WHERE lift_key = ?",
        ("barbell_bench_press",),
    )
    assert saved["weight_kg"] == 102.5
    assert saved["reps"] == 7


def test_promote_calibration_to_profile_requires_overwrite_for_existing_reference(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=110.0, scored_max_reps=6)
    update_calibration_for_exercise(ex, db=clean_db)
    clean_db.execute_query(
        """
        INSERT INTO user_profile_lifts (lift_key, weight_kg, reps, updated_at)
        VALUES ('barbell_bench_press', 90.0, 5, CURRENT_TIMESTAMP)
        """
    )

    blocked = promote_calibration_to_profile(ex, db=clean_db)
    assert blocked["status"] == "exists"
    saved = clean_db.fetch_one(
        "SELECT weight_kg, reps FROM user_profile_lifts WHERE lift_key = ?",
        ("barbell_bench_press",),
    )
    assert saved["weight_kg"] == 90.0
    assert saved["reps"] == 5

    overwritten = promote_calibration_to_profile(ex, db=clean_db, overwrite=True)
    assert overwritten["status"] == "promoted"
    assert overwritten["overwrote"] is True
    assert overwritten["previous"] == {"weight_kg": 90.0, "reps": 5}
    saved = clean_db.fetch_one(
        "SELECT weight_kg, reps FROM user_profile_lifts WHERE lift_key = ?",
        ("barbell_bench_press",),
    )
    assert saved["weight_kg"] == 110.0
    assert saved["reps"] == 6


def test_calibration_dashboard_adds_promotion_annotations(
    clean_db, exercise_factory, workout_plan_factory
):
    ex = exercise_factory("Barbell Bench Press", equipment="Barbell")
    plan = workout_plan_factory(exercise_name=ex)
    _log(clean_db, plan, ex, scored_weight=100.0, scored_max_reps=8)
    update_calibration_for_exercise(ex, db=clean_db)

    dashboard = get_calibration_dashboard(db=clean_db)
    row = dashboard["learned"][0]
    assert row["promotable"] is True
    assert row["lift_key"] == "barbell_bench_press"
    assert row["lift_label"] == "Barbell Bench Press"
    assert row["promote_weight_kg"] == 100.0
    assert row["promote_reps"] == 8
