"""Tests for utils/body_fat.py — Issue #21 first slice.

Pure-function tests; no DB or HTTP. Tolerances use pytest.approx with
explicit absolute bounds because the Navy formula chains two log10 calls
and small rounding differences are expected across implementations.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils.body_fat import (
    ace_category,
    compute_bmi,
    compute_navy,
    jackson_pollock_ideal,
)


PARITY_FIXTURE = (
    Path(__file__).resolve().parents[1] / "e2e" / "fixtures" / "body-fat-parity.json"
)


def test_shared_js_python_parity_fixture_matches_all_four_public_functions():
    cases = json.loads(PARITY_FIXTURE.read_text(encoding="utf-8"))
    assert cases

    for case in cases:
        profile = case["profile"]
        expected = case["expected"]
        bmi = compute_bmi(
            gender=profile["gender"],
            age_years=profile["age"],
            height_cm=profile["height_cm"],
            bodyweight_kg=profile["weight_kg"],
        )
        if case["tape"] is None:
            effective_bfp = bmi["bfp"]
        else:
            effective_bfp = compute_navy(
                gender=profile["gender"],
                height_cm=profile["height_cm"],
                **case["tape"],
            )

        assert round(effective_bfp, 1) == expected["bfp"], case["id"]
        assert round(bmi["bmi"], 1) == expected["bmi"], case["id"]
        assert ace_category(effective_bfp, profile["gender"]) == expected["ace"], case["id"]
        assert round(jackson_pollock_ideal(profile["age"], profile["gender"]), 1) == expected[
            "jackson_pollock_ideal"
        ], case["id"]


# -- compute_navy -----------------------------------------------------------

def test_compute_navy_male_typical_lifter():
    bfp = compute_navy(
        gender="M", height_cm=180.0, neck_cm=38.0, waist_cm=85.0
    )
    assert bfp == pytest.approx(16.13, abs=0.1)


def test_compute_navy_female_typical_lifter():
    bfp = compute_navy(
        gender="F",
        height_cm=165.0,
        neck_cm=32.0,
        waist_cm=70.0,
        hip_cm=95.0,
    )
    assert bfp == pytest.approx(24.86, abs=0.1)


def test_compute_navy_male_rejects_waist_le_neck_log_domain():
    with pytest.raises(ValueError, match="waist circumference"):
        compute_navy(gender="M", height_cm=180.0, neck_cm=40.0, waist_cm=40.0)
    with pytest.raises(ValueError, match="waist circumference"):
        compute_navy(gender="M", height_cm=180.0, neck_cm=42.0, waist_cm=40.0)


def test_compute_navy_female_rejects_log_domain_violation():
    with pytest.raises(ValueError, match="waist \\+ hip"):
        compute_navy(
            gender="F",
            height_cm=165.0,
            neck_cm=200.0,
            waist_cm=50.0,
            hip_cm=50.0,
        )


def test_compute_navy_male_rejects_hip_argument():
    with pytest.raises(ValueError, match="hip must not be provided"):
        compute_navy(
            gender="M",
            height_cm=180.0,
            neck_cm=38.0,
            waist_cm=85.0,
            hip_cm=95.0,
        )


def test_compute_navy_female_requires_hip():
    with pytest.raises(ValueError, match="hip is required"):
        compute_navy(gender="F", height_cm=165.0, neck_cm=32.0, waist_cm=70.0)


def test_compute_navy_rejects_out_of_range_height():
    with pytest.raises(ValueError, match="height"):
        compute_navy(gender="M", height_cm=50.0, neck_cm=38.0, waist_cm=85.0)
    with pytest.raises(ValueError, match="height"):
        compute_navy(gender="M", height_cm=300.0, neck_cm=38.0, waist_cm=85.0)


def test_compute_navy_rejects_invalid_gender():
    with pytest.raises(ValueError, match="gender"):
        compute_navy(gender="X", height_cm=180.0, neck_cm=38.0, waist_cm=85.0)


# -- compute_bmi ------------------------------------------------------------

def test_compute_bmi_adult_male():
    result = compute_bmi(
        gender="M", age_years=30, height_cm=180.0, bodyweight_kg=80.0
    )
    assert result["bmi"] == pytest.approx(24.691, abs=0.01)
    assert result["bfp"] == pytest.approx(20.33, abs=0.1)


def test_compute_bmi_adult_female():
    result = compute_bmi(
        gender="F", age_years=30, height_cm=165.0, bodyweight_kg=60.0
    )
    assert result["bmi"] == pytest.approx(22.04, abs=0.01)
    assert result["bfp"] == pytest.approx(27.95, abs=0.1)


def test_compute_bmi_boy_under_18():
    result = compute_bmi(
        gender="M", age_years=14, height_cm=160.0, bodyweight_kg=50.0
    )
    assert result["bmi"] == pytest.approx(19.531, abs=0.01)
    assert result["bfp"] == pytest.approx(17.49, abs=0.1)


def test_compute_bmi_girl_under_18():
    result = compute_bmi(
        gender="F", age_years=14, height_cm=160.0, bodyweight_kg=50.0
    )
    assert result["bmi"] == pytest.approx(19.531, abs=0.01)
    assert result["bfp"] == pytest.approx(21.09, abs=0.1)


def test_compute_bmi_age_18_uses_adult_formula():
    adult = compute_bmi(gender="M", age_years=18, height_cm=180.0, bodyweight_kg=80.0)
    minor = compute_bmi(gender="M", age_years=17, height_cm=180.0, bodyweight_kg=80.0)
    assert adult["bfp"] != pytest.approx(minor["bfp"], abs=0.01)


def test_compute_bmi_rejects_out_of_range_weight():
    with pytest.raises(ValueError, match="bodyweight"):
        compute_bmi(gender="M", age_years=30, height_cm=180.0, bodyweight_kg=10.0)


# -- ace_category -----------------------------------------------------------

@pytest.mark.parametrize(
    "bfp, expected",
    [
        (3.0, "Essential fat"),
        (5.9, "Essential fat"),
        (6.0, "Athletes"),
        (13.9, "Athletes"),
        (14.0, "Fitness"),
        (17.9, "Fitness"),
        (18.0, "Average"),
        (24.9, "Average"),
        (25.0, "Obese"),
        (45.0, "Obese"),
    ],
)
def test_ace_category_male_boundaries(bfp, expected):
    assert ace_category(bfp, "M") == expected


@pytest.mark.parametrize(
    "bfp, expected",
    [
        (12.0, "Essential fat"),
        (13.9, "Essential fat"),
        (14.0, "Athletes"),
        (20.9, "Athletes"),
        (21.0, "Fitness"),
        (24.9, "Fitness"),
        (25.0, "Average"),
        (31.9, "Average"),
        (32.0, "Obese"),
        (45.0, "Obese"),
    ],
)
def test_ace_category_female_boundaries(bfp, expected):
    assert ace_category(bfp, "F") == expected


def test_ace_category_low_values_clamp_to_essential_fat():
    assert ace_category(0.5, "M") == "Essential fat"
    assert ace_category(0.5, "F") == "Essential fat"


# -- jackson_pollock_ideal --------------------------------------------------

def test_jackson_pollock_table_anchor_male_age_30():
    assert jackson_pollock_ideal(30, "M") == pytest.approx(12.7, abs=0.001)


def test_jackson_pollock_table_anchor_female_age_40():
    assert jackson_pollock_ideal(40, "F") == pytest.approx(22.2, abs=0.001)


def test_jackson_pollock_interpolation_male_age_27():
    # Between (25, 10.5) and (30, 12.7) — ratio 2/5
    expected = 10.5 + (12.7 - 10.5) * (2 / 5)
    assert jackson_pollock_ideal(27, "M") == pytest.approx(expected, abs=0.001)


def test_jackson_pollock_interpolation_female_age_42():
    # Between (40, 22.2) and (45, 22.9) — ratio 2/5
    expected = 22.2 + (22.9 - 22.2) * (2 / 5)
    assert jackson_pollock_ideal(42, "F") == pytest.approx(expected, abs=0.001)


def test_jackson_pollock_age_clamp_below_20():
    # Ages below 20 clamp to the 20-year row.
    assert jackson_pollock_ideal(18, "M") == pytest.approx(8.5, abs=0.001)
    assert jackson_pollock_ideal(15, "F") == pytest.approx(17.7, abs=0.001)
    assert jackson_pollock_ideal(20, "M") == pytest.approx(8.5, abs=0.001)


def test_jackson_pollock_age_clamp_above_55():
    # Ages above 55 clamp to the 55-year row.
    assert jackson_pollock_ideal(60, "M") == pytest.approx(20.9, abs=0.001)
    assert jackson_pollock_ideal(72, "F") == pytest.approx(26.3, abs=0.001)
    assert jackson_pollock_ideal(55, "M") == pytest.approx(20.9, abs=0.001)


def test_jackson_pollock_rejects_invalid_gender():
    with pytest.raises(ValueError, match="gender"):
        jackson_pollock_ideal(30, "x")
