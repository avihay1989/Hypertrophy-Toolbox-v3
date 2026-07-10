"""Fatigue Meter — Phase 2 period selector (this session / this week / last 4 weeks).

Internal leaf of the ``utils.fatigue`` facade (WP2.4). Bodies moved verbatim from
the original ``utils/fatigue.py`` Phase 2 period-selector section. Depends on the
Phase 1 core leaf (``_coerce_sets``) and the per-muscle leaf
(``aggregate_muscles_for_session``). Pure: helpers operate on already-loaded rows;
the DB layer in utils.fatigue_data owns the SQL date filter.
"""
from datetime import date, datetime, timedelta
from typing import Any, Mapping, Optional, Sequence

from utils.logger import get_logger

from utils._fatigue.core import _coerce_sets
from utils._fatigue.per_muscle import aggregate_muscles_for_session

logger = get_logger()


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
