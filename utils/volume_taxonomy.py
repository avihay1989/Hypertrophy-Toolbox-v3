"""Volume progress muscle taxonomy.

This module is the Phase 0 source of truth for Plan <-> Distribute volume
taxonomy decisions. It is intentionally pure: no route imports and no DB access.

Phase 0 records the execution-plan recommended/default decisions confirmed by
the user before Phase 1 implementation.
"""
from __future__ import annotations

import re


# Decision (Phase 0 §5.2): add Middle-Shoulder to Basic rather than rolling it
# into anterior/posterior shoulder buckets.
# Decision (Phase 0 §5.2): add Hip-Adductors to Basic rather than rolling it
# into Glutes.
BASIC_MUSCLE_GROUPS: list[str] = [
    "Neck",
    "Front-Shoulder",
    "Middle-Shoulder",
    "Rear-Shoulder",
    "Biceps",
    "Triceps",
    "Chest",
    "Forearms",
    "Abdominals",
    "Quadriceps",
    "Hamstrings",
    "Calves",
    "Latissimus-Dorsi",
    "Glutes",
    "Hip-Adductors",
    "Lower Back",
    "Traps",
    "Middle-Traps",
]

ADVANCED_MUSCLE_GROUPS: list[str] = [
    # Deltoids & Trapezius
    "anterior-deltoid",
    "lateral-deltoid",
    "posterior-deltoid",
    "upper-trapezius",
    "traps-middle",
    "lower-trapezius",
    # Pectorals & Biceps/Triceps
    "upper-pectoralis",
    "mid-lower-pectoralis",
    "short-head-biceps",
    "long-head-biceps",
    "lateral-head-triceps",
    "long-head-triceps",
    "medial-head-triceps",
    # Forearms
    "wrist-extensors",
    "wrist-flexors",
    # Core
    "upper-abdominals",
    "lower-abdominals",
    "obliques",
    # Hips/Thigh
    "groin",
    "inner-thigh",
    "rectus-femoris",
    "inner-quadriceps",
    "outer-quadriceps",
    # Lower leg
    "soleus",
    "tibialis",
    "gastrocnemius",
    # Hamstrings & Glutes
    "medial-hamstrings",
    "lateral-hamstrings",
    "gluteus-maximus",
    "gluteus-medius",
    # Back (lats)
    "lats",
    # Spine extensors
    "lowerback",
]

# Decision (Phase 0 §5.2.1): default D-blank-pst strategy. Blank rows are still
# diagnostic rows; Phase 1 aggregation uses isolated tokens when available.
BLANK_PST_STRATEGY = "isolated_only"


COARSE_TO_BASIC: dict[str, str] = {
    "Abdominals": "Abdominals",
    "Abs/Core": "Abdominals",
    "Back": "Latissimus-Dorsi",
    "Biceps": "Biceps",
    "Calves": "Calves",
    "Chest": "Chest",
    "Core": "Abdominals",
    "Erectors": "Lower Back",
    "External Obliques": "Abdominals",
    "Forearms": "Forearms",
    "Front-Shoulder": "Front-Shoulder",
    "Gluteus Maximus": "Glutes",
    "Glutes": "Glutes",
    "Hamstrings": "Hamstrings",
    "Hip-Adductors": "Hip-Adductors",
    "Latissimus Dorsi": "Latissimus-Dorsi",
    "Latissimus-Dorsi": "Latissimus-Dorsi",
    "Lower Back": "Lower Back",
    "Middle-Shoulder": "Middle-Shoulder",
    "Middle-Traps": "Middle-Traps",
    "Neck": "Neck",
    "Quadriceps": "Quadriceps",
    "Rear-Shoulder": "Rear-Shoulder",
    "Rectus Abdominis": "Abdominals",
    # Decision (Phase 0 §5.2): rotator cuff rolls to Rear-Shoulder.
    "Rotator Cuff": "Rear-Shoulder",
    # Decision (Phase 0 §5.2): underspecified shoulders roll to Front-Shoulder.
    "Shoulders": "Front-Shoulder",
    "Traps": "Traps",
    # Decision (Phase 0 §5.2): Trapezius / Upper Traps roll to Traps.
    "Trapezius": "Traps",
    "Triceps": "Triceps",
    # Decision (Phase 0 §5.2): Upper Back rolls to Middle-Traps.
    "Upper Back": "Middle-Traps",
    "Upper Chest": "Chest",
    "Upper Traps": "Traps",
}

COARSE_TO_REPRESENTATIVE_ADVANCED: dict[str, str] = {
    "Abdominals": "upper-abdominals",
    "Abs/Core": "upper-abdominals",
    "Back": "lats",
    "Biceps": "long-head-biceps",
    "Calves": "gastrocnemius",
    "Chest": "mid-lower-pectoralis",
    "Core": "upper-abdominals",
    "Erectors": "lowerback",
    "External Obliques": "obliques",
    "Forearms": "wrist-flexors",
    "Front-Shoulder": "anterior-deltoid",
    "Gluteus Maximus": "gluteus-maximus",
    "Glutes": "gluteus-maximus",
    "Hamstrings": "medial-hamstrings",
    "Hip-Adductors": "inner-thigh",
    "Latissimus Dorsi": "lats",
    "Latissimus-Dorsi": "lats",
    "Lower Back": "lowerback",
    "Middle-Shoulder": "lateral-deltoid",
    "Middle-Traps": "traps-middle",
    # Neck has no dedicated advanced splitter today; upper-trapezius is only a
    # fallback target for coarse-role advanced aggregation.
    "Neck": "upper-trapezius",
    "Quadriceps": "rectus-femoris",
    "Rear-Shoulder": "posterior-deltoid",
    "Rectus Abdominis": "upper-abdominals",
    "Rotator Cuff": "posterior-deltoid",
    "Shoulders": "anterior-deltoid",
    "Traps": "upper-trapezius",
    "Trapezius": "upper-trapezius",
    "Triceps": "long-head-triceps",
    "Upper Back": "traps-middle",
    "Upper Chest": "upper-pectoralis",
    "Upper Traps": "upper-trapezius",
}

ADVANCED_TO_BASIC: dict[str, str] = {
    "anterior-deltoid": "Front-Shoulder",
    "lateral-deltoid": "Middle-Shoulder",
    "posterior-deltoid": "Rear-Shoulder",
    "upper-trapezius": "Traps",
    "traps-middle": "Middle-Traps",
    # Decision (Phase 0 §6.3): no Lower-Traps Basic bucket.
    "lower-trapezius": "Middle-Traps",
    "upper-pectoralis": "Chest",
    "mid-lower-pectoralis": "Chest",
    "short-head-biceps": "Biceps",
    "long-head-biceps": "Biceps",
    "lateral-head-triceps": "Triceps",
    "long-head-triceps": "Triceps",
    "medial-head-triceps": "Triceps",
    "wrist-extensors": "Forearms",
    "wrist-flexors": "Forearms",
    "upper-abdominals": "Abdominals",
    "lower-abdominals": "Abdominals",
    "obliques": "Abdominals",
    "groin": "Hip-Adductors",
    "inner-thigh": "Hip-Adductors",
    "rectus-femoris": "Quadriceps",
    "inner-quadriceps": "Quadriceps",
    "outer-quadriceps": "Quadriceps",
    "soleus": "Calves",
    "tibialis": "Calves",
    "gastrocnemius": "Calves",
    "medial-hamstrings": "Hamstrings",
    "lateral-hamstrings": "Hamstrings",
    "gluteus-maximus": "Glutes",
    "gluteus-medius": "Glutes",
    "lats": "Latissimus-Dorsi",
    "lowerback": "Lower Back",
}

DISTRIBUTED_UMBRELLA_TOKENS: dict[str, tuple[str, ...]] = {
    # Decision (Phase 0 §6.3): quadriceps umbrella distributes across all quad
    # splitter buckets rather than mapping to a single advanced key.
    "quadriceps": ("rectus-femoris", "inner-quadriceps", "outer-quadriceps"),
}

TOKEN_TO_ADVANCED: dict[str, str | None] = {
    "adductors": "inner-thigh",
    "anterior-deltoid": "anterior-deltoid",
    "back": "lats",
    "biceps-brachii": "long-head-biceps",
    "brachialis": "wrist-flexors",
    "brachioradialis": "wrist-flexors",
    "chest": "mid-lower-pectoralis",
    "erector-spinae": "lowerback",
    "gastrocnemius": "gastrocnemius",
    "general-back": "lats",
    "gluteus-maximus": "gluteus-maximus",
    "gluteus-medius": "gluteus-medius",
    "hamstrings": "medial-hamstrings",
    "hip-adductors": "inner-thigh",
    # Decision (Phase 0 §5.2): rotator-cuff tokens follow the Rear-Shoulder
    # rollup by using posterior-deltoid as the advanced representative.
    "infraspinatus": "posterior-deltoid",
    "subscapularis": "posterior-deltoid",
    "supraspinatus": "posterior-deltoid",
    "inner-quadricep": "inner-quadriceps",
    "inner-quadriceps": "inner-quadriceps",
    "inner-thigh": "inner-thigh",
    "lateral-deltoid": "lateral-deltoid",
    "lateral-hamstrings": "lateral-hamstrings",
    "lateral-head-triceps": "lateral-head-triceps",
    "latissimus-dorsi": "lats",
    "long-head-bicep": "long-head-biceps",
    "long-head-tricep": "long-head-triceps",
    "lower-abdominals": "lower-abdominals",
    "lower-traps": "lower-trapezius",
    "medial-hamstrings": "medial-hamstrings",
    "medial-head-triceps": "medial-head-triceps",
    "mid-and-lower-chest": "mid-lower-pectoralis",
    "middle-traps": "traps-middle",
    "obliques": "obliques",
    "outer-quadricep": "outer-quadriceps",
    "pectoralis-major-clavicular": "upper-pectoralis",
    "pectoralis-major-sternal-head": "mid-lower-pectoralis",
    "posterior-deltoid": "posterior-deltoid",
    "pronators": "wrist-flexors",
    "rear-delts": "posterior-deltoid",
    "rear-shoulder": "posterior-deltoid",
    "rectus-abdominis": "upper-abdominals",
    "rectus-femoris": "rectus-femoris",
    # Decision (Phase 0 §6.3): serratus stays represented by Chest /
    # mid-lower-pectoralis and does not add a splitter slider.
    "serratus-anterior": "mid-lower-pectoralis",
    "short-head-bicep": "short-head-biceps",
    "soleus": "soleus",
    "supinator": "wrist-extensors",
    "tfl": "gluteus-medius",
    "tibialis": "tibialis",
    "traps-(mid-back)": "traps-middle",
    "triceps-brachi": "long-head-triceps",
    "triceps-brachii": "long-head-triceps",
    "upper-abdominals": "upper-abdominals",
    "upper-pectoralis": "upper-pectoralis",
    "upper-trapezius": "upper-trapezius",
    "upper-traps": "upper-trapezius",
    "wrist-extensors": "wrist-extensors",
    "wrist-flexors": "wrist-flexors",
    # No dedicated advanced neck slider exists today.
    "splenius": None,
    "sternocleidomastoid": None,
}

IGNORED_TOKENS: frozenset[str] = frozenset(
    token for token, advanced in TOKEN_TO_ADVANCED.items() if advanced is None
)


_PST_ALIASES = {
    "front shoulder": "Front-Shoulder",
    "front-shoulder": "Front-Shoulder",
    "latissimus dorsi": "Latissimus Dorsi",
    "latissimus-dorsi": "Latissimus-Dorsi",
    "middle shoulder": "Middle-Shoulder",
    "middle-shoulder": "Middle-Shoulder",
    "middle traps": "Middle-Traps",
    "middle-traps": "Middle-Traps",
    "rear shoulder": "Rear-Shoulder",
    "rear-shoulder": "Rear-Shoulder",
}


def canonical_pst(value: str | None) -> str | None:
    """Normalize a raw P/S/T muscle_group value for dict lookup."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return _PST_ALIASES.get(stripped.lower(), stripped)


def normalize_isolated_token(token: str) -> str:
    """Normalize an isolated-muscle token for TOKEN_TO_ADVANCED lookup."""
    normalized = (token or "").strip().lower().replace("_", " ")
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")


def coarse_to_basic(coarse: str) -> str:
    """Return the Basic bucket for a coarse P/S/T value; raises on gaps."""
    key = canonical_pst(coarse)
    if key is None:
        raise KeyError(coarse)
    return COARSE_TO_BASIC[key]


def coarse_to_representative_advanced(coarse: str) -> str:
    """Return the Advanced representative for a coarse P/S/T value."""
    key = canonical_pst(coarse)
    if key is None:
        raise KeyError(coarse)
    return COARSE_TO_REPRESENTATIVE_ADVANCED[key]


def advanced_to_basic(advanced: str) -> str:
    """Return the Basic bucket for an Advanced splitter key."""
    return ADVANCED_TO_BASIC[advanced]


def expand_umbrella(token: str) -> tuple[str, ...] | None:
    """Return the advanced distribution tuple for an umbrella token."""
    return DISTRIBUTED_UMBRELLA_TOKENS.get(normalize_isolated_token(token))


def advanced_token_belongs_to_coarse(token: str, coarse: str) -> bool:
    """Return whether an isolated token maps to the same Basic bucket as coarse."""
    coarse_key = canonical_pst(coarse)
    if coarse_key is None or coarse_key not in COARSE_TO_BASIC:
        return False

    coarse_basic = COARSE_TO_BASIC[coarse_key]
    normalized = normalize_isolated_token(token)
    expanded = expand_umbrella(normalized)
    if expanded:
        return all(ADVANCED_TO_BASIC.get(advanced) == coarse_basic for advanced in expanded)

    advanced = TOKEN_TO_ADVANCED.get(normalized)
    if advanced is None:
        return False
    return ADVANCED_TO_BASIC.get(advanced) == coarse_basic
