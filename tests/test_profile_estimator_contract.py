"""Stable import/export contracts required before profile_estimator is split."""

from __future__ import annotations

import subprocess
import sys

import pytest

import utils.lift_matching as lift_matching
import utils.profile_estimator as profile_estimator


SUPPORTED_ESTIMATOR_EXPORTS = {
    "ACCURACY_MAJOR_MUSCLE_GROUPS",
    "ADVANCED_COHORT_REACH",
    "BODYMAP_MUSCLE_KEYS",
    "DEFAULT_ESTIMATE",
    "DEFAULT_PREFERENCES",
    "DIRECT_LIFT_MATCHERS",
    "DUMBBELL_LIFT_KEYS",
    "EXPERIENCE_MULTIPLIERS",
    "KEY_LIFTS",
    "KEY_LIFT_LABELS",
    "KEY_LIFT_SIDE",
    "KEY_LIFT_TIER",
    "MUSCLE_TO_KEY_LIFT",
    "REP_RANGE_PRESETS",
    "_load_basis_factor",
    "_match_direct_lift_key",
    "accuracy_band",
    "classify_tier",
    "cohort_bars",
    "cohort_ranges",
    "cold_start_1rm",
    "cold_start_anchor_lifts",
    "coverage_donut",
    "epley_1rm",
    "estimate_for_exercise",
    "match_direct_lift_key",
    "muscle_coverage_state",
    "next_high_impact_lifts",
    "replaced_anchor_lifts",
    "round_weight",
}


def test_supported_estimator_export_surface_is_present():
    missing = SUPPORTED_ESTIMATOR_EXPORTS - vars(profile_estimator).keys()
    assert not missing, f"profile_estimator dropped supported exports: {sorted(missing)}"


def test_lift_matching_aliases_preserve_object_identity():
    assert profile_estimator.DIRECT_LIFT_MATCHERS is lift_matching.DIRECT_LIFT_MATCHERS
    assert profile_estimator.match_direct_lift_key is lift_matching.match_direct_lift_key
    assert profile_estimator._match_direct_lift_key is lift_matching.match_direct_lift_key


@pytest.mark.parametrize(
    "first, second",
    [
        ("utils.profile_estimator", "utils.strength_calibration"),
        ("utils.strength_calibration", "utils.profile_estimator"),
    ],
)
def test_profile_estimator_and_calibration_import_in_either_order(first, second):
    script = f"""
import importlib
import sys

first = importlib.import_module({first!r})
second = importlib.import_module({second!r})
profile = importlib.import_module('utils.profile_estimator')
calibration = importlib.import_module('utils.strength_calibration')
matching = importlib.import_module('utils.lift_matching')

assert profile.epley_1rm is calibration.epley_1rm
assert profile.match_direct_lift_key is matching.match_direct_lift_key
assert profile._match_direct_lift_key is matching.match_direct_lift_key
assert 'utils.profile_estimator' in sys.modules
assert 'utils.strength_calibration' in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
