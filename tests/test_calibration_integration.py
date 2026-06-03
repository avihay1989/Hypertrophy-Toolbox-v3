"""Estimator-integration + endpoint tests for learned strength calibration.

Covers the PR-2 surface: the settings endpoint, the default-off regression
guard (no settings row ⇒ current estimator chain, learned rows ignored), the
``suggest``-mode learned-source path, the usable-confidence gate, the
per-exercise reset endpoint, and estimator fallback when there is no usable
calibration. See ``docs/user_profile/LEARNED_CALIBRATION_PLAN.md``.
"""
from utils.strength_calibration import (
    get_calibration_mode,
    set_calibration_mode,
    update_calibration_for_exercise,
)

SQUAT = "Barbell Back Squat"


def _seed_exercise(exercise_factory):
    return exercise_factory(
        SQUAT,
        primary_muscle_group="Quadriceps",
        equipment="Barbell",
        mechanic="Compound",
    )


def _seed_log(clean_db, workout_plan_factory, workout_log_factory, **scored):
    """One scored log for SQUAT, returning its id."""
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
# Settings endpoint
# --------------------------------------------------------------------------- #

def test_settings_default_off_with_no_row(client, clean_db):
    resp = client.get("/api/user_profile/calibration_settings")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["data"]["mode"] == "off"


def test_settings_set_suggest_round_trips(client, clean_db):
    post = client.post(
        "/api/user_profile/calibration_settings", json={"mode": "suggest"}
    )
    assert post.status_code == 200
    assert post.get_json()["data"]["mode"] == "suggest"

    get = client.get("/api/user_profile/calibration_settings")
    assert get.get_json()["data"]["mode"] == "suggest"


def test_settings_rejects_invalid_mode(client, clean_db):
    resp = client.post(
        "/api/user_profile/calibration_settings", json={"mode": "auto_apply"}
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    # Invalid POST must not create a row — still reads as off.
    assert get_calibration_mode(db=clean_db) == "off"


# --------------------------------------------------------------------------- #
# Default-off regression guard
# --------------------------------------------------------------------------- #

def test_default_off_ignores_learned_row(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    """No settings row ⇒ current chain. A learned row exists but is not used."""
    _seed_exercise(exercise_factory)
    _seed_log(clean_db, workout_plan_factory, workout_log_factory)
    calibration = update_calibration_for_exercise(SQUAT, db=clean_db)
    assert calibration is not None  # a usable row exists...

    resp = client.get("/api/user_profile/estimate", query_string={"exercise": SQUAT})
    estimate = resp.get_json()["data"]
    # ...but with mode off the estimate is the last-logged set, untouched.
    assert estimate["source"] == "log"
    assert estimate["weight"] == 100.0


# --------------------------------------------------------------------------- #
# Learned source when mode == suggest
# --------------------------------------------------------------------------- #

def test_suggest_mode_surfaces_learned_source(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    _seed_log(clean_db, workout_plan_factory, workout_log_factory)
    calibration = update_calibration_for_exercise(SQUAT, db=clean_db)
    set_calibration_mode("suggest", db=clean_db)

    resp = client.get("/api/user_profile/estimate", query_string={"exercise": SQUAT})
    estimate = resp.get_json()["data"]
    assert estimate["source"] == "learned"
    assert estimate["reason"] == "learned_calibration"
    assert estimate["weight"] == calibration["suggested_weight"]
    assert estimate["trace"]["source"] == "learned"
    assert estimate["trace"]["confidence"] == calibration["confidence"]


def test_low_confidence_row_is_not_used(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    """A stored ``low``-band row must not displace the existing chain."""
    _seed_exercise(exercise_factory)
    _seed_log(clean_db, workout_plan_factory, workout_log_factory)
    set_calibration_mode("suggest", db=clean_db)
    clean_db.execute_query(
        """
        INSERT INTO learned_strength_calibrations (
            exercise_name, suggested_weight, suggested_min_reps,
            suggested_max_reps, confidence, sample_count, estimated_1rm, source,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'low', 1, 130.0, 'exact_logs',
                  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (SQUAT, 999.0, 6, 8),
    )

    resp = client.get("/api/user_profile/estimate", query_string={"exercise": SQUAT})
    estimate = resp.get_json()["data"]
    assert estimate["source"] == "log"
    assert estimate["weight"] == 100.0


def test_suggest_mode_falls_back_when_no_calibration_row(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    """Mode on but nothing learned yet ⇒ last-log fallback, no error."""
    _seed_exercise(exercise_factory)
    _seed_log(clean_db, workout_plan_factory, workout_log_factory)
    set_calibration_mode("suggest", db=clean_db)
    # No update_calibration_for_exercise call ⇒ no row.

    resp = client.get("/api/user_profile/estimate", query_string={"exercise": SQUAT})
    estimate = resp.get_json()["data"]
    assert estimate["source"] == "log"


# --------------------------------------------------------------------------- #
# Per-exercise reset endpoint
# --------------------------------------------------------------------------- #

def test_reset_endpoint_clears_then_falls_back(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    _seed_exercise(exercise_factory)
    _seed_log(clean_db, workout_plan_factory, workout_log_factory)
    update_calibration_for_exercise(SQUAT, db=clean_db)
    set_calibration_mode("suggest", db=clean_db)

    # Learned first...
    first = client.get("/api/user_profile/estimate", query_string={"exercise": SQUAT})
    assert first.get_json()["data"]["source"] == "learned"

    reset = client.post(
        "/api/user_profile/calibration/reset", json={"exercise": SQUAT}
    )
    assert reset.status_code == 200
    assert reset.get_json()["ok"] is True
    assert (
        clean_db.fetch_one(
            "SELECT COUNT(*) AS n FROM learned_strength_calibrations WHERE exercise_name = ?",
            (SQUAT,),
        )["n"]
        == 0
    )

    # ...then back to the last-log fallback, mode still suggest.
    after = client.get("/api/user_profile/estimate", query_string={"exercise": SQUAT})
    assert after.get_json()["data"]["source"] == "log"


def test_reset_endpoint_requires_exercise(client, clean_db):
    resp = client.post("/api/user_profile/calibration/reset", json={})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"
