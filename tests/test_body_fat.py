"""Unit tests for ``utils.body_fat`` — Issue #21 Phase 1 (pure estimator).

Coverage map (per the Issue #21 acceptance checklist):
- ``compute_navy``: male + female + log-domain rejection + range
  rejection + missing/extra hip rejection.
- ``compute_bmi``: adult male / adult female / boy / girl + the ≤15
  juvenile cut.
- ``ace_category``: boundary rows for both genders.
- ``jackson_pollock_ideal``: interpolation between brackets and clamp
  outside [20, 55].
"""
from __future__ import annotations

import math

import pytest

from utils.body_fat import (
    BodyFatValidationError,
    ace_category,
    compute_bmi,
    compute_navy,
    jackson_pollock_ideal,
)


# ---------------------------------------------------------------------------
# compute_navy — male
# ---------------------------------------------------------------------------


def test_compute_navy_male_known_value():
    # height=180, neck=38, waist=85 → ≈16.13 %.
    bfp = compute_navy(gender="M", height_cm=180, neck_cm=38, waist_cm=85)
    assert bfp == pytest.approx(16.13, abs=0.05)


def test_compute_navy_male_lean_athlete():
    # Lean lifter: large neck, small waist relative to height.
    bfp = compute_navy(gender="M", height_cm=178, neck_cm=40, waist_cm=78)
    assert 5.0 < bfp < 12.0


def test_compute_navy_male_rejects_waist_le_neck():
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_navy(gender="M", height_cm=180, neck_cm=40, waist_cm=40)
    assert excinfo.value.code == "LOG_DOMAIN"


def test_compute_navy_male_rejects_hip_argument():
    # Male path must not accept a hip value — server enforces the
    # gender-specific tape contract.
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_navy(
            gender="M", height_cm=180, neck_cm=38, waist_cm=85, hip_cm=100
        )
    assert excinfo.value.code == "UNEXPECTED_HIP"
    assert excinfo.value.field == "hip_cm"


# ---------------------------------------------------------------------------
# compute_navy — female
# ---------------------------------------------------------------------------


def test_compute_navy_female_known_value():
    # height=165, neck=32, waist=75, hip=100 → ≈29.94 %.
    bfp = compute_navy(
        gender="F", height_cm=165, neck_cm=32, waist_cm=75, hip_cm=100
    )
    assert bfp == pytest.approx(29.94, abs=0.05)


def test_compute_navy_female_requires_hip():
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_navy(gender="F", height_cm=165, neck_cm=32, waist_cm=75)
    assert excinfo.value.code == "MISSING_HIP"
    assert excinfo.value.field == "hip_cm"


def test_compute_navy_female_log_domain_rejection():
    # Make waist + hip - neck ≤ 0 by giving a huge neck. Hard to do
    # in physiological range, so use boundary values.
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_navy(
            gender="F", height_cm=165, neck_cm=200, waist_cm=80, hip_cm=100
        )
    assert excinfo.value.code == "LOG_DOMAIN"


# ---------------------------------------------------------------------------
# compute_navy — shared validation
# ---------------------------------------------------------------------------


def test_compute_navy_rejects_unknown_gender():
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_navy(
            gender="Other",  # type: ignore[arg-type]
            height_cm=180,
            neck_cm=38,
            waist_cm=85,
        )
    assert excinfo.value.code == "UNSUPPORTED_GENDER"


@pytest.mark.parametrize(
    "field,kwargs",
    [
        (
            "neck_cm",
            dict(gender="M", height_cm=180, neck_cm=10, waist_cm=85),
        ),
        (
            "waist_cm",
            dict(gender="M", height_cm=180, neck_cm=38, waist_cm=300),
        ),
        (
            "height_cm",
            dict(gender="M", height_cm=50, neck_cm=38, waist_cm=85),
        ),
    ],
)
def test_compute_navy_rejects_out_of_range(field, kwargs):
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_navy(**kwargs)
    assert excinfo.value.code == "OUT_OF_RANGE"
    assert excinfo.value.field == field


# ---------------------------------------------------------------------------
# compute_bmi — adult / juvenile branches
# ---------------------------------------------------------------------------


def test_compute_bmi_adult_male():
    # age=30, height=175, weight=75 → BMI=24.49 → BFP≈20.09.
    bfp = compute_bmi(gender="M", age=30, height_cm=175, weight_kg=75)
    assert bfp == pytest.approx(20.09, abs=0.05)


def test_compute_bmi_adult_female():
    # age=30, height=165, weight=60 → BMI=22.04 → BFP≈27.95.
    bfp = compute_bmi(gender="F", age=30, height_cm=165, weight_kg=60)
    assert bfp == pytest.approx(27.95, abs=0.05)


def test_compute_bmi_boy_uses_juvenile_formula():
    # age=12, height=150, weight=45 → BMI=20 → BFP=19.6.
    bfp = compute_bmi(gender="M", age=12, height_cm=150, weight_kg=45)
    assert bfp == pytest.approx(19.6, abs=0.05)


def test_compute_bmi_girl_uses_juvenile_formula():
    # age=14, height=155, weight=50 → BMI≈20.81 → BFP≈23.03.
    bfp = compute_bmi(gender="F", age=14, height_cm=155, weight_kg=50)
    assert bfp == pytest.approx(23.03, abs=0.05)


def test_compute_bmi_juvenile_cut_is_inclusive_at_15():
    # age 15 → juvenile branch (≤15). age 16 → adult branch.
    juv = compute_bmi(gender="M", age=15, height_cm=170, weight_kg=60)
    adult = compute_bmi(gender="M", age=16, height_cm=170, weight_kg=60)
    bmi = 60 / (1.70 ** 2)
    expected_juv = 1.51 * bmi - 0.70 * 15 - 2.2
    expected_adult = 1.20 * bmi + 0.23 * 16 - 16.2
    assert juv == pytest.approx(expected_juv, abs=1e-6)
    assert adult == pytest.approx(expected_adult, abs=1e-6)


def test_compute_bmi_rejects_unsupported_gender():
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_bmi(
            gender="X",  # type: ignore[arg-type]
            age=30,
            height_cm=175,
            weight_kg=75,
        )
    assert excinfo.value.code == "UNSUPPORTED_GENDER"


def test_compute_bmi_rejects_out_of_range_weight():
    with pytest.raises(BodyFatValidationError) as excinfo:
        compute_bmi(gender="M", age=30, height_cm=175, weight_kg=500)
    assert excinfo.value.code == "OUT_OF_RANGE"
    assert excinfo.value.field == "weight_kg"


# ---------------------------------------------------------------------------
# ace_category — boundary rows for men and women
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bfp,expected",
    [
        (1.0, "Essential fat"),     # below the table — clamps up
        (5.99, "Essential fat"),
        (6.0, "Athletes"),
        (13.99, "Athletes"),
        (14.0, "Fitness"),
        (17.99, "Fitness"),
        (18.0, "Average"),
        (24.99, "Average"),
        (25.0, "Obese"),
        (40.0, "Obese"),
    ],
)
def test_ace_category_men_boundaries(bfp, expected):
    assert ace_category(bfp, "M") == expected


@pytest.mark.parametrize(
    "bfp,expected",
    [
        (5.0, "Essential fat"),     # below the table — clamps up
        (13.99, "Essential fat"),
        (14.0, "Athletes"),
        (20.99, "Athletes"),
        (21.0, "Fitness"),
        (24.99, "Fitness"),
        (25.0, "Average"),
        (31.99, "Average"),
        (32.0, "Obese"),
        (50.0, "Obese"),
    ],
)
def test_ace_category_women_boundaries(bfp, expected):
    assert ace_category(bfp, "F") == expected


def test_ace_category_rejects_unsupported_gender():
    with pytest.raises(BodyFatValidationError):
        ace_category(20.0, "Other")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# jackson_pollock_ideal — interpolation + clamp
# ---------------------------------------------------------------------------


def test_jackson_pollock_table_corners():
    assert jackson_pollock_ideal(20, "F") == pytest.approx(17.7)
    assert jackson_pollock_ideal(20, "M") == pytest.approx(8.5)
    assert jackson_pollock_ideal(55, "F") == pytest.approx(26.3)
    assert jackson_pollock_ideal(55, "M") == pytest.approx(20.9)


def test_jackson_pollock_clamps_below_table():
    # Age 18 → clamp to age-20 row.
    assert jackson_pollock_ideal(18, "F") == pytest.approx(17.7)
    assert jackson_pollock_ideal(18, "M") == pytest.approx(8.5)


def test_jackson_pollock_clamps_above_table():
    # Age 70 → clamp to age-55 row.
    assert jackson_pollock_ideal(70, "F") == pytest.approx(26.3)
    assert jackson_pollock_ideal(70, "M") == pytest.approx(20.9)


def test_jackson_pollock_interpolates_female():
    # Age 22.5 between 20 (17.7) and 25 (18.4) — but age must be int.
    # Use 22: frac = 0.4 → 17.7 + 0.4*(18.4-17.7) = 17.98.
    bfp = jackson_pollock_ideal(22, "F")
    assert bfp == pytest.approx(17.98, abs=1e-3)


def test_jackson_pollock_interpolates_male():
    # Age 27 between 25 (10.5) and 30 (12.7), frac = 0.4 → 11.38.
    bfp = jackson_pollock_ideal(27, "M")
    assert bfp == pytest.approx(11.38, abs=1e-3)


def test_jackson_pollock_interpolates_at_bracket_boundary():
    # Age == bracket row → exact table value, no interpolation drift.
    assert jackson_pollock_ideal(35, "M") == pytest.approx(13.7)
    assert jackson_pollock_ideal(40, "F") == pytest.approx(22.2)


def test_jackson_pollock_rejects_unsupported_gender():
    with pytest.raises(BodyFatValidationError):
        jackson_pollock_ideal(30, "X")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Python ↔ JS mirror lockstep
#
# Mirrors the precedent set by
# tests/test_profile_estimator.py:test_bodymap_canonical_in_sync — catches
# the case where someone edits one side of the Python ↔ JS mirror without
# the other. Parses the JS module as text and compares its exported
# constants against the Python source.
# ---------------------------------------------------------------------------


def test_body_fat_python_js_mirror_in_sync():
    import re
    from pathlib import Path

    from utils.body_fat import (
        BMI_JUVENILE_AGE_CUTOFF,
        _ACE_BANDS_MEN,
        _ACE_BANDS_WOMEN,
        _JP_TABLE,
    )

    js_path = (
        Path(__file__).resolve().parents[1]
        / "static"
        / "js"
        / "modules"
        / "body-composition.js"
    )
    js_text = js_path.read_text(encoding="utf-8")

    # 1) Juvenile age cutoff.
    cutoff_match = re.search(
        r"BMI_JUVENILE_AGE_CUTOFF\s*=\s*(\d+)\s*;", js_text
    )
    assert cutoff_match, "BMI_JUVENILE_AGE_CUTOFF not found in JS module"
    assert int(cutoff_match.group(1)) == BMI_JUVENILE_AGE_CUTOFF

    # 2) ACE bands — men and women.
    def _parse_ace_block(name):
        block = re.search(
            rf"{name}\s*=\s*\[(.+?)\];",
            js_text,
            re.DOTALL,
        )
        assert block, f"{name} block not found in JS module"
        rows = re.findall(
            r"\[\s*'([^']+)'\s*,\s*([\w.]+)\s*\]",
            block.group(1),
        )

        def _to_float(token):
            return float("inf") if token == "Infinity" else float(token)

        return [(label, _to_float(upper)) for label, upper in rows]

    js_men = _parse_ace_block("ACE_BANDS_MEN")
    js_women = _parse_ace_block("ACE_BANDS_WOMEN")
    assert js_men == list(_ACE_BANDS_MEN), (
        f"ACE_BANDS_MEN drift: JS={js_men} PY={list(_ACE_BANDS_MEN)}"
    )
    assert js_women == list(_ACE_BANDS_WOMEN), (
        f"ACE_BANDS_WOMEN drift: JS={js_women} PY={list(_ACE_BANDS_WOMEN)}"
    )

    # 3) Jackson & Pollock table.
    jp_block = re.search(r"JP_TABLE\s*=\s*\[(.+?)\];", js_text, re.DOTALL)
    assert jp_block, "JP_TABLE block not found in JS module"
    js_jp = [
        (int(age), float(women), float(men))
        for age, women, men in re.findall(
            r"\[\s*(\d+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]",
            jp_block.group(1),
        )
    ]
    assert js_jp == list(_JP_TABLE), (
        f"JP_TABLE drift: JS={js_jp} PY={list(_JP_TABLE)}"
    )
