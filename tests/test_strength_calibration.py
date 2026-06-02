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
    get_calibration_mode,
    reset_calibration_for_exercise,
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
