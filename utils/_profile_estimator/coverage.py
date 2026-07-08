"""Cluster 3 — accuracy & coverage-guidance helpers for the profile estimator.

Accuracy-band and coverage-guidance helpers extracted verbatim from
:mod:`utils.profile_estimator` (WP2.1d, Deep Refactor Plan v3 Phase 2 — see
``docs/user_profile/PROFILE_ESTIMATOR_CLUSTERS.md`` §2/§3). These names are
re-exported by the :mod:`utils.profile_estimator` facade; import them from
there, not from this internal module. Depends on the constants leaf and the
core-math primitives only — no ``strength_calibration`` import (the estimator
cycle stays held by the facade's function-local lazy imports).
"""
from __future__ import annotations

from typing import Any, Optional

from utils._profile_estimator.constants import (
    ACCURACY_MAJOR_MUSCLE_GROUPS,
    COLD_START_CANONICAL_COMPOUND,
    HIGH_IMPACT_LIFT_PRIORITY,
    KEY_LIFT_LABELS,
    KEY_LIFTS,
)
from utils._profile_estimator.core_math import (
    cold_start_1rm,
    epley_1rm,
)


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
