"""Response-contract tests for the calibration summary on ``/update_workout_log``.

The workout-log update route now forwards a small ``data.calibration`` summary
after a *scored* change so the client can choose the right notification
(plan §"Notifications"): ``off`` / ``updated`` / ``low_confidence`` / ``none``.
Non-scored updates (e.g. progression date) carry no calibration block.

Also covers the pure :func:`recompute_calibration_after_log` status mapping.
See ``docs/user_profile/LEARNED_CALIBRATION_PLAN.md``.
"""
from utils.strength_calibration import (
    recompute_calibration_after_log,
    set_calibration_mode,
)

SQUAT = "Barbell Back Squat"


def _seed_exercise(exercise_factory):
    return exercise_factory(
        SQUAT,
        primary_muscle_group="Quadriceps",
        equipment="Barbell",
        mechanic="Compound",
    )


def _seed_log(workout_plan_factory, workout_log_factory, **scored):
    plan_id = workout_plan_factory(exercise_name=SQUAT)
    defaults = {
        "exercise": SQUAT,
        "scored_weight": 100.0,
        "scored_min_reps": 6,
        "scored_max_reps": 8,
        "scored_rir": 2,
    }
    defaults.update(scored)
    return workout_log_factory(plan_id=plan_id, **defaults)


# --------------------------------------------------------------------------- #
# Route response contract
# --------------------------------------------------------------------------- #

def test_scored_update_off_mode_reports_off(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    log_id = _seed_log(workout_plan_factory, workout_log_factory)

    resp = client.post(
        "/update_workout_log",
        json={"id": log_id, "updates": {"scored_weight": 105.0}},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["data"]["calibration"]["mode"] == "off"
    assert body["data"]["calibration"]["status"] == "off"


def test_scored_update_suggest_mode_reports_updated(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    log_id = _seed_log(workout_plan_factory, workout_log_factory)
    set_calibration_mode("suggest", db=clean_db)

    resp = client.post(
        "/update_workout_log",
        json={"id": log_id, "updates": {"scored_weight": 110.0}},
    )
    cal = resp.get_json()["data"]["calibration"]
    assert cal["mode"] == "suggest"
    assert cal["status"] == "updated"
    assert cal["confidence"] in ("medium", "high")
    assert cal["exercise"] == SQUAT
    # The recompute ran inside the write path: a row now exists.
    assert (
        clean_db.fetch_one(
            "SELECT COUNT(*) AS n FROM learned_strength_calibrations WHERE exercise_name = ?",
            (SQUAT,),
        )["n"]
        == 1
    )


def test_scored_update_suggest_mode_low_confidence(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    log_id = _seed_log(workout_plan_factory, workout_log_factory)
    # Age the only log past the staleness window so it can't reach `medium`.
    clean_db.execute_query(
        "UPDATE workout_log SET created_at = datetime('now', '-200 days') WHERE id = ?",
        (log_id,),
    )
    set_calibration_mode("suggest", db=clean_db)

    resp = client.post(
        "/update_workout_log",
        json={"id": log_id, "updates": {"scored_rir": 1}},
    )
    cal = resp.get_json()["data"]["calibration"]
    assert cal["mode"] == "suggest"
    assert cal["status"] == "low_confidence"


def test_scored_update_suggest_mode_none_when_no_usable_data(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    log_id = _seed_log(workout_plan_factory, workout_log_factory)
    set_calibration_mode("suggest", db=clean_db)

    # Clearing scored_weight leaves no usable scored log to learn from.
    resp = client.post(
        "/update_workout_log",
        json={"id": log_id, "updates": {"scored_weight": ""}},
    )
    cal = resp.get_json()["data"]["calibration"]
    assert cal["status"] == "none"
    assert cal["confidence"] is None


def test_non_scored_update_has_no_calibration_block(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    log_id = _seed_log(workout_plan_factory, workout_log_factory)
    set_calibration_mode("suggest", db=clean_db)

    resp = client.post(
        "/update_workout_log",
        json={"id": log_id, "updates": {"last_progression_date": "2026-06-04"}},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "data" not in body or body.get("data") is None


# --------------------------------------------------------------------------- #
# recompute_calibration_after_log status mapping (unit)
# --------------------------------------------------------------------------- #

def test_recompute_summary_off_when_mode_off(
    clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    _seed_log(workout_plan_factory, workout_log_factory)
    summary = recompute_calibration_after_log(SQUAT, db=clean_db)
    assert summary["mode"] == "off"
    assert summary["status"] == "off"
    # Recompute still wrote the row so it's ready if the user enables suggest.
    assert (
        clean_db.fetch_one(
            "SELECT COUNT(*) AS n FROM learned_strength_calibrations WHERE exercise_name = ?",
            (SQUAT,),
        )["n"]
        == 1
    )


def test_recompute_summary_none_for_unknown_exercise(clean_db):
    set_calibration_mode("suggest", db=clean_db)
    summary = recompute_calibration_after_log("No Such Lift", db=clean_db)
    assert summary["status"] == "none"
    assert summary["confidence"] is None
