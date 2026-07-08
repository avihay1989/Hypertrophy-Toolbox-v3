"""Core-math primitives for the profile estimator.

Near-leaf numeric and classification helpers extracted verbatim from
:mod:`utils.profile_estimator` (WP2.1c, Deep Refactor Plan v3 Phase 2 — see
``docs/user_profile/PROFILE_ESTIMATOR_CLUSTERS.md`` §2/§6). These names are
re-exported by the :mod:`utils.profile_estimator` facade; import them from
there, not from this internal module. This module takes no
``strength_calibration`` import — the ``profile_estimator ⇄ strength_calibration``
cycle is held only by the two function-local lazy imports in the orchestration
core, which stay in the facade.
"""
from __future__ import annotations

import math
from typing import Any, Optional

from utils.normalization import normalize_equipment, normalize_muscle

from utils._profile_estimator.constants import (
    COLD_START_RATIOS,
    COMPLEX_ALLOWLIST,
    DUMBBELL_LIFT_KEYS,
    EXCLUDED_EQUIPMENT,
    EXPERIENCE_MULTIPLIERS,
    EXPERIENCE_TIER_BOUNDS,
    Tier,
)


def _normalize_for_matching(text: str) -> str:
    """Lowercase, replace hyphens with spaces, and strip a single trailing
    `s` from each word so that plural/hyphen variants ("Pull Ups", "Chin-Ups",
    "Hip Thrusts") collapse to the same canonical form as the allowlist
    keywords. Both the exercise name and each COMPLEX_ALLOWLIST keyword are
    normalised the same way at match time, so the allowlist stays the source
    of truth without needing an entry per variant.
    """
    if not text:
        return ""
    lowered = text.lower().replace("-", " ")
    words = []
    for word in lowered.split():
        if len(word) > 1 and word.endswith("s"):
            word = word[:-1]
        words.append(word)
    return " ".join(words)


_COMPLEX_ALLOWLIST_NORMALIZED: tuple[str, ...] = tuple(
    _normalize_for_matching(keyword) for keyword in COMPLEX_ALLOWLIST
)


def classify_tier(exercise_row: dict[str, Any]) -> Tier:
    equipment = normalize_equipment(exercise_row.get("equipment"))
    if equipment in EXCLUDED_EQUIPMENT:
        return "excluded"

    mechanic = str(exercise_row.get("mechanic") or "").strip().lower()
    movement_pattern = str(exercise_row.get("movement_pattern") or "").strip().lower()
    if mechanic == "isolation" or movement_pattern in {"upper_isolation", "lower_isolation"}:
        return "isolated"

    name = _normalize_for_matching(str(exercise_row.get("exercise_name") or ""))
    if any(keyword in name for keyword in _COMPLEX_ALLOWLIST_NORMALIZED):
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


def _load_basis_factor(reference_lift_key: str, target_is_per_hand: bool) -> float:
    """Reconcile per-hand (dumbbell) vs total (barbell/machine) load bases.

    Dumbbell loads — references in ``DUMBBELL_LIFT_KEYS`` and dumbbell-equipment
    targets — are expressed **per hand**; everything else is a single total /
    system load (see the module docstring, Issue #10). The estimator math is
    otherwise unit-agnostic, so a total-load reference fed into a per-hand
    target (or vice versa) is off by ~2× with no correction. When the two
    disagree, convert with the simple "two dumbbells = one barbell" model:
      - per-hand reference → total target: ×2
      - total reference → per-hand target: ÷2
    Same-basis pairs return 1.0 (no conversion).
    """
    reference_is_per_hand = reference_lift_key in DUMBBELL_LIFT_KEYS
    if reference_is_per_hand == target_is_per_hand:
        return 1.0
    return 2.0 if reference_is_per_hand else 0.5


def _classify_experience_tier(experience_years: Optional[float]) -> str:
    """Map raw experience years into the cold-start strength tier."""
    if experience_years is None:
        return "novice"
    try:
        years = float(experience_years)
    except (TypeError, ValueError):
        return "novice"
    if years < 0:
        return "novice"
    for label, upper in EXPERIENCE_TIER_BOUNDS:
        if years <= upper:
            return label
    return "advanced"


def cold_start_1rm(
    exercise_row: dict[str, Any],
    demographics: Optional[dict[str, Any]],
) -> Optional[float]:
    """Population-table 1RM seed for an exercise from demographics alone.

    Issue #16: fires only as a last-resort fallback when the user has filled
    Demographics but no reference lifts. Returns ``None`` if essential
    demographics are missing, the equipment can't be modelled (Dumbbells /
    Bodyweight / Trx etc.), or the primary muscle has no entry in
    :data:`COLD_START_RATIOS`. The chain in
    :func:`_estimate_from_cold_start` then applies the existing tier ratio
    so accessory / isolation targets are scaled down from the
    complex-tier seed.
    """
    if not demographics:
        return None

    gender = demographics.get("gender")
    if gender not in {"M", "F"}:
        return None

    weight_kg = demographics.get("weight_kg")
    try:
        bodyweight = float(weight_kg) if weight_kg is not None else 0.0
    except (TypeError, ValueError):
        return None
    if bodyweight <= 0:
        return None

    equipment = normalize_equipment(exercise_row.get("equipment"))
    if equipment in EXCLUDED_EQUIPMENT or equipment in {"Dumbbells", "Bodyweight"}:
        return None

    primary_muscle = normalize_muscle(exercise_row.get("primary_muscle_group"))
    if not primary_muscle:
        return None

    ratio = COLD_START_RATIOS.get((primary_muscle, gender))
    if ratio is None:
        return None

    tier = _classify_experience_tier(demographics.get("experience_years"))
    multiplier = EXPERIENCE_MULTIPLIERS[tier]

    return bodyweight * ratio * multiplier
