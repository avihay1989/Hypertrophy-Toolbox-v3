from __future__ import annotations

from typing import Any, Optional

from flask import Blueprint, jsonify, render_template, request

from utils.database import (
    DatabaseHandler,
    upsert_user_profile_demographics,
    upsert_user_profile_lift,
    upsert_user_profile_preference,
)
from utils.errors import error_response, success_response
from utils.logger import get_logger
from utils.profile_estimator import (
    DEFAULT_PREFERENCES,
    KEY_LIFTS,
    REP_RANGE_PRESETS,
    estimate_for_exercise,
)

user_profile_bp = Blueprint("user_profile", __name__)
logger = get_logger()

VALID_GENDERS = {"M", "F", "Other"}
VALID_TIERS = {"complex", "accessory", "isolated"}
VALID_REP_RANGES = {"heavy", "moderate", "light"}

REFERENCE_LIFT_LABELS = {
    "barbell_bench_press": "Barbell or Dumbbell Bench Press",
    "barbell_back_squat": "Barbell Back Squat",
    "romanian_deadlift": "Romanian or Conventional Deadlift",
    "triceps_extension": "Triceps Extension",
    "barbell_bicep_curl": "Barbell Bicep Curl",
    "dumbbell_lateral_raise": "Dumbbell Lateral Raise",
    "military_press": "Military / Shoulder Press",
    "leg_curl": "Leg Curl",
    "leg_extension": "Leg Extension",
    "weighted_dips": "Weighted Dips",
    "weighted_pullups": "Weighted Pull-ups",
    "bodyweight_pullups": "Bodyweight Pull-ups",
    "bodyweight_dips": "Bodyweight Dips",
    "barbell_row": "Barbell Row",
}


def _get_json_payload(route_name: str) -> Any:
    data = request.get_json(silent=True)
    if data is None:
        logger.warning("Invalid JSON in %s request", route_name)
        raise ValueError("Invalid JSON data")
    return data


def _nullable_text(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    normalized = str(value).strip()
    return normalized or None


def _nullable_float(value: Any, field_name: str, minimum: float, maximum: float) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}")
    return parsed


def _nullable_int(value: Any, field_name: str, minimum: int, maximum: int) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        parsed_float = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if not parsed_float.is_integer():
        raise ValueError(f"{field_name} must be an integer")
    parsed = int(parsed_float)
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return parsed


def _load_profile_context(db: DatabaseHandler) -> dict[str, Any]:
    profile = db.fetch_one("SELECT * FROM user_profile WHERE id = 1")
    lift_rows = db.fetch_all("SELECT lift_key, weight_kg, reps FROM user_profile_lifts")
    preference_rows = db.fetch_all("SELECT tier, rep_range FROM user_profile_preferences")
    lifts = {row["lift_key"]: row for row in lift_rows}
    preferences = {**DEFAULT_PREFERENCES}
    preferences.update(
        {
            row["tier"]: row["rep_range"]
            for row in preference_rows
            if row.get("tier") and row.get("rep_range")
        }
    )
    reference_lifts = [
        {
            "lift_key": lift_key,
            "label": REFERENCE_LIFT_LABELS[lift_key],
            "weight_kg": lifts.get(lift_key, {}).get("weight_kg"),
            "reps": lifts.get(lift_key, {}).get("reps"),
        }
        for lift_key in REFERENCE_LIFT_LABELS
    ]
    return {
        "profile": profile or {},
        "reference_lifts": reference_lifts,
        "preferences": preferences,
        "rep_range_presets": REP_RANGE_PRESETS,
    }


@user_profile_bp.route("/user_profile")
def user_profile():
    try:
        with DatabaseHandler() as db:
            context = _load_profile_context(db)
        return render_template("user_profile.html", **context)
    except Exception:
        logger.exception("Error rendering user profile")
        return render_template("error.html", message="Unable to load user profile."), 500


@user_profile_bp.route("/api/user_profile", methods=["POST"])
def save_user_profile():
    data = None
    try:
        data = _get_json_payload("save_user_profile")
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON data")

        gender = _nullable_text(data.get("gender"))
        if gender is not None and gender not in VALID_GENDERS:
            raise ValueError("gender must be one of M, F, Other")

        profile = {
            "gender": gender,
            "age": _nullable_int(data.get("age"), "age", 10, 100),
            "height_cm": _nullable_float(data.get("height_cm"), "height_cm", 100, 250),
            "weight_kg": _nullable_float(data.get("weight_kg"), "weight_kg", 30, 300),
            "experience_years": _nullable_float(
                data.get("experience_years"), "experience_years", 0, 80
            ),
        }

        with DatabaseHandler() as db:
            upsert_user_profile_demographics(**profile, db=db)
            saved = db.fetch_one("SELECT * FROM user_profile WHERE id = 1")

        return jsonify(success_response(data=saved, message="Profile saved"))
    except ValueError as exc:
        logger.warning("Validation error saving user profile", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to save user profile", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to save user profile", 500)


@user_profile_bp.route("/api/user_profile/lifts", methods=["POST"])
def save_user_profile_lifts():
    data = None
    try:
        data = _get_json_payload("save_user_profile_lifts")
        if isinstance(data, dict):
            entries = data.get("lifts")
        else:
            entries = data
        if not isinstance(entries, list):
            raise ValueError("Expected a list of lift entries")

        saved_entries = []
        with DatabaseHandler() as db:
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("Each lift entry must be an object")
                lift_key = _nullable_text(entry.get("lift_key"))
                if lift_key not in KEY_LIFTS:
                    raise ValueError("Unknown lift_key")

                weight_kg = _nullable_float(entry.get("weight_kg"), "weight_kg", 0, 1000)
                reps = _nullable_int(entry.get("reps"), "reps", 0, 100)
                upsert_user_profile_lift(lift_key, weight_kg, reps, db=db)
                saved_entries.append(
                    {"lift_key": lift_key, "weight_kg": weight_kg, "reps": reps}
                )

        return jsonify(success_response(data=saved_entries, message="Reference lifts saved"))
    except ValueError as exc:
        logger.warning("Validation error saving user profile lifts", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to save user profile lifts", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to save reference lifts", 500)


@user_profile_bp.route("/api/user_profile/preferences", methods=["POST"])
def save_user_profile_preferences():
    data = None
    try:
        data = _get_json_payload("save_user_profile_preferences")
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON data")

        unknown_tiers = set(data) - VALID_TIERS
        if unknown_tiers:
            raise ValueError("Unknown tier")

        saved = {}
        with DatabaseHandler() as db:
            for tier, rep_range in data.items():
                normalized_rep_range = _nullable_text(rep_range)
                if normalized_rep_range not in VALID_REP_RANGES:
                    raise ValueError("rep_range must be heavy, moderate, or light")
                upsert_user_profile_preference(tier, normalized_rep_range, db=db)
                saved[tier] = normalized_rep_range

        return jsonify(success_response(data=saved, message="Preferences saved"))
    except ValueError as exc:
        logger.warning("Validation error saving user profile preferences", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to save user profile preferences", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to save preferences", 500)


@user_profile_bp.route("/api/user_profile/estimate")
def get_user_profile_estimate():
    exercise = request.args.get("exercise", "")
    try:
        with DatabaseHandler() as db:
            estimate = estimate_for_exercise(exercise, db=db)
        return jsonify(success_response(data=estimate))
    except Exception:
        logger.exception("Failed to estimate exercise", extra={"exercise": exercise})
        return error_response("INTERNAL_ERROR", "Failed to estimate exercise", 500)
