"""User-profile-based workout control estimates."""
from __future__ import annotations

import math
from typing import Any, Literal, Optional

from utils.database import DatabaseHandler
from utils.logger import get_logger
from utils.normalization import normalize_equipment, normalize_muscle

logger = get_logger()

Tier = Literal["complex", "accessory", "isolated", "excluded"]

KEY_LIFTS = frozenset(
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

COMPLEX_ALLOWLIST = frozenset(
    {
        "barbell back squat",
        "barbell front squat",
        "back squat",
        "front squat",
        "conventional deadlift",
        "sumo deadlift",
        "romanian deadlift",
        "trap bar deadlift",
        "deadlift",
        "barbell bench press",
        "dumbbell bench press",
        "incline barbell bench",
        "incline dumbbell bench",
        "flat bench press",
        "overhead press",
        "military press",
        "shoulder press",
        "weighted dip",
        "weighted pull-up",
        "weighted pullup",
        "weighted chin-up",
        "weighted chinup",
        "barbell row",
        "pendlay row",
        "t-bar row",
        "bent-over row",
        "hip thrust",
        "power clean",
        "hang clean",
        "snatch",
        "push press",
    }
)

EXCLUDED_EQUIPMENT = frozenset(
    {"Trx", "Bosu_Ball", "Cardio", "Recovery", "Yoga", "Vitruvian", "Band", "Stretches"}
)

TIER_RATIOS = {
    "complex": 1.00,
    "accessory": 0.70,
    "isolated": 0.40,
}

REP_RANGE_PRESETS = {
    "heavy": {"min_rep": 4, "max_rep": 6, "pct_1rm": 0.85, "rir": 1, "rpe": 9.0},
    "moderate": {"min_rep": 6, "max_rep": 8, "pct_1rm": 0.77, "rir": 2, "rpe": 8.0},
    "light": {"min_rep": 10, "max_rep": 15, "pct_1rm": 0.65, "rir": 2, "rpe": 7.5},
}
REP_RANGE_PCT = {key: preset["pct_1rm"] for key, preset in REP_RANGE_PRESETS.items()}

DEFAULT_PREFERENCES = {
    "complex": "heavy",
    "accessory": "moderate",
    "isolated": "light",
}

DEFAULT_ESTIMATE = {
    "weight": 25.0,
    "sets": 3,
    "min_rep": 6,
    "max_rep": 8,
    "rir": 3,
    "rpe": 7.0,
    "source": "default",
}

CROSS_FALLBACK_FACTOR = 0.6
PROFILE_DEFAULT_SETS = 3

MUSCLE_TO_KEY_LIFT = {
    "Chest": ["barbell_bench_press"],
    "Quadriceps": ["barbell_back_squat", "romanian_deadlift"],
    "Hamstrings": ["leg_curl", "romanian_deadlift"],
    "Gluteus Maximus": ["romanian_deadlift", "barbell_back_squat"],
    "Glutes": ["romanian_deadlift", "barbell_back_squat"],
    "Hip-Adductors": [],
    "Latissimus Dorsi": ["weighted_pullups", "bodyweight_pullups", "barbell_row"],
    "Latissimus-Dorsi": ["weighted_pullups", "bodyweight_pullups", "barbell_row"],
    "Upper Back": ["barbell_row", "weighted_pullups"],
    "Mid/Upper Back": ["barbell_row", "weighted_pullups"],
    "Middle-Traps": ["barbell_row"],
    "Trapezius": ["barbell_row"],
    "Lower Back": ["romanian_deadlift"],
    "Front-Shoulder": ["military_press", "barbell_bench_press"],
    "Anterior Delts": ["military_press", "barbell_bench_press"],
    "Middle-Shoulder": ["dumbbell_lateral_raise", "military_press"],
    "Medial Delts": ["dumbbell_lateral_raise", "military_press"],
    "Rear-Shoulder": ["barbell_row"],
    "Rear Delts": ["barbell_row"],
    "Biceps": ["barbell_bicep_curl"],
    "Triceps": ["triceps_extension", "weighted_dips", "barbell_bench_press"],
    "Calves": [],
    "Forearms": [],
    "Rectus Abdominis": [],
    "Abs/Core": [],
    "Neck": [],
    "External Obliques": [],
    "Obliques": [],
}


def _default(reason: str) -> dict[str, Any]:
    return {**DEFAULT_ESTIMATE, "reason": reason}


def classify_tier(exercise_row: dict[str, Any]) -> Tier:
    equipment = normalize_equipment(exercise_row.get("equipment"))
    if equipment in EXCLUDED_EQUIPMENT:
        return "excluded"

    mechanic = str(exercise_row.get("mechanic") or "").strip().lower()
    movement_pattern = str(exercise_row.get("movement_pattern") or "").strip().lower()
    if mechanic == "isolation" or movement_pattern in {"upper_isolation", "lower_isolation"}:
        return "isolated"

    name = str(exercise_row.get("exercise_name") or "").lower()
    if any(keyword in name for keyword in COMPLEX_ALLOWLIST):
        return "complex"

    return "accessory"


def epley_1rm(weight: float, reps: int) -> float:
    if reps <= 0 or weight <= 0:
        return 0.0
    capped_reps = min(reps, 12)
    return float(weight) * (1 + capped_reps / 30)


def round_weight(weight: float, equipment: Optional[str], tier: str) -> float:
    if weight <= 0:
        return 0.0

    normalized_equipment = normalize_equipment(equipment)
    if normalized_equipment == "Bodyweight":
        return 0.0

    if normalized_equipment in {"Barbell", "Trapbar", "Smith_Machine", "Plate"}:
        increment = 1.25
        floor = 20.0 if tier == "complex" else 1.25
    elif normalized_equipment == "Dumbbells":
        increment = 0.5 if weight < 10 else 1.0
        floor = 1.0
    elif normalized_equipment in {"Cables", "Machine", "Kettlebells", "Medicine_Ball"}:
        increment = 1.0
        floor = 1.0
    else:
        increment = 1.0
        floor = 1.0

    rounded = math.floor(weight / increment + 0.5) * increment
    return round(max(rounded, floor), 2)


def estimate_for_exercise(exercise_name: str, *, db: DatabaseHandler) -> dict[str, Any]:
    try:
        if not exercise_name or not exercise_name.strip():
            return _default("default_missing")

        exercise_row = db.fetch_one(
            """
            SELECT exercise_name, primary_muscle_group, equipment, mechanic, movement_pattern
            FROM exercises
            WHERE exercise_name = ? COLLATE NOCASE
            """,
            (exercise_name.strip(),),
        )
        if not exercise_row:
            return _default("default_missing")

        logged = _lookup_last_logged(exercise_row["exercise_name"], db)
        if logged:
            return logged

        profile_lifts = db.fetch_all(
            "SELECT lift_key, weight_kg, reps FROM user_profile_lifts"
        )
        preferences = db.fetch_all(
            "SELECT tier, rep_range FROM user_profile_preferences"
        )
        estimate = _estimate_from_profile(exercise_row, profile_lifts, preferences)
        if estimate:
            return estimate

        if classify_tier(exercise_row) == "excluded":
            return _default("default_excluded")
        return _default("default_no_reference")
    except Exception:
        logger.exception("Failed to estimate workout controls for %s", exercise_name)
        return _default("default_missing")


def _lookup_last_logged(exercise_name: str, db: DatabaseHandler) -> Optional[dict[str, Any]]:
    row = db.fetch_one(
        """
        SELECT
            COALESCE(scored_weight, planned_weight) AS weight,
            planned_sets AS sets,
            COALESCE(scored_min_reps, planned_min_reps) AS min_rep,
            COALESCE(scored_max_reps, planned_max_reps) AS max_rep,
            COALESCE(scored_rir, planned_rir) AS rir,
            COALESCE(scored_rpe, planned_rpe) AS rpe
        FROM workout_log
        WHERE exercise = ? COLLATE NOCASE
        ORDER BY id DESC
        LIMIT 1
        """,
        (exercise_name,),
    )
    if not row:
        return None

    default = DEFAULT_ESTIMATE
    return {
        "weight": float(row["weight"] if row["weight"] is not None else default["weight"]),
        "sets": int(row["sets"] if row["sets"] is not None else default["sets"]),
        "min_rep": int(row["min_rep"] if row["min_rep"] is not None else default["min_rep"]),
        "max_rep": int(row["max_rep"] if row["max_rep"] is not None else default["max_rep"]),
        "rir": int(row["rir"] if row["rir"] is not None else default["rir"]),
        "rpe": float(row["rpe"] if row["rpe"] is not None else default["rpe"]),
        "source": "log",
        "reason": "log",
    }


def _estimate_from_profile(
    exercise_row: dict[str, Any],
    profile_lifts: list[dict[str, Any]],
    preferences: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    tier = classify_tier(exercise_row)
    if tier == "excluded":
        return None

    primary_muscle = normalize_muscle(exercise_row.get("primary_muscle_group"))
    lift_chain = MUSCLE_TO_KEY_LIFT.get(primary_muscle or "", [])
    if not lift_chain:
        return None

    lifts_by_key = {row.get("lift_key"): row for row in profile_lifts}
    preference_by_tier = {
        row.get("tier"): row.get("rep_range")
        for row in preferences
        if row.get("tier") and row.get("rep_range")
    }
    preset_key = preference_by_tier.get(tier, DEFAULT_PREFERENCES[tier])
    preset = REP_RANGE_PRESETS[preset_key]

    for index, lift_key in enumerate(lift_chain):
        lift = lifts_by_key.get(lift_key)
        if not lift:
            continue

        reps = int(lift.get("reps") or 0)
        weight = float(lift.get("weight_kg") or 0)
        is_bodyweight_reference = lift_key.startswith("bodyweight_") and weight == 0
        if reps <= 0 or (weight <= 0 and not is_bodyweight_reference):
            continue

        cross_factor = CROSS_FALLBACK_FACTOR if index > 0 else 1.0
        reason = "profile_cross" if index > 0 else "profile"

        if is_bodyweight_reference:
            copied_reps = max(reps, 1)
            return {
                "weight": 0.0,
                "sets": PROFILE_DEFAULT_SETS,
                "min_rep": copied_reps,
                "max_rep": copied_reps,
                "rir": preset["rir"],
                "rpe": preset["rpe"],
                "source": "profile",
                "reason": reason,
            }

        reference_1rm = epley_1rm(weight, reps)
        if reference_1rm <= 0:
            continue

        target_1rm = reference_1rm * TIER_RATIOS[tier] * cross_factor
        working_weight = round_weight(
            target_1rm * preset["pct_1rm"],
            exercise_row.get("equipment"),
            tier,
        )
        return {
            "weight": working_weight,
            "sets": PROFILE_DEFAULT_SETS,
            "min_rep": preset["min_rep"],
            "max_rep": preset["max_rep"],
            "rir": preset["rir"],
            "rpe": preset["rpe"],
            "source": "profile",
            "reason": reason,
        }

    return None
