"""Aggregations for weekly volume and supporting analytics."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from utils.database import DatabaseHandler
from utils.volume_classifier import get_volume_class
from utils.effective_sets import (
    CountingMode,
    ContributionMode,
    calculate_effective_sets,
    get_weekly_volume_class,
    MUSCLE_CONTRIBUTION_WEIGHTS,
)
from utils.logger import get_logger


STATUS_MAP = {
    'low-volume': 'low',
    'medium-volume': 'medium',
    'high-volume': 'high',
    'ultra-volume': 'excessive',
}

# Map new volume classes to CSS-compatible status
EFFECTIVE_STATUS_MAP = {
    'low': 'low',
    'medium': 'medium',
    'high': 'high',
    'excessive': 'excessive',
}
logger = get_logger()


def calculate_weekly_summary(
    method: Optional[str] = None,
    counting_mode: CountingMode = CountingMode.EFFECTIVE,
    contribution_mode: ContributionMode = ContributionMode.TOTAL,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate weighted weekly set counts per muscle group with effective sets.

    Args:
        method: Optional summary mode retained for backwards compatibility. Current
            implementation ignores the value but accepts inputs like "Total" so
            existing callers do not raise ``TypeError``.
        counting_mode: RAW or EFFECTIVE set counting mode.
        contribution_mode: DIRECT_ONLY or TOTAL muscle contribution mode.
        
    Returns:
        Dictionary mapping muscle groups to their volume statistics including:
        - weekly_sets: Total (effective or raw) sets for the week
        - raw_weekly_sets: Always the raw set count (for reference)
        - effective_weekly_sets: Always the effective set count
        - sets_per_session: Average sets per training session
        - frequency: Number of sessions where muscle got >= 1.0 effective sets
        - status: Volume classification (low/medium/high/excessive)
        - volume_class: CSS class for UI styling
        - total_reps: Weighted rep total
        - total_volume: Weighted volume (sets * reps * weight)
    """
    _ = method  # Method handled implicitly; provided for API compatibility.
    query = """
        SELECT
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
    """

    with DatabaseHandler() as db:
        rows = db.fetch_all(query)

    # Track both effective and raw totals
    effective_totals = defaultdict(lambda: {'sets': 0.0, 'reps': 0.0, 'volume': 0.0})
    raw_totals = defaultdict(lambda: {'sets': 0.0, 'reps': 0.0, 'volume': 0.0})
    sessions_by_muscle: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for row in rows:
        sets = row.get('sets') or 0
        routine = row.get('routine')
        min_rep = row.get('min_rep_range')
        max_rep = row.get('max_rep_range')
        rir = row.get('rir')
        rpe = row.get('rpe')
        load = row.get('weight') or 0
        
        avg_reps = 0.0
        if min_rep is not None and max_rep is not None:
            avg_reps = (min_rep + max_rep) / 2.0
        
        # Effective totals are always computed with effective-mode weighting.
        # The counting_mode toggle only changes which aggregate is presented
        # as the primary `weekly_sets` metric.
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
        
        # Aggregate per-muscle contributions
        contributions = [
            (row.get('primary_muscle_group'), MUSCLE_CONTRIBUTION_WEIGHTS['primary']),
            (row.get('secondary_muscle_group'), MUSCLE_CONTRIBUTION_WEIGHTS['secondary']),
            (row.get('tertiary_muscle_group'), MUSCLE_CONTRIBUTION_WEIGHTS['tertiary']),
        ]
        
        for muscle, weight_factor in contributions:
            if not muscle:
                continue
                
            # Skip secondary/tertiary in direct-only mode
            if contribution_mode == ContributionMode.DIRECT_ONLY:
                if weight_factor != MUSCLE_CONTRIBUTION_WEIGHTS['primary']:
                    continue
                weight_factor = 1.0  # Full credit for primary in direct mode
            
            # Get effective contribution for this muscle
            eff_contribution = eff_result.muscle_contributions.get(muscle, 0.0)
            
            # Raw calculations (always use standard weighting)
            raw_weighted_sets = sets * weight_factor
            raw_weighted_reps = raw_weighted_sets * avg_reps
            raw_weighted_volume = raw_weighted_reps * load
            
            # Effective calculations
            eff_weighted_reps = eff_contribution * avg_reps
            eff_weighted_volume = eff_weighted_reps * load
            
            # Update effective totals
            eff_bucket = effective_totals[muscle]
            eff_bucket['sets'] += eff_contribution
            eff_bucket['reps'] += eff_weighted_reps
            eff_bucket['volume'] += eff_weighted_volume
            
            # Update raw totals (preserve for display/debugging)
            raw_bucket = raw_totals[muscle]
            raw_bucket['sets'] += raw_weighted_sets
            raw_bucket['reps'] += raw_weighted_reps
            raw_bucket['volume'] += raw_weighted_volume
            
            # Track session contributions for frequency calculation
            if routine:
                sessions_by_muscle[muscle][routine] += eff_contribution

    global_sessions = {row.get('routine') for row in rows if row.get('routine')}
    summary: Dict[str, Dict[str, Any]] = {}
    
    for muscle in set(effective_totals.keys()) | set(raw_totals.keys()):
        eff_aggregates = effective_totals[muscle]
        raw_aggregates = raw_totals[muscle]
        
        weekly_eff_sets = eff_aggregates['sets']
        weekly_raw_sets = raw_aggregates['sets']
        
        # Use effective sets as the primary metric (or raw if in RAW mode)
        if counting_mode == CountingMode.RAW:
            weekly_sets = weekly_raw_sets
        else:
            weekly_sets = weekly_eff_sets
        
        # Calculate frequency: sessions where muscle got >= 1.0 effective sets
        muscle_sessions = sessions_by_muscle.get(muscle, {})
        frequency = sum(1 for eff_sets in muscle_sessions.values() if eff_sets >= 1.0)
        
        # Fallback session count for backward compatibility
        session_count = frequency if frequency > 0 else (len(global_sessions) or 1)
        sets_per_session = weekly_sets / session_count if session_count else weekly_sets
        
        # Use effective-sets-based classification
        volume_class_str = get_weekly_volume_class(weekly_eff_sets)
        legacy_volume_class = get_volume_class(weekly_sets)
        
        summary[muscle] = {
            # Primary metrics (mode-dependent)
            'weekly_sets': round(weekly_sets, 2),
            'sets_per_session': round(sets_per_session, 2),
            'status': EFFECTIVE_STATUS_MAP.get(volume_class_str, 'low'),
            'volume_class': legacy_volume_class,  # Keep legacy CSS class
            
            # Always-available metrics
            'raw_weekly_sets': round(weekly_raw_sets, 2),
            'effective_weekly_sets': round(weekly_eff_sets, 2),
            'frequency': frequency,
            'avg_sets_per_session': round(weekly_eff_sets / frequency, 2) if frequency > 0 else 0.0,
            'max_sets_per_session': round(max(muscle_sessions.values()), 2) if muscle_sessions else 0.0,
            
            # Volume totals
            'total_reps': round(eff_aggregates['reps'], 2),
            'total_volume': round(eff_aggregates['volume'], 2),
            'raw_total_reps': round(raw_aggregates['reps'], 2),
            'raw_total_volume': round(raw_aggregates['volume'], 2),
            
            # Mode indicators
            'counting_mode': counting_mode.value,
            'contribution_mode': contribution_mode.value,
        }

    return dict(sorted(summary.items()))


def calculate_exercise_categories() -> List[Dict[str, Any]]:
    """Count distinct exercises per canonical classification bucket."""
    query = """
        SELECT
            us.exercise,
            e.mechanic,
            e.utility,
            e.force,
            e.difficulty
        FROM user_selection us
        JOIN exercises e ON us.exercise = e.exercise_name
    """

    with DatabaseHandler() as db:
        rows = db.fetch_all(query)

    categories = {
        'Mechanic': defaultdict(set),
        'Utility': defaultdict(set),
        'Force': defaultdict(set),
        'Difficulty': defaultdict(set),
    }

    for row in rows:
        exercise = row.get('exercise')
        if not exercise:
            continue
        if row.get('mechanic'):
            categories['Mechanic'][row['mechanic'].title()].add(exercise)
        if row.get('utility'):
            categories['Utility'][row['utility'].title()].add(exercise)
        if row.get('force'):
            categories['Force'][row['force'].title()].add(exercise)
        if row.get('difficulty'):
            categories['Difficulty'][row['difficulty'].title()].add(exercise)

    results: List[Dict[str, Any]] = []
    for category, sub_map in categories.items():
        for subcategory in sorted(sub_map.keys()):
            results.append(
                {
                    'category': category,
                    'subcategory': subcategory,
                    'total_exercises': len(sub_map[subcategory]),
                }
            )
    return results


def calculate_isolated_muscles_stats() -> List[Dict[str, Any]]:
    """
    Calculate statistics for advanced isolated muscles using the mapping table.
    Assumes tables: user_selection us, exercises e, exercise_isolated_muscles eim.
    """
    query = """
    SELECT 
        eim.muscle                          AS isolated_muscle,
        COUNT(DISTINCT us.exercise)         AS exercise_count,
        SUM(us.sets)                        AS total_sets,
        SUM(us.sets * (us.min_rep_range + us.max_rep_range) / 2.0) AS total_reps,
        SUM(us.sets * (us.min_rep_range + us.max_rep_range) / 2.0 * us.weight) AS total_volume
    FROM user_selection us
    JOIN exercises e ON us.exercise = e.exercise_name
    JOIN exercise_isolated_muscles eim ON eim.exercise_name = e.exercise_name
    GROUP BY eim.muscle
    ORDER BY eim.muscle ASC
    """
    try:
        with DatabaseHandler() as db:
            return db.fetch_all(query)
    except Exception as e:
        logger.exception("Error calculating isolated muscles stats: %s", e)
        return []


def calculate_pattern_coverage() -> Dict[str, Any]:
    """
    Analyze movement pattern coverage in the current workout plan.
    
    Returns:
        Dictionary containing:
        - per_routine: Dict mapping routine names to pattern coverage stats
        - total: Aggregated pattern coverage across all routines
        - warnings: List of actionable warnings about missing or imbalanced patterns
        - sets_per_routine: Total sets per routine with min/max warnings
    """
    # Query to get exercise patterns with their sets per routine
    query = """
        SELECT
            us.routine,
            us.exercise,
            us.sets,
            e.movement_pattern,
            e.movement_subpattern,
            e.primary_muscle_group,
            e.mechanic
        FROM user_selection us
        JOIN exercises e ON us.exercise = e.exercise_name
        ORDER BY us.routine
    """
    
    try:
        with DatabaseHandler() as db:
            rows = db.fetch_all(query)
    except Exception as e:
        logger.exception("Error calculating pattern coverage: %s", e)
        return {"per_routine": {}, "total": {}, "warnings": [], "sets_per_routine": {}}
    
    # Core movement patterns that should be present in a balanced program
    CORE_PATTERNS = {
        "squat": "Lower body push (quads, glutes)",
        "hinge": "Lower body pull (hamstrings, glutes, back)",
        "horizontal_push": "Upper body horizontal push (chest, shoulders, triceps)",
        "horizontal_pull": "Upper body horizontal pull (back, biceps)",
        "vertical_push": "Upper body vertical push (shoulders, triceps)",
        "vertical_pull": "Upper body vertical pull (lats, biceps)",
    }
    
    # Track patterns per routine
    per_routine: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_patterns: Dict[str, int] = defaultdict(int)
    sets_per_routine: Dict[str, int] = defaultdict(int)
    
    for row in rows:
        routine = row.get('routine', 'Unknown')
        sets = row.get('sets', 0) or 0
        pattern = row.get('movement_pattern', '')
        
        sets_per_routine[routine] += sets
        
        if pattern:
            per_routine[routine][pattern] += sets
            total_patterns[pattern] += sets
        else:
            # Fallback: classify by mechanic/muscle if no pattern stored
            mechanic = (row.get('mechanic') or '').lower()
            primary_muscle = (row.get('primary_muscle_group') or '').lower()
            
            # Infer pattern from muscle group
            if 'quad' in primary_muscle or 'glute' in primary_muscle:
                inferred = 'squat' if 'quad' in primary_muscle else 'hinge'
            elif 'chest' in primary_muscle:
                inferred = 'horizontal_push'
            elif 'lat' in primary_muscle or 'back' in primary_muscle:
                if mechanic == 'compound':
                    inferred = 'vertical_pull'
                else:
                    inferred = 'horizontal_pull'
            elif 'bicep' in primary_muscle or 'tricep' in primary_muscle:
                inferred = 'upper_isolation'
            elif 'calf' in primary_muscle or 'hamstring' in primary_muscle:
                inferred = 'lower_isolation'
            elif 'core' in primary_muscle or 'abs' in primary_muscle:
                inferred = 'core_dynamic'
            else:
                inferred = 'other'
            
            per_routine[routine][inferred] += sets
            total_patterns[inferred] += sets
    
    # Generate warnings
    warnings: List[Dict[str, str]] = []
    
    # Check for missing core patterns
    for pattern, description in CORE_PATTERNS.items():
        if total_patterns.get(pattern, 0) == 0:
            warnings.append({
                "level": "high",
                "type": "missing_pattern",
                "message": f"Missing {pattern.replace('_', ' ')} exercises",
                "description": f"No {description} exercises found. Consider adding exercises like "
                              f"{'squats, leg press' if pattern == 'squat' else ''}"
                              f"{'deadlifts, hip thrusts' if pattern == 'hinge' else ''}"
                              f"{'bench press, push-ups' if pattern == 'horizontal_push' else ''}"
                              f"{'rows, face pulls' if pattern == 'horizontal_pull' else ''}"
                              f"{'overhead press, dips' if pattern == 'vertical_push' else ''}"
                              f"{'pull-ups, lat pulldowns' if pattern == 'vertical_pull' else ''}.",
            })
    
    # Check sets per routine (ideal: 15-24)
    MIN_SETS = 15
    MAX_SETS = 24
    
    for routine, total_sets in sets_per_routine.items():
        if total_sets < MIN_SETS:
            warnings.append({
                "level": "medium",
                "type": "low_volume",
                "message": f"Routine '{routine}' has only {total_sets} sets",
                "description": f"Consider adding {MIN_SETS - total_sets} more sets. "
                              f"Target is {MIN_SETS}-{MAX_SETS} sets per session for optimal results.",
            })
        elif total_sets > MAX_SETS:
            warnings.append({
                "level": "medium",
                "type": "high_volume",
                "message": f"Routine '{routine}' has {total_sets} sets",
                "description": f"Consider reducing by {total_sets - MAX_SETS} sets. "
                              f"High volume ({MAX_SETS}+ sets) may impair recovery.",
            })
    
    # Check for isolation skew (too much isolation vs compound)
    total_isolation = total_patterns.get('upper_isolation', 0) + total_patterns.get('lower_isolation', 0)
    total_compound = sum(
        total_patterns.get(p, 0) 
        for p in ['squat', 'hinge', 'horizontal_push', 'horizontal_pull', 'vertical_push', 'vertical_pull']
    )
    
    if total_compound > 0 and total_isolation > total_compound * 1.5:
        warnings.append({
            "level": "medium",
            "type": "isolation_skew",
            "message": "High isolation-to-compound ratio",
            "description": f"Isolation work ({total_isolation} sets) significantly exceeds "
                          f"compound work ({total_compound} sets). Consider balancing with more "
                          f"compound movements for better overall development.",
        })
    
    # Check for push/pull imbalance
    total_push = total_patterns.get('horizontal_push', 0) + total_patterns.get('vertical_push', 0)
    total_pull = total_patterns.get('horizontal_pull', 0) + total_patterns.get('vertical_pull', 0)
    
    if total_push > 0 and total_pull > 0:
        ratio = total_push / total_pull if total_pull > 0 else float('inf')
        if ratio > 1.5:
            warnings.append({
                "level": "medium",
                "type": "push_pull_imbalance",
                "message": "Push-dominant program",
                "description": f"Push volume ({total_push} sets) exceeds pull volume ({total_pull} sets) "
                              f"by more than 50%. Consider adding more pulling exercises for shoulder health.",
            })
        elif ratio < 0.67:
            warnings.append({
                "level": "low",
                "type": "push_pull_imbalance",
                "message": "Pull-dominant program",
                "description": f"Pull volume ({total_pull} sets) exceeds push volume ({total_push} sets). "
                              f"This is generally okay but ensure adequate chest/shoulder work.",
            })
    
    return {
        "per_routine": dict(per_routine),
        "total": dict(total_patterns),
        "warnings": warnings,
        "sets_per_routine": dict(sets_per_routine),
        "ideal_sets_range": {"min": MIN_SETS, "max": MAX_SETS},
    }
