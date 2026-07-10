"""Fatigue Meter — Phase 2 per-muscle channel (Stage 2).

Internal leaf of the ``utils.fatigue`` facade (WP2.4). Bodies moved verbatim from
the original ``utils/fatigue.py`` Phase 2 per-muscle section. Depends on the
Phase 1 core leaf for ``calculate_set_fatigue`` / ``_coerce_sets`` and on
``utils.volume_taxonomy`` for the canonical Basic-bucket mapping. Pure: no DB
access, no Flask imports.
"""
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from utils.logger import get_logger
from utils.volume_taxonomy import COARSE_TO_BASIC, canonical_pst

from utils._fatigue.core import _coerce_sets, calculate_set_fatigue

logger = get_logger()


# =============================================================================
# Phase 2 (per-muscle channel) — Stage 2
# =============================================================================
# Stage 2 ships a per-muscle local-fatigue accumulator alongside the Phase 1
# global score. Per D2.4 the channel uses RAW set count (CountingMode-invariant,
# same reasoning as Phase 1 D3). Per D2.9 each exercise contributes to up to
# three muscle buckets (primary/secondary/tertiary) weighted by the standard
# muscle-contribution ladder, mirroring utils.effective_sets so the meaning is
# consistent with the rest of the codebase — but kept here so the math layer
# stays pure (no effective_sets import).


MUSCLE_CONTRIBUTION_WEIGHTS: dict[str, float] = {
    "primary": 1.0,
    "secondary": 0.5,
    "tertiary": 0.25,
}


# Sentinel bucket for the 501 dormant catalog rows the Stage 1 cleanup
# assigned. volume_taxonomy.COARSE_TO_BASIC routes "Unassigned" → "Abdominals"
# only to keep the volume-rollup invariant satisfied; fatigue per-muscle math
# has no such invariant and must NOT silently inflate Abdominals readings.
UNASSIGNED_MUSCLE_BUCKET: str = "Unassigned"


# BRAINSTORM §5 per-muscle MEV / MAV (low, high) / MRV defaults — shipped
# verbatim per Stage 0 owner decision. Twelve muscles have published landmarks.
# Canonical catalog labels for Front-Shoulder, Rear-Shoulder, Lower Back,
# Hip-Adductors, Middle-Traps, and Neck are deliberately absent here — those
# bars render with "—" for the % column and a neutral state (Phase 3 follow-up).
MUSCLE_VOLUME_LANDMARKS: dict[str, tuple[float, float, float, float]] = {
    # (MEV, MAV_low, MAV_high, MRV) — weekly counts per §5.
    "Chest":            (8.0,  12.0, 16.0, 22.0),
    "Latissimus-Dorsi": (10.0, 14.0, 22.0, 25.0),
    "Middle-Shoulder":  (8.0,  16.0, 22.0, 26.0),
    "Biceps":           (8.0,  14.0, 20.0, 26.0),
    "Triceps":          (6.0,  10.0, 14.0, 18.0),
    "Quadriceps":       (8.0,  12.0, 18.0, 20.0),
    "Hamstrings":       (6.0,  10.0, 14.0, 20.0),
    "Glutes":           (0.0,  4.0,  12.0, 16.0),
    "Calves":           (8.0,  12.0, 16.0, 22.0),
    "Abdominals":       (0.0,  6.0,  25.0, 25.0),
    "Traps":            (0.0,  8.0,  14.0, 26.0),
    "Forearms":         (0.0,  6.0,  12.0, 16.0),
}


@dataclass(frozen=True)
class MuscleFatigueResult:
    """Per-muscle aggregated fatigue (one row per canonical bucket)."""
    muscle: str
    score: float
    band: Optional[str]              # None when no §5 landmarks exist for this muscle
    percent_of_mrv: Optional[float]  # None when no §5 landmarks exist
    has_landmarks: bool


def canonicalize_muscle_for_fatigue(value: Optional[str]) -> Optional[str]:
    """
    Map a raw exercises.{primary,secondary,tertiary}_muscle_group value to
    its canonical Basic-bucket label for the per-muscle fatigue accumulator.

    Re-uses volume_taxonomy.COARSE_TO_BASIC for the established aliases
    (Gluteus Maximus → Glutes, Rectus Abdominis → Abdominals, ...) with one
    fatigue-specific override: the Stage 1 "Unassigned" sentinel stays its
    own bucket. volume_taxonomy routes it to Abdominals only to satisfy the
    volume-rollup invariant; fatigue would silently inflate Abdominals if it
    reused that mapping.

    Returns None for null/empty input (caller decides how to bucket).
    Unknown labels pass through verbatim so they surface as their own bars
    rather than being silently absorbed.
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped == UNASSIGNED_MUSCLE_BUCKET:
        return UNASSIGNED_MUSCLE_BUCKET
    key = canonical_pst(stripped)
    if key is None:
        return None
    return COARSE_TO_BASIC.get(key, key)


def classify_muscle_fatigue(muscle: str, score: float) -> Optional[str]:
    """
    Map a per-muscle accumulated score to light / moderate / heavy /
    very_heavy using the §5 landmarks. Returns None when no landmarks are
    defined for this muscle (the six missing-from-§5 catalog labels and
    the Unassigned sentinel) — caller renders those bars with neutral
    state and "—" for the % column.

    Boundary convention mirrors the Phase 1 session/weekly classifier
    (lower-inclusive, upper-exclusive): score == MEV → moderate;
    score == MAV_high → heavy; score == MRV → very_heavy.
    """
    landmarks = MUSCLE_VOLUME_LANDMARKS.get(muscle)
    if landmarks is None:
        return None
    mev, _mav_low, mav_high, mrv = landmarks
    if score < mev:
        return "light"
    if score < mav_high:
        return "moderate"
    if score < mrv:
        return "heavy"
    return "very_heavy"


def muscle_percent_of_mrv(muscle: str, score: float) -> Optional[float]:
    """
    Return 100 * score / MRV for this muscle, or None when no §5 landmarks
    exist. Drives the descending per-muscle bar sort (D2.11).
    """
    landmarks = MUSCLE_VOLUME_LANDMARKS.get(muscle)
    if landmarks is None:
        return None
    *_, mrv = landmarks
    if mrv <= 0:
        return None
    return 100.0 * score / mrv


def aggregate_muscles_for_session(
    exercises: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    """
    Aggregate per-muscle fatigue across one session's exercises.

    Each exercise mapping is read for: `sets`, `movement_pattern`,
    `min_reps` (alias `min_rep_range`), `max_reps` (alias `max_rep_range`),
    `rir`, `primary_muscle_group`, `secondary_muscle_group`,
    `tertiary_muscle_group`. The aliases match the `exercises` + `user_selection`
    column names so the route layer can pass DB rows directly.

    Per D2.4 (carry-forward of Phase 1 D3) this is RAW set count —
    CountingMode is irrelevant. Each role contributes:
        set_fatigue * sets * MUSCLE_CONTRIBUTION_WEIGHTS[role]
    summed by canonical bucket. The "Unassigned" sentinel stays its own
    bucket (NEVER folded into Abdominals — see
    canonicalize_muscle_for_fatigue).

    NULL primary_muscle_group → routed to UNASSIGNED_MUSCLE_BUCKET with a
    warning (Stage 1 cleanup eliminated NULLs, so this is defensive — a
    surfaced warning means the catalog regressed). NULL secondary/tertiary
    contribute nothing (those are legitimately optional).
    """
    totals: dict[str, float] = {}
    for ex in exercises:
        sets = _coerce_sets(ex.get("sets"))
        if sets == 0:
            continue
        per_set = calculate_set_fatigue(
            movement_pattern=ex.get("movement_pattern"),
            min_reps=ex.get("min_reps", ex.get("min_rep_range")),
            max_reps=ex.get("max_reps", ex.get("max_rep_range")),
            rir=ex.get("rir"),
        )
        exercise_fatigue = per_set.fatigue * sets

        primary_bucket = canonicalize_muscle_for_fatigue(
            ex.get("primary_muscle_group")
        )
        if primary_bucket is None:
            logger.warning(
                "fatigue per-muscle: NULL/empty primary_muscle_group, routing to %s bucket",
                UNASSIGNED_MUSCLE_BUCKET,
                extra={"event": "fatigue_primary_muscle_unset"},
            )
            primary_bucket = UNASSIGNED_MUSCLE_BUCKET
        totals[primary_bucket] = totals.get(primary_bucket, 0.0) + (
            exercise_fatigue * MUSCLE_CONTRIBUTION_WEIGHTS["primary"]
        )

        for role, raw in (
            ("secondary", ex.get("secondary_muscle_group")),
            ("tertiary", ex.get("tertiary_muscle_group")),
        ):
            bucket = canonicalize_muscle_for_fatigue(raw)
            if bucket is None:
                continue
            totals[bucket] = totals.get(bucket, 0.0) + (
                exercise_fatigue * MUSCLE_CONTRIBUTION_WEIGHTS[role]
            )
    return totals


def summarize_muscle_bars(
    totals: Mapping[str, float],
) -> list[MuscleFatigueResult]:
    """
    Turn a {muscle_bucket → score} map into a sorted list of
    MuscleFatigueResult rows ready for template rendering.

    Sort key (Stage 0 D2.11 — by % of MRV, highest first):
      1. Muscles with §5 landmarks, sorted by percent_of_mrv DESC.
      2. Muscles WITHOUT landmarks (incl. Unassigned), sorted by raw
         score DESC at the bottom — they have no MRV reference to compare
         against. Bar name then alphabetical as a tiebreaker.
    """
    rows: list[MuscleFatigueResult] = []
    for muscle, score in totals.items():
        band = classify_muscle_fatigue(muscle, score)
        pct = muscle_percent_of_mrv(muscle, score)
        rows.append(
            MuscleFatigueResult(
                muscle=muscle,
                score=score,
                band=band,
                percent_of_mrv=pct,
                has_landmarks=pct is not None,
            )
        )
    rows.sort(
        key=lambda r: (
            0 if r.has_landmarks else 1,
            -(r.percent_of_mrv or 0.0),
            -r.score,
            r.muscle,
        )
    )
    return rows
