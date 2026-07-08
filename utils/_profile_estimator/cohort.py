"""Cluster 4 — cohort ranges/bars/donut for the profile estimator.

Cohort reference-range, bar-chart, and coverage-donut helpers extracted
verbatim from :mod:`utils.profile_estimator` (WP2.1e, Deep Refactor Plan v3
Phase 2 — see ``docs/user_profile/PROFILE_ESTIMATOR_CLUSTERS.md`` §2/§3).
These names are re-exported by the :mod:`utils.profile_estimator` facade;
import them from there, not from this internal module. Depends on the
constants leaf, the core-math primitives, and the coverage leaf only — no
``strength_calibration`` import (the estimator cycle stays held by the
facade's function-local lazy imports).
"""
from __future__ import annotations

import math
from typing import Any, Optional

from utils._profile_estimator.constants import (
    ADVANCED_COHORT_REACH,
    COHORT_AGE_YEARS,
    COHORT_BODYWEIGHT_KG,
    COHORT_HEIGHT_CM,
    COLD_START_CANONICAL_COMPOUND,
    EXPERIENCE_MULTIPLIERS,
    EXPERIENCE_TIER_ORDER,
    KEY_LIFT_LABELS,
    KEY_LIFTS,
)
from utils._profile_estimator.core_math import (
    _classify_experience_tier,
    cold_start_1rm,
    epley_1rm,
)
from utils._profile_estimator.coverage import (
    _is_lift_filled,
    filled_lift_keys,
)


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
