"""User-profile-based workout control estimates.

Dumbbell weight convention (Issue #10, 2026-04-27)
--------------------------------------------------
All dumbbell weights — both **inputs** (Reference Lifts on
``/user_profile``) and **outputs** (Workout Controls suggestions on
``/workout_plan``) — are expressed as **weight per hand**, i.e. the
mass of one dumbbell. A user holding 20 kg in each hand records 20 (not
40) for ``dumbbell_bench_press``, and the estimator returns 20 (not 40)
for the working weight on a dumbbell exercise.

The estimator math (``epley_1rm`` → ``TIER_RATIOS`` → ``REP_RANGE_PRESETS``
→ ``round_weight``) is unit-agnostic: it treats ``weight`` as a single
opaque scalar end-to-end. As long as input and output share the same
convention, no conversion is needed. Helper text on the questionnaire
and on the Workout Controls weight field communicates the convention to
the user; ``DUMBBELL_LIFT_KEYS`` and the ``is_dumbbell`` flag on the
estimate response drive the conditional UI.

See ``docs/user_profile/DESIGN.md`` §6.1 for the canonical statement.
"""
from __future__ import annotations

from typing import Any, Optional

from utils.database import DatabaseHandler
from utils.logger import get_logger
from utils.normalization import normalize_equipment, normalize_muscle

logger = get_logger()

# Cluster 1 constants & lookup tables now live in
# ``utils._profile_estimator.constants`` (WP2.1b, Deep Refactor Plan v3 Phase 2 —
# see docs/user_profile/PROFILE_ESTIMATOR_CLUSTERS.md). Re-exported here so the
# public ``utils.profile_estimator`` surface and every internal caller are
# unchanged. The ``lift_matching`` re-exports keep object identity, and
# ``strength_calibration`` still imports DEFAULT_ESTIMATE/KEY_LIFTS/classify_tier/
# epley_1rm from this facade at module load.
from utils._profile_estimator.constants import (  # noqa: F401
    _match_direct_lift_key,
    ACCURACY_MAJOR_MUSCLE_GROUPS,
    ADVANCED_COHORT_REACH,
    BODYMAP_MUSCLE_KEYS,
    COHORT_AGE_YEARS,
    COHORT_BODYWEIGHT_KG,
    COHORT_HEIGHT_CM,
    COLD_START_CANONICAL_COMPOUND,
    COLD_START_PRESET,
    COLD_START_RATIOS,
    COMPLEX_ALLOWLIST,
    CROSS_FALLBACK_FACTOR,
    DEFAULT_ESTIMATE,
    DEFAULT_PREFERENCES,
    DIRECT_LIFT_MATCHERS,
    DUMBBELL_LIFT_KEYS,
    EXCLUDED_EQUIPMENT,
    EXPERIENCE_MULTIPLIERS,
    EXPERIENCE_TIER_BOUNDS,
    EXPERIENCE_TIER_ORDER,
    HIGH_IMPACT_LIFT_PRIORITY,
    KEY_LIFT_LABELS,
    KEY_LIFT_SIDE,
    KEY_LIFT_TIER,
    KEY_LIFTS,
    match_direct_lift_key,
    MUSCLE_TO_KEY_LIFT,
    PROFILE_DEFAULT_SETS,
    REP_RANGE_PRESETS,
    Tier,
    TIER_RATIOS,
)
from utils._profile_estimator.core_math import (  # noqa: F401
    _classify_experience_tier,
    _COMPLEX_ALLOWLIST_NORMALIZED,
    _load_basis_factor,
    _normalize_for_matching,
    classify_tier,
    cold_start_1rm,
    epley_1rm,
    round_weight,
)
from utils._profile_estimator.traces import (  # noqa: F401
    _build_cold_start_trace,
    _build_default_trace,
    _build_learned_trace,
    _build_log_trace,
    _build_profile_bodyweight_trace,
    _build_profile_trace,
    _build_related_learned_trace,
    _default,
    _format_experience_label,
    _format_rounding_label,
)


from utils._profile_estimator.coverage import (  # noqa: F401
    _is_lift_filled,
    accuracy_band,
    cold_start_anchor_lifts,
    filled_lift_keys,
    next_high_impact_lifts,
    replaced_anchor_lifts,
)


from utils._profile_estimator.cohort import (  # noqa: F401
    _build_cohort_summary,
    _coerce_float,
    _format_cm,
    _format_kg,
    _format_years,
    _gender_label,
    _next_tier_multiplier,
    cohort_bars,
    cohort_ranges,
    coverage_donut,
)


from utils._profile_estimator.bodymap import (  # noqa: F401
    muscle_coverage_state,
)


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

        is_dumbbell = normalize_equipment(exercise_row.get("equipment")) == "Dumbbells"

        learned = _lookup_learned_calibration(exercise_row["exercise_name"], db)
        if learned:
            learned["is_dumbbell"] = is_dumbbell
            return learned

        logged = _lookup_last_logged(exercise_row["exercise_name"], db)
        if logged:
            logged["is_dumbbell"] = is_dumbbell
            return logged

        related = _lookup_related_learned_calibration(exercise_row, db)
        if related:
            related["is_dumbbell"] = is_dumbbell
            return related

        profile_lifts = db.fetch_all(
            "SELECT lift_key, weight_kg, reps FROM user_profile_lifts"
        )
        preferences = db.fetch_all(
            "SELECT tier, rep_range FROM user_profile_preferences"
        )
        estimate = _estimate_from_profile(exercise_row, profile_lifts, preferences)
        if estimate:
            estimate["is_dumbbell"] = is_dumbbell
            return estimate

        demographics = db.fetch_one(
            "SELECT gender, weight_kg, experience_years FROM user_profile WHERE id = 1"
        )
        cold_start = _estimate_from_cold_start(exercise_row, demographics)
        if cold_start:
            cold_start["is_dumbbell"] = is_dumbbell
            return cold_start

        if classify_tier(exercise_row) == "excluded":
            return _default("default_excluded", is_dumbbell=is_dumbbell)
        return _default("default_no_reference", is_dumbbell=is_dumbbell)
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
    weight = float(row["weight"] if row["weight"] is not None else default["weight"])
    min_rep = int(row["min_rep"] if row["min_rep"] is not None else default["min_rep"])
    max_rep = int(row["max_rep"] if row["max_rep"] is not None else default["max_rep"])
    return {
        "weight": weight,
        "sets": int(row["sets"] if row["sets"] is not None else default["sets"]),
        "min_rep": min_rep,
        "max_rep": max_rep,
        "rir": int(row["rir"] if row["rir"] is not None else default["rir"]),
        "rpe": float(row["rpe"] if row["rpe"] is not None else default["rpe"]),
        "source": "log",
        "reason": "log",
        "trace": _build_log_trace(
            weight=weight, reps_low=min_rep, reps_high=max_rep
        ),
    }


def _lookup_related_learned_calibration(
    exercise_row: dict[str, Any], db: DatabaseHandler
) -> Optional[dict[str, Any]]:
    """Read-only related learned estimate, after exact learned/log fallbacks."""
    from utils.strength_calibration import get_related_calibration_candidate

    candidate = get_related_calibration_candidate(exercise_row, db=db)
    if not candidate:
        return None

    target_tier = classify_tier(exercise_row)
    if target_tier == "excluded":
        return None

    preferences = db.fetch_all("SELECT tier, rep_range FROM user_profile_preferences")
    preference_by_tier = {
        row.get("tier"): row.get("rep_range")
        for row in preferences
        if row.get("tier") and row.get("rep_range")
    }
    preset_key = preference_by_tier.get(target_tier, DEFAULT_PREFERENCES[target_tier])
    preset = REP_RANGE_PRESETS[preset_key]

    try:
        target_1rm = float(candidate["target_estimated_1rm"])
    except (TypeError, ValueError):
        return None
    if target_1rm <= 0:
        return None

    pre_round_weight = target_1rm * preset["pct_1rm"]
    working_weight = round_weight(
        pre_round_weight,
        exercise_row.get("equipment"),
        target_tier,
    )
    return {
        "weight": working_weight,
        "sets": PROFILE_DEFAULT_SETS,
        "min_rep": preset["min_rep"],
        "max_rep": preset["max_rep"],
        "rir": preset["rir"],
        "rpe": preset["rpe"],
        "source": "related_learned",
        "reason": "related_calibration",
        "trace": _build_related_learned_trace(
            candidate,
            target_tier=target_tier,
            preset_key=preset_key,
            preset=preset,
            pre_round_weight=pre_round_weight,
            working_weight=working_weight,
            equipment=exercise_row.get("equipment"),
        ),
    }


def _lookup_learned_calibration(
    exercise_name: str, db: DatabaseHandler
) -> Optional[dict[str, Any]]:
    """Top-priority estimate from learned calibration, or None to fall through.

    Returns a suggestion only when the user has opted in (settings mode
    ``suggest``) AND a stored row exists with usable confidence. Anything else
    — mode ``off``/no settings row, no calibration row, or a ``low`` band —
    returns None so the existing last-log → Profile → cold-start chain runs
    unchanged (plan §"Estimate Priority" / §"Settings Default" regression
    guard). Imported lazily because ``strength_calibration`` imports from this
    module (avoids a circular import at load time).
    """
    from utils.strength_calibration import (
        USABLE_SUGGEST_CONFIDENCES,
        get_calibration_mode,
        get_learned_calibration,
    )

    if get_calibration_mode(db=db) != "suggest":
        return None
    row = get_learned_calibration(exercise_name, db=db)
    if not row or row.get("confidence") not in USABLE_SUGGEST_CONFIDENCES:
        return None
    if row.get("suggested_weight") is None:
        return None

    default = DEFAULT_ESTIMATE
    weight = float(row["suggested_weight"])
    min_rep = (
        int(row["suggested_min_reps"])
        if row.get("suggested_min_reps") is not None
        else default["min_rep"]
    )
    max_rep = (
        int(row["suggested_max_reps"])
        if row.get("suggested_max_reps") is not None
        else default["max_rep"]
    )
    return {
        "weight": weight,
        "sets": default["sets"],
        "min_rep": min_rep,
        "max_rep": max_rep,
        "rir": (
            int(row["suggested_rir"])
            if row.get("suggested_rir") is not None
            else default["rir"]
        ),
        "rpe": (
            float(row["suggested_rpe"])
            if row.get("suggested_rpe") is not None
            else default["rpe"]
        ),
        "source": "learned",
        "reason": "learned_calibration",
        "trace": _build_learned_trace(
            row, weight=weight, reps_low=min_rep, reps_high=max_rep
        ),
    }


# _match_direct_lift_key is now imported from utils.lift_matching (see top of
# this section). The backward-compatible alias is defined next to the import.


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

    target_is_per_hand = normalize_equipment(exercise_row.get("equipment")) == "Dumbbells"

    direct_lift_key = _match_direct_lift_key(exercise_row.get("exercise_name", ""))

    candidates: list[tuple[str, bool]] = []
    if direct_lift_key:
        candidates.append((direct_lift_key, False))
    for index, lift_key in enumerate(lift_chain):
        if direct_lift_key and lift_key == direct_lift_key:
            continue
        candidates.append((lift_key, index > 0 or direct_lift_key is not None))

    if not candidates:
        return None

    lifts_by_key = {row.get("lift_key"): row for row in profile_lifts}
    preference_by_tier = {
        row.get("tier"): row.get("rep_range")
        for row in preferences
        if row.get("tier") and row.get("rep_range")
    }
    preset_key = preference_by_tier.get(tier, DEFAULT_PREFERENCES[tier])
    preset = REP_RANGE_PRESETS[preset_key]

    for lift_key, is_cross in candidates:
        lift = lifts_by_key.get(lift_key)
        if not lift:
            continue

        reps = int(lift.get("reps") or 0)
        weight = float(lift.get("weight_kg") or 0)
        is_bodyweight_reference = lift_key.startswith("bodyweight_") and weight == 0
        if reps <= 0 or (weight <= 0 and not is_bodyweight_reference):
            continue

        cross_factor = CROSS_FALLBACK_FACTOR if is_cross else 1.0
        reason = "profile_cross" if is_cross else "profile"

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
                "trace": _build_profile_bodyweight_trace(
                    lift_key=lift_key,
                    reference_reps=copied_reps,
                    is_cross=is_cross,
                    preset_key=preset_key,
                    preset=preset,
                    target_exercise_name=exercise_row.get("exercise_name", ""),
                    target_primary_muscle=primary_muscle,
                ),
            }

        reference_1rm = epley_1rm(weight, reps)
        if reference_1rm <= 0:
            continue

        reference_tier = KEY_LIFT_TIER.get(lift_key, "complex")
        tier_multiplier = min(
            TIER_RATIOS[tier] / TIER_RATIOS[reference_tier],
            1.0,
        )
        basis_factor = _load_basis_factor(lift_key, target_is_per_hand)
        target_1rm = reference_1rm * tier_multiplier * cross_factor * basis_factor
        pre_round_weight = target_1rm * preset["pct_1rm"]
        working_weight = round_weight(
            pre_round_weight,
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
            "trace": _build_profile_trace(
                lift_key=lift_key,
                reference_weight=weight,
                reference_reps=reps,
                is_cross=is_cross,
                reference_1rm=reference_1rm,
                reference_tier=reference_tier,
                target_tier=tier,
                tier_multiplier=tier_multiplier,
                cross_factor=cross_factor,
                basis_factor=basis_factor,
                preset_key=preset_key,
                preset=preset,
                target_1rm=target_1rm,
                pre_round_weight=pre_round_weight,
                working_weight=working_weight,
                equipment=exercise_row.get("equipment"),
                target_exercise_name=exercise_row.get("exercise_name", ""),
                target_primary_muscle=primary_muscle,
            ),
        }

    return None


def _estimate_from_cold_start(
    exercise_row: dict[str, Any],
    demographics: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Wrap :func:`cold_start_1rm` into the standard estimate response shape.

    Forces the Light preset so the seeded suggestion errs toward
    under-prescription, since the user has no measured data yet.
    """
    target_tier = classify_tier(exercise_row)
    if target_tier == "excluded":
        return None

    base_1rm = cold_start_1rm(exercise_row, demographics)
    if base_1rm is None or base_1rm <= 0:
        return None

    tier_multiplier = TIER_RATIOS[target_tier] / TIER_RATIOS["complex"]
    preset = REP_RANGE_PRESETS[COLD_START_PRESET]
    target_1rm = base_1rm * tier_multiplier
    pre_round_weight = target_1rm * preset["pct_1rm"]
    working_weight = round_weight(
        pre_round_weight,
        exercise_row.get("equipment"),
        target_tier,
    )

    primary_muscle = normalize_muscle(exercise_row.get("primary_muscle_group")) or ""
    gender = (demographics or {}).get("gender") or ""
    bodyweight = float((demographics or {}).get("weight_kg") or 0)
    experience_years = (demographics or {}).get("experience_years")
    experience_tier = _classify_experience_tier(experience_years)
    experience_multiplier = EXPERIENCE_MULTIPLIERS[experience_tier]
    ratio = COLD_START_RATIOS.get((primary_muscle, gender), 0.0)

    return {
        "weight": working_weight,
        "sets": PROFILE_DEFAULT_SETS,
        "min_rep": preset["min_rep"],
        "max_rep": preset["max_rep"],
        "rir": preset["rir"],
        "rpe": preset["rpe"],
        "source": "cold_start",
        "reason": "profile_cold_start",
        "trace": _build_cold_start_trace(
            target_exercise_name=exercise_row.get("exercise_name", ""),
            target_tier=target_tier,
            target_primary_muscle=primary_muscle,
            base_1rm=base_1rm,
            bodyweight=bodyweight,
            gender=gender,
            ratio=ratio,
            experience_tier=experience_tier,
            experience_years=experience_years,
            experience_multiplier=experience_multiplier,
            tier_multiplier=tier_multiplier,
            target_1rm=target_1rm,
            preset=preset,
            pre_round_weight=pre_round_weight,
            working_weight=working_weight,
            equipment=exercise_row.get("equipment"),
        ),
    }
