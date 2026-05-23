"""
Fatigue Meter — DB query layer (Phase 1 + Phase 2).

Reads `user_selection` (planned) and `workout_log` (logged) joined to
`exercises` and shapes rows for the pure-math layer in `utils/fatigue.py`.

Phase 1: per Stage 0 D10, the data source was planned only. Per D13, this
module pulls `movement_pattern`, `min_rep_range`, `max_rep_range`, `sets`,
and `rir` directly from the join rather than relying on the already-aggregated
rows in `utils/session_summary.py` / `utils/weekly_summary.py` (those don't
carry pattern or RIR).

Phase 2 (Stage 2): adds per-muscle aggregation and logged-side queries per
D2.5 (planned + logged side-by-side) and D2.9 (re-query both tables; don't
reuse aggregated rows). Date filter for the logged side matches the existing
`utils/session_summary.py` convention (`DATE(wl.created_at)`).

Kept separate from `utils/fatigue.py` so the math layer stays pure.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from utils.database import DatabaseHandler
from utils.effective_sets import (
    ContributionMode,
    CountingMode,
    calculate_effective_sets,
)
from utils.fatigue import (
    DEFAULT_PERIOD,
    MuscleFatigueResult,
    PERIOD_LABELS,
    SessionFatigueResult,
    VALID_PERIODS,
    WeeklyFatigueResult,
    aggregate_logged_muscles,
    aggregate_muscles_for_session,
    aggregate_session_fatigue,
    aggregate_weekly_fatigue,
    classify_session_fatigue,
    compute_period_window,
    compute_sfr,
    filter_rows_by_date_window,
    normalize_period,
    summarize_muscle_bars,
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


# =============================================================================
# Phase 2 (Stage 2) — per-muscle planned + logged queries + page builder
# =============================================================================


def load_planned_exercises_with_muscles() -> list[dict[str, Any]]:
    """
    Same as `load_planned_exercises` but pulls the three muscle-group columns
    needed for the per-muscle accumulator (D2.9 / D13: re-query the rows;
    don't reuse already-aggregated session_summary output).
    """
    query = """
        SELECT
            us.routine,
            us.sets,
            us.min_rep_range,
            us.max_rep_range,
            us.rir,
            e.movement_pattern,
            e.primary_muscle_group,
            e.secondary_muscle_group,
            e.tertiary_muscle_group
        FROM user_selection us
        LEFT JOIN exercises e ON e.exercise_name = us.exercise
    """
    with DatabaseHandler() as db:
        return db.fetch_all(query)


def load_logged_exercises_with_muscles(
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[dict[str, Any]]:
    """
    Fetch workout_log rows in the optional [start, end] inclusive window,
    joined to `exercises` for movement_pattern + muscle-group columns.

    SQL date filter matches the `DATE(wl.created_at)` convention used by
    `utils/session_summary.py` — the SQLite TIMESTAMP DEFAULT
    CURRENT_TIMESTAMP column renders as 'YYYY-MM-DD HH:MM:SS' and the
    DATE() truncation is sargable enough at this scale.

    When `start` is None and `end` is None the call returns every logged
    row — useful for the `this_session` period (which needs to discover
    the latest logged date before the window can be computed).
    """
    query = """
        SELECT
            wl.routine,
            wl.created_at,
            wl.planned_sets,
            wl.planned_min_reps,
            wl.planned_max_reps,
            wl.planned_rir,
            wl.scored_min_reps,
            wl.scored_max_reps,
            wl.scored_rir,
            wl.scored_weight,
            e.movement_pattern,
            e.primary_muscle_group,
            e.secondary_muscle_group,
            e.tertiary_muscle_group
        FROM workout_log wl
        LEFT JOIN exercises e ON e.exercise_name = wl.exercise
    """
    params: list[Any] = []
    clauses: list[str] = []
    if start is not None:
        clauses.append("DATE(wl.created_at) >= DATE(?)")
        params.append(start.isoformat())
    if end is not None:
        clauses.append("DATE(wl.created_at) <= DATE(?)")
        params.append(end.isoformat())
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    with DatabaseHandler() as db:
        return db.fetch_all(query, tuple(params))


def _stimulus_from_rows(
    rows: list[dict[str, Any]],
    side: str,
) -> float:
    """
    Page-level stimulus proxy for the SFR card — Σ effective_sets across
    every row on the given side (`planned` or `logged`). Uses the standard
    EFFECTIVE / TOTAL configuration from utils.effective_sets so the
    number is comparable to the rest of the app's volume readouts.
    """
    total = 0.0
    for row in rows:
        if side == "planned":
            sets = row.get("sets") or 0
            rir = row.get("rir")
            min_r = row.get("min_rep_range")
            max_r = row.get("max_rep_range")
        else:
            scored_rir = row.get("scored_rir")
            scored_min = row.get("scored_min_reps")
            scored_max = row.get("scored_max_reps")
            scored_weight = row.get("scored_weight")
            has_any_scored = any(
                v is not None for v in (scored_rir, scored_min, scored_max, scored_weight)
            )
            sets = (row.get("planned_sets") or 0) if has_any_scored else 0
            rir = scored_rir if scored_rir is not None else row.get("planned_rir")
            min_r = scored_min if scored_min is not None else row.get("planned_min_reps")
            max_r = scored_max if scored_max is not None else row.get("planned_max_reps")
        if not sets:
            continue
        result = calculate_effective_sets(
            sets=int(sets),
            rir=rir,
            min_rep_range=min_r,
            max_rep_range=max_r,
            primary_muscle=row.get("primary_muscle_group"),
            secondary_muscle=row.get("secondary_muscle_group"),
            tertiary_muscle=row.get("tertiary_muscle_group"),
            counting_mode=CountingMode.EFFECTIVE,
            contribution_mode=ContributionMode.TOTAL,
        )
        total += result.effective_sets
    return total


def _bar_to_dict(bar: MuscleFatigueResult) -> dict[str, Any]:
    """Template-friendly dict (Jinja doesn't enjoy frozen dataclasses)."""
    return {
        "muscle": bar.muscle,
        "score": bar.score,
        "band": bar.band,
        "percent_of_mrv": bar.percent_of_mrv,
        "has_landmarks": bar.has_landmarks,
    }


def _merge_muscle_rows(
    planned_bars: list[MuscleFatigueResult],
    logged_bars: list[MuscleFatigueResult],
) -> list[dict[str, Any]]:
    """
    Merge the planned and logged bar lists into one row per muscle so the
    template can render dual sub-bars (D2.5). Sort key matches
    summarize_muscle_bars for the merged view:
      1. Muscles WITH §5 landmarks first; muscles WITHOUT (incl. Unassigned) last.
      2. Within each group, descending by the larger of the two sides'
         %MRV (so the worst-stressed muscle floats up regardless of which
         side reflects it).
      3. Score descending as a tiebreak, then muscle name ascending.
    """
    by_muscle: dict[str, dict[str, Any]] = {}
    for bar in planned_bars:
        by_muscle.setdefault(bar.muscle, {"muscle": bar.muscle, "planned": None, "logged": None})
        by_muscle[bar.muscle]["planned"] = _bar_to_dict(bar)
    for bar in logged_bars:
        by_muscle.setdefault(bar.muscle, {"muscle": bar.muscle, "planned": None, "logged": None})
        by_muscle[bar.muscle]["logged"] = _bar_to_dict(bar)

    rows: list[dict[str, Any]] = []
    for row in by_muscle.values():
        planned = row["planned"]
        logged = row["logged"]
        has_landmarks = bool(
            (planned and planned["has_landmarks"])
            or (logged and logged["has_landmarks"])
        )
        pcts = [
            x["percent_of_mrv"]
            for x in (planned, logged)
            if x and x["percent_of_mrv"] is not None
        ]
        scores = [x["score"] for x in (planned, logged) if x]
        row["has_landmarks"] = has_landmarks
        row["max_percent_of_mrv"] = max(pcts) if pcts else None
        row["max_score"] = max(scores) if scores else 0.0
        rows.append(row)

    rows.sort(
        key=lambda r: (
            0 if r["has_landmarks"] else 1,
            -(r["max_percent_of_mrv"] or 0.0),
            -r["max_score"],
            r["muscle"],
        )
    )
    return rows


def build_fatigue_page_context(
    period: Optional[str],
    today: Optional[date] = None,
) -> dict[str, Any]:
    """
    Assemble the full template context for `GET /fatigue`.

    Steps:
      1. Normalize the requested period (invalid → DEFAULT_PERIOD silently,
         matching the existing summary-route convention).
      2. Load planned rows once; aggregate per-muscle and total fatigue.
      3. Resolve the logged-side date window (for `this_session`, peek at
         workout_log to find the latest date), then query logged rows in
         that window.
      4. Aggregate logged per-muscle + total fatigue; compute SFR for both
         sides; pack everything in a Jinja-friendly dict.
    """
    period = normalize_period(period)

    planned_rows = load_planned_exercises_with_muscles()
    planned_muscle_totals = aggregate_muscles_for_session(planned_rows)
    planned_bars = summarize_muscle_bars(planned_muscle_totals)
    planned_fatigue = sum(planned_muscle_totals.values())
    planned_stimulus = _stimulus_from_rows(planned_rows, side="planned")

    window_start: Optional[date]
    window_end: Optional[date]
    if period == "this_session":
        all_logged_dates = [
            r.get("created_at")
            for r in load_logged_exercises_with_muscles(start=None, end=None)
        ]
        window_start, window_end = compute_period_window(
            period, today=today, logged_dates=all_logged_dates
        )
    else:
        window_start, window_end = compute_period_window(period, today=today)

    if window_start is None and window_end is None:
        logged_rows: list[dict[str, Any]] = []
    else:
        logged_rows = load_logged_exercises_with_muscles(
            start=window_start, end=window_end
        )

    # Defensive belt: drop any row whose created_at falls outside the window
    # (SQLite DATE() should already enforce this; the helper handles the
    # this_session "no window" edge case cleanly).
    if window_start is not None or window_end is not None:
        logged_rows = filter_rows_by_date_window(
            logged_rows, window_start, window_end, date_field="created_at"
        )

    logged_muscle_totals = aggregate_logged_muscles(logged_rows)
    logged_bars = summarize_muscle_bars(logged_muscle_totals)
    logged_fatigue = sum(logged_muscle_totals.values())
    logged_stimulus = _stimulus_from_rows(logged_rows, side="logged")

    return {
        "period": period,
        "period_label": PERIOD_LABELS[period],
        "valid_periods": list(VALID_PERIODS),
        "period_labels": dict(PERIOD_LABELS),
        "window_start": window_start.isoformat() if window_start else None,
        "window_end": window_end.isoformat() if window_end else None,
        "muscles_planned": [_bar_to_dict(b) for b in planned_bars],
        "muscles_logged": [_bar_to_dict(b) for b in logged_bars],
        "muscle_rows": _merge_muscle_rows(planned_bars, logged_bars),
        "planned_fatigue_score": planned_fatigue,
        "planned_fatigue_band": classify_session_fatigue(planned_fatigue),
        "logged_fatigue_score": logged_fatigue,
        "logged_fatigue_band": classify_session_fatigue(logged_fatigue),
        "planned_stimulus": planned_stimulus,
        "logged_stimulus": logged_stimulus,
        "sfr_planned": compute_sfr(planned_stimulus, planned_fatigue),
        "sfr_logged": compute_sfr(logged_stimulus, logged_fatigue),
        "planned_has_data": bool(planned_rows),
        "logged_has_data": bool(logged_rows),
    }
