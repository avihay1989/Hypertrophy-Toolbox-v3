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

import math
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


# Issue #17 — Deliverable C — accuracy-improvement guidance.
# Computed server-side at Profile-page render time (and re-rendered after
# the user saves the Reference Lifts form via the Issue #17 JS handler).


def _is_lift_filled(lift_row: Optional[dict[str, Any]]) -> bool:
    """A lift counts as filled when the user has saved both a weight (or zero
    for bodyweight slugs) AND a non-zero rep count. Matches the gate inside
    `_estimate_from_profile` — a lift with only one half stored can't seed
    a 1RM, so it shouldn't bump the accuracy band either.
    """
    if not lift_row:
        return False
    reps = lift_row.get("reps")
    weight = lift_row.get("weight_kg")
    if reps is None or weight is None:
        return False
    try:
        reps_int = int(reps)
    except (TypeError, ValueError):
        return False
    if reps_int <= 0:
        return False
    try:
        weight_float = float(weight)
    except (TypeError, ValueError):
        return False
    lift_key = lift_row.get("lift_key") or ""
    if lift_key.startswith("bodyweight_"):
        return weight_float >= 0
    return weight_float > 0


def filled_lift_keys(profile_lifts: list[dict[str, Any]]) -> set[str]:
    """Return the set of lift_keys with a usable (weight, reps) pair stored."""
    filled: set[str] = set()
    for row in profile_lifts:
        if _is_lift_filled(row):
            key = row.get("lift_key")
            if isinstance(key, str):
                filled.add(key)
    return filled


def accuracy_band(
    *,
    profile_lifts: list[dict[str, Any]],
    demographics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Compute the user's overall estimator-accuracy band + copy.

    Bands (matching Issue #17 §C):
    - ``population_only`` — no reference lifts saved (demographics may exist).
    - ``partial`` — 1–4 reference lifts saved.
    - ``mostly`` — 5+ reference lifts AND every major muscle group has at
      least one saved entry.
    - ``fully`` — all `KEY_LIFTS` slugs saved.
    """
    filled = filled_lift_keys(profile_lifts)
    filled_count = len(filled)
    total_slugs = len(KEY_LIFTS)
    has_demographics = bool(
        demographics
        and (
            demographics.get("gender")
            or demographics.get("weight_kg")
            or demographics.get("experience_years")
        )
    )

    if filled_count >= total_slugs:
        band = "fully"
        copy = (
            "All your suggestions use your measured lifts. "
            "Re-enter your reference lifts when you set a new PR to keep them current."
        )
    elif filled_count >= 5 and all(
        any(slug in filled for slug in slugs)
        for _, slugs in ACCURACY_MAJOR_MUSCLE_GROUPS
    ):
        band = "mostly"
        copy = (
            "Most of your suggestions use your real data. "
            "Add the lifts below to refine the remaining estimates."
        )
    elif filled_count >= 1:
        band = "partial"
        copy = (
            "About a third of your suggestions use your real data. "
            "Add the lifts below to lift this further."
        )
    else:
        band = "population_only"
        copy = (
            "Numbers come from population averages. "
            "Add even one reference lift to start personalising."
            if has_demographics
            else "No reference lifts or demographics saved yet — "
            "fill in either to start personalising your suggestions."
        )

    return {
        "band": band,
        "filled_count": filled_count,
        "total_count": total_slugs,
        "copy": copy,
    }


def next_high_impact_lifts(
    profile_lifts: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, str]]:
    """Return the top-`limit` reference lifts the user has NOT yet saved,
    in priority order. Each entry exposes both the slug and its display
    label so the UI can render either."""
    filled = filled_lift_keys(profile_lifts)
    out: list[dict[str, str]] = []
    for slug in HIGH_IMPACT_LIFT_PRIORITY:
        if slug in filled:
            continue
        label = KEY_LIFT_LABELS.get(slug)
        if not label:
            continue
        out.append({"lift_key": slug, "label": label})
        if len(out) >= limit:
            break
    return out


def cold_start_anchor_lifts(
    demographics: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the cold-start 1RM seed for each canonical compound used by
    the "How the system sees you" card.

    Each entry: ``{"lift_key", "label", "muscle", "weight_1rm"}``.
    `weight_1rm` is the rounded-to-the-half-kg complex-tier 1RM seed
    (i.e. the ``base_1rm`` from :func:`cold_start_1rm`, before tier and
    preset scaling). ``None`` if demographics are too incomplete to seed
    a number for that muscle.
    """
    out: list[dict[str, Any]] = []
    for muscle, slug in COLD_START_CANONICAL_COMPOUND.items():
        seed = cold_start_1rm(
            {"primary_muscle_group": muscle, "equipment": "Barbell"},
            demographics,
        )
        out.append(
            {
                "lift_key": slug,
                "label": KEY_LIFT_LABELS.get(slug, slug),
                "muscle": muscle,
                "weight_1rm": (
                    round(float(seed), 1) if seed is not None and seed > 0 else None
                ),
            }
        )
    return out


def replaced_anchor_lifts(
    profile_lifts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return canonical-compound lifts the user has filled in. Used by the
    "Replaced by your data" panel of the "How the system sees you" card.

    Each entry: ``{"lift_key", "label", "muscle", "weight_kg", "reps",
    "estimated_1rm"}``. Skips bodyweight slugs (no useful 1RM number)."""
    lifts_by_key = {
        row.get("lift_key"): row
        for row in profile_lifts
        if isinstance(row.get("lift_key"), str)
    }
    out: list[dict[str, Any]] = []
    for muscle, slug in COLD_START_CANONICAL_COMPOUND.items():
        lift = lifts_by_key.get(slug)
        if not _is_lift_filled(lift):
            continue
        if slug.startswith("bodyweight_"):
            continue
        weight = float(lift.get("weight_kg") or 0)
        reps = int(lift.get("reps") or 0)
        if weight <= 0 or reps <= 0:
            continue
        out.append(
            {
                "lift_key": slug,
                "label": KEY_LIFT_LABELS.get(slug, slug),
                "muscle": muscle,
                "weight_kg": weight,
                "reps": reps,
                "estimated_1rm": round(epley_1rm(weight, reps), 1),
            }
        )
    return out


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _format_kg(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:g} kg"


def _format_cm(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:g} cm"


def _format_years(value: Optional[float]) -> str:
    if value is None:
        return "—"
    if float(value).is_integer():
        return f"{int(value)} yrs"
    return f"{value:g} yrs"


def _gender_label(gender: Optional[str]) -> Optional[str]:
    if gender == "M":
        return "Male"
    if gender == "F":
        return "Female"
    return None


def _next_tier_multiplier(tier: str) -> float:
    """Return the multiplier for the tier above ``tier``. For advanced, an
    extrapolated 'elite reach' multiplier keeps the bar chart's right anchor
    above the user's marker without introducing a new tier in the table."""
    if tier in EXPERIENCE_TIER_ORDER:
        idx = EXPERIENCE_TIER_ORDER.index(tier)
        if idx < len(EXPERIENCE_TIER_ORDER) - 1:
            return EXPERIENCE_MULTIPLIERS[EXPERIENCE_TIER_ORDER[idx + 1]]
    return EXPERIENCE_MULTIPLIERS["advanced"] * ADVANCED_COHORT_REACH


def cohort_ranges(
    demographics: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Static reference cohort buckets keyed off the user's demographics.

    Returns four tiles (bodyweight, height, age, experience) plus the
    classifier metadata (tier, multiplier, next-tier multiplier) used by
    the cohort bar chart. The helper is **read-only** — it never mutates
    or drives the estimator output. Tiles for inputs the estimator does
    NOT yet consume (height, age) are flagged ``used=False`` so the UI
    can de-emphasise them and explain why the value is collected but
    not yet load-bearing.
    """
    demos = demographics or {}
    raw_gender = demos.get("gender") if demos.get("gender") in {"M", "F"} else None
    bodyweight = _coerce_float(demos.get("weight_kg"))
    height = _coerce_float(demos.get("height_cm"))
    age = _coerce_float(demos.get("age"))
    experience_years = _coerce_float(demos.get("experience_years"))

    tier = (
        _classify_experience_tier(experience_years)
        if experience_years is not None
        else None
    )
    tier_multiplier = (
        EXPERIENCE_MULTIPLIERS[tier] if tier else None
    )
    next_tier = (
        EXPERIENCE_TIER_ORDER[
            min(
                EXPERIENCE_TIER_ORDER.index(tier) + 1,
                len(EXPERIENCE_TIER_ORDER) - 1,
            )
        ]
        if tier
        else None
    )
    next_tier_multiplier = _next_tier_multiplier(tier) if tier else None

    bodyweight_low, bodyweight_high = (
        COHORT_BODYWEIGHT_KG[raw_gender] if raw_gender else (None, None)
    )
    height_low, height_high = (
        COHORT_HEIGHT_CM[raw_gender] if raw_gender else (None, None)
    )
    age_low, age_high = COHORT_AGE_YEARS

    bodyweight_tile = {
        "value_text": _format_kg(bodyweight),
        "value_raw": bodyweight,
        "cohort_text": (
            f"Cohort: {bodyweight_low:g}–{bodyweight_high:g} kg"
            f" ({_gender_label(raw_gender).lower()} {tier})"
            if raw_gender and bodyweight_low is not None and tier
            else f"Cohort: {bodyweight_low:g}–{bodyweight_high:g} kg ({_gender_label(raw_gender).lower()})"
            if raw_gender and bodyweight_low is not None
            else "Cohort range needs gender"
        ),
        "cohort_low": bodyweight_low,
        "cohort_high": bodyweight_high,
        "empty": bodyweight is None,
        "empty_text": "Add bodyweight to enable",
        "used": True,
    }
    height_tile = {
        "value_text": _format_cm(height),
        "value_raw": height,
        "cohort_text": (
            f"Cohort: {height_low:g}–{height_high:g} cm ({_gender_label(raw_gender).lower()})"
            if raw_gender and height_low is not None
            else "Cohort range needs gender"
        ),
        "cohort_low": height_low,
        "cohort_high": height_high,
        "empty": height is None,
        "empty_text": "Add height (currently unused — flagged for future use)",
        "used": False,
        "unused_reason": "Currently unused (collected, not in formula)",
    }
    age_tile = {
        "value_text": _format_years(age),
        "value_raw": age,
        "cohort_text": f"Cohort: {age_low:g}–{age_high:g} yrs",
        "cohort_low": age_low,
        "cohort_high": age_high,
        "empty": age is None,
        "empty_text": "Add age (currently unused)",
        "used": False,
        "unused_reason": "Currently unused (collected, not in formula)",
    }
    experience_tile = {
        "value_text": tier.title() if tier else "—",
        "value_raw": experience_years,
        "years_text": _format_years(experience_years) if experience_years is not None else None,
        "cohort_text": (
            f"Tier multiplier: ×{tier_multiplier:.2f} of trained max"
            if tier_multiplier is not None
            else "Tier multiplier: —"
        ),
        "tier": tier,
        "tier_multiplier": tier_multiplier,
        "empty": tier is None,
        "empty_text": "Pick a level to enable cold-start estimates",
        "used": True,
    }

    summary = _build_cohort_summary(
        gender_label=_gender_label(raw_gender),
        age_low=age_low,
        age_high=age_high,
        bodyweight_tile=bodyweight_tile,
        experience_tile=experience_tile,
    )

    return {
        "tier": tier,
        "tier_multiplier": tier_multiplier,
        "next_tier": next_tier,
        "next_tier_multiplier": next_tier_multiplier,
        "tiles": {
            "bodyweight": bodyweight_tile,
            "height": height_tile,
            "age": age_tile,
            "experience": experience_tile,
        },
        "summary": summary,
    }


def _build_cohort_summary(
    *,
    gender_label: Optional[str],
    age_low: float,
    age_high: float,
    bodyweight_tile: dict[str, Any],
    experience_tile: dict[str, Any],
) -> str:
    """One-line plain-language summary of the cohort the estimator is
    calibrated to. Empty fields render as ``"unknown"`` so the user can
    see what's missing at a glance."""
    gender_text = gender_label.lower() if gender_label else "unknown gender"
    age_text = f"age {age_low:g}–{age_high:g}"
    bw_low = bodyweight_tile.get("cohort_low")
    bw_high = bodyweight_tile.get("cohort_high")
    bodyweight_text = (
        f"bodyweight {bw_low:g}–{bw_high:g} kg"
        if bw_low is not None and bw_high is not None
        else "bodyweight unknown"
    )
    tier = experience_tile.get("tier")
    years_text = experience_tile.get("years_text")
    experience_text = (
        f"{tier} ({years_text} trained)"
        if tier and years_text
        else "experience level unknown"
    )

    missing = (not gender_label) or experience_text == "experience level unknown"
    parts = [gender_text, age_text, bodyweight_text, experience_text]
    body = ", ".join(parts)
    if missing:
        return f"Estimator cohort: {body} — fill these to calibrate."
    return (
        f"Estimator cohort: {body}. "
        "Suggestions are calibrated to lifters in this bucket."
    )


def cohort_bars(
    profile_lifts: list[dict[str, Any]],
    demographics: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One bar-chart row per filled canonical-compound reference lift.

    Each row carries the user's Epley-derived 1RM, the cold-start anchor
    1RM the estimator would otherwise have used, and a cohort upper
    bound (one tier up). Bodyweight slugs are skipped — there's no
    meaningful kg comparison. Rows where the cold-start anchor cannot be
    computed (incomplete demographics, muscle outside `COLD_START_RATIOS`)
    are skipped: the bar chart only renders when the comparison is
    well-defined.
    """
    demos = demographics or {}
    if demos.get("gender") not in {"M", "F"} or _coerce_float(demos.get("weight_kg")) is None:
        return []

    tier = _classify_experience_tier(demos.get("experience_years"))
    current_multiplier = EXPERIENCE_MULTIPLIERS[tier]
    next_multiplier = _next_tier_multiplier(tier)

    lifts_by_key = {
        row.get("lift_key"): row
        for row in profile_lifts
        if isinstance(row.get("lift_key"), str)
    }

    out: list[dict[str, Any]] = []
    for muscle, slug in COLD_START_CANONICAL_COMPOUND.items():
        if slug.startswith("bodyweight_"):
            continue
        lift = lifts_by_key.get(slug)
        if not _is_lift_filled(lift):
            continue
        weight = float(lift.get("weight_kg") or 0)
        reps = int(lift.get("reps") or 0)
        if weight <= 0 or reps <= 0:
            continue

        cold_start = cold_start_1rm(
            {"primary_muscle_group": muscle, "equipment": "Barbell"},
            demos,
        )
        if cold_start is None or cold_start <= 0:
            continue

        user_1rm = epley_1rm(weight, reps)
        cohort_upper = cold_start * (next_multiplier / current_multiplier)
        max_kg = max(cold_start, user_1rm, cohort_upper) * 1.05
        min_kg = 0.0

        out.append(
            {
                "lift_key": slug,
                "label": KEY_LIFT_LABELS.get(slug, slug),
                "muscle": muscle,
                "user_1rm_kg": round(user_1rm, 1),
                "cold_start_1rm_kg": round(cold_start, 1),
                "cohort_upper_kg": round(cohort_upper, 1),
                "max_kg": round(max_kg, 1),
                "min_kg": min_kg,
            }
        )
    return out


def coverage_donut(
    profile_lifts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compact circular-progress payload for the "How the system sees you"
    card. Mirrors `accuracy_band()` counts but in donut shape so the same
    metric reads more glanceably."""
    filled = filled_lift_keys(profile_lifts)
    filled_count = len(filled)
    total_count = len(KEY_LIFTS)
    pct = (filled_count / total_count) if total_count > 0 else 0.0
    return {
        "filled_count": filled_count,
        "total_count": total_count,
        "percent": round(pct * 100, 1),
    }


def muscle_coverage_state(
    profile_lifts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Per-muscle coverage state powering the Profile-page bodymap.

    For each backend muscle key in :data:`BODYMAP_MUSCLE_KEYS`, return one
    of four states:

    * ``"measured"`` — the **first** lift in
      :data:`MUSCLE_TO_KEY_LIFT[muscle]` is filled. The estimator will
      use it directly (no cross-muscle penalty).
    * ``"cross_muscle"`` — at least one chain entry is filled but the
      first slot isn't, so the estimator borrows from a fallback lift
      with the cross-factor penalty.
    * ``"cold_start_only"`` — the chain has entries but none are filled.
      Suggestions for this muscle fall back to the cold-start population
      estimate (or the default if demographics are also missing).
    * ``"not_assessed"`` — the chain is empty (e.g. ``Forearms``,
      ``Neck``). The estimator never seeds suggestions for these muscles.

    Each entry also exposes the ordered chain, the filled lifts (for
    popover bodies), and a recommended improvement lift (the first
    unfilled slug in the chain) so the JS layer can mount popovers
    without re-querying the estimator.
    """
    lifts_by_key = {
        row.get("lift_key"): row
        for row in profile_lifts
        if isinstance(row.get("lift_key"), str)
    }

    out: dict[str, dict[str, Any]] = {}
    for muscle in BODYMAP_MUSCLE_KEYS:
        chain = MUSCLE_TO_KEY_LIFT.get(muscle, [])
        chain_entries: list[dict[str, Any]] = []
        filled_entries: list[dict[str, Any]] = []
        first_filled_idx: Optional[int] = None
        for idx, slug in enumerate(chain):
            label = KEY_LIFT_LABELS.get(slug, slug)
            lift_row = lifts_by_key.get(slug)
            is_filled = _is_lift_filled(lift_row)
            entry: dict[str, Any] = {
                "lift_key": slug,
                "label": label,
                "filled": is_filled,
            }
            if is_filled and lift_row is not None:
                weight = float(lift_row.get("weight_kg") or 0)
                reps = int(lift_row.get("reps") or 0)
                entry["weight_kg"] = weight
                entry["reps"] = reps
                if not slug.startswith("bodyweight_") and weight > 0 and reps > 0:
                    entry["estimated_1rm"] = round(epley_1rm(weight, reps), 1)
                if first_filled_idx is None:
                    first_filled_idx = idx
                filled_entries.append(entry)
            chain_entries.append(entry)

        if not chain:
            state = "not_assessed"
        elif first_filled_idx == 0:
            state = "measured"
        elif first_filled_idx is not None:
            state = "cross_muscle"
        else:
            state = "cold_start_only"

        primary_slug: Optional[str] = chain[0] if chain else None
        improvement_slug: Optional[str] = None
        if state in {"cross_muscle", "cold_start_only"}:
            for entry in chain_entries:
                if not entry["filled"]:
                    improvement_slug = entry["lift_key"]
                    break

        out[muscle] = {
            "muscle": muscle,
            "state": state,
            "chain": chain_entries,
            "filled": filled_entries,
            "primary_lift_key": primary_slug,
            "primary_lift_label": (
                KEY_LIFT_LABELS.get(primary_slug, primary_slug) if primary_slug else None
            ),
            "improvement_lift_key": improvement_slug,
            "improvement_lift_label": (
                KEY_LIFT_LABELS.get(improvement_slug, improvement_slug)
                if improvement_slug
                else None
            ),
        }
    return out
