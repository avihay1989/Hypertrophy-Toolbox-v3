"""Shared validation for persisted workout-plan and workout-log values."""
from __future__ import annotations

import math
from typing import Any, Optional

from utils.constants import (
    MAX_RIR,
    MAX_WORKOUT_WEIGHT_KG,
    MIN_RIR,
    MIN_WORKOUT_WEIGHT_KG,
)


UNSET = object()


def _number(value: Any, field_label: str) -> tuple[Optional[float], Optional[str]]:
    """Coerce a JSON numeric value while rejecting booleans and non-finite values."""
    if isinstance(value, bool):
        return None, f"{field_label} must be a finite number."
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"{field_label} must be a finite number."
    if not math.isfinite(number):
        return None, f"{field_label} must be a finite number."
    return number, None


def validate_workout_bounds(
    *,
    weight: Any = UNSET,
    rir: Any = UNSET,
    min_reps: Any = UNSET,
    max_reps: Any = UNSET,
    allow_null: bool = False,
) -> Optional[str]:
    """Return a validation message, or ``None`` when canonical bounds hold.

    ``UNSET`` distinguishes an omitted partial-update field from an explicit
    JSON null. Scored log values are nullable/blank, while bounded plan values
    are not nullable when supplied.
    """
    numeric_values: dict[str, Optional[float]] = {}
    for key, value, label in (
        ("weight", weight, "Weight"),
        ("rir", rir, "RIR"),
        ("min_reps", min_reps, "Minimum reps"),
        ("max_reps", max_reps, "Maximum reps"),
    ):
        if value is UNSET:
            continue
        if allow_null and (value is None or value == ""):
            numeric_values[key] = None
            continue
        if value is None:
            return f"{label} cannot be null."
        number, error = _number(value, label)
        if error:
            return error
        numeric_values[key] = number

    parsed_weight = numeric_values.get("weight")
    if parsed_weight is not None and not (
        MIN_WORKOUT_WEIGHT_KG <= parsed_weight <= MAX_WORKOUT_WEIGHT_KG
    ):
        return (
            f"Weight must be between {MIN_WORKOUT_WEIGHT_KG:g} and "
            f"{MAX_WORKOUT_WEIGHT_KG:g} kg."
        )

    parsed_rir = numeric_values.get("rir")
    if parsed_rir is not None and not (MIN_RIR <= parsed_rir <= MAX_RIR):
        return f"RIR must be between {MIN_RIR:g} and {MAX_RIR:g}."

    parsed_min = numeric_values.get("min_reps")
    parsed_max = numeric_values.get("max_reps")
    if parsed_min is not None and parsed_max is not None and parsed_min > parsed_max:
        return "Minimum reps cannot exceed maximum reps."

    return None
