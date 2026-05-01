"""
Fatigue Meter — DB query layer (Phase 1).

Reads `user_selection` joined to `exercises` and shapes rows for the
pure-math layer in `utils/fatigue.py`. Per Stage 0 D10, the data source
is the planned program (`user_selection`), not `workout_log`. Per the
D13 override, this module pulls `movement_pattern`, `min_rep_range`,
`max_rep_range`, `sets`, and `rir` directly from the join rather than
relying on the already-aggregated rows in `utils/session_summary.py` /
`utils/weekly_summary.py` (those don't carry pattern or RIR).

Kept separate from `utils/fatigue.py` so the math layer stays pure.
"""
from __future__ import annotations

from typing import Any, Optional

from utils.database import DatabaseHandler
from utils.fatigue import (
    SessionFatigueResult,
    WeeklyFatigueResult,
    aggregate_session_fatigue,
    aggregate_weekly_fatigue,
)
from utils.logger import get_logger

logger = get_logger()


def load_planned_exercises(routine: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Fetch planned-routine rows in the shape `aggregate_session_fatigue`
    consumes. Each row has: `routine`, `sets`, `min_rep_range`,
    `max_rep_range`, `rir`, `movement_pattern`.

    `LEFT JOIN` on `exercises` so a row with an exercise_name not in the
    catalog still surfaces (movement_pattern will be None and the math
    layer's neutral fallback kicks in).
    """
    query = """
        SELECT
            us.routine,
            us.sets,
            us.min_rep_range,
            us.max_rep_range,
            us.rir,
            e.movement_pattern
        FROM user_selection us
        LEFT JOIN exercises e ON e.exercise_name = us.exercise
    """
    params: tuple[Any, ...]
    if routine:
        query += " WHERE us.routine = ?"
        params = (routine,)
    else:
        params = ()
    with DatabaseHandler() as db:
        return db.fetch_all(query, params)


def compute_session_fatigue_for_routine(routine: str) -> SessionFatigueResult:
    """Project session fatigue for a single named routine."""
    rows = load_planned_exercises(routine=routine)
    return aggregate_session_fatigue(rows)


def compute_heaviest_session_fatigue() -> tuple[Optional[str], SessionFatigueResult]:
    """
    Pick the planned routine with the highest projected session fatigue.

    Returns `(routine_name, result)`. If there are no planned routines,
    returns `(None, SessionFatigueResult(score=0, band='light', ...))`.
    """
    rows = load_planned_exercises()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = row.get("routine") or ""
        grouped.setdefault(key, []).append(row)
    if not grouped:
        return None, aggregate_session_fatigue([])
    scored = [
        (name, aggregate_session_fatigue(group))
        for name, group in grouped.items()
    ]
    scored.sort(key=lambda pair: pair[1].score, reverse=True)
    return scored[0]


def compute_weekly_fatigue() -> WeeklyFatigueResult:
    """
    Sum session-level fatigue across every planned routine.

    Phase 1 has no decay (D6) and no real dates — `user_selection`
    represents the program template. Each distinct `routine` is treated
    as one session in the week.
    """
    rows = load_planned_exercises()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = row.get("routine") or ""
        grouped.setdefault(key, []).append(row)
    sessions = [aggregate_session_fatigue(group) for group in grouped.values()]
    return aggregate_weekly_fatigue(sessions)
