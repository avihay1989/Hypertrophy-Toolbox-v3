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
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Optional, Sequence

from utils.logger import get_logger
from utils.volume_taxonomy import COARSE_TO_BASIC, canonical_pst

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


# =============================================================================
# Phase 2 — period selector (this session / this week / last 4 weeks)
# =============================================================================
# The page-level period selector (D2.12) operates on logged rows from
# workout_log. Phase 1 had no period concept; this is the first place in the
# codebase that computes a rolling 4-week window. The math stays pure: helpers
# operate on already-loaded rows tagged with a `created_at`-style date string,
# and the DB layer in utils.fatigue_data is responsible for the SQL filter
# itself (matching the existing utils.session_summary date-window pattern).


VALID_PERIODS: tuple[str, ...] = ("this_session", "this_week", "last_4_weeks")
DEFAULT_PERIOD: str = "this_week"

PERIOD_LABELS: dict[str, str] = {
    "this_session": "Most recent session",
    "this_week": "This week (Mon–Sun)",
    "last_4_weeks": "Last 4 weeks",
}


def normalize_period(value: Optional[str]) -> str:
    """
    Map a raw query-param value to one of VALID_PERIODS. Unknown / missing
    values silently fall back to DEFAULT_PERIOD — matches the existing
    summary-route convention so the page never errors on a bad URL.
    """
    if not value:
        return DEFAULT_PERIOD
    key = value.strip().lower()
    if key in VALID_PERIODS:
        return key
    logger.info(
        "fatigue: unknown period %r, falling back to %s",
        value,
        DEFAULT_PERIOD,
        extra={"event": "fatigue_period_fallback", "raw": value},
    )
    return DEFAULT_PERIOD


def _coerce_date(value: Any) -> Optional[date]:
    """
    Accept a date, datetime, or ISO-ish string (the shape SQLite returns for
    `created_at`) and return a `date`. Returns None for anything unparseable
    so callers can decide whether to drop or warn.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    # SQLite TIMESTAMP DEFAULT CURRENT_TIMESTAMP renders as 'YYYY-MM-DD HH:MM:SS'
    # — take the leading 10 chars, matching utils.session_summary.
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def compute_period_window(
    period: str,
    today: Optional[date] = None,
    logged_dates: Optional[Sequence[Any]] = None,
) -> tuple[Optional[date], Optional[date]]:
    """
    Resolve a period name to a (start, end) inclusive date window.

    - `this_session`  → window covering the most-recent logged date. If
                        `logged_dates` is None or empty, returns (None, None)
                        and the caller renders empty state.
    - `this_week`     → Monday through Sunday of the ISO week that
                        contains `today`.
    - `last_4_weeks`  → trailing 28 days inclusive of `today`
                        (today − 27 .. today).

    Both bounds are inclusive ISO dates (matches `DATE(wl.created_at)` SQL).
    """
    period = normalize_period(period)
    anchor = today or date.today()

    if period == "this_week":
        start = anchor - timedelta(days=anchor.weekday())  # Monday
        end = start + timedelta(days=6)                    # Sunday
        return start, end

    if period == "last_4_weeks":
        start = anchor - timedelta(days=27)
        return start, anchor

    # this_session
    if not logged_dates:
        return None, None
    parsed = [d for d in (_coerce_date(v) for v in logged_dates) if d is not None]
    if not parsed:
        return None, None
    latest = max(parsed)
    return latest, latest


def filter_rows_by_date_window(
    rows: Sequence[Mapping[str, Any]],
    start: Optional[date],
    end: Optional[date],
    date_field: str = "created_at",
) -> list[dict[str, Any]]:
    """
    Return only the rows whose `date_field` falls within [start, end]
    inclusive. If both bounds are None, every row passes (caller should
    treat this as an empty window — see compute_period_window).
    """
    if start is None and end is None:
        return []
    keep: list[dict[str, Any]] = []
    for row in rows:
        row_date = _coerce_date(row.get(date_field))
        if row_date is None:
            continue
        if start is not None and row_date < start:
            continue
        if end is not None and row_date > end:
            continue
        keep.append(dict(row))
    return keep


def adapt_logged_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """
    Translate a workout_log JOIN exercises row into the shape
    `aggregate_muscles_for_session` consumes.

    Mapping:
        sets       ← planned_sets (counts logged sets; the schema has no
                     per-set granularity, so the planned count is the best
                     proxy when the row carries scored values).
        rir        ← scored_rir if not None else planned_rir
        min_reps   ← scored_min_reps if not None else planned_min_reps
        max_reps   ← scored_max_reps if not None else planned_max_reps
        primary_muscle_group / secondary_ / tertiary_ / movement_pattern
                   ← passed through from the exercises JOIN.

    Rows with no scored value at all (every scored_* field is NULL) are
    treated as `sets = 0` (the exercise was skipped) so they contribute
    no fatigue. This matches the §7 unit-test row "Mixed completed +
    skipped sets → only scored sets contribute."
    """
    scored_rir = row.get("scored_rir")
    scored_min = row.get("scored_min_reps")
    scored_max = row.get("scored_max_reps")
    scored_weight = row.get("scored_weight")

    has_any_scored = any(
        v is not None for v in (scored_rir, scored_min, scored_max, scored_weight)
    )
    sets = _coerce_sets(row.get("planned_sets")) if has_any_scored else 0

    return {
        "sets": sets,
        "rir": scored_rir if scored_rir is not None else row.get("planned_rir"),
        "min_reps": scored_min if scored_min is not None else row.get("planned_min_reps"),
        "max_reps": scored_max if scored_max is not None else row.get("planned_max_reps"),
        "movement_pattern": row.get("movement_pattern"),
        "primary_muscle_group": row.get("primary_muscle_group"),
        "secondary_muscle_group": row.get("secondary_muscle_group"),
        "tertiary_muscle_group": row.get("tertiary_muscle_group"),
    }


def aggregate_logged_muscles(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    """
    Per-muscle fatigue accumulator for already-filtered workout_log rows.

    Each row is passed through `adapt_logged_row` and then handed to
    `aggregate_muscles_for_session`. The caller is responsible for
    filtering rows to the requested period (see compute_period_window +
    filter_rows_by_date_window) — keeping that split makes the math
    layer pure and lets the DB layer push the date filter into SQL where
    it belongs.
    """
    adapted = [adapt_logged_row(r) for r in rows]
    return aggregate_muscles_for_session(adapted)


# =============================================================================
# Phase 2 — Stimulus-to-Fatigue Ratio (page-level, D2.6)
# =============================================================================
# SFR ships as two cards at the top of /fatigue (planned + logged). Stimulus
# is the page-level effective_sets sum (computed by the route layer from
# utils.effective_sets); fatigue is the Phase 1 session/weekly score for the
# same side. Per-muscle SFR stays deferred (D2.6).


SFR_FATIGUE_ZERO_SENTINEL: Optional[float] = None
"""Sentinel used when the denominator (fatigue) is zero — render as "—",
never as `inf`. Per §16.1 SFR test row."""


def compute_sfr(
    stimulus: Optional[float],
    fatigue: Optional[float],
) -> Optional[float]:
    """
    stimulus / fatigue, with two guarded cases per §16.1:
      - fatigue == 0 (or None)  → returns SFR_FATIGUE_ZERO_SENTINEL (None);
                                  the template renders "—".
      - stimulus == 0           → returns 0.0; the user did the work but
                                  it produced no recorded stimulus.
    Both positive → straightforward ratio.
    """
    if fatigue is None or fatigue <= 0:
        return SFR_FATIGUE_ZERO_SENTINEL
    if stimulus is None:
        return 0.0
    return float(stimulus) / float(fatigue)
