from __future__ import annotations

from typing import Any, Optional

from flask import Blueprint, jsonify, render_template, request

from utils.body_fat import ace_category
from utils.database import (
    DatabaseHandler,
    upsert_user_profile_demographics,
    upsert_user_profile_lift,
    upsert_user_profile_preference,
)
from utils.errors import error_response, success_response
from utils.logger import get_logger
from utils.strength_calibration import (
    VALID_CALIBRATION_MODES,
    clear_ignored_transfers,
    get_calibration_dashboard,
    get_calibration_settings,
    ignore_calibration_transfer,
    promote_calibration_to_profile,
    reset_all_calibrations,
    reset_calibration_for_exercise,
    set_calibration_settings,
    unignore_calibration_transfer,
)
from utils.profile_estimator import (
    DEFAULT_PREFERENCES,
    DUMBBELL_LIFT_KEYS,
    KEY_LIFT_SIDE,
    KEY_LIFTS,
    REP_RANGE_PRESETS,
    accuracy_band,
    cohort_bars,
    cohort_ranges,
    cold_start_anchor_lifts,
    coverage_donut,
    estimate_for_exercise,
    muscle_coverage_state,
    next_high_impact_lifts,
    replaced_anchor_lifts,
)

user_profile_bp = Blueprint("user_profile", __name__)
logger = get_logger()

VALID_GENDERS = {"M", "F"}
VALID_TIERS = {"complex", "accessory", "isolated"}
VALID_REP_RANGES = {"heavy", "moderate", "light"}

# Issue #24 — Reference Lifts split into anterior + posterior side-by-side
# cards mirroring the Coverage map (Issue #19) front/back framing. Each
# group entry carries its `side` ("anterior" | "posterior"); the route
# context partitions the list into two arrays the template renders inside
# two `frame-calm-glass` cards. Slug routing in `MUSCLE_TO_KEY_LIFT` and
# `KEY_LIFT_LABELS` (`utils/profile_estimator.py`) is unchanged — this is
# purely presentation-side. The "Shoulders" group splits into "Front
# Shoulders" + "Rear Shoulders / Traps", and the original "Legs — Quads &
# Glutes" group is split with quad-biased compounds under "Quads"
# (anterior) and `hip_thrust` moved to "Glutes / Hip" (posterior).
REFERENCE_LIFT_GROUPS: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("Chest", "anterior", [
        ("barbell_bench_press", "Barbell Bench Press"),
        ("dumbbell_bench_press", "Dumbbell Bench Press"),
        ("incline_bench_press", "Incline Barbell/Dumbbell Bench Press"),
        ("smith_machine_bench_press", "Smith Machine Bench Press"),
        ("machine_chest_press", "Machine Chest Press"),
        ("dumbbell_fly", "Dumbbell Fly"),
    ]),
    ("Front Shoulders", "anterior", [
        ("military_press", "Military / Shoulder Press"),
        ("dumbbell_shoulder_press", "Dumbbell Shoulder Press"),
        ("machine_shoulder_press", "Machine Shoulder Press"),
        ("arnold_press", "Arnold Press"),
        ("dumbbell_lateral_raise", "Dumbbell Lateral Raise"),
    ]),
    ("Biceps", "anterior", [
        ("barbell_bicep_curl", "Barbell Bicep Curl"),
        ("dumbbell_curl", "Dumbbell Curl"),
        ("preacher_curl", "Preacher Curl (EZ Bar)"),
        ("incline_dumbbell_curl", "Incline Dumbbell Curl"),
    ]),
    ("Core / Abs", "anterior", [
        ("cable_crunch", "Cable Crunch"),
        ("machine_crunch", "Machine Crunch"),
        ("weighted_crunch", "Weighted Crunch"),
        ("cable_woodchop", "Cable Woodchop"),
        ("side_bend", "Side Bend"),
    ]),
    ("Quads", "anterior", [
        ("barbell_back_squat", "Barbell Back Squat"),
        ("leg_press", "Leg Press"),
        ("leg_extension", "Leg Extension"),
        ("dumbbell_squat", "Dumbbell Squat"),
        ("dumbbell_lunge", "Dumbbell Lunge"),
        ("reverse_lunge", "Reverse Lunge"),
        ("dumbbell_step_up", "Dumbbell Step-Up"),
        ("bulgarian_split_squat", "Bulgarian Split Squat"),
    ]),
    ("Upper Back", "posterior", [
        ("barbell_row", "Barbell Row"),
        ("machine_row", "Machine Row"),
        ("weighted_pullups", "Weighted Pull-ups"),
        ("bodyweight_pullups", "Bodyweight Pull-ups"),
        ("bodyweight_chinups", "Bodyweight Chin-ups"),
    ]),
    ("Rear Shoulders / Traps", "posterior", [
        ("face_pulls", "Face Pulls"),
        ("barbell_shrugs", "Barbell Shrugs"),
    ]),
    ("Triceps", "posterior", [
        ("triceps_extension", "Triceps Extension"),
        ("skull_crusher", "Skull Crusher (EZ Bar / Barbell)"),
        ("jm_press", "JM Press"),
        ("weighted_dips", "Weighted Dips"),
        ("bodyweight_dips", "Bodyweight Dips"),
    ]),
    ("Lower Back", "posterior", [
        ("back_extension", "Back Extension"),
        ("loaded_back_extension", "Loaded 45° Back Extension"),
        ("reverse_hyperextension", "Reverse Hyperextension"),
        ("jefferson_curl", "Jefferson Curl"),
    ]),
    ("Glutes / Hip", "posterior", [
        ("hip_thrust", "Hip Thrust"),
        ("barbell_glute_bridge", "Barbell Glute Bridge"),
        ("b_stance_hip_thrust", "B-Stance Hip Thrust"),
        ("cable_pull_through", "Cable Pull-Through"),
        ("cable_kickback", "Cable Kickback"),
        ("machine_hip_abduction", "Machine Hip Abduction"),
    ]),
    ("Hamstrings", "posterior", [
        ("romanian_deadlift", "Romanian Deadlift"),
        ("conventional_deadlift", "Conventional Deadlift"),
        ("sumo_deadlift", "Sumo Deadlift"),
        ("stiff_leg_deadlift", "Stiff-Leg Deadlift"),
        ("good_morning", "Good Morning"),
        ("seated_good_morning", "Seated Good Morning"),
        ("single_leg_rdl", "Single-Leg RDL"),
        ("leg_curl", "Leg Curl"),
    ]),
    ("Calves", "posterior", [
        ("standing_calf_raise", "Standing Calf Raise"),
        ("seated_calf_raise", "Seated Calf Raise"),
        ("leg_press_calf_raise", "Leg Press Calf Raise"),
        ("smith_machine_calf_raise", "Smith Machine Calf Raise"),
        ("single_leg_standing_calf_raise", "Single-Leg Standing Calf Raise"),
        ("donkey_calf_raise", "Donkey Calf Raise"),
    ]),
]

REFERENCE_LIFT_LABELS = {
    lift_key: label
    for _, _, lifts in REFERENCE_LIFT_GROUPS
    for lift_key, label in lifts
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


def _optional_bool(data: dict[str, Any], field_name: str) -> Optional[bool]:
    if field_name not in data or data.get(field_name) is None:
        return None
    value = data.get(field_name)
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ValueError(f"{field_name} must be true or false")


def _load_latest_body_composition(db: DatabaseHandler) -> Optional[dict[str, Any]]:
    """Return the most recent `body_composition_snapshots` row enriched with
    the effective BFP (Navy if measured, else BMI), the ACE band label, and
    the lean mass — or None if no snapshot has been saved.

    Display-only — Profile page surfaces Issues #17 ("Body fat: X% · {ACE
    band}") and #18 (Lean Mass sub-line on bodyweight tile). All math lives
    in the snapshot row itself; this helper just picks Navy-over-BMI and
    looks up the ACE label.
    """
    row = db.fetch_one(
        """
        SELECT bfp_navy, bfp_bmi, lean_mass_kg, fat_mass_kg, gender
        FROM body_composition_snapshots
        ORDER BY captured_at DESC, id DESC
        LIMIT 1
        """
    )
    if row is None:
        return None
    bfp_navy = row["bfp_navy"]
    bfp_bmi = row["bfp_bmi"]
    bfp = bfp_navy if bfp_navy is not None else bfp_bmi
    gender = row["gender"]
    band: Optional[str] = None
    if bfp is not None and gender in VALID_GENDERS:
        try:
            band = ace_category(bfp, gender)
        except ValueError:
            band = None
    return {
        "bfp": bfp,
        "bfp_source": "navy" if bfp_navy is not None else "bmi",
        "ace_band": band,
        "lean_mass_kg": row["lean_mass_kg"],
        "fat_mass_kg": row["fat_mass_kg"],
    }


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
    reference_lift_groups = [
        {
            "group": group_label,
            "side": side,
            "lifts": [
                {
                    "lift_key": lift_key,
                    "label": label,
                    "weight_kg": lifts.get(lift_key, {}).get("weight_kg"),
                    "reps": lifts.get(lift_key, {}).get("reps"),
                    "is_dumbbell": lift_key in DUMBBELL_LIFT_KEYS,
                }
                for lift_key, label in entries
            ],
        }
        for group_label, side, entries in REFERENCE_LIFT_GROUPS
    ]
    reference_lift_groups_anterior = [
        group for group in reference_lift_groups if group["side"] == "anterior"
    ]
    reference_lift_groups_posterior = [
        group for group in reference_lift_groups if group["side"] == "posterior"
    ]
    reference_lifts = [
        lift for group in reference_lift_groups for lift in group["lifts"]
    ]
    insights = _build_profile_insights(profile or {}, lift_rows)
    latest_body_composition = _load_latest_body_composition(db)
    calibration_settings = get_calibration_settings(db=db)
    return {
        "profile": profile or {},
        "calibration_mode": calibration_settings["mode"],
        "calibration_allow_related": calibration_settings["allow_related_exercise_learning"],
        "reference_lifts": reference_lifts,
        "reference_lift_groups": reference_lift_groups,
        "reference_lift_groups_anterior": reference_lift_groups_anterior,
        "reference_lift_groups_posterior": reference_lift_groups_posterior,
        "preferences": preferences,
        "rep_range_presets": REP_RANGE_PRESETS,
        "profile_insights": insights,
        "latest_body_composition": latest_body_composition,
    }


def _classify_experience_label(years: Optional[float]) -> Optional[str]:
    """Plain-English experience tier for the classification line on the
    "How the system sees you" card. Returns None when the input is missing.
    """
    if years is None:
        return None
    try:
        years_value = float(years)
    except (TypeError, ValueError):
        return None
    if years_value < 0:
        return None
    if years_value <= 1.0:
        tier = "novice"
    elif years_value <= 3.0:
        tier = "intermediate"
    else:
        tier = "advanced"
    return f"{tier} ({years_value:g} yrs)"


def _build_profile_insights(
    profile: dict[str, Any], lift_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Computed inputs for the "How the system sees you" card + accuracy
    band. Returned as a JSON-friendly dict so the template AND the JS
    can both consume the same structure (the JS re-renders the card
    after each form change without needing a round-trip)."""
    demographics = {
        "gender": profile.get("gender"),
        "age": profile.get("age"),
        "height_cm": profile.get("height_cm"),
        "weight_kg": profile.get("weight_kg"),
        "experience_years": profile.get("experience_years"),
    }
    band = accuracy_band(
        profile_lifts=lift_rows,
        demographics=demographics,
    )
    anchors = cold_start_anchor_lifts(demographics)
    replaced = replaced_anchor_lifts(lift_rows)
    next_lifts = next_high_impact_lifts(lift_rows, limit=3)
    cohort = cohort_ranges(demographics)
    bars = cohort_bars(lift_rows, demographics)
    donut = coverage_donut(lift_rows)
    coverage = muscle_coverage_state(lift_rows)

    classification_parts = {
        "gender": (
            "Male" if demographics["gender"] == "M"
            else "Female" if demographics["gender"] == "F"
            else None
        ),
        "experience": _classify_experience_label(demographics["experience_years"]),
        "bodyweight": (
            f"{float(demographics['weight_kg']):g} kg"
            if demographics["weight_kg"] is not None
            else None
        ),
    }
    return {
        "accuracy_band": band,
        "next_high_impact_lifts": next_lifts,
        "cold_start_anchor_lifts": anchors,
        "replaced_anchor_lifts": replaced,
        "classification": classification_parts,
        "demographics_complete": all(classification_parts.values()),
        "cohort_ranges": cohort,
        "cohort_bars": bars,
        "coverage_donut": donut,
        "muscle_coverage": coverage,
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
            raise ValueError("gender must be one of M, F")

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


@user_profile_bp.route("/api/user_profile/calibration_settings", methods=["GET", "POST"])
def calibration_settings():
    """Read or update the learned-calibration mode (default-off feature switch).

    GET returns the active mode (``off`` when no settings row exists). POST sets
    it; ``suggest`` is the explicit opt-in that lets the estimator prioritise
    learned suggestions. See ``docs/user_profile/LEARNED_CALIBRATION_PLAN.md``.
    """
    if request.method == "GET":
        try:
            with DatabaseHandler() as db:
                settings = get_calibration_settings(db=db)
            return jsonify(success_response(data=settings))
        except Exception:
            logger.exception("Failed to read calibration settings")
            return error_response("INTERNAL_ERROR", "Failed to read calibration settings", 500)

    data = None
    try:
        data = _get_json_payload("calibration_settings")
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON data")
        mode = _nullable_text(data.get("mode"))
        if mode not in VALID_CALIBRATION_MODES:
            raise ValueError(f"mode must be one of {', '.join(VALID_CALIBRATION_MODES)}")
        allow_related = _optional_bool(data, "allow_related_exercise_learning")

        with DatabaseHandler() as db:
            saved = set_calibration_settings(
                mode,
                db=db,
                allow_related_exercise_learning=allow_related,
            )
        return jsonify(success_response(data=saved, message="Calibration settings saved"))
    except ValueError as exc:
        logger.warning("Validation error saving calibration settings", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to save calibration settings", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to save calibration settings", 500)


@user_profile_bp.route("/api/user_profile/calibration/reset", methods=["POST"])
def reset_calibration():
    """Clear the learned calibration for one exercise (user reset action)."""
    data = None
    try:
        data = _get_json_payload("reset_calibration")
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON data")
        exercise = _nullable_text(data.get("exercise"))
        if exercise is None:
            raise ValueError("exercise is required")

        with DatabaseHandler() as db:
            reset_calibration_for_exercise(exercise, db=db)
        return jsonify(
            success_response(data={"exercise": exercise}, message="Learned calibration reset")
        )
    except ValueError as exc:
        logger.warning("Validation error resetting calibration", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to reset calibration", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to reset calibration", 500)


@user_profile_bp.route("/api/user_profile/calibration/ignore_transfer", methods=["POST"])
def ignore_calibration_transfer_route():
    """Ignore one related source-target calibration pair."""
    data = None
    try:
        data = _get_json_payload("ignore_calibration_transfer")
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON data")
        source = _nullable_text(data.get("source_exercise"))
        target = _nullable_text(data.get("target_exercise"))
        if source is None:
            raise ValueError("source_exercise is required")
        if target is None:
            raise ValueError("target_exercise is required")

        with DatabaseHandler() as db:
            ignore_calibration_transfer(source, target, db=db)
        return jsonify(
            success_response(
                data={"source_exercise": source, "target_exercise": target},
                message="Related calibration ignored",
            )
        )
    except ValueError as exc:
        logger.warning("Validation error ignoring calibration transfer", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to ignore calibration transfer", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to ignore calibration transfer", 500)


@user_profile_bp.route("/api/user_profile/calibration/dashboard")
def calibration_dashboard():
    """Read-only calibration review surface (Phase 2B + 2C annotations).

    Returns the learned-calibration rows (each annotated with Phase 2C
    promotion state: ``promotable`` / ``lift_key`` / ``lift_label`` /
    ``existing_reference`` / ``promote_weight_kg`` / ``promote_reps``) and the
    ignored related pairs the Profile page renders. Never mutates state and
    never exposes internal transfer-ratio tuning data. See
    ``docs/user_profile/LEARNED_CALIBRATION_PLAN.md``.
    """
    try:
        with DatabaseHandler() as db:
            data = get_calibration_dashboard(db=db)
        return jsonify(success_response(data=data))
    except Exception:
        logger.exception("Failed to load calibration dashboard")
        return error_response("INTERNAL_ERROR", "Failed to load calibration dashboard", 500)


@user_profile_bp.route("/api/user_profile/calibration/promote", methods=["POST"])
def promote_calibration_route():
    """Promote an exact learned calibration into a declared Profile reference lift.

    Writes the measured top set (basis-converted) into ``user_profile_lifts``.
    Never silent: an existing reference lift requires ``overwrite=true`` (the UI
    confirms old→new first). Does not change estimator priority. See
    ``docs/user_profile/LEARNED_CALIBRATION_PLAN.md`` §"Phase 2C".
    """
    data = None
    try:
        data = _get_json_payload("promote_calibration")
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON data")
        exercise = _nullable_text(data.get("exercise"))
        if exercise is None:
            raise ValueError("exercise is required")
        overwrite = bool(_optional_bool(data, "overwrite"))

        with DatabaseHandler() as db:
            result = promote_calibration_to_profile(exercise, db=db, overwrite=overwrite)

        status = result.get("status")
        if status == "not_promotable":
            return error_response(
                "NOT_PROMOTABLE",
                "This learned calibration can't be promoted to a Profile reference lift.",
                400,
            )
        if status == "exists":
            return error_response(
                "REFERENCE_LIFT_EXISTS",
                "A Profile reference lift already exists for this lift; confirm to overwrite it.",
                400,
            )
        return jsonify(
            success_response(
                data={
                    "exercise": exercise,
                    "lift_key": result["lift_key"],
                    "lift_label": result["lift_label"],
                    "weight_kg": result["weight_kg"],
                    "reps": result["reps"],
                    "overwrote": result["overwrote"],
                    "previous": result["previous"],
                },
                message="Promoted to Profile reference lift",
            )
        )
    except ValueError as exc:
        logger.warning("Validation error promoting calibration", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to promote calibration", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to promote calibration", 500)


@user_profile_bp.route("/api/user_profile/calibration/unignore_transfer", methods=["POST"])
def unignore_calibration_transfer_route():
    """Restore one previously-ignored related source-target pair (Phase 2B)."""
    data = None
    try:
        data = _get_json_payload("unignore_calibration_transfer")
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON data")
        source = _nullable_text(data.get("source_exercise"))
        target = _nullable_text(data.get("target_exercise"))
        if source is None:
            raise ValueError("source_exercise is required")
        if target is None:
            raise ValueError("target_exercise is required")

        with DatabaseHandler() as db:
            unignore_calibration_transfer(source, target, db=db)
        return jsonify(
            success_response(
                data={"source_exercise": source, "target_exercise": target},
                message="Related calibration restored",
            )
        )
    except ValueError as exc:
        logger.warning("Validation error restoring calibration transfer", extra={"error": str(exc)})
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Failed to restore calibration transfer", extra={"payload": data})
        return error_response("INTERNAL_ERROR", "Failed to restore calibration transfer", 500)


@user_profile_bp.route("/api/user_profile/calibration/clear_ignored_transfers", methods=["POST"])
def clear_ignored_calibration_transfers_route():
    """Remove all ignored related pairs (Phase 2B bulk control)."""
    try:
        with DatabaseHandler() as db:
            clear_ignored_transfers(db=db)
        return jsonify(success_response(data={}, message="Cleared all ignored transfers"))
    except Exception:
        logger.exception("Failed to clear ignored calibration transfers")
        return error_response("INTERNAL_ERROR", "Failed to clear ignored transfers", 500)


@user_profile_bp.route("/api/user_profile/calibration/reset_all", methods=["POST"])
def reset_all_calibration_route():
    """Clear every learned-calibration row (Phase 2B bulk reset control)."""
    try:
        with DatabaseHandler() as db:
            reset_all_calibrations(db=db)
        return jsonify(success_response(data={}, message="Reset all learned calibration"))
    except Exception:
        logger.exception("Failed to reset all calibration")
        return error_response("INTERNAL_ERROR", "Failed to reset all calibration", 500)
