"""Cluster 5 — bodymap coverage state for the profile estimator.

Per-muscle bodymap coverage-state helper extracted verbatim from
:mod:`utils.profile_estimator` (WP2.1f, Deep Refactor Plan v3 Phase 2 — see
``docs/user_profile/PROFILE_ESTIMATOR_CLUSTERS.md`` §2/§3). These names are
re-exported by the :mod:`utils.profile_estimator` facade; import them from
there, not from this internal module. Depends on the constants leaf, the
core-math primitives, and the coverage leaf only — no ``strength_calibration``
import (the estimator cycle stays held by the facade's function-local lazy
imports).
"""
from __future__ import annotations

from typing import Any, Optional

from utils._profile_estimator.constants import (
    BODYMAP_MUSCLE_KEYS,
    KEY_LIFT_LABELS,
    MUSCLE_TO_KEY_LIFT,
)
from utils._profile_estimator.core_math import (
    epley_1rm,
)
from utils._profile_estimator.coverage import (
    _is_lift_filled,
)


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
