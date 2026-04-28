"""User-profile-based workout control estimates.

Dumbbell weight convention (Issue #10, 2026-04-27)
--------------------------------------------------
All dumbbell weights — both **inputs** (Reference Lifts on
``/user_profile``) and **outputs** (Workout Controls suggestions on
``/workout_plan``) — are expressed as **weight per hand**, i.e. the
mass of one dumbbell. A user holding 20 kg in each hand records 20 (not
40) for ``dumbbell_bench_press``, and the estimator returns 20 (not 40)
for the working weight on a dumbbell exercise.

The estimator math (``epley_1rm`` → ``TIER_RATIOS`` → ``REP_RANGE_PRESETS``
→ ``round_weight``) is unit-agnostic: it treats ``weight`` as a single
opaque scalar end-to-end. As long as input and output share the same
convention, no conversion is needed. Helper text on the questionnaire
and on the Workout Controls weight field communicates the convention to
the user; ``DUMBBELL_LIFT_KEYS`` and the ``is_dumbbell`` flag on the
estimate response drive the conditional UI.

See ``docs/user_profile/DESIGN.md`` §6.1 for the canonical statement.
"""
from __future__ import annotations

import math
from typing import Any, Literal, Optional

from utils.database import DatabaseHandler
from utils.logger import get_logger
from utils.normalization import normalize_equipment, normalize_muscle

logger = get_logger()

Tier = Literal["complex", "accessory", "isolated", "excluded"]

DUMBBELL_LIFT_KEYS = frozenset(
    {
        "dumbbell_bench_press",
        "dumbbell_fly",
        "dumbbell_shoulder_press",
        "dumbbell_lateral_raise",
        "dumbbell_curl",
        "incline_dumbbell_curl",
        "dumbbell_squat",
        "dumbbell_lunge",
        "dumbbell_step_up",
        "arnold_press",
    }
)

KEY_LIFTS = frozenset(
    {
        # Original questionnaire slugs.
        "barbell_bench_press",
        "barbell_back_squat",
        "romanian_deadlift",
        "triceps_extension",
        "barbell_bicep_curl",
        "dumbbell_lateral_raise",
        "military_press",
        "leg_curl",
        "leg_extension",
        "weighted_dips",
        "weighted_pullups",
        "bodyweight_pullups",
        "bodyweight_dips",
        "barbell_row",
        # Issue #9 — splits of formerly combined slugs.
        "conventional_deadlift",
        "dumbbell_bench_press",
        # Issue #6 — chest additions.
        "incline_bench_press",
        "smith_machine_bench_press",
        "machine_chest_press",
        "dumbbell_fly",
        # Issue #6 — back additions.
        "machine_row",
        "bodyweight_chinups",
        # Issue #6 — shoulder additions.
        "dumbbell_shoulder_press",
        "machine_shoulder_press",
        "arnold_press",
        "face_pulls",
        "barbell_shrugs",
        # Issue #6 — biceps additions.
        "dumbbell_curl",
        "preacher_curl",
        "incline_dumbbell_curl",
        # Issue #6 — triceps additions.
        "skull_crusher",
        "jm_press",
        # Issue #6 — quads / glutes additions.
        "leg_press",
        "dumbbell_squat",
        "dumbbell_lunge",
        "dumbbell_step_up",
        "hip_thrust",
        # Issue #6 — hamstring additions.
        "stiff_leg_deadlift",
        "good_morning",
        "single_leg_rdl",
        # Issue #6 — calves.
        "standing_calf_raise",
        # Issue #6 — glutes / hip.
        "machine_hip_abduction",
        # Issue #6 — core / abs.
        "cable_crunch",
        "machine_crunch",
        "weighted_crunch",
        "cable_woodchop",
        "side_bend",
        # Issue #6 — lower back.
        "back_extension",
        # Issue #20 — calves expansion.
        "seated_calf_raise",
        "leg_press_calf_raise",
        "smith_machine_calf_raise",
        "single_leg_standing_calf_raise",
        "donkey_calf_raise",
        # Issue #20 — glutes / hips expansion.
        "barbell_glute_bridge",
        "cable_pull_through",
        "bulgarian_split_squat",
        "b_stance_hip_thrust",
        "reverse_lunge",
        "sumo_deadlift",
        "cable_kickback",
        # Issue #20 — lower back expansion.
        "loaded_back_extension",
        "reverse_hyperextension",
        "seated_good_morning",
        "jefferson_curl",
    }
)

COMPLEX_ALLOWLIST = frozenset(
    {
        "barbell back squat",
        "barbell front squat",
        "back squat",
        "front squat",
        "conventional deadlift",
        "sumo deadlift",
        "romanian deadlift",
        "trap bar deadlift",
        "stiff leg deadlift",
        "single leg rdl",
        "good morning",
        "deadlift",
        "barbell bench press",
        "dumbbell bench press",
        "incline barbell bench",
        "incline dumbbell bench",
        "flat bench press",
        "overhead press",
        "military press",
        "shoulder press",
        "weighted dip",
        "weighted pull up",
        "weighted pullup",
        "weighted chin up",
        "weighted chinup",
        "pull up",
        "pullup",
        "chin up",
        "chinup",
        "barbell row",
        "pendlay row",
        "t bar row",
        "bent over row",
        "hip thrust",
        "power clean",
        "hang clean",
        "snatch",
        "push press",
        # Issue #20 — additions to the complex allowlist.
        "glute bridge",
        "b-stance hip thrust",
        "b stance hip thrust",
        "seated good morning",
    }
)

EXCLUDED_EQUIPMENT = frozenset(
    {"Trx", "Bosu_Ball", "Cardio", "Recovery", "Yoga", "Vitruvian", "Band", "Stretches"}
)

TIER_RATIOS = {
    "complex": 1.00,
    "accessory": 0.70,
    "isolated": 0.40,
}

# Implied tier of each questionnaire reference lift, used to normalise the
# tier multiplier in `_estimate_from_profile` (Issue #14). Without this,
# `TIER_RATIOS[target_tier]` is applied unconditionally, double-discounting
# same-tier paths (iso→iso, accessory→accessory) and producing severely
# underestimated suggestions. With normalisation
# (`min(TIER_RATIOS[target] / TIER_RATIOS[reference], 1.0)`), same-tier
# paths use multiplier 1.00 while complex→iso etc. preserve their downscaling.
# The `min(..., 1.0)` cap keeps the conservative behaviour of upscaling
# paths (e.g. iso reference → complex target stays at 1.00, never inflates).
KEY_LIFT_TIER: dict[str, Tier] = {
    # Complex compound lifts (heavy multi-joint, in COMPLEX_ALLOWLIST).
    "barbell_bench_press": "complex",
    "dumbbell_bench_press": "complex",
    "incline_bench_press": "complex",
    "barbell_back_squat": "complex",
    "romanian_deadlift": "complex",
    "conventional_deadlift": "complex",
    "stiff_leg_deadlift": "complex",
    "single_leg_rdl": "complex",
    "good_morning": "complex",
    "military_press": "complex",
    "weighted_dips": "complex",
    "weighted_pullups": "complex",
    "bodyweight_pullups": "complex",
    "bodyweight_chinups": "complex",
    "bodyweight_dips": "complex",
    "barbell_row": "complex",
    "hip_thrust": "complex",
    # Issue #20 — glute / hip / lower-back complex compounds.
    "barbell_glute_bridge": "complex",
    "b_stance_hip_thrust": "complex",
    "sumo_deadlift": "complex",
    "seated_good_morning": "complex",
    # Accessory compound lifts (machine / dumbbell variants of compounds,
    # smaller-mover compounds).
    "smith_machine_bench_press": "accessory",
    "machine_chest_press": "accessory",
    "machine_row": "accessory",
    "leg_press": "accessory",
    "dumbbell_squat": "accessory",
    "dumbbell_lunge": "accessory",
    "dumbbell_step_up": "accessory",
    "dumbbell_shoulder_press": "accessory",
    "machine_shoulder_press": "accessory",
    "arnold_press": "accessory",
    "face_pulls": "accessory",
    "barbell_shrugs": "accessory",
    "skull_crusher": "accessory",
    "jm_press": "accessory",
    # Issue #20 — additional accessory variants.
    "cable_pull_through": "accessory",
    "bulgarian_split_squat": "accessory",
    "reverse_lunge": "accessory",
    "loaded_back_extension": "accessory",
    # Isolation lifts (single-joint).
    "triceps_extension": "isolated",
    "barbell_bicep_curl": "isolated",
    "dumbbell_curl": "isolated",
    "preacher_curl": "isolated",
    "incline_dumbbell_curl": "isolated",
    "dumbbell_lateral_raise": "isolated",
    "dumbbell_fly": "isolated",
    "leg_curl": "isolated",
    "leg_extension": "isolated",
    "standing_calf_raise": "isolated",
    "machine_hip_abduction": "isolated",
    "cable_crunch": "isolated",
    "machine_crunch": "isolated",
    "weighted_crunch": "isolated",
    "cable_woodchop": "isolated",
    "side_bend": "isolated",
    "back_extension": "isolated",
    # Issue #20 — calf isolation variants.
    "seated_calf_raise": "isolated",
    "leg_press_calf_raise": "isolated",
    "smith_machine_calf_raise": "isolated",
    "single_leg_standing_calf_raise": "isolated",
    "donkey_calf_raise": "isolated",
    # Issue #20 — additional glute / lower-back isolation variants.
    "cable_kickback": "isolated",
    "reverse_hyperextension": "isolated",
    "jefferson_curl": "isolated",
}

REP_RANGE_PRESETS = {
    "heavy": {"min_rep": 4, "max_rep": 6, "pct_1rm": 0.85, "rir": 1, "rpe": 9.0},
    "moderate": {"min_rep": 6, "max_rep": 8, "pct_1rm": 0.77, "rir": 2, "rpe": 8.0},
    "light": {"min_rep": 10, "max_rep": 15, "pct_1rm": 0.65, "rir": 2, "rpe": 7.5},
}
REP_RANGE_PCT = {key: preset["pct_1rm"] for key, preset in REP_RANGE_PRESETS.items()}

DEFAULT_PREFERENCES = {
    "complex": "heavy",
    "accessory": "moderate",
    "isolated": "light",
}

DEFAULT_ESTIMATE = {
    "weight": 25.0,
    "sets": 3,
    "min_rep": 6,
    "max_rep": 8,
    "rir": 3,
    "rpe": 7.0,
    "source": "default",
}

CROSS_FALLBACK_FACTOR = 0.6
PROFILE_DEFAULT_SETS = 3

# Issue #17 — friendly display names for trace + accuracy-band copy.
# Mirrors the labels used by the Reference Lifts questionnaire on
# `/user_profile`. Kept in this module so the estimator can build
# user-facing trace strings without pulling on `routes.user_profile`.
KEY_LIFT_LABELS: dict[str, str] = {
    "barbell_bench_press": "Barbell Bench Press",
    "dumbbell_bench_press": "Dumbbell Bench Press",
    "incline_bench_press": "Incline Bench Press",
    "smith_machine_bench_press": "Smith Machine Bench Press",
    "machine_chest_press": "Machine Chest Press",
    "dumbbell_fly": "Dumbbell Fly",
    "barbell_row": "Barbell Row",
    "machine_row": "Machine Row",
    "weighted_pullups": "Weighted Pull-ups",
    "bodyweight_pullups": "Bodyweight Pull-ups",
    "bodyweight_chinups": "Bodyweight Chin-ups",
    "military_press": "Military / Shoulder Press",
    "dumbbell_shoulder_press": "Dumbbell Shoulder Press",
    "machine_shoulder_press": "Machine Shoulder Press",
    "arnold_press": "Arnold Press",
    "dumbbell_lateral_raise": "Dumbbell Lateral Raise",
    "face_pulls": "Face Pulls",
    "barbell_shrugs": "Barbell Shrugs",
    "barbell_bicep_curl": "Barbell Bicep Curl",
    "dumbbell_curl": "Dumbbell Curl",
    "preacher_curl": "Preacher Curl (EZ Bar)",
    "incline_dumbbell_curl": "Incline Dumbbell Curl",
    "triceps_extension": "Triceps Extension",
    "skull_crusher": "Skull Crusher (EZ Bar / Barbell)",
    "jm_press": "JM Press",
    "weighted_dips": "Weighted Dips",
    "bodyweight_dips": "Bodyweight Dips",
    "barbell_back_squat": "Barbell Back Squat",
    "leg_press": "Leg Press",
    "leg_extension": "Leg Extension",
    "leg_curl": "Leg Curl",
    "dumbbell_squat": "Dumbbell Squat",
    "dumbbell_lunge": "Dumbbell Lunge",
    "dumbbell_step_up": "Dumbbell Step-Up",
    "hip_thrust": "Hip Thrust",
    "romanian_deadlift": "Romanian Deadlift",
    "conventional_deadlift": "Conventional Deadlift",
    "stiff_leg_deadlift": "Stiff-Leg Deadlift",
    "good_morning": "Good Morning",
    "single_leg_rdl": "Single-Leg RDL",
    "standing_calf_raise": "Standing Calf Raise",
    "seated_calf_raise": "Seated Calf Raise",
    "leg_press_calf_raise": "Leg Press Calf Raise",
    "smith_machine_calf_raise": "Smith Machine Calf Raise",
    "single_leg_standing_calf_raise": "Single-Leg Standing Calf Raise",
    "donkey_calf_raise": "Donkey Calf Raise",
    "machine_hip_abduction": "Machine Hip Abduction",
    "barbell_glute_bridge": "Barbell Glute Bridge",
    "cable_pull_through": "Cable Pull-Through",
    "bulgarian_split_squat": "Bulgarian Split Squat",
    "b_stance_hip_thrust": "B-Stance Hip Thrust",
    "reverse_lunge": "Reverse Lunge",
    "sumo_deadlift": "Sumo Deadlift",
    "cable_kickback": "Cable Kickback",
    "cable_crunch": "Cable Crunch",
    "machine_crunch": "Machine Crunch",
    "weighted_crunch": "Weighted Crunch",
    "cable_woodchop": "Cable Woodchop",
    "side_bend": "Side Bend",
    "back_extension": "Back Extension",
    "loaded_back_extension": "Loaded 45° Back Extension",
    "reverse_hyperextension": "Reverse Hyperextension",
    "seated_good_morning": "Seated Good Morning",
    "jefferson_curl": "Jefferson Curl",
}

# Issue #24 — anatomical side for each reference-lift slug. Drives the
# anterior/posterior partition rendered as two side-by-side cards on the
# Profile page so the questionnaire mirrors the front/back framing of the
# Coverage map (Issue #19). Presentation-only: estimator math, slug routing
# (`MUSCLE_TO_KEY_LIFT`), and tier ratios are unchanged. Every slug in
# `KEY_LIFT_LABELS` must appear on exactly one side — guarded by
# `tests/test_profile_estimator.py::test_key_lift_side_partitions_every_slug`.
KEY_LIFT_SIDE: dict[str, str] = {
    # Anterior — visible on the front view of the bodymap.
    "barbell_bench_press": "anterior",
    "dumbbell_bench_press": "anterior",
    "incline_bench_press": "anterior",
    "smith_machine_bench_press": "anterior",
    "machine_chest_press": "anterior",
    "dumbbell_fly": "anterior",
    "military_press": "anterior",
    "dumbbell_shoulder_press": "anterior",
    "machine_shoulder_press": "anterior",
    "arnold_press": "anterior",
    "dumbbell_lateral_raise": "anterior",
    "barbell_bicep_curl": "anterior",
    "dumbbell_curl": "anterior",
    "preacher_curl": "anterior",
    "incline_dumbbell_curl": "anterior",
    "barbell_back_squat": "anterior",
    "leg_press": "anterior",
    "leg_extension": "anterior",
    "dumbbell_squat": "anterior",
    "dumbbell_lunge": "anterior",
    "reverse_lunge": "anterior",
    "dumbbell_step_up": "anterior",
    "bulgarian_split_squat": "anterior",
    "cable_crunch": "anterior",
    "machine_crunch": "anterior",
    "weighted_crunch": "anterior",
    "cable_woodchop": "anterior",
    "side_bend": "anterior",
    # Posterior — visible on the back view of the bodymap.
    "barbell_row": "posterior",
    "machine_row": "posterior",
    "weighted_pullups": "posterior",
    "bodyweight_pullups": "posterior",
    "bodyweight_chinups": "posterior",
    "face_pulls": "posterior",
    "barbell_shrugs": "posterior",
    "triceps_extension": "posterior",
    "skull_crusher": "posterior",
    "jm_press": "posterior",
    "weighted_dips": "posterior",
    "bodyweight_dips": "posterior",
    "hip_thrust": "posterior",
    "barbell_glute_bridge": "posterior",
    "b_stance_hip_thrust": "posterior",
    "cable_pull_through": "posterior",
    "cable_kickback": "posterior",
    "machine_hip_abduction": "posterior",
    "romanian_deadlift": "posterior",
    "conventional_deadlift": "posterior",
    "sumo_deadlift": "posterior",
    "stiff_leg_deadlift": "posterior",
    "good_morning": "posterior",
    "seated_good_morning": "posterior",
    "single_leg_rdl": "posterior",
    "leg_curl": "posterior",
    "standing_calf_raise": "posterior",
    "seated_calf_raise": "posterior",
    "leg_press_calf_raise": "posterior",
    "smith_machine_calf_raise": "posterior",
    "single_leg_standing_calf_raise": "posterior",
    "donkey_calf_raise": "posterior",
    "back_extension": "posterior",
    "loaded_back_extension": "posterior",
    "reverse_hyperextension": "posterior",
    "jefferson_curl": "posterior",
}

# Issue #16 — cold-start 1RM seeding from demographics.
# Fires only when the entire user_profile_lifts chain for a target muscle is
# empty: a measured reference always wins over a population estimate. Output
# is forced to the Light preset because the user has no measured data and an
# over-prescription is more dangerous than an under-prescription.
COLD_START_PRESET = "light"

# Experience-tier cutoffs in years. Years <= the upper bound for a tier is
# classified into that tier; the highest tier captures everything above the
# previous bound.
EXPERIENCE_TIER_BOUNDS: tuple[tuple[str, float], ...] = (
    ("novice", 1.0),
    ("intermediate", 3.0),
)

EXPERIENCE_MULTIPLIERS = {
    "novice": 0.7,
    "intermediate": 1.0,
    "advanced": 1.2,
}

# Population-table 1RM-per-bodyweight ratios for the representative COMPLEX
# compound on each major muscle group, by gender. Sourced from ExRx /
# Strength Level intermediate columns. The estimator scales the resulting
# 1RM down for accessory / isolation targets via the existing tier ratio
# (`TIER_RATIOS[target] / TIER_RATIOS["complex"]`), then applies the Light
# preset's pct_1rm and rounds for the target equipment.
COLD_START_RATIOS: dict[tuple[str, str], float] = {
    ("Chest", "M"): 1.00,
    ("Chest", "F"): 0.65,
    ("Quadriceps", "M"): 1.50,
    ("Quadriceps", "F"): 1.10,
    ("Hamstrings", "M"): 1.75,
    ("Hamstrings", "F"): 1.35,
    ("Gluteus Maximus", "M"): 2.00,
    ("Gluteus Maximus", "F"): 1.50,
    ("Latissimus Dorsi", "M"): 1.10,
    ("Latissimus Dorsi", "F"): 0.70,
    ("Front-Shoulder", "M"): 0.65,
    ("Front-Shoulder", "F"): 0.40,
    ("Biceps", "M"): 0.40,
    ("Biceps", "F"): 0.25,
    ("Triceps", "M"): 0.45,
    ("Triceps", "F"): 0.30,
}

# Canonical (representative) complex compound for each muscle in
# COLD_START_RATIOS — used by the Issue #17 trace + "How the system sees you"
# card to point users toward the highest-impact reference lift to enter.
COLD_START_CANONICAL_COMPOUND: dict[str, str] = {
    "Chest": "barbell_bench_press",
    "Quadriceps": "barbell_back_squat",
    "Hamstrings": "romanian_deadlift",
    "Gluteus Maximus": "hip_thrust",
    "Latissimus Dorsi": "weighted_pullups",
    "Front-Shoulder": "military_press",
    "Biceps": "barbell_bicep_curl",
    "Triceps": "triceps_extension",
}

# Issue #17 — priority order used when surfacing the next-most-impactful
# reference lift the user has not yet entered (Profile-page card +
# accuracy-band guidance). The first 3 unfilled slugs from this list are
# returned by `next_high_impact_lifts()`.
HIGH_IMPACT_LIFT_PRIORITY: tuple[str, ...] = (
    "barbell_bench_press",
    "barbell_back_squat",
    "romanian_deadlift",
    "weighted_pullups",
    "military_press",
    "barbell_bicep_curl",
    "triceps_extension",
    "barbell_row",
    "standing_calf_raise",
)

# Major-muscle groups whose coverage gates the "mostly personalised" band
# in `accuracy_band()`. Each group is satisfied if any of the listed slugs
# has a non-null entry in `user_profile_lifts`.
ACCURACY_MAJOR_MUSCLE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Chest", (
        "barbell_bench_press",
        "dumbbell_bench_press",
        "incline_bench_press",
        "smith_machine_bench_press",
        "machine_chest_press",
        "dumbbell_fly",
    )),
    ("Back", (
        "barbell_row",
        "machine_row",
        "weighted_pullups",
        "bodyweight_pullups",
        "bodyweight_chinups",
    )),
    ("Legs", (
        "barbell_back_squat",
        "leg_press",
        "leg_extension",
        "dumbbell_squat",
        "dumbbell_lunge",
        "dumbbell_step_up",
        "hip_thrust",
        "romanian_deadlift",
        "conventional_deadlift",
        "stiff_leg_deadlift",
        "good_morning",
        "single_leg_rdl",
        "leg_curl",
        # Issue #20 — additional leg / glute / hip compounds.
        "barbell_glute_bridge",
        "cable_pull_through",
        "bulgarian_split_squat",
        "b_stance_hip_thrust",
        "reverse_lunge",
        "sumo_deadlift",
    )),
    ("Shoulders", (
        "military_press",
        "dumbbell_shoulder_press",
        "machine_shoulder_press",
        "arnold_press",
        "dumbbell_lateral_raise",
    )),
    ("Biceps", (
        "barbell_bicep_curl",
        "dumbbell_curl",
        "preacher_curl",
        "incline_dumbbell_curl",
    )),
    ("Triceps", (
        "triceps_extension",
        "skull_crusher",
        "jm_press",
        "weighted_dips",
        "bodyweight_dips",
    )),
)

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

MUSCLE_TO_KEY_LIFT = {
    "Chest": [
        "barbell_bench_press",
        "dumbbell_bench_press",
        "incline_bench_press",
        "smith_machine_bench_press",
        "machine_chest_press",
        "dumbbell_fly",
    ],
    "Quadriceps": [
        "barbell_back_squat",
        "leg_press",
        "dumbbell_squat",
        "dumbbell_lunge",
        "dumbbell_step_up",
        "bulgarian_split_squat",
        "reverse_lunge",
        "romanian_deadlift",
        "conventional_deadlift",
    ],
    "Hamstrings": [
        "leg_curl",
        "romanian_deadlift",
        "conventional_deadlift",
        "stiff_leg_deadlift",
        "good_morning",
        "seated_good_morning",
        "single_leg_rdl",
        "cable_pull_through",
        "sumo_deadlift",
    ],
    "Gluteus Maximus": [
        "hip_thrust",
        "barbell_glute_bridge",
        "b_stance_hip_thrust",
        "romanian_deadlift",
        "conventional_deadlift",
        "sumo_deadlift",
        "barbell_back_squat",
        "bulgarian_split_squat",
        "dumbbell_squat",
        "dumbbell_lunge",
        "reverse_lunge",
        "dumbbell_step_up",
        "cable_pull_through",
        "cable_kickback",
        "machine_hip_abduction",
    ],
    "Glutes": [
        "hip_thrust",
        "barbell_glute_bridge",
        "b_stance_hip_thrust",
        "romanian_deadlift",
        "conventional_deadlift",
        "sumo_deadlift",
        "barbell_back_squat",
        "bulgarian_split_squat",
        "dumbbell_squat",
        "dumbbell_lunge",
        "reverse_lunge",
        "dumbbell_step_up",
        "cable_pull_through",
        "cable_kickback",
        "machine_hip_abduction",
    ],
    "Hip-Adductors": [],
    "Latissimus Dorsi": [
        "weighted_pullups",
        "bodyweight_pullups",
        "bodyweight_chinups",
        "barbell_row",
        "machine_row",
    ],
    "Latissimus-Dorsi": [
        "weighted_pullups",
        "bodyweight_pullups",
        "bodyweight_chinups",
        "barbell_row",
        "machine_row",
    ],
    "Upper Back": ["barbell_row", "machine_row", "weighted_pullups"],
    "Mid/Upper Back": ["barbell_row", "machine_row", "weighted_pullups"],
    "Middle-Traps": ["barbell_row", "machine_row"],
    "Trapezius": ["barbell_shrugs", "barbell_row"],
    "Lower Back": [
        "romanian_deadlift",
        "conventional_deadlift",
        "sumo_deadlift",
        "back_extension",
        "loaded_back_extension",
        "reverse_hyperextension",
        "good_morning",
        "seated_good_morning",
        "jefferson_curl",
    ],
    "Front-Shoulder": [
        "military_press",
        "dumbbell_shoulder_press",
        "arnold_press",
        "machine_shoulder_press",
        "barbell_bench_press",
    ],
    "Anterior Delts": [
        "military_press",
        "dumbbell_shoulder_press",
        "arnold_press",
        "machine_shoulder_press",
        "barbell_bench_press",
    ],
    "Middle-Shoulder": ["dumbbell_lateral_raise", "military_press"],
    "Medial Delts": ["dumbbell_lateral_raise", "military_press"],
    "Rear-Shoulder": ["face_pulls", "barbell_row"],
    "Rear Delts": ["face_pulls", "barbell_row"],
    "Biceps": [
        "barbell_bicep_curl",
        "dumbbell_curl",
        "preacher_curl",
        "incline_dumbbell_curl",
    ],
    "Triceps": [
        "triceps_extension",
        "skull_crusher",
        "jm_press",
        "weighted_dips",
        "barbell_bench_press",
    ],
    "Calves": [
        "standing_calf_raise",
        "seated_calf_raise",
        "leg_press_calf_raise",
        "smith_machine_calf_raise",
        "single_leg_standing_calf_raise",
        "donkey_calf_raise",
    ],
    "Forearms": [],
    "Rectus Abdominis": ["cable_crunch", "machine_crunch", "weighted_crunch"],
    "Abs/Core": ["cable_crunch", "machine_crunch", "weighted_crunch"],
    "Neck": [],
    "External Obliques": ["cable_woodchop", "side_bend"],
    "Obliques": ["cable_woodchop", "side_bend"],
}


def _default(reason: str, *, is_dumbbell: bool = False) -> dict[str, Any]:
    return {
        **DEFAULT_ESTIMATE,
        "reason": reason,
        "is_dumbbell": is_dumbbell,
        "trace": _build_default_trace(reason),
    }


def _format_experience_label(tier: str, years: Optional[float]) -> str:
    """Render an experience tier as `intermediate (3 yrs)` for trace copy."""
    if years is None:
        return tier
    try:
        return f"{tier} ({float(years):g} yrs)"
    except (TypeError, ValueError):
        return tier


def _format_rounding_label(equipment: Optional[str]) -> str:
    eq = normalize_equipment(equipment)
    if eq in {"Barbell", "Trapbar", "Smith_Machine", "Plate"}:
        return "barbell (1.25 kg increments)"
    if eq == "Dumbbells":
        return "dumbbell (per-hand, 0.5–1.0 kg increments)"
    if eq in {"Cables", "Machine", "Kettlebells", "Medicine_Ball"}:
        return "machine (1.0 kg increments)"
    if eq == "Bodyweight":
        return "bodyweight (no added load)"
    return "default (1.0 kg increments)"


def _build_default_trace(reason: str) -> dict[str, Any]:
    if reason == "default_excluded":
        return {
            "source": "default",
            "steps": [
                {
                    "label": "Equipment is not modelled by the estimator",
                    "detail": "TRX / BOSU / Cardio / Recovery / Yoga / Stretches / Bands are intentionally skipped.",
                },
                {
                    "label": "Default values used",
                    "detail": "Adjust the Workout Controls manually for this exercise.",
                },
            ],
        }
    if reason == "default_missing":
        return {
            "source": "default",
            "steps": [
                {
                    "label": "Exercise not found",
                    "detail": "No matching row in the exercise catalogue — defaults shown.",
                },
            ],
        }
    return {
        "source": "default",
        "steps": [
            {
                "label": "No reference data available",
                "detail": "No saved reference lift, no demographics, and no logged set yet for this exercise.",
            },
        ],
        "improvement_hint": {
            "action": "enter_reference_lift",
            "lift_key": None,
            "copy": (
                "Fill in your Demographics or any Reference Lift on the Profile "
                "page to start personalising this suggestion."
            ),
        },
    }


def _build_log_trace(
    *, weight: float, reps_low: int, reps_high: int
) -> dict[str, Any]:
    if reps_low == reps_high:
        rep_label = f"{reps_low}"
    else:
        rep_label = f"{reps_low}–{reps_high}"
    return {
        "source": "log",
        "steps": [
            {
                "label": "Most recent logged set wins",
                "value": f"{weight:g} kg × {rep_label}",
                "detail": (
                    "Suggestion mirrors what you actually performed last time you "
                    "logged this exercise — measured data overrides reference-lift "
                    "and cold-start estimates."
                ),
            },
        ],
    }


def _build_profile_trace(
    *,
    lift_key: str,
    reference_weight: float,
    reference_reps: int,
    is_cross: bool,
    reference_1rm: float,
    reference_tier: Tier,
    target_tier: Tier,
    tier_multiplier: float,
    cross_factor: float,
    preset_key: str,
    preset: dict[str, Any],
    target_1rm: float,
    pre_round_weight: float,
    working_weight: float,
    equipment: Optional[str],
    target_exercise_name: str,
    target_primary_muscle: Optional[str],
) -> dict[str, Any]:
    label_friendly = KEY_LIFT_LABELS.get(lift_key, lift_key)
    pct = preset["pct_1rm"]

    detail_for_reference = (
        "Cross-muscle fallback — the target exercise isn't a direct match "
        "for any of your saved reference lifts."
        if is_cross
        else "Direct match — this is the questionnaire entry that maps to the target exercise."
    )

    steps: list[dict[str, Any]] = [
        {
            "label": "Reference lift",
            "value": f"{label_friendly} {reference_weight:g} kg × {reference_reps:g}",
            "detail": detail_for_reference,
        },
        {
            "label": "Estimated 1RM (Epley)",
            "value": round(reference_1rm, 1),
            "unit": "kg",
            "detail": f"Epley({reference_weight:g}, {reference_reps:g}) ≈ {round(reference_1rm, 1)} kg",
        },
        {
            "label": f"Tier scaling: {reference_tier} → {target_tier}",
            "factor": round(tier_multiplier, 2),
        },
    ]

    if is_cross:
        steps.append({
            "label": "Cross-muscle factor",
            "factor": round(cross_factor, 2),
            "detail": "Applied because the target exercise isn't a direct match for the reference lift.",
        })

    steps.append({
        "label": f"Preset: {preset_key.capitalize()}",
        "factor": round(pct, 2),
        "detail": (
            f"RIR {preset['rir']}, RPE {preset['rpe']}, "
            f"{preset['min_rep']}–{preset['max_rep']} reps "
            f"@ {pct} of 1RM."
        ),
    })

    steps.append({
        "label": "Working weight",
        "value": working_weight,
        "unit": "kg",
        "detail": f"≈ {round(pre_round_weight, 2)} kg before rounding",
    })
    steps.append({
        "label": "Rounding",
        "value": _format_rounding_label(equipment),
    })

    trace: dict[str, Any] = {"source": "profile", "steps": steps}

    if is_cross:
        direct_slug = _match_direct_lift_key(target_exercise_name)
        if direct_slug and direct_slug in KEY_LIFT_LABELS:
            trace["improvement_hint"] = {
                "action": "enter_reference_lift",
                "lift_key": direct_slug,
                "copy": (
                    f"Enter {KEY_LIFT_LABELS[direct_slug]} directly in your "
                    "Reference Lifts to skip the cross-muscle factor."
                ),
            }
        else:
            chain = MUSCLE_TO_KEY_LIFT.get(target_primary_muscle or "", [])
            chain_first = chain[0] if chain else None
            if chain_first and chain_first in KEY_LIFT_LABELS:
                trace["improvement_hint"] = {
                    "action": "enter_reference_lift",
                    "lift_key": chain_first,
                    "copy": (
                        "Add a reference lift for this muscle group "
                        f"(e.g. {KEY_LIFT_LABELS[chain_first]}) to refine this suggestion."
                    ),
                }

    return trace


def _build_profile_bodyweight_trace(
    *,
    lift_key: str,
    reference_reps: int,
    is_cross: bool,
    preset_key: str,
    preset: dict[str, Any],
    target_exercise_name: str,
    target_primary_muscle: Optional[str],
) -> dict[str, Any]:
    label_friendly = KEY_LIFT_LABELS.get(lift_key, lift_key)
    detail = (
        "Cross-muscle bodyweight fallback — copying your saved rep count."
        if is_cross
        else "Bodyweight reference — copying the rep count from your questionnaire entry."
    )
    steps: list[dict[str, Any]] = [
        {
            "label": "Reference lift",
            "value": f"{label_friendly}: {reference_reps:g} reps (bodyweight)",
            "detail": detail,
        },
        {
            "label": f"Preset: {preset_key.capitalize()}",
            "factor": round(preset["pct_1rm"], 2),
            "detail": f"RIR {preset['rir']}, RPE {preset['rpe']} (rep count copied from your reference set).",
        },
        {
            "label": "Working weight",
            "value": 0.0,
            "unit": "kg",
            "detail": "Bodyweight movement — no added load.",
        },
    ]
    trace: dict[str, Any] = {"source": "profile", "steps": steps}
    if is_cross:
        direct_slug = _match_direct_lift_key(target_exercise_name)
        if direct_slug and direct_slug in KEY_LIFT_LABELS:
            trace["improvement_hint"] = {
                "action": "enter_reference_lift",
                "lift_key": direct_slug,
                "copy": (
                    f"Enter {KEY_LIFT_LABELS[direct_slug]} directly in your "
                    "Reference Lifts to skip the cross-muscle factor."
                ),
            }
    return trace


def _build_cold_start_trace(
    *,
    target_exercise_name: str,
    target_tier: Tier,
    target_primary_muscle: str,
    base_1rm: float,
    bodyweight: float,
    gender: str,
    ratio: float,
    experience_tier: str,
    experience_years: Optional[float],
    experience_multiplier: float,
    tier_multiplier: float,
    target_1rm: float,
    preset: dict[str, Any],
    pre_round_weight: float,
    working_weight: float,
    equipment: Optional[str],
) -> dict[str, Any]:
    gender_label = "male" if gender == "M" else "female"
    pct = preset["pct_1rm"]
    muscle_label = (target_primary_muscle or "").lower() or "muscle"

    steps: list[dict[str, Any]] = [
        {
            "label": "No reference lift saved for this muscle",
            "detail": "Falling back to a population estimate from your demographics.",
        },
        {
            "label": f"Bodyweight ratio ({muscle_label} × {gender_label})",
            "factor": round(ratio, 2),
        },
        {
            "label": "Bodyweight",
            "value": bodyweight,
            "unit": "kg",
        },
        {
            "label": "Experience tier",
            "value": _format_experience_label(experience_tier, experience_years),
            "factor": round(experience_multiplier, 2),
            "detail": "Height, age, and BMI are intentionally not used (see Issue #16).",
        },
        {
            "label": "Cold-start 1RM",
            "value": round(base_1rm, 1),
            "unit": "kg",
            "detail": f"{round(ratio, 2)} × {bodyweight:g} kg × {round(experience_multiplier, 2)}",
        },
        {
            "label": f"Tier scaling: complex → {target_tier}",
            "factor": round(tier_multiplier, 2),
        },
        {
            "label": "Preset: Light (forced for cold-start safety)",
            "factor": round(pct, 2),
            "detail": (
                f"RIR {preset['rir']}, RPE {preset['rpe']}, "
                f"{preset['min_rep']}–{preset['max_rep']} reps @ {pct} of 1RM."
            ),
        },
        {
            "label": "Working weight",
            "value": working_weight,
            "unit": "kg",
            "detail": f"≈ {round(pre_round_weight, 2)} kg before rounding",
        },
        {
            "label": "Rounding",
            "value": _format_rounding_label(equipment),
        },
    ]

    trace: dict[str, Any] = {"source": "cold_start", "steps": steps}

    direct_slug = _match_direct_lift_key(target_exercise_name)
    canonical = COLD_START_CANONICAL_COMPOUND.get(target_primary_muscle)
    suggested = direct_slug if direct_slug in KEY_LIFT_LABELS else canonical
    if suggested and suggested in KEY_LIFT_LABELS:
        trace["improvement_hint"] = {
            "action": "enter_reference_lift",
            "lift_key": suggested,
            "copy": (
                f"Enter {KEY_LIFT_LABELS[suggested]} in your Reference Lifts. "
                "A measured 1RM replaces this population guess and unlocks "
                "Heavy/Moderate presets based on your actual strength."
            ),
        }
    return trace


def _normalize_for_matching(text: str) -> str:
    """Lowercase, replace hyphens with spaces, and strip a single trailing
    `s` from each word so that plural/hyphen variants ("Pull Ups", "Chin-Ups",
    "Hip Thrusts") collapse to the same canonical form as the allowlist
    keywords. Both the exercise name and each COMPLEX_ALLOWLIST keyword are
    normalised the same way at match time, so the allowlist stays the source
    of truth without needing an entry per variant.
    """
    if not text:
        return ""
    lowered = text.lower().replace("-", " ")
    words = []
    for word in lowered.split():
        if len(word) > 1 and word.endswith("s"):
            word = word[:-1]
        words.append(word)
    return " ".join(words)


_COMPLEX_ALLOWLIST_NORMALIZED: tuple[str, ...] = tuple(
    _normalize_for_matching(keyword) for keyword in COMPLEX_ALLOWLIST
)


def classify_tier(exercise_row: dict[str, Any]) -> Tier:
    equipment = normalize_equipment(exercise_row.get("equipment"))
    if equipment in EXCLUDED_EQUIPMENT:
        return "excluded"

    mechanic = str(exercise_row.get("mechanic") or "").strip().lower()
    movement_pattern = str(exercise_row.get("movement_pattern") or "").strip().lower()
    if mechanic == "isolation" or movement_pattern in {"upper_isolation", "lower_isolation"}:
        return "isolated"

    name = _normalize_for_matching(str(exercise_row.get("exercise_name") or ""))
    if any(keyword in name for keyword in _COMPLEX_ALLOWLIST_NORMALIZED):
        return "complex"

    return "accessory"


def epley_1rm(weight: float, reps: int) -> float:
    if reps <= 0 or weight <= 0:
        return 0.0
    capped_reps = min(reps, 12)
    return float(weight) * (1 + capped_reps / 30)


def round_weight(weight: float, equipment: Optional[str], tier: str) -> float:
    if weight <= 0:
        return 0.0

    normalized_equipment = normalize_equipment(equipment)
    if normalized_equipment == "Bodyweight":
        return 0.0

    if normalized_equipment in {"Barbell", "Trapbar", "Smith_Machine", "Plate"}:
        increment = 1.25
        floor = 20.0 if tier == "complex" else 1.25
    elif normalized_equipment == "Dumbbells":
        increment = 0.5 if weight < 10 else 1.0
        floor = 1.0
    elif normalized_equipment in {"Cables", "Machine", "Kettlebells", "Medicine_Ball"}:
        increment = 1.0
        floor = 1.0
    else:
        increment = 1.0
        floor = 1.0

    rounded = math.floor(weight / increment + 0.5) * increment
    return round(max(rounded, floor), 2)


def estimate_for_exercise(exercise_name: str, *, db: DatabaseHandler) -> dict[str, Any]:
    try:
        if not exercise_name or not exercise_name.strip():
            return _default("default_missing")

        exercise_row = db.fetch_one(
            """
            SELECT exercise_name, primary_muscle_group, equipment, mechanic, movement_pattern
            FROM exercises
            WHERE exercise_name = ? COLLATE NOCASE
            """,
            (exercise_name.strip(),),
        )
        if not exercise_row:
            return _default("default_missing")

        is_dumbbell = normalize_equipment(exercise_row.get("equipment")) == "Dumbbells"

        logged = _lookup_last_logged(exercise_row["exercise_name"], db)
        if logged:
            logged["is_dumbbell"] = is_dumbbell
            return logged

        profile_lifts = db.fetch_all(
            "SELECT lift_key, weight_kg, reps FROM user_profile_lifts"
        )
        preferences = db.fetch_all(
            "SELECT tier, rep_range FROM user_profile_preferences"
        )
        estimate = _estimate_from_profile(exercise_row, profile_lifts, preferences)
        if estimate:
            estimate["is_dumbbell"] = is_dumbbell
            return estimate

        demographics = db.fetch_one(
            "SELECT gender, weight_kg, experience_years FROM user_profile WHERE id = 1"
        )
        cold_start = _estimate_from_cold_start(exercise_row, demographics)
        if cold_start:
            cold_start["is_dumbbell"] = is_dumbbell
            return cold_start

        if classify_tier(exercise_row) == "excluded":
            return _default("default_excluded", is_dumbbell=is_dumbbell)
        return _default("default_no_reference", is_dumbbell=is_dumbbell)
    except Exception:
        logger.exception("Failed to estimate workout controls for %s", exercise_name)
        return _default("default_missing")


def _lookup_last_logged(exercise_name: str, db: DatabaseHandler) -> Optional[dict[str, Any]]:
    row = db.fetch_one(
        """
        SELECT
            COALESCE(scored_weight, planned_weight) AS weight,
            planned_sets AS sets,
            COALESCE(scored_min_reps, planned_min_reps) AS min_rep,
            COALESCE(scored_max_reps, planned_max_reps) AS max_rep,
            COALESCE(scored_rir, planned_rir) AS rir,
            COALESCE(scored_rpe, planned_rpe) AS rpe
        FROM workout_log
        WHERE exercise = ? COLLATE NOCASE
        ORDER BY id DESC
        LIMIT 1
        """,
        (exercise_name,),
    )
    if not row:
        return None

    default = DEFAULT_ESTIMATE
    weight = float(row["weight"] if row["weight"] is not None else default["weight"])
    min_rep = int(row["min_rep"] if row["min_rep"] is not None else default["min_rep"])
    max_rep = int(row["max_rep"] if row["max_rep"] is not None else default["max_rep"])
    return {
        "weight": weight,
        "sets": int(row["sets"] if row["sets"] is not None else default["sets"]),
        "min_rep": min_rep,
        "max_rep": max_rep,
        "rir": int(row["rir"] if row["rir"] is not None else default["rir"]),
        "rpe": float(row["rpe"] if row["rpe"] is not None else default["rpe"]),
        "source": "log",
        "reason": "log",
        "trace": _build_log_trace(
            weight=weight, reps_low=min_rep, reps_high=max_rep
        ),
    }


def _match_direct_lift_key(exercise_name: str) -> Optional[str]:
    """Return the key_lift slug that directly matches the given exercise name.

    Used to bypass the muscle-chain cross_factor penalty when the exercise
    being estimated is itself one of the questionnaire reference lifts
    (e.g. estimating "Barbell Romanian Deadlift" should use the user's
    `romanian_deadlift` reference directly, not fall through Hamstrings'
    leg_curl-first chain).
    """
    name = (exercise_name or "").lower()
    if not name:
        return None
    for keyword, lift_key in DIRECT_LIFT_MATCHERS:
        if keyword in name:
            return lift_key
    return None


def _estimate_from_profile(
    exercise_row: dict[str, Any],
    profile_lifts: list[dict[str, Any]],
    preferences: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    tier = classify_tier(exercise_row)
    if tier == "excluded":
        return None

    primary_muscle = normalize_muscle(exercise_row.get("primary_muscle_group"))
    lift_chain = MUSCLE_TO_KEY_LIFT.get(primary_muscle or "", [])

    direct_lift_key = _match_direct_lift_key(exercise_row.get("exercise_name", ""))

    candidates: list[tuple[str, bool]] = []
    if direct_lift_key:
        candidates.append((direct_lift_key, False))
    for index, lift_key in enumerate(lift_chain):
        if direct_lift_key and lift_key == direct_lift_key:
            continue
        candidates.append((lift_key, index > 0 or direct_lift_key is not None))

    if not candidates:
        return None

    lifts_by_key = {row.get("lift_key"): row for row in profile_lifts}
    preference_by_tier = {
        row.get("tier"): row.get("rep_range")
        for row in preferences
        if row.get("tier") and row.get("rep_range")
    }
    preset_key = preference_by_tier.get(tier, DEFAULT_PREFERENCES[tier])
    preset = REP_RANGE_PRESETS[preset_key]

    for lift_key, is_cross in candidates:
        lift = lifts_by_key.get(lift_key)
        if not lift:
            continue

        reps = int(lift.get("reps") or 0)
        weight = float(lift.get("weight_kg") or 0)
        is_bodyweight_reference = lift_key.startswith("bodyweight_") and weight == 0
        if reps <= 0 or (weight <= 0 and not is_bodyweight_reference):
            continue

        cross_factor = CROSS_FALLBACK_FACTOR if is_cross else 1.0
        reason = "profile_cross" if is_cross else "profile"

        if is_bodyweight_reference:
            copied_reps = max(reps, 1)
            return {
                "weight": 0.0,
                "sets": PROFILE_DEFAULT_SETS,
                "min_rep": copied_reps,
                "max_rep": copied_reps,
                "rir": preset["rir"],
                "rpe": preset["rpe"],
                "source": "profile",
                "reason": reason,
                "trace": _build_profile_bodyweight_trace(
                    lift_key=lift_key,
                    reference_reps=copied_reps,
                    is_cross=is_cross,
                    preset_key=preset_key,
                    preset=preset,
                    target_exercise_name=exercise_row.get("exercise_name", ""),
                    target_primary_muscle=primary_muscle,
                ),
            }

        reference_1rm = epley_1rm(weight, reps)
        if reference_1rm <= 0:
            continue

        reference_tier = KEY_LIFT_TIER.get(lift_key, "complex")
        tier_multiplier = min(
            TIER_RATIOS[tier] / TIER_RATIOS[reference_tier],
            1.0,
        )
        target_1rm = reference_1rm * tier_multiplier * cross_factor
        pre_round_weight = target_1rm * preset["pct_1rm"]
        working_weight = round_weight(
            pre_round_weight,
            exercise_row.get("equipment"),
            tier,
        )
        return {
            "weight": working_weight,
            "sets": PROFILE_DEFAULT_SETS,
            "min_rep": preset["min_rep"],
            "max_rep": preset["max_rep"],
            "rir": preset["rir"],
            "rpe": preset["rpe"],
            "source": "profile",
            "reason": reason,
            "trace": _build_profile_trace(
                lift_key=lift_key,
                reference_weight=weight,
                reference_reps=reps,
                is_cross=is_cross,
                reference_1rm=reference_1rm,
                reference_tier=reference_tier,
                target_tier=tier,
                tier_multiplier=tier_multiplier,
                cross_factor=cross_factor,
                preset_key=preset_key,
                preset=preset,
                target_1rm=target_1rm,
                pre_round_weight=pre_round_weight,
                working_weight=working_weight,
                equipment=exercise_row.get("equipment"),
                target_exercise_name=exercise_row.get("exercise_name", ""),
                target_primary_muscle=primary_muscle,
            ),
        }

    return None


def _classify_experience_tier(experience_years: Optional[float]) -> str:
    """Map raw experience years into the cold-start strength tier."""
    if experience_years is None:
        return "novice"
    try:
        years = float(experience_years)
    except (TypeError, ValueError):
        return "novice"
    if years < 0:
        return "novice"
    for label, upper in EXPERIENCE_TIER_BOUNDS:
        if years <= upper:
            return label
    return "advanced"


def cold_start_1rm(
    exercise_row: dict[str, Any],
    demographics: Optional[dict[str, Any]],
) -> Optional[float]:
    """Population-table 1RM seed for an exercise from demographics alone.

    Issue #16: fires only as a last-resort fallback when the user has filled
    Demographics but no reference lifts. Returns ``None`` if essential
    demographics are missing, the equipment can't be modelled (Dumbbells /
    Bodyweight / Trx etc.), or the primary muscle has no entry in
    :data:`COLD_START_RATIOS`. The chain in
    :func:`_estimate_from_cold_start` then applies the existing tier ratio
    so accessory / isolation targets are scaled down from the
    complex-tier seed.
    """
    if not demographics:
        return None

    gender = demographics.get("gender")
    if gender not in {"M", "F"}:
        return None

    weight_kg = demographics.get("weight_kg")
    try:
        bodyweight = float(weight_kg) if weight_kg is not None else 0.0
    except (TypeError, ValueError):
        return None
    if bodyweight <= 0:
        return None

    equipment = normalize_equipment(exercise_row.get("equipment"))
    if equipment in EXCLUDED_EQUIPMENT or equipment in {"Dumbbells", "Bodyweight"}:
        return None

    primary_muscle = normalize_muscle(exercise_row.get("primary_muscle_group"))
    if not primary_muscle:
        return None

    ratio = COLD_START_RATIOS.get((primary_muscle, gender))
    if ratio is None:
        return None

    tier = _classify_experience_tier(demographics.get("experience_years"))
    multiplier = EXPERIENCE_MULTIPLIERS[tier]

    return bodyweight * ratio * multiplier


def _estimate_from_cold_start(
    exercise_row: dict[str, Any],
    demographics: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Wrap :func:`cold_start_1rm` into the standard estimate response shape.

    Forces the Light preset so the seeded suggestion errs toward
    under-prescription, since the user has no measured data yet.
    """
    target_tier = classify_tier(exercise_row)
    if target_tier == "excluded":
        return None

    base_1rm = cold_start_1rm(exercise_row, demographics)
    if base_1rm is None or base_1rm <= 0:
        return None

    tier_multiplier = TIER_RATIOS[target_tier] / TIER_RATIOS["complex"]
    preset = REP_RANGE_PRESETS[COLD_START_PRESET]
    target_1rm = base_1rm * tier_multiplier
    pre_round_weight = target_1rm * preset["pct_1rm"]
    working_weight = round_weight(
        pre_round_weight,
        exercise_row.get("equipment"),
        target_tier,
    )

    primary_muscle = normalize_muscle(exercise_row.get("primary_muscle_group")) or ""
    gender = (demographics or {}).get("gender") or ""
    bodyweight = float((demographics or {}).get("weight_kg") or 0)
    experience_years = (demographics or {}).get("experience_years")
    experience_tier = _classify_experience_tier(experience_years)
    experience_multiplier = EXPERIENCE_MULTIPLIERS[experience_tier]
    ratio = COLD_START_RATIOS.get((primary_muscle, gender), 0.0)

    return {
        "weight": working_weight,
        "sets": PROFILE_DEFAULT_SETS,
        "min_rep": preset["min_rep"],
        "max_rep": preset["max_rep"],
        "rir": preset["rir"],
        "rpe": preset["rpe"],
        "source": "cold_start",
        "reason": "profile_cold_start",
        "trace": _build_cold_start_trace(
            target_exercise_name=exercise_row.get("exercise_name", ""),
            target_tier=target_tier,
            target_primary_muscle=primary_muscle,
            base_1rm=base_1rm,
            bodyweight=bodyweight,
            gender=gender,
            ratio=ratio,
            experience_tier=experience_tier,
            experience_years=experience_years,
            experience_multiplier=experience_multiplier,
            tier_multiplier=tier_multiplier,
            target_1rm=target_1rm,
            preset=preset,
            pre_round_weight=pre_round_weight,
            working_weight=working_weight,
            equipment=exercise_row.get("equipment"),
        ),
    }


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


# Issue #18 — "How the system sees you" card: stats tiles + cohort bars +
# coverage donut. The estimator stays the single source of truth. Cohort
# ranges are static reference brackets that contextualise the user's
# demographics; they do NOT alter any suggestion math (matching the
# "informational only" invariant). Height + age are exposed as tiles so the
# user can see what's collected, but flagged `used=False` because they do
# not (yet) feed into `cold_start_1rm` or any other estimator branch.
COHORT_BODYWEIGHT_KG: dict[str, tuple[float, float]] = {
    "M": (70.0, 90.0),
    "F": (55.0, 75.0),
}
COHORT_HEIGHT_CM: dict[str, tuple[float, float]] = {
    "M": (170.0, 188.0),
    "F": (158.0, 175.0),
}
COHORT_AGE_YEARS: tuple[float, float] = (25.0, 45.0)

EXPERIENCE_TIER_ORDER: tuple[str, ...] = ("novice", "intermediate", "advanced")

# When the user is already at the top tier, the cohort upper for the bar
# chart extrapolates one additional notch using the same step ratio
# advanced :: intermediate, so the user marker still sits inside the bar.
ADVANCED_COHORT_REACH = 1.2


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _format_kg(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:g} kg"


def _format_cm(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:g} cm"


def _format_years(value: Optional[float]) -> str:
    if value is None:
        return "—"
    if float(value).is_integer():
        return f"{int(value)} yrs"
    return f"{value:g} yrs"


def _gender_label(gender: Optional[str]) -> Optional[str]:
    if gender == "M":
        return "Male"
    if gender == "F":
        return "Female"
    return None


def _next_tier_multiplier(tier: str) -> float:
    """Return the multiplier for the tier above ``tier``. For advanced, an
    extrapolated 'elite reach' multiplier keeps the bar chart's right anchor
    above the user's marker without introducing a new tier in the table."""
    if tier in EXPERIENCE_TIER_ORDER:
        idx = EXPERIENCE_TIER_ORDER.index(tier)
        if idx < len(EXPERIENCE_TIER_ORDER) - 1:
            return EXPERIENCE_MULTIPLIERS[EXPERIENCE_TIER_ORDER[idx + 1]]
    return EXPERIENCE_MULTIPLIERS["advanced"] * ADVANCED_COHORT_REACH


def cohort_ranges(
    demographics: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Static reference cohort buckets keyed off the user's demographics.

    Returns four tiles (bodyweight, height, age, experience) plus the
    classifier metadata (tier, multiplier, next-tier multiplier) used by
    the cohort bar chart. The helper is **read-only** — it never mutates
    or drives the estimator output. Tiles for inputs the estimator does
    NOT yet consume (height, age) are flagged ``used=False`` so the UI
    can de-emphasise them and explain why the value is collected but
    not yet load-bearing.
    """
    demos = demographics or {}
    raw_gender = demos.get("gender") if demos.get("gender") in {"M", "F"} else None
    bodyweight = _coerce_float(demos.get("weight_kg"))
    height = _coerce_float(demos.get("height_cm"))
    age = _coerce_float(demos.get("age"))
    experience_years = _coerce_float(demos.get("experience_years"))

    tier = (
        _classify_experience_tier(experience_years)
        if experience_years is not None
        else None
    )
    tier_multiplier = (
        EXPERIENCE_MULTIPLIERS[tier] if tier else None
    )
    next_tier = (
        EXPERIENCE_TIER_ORDER[
            min(
                EXPERIENCE_TIER_ORDER.index(tier) + 1,
                len(EXPERIENCE_TIER_ORDER) - 1,
            )
        ]
        if tier
        else None
    )
    next_tier_multiplier = _next_tier_multiplier(tier) if tier else None

    bodyweight_low, bodyweight_high = (
        COHORT_BODYWEIGHT_KG[raw_gender] if raw_gender else (None, None)
    )
    height_low, height_high = (
        COHORT_HEIGHT_CM[raw_gender] if raw_gender else (None, None)
    )
    age_low, age_high = COHORT_AGE_YEARS

    bodyweight_tile = {
        "value_text": _format_kg(bodyweight),
        "value_raw": bodyweight,
        "cohort_text": (
            f"Cohort: {bodyweight_low:g}–{bodyweight_high:g} kg"
            f" ({_gender_label(raw_gender).lower()} {tier})"
            if raw_gender and bodyweight_low is not None and tier
            else f"Cohort: {bodyweight_low:g}–{bodyweight_high:g} kg ({_gender_label(raw_gender).lower()})"
            if raw_gender and bodyweight_low is not None
            else "Cohort range needs gender"
        ),
        "cohort_low": bodyweight_low,
        "cohort_high": bodyweight_high,
        "empty": bodyweight is None,
        "empty_text": "Add bodyweight to enable",
        "used": True,
    }
    height_tile = {
        "value_text": _format_cm(height),
        "value_raw": height,
        "cohort_text": (
            f"Cohort: {height_low:g}–{height_high:g} cm ({_gender_label(raw_gender).lower()})"
            if raw_gender and height_low is not None
            else "Cohort range needs gender"
        ),
        "cohort_low": height_low,
        "cohort_high": height_high,
        "empty": height is None,
        "empty_text": "Add height (currently unused — flagged for future use)",
        "used": False,
        "unused_reason": "Currently unused (collected, not in formula)",
    }
    age_tile = {
        "value_text": _format_years(age),
        "value_raw": age,
        "cohort_text": f"Cohort: {age_low:g}–{age_high:g} yrs",
        "cohort_low": age_low,
        "cohort_high": age_high,
        "empty": age is None,
        "empty_text": "Add age (currently unused)",
        "used": False,
        "unused_reason": "Currently unused (collected, not in formula)",
    }
    experience_tile = {
        "value_text": tier.title() if tier else "—",
        "value_raw": experience_years,
        "years_text": _format_years(experience_years) if experience_years is not None else None,
        "cohort_text": (
            f"Tier multiplier: ×{tier_multiplier:.2f} of trained max"
            if tier_multiplier is not None
            else "Tier multiplier: —"
        ),
        "tier": tier,
        "tier_multiplier": tier_multiplier,
        "empty": tier is None,
        "empty_text": "Pick a level to enable cold-start estimates",
        "used": True,
    }

    summary = _build_cohort_summary(
        gender_label=_gender_label(raw_gender),
        age_low=age_low,
        age_high=age_high,
        bodyweight_tile=bodyweight_tile,
        experience_tile=experience_tile,
    )

    return {
        "tier": tier,
        "tier_multiplier": tier_multiplier,
        "next_tier": next_tier,
        "next_tier_multiplier": next_tier_multiplier,
        "tiles": {
            "bodyweight": bodyweight_tile,
            "height": height_tile,
            "age": age_tile,
            "experience": experience_tile,
        },
        "summary": summary,
    }


def _build_cohort_summary(
    *,
    gender_label: Optional[str],
    age_low: float,
    age_high: float,
    bodyweight_tile: dict[str, Any],
    experience_tile: dict[str, Any],
) -> str:
    """One-line plain-language summary of the cohort the estimator is
    calibrated to. Empty fields render as ``"unknown"`` so the user can
    see what's missing at a glance."""
    gender_text = gender_label.lower() if gender_label else "unknown gender"
    age_text = f"age {age_low:g}–{age_high:g}"
    bw_low = bodyweight_tile.get("cohort_low")
    bw_high = bodyweight_tile.get("cohort_high")
    bodyweight_text = (
        f"bodyweight {bw_low:g}–{bw_high:g} kg"
        if bw_low is not None and bw_high is not None
        else "bodyweight unknown"
    )
    tier = experience_tile.get("tier")
    years_text = experience_tile.get("years_text")
    experience_text = (
        f"{tier} ({years_text} trained)"
        if tier and years_text
        else "experience level unknown"
    )

    missing = (not gender_label) or experience_text == "experience level unknown"
    parts = [gender_text, age_text, bodyweight_text, experience_text]
    body = ", ".join(parts)
    if missing:
        return f"Estimator cohort: {body} — fill these to calibrate."
    return (
        f"Estimator cohort: {body}. "
        "Suggestions are calibrated to lifters in this bucket."
    )


def cohort_bars(
    profile_lifts: list[dict[str, Any]],
    demographics: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One bar-chart row per filled canonical-compound reference lift.

    Each row carries the user's Epley-derived 1RM, the cold-start anchor
    1RM the estimator would otherwise have used, and a cohort upper
    bound (one tier up). Bodyweight slugs are skipped — there's no
    meaningful kg comparison. Rows where the cold-start anchor cannot be
    computed (incomplete demographics, muscle outside `COLD_START_RATIOS`)
    are skipped: the bar chart only renders when the comparison is
    well-defined.
    """
    demos = demographics or {}
    if demos.get("gender") not in {"M", "F"} or _coerce_float(demos.get("weight_kg")) is None:
        return []

    tier = _classify_experience_tier(demos.get("experience_years"))
    current_multiplier = EXPERIENCE_MULTIPLIERS[tier]
    next_multiplier = _next_tier_multiplier(tier)

    lifts_by_key = {
        row.get("lift_key"): row
        for row in profile_lifts
        if isinstance(row.get("lift_key"), str)
    }

    out: list[dict[str, Any]] = []
    for muscle, slug in COLD_START_CANONICAL_COMPOUND.items():
        if slug.startswith("bodyweight_"):
            continue
        lift = lifts_by_key.get(slug)
        if not _is_lift_filled(lift):
            continue
        weight = float(lift.get("weight_kg") or 0)
        reps = int(lift.get("reps") or 0)
        if weight <= 0 or reps <= 0:
            continue

        cold_start = cold_start_1rm(
            {"primary_muscle_group": muscle, "equipment": "Barbell"},
            demos,
        )
        if cold_start is None or cold_start <= 0:
            continue

        user_1rm = epley_1rm(weight, reps)
        cohort_upper = cold_start * (next_multiplier / current_multiplier)
        max_kg = max(cold_start, user_1rm, cohort_upper) * 1.05
        min_kg = 0.0

        out.append(
            {
                "lift_key": slug,
                "label": KEY_LIFT_LABELS.get(slug, slug),
                "muscle": muscle,
                "user_1rm_kg": round(user_1rm, 1),
                "cold_start_1rm_kg": round(cold_start, 1),
                "cohort_upper_kg": round(cohort_upper, 1),
                "max_kg": round(max_kg, 1),
                "min_kg": min_kg,
            }
        )
    return out


def coverage_donut(
    profile_lifts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compact circular-progress payload for the "How the system sees you"
    card. Mirrors `accuracy_band()` counts but in donut shape so the same
    metric reads more glanceably."""
    filled = filled_lift_keys(profile_lifts)
    filled_count = len(filled)
    total_count = len(KEY_LIFTS)
    pct = (filled_count / total_count) if total_count > 0 else 0.0
    return {
        "filled_count": filled_count,
        "total_count": total_count,
        "percent": round(pct * 100, 1),
    }


# Issue #19 — bodymap coverage view.
#
# Each backend muscle key drives one or more polygons on the
# react-body-highlighter SVG (anterior + posterior). Polygons not in this
# table render as "not_assessed" and the coverage helper does not emit a
# state for them — the view layer renders them as a dim outline.
#
# KEEP THIS LIST IN SYNC with `BODYMAP_COVERAGE_MUSCLES` /
# `COVERAGE_MUSCLE_CHAIN` in `static/js/modules/bodymap-svg.js`. The
# `test_bodymap_canonical_in_sync` test enforces drift detection.
BODYMAP_MUSCLE_KEYS: tuple[str, ...] = (
    "Chest",
    "Front-Shoulder",
    "Biceps",
    "Triceps",
    "Abs/Core",
    "Obliques",
    "Quadriceps",
    "Calves",
    "Trapezius",
    "Rear-Shoulder",
    "Upper Back",
    "Lower Back",
    "Gluteus Maximus",
    "Hamstrings",
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
