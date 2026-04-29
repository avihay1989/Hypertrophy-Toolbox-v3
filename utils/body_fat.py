"""Body Fat Percentage (BFP) estimation — pure functions.

This module is the single source of truth for the four estimation
primitives consumed by the ``/body_composition`` page (Issue #21):

- ``compute_navy``           — U.S. Navy circumference method (Hodgdon &
                                Beckett, 1984). Metric (SI) variant only.
- ``compute_bmi``            — BMI method (Deurenberg, Weststrate &
                                Seidell, 1991). Adult / juvenile branch
                                cuts at age 15 (≤15 = juvenile, >15 = adult).
- ``ace_category``           — ACE Body Fat Categorization band.
- ``jackson_pollock_ideal``  — Jackson & Pollock ideal BFP by age,
                                linearly interpolated between the
                                published 5-year brackets and clamped
                                outside [20, 55].

All four are pure functions — no DB access, no Flask imports — so the
JS mirror in ``static/js/modules/body-composition.js`` can be checked
against them via a lockstep drift test (Issue #21 acceptance checklist).

JS MIRROR — must match Python
-----------------------------
Every constant table and branching rule in this file has a paired
``static/js/modules/body-composition.js`` counterpart. Editing one
side without the other will trip the Python↔JS lockstep regression
test (precedent: ``tests/test_profile_estimator.py:test_bodymap_canonical_in_sync``).

Refactor invariant (CLAUDE.md §1): outputs of these functions are
**informational only** — they never auto-adjust weight / rep / RIR
suggestions on ``/workout_plan``.
"""
from __future__ import annotations

import math
from typing import Literal, Optional

from utils.logger import get_logger

logger = get_logger()

Gender = Literal["M", "F"]


# ---------------------------------------------------------------------------
# Validation bounds — shared by both Navy and BMI paths.
# ---------------------------------------------------------------------------

CIRCUMFERENCE_MIN_CM = 20.0
CIRCUMFERENCE_MAX_CM = 250.0
HEIGHT_MIN_CM = 100.0
HEIGHT_MAX_CM = 250.0
WEIGHT_MIN_KG = 20.0
WEIGHT_MAX_KG = 350.0
AGE_MIN_YEARS = 2
AGE_MAX_YEARS = 120

# Deurenberg/Weststrate/Seidell juvenile cut. age <= 15 uses the
# child formula; age > 15 uses the adult formula.
BMI_JUVENILE_AGE_CUTOFF = 15


class BodyFatValidationError(ValueError):
    """Raised when an estimator input is out-of-range or in the
    log-domain prohibited region.

    ``code`` is a stable machine-readable string (used by the route
    layer to surface a structured 4xx). ``field`` names the offending
    input where relevant. ``message`` is the user-facing copy.
    """

    def __init__(self, code: str, message: str, *, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


# ---------------------------------------------------------------------------
# U.S. Navy circumference method (Hodgdon & Beckett, 1984), SI form.
# ---------------------------------------------------------------------------


def compute_navy(
    *,
    gender: Gender,
    height_cm: float,
    neck_cm: float,
    waist_cm: float,
    hip_cm: Optional[float] = None,
) -> float:
    """Return BFP (%) via the U.S. Navy method.

    Male formula:
        BFP = 495 / (1.0324 - 0.19077*log10(waist - neck) +
                     0.15456*log10(height)) - 450

    Female formula:
        BFP = 495 / (1.29579 - 0.35004*log10(waist + hip - neck) +
                     0.22100*log10(height)) - 450

    Raises ``BodyFatValidationError`` if any input is out of range or
    the log argument would be ≤ 0.
    """
    _validate_gender(gender)
    _validate_circumference("neck_cm", neck_cm)
    _validate_circumference("waist_cm", waist_cm)
    _validate_height(height_cm)

    if gender == "M":
        if hip_cm is not None:
            raise BodyFatValidationError(
                "UNEXPECTED_HIP",
                "Hip circumference is only used for the female Navy formula.",
                field="hip_cm",
            )
        log_arg = waist_cm - neck_cm
        if log_arg <= 0:
            raise BodyFatValidationError(
                "LOG_DOMAIN",
                "Waist circumference must be larger than neck circumference.",
                field="waist_cm",
            )
        denom = 1.0324 - 0.19077 * math.log10(log_arg) + 0.15456 * math.log10(height_cm)
    else:
        if hip_cm is None:
            raise BodyFatValidationError(
                "MISSING_HIP",
                "Hip circumference is required for the female Navy formula.",
                field="hip_cm",
            )
        _validate_circumference("hip_cm", hip_cm)
        log_arg = waist_cm + hip_cm - neck_cm
        if log_arg <= 0:
            raise BodyFatValidationError(
                "LOG_DOMAIN",
                "Waist plus hip circumference must be larger than neck circumference.",
                field="waist_cm",
            )
        denom = 1.29579 - 0.35004 * math.log10(log_arg) + 0.22100 * math.log10(height_cm)

    if denom <= 0:
        raise BodyFatValidationError(
            "LOG_DOMAIN",
            "Tape values produce a non-physical body-fat estimate; "
            "double-check the measurements.",
        )
    return 495.0 / denom - 450.0


# ---------------------------------------------------------------------------
# BMI method (Deurenberg, Weststrate & Seidell, 1991).
# ---------------------------------------------------------------------------


def compute_bmi(
    *,
    gender: Gender,
    age: int,
    height_cm: float,
    weight_kg: float,
) -> float:
    """Return BFP (%) via the Deurenberg BMI formulas.

    BMI = weight_kg / (height_m ** 2)

    Adult male   (age >  15): BFP = 1.20*BMI + 0.23*age - 16.2
    Adult female (age >  15): BFP = 1.20*BMI + 0.23*age -  5.4
    Boy          (age <= 15): BFP = 1.51*BMI - 0.70*age -  2.2
    Girl         (age <= 15): BFP = 1.51*BMI - 0.70*age +  1.4

    The ``≤15`` juvenile cut matches the published source — earlier
    drafts used ``<18`` in error.
    """
    _validate_gender(gender)
    _validate_age(age)
    _validate_height(height_cm)
    _validate_weight(weight_kg)

    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m * height_m)

    if age <= BMI_JUVENILE_AGE_CUTOFF:
        if gender == "M":
            return 1.51 * bmi - 0.70 * age - 2.2
        return 1.51 * bmi - 0.70 * age + 1.4
    if gender == "M":
        return 1.20 * bmi + 0.23 * age - 16.2
    return 1.20 * bmi + 0.23 * age - 5.4


# ---------------------------------------------------------------------------
# ACE Body Fat Categorization band lookup.
# ---------------------------------------------------------------------------

# (label, upper_bound_exclusive) — the last entry's bound is +infinity.
# Source: American Council on Exercise — Body Fat Categorization.
_ACE_BANDS_MEN: tuple[tuple[str, float], ...] = (
    ("Essential fat", 6.0),
    ("Athletes", 14.0),
    ("Fitness", 18.0),
    ("Average", 25.0),
    ("Obese", math.inf),
)
_ACE_BANDS_WOMEN: tuple[tuple[str, float], ...] = (
    ("Essential fat", 14.0),
    ("Athletes", 21.0),
    ("Fitness", 25.0),
    ("Average", 32.0),
    ("Obese", math.inf),
)


def ace_category(bfp: float, gender: Gender) -> str:
    """Return the ACE band label for ``bfp`` (%).

    Boundary convention: ``[lower, next_lower)`` — i.e. ``bfp = 14.0``
    for a man falls in *Fitness*, not *Athletes*. Below the lowest
    band we still return *Essential fat* (the band the user is closest
    to); above the highest we return *Obese*.
    """
    _validate_gender(gender)
    bands = _ACE_BANDS_MEN if gender == "M" else _ACE_BANDS_WOMEN
    for label, upper in bands:
        if bfp < upper:
            return label
    return bands[-1][0]


# ---------------------------------------------------------------------------
# Jackson & Pollock ideal BFP by age (linear interpolation, clamped).
# ---------------------------------------------------------------------------

# Source: Jackson & Pollock — Ideal Body Fat Percentages by Age.
# Rows are (age, women_bfp, men_bfp). Must remain sorted by age.
_JP_TABLE: tuple[tuple[int, float, float], ...] = (
    (20, 17.7, 8.5),
    (25, 18.4, 10.5),
    (30, 19.3, 12.7),
    (35, 21.5, 13.7),
    (40, 22.2, 15.3),
    (45, 22.9, 16.4),
    (50, 25.2, 18.9),
    (55, 26.3, 20.9),
)


def jackson_pollock_ideal(age: int, gender: Gender) -> float:
    """Return the Jackson & Pollock ideal BFP (%) for ``age`` and ``gender``.

    Linearly interpolates between the published 5-year brackets.
    Ages outside ``[20, 55]`` clamp to the nearest edge (i.e. age 18
    returns the age-20 row, age 70 returns the age-55 row).
    """
    _validate_gender(gender)
    _validate_age(age)
    col = 2 if gender == "M" else 1

    if age <= _JP_TABLE[0][0]:
        return _JP_TABLE[0][col]
    if age >= _JP_TABLE[-1][0]:
        return _JP_TABLE[-1][col]

    for i in range(len(_JP_TABLE) - 1):
        lo_age, *_ = _JP_TABLE[i]
        hi_age, *_ = _JP_TABLE[i + 1]
        if lo_age <= age <= hi_age:
            lo_val = _JP_TABLE[i][col]
            hi_val = _JP_TABLE[i + 1][col]
            frac = (age - lo_age) / (hi_age - lo_age)
            return lo_val + frac * (hi_val - lo_val)
    # Unreachable given the clamps above, but keep the type-checker happy.
    return _JP_TABLE[-1][col]


# ---------------------------------------------------------------------------
# Shared validators.
# ---------------------------------------------------------------------------


def _validate_gender(gender: object) -> None:
    if gender not in ("M", "F"):
        raise BodyFatValidationError(
            "UNSUPPORTED_GENDER",
            "Gender must be 'M' or 'F'.",
            field="gender",
        )


def _validate_circumference(field: str, value: object) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BodyFatValidationError(
            "INVALID_TYPE",
            f"{field} must be a number.",
            field=field,
        )
    if not (CIRCUMFERENCE_MIN_CM <= value <= CIRCUMFERENCE_MAX_CM):
        raise BodyFatValidationError(
            "OUT_OF_RANGE",
            f"{field} must be between {CIRCUMFERENCE_MIN_CM:g} and "
            f"{CIRCUMFERENCE_MAX_CM:g} cm.",
            field=field,
        )


def _validate_height(value: object) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BodyFatValidationError(
            "INVALID_TYPE", "height_cm must be a number.", field="height_cm"
        )
    if not (HEIGHT_MIN_CM <= value <= HEIGHT_MAX_CM):
        raise BodyFatValidationError(
            "OUT_OF_RANGE",
            f"height_cm must be between {HEIGHT_MIN_CM:g} and {HEIGHT_MAX_CM:g} cm.",
            field="height_cm",
        )


def _validate_weight(value: object) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BodyFatValidationError(
            "INVALID_TYPE", "weight_kg must be a number.", field="weight_kg"
        )
    if not (WEIGHT_MIN_KG <= value <= WEIGHT_MAX_KG):
        raise BodyFatValidationError(
            "OUT_OF_RANGE",
            f"weight_kg must be between {WEIGHT_MIN_KG:g} and {WEIGHT_MAX_KG:g} kg.",
            field="weight_kg",
        )


def _validate_age(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BodyFatValidationError(
            "INVALID_TYPE", "age must be an integer.", field="age"
        )
    if not (AGE_MIN_YEARS <= value <= AGE_MAX_YEARS):
        raise BodyFatValidationError(
            "OUT_OF_RANGE",
            f"age must be between {AGE_MIN_YEARS} and {AGE_MAX_YEARS} years.",
            field="age",
        )
