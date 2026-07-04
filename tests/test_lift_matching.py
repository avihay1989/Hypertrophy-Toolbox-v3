"""Direct characterization of the shared lift-name matching contract."""

from utils.lift_matching import DIRECT_LIFT_MATCHERS, match_direct_lift_key


def test_every_declared_keyword_resolves_to_its_declared_lift_key():
    for keyword, lift_key in DIRECT_LIFT_MATCHERS:
        assert match_direct_lift_key(keyword) == lift_key, keyword


def test_specific_variants_precede_broader_substring_fallbacks():
    cases = {
        "Weighted Pull Up": "weighted_pullups",
        "Leg Press Calf Raise": "leg_press_calf_raise",
        "Reverse Lunge": "reverse_lunge",
        "B-Stance Hip Thrust": "b_stance_hip_thrust",
        "Loaded Back Extension": "loaded_back_extension",
        "Seated Good Morning": "seated_good_morning",
    }

    assert list(cases)  # make an accidentally emptied characterization fail loudly
    for exercise_name, expected in cases.items():
        assert match_direct_lift_key(exercise_name) == expected


def test_matching_is_case_insensitive_substring_based_and_empty_safe():
    assert match_direct_lift_key("Tempo BARBELL BACK SQUAT (Paused)") == "barbell_back_squat"
    assert match_direct_lift_key("Cable movement with no reference lift") is None
    assert match_direct_lift_key("") is None
    assert match_direct_lift_key(None) is None  # type: ignore[arg-type]
