"""
Fatigue Meter — pure calculation module (Phase 1).

Phase 1 ships a single global fatigue score for a planned training session
or week. This module is the math layer; route wiring (which reads
`user_selection`) and the badge template come in later chapters.

Per `docs/fatigue_meter/PLANNING.md` Stage 0:
- D3: fatigue uses **raw set count**, independent of `CountingMode`.
  Effective-sets logic in `utils/effective_sets.py` is unrelated and is
  not consulted here.
- D6: no decay in Phase 1.
- D7: no technique modifier in Phase 1.
- D8: RIR multiplier is the discrete-bucket form below.
- D10: planned `user_selection` is the data source — the route layer
  passes already-loaded rows in; this module never touches the DB.
- D11: numbers locked from `BRAINSTORM.md §24.B`.

Per-set formula (§24.B):
    set_fatigue = pattern_weight * load_multiplier * intensity_multiplier
Aggregations:
    session_fatigue = Σ (sets * set_fatigue) across exercises in the session
    weekly_fatigue  = Σ session_fatigue across sessions in the week

Threshold convention: lower-inclusive, upper-exclusive. A score equal to
a band's upper bound classifies into the next-higher band (e.g. 20.0 →
"moderate", 50.0 → "heavy").

This module is pure: no DB access, no Flask imports, no `routes` imports.
"""
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from utils.logger import get_logger

logger = get_logger()


PATTERN_WEIGHTS: dict[str, float] = {
    "hinge": 1.7,
    "squat": 1.6,
    "vertical_push": 1.3,
    "horizontal_push": 1.2,
    "horizontal_pull": 1.2,
    "vertical_pull": 1.2,
    "lower_isolation": 0.9,
    "upper_isolation": 0.8,
    "core_dynamic": 0.8,
    "core_static": 0.7,
}
DEFAULT_PATTERN_WEIGHT: float = 1.0


LOAD_MULTIPLIER_BUCKETS: tuple[tuple[float, float], ...] = (
    (5.0, 1.3),
    (10.0, 1.1),
    (15.0, 1.0),
    (20.0, 0.95),
    (float("inf"), 0.9),
)
DEFAULT_LOAD_MULTIPLIER: float = 1.0


INTENSITY_MULTIPLIER_BUCKETS: dict[str, float] = {
    "0": 2.0,
    "1": 1.5,
    "2": 1.25,
    "3-4": 1.05,
    "5+": 1.0,
}
DEFAULT_INTENSITY_MULTIPLIER: float = 1.0


SESSION_FATIGUE_BANDS: tuple[tuple[float, str], ...] = (
    (20.0, "light"),
    (50.0, "moderate"),
    (80.0, "heavy"),
    (float("inf"), "very_heavy"),
)
WEEKLY_FATIGUE_BANDS: tuple[tuple[float, str], ...] = (
    (80.0, "light"),
    (200.0, "moderate"),
    (320.0, "heavy"),
    (float("inf"), "very_heavy"),
)


@dataclass(frozen=True)
class SetFatigueResult:
    """Per-single-set fatigue. Multiply by `sets` for an exercise total."""
    fatigue: float
    pattern_weight: float
    load_multiplier: float
    intensity_multiplier: float
    pattern_used: str
    rir_bucket: str


@dataclass(frozen=True)
class SessionFatigueResult:
    """Aggregated session fatigue (one routine's worth of exercises)."""
    score: float
    band: str
    exercise_count: int
    set_count: int


@dataclass(frozen=True)
class WeeklyFatigueResult:
    """Aggregated weekly fatigue across sessions. Phase 1: simple sum, no decay."""
    score: float
    band: str
    session_count: int


def _resolve_pattern_weight(movement_pattern: Optional[str]) -> tuple[float, str]:
    if movement_pattern is None:
        logger.warning(
            "fatigue: movement_pattern is NULL, applying neutral fallback %.2f",
            DEFAULT_PATTERN_WEIGHT,
            extra={"event": "fatigue_pattern_unset"},
        )
        return DEFAULT_PATTERN_WEIGHT, "unset"
    key = movement_pattern.strip().lower()
    if not key:
        logger.warning(
            "fatigue: movement_pattern is empty, applying neutral fallback %.2f",
            DEFAULT_PATTERN_WEIGHT,
            extra={"event": "fatigue_pattern_unset"},
        )
        return DEFAULT_PATTERN_WEIGHT, "unset"
    weight = PATTERN_WEIGHTS.get(key)
    if weight is None:
        logger.warning(
            "fatigue: unrecognized movement_pattern %r, applying neutral fallback %.2f",
            key,
            DEFAULT_PATTERN_WEIGHT,
            extra={"event": "fatigue_pattern_unknown", "pattern": key},
        )
        return DEFAULT_PATTERN_WEIGHT, "unset"
    return weight, key


def _resolve_load_multiplier(min_reps: Optional[int], max_reps: Optional[int]) -> float:
    lo = min_reps if (min_reps is not None and min_reps > 0) else None
    hi = max_reps if (max_reps is not None and max_reps > 0) else None
    if lo is None and hi is None:
        return DEFAULT_LOAD_MULTIPLIER
    if lo is None:
        avg = float(hi)  # type: ignore[arg-type]
    elif hi is None:
        avg = float(lo)
    else:
        avg = (lo + hi) / 2.0
    for upper, mult in LOAD_MULTIPLIER_BUCKETS:
        if avg <= upper:
            return mult
    return DEFAULT_LOAD_MULTIPLIER


def _rir_to_bucket(rir: int) -> str:
    if rir <= 0:
        return "0"
    if rir == 1:
        return "1"
    if rir == 2:
        return "2"
    if rir <= 4:
        return "3-4"
    return "5+"


def _resolve_intensity_multiplier(rir: Optional[int]) -> tuple[float, str]:
    if rir is None:
        logger.warning(
            "fatigue: RIR is NULL, applying neutral multiplier %.2f",
            DEFAULT_INTENSITY_MULTIPLIER,
            extra={"event": "fatigue_rir_unset"},
        )
        return DEFAULT_INTENSITY_MULTIPLIER, "unknown"
    if rir < 0:
        logger.warning(
            "fatigue: RIR %r is negative, treating as unknown",
            rir,
            extra={"event": "fatigue_rir_invalid", "rir": rir},
        )
        return DEFAULT_INTENSITY_MULTIPLIER, "unknown"
    bucket = _rir_to_bucket(rir)
    return INTENSITY_MULTIPLIER_BUCKETS[bucket], bucket


def calculate_set_fatigue(
    movement_pattern: Optional[str],
    min_reps: Optional[int],
    max_reps: Optional[int],
    rir: Optional[int],
) -> SetFatigueResult:
    """
    Compute per-single-set fatigue per §24.B:
        set_fatigue = pattern_weight * load_multiplier * intensity_multiplier
    All four inputs may be None — neutral fallbacks apply, and a warning
    is logged for `movement_pattern` and `rir` so calibration can spot
    catalog or input gaps.
    """
    pattern_weight, pattern_used = _resolve_pattern_weight(movement_pattern)
    load_multiplier = _resolve_load_multiplier(min_reps, max_reps)
    intensity_multiplier, rir_bucket = _resolve_intensity_multiplier(rir)
    fatigue = pattern_weight * load_multiplier * intensity_multiplier
    return SetFatigueResult(
        fatigue=fatigue,
        pattern_weight=pattern_weight,
        load_multiplier=load_multiplier,
        intensity_multiplier=intensity_multiplier,
        pattern_used=pattern_used,
        rir_bucket=rir_bucket,
    )


def _coerce_sets(value: Any) -> int:
    if value is None:
        return 0
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def aggregate_session_fatigue(
    exercises: Sequence[Mapping[str, Any]],
) -> SessionFatigueResult:
    """
    Sum per-set fatigue × sets across exercises in one session.

    Each exercise mapping is read for: `sets`, `movement_pattern`,
    `min_reps` (alias `min_rep_range`), `max_reps` (alias `max_rep_range`),
    and `rir`. The aliases match the `user_selection` column names so the
    route layer can pass DB rows directly.

    Per Stage 0 D3, this is RAW set count — `CountingMode` is irrelevant
    here. Empty list or all-zero-set inputs → score 0.0, band 'light'.
    Same exercise listed twice contributes twice (no dedup).
    """
    total = 0.0
    set_count = 0
    exercise_count = 0
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
        total += per_set.fatigue * sets
        set_count += sets
        exercise_count += 1
    return SessionFatigueResult(
        score=total,
        band=classify_session_fatigue(total),
        exercise_count=exercise_count,
        set_count=set_count,
    )


def aggregate_weekly_fatigue(
    sessions: Sequence[SessionFatigueResult],
) -> WeeklyFatigueResult:
    """
    Sum session scores across the week. Phase 1: no decay (D6).

    Date-bucketing into ISO weeks belongs in the route layer that calls
    this — Phase 1's `user_selection` source has no date column (D10), so
    "week" here means "the set of routines passed in".
    """
    total = sum(s.score for s in sessions)
    return WeeklyFatigueResult(
        score=total,
        band=classify_weekly_fatigue(total),
        session_count=len(sessions),
    )


def _classify(score: float, bands: Sequence[tuple[float, str]]) -> str:
    for upper, name in bands:
        if score < upper:
            return name
    return bands[-1][1]


def classify_session_fatigue(score: float) -> str:
    """Map a session-level score to one of light / moderate / heavy / very_heavy."""
    return _classify(score, SESSION_FATIGUE_BANDS)


def classify_weekly_fatigue(score: float) -> str:
    """Map a weekly-level score to one of light / moderate / heavy / very_heavy."""
    return _classify(score, WEEKLY_FATIGUE_BANDS)
