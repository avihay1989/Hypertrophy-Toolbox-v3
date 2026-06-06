"""Shared exercise-name → key-lift slug matching.

Extracted from ``profile_estimator.py`` so both the estimator and
``strength_calibration.py`` can reference the matching logic without a
circular import chain.

The ``DIRECT_LIFT_MATCHERS`` table and the ``match_direct_lift_key()``
function are the only public API. Order in ``DIRECT_LIFT_MATCHERS``
matters: longer/more-specific keywords must come before shorter ones
(e.g. "weighted pull up" before "pull up").
"""
from __future__ import annotations

from typing import Optional

# Exercise-name keywords that map directly to a key_lift slug. When the
# exercise being estimated matches one of these, the corresponding lift is
# used as the primary reference (no cross_factor penalty), regardless of
# the muscle's chain order. Order matters: longer/more-specific keywords
# must come before shorter ones (e.g. "weighted pull up" before "pull up").
DIRECT_LIFT_MATCHERS: tuple[tuple[str, str], ...] = (
    # Weighted pull-up / chin-up / dip variants — must precede bare forms.
    ("weighted pull-up", "weighted_pullups"),
    ("weighted pull up", "weighted_pullups"),
    ("weighted pullup", "weighted_pullups"),
    ("weighted chin-up", "weighted_pullups"),
    ("weighted chin up", "weighted_pullups"),
    ("weighted chinup", "weighted_pullups"),
    ("weighted dip", "weighted_dips"),
    # Squat variants — barbell-back/front first, dumbbell variants own slug.
    ("barbell back squat", "barbell_back_squat"),
    ("back squat", "barbell_back_squat"),
    ("front squat", "barbell_back_squat"),
    # Issue #20 — Bulgarian / split-squat variant before bare squat fallbacks.
    ("bulgarian split squat", "bulgarian_split_squat"),
    ("split squat", "bulgarian_split_squat"),
    ("goblet squat", "dumbbell_squat"),
    ("dumbbell squat", "dumbbell_squat"),
    # Lunges and step-ups (longest-first).
    # Issue #20 — reverse-lunge variant must precede bare lunge match.
    ("reverse lunge", "reverse_lunge"),
    ("dumbbell lunge", "dumbbell_lunge"),
    ("dumbbell step-up", "dumbbell_step_up"),
    ("dumbbell step up", "dumbbell_step_up"),
    ("step-up", "dumbbell_step_up"),
    ("step up", "dumbbell_step_up"),
    ("lunge", "dumbbell_lunge"),
    # Deadlift family — Issue #9 splits + Issue #6 hamstring additions.
    ("single-leg rdl", "single_leg_rdl"),
    ("single leg rdl", "single_leg_rdl"),
    ("single-leg romanian deadlift", "single_leg_rdl"),
    ("single leg romanian deadlift", "single_leg_rdl"),
    ("stiff-leg deadlift", "stiff_leg_deadlift"),
    ("stiff leg deadlift", "stiff_leg_deadlift"),
    ("romanian deadlift", "romanian_deadlift"),
    ("conventional deadlift", "conventional_deadlift"),
    # Issue #20 — sumo deadlift now has its own slug (was routed to
    # conventional_deadlift). The trap-bar variant stays mapped to
    # conventional_deadlift since it remains a hip-dominant trap-bar pull
    # and we don't have a dedicated slug for it.
    ("sumo deadlift", "sumo_deadlift"),
    ("trap bar deadlift", "conventional_deadlift"),
    # Issue #20 — Jefferson curl is a loaded spinal-flexion accessory.
    ("jefferson curl", "jefferson_curl"),
    # Issue #20 — seated good morning before bare good-morning match.
    ("seated good morning", "seated_good_morning"),
    ("good morning", "good_morning"),
    # Bench-press family — Issue #9 split + Issue #6 chest additions.
    ("incline barbell bench", "incline_bench_press"),
    ("incline dumbbell bench", "incline_bench_press"),
    ("incline bench press", "incline_bench_press"),
    ("smith machine bench", "smith_machine_bench_press"),
    ("smith bench", "smith_machine_bench_press"),
    ("machine chest press", "machine_chest_press"),
    ("machine bench press", "machine_chest_press"),
    ("dumbbell fly", "dumbbell_fly"),
    ("dumbbell flye", "dumbbell_fly"),
    ("chest fly", "dumbbell_fly"),
    ("dumbbell bench press", "dumbbell_bench_press"),
    ("flat dumbbell bench press", "dumbbell_bench_press"),
    ("flat dumbbell bench", "dumbbell_bench_press"),
    ("barbell bench press", "barbell_bench_press"),
    ("flat bench press", "barbell_bench_press"),
    # Hip thrust — Issue #20 splits B-stance and barbell glute bridge first.
    ("b-stance hip thrust", "b_stance_hip_thrust"),
    ("b stance hip thrust", "b_stance_hip_thrust"),
    ("barbell glute bridge", "barbell_glute_bridge"),
    ("glute bridge", "barbell_glute_bridge"),
    ("hip thrust", "hip_thrust"),
    # Issue #20 — pull-through and cable-kickback glute accessories.
    ("cable pull-through", "cable_pull_through"),
    ("cable pull through", "cable_pull_through"),
    ("pull-through", "cable_pull_through"),
    ("pull through", "cable_pull_through"),
    ("cable kickback", "cable_kickback"),
    ("glute kickback", "cable_kickback"),
    ("kickback", "cable_kickback"),
    # Leg press — Issue #20: leg-press calf raise routes ahead of bare leg press.
    ("leg press calf raise", "leg_press_calf_raise"),
    ("leg press", "leg_press"),
    # Rows — barbell-row family + machine row split-out.
    ("barbell row", "barbell_row"),
    ("bent-over row", "barbell_row"),
    ("bent over row", "barbell_row"),
    ("pendlay row", "barbell_row"),
    ("t-bar row", "barbell_row"),
    ("machine row", "machine_row"),
    # Overhead / shoulder press family — Issue #6 additions.
    ("arnold press", "arnold_press"),
    ("dumbbell shoulder press", "dumbbell_shoulder_press"),
    ("dumbbell overhead press", "dumbbell_shoulder_press"),
    ("machine shoulder press", "machine_shoulder_press"),
    ("machine overhead press", "machine_shoulder_press"),
    ("military press", "military_press"),
    ("overhead press", "military_press"),
    ("barbell shoulder press", "military_press"),
    # Face pulls / shrugs.
    ("face pull", "face_pulls"),
    ("barbell shrug", "barbell_shrugs"),
    ("shrug", "barbell_shrugs"),
    # Bicep curls — split out new dumbbell / preacher / incline variants.
    ("incline dumbbell curl", "incline_dumbbell_curl"),
    ("incline curl", "incline_dumbbell_curl"),
    ("preacher curl", "preacher_curl"),
    ("hammer curl", "dumbbell_curl"),
    ("dumbbell bicep curl", "dumbbell_curl"),
    ("dumbbell curl", "dumbbell_curl"),
    ("barbell bicep curl", "barbell_bicep_curl"),
    ("barbell curl", "barbell_bicep_curl"),
    ("ez bar curl", "barbell_bicep_curl"),
    # Triceps — skull crusher / JM press split out.
    ("skull crusher", "skull_crusher"),
    ("jm press", "jm_press"),
    ("triceps extension", "triceps_extension"),
    ("tricep extension", "triceps_extension"),
    # Lower-body isolation.
    ("leg curl", "leg_curl"),
    ("leg extension", "leg_extension"),
    # Lateral raise.
    ("lateral raise", "dumbbell_lateral_raise"),
    # Calves — Issue #20: variant slugs (longest-first) precede bare match.
    ("single-leg standing calf raise", "single_leg_standing_calf_raise"),
    ("single leg standing calf raise", "single_leg_standing_calf_raise"),
    ("seated calf raise", "seated_calf_raise"),
    ("smith machine calf raise", "smith_machine_calf_raise"),
    ("smith calf raise", "smith_machine_calf_raise"),
    ("donkey calf raise", "donkey_calf_raise"),
    ("standing calf raise", "standing_calf_raise"),
    ("calf raise", "standing_calf_raise"),
    # Hip abduction.
    ("hip abduction", "machine_hip_abduction"),
    ("machine abduction", "machine_hip_abduction"),
    # Core / abs.
    ("cable crunch", "cable_crunch"),
    ("machine crunch", "machine_crunch"),
    ("weighted crunch", "weighted_crunch"),
    ("cable woodchop", "cable_woodchop"),
    ("wood chop", "cable_woodchop"),
    ("woodchop", "cable_woodchop"),
    ("side bend", "side_bend"),
    # Lower back — Issue #20: loaded / reverse variants precede bare matches.
    ("loaded back extension", "loaded_back_extension"),
    ("loaded hyperextension", "loaded_back_extension"),
    ("45 back extension", "loaded_back_extension"),
    ("45 degree back extension", "loaded_back_extension"),
    ("reverse hyperextension", "reverse_hyperextension"),
    ("reverse hyper", "reverse_hyperextension"),
    ("back extension", "back_extension"),
    ("hyperextension", "back_extension"),
    # Bare pull-up / chin-up — bodyweight (must come AFTER weighted entries).
    ("pull-up", "bodyweight_pullups"),
    ("pull up", "bodyweight_pullups"),
    ("pullup", "bodyweight_pullups"),
    ("chin-up", "bodyweight_chinups"),
    ("chin up", "bodyweight_chinups"),
    ("chinup", "bodyweight_chinups"),
)


def match_direct_lift_key(exercise_name: str) -> Optional[str]:
    """Return the key_lift slug that directly matches the given exercise name.

    Used to bypass the muscle-chain cross_factor penalty when the exercise
    being estimated is itself one of the questionnaire reference lifts
    (e.g. estimating "Barbell Romanian Deadlift" should use the user's
    ``romanian_deadlift`` reference directly, not fall through Hamstrings'
    leg_curl-first chain).
    """
    name = (exercise_name or "").lower()
    if not name:
        return None
    for keyword, lift_key in DIRECT_LIFT_MATCHERS:
        if keyword in name:
            return lift_key
    return None
