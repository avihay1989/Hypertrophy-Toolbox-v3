"""Session-level analytics mirroring the weekly summary weighting."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Optional, Tuple

from utils.database import DatabaseHandler
from utils.volume_classifier import get_volume_class
from utils.weekly_summary import EFFECTIVE_STATUS_MAP
from utils.effective_sets import (
    CountingMode,
    ContributionMode,
    VolumeWarningLevel,
    calculate_effective_sets,
    get_session_volume_warning,
    get_weekly_volume_class,
    MUSCLE_CONTRIBUTION_WEIGHTS,
)


def _build_plan_query(routine: Optional[str] = None) -> Tuple[str, list[Any]]:
    plan_params: list[Any] = []
    plan_query = """
        SELECT
            us.id AS selection_id,
            us.routine,
            us.sets,
            us.min_rep_range,
            us.max_rep_range,
            us.weight,
            us.rir,
            us.rpe,
            e.primary_muscle_group,
            e.secondary_muscle_group,
            e.tertiary_muscle_group
        FROM user_selection us
        JOIN exercises e ON us.exercise = e.exercise_name
        WHERE 1=1
    """
    if routine:
        plan_query += " AND us.routine = ?"
        plan_params.append(routine)
    return plan_query, plan_params


def _build_log_query(
    routine: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
) -> Tuple[str, list[Any]]:
    log_params: list[Any] = []
    log_query = """
        SELECT
            wl.workout_plan_id,
            wl.created_at
        FROM workout_log wl
        JOIN user_selection us ON wl.workout_plan_id = us.id
        WHERE wl.workout_plan_id IS NOT NULL
    """
    if routine:
        log_query += " AND us.routine = ?"
        log_params.append(routine)
    if start_date:
        log_query += " AND DATE(wl.created_at) >= DATE(?)"
        log_params.append(start_date)
    if end_date:
        log_query += " AND DATE(wl.created_at) <= DATE(?)"
        log_params.append(end_date)
    return log_query, log_params


def _aggregate_muscle_volumes(
    plan_rows: list[Dict[str, Any]], 
    contribution_mode: ContributionMode
) -> Tuple[
    Dict[str, Dict[str, Dict[str, float]]],
    Dict[str, Dict[str, Dict[str, float]]],
    Dict[int, Tuple[str, Tuple[str, ...]]]
]:
    effective_totals: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {'sets': 0.0, 'reps': 0.0, 'volume': 0.0})
    )
    raw_totals: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {'sets': 0.0, 'reps': 0.0, 'volume': 0.0})
    )
    selection_to_muscles: Dict[int, Tuple[str, Tuple[str, ...]]] = {}
    
    for row in plan_rows:
        selection_id = row.get('selection_id')
        routine_name = row.get('routine') or 'Unassigned'
        sets = row.get('sets') or 0
        min_rep = row.get('min_rep_range')
        max_rep = row.get('max_rep_range')
        rir = row.get('rir')
        rpe = row.get('rpe')
        load = row.get('weight') or 0
        
        avg_reps = 0.0
        if min_rep is not None and max_rep is not None:
            avg_reps = (min_rep + max_rep) / 2.0
            
        eff_result = calculate_effective_sets(
            sets=sets,
            rir=rir,
            rpe=rpe,
            min_rep_range=min_rep,
            max_rep_range=max_rep,
            primary_muscle=row.get('primary_muscle_group'),
            secondary_muscle=row.get('secondary_muscle_group'),
            tertiary_muscle=row.get('tertiary_muscle_group'),
            counting_mode=CountingMode.EFFECTIVE,
            contribution_mode=contribution_mode,
        )
        
        contributions = [
            (row.get('primary_muscle_group'), MUSCLE_CONTRIBUTION_WEIGHTS['primary']),
            (row.get('secondary_muscle_group'), MUSCLE_CONTRIBUTION_WEIGHTS['secondary']),
            (row.get('tertiary_muscle_group'), MUSCLE_CONTRIBUTION_WEIGHTS['tertiary']),
        ]
        contributed_muscles: list[str] = []
        
        for muscle, weight_factor in contributions:
            if not muscle:
                continue
            
            if contribution_mode == ContributionMode.DIRECT_ONLY:
                if weight_factor != MUSCLE_CONTRIBUTION_WEIGHTS['primary']:
                    continue
                weight_factor = 1.0
            
            eff_contribution = eff_result.muscle_contributions.get(muscle, 0.0)
            
            raw_weighted_sets = sets * weight_factor
            raw_weighted_reps = raw_weighted_sets * avg_reps
            raw_weighted_volume = raw_weighted_reps * load
            
            eff_weighted_reps = eff_contribution * avg_reps
            eff_weighted_volume = eff_weighted_reps * load
            
            eff_bucket = effective_totals[routine_name][muscle]
            eff_bucket['sets'] += eff_contribution
            eff_bucket['reps'] += eff_weighted_reps
            eff_bucket['volume'] += eff_weighted_volume
            
            raw_bucket = raw_totals[routine_name][muscle]
            raw_bucket['sets'] += raw_weighted_sets
            raw_bucket['reps'] += raw_weighted_reps
            raw_bucket['volume'] += raw_weighted_volume

            contributed_muscles.append(muscle)

        if selection_id is not None and contributed_muscles:
            unique_muscles = tuple(dict.fromkeys(contributed_muscles))
            selection_to_muscles[int(selection_id)] = (routine_name, unique_muscles)
            
    return effective_totals, raw_totals, selection_to_muscles


def _aggregate_session_dates(
    log_rows: list[Dict[str, Any]], 
    selection_to_muscles: Dict[int, Tuple[str, Tuple[str, ...]]]
) -> Dict[str, Dict[str, set]]:
    session_dates: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for log_row in log_rows:
        selection_id = log_row.get('workout_plan_id')
        created_at = log_row.get('created_at')
        session_date = str(created_at)[:10] if created_at else None
        if selection_id is None or not session_date:
            continue

        selection_map = selection_to_muscles.get(int(selection_id))
        if not selection_map:
            continue

        routine_name, muscles = selection_map
        for muscle in muscles:
            session_dates[routine_name][muscle].add(session_date)
    return session_dates


def _build_summary_output(
    effective_totals: Dict[str, Dict[str, Dict[str, float]]],
    raw_totals: Dict[str, Dict[str, Dict[str, float]]],
    session_dates: Dict[str, Dict[str, set]],
    counting_mode: CountingMode,
    contribution_mode: ContributionMode
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    summary: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
    for routine_name in set(effective_totals.keys()) | set(raw_totals.keys()):
        summary[routine_name] = {}
        all_muscles = set(effective_totals[routine_name].keys()) | set(raw_totals[routine_name].keys())
        
        for muscle in sorted(all_muscles):
            eff_aggregates = effective_totals[routine_name][muscle]
            raw_aggregates = raw_totals[routine_name][muscle]
            
            weekly_eff_sets = eff_aggregates['sets']
            weekly_raw_sets = raw_aggregates['sets']
            
            if counting_mode == CountingMode.RAW:
                weekly_sets = weekly_raw_sets
            else:
                weekly_sets = weekly_eff_sets
            
            unique_dates = session_dates[routine_name].get(muscle, set())
            session_count = len(unique_dates)
            has_logged_sessions = session_count > 0

            volume_class_str = get_weekly_volume_class(weekly_eff_sets)
            legacy_volume_class = get_volume_class(weekly_sets)

            if has_logged_sessions:
                sets_per_session = round(weekly_sets / session_count, 2)
                eff_per_session = round(weekly_eff_sets / session_count, 2)
                warning_level = get_session_volume_warning(eff_per_session)
            else:
                sets_per_session = None
                eff_per_session = None
                warning_level = VolumeWarningLevel.OK 

            summary[routine_name][muscle] = {
                'weekly_sets': round(weekly_sets, 2),
                'sets_per_session': sets_per_session,
                'status': EFFECTIVE_STATUS_MAP.get(volume_class_str, 'low'),
                'volume_class': legacy_volume_class,

                'raw_sets': round(weekly_raw_sets, 2),
                'effective_sets': round(weekly_eff_sets, 2),
                'effective_per_session': eff_per_session,

                'session_count': session_count,
                'has_logged_sessions': has_logged_sessions,

                'warning_level': 'no_data' if not has_logged_sessions else warning_level.value,
                'is_borderline': has_logged_sessions and warning_level == VolumeWarningLevel.BORDERLINE,
                'is_excessive': has_logged_sessions and warning_level == VolumeWarningLevel.EXCESSIVE,

                'total_reps': round(eff_aggregates['reps'], 2),
                'total_volume': round(eff_aggregates['volume'], 2),
                'raw_total_reps': round(raw_aggregates['reps'], 2),
                'raw_total_volume': round(raw_aggregates['volume'], 2),

                'counting_mode': counting_mode.value,
                'contribution_mode': contribution_mode.value,
            }

    return summary


def calculate_session_summary(
    routine: Optional[str] = None,
    time_window: Optional[Tuple[str, str]] = None,
    counting_mode: CountingMode = CountingMode.EFFECTIVE,
    contribution_mode: ContributionMode = ContributionMode.TOTAL,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Aggregate weighted sets per muscle, grouped by routine and optional date window.
    
    Applies effective set calculation at the per-exercise level, including:
    - Effort factor (RIR/RPE based)
    - Rep range factor
    - Muscle contribution weighting
    
    Args:
        routine: Optional filter for specific routine.
        time_window: Optional (start_date, end_date) tuple for filtering.
        counting_mode: RAW or EFFECTIVE set counting mode.
        contribution_mode: DIRECT_ONLY or TOTAL muscle contribution mode.
        
    Returns:
        Nested dict: {routine: {muscle: {volume_stats}}} with:
        - weekly_sets: Session sets (effective or raw based on mode)
        - effective_sets: Always the effective set count
        - raw_sets: Always the raw set count
        - sets_per_session: Average per session occurrence
        - status: Volume classification
        - volume_class: CSS class for styling
        - warning_level: Session volume warning (ok/borderline/excessive)
        - total_reps: Rep total for session
        - total_volume: Volume total (sets * reps * weight)
    """
    start_date, end_date = (time_window if time_window else (None, None))
    
    plan_query, plan_params = _build_plan_query(routine)
    log_query, log_params = _build_log_query(routine, start_date, end_date)
    
    with DatabaseHandler() as db:
        plan_rows = db.fetch_all(plan_query, plan_params if plan_params else None)
        log_rows = db.fetch_all(log_query, log_params if log_params else None)
        
    effective_totals, raw_totals, selection_to_muscles = _aggregate_muscle_volumes(
        plan_rows, contribution_mode
    )
    
    session_dates = _aggregate_session_dates(log_rows, selection_to_muscles)
    
    return _build_summary_output(
        effective_totals, raw_totals, session_dates, counting_mode, contribution_mode
    )
