"""Trace builders for the profile estimator.

"Show the math" trace dictionaries extracted verbatim from
:mod:`utils.profile_estimator` (WP2.1c, Deep Refactor Plan v3 Phase 2 — see
``docs/user_profile/PROFILE_ESTIMATOR_CLUSTERS.md`` §2). These names are
re-exported by the :mod:`utils.profile_estimator` facade; import them from
there, not from this internal module. Depends only on the constants leaf and
``utils.normalization`` — no ``strength_calibration`` import (the estimator
cycle stays held by the facade's function-local lazy imports) and no core-math
dependency.
"""
from __future__ import annotations

from typing import Any, Optional

from utils.normalization import normalize_equipment

from utils._profile_estimator.constants import (
    COLD_START_CANONICAL_COMPOUND,
    DEFAULT_ESTIMATE,
    KEY_LIFT_LABELS,
    MUSCLE_TO_KEY_LIFT,
    Tier,
    _match_direct_lift_key,
)


def _default(reason: str, *, is_dumbbell: bool = False) -> dict[str, Any]:
    return {
        **DEFAULT_ESTIMATE,
        "reason": reason,
        "is_dumbbell": is_dumbbell,
        "trace": _build_default_trace(reason),
    }


def _format_experience_label(tier: str, years: Optional[float]) -> str:
    """Render an experience tier as `intermediate (3 yrs)` for trace copy."""
    if years is None:
        return tier
    try:
        return f"{tier} ({float(years):g} yrs)"
    except (TypeError, ValueError):
        return tier


def _format_rounding_label(equipment: Optional[str]) -> str:
    eq = normalize_equipment(equipment)
    if eq in {"Barbell", "Trapbar", "Smith_Machine", "Plate"}:
        return "barbell (1.25 kg increments)"
    if eq == "Dumbbells":
        return "dumbbell (per-hand, 0.5–1.0 kg increments)"
    if eq in {"Cables", "Machine", "Kettlebells", "Medicine_Ball"}:
        return "machine (1.0 kg increments)"
    if eq == "Bodyweight":
        return "bodyweight (no added load)"
    return "default (1.0 kg increments)"


def _build_default_trace(reason: str) -> dict[str, Any]:
    if reason == "default_excluded":
        return {
            "source": "default",
            "steps": [
                {
                    "label": "Equipment is not modelled by the estimator",
                    "detail": "TRX / BOSU / Cardio / Recovery / Yoga / Stretches / Bands are intentionally skipped.",
                },
                {
                    "label": "Default values used",
                    "detail": "Adjust the Workout Controls manually for this exercise.",
                },
            ],
        }
    if reason == "default_missing":
        return {
            "source": "default",
            "steps": [
                {
                    "label": "Exercise not found",
                    "detail": "No matching row in the exercise catalogue — defaults shown.",
                },
            ],
        }
    return {
        "source": "default",
        "steps": [
            {
                "label": "No reference data available",
                "detail": "No saved reference lift, no demographics, and no logged set yet for this exercise.",
            },
        ],
        "improvement_hint": {
            "action": "enter_reference_lift",
            "lift_key": None,
            "copy": (
                "Fill in your Demographics or any Reference Lift on the Profile "
                "page to start personalising this suggestion."
            ),
        },
    }


def _build_log_trace(
    *, weight: float, reps_low: int, reps_high: int
) -> dict[str, Any]:
    if reps_low == reps_high:
        rep_label = f"{reps_low}"
    else:
        rep_label = f"{reps_low}–{reps_high}"
    return {
        "source": "log",
        "steps": [
            {
                "label": "Most recent logged set wins",
                "value": f"{weight:g} kg × {rep_label}",
                "detail": (
                    "Suggestion mirrors what you actually performed last time you "
                    "logged this exercise — measured data overrides reference-lift "
                    "and cold-start estimates."
                ),
            },
        ],
    }


def _build_profile_trace(
    *,
    lift_key: str,
    reference_weight: float,
    reference_reps: int,
    is_cross: bool,
    reference_1rm: float,
    reference_tier: Tier,
    target_tier: Tier,
    tier_multiplier: float,
    cross_factor: float,
    basis_factor: float,
    preset_key: str,
    preset: dict[str, Any],
    target_1rm: float,
    pre_round_weight: float,
    working_weight: float,
    equipment: Optional[str],
    target_exercise_name: str,
    target_primary_muscle: Optional[str],
) -> dict[str, Any]:
    label_friendly = KEY_LIFT_LABELS.get(lift_key, lift_key)
    pct = preset["pct_1rm"]

    detail_for_reference = (
        "Cross-muscle fallback — the target exercise isn't a direct match "
        "for any of your saved reference lifts."
        if is_cross
        else "Direct match — this is the questionnaire entry that maps to the target exercise."
    )

    steps: list[dict[str, Any]] = [
        {
            "label": "Reference lift",
            "value": f"{label_friendly} {reference_weight:g} kg × {reference_reps:g}",
            "detail": detail_for_reference,
        },
        {
            "label": "Estimated 1RM (Epley)",
            "value": round(reference_1rm, 1),
            "unit": "kg",
            "detail": f"Epley({reference_weight:g}, {reference_reps:g}) ≈ {round(reference_1rm, 1)} kg",
        },
        {
            "label": f"Tier scaling: {reference_tier} → {target_tier}",
            "factor": round(tier_multiplier, 2),
        },
    ]

    if is_cross:
        steps.append({
            "label": "Cross-muscle factor",
            "factor": round(cross_factor, 2),
            "detail": "Applied because the target exercise isn't a direct match for the reference lift.",
        })

    if basis_factor != 1.0:
        direction = (
            "per-hand dumbbell → total load"
            if basis_factor > 1.0
            else "total load → per-hand dumbbell"
        )
        steps.append({
            "label": "Dumbbell load conversion",
            "factor": round(basis_factor, 2),
            "detail": (
                f"Reference and target use different load bases ({direction}); "
                "applying the two-dumbbells-per-barbell factor."
            ),
        })

    steps.append({
        "label": f"Preset: {preset_key.capitalize()}",
        "factor": round(pct, 2),
        "detail": (
            f"RIR {preset['rir']}, RPE {preset['rpe']}, "
            f"{preset['min_rep']}–{preset['max_rep']} reps "
            f"@ {pct} of 1RM."
        ),
    })

    steps.append({
        "label": "Working weight",
        "value": working_weight,
        "unit": "kg",
        "detail": f"≈ {round(pre_round_weight, 2)} kg before rounding",
    })
    steps.append({
        "label": "Rounding",
        "value": _format_rounding_label(equipment),
    })

    trace: dict[str, Any] = {"source": "profile", "steps": steps}

    if is_cross:
        direct_slug = _match_direct_lift_key(target_exercise_name)
        if direct_slug and direct_slug in KEY_LIFT_LABELS:
            trace["improvement_hint"] = {
                "action": "enter_reference_lift",
                "lift_key": direct_slug,
                "copy": (
                    f"Enter {KEY_LIFT_LABELS[direct_slug]} directly in your "
                    "Reference Lifts to skip the cross-muscle factor."
                ),
            }
        else:
            chain = MUSCLE_TO_KEY_LIFT.get(target_primary_muscle or "", [])
            chain_first = chain[0] if chain else None
            if chain_first and chain_first in KEY_LIFT_LABELS:
                trace["improvement_hint"] = {
                    "action": "enter_reference_lift",
                    "lift_key": chain_first,
                    "copy": (
                        "Add a reference lift for this muscle group "
                        f"(e.g. {KEY_LIFT_LABELS[chain_first]}) to refine this suggestion."
                    ),
                }

    return trace


def _build_profile_bodyweight_trace(
    *,
    lift_key: str,
    reference_reps: int,
    is_cross: bool,
    preset_key: str,
    preset: dict[str, Any],
    target_exercise_name: str,
    target_primary_muscle: Optional[str],
) -> dict[str, Any]:
    label_friendly = KEY_LIFT_LABELS.get(lift_key, lift_key)
    detail = (
        "Cross-muscle bodyweight fallback — copying your saved rep count."
        if is_cross
        else "Bodyweight reference — copying the rep count from your questionnaire entry."
    )
    steps: list[dict[str, Any]] = [
        {
            "label": "Reference lift",
            "value": f"{label_friendly}: {reference_reps:g} reps (bodyweight)",
            "detail": detail,
        },
        {
            "label": f"Preset: {preset_key.capitalize()}",
            "factor": round(preset["pct_1rm"], 2),
            "detail": f"RIR {preset['rir']}, RPE {preset['rpe']} (rep count copied from your reference set).",
        },
        {
            "label": "Working weight",
            "value": 0.0,
            "unit": "kg",
            "detail": "Bodyweight movement — no added load.",
        },
    ]
    trace: dict[str, Any] = {"source": "profile", "steps": steps}
    if is_cross:
        direct_slug = _match_direct_lift_key(target_exercise_name)
        if direct_slug and direct_slug in KEY_LIFT_LABELS:
            trace["improvement_hint"] = {
                "action": "enter_reference_lift",
                "lift_key": direct_slug,
                "copy": (
                    f"Enter {KEY_LIFT_LABELS[direct_slug]} directly in your "
                    "Reference Lifts to skip the cross-muscle factor."
                ),
            }
    return trace


def _build_cold_start_trace(
    *,
    target_exercise_name: str,
    target_tier: Tier,
    target_primary_muscle: str,
    base_1rm: float,
    bodyweight: float,
    gender: str,
    ratio: float,
    experience_tier: str,
    experience_years: Optional[float],
    experience_multiplier: float,
    tier_multiplier: float,
    target_1rm: float,
    preset: dict[str, Any],
    pre_round_weight: float,
    working_weight: float,
    equipment: Optional[str],
) -> dict[str, Any]:
    gender_label = "male" if gender == "M" else "female"
    pct = preset["pct_1rm"]
    muscle_label = (target_primary_muscle or "").lower() or "muscle"

    steps: list[dict[str, Any]] = [
        {
            "label": "No reference lift saved for this muscle",
            "detail": "Falling back to a population estimate from your demographics.",
        },
        {
            "label": f"Bodyweight ratio ({muscle_label} × {gender_label})",
            "factor": round(ratio, 2),
        },
        {
            "label": "Bodyweight",
            "value": bodyweight,
            "unit": "kg",
        },
        {
            "label": "Experience tier",
            "value": _format_experience_label(experience_tier, experience_years),
            "factor": round(experience_multiplier, 2),
            "detail": "Height, age, and BMI are intentionally not used (see Issue #16).",
        },
        {
            "label": "Cold-start 1RM",
            "value": round(base_1rm, 1),
            "unit": "kg",
            "detail": f"{round(ratio, 2)} × {bodyweight:g} kg × {round(experience_multiplier, 2)}",
        },
        {
            "label": f"Tier scaling: complex → {target_tier}",
            "factor": round(tier_multiplier, 2),
        },
        {
            "label": "Preset: Light (forced for cold-start safety)",
            "factor": round(pct, 2),
            "detail": (
                f"RIR {preset['rir']}, RPE {preset['rpe']}, "
                f"{preset['min_rep']}–{preset['max_rep']} reps @ {pct} of 1RM."
            ),
        },
        {
            "label": "Working weight",
            "value": working_weight,
            "unit": "kg",
            "detail": f"≈ {round(pre_round_weight, 2)} kg before rounding",
        },
        {
            "label": "Rounding",
            "value": _format_rounding_label(equipment),
        },
    ]

    trace: dict[str, Any] = {"source": "cold_start", "steps": steps}

    direct_slug = _match_direct_lift_key(target_exercise_name)
    canonical = COLD_START_CANONICAL_COMPOUND.get(target_primary_muscle)
    suggested = direct_slug if direct_slug in KEY_LIFT_LABELS else canonical
    if suggested and suggested in KEY_LIFT_LABELS:
        trace["improvement_hint"] = {
            "action": "enter_reference_lift",
            "lift_key": suggested,
            "copy": (
                f"Enter {KEY_LIFT_LABELS[suggested]} in your Reference Lifts. "
                "A measured 1RM replaces this population guess and unlocks "
                "Heavy/Moderate presets based on your actual strength."
            ),
        }
    return trace


def _build_learned_trace(
    row: dict[str, Any], *, weight: float, reps_low: int, reps_high: int
) -> dict[str, Any]:
    rep_label = f"{reps_low}" if reps_low == reps_high else f"{reps_low}–{reps_high}"
    sample_count = row.get("sample_count") or 0
    confidence = row.get("confidence")
    e1rm = row.get("estimated_1rm")
    steps: list[dict[str, Any]] = [
        {
            "label": "Learned from your logged sets",
            "value": f"{weight:g} kg × {rep_label}",
            "detail": (
                f"Calibrated from {sample_count} scored "
                f"{'log' if sample_count == 1 else 'logs'} for this exact "
                f"exercise (confidence: {confidence})."
            ),
        },
    ]
    if e1rm:
        steps.append({
            "label": "Estimated strength",
            "value": f"~{float(e1rm):g} kg e1RM",
            "detail": "Canonical Epley estimate from your best recent top set.",
        })
    return {
        "source": "learned",
        "confidence": confidence,
        "sample_count": sample_count,
        "steps": steps,
    }


def _build_related_learned_trace(
    candidate: dict[str, Any],
    *,
    target_tier: str,
    preset_key: str,
    preset: dict[str, Any],
    pre_round_weight: float,
    working_weight: float,
    equipment: Optional[str],
) -> dict[str, Any]:
    source_e1rm = float(candidate.get("source_estimated_1rm") or 0)
    target_e1rm = float(candidate.get("target_estimated_1rm") or 0)
    ratio = float(candidate.get("transfer_ratio") or 0)
    basis_factor = float(candidate.get("load_basis_factor") or 1)
    source_name = candidate.get("source_exercise_name") or "related exercise"
    target_name = candidate.get("target_exercise_name") or "target exercise"
    sample_count = int(candidate.get("source_sample_count") or 0)
    confidence = candidate.get("source_confidence")
    load_basis = str(candidate.get("load_basis") or "").replace("_", " ")
    relationship = str(candidate.get("relationship_type") or "").replace("_", " ")

    return {
        "source": "related_learned",
        "confidence": confidence,
        "sample_count": sample_count,
        "source_exercise": source_name,
        "target_exercise": target_name,
        "relationship_type": candidate.get("relationship_type"),
        "transfer_ratio": ratio,
        "load_basis": candidate.get("load_basis"),
        "steps": [
            {
                "label": "Related learned calibration",
                "value": f"Learned from {source_name}",
                "detail": (
                    f"{sample_count} scored "
                    f"{'log' if sample_count == 1 else 'logs'}, "
                    f"confidence: {confidence}. Exact learned/log data for "
                    f"{target_name} was not available."
                ),
            },
            {
                "label": "Transfer",
                "value": f"{source_name} -> {target_name}",
                "detail": (
                    f"Relationship: {relationship}; ratio {ratio:g}; "
                    f"load basis: {load_basis} (factor {basis_factor:g})."
                ),
            },
            {
                "label": "Estimated strength",
                "value": f"~{target_e1rm:g} kg e1RM",
                "detail": (
                    f"Source e1RM ~{source_e1rm:g} kg × ratio {ratio:g} × "
                    f"basis factor {basis_factor:g}."
                ),
            },
            {
                "label": "Progression target",
                "value": f"{working_weight:g} kg × {preset['min_rep']}–{preset['max_rep']}",
                "detail": (
                    f"{preset_key.title()} preset for {target_tier} tier "
                    f"({preset['pct_1rm']:.0%} e1RM), then rounded for "
                    f"{normalize_equipment(equipment) or 'equipment'} from "
                    f"{round(pre_round_weight, 2)} kg."
                ),
            },
        ],
    }
