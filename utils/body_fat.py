"""Body-fat percentage formulas and reference tables (Issue #21).

Pure functions only — no DB access, no I/O. All inputs are SI / metric units
(cm, kg, years). Outputs are floats unless otherwise noted.

**Must match JS mirror.** The `/body_composition` page recomputes BFP on
every input event in the browser for live feedback (Issues #17 / #18 / #19
JS-mirror contract). Any change to the four public functions here
(`compute_navy`, `compute_bmi`, `ace_category`, `jackson_pollock_ideal`)
must be reflected verbatim in `static/js/modules/body-composition.js`.
"""
from __future__ import annotations

import math
from typing import Literal, Optional

Gender = Literal["M", "F"]

# Validation ranges — server-side guardrails. Out-of-range inputs raise
# ValueError; routes translate that into a structured 4xx response.
CIRCUMFERENCE_MIN_CM = 20.0
CIRCUMFERENCE_MAX_CM = 250.0
HEIGHT_MIN_CM = 100.0
HEIGHT_MAX_CM = 250.0
BODYWEIGHT_MIN_KG = 20.0
BODYWEIGHT_MAX_KG = 350.0
ADULT_AGE_THRESHOLD = 18

# Jackson & Pollock ideal BFP table (age → (women%, men%)).
# Source: Jackson, A.S. & Pollock, M.L. — Ideal Body Fat Percentages by Age.
JACKSON_POLLOCK_TABLE: tuple[tuple[int, float, float], ...] = (
    (20, 17.7, 8.5),
    (25, 18.4, 10.5),
    (30, 19.3, 12.7),
    (35, 21.5, 13.7),
    (40, 22.2, 15.3),
    (45, 22.9, 16.4),
    (50, 25.2, 18.9),
    (55, 26.3, 20.9),
)

# ACE body-fat category bands (inclusive lower, exclusive upper except for the
# final "Obese" band which is open-ended). Source: American Council on
# Exercise — Body Fat Categorization.
ACE_BANDS_MALE: tuple[tuple[str, float, Optional[float]], ...] = (
    ("Essential fat", 2.0, 6.0),
    ("Athletes", 6.0, 14.0),
    ("Fitness", 14.0, 18.0),
    ("Average", 18.0, 25.0),
    ("Obese", 25.0, None),
)
ACE_BANDS_FEMALE: tuple[tuple[str, float, Optional[float]], ...] = (
    ("Essential fat", 10.0, 14.0),
    ("Athletes", 14.0, 21.0),
    ("Fitness", 21.0, 25.0),
    ("Average", 25.0, 32.0),
    ("Obese", 32.0, None),
)


def _normalize_gender(gender: str) -> Gender:
    if not isinstance(gender, str):
        raise ValueError("gender must be 'M' or 'F'")
    upper = gender.strip().upper()
    if upper not in ("M", "F"):
        raise ValueError("gender must be 'M' or 'F'")
    return upper  # type: ignore[return-value]


def _check_range(value: float, lo: float, hi: float, field: str, unit: str) -> None:
    if value is None or not isinstance(value, (int, float)) or math.isnan(float(value)):
        raise ValueError(f"{field} must be a number in [{lo}, {hi}] {unit}")
    if value < lo or value > hi:
        raise ValueError(f"{field} must be in [{lo}, {hi}] {unit}")


def compute_navy(
    *,
    gender: str,
    height_cm: float,
    neck_cm: float,
    waist_cm: float,
    hip_cm: Optional[float] = None,
) -> float:
    """U.S. Navy circumference method BFP (Hodgdon & Beckett, 1984).

    Metric (SI) form. Male formula uses `(waist - neck)`; female formula
    uses `(waist + hip - neck)`. Both arguments to `log10` must be > 0,
    otherwise raises ValueError (log-domain violation).
    """
    sex = _normalize_gender(gender)
    _check_range(height_cm, HEIGHT_MIN_CM, HEIGHT_MAX_CM, "height", "cm")
    _check_range(neck_cm, CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM, "neck", "cm")
    _check_range(waist_cm, CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM, "waist", "cm")

    if sex == "M":
        if hip_cm is not None:
            raise ValueError("hip must not be provided when gender is 'M'")
        delta = waist_cm - neck_cm
        if delta <= 0:
            raise ValueError("waist circumference must be larger than neck circumference")
        bfp = 495.0 / (
            1.0324 - 0.19077 * math.log10(delta) + 0.15456 * math.log10(height_cm)
        ) - 450.0
    else:
        if hip_cm is None:
            raise ValueError("hip is required when gender is 'F'")
        _check_range(hip_cm, CIRCUMFERENCE_MIN_CM, CIRCUMFERENCE_MAX_CM, "hip", "cm")
        delta = waist_cm + hip_cm - neck_cm
        if delta <= 0:
            raise ValueError("waist + hip must be larger than neck circumference")
        bfp = 495.0 / (
            1.29579 - 0.35004 * math.log10(delta) + 0.22100 * math.log10(height_cm)
        ) - 450.0
    return bfp


def compute_bmi(
    *,
    gender: str,
    age_years: int,
    height_cm: float,
    bodyweight_kg: float,
) -> dict[str, float]:
    """BMI-method BFP fallback (Deurenberg et al. variants).

    Returns a dict with the raw BMI and the gender/age-appropriate BFP.
    Adult (>=18) uses the linear `1.20 * BMI + 0.23 * age - {16.2 | 5.4}`
    form; minors (<18) use the `1.51 * BMI - 0.70 * age {-2.2 | +1.4}` form.
    """
    sex = _normalize_gender(gender)
    if not isinstance(age_years, int) or isinstance(age_years, bool):
        raise ValueError("age_years must be a non-negative integer")
    if age_years < 0 or age_years > 120:
        raise ValueError("age_years must be in [0, 120]")
    _check_range(height_cm, HEIGHT_MIN_CM, HEIGHT_MAX_CM, "height", "cm")
    _check_range(bodyweight_kg, BODYWEIGHT_MIN_KG, BODYWEIGHT_MAX_KG, "bodyweight", "kg")

    height_m = height_cm / 100.0
    bmi = bodyweight_kg / (height_m * height_m)
    if age_years >= ADULT_AGE_THRESHOLD:
        if sex == "M":
            bfp = 1.20 * bmi + 0.23 * age_years - 16.2
        else:
            bfp = 1.20 * bmi + 0.23 * age_years - 5.4
    else:
        if sex == "M":
            bfp = 1.51 * bmi - 0.70 * age_years - 2.2
        else:
            bfp = 1.51 * bmi - 0.70 * age_years + 1.4
    return {"bmi": bmi, "bfp": bfp}


def ace_category(bfp: float, gender: str) -> str:
    """Return the ACE band label for `bfp` and `gender`.

    Bands are inclusive on the lower bound, exclusive on the upper, except
    for "Obese" which is open-ended. Values below the first band's lower
    bound clamp to "Essential fat" (consistent with the docs spec which
    treats the table as a display-only mapping for any non-negative BFP).
    """
    sex = _normalize_gender(gender)
    if not isinstance(bfp, (int, float)) or math.isnan(float(bfp)):
        raise ValueError("bfp must be a number")
    bands = ACE_BANDS_MALE if sex == "M" else ACE_BANDS_FEMALE
    for label, lo, hi in bands:
        if hi is None:
            if bfp >= lo:
                return label
        elif bfp < hi:
            return label
    return bands[-1][0]


def jackson_pollock_ideal(age_years: int, gender: str) -> float:
    """Linearly-interpolated Jackson & Pollock ideal BFP for `age_years`.

    Ages below 20 clamp to the 20-year row; ages above 55 clamp to the
    55-year row. Anything in between linearly interpolates between the
    two bracketing rows.
    """
    sex = _normalize_gender(gender)
    if not isinstance(age_years, int) or isinstance(age_years, bool):
        raise ValueError("age_years must be a non-negative integer")
    if age_years < 0 or age_years > 120:
        raise ValueError("age_years must be in [0, 120]")

    col = 2 if sex == "M" else 1
    first_age = JACKSON_POLLOCK_TABLE[0][0]
    last_age = JACKSON_POLLOCK_TABLE[-1][0]
    if age_years <= first_age:
        return JACKSON_POLLOCK_TABLE[0][col]
    if age_years >= last_age:
        return JACKSON_POLLOCK_TABLE[-1][col]
    for i in range(len(JACKSON_POLLOCK_TABLE) - 1):
        lo_age, lo_w, lo_m = JACKSON_POLLOCK_TABLE[i]
        hi_age, hi_w, hi_m = JACKSON_POLLOCK_TABLE[i + 1]
        if lo_age <= age_years <= hi_age:
            lo_val = lo_m if sex == "M" else lo_w
            hi_val = hi_m if sex == "M" else hi_w
            ratio = (age_years - lo_age) / (hi_age - lo_age)
            return lo_val + (hi_val - lo_val) * ratio
    return JACKSON_POLLOCK_TABLE[-1][col]
