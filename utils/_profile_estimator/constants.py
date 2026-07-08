"""Cluster 1 — constants & lookup tables for the profile estimator.

Pure data extracted from :mod:`utils.profile_estimator` (WP2.1b, Deep Refactor
Plan v3 Phase 2). See ``docs/user_profile/PROFILE_ESTIMATOR_CLUSTERS.md`` §2.

These names are re-exported by the :mod:`utils.profile_estimator` facade; import
them from there, not from this internal module. The ``lift_matching`` re-exports
below preserve object identity (they are the same objects exposed by
:mod:`utils.lift_matching`), which the estimator import-contract test asserts in
both import orders. This module takes no ``strength_calibration`` import — the
``profile_estimator ⇄ strength_calibration`` cycle is held only by the two
function-local lazy imports in the orchestration core, which stay in the facade.
"""
from __future__ import annotations

from typing import Literal

from utils.lift_matching import DIRECT_LIFT_MATCHERS  # noqa: F401
from utils.lift_matching import match_direct_lift_key as match_direct_lift_key  # noqa: F401

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

# Backward-compatible private alias used by internal callers (trace builders,
# estimator chain). New code should use ``match_direct_lift_key`` directly.
_match_direct_lift_key = match_direct_lift_key

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

# Issue #19 — bodymap coverage view.
#
# Each backend muscle key drives one or more polygons on the workout-cool SVG
# (anterior + posterior). Polygons without a coverage chain render as
# "not_assessed" and the coverage helper does not emit a state for them — the
# view layer renders them as a dim outline.
#
# KEEP THIS LIST IN SYNC with `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES` /
# `COVERAGE_MUSCLE_CHAIN` in `static/js/modules/bodymap-svg.js`. The
# `test_workout_cool_back_region_multi_key_mapping_matches_python_keys` and
# related bodymap tests enforce drift detection.
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
