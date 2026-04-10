"""Effective Sets Calculation Module.

This module provides the core logic for calculating effective (hypertrophy-relevant)
sets based on effort, rep range, and muscle contribution factors.

All outputs are descriptive, not prescriptive - calculations are informational
and never auto-adjust or block user intent.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Enums & Constants
# =============================================================================

class CountingMode(Enum):
    """Toggle for raw vs effective set counting."""
    RAW = "raw"
    EFFECTIVE = "effective"


class ContributionMode(Enum):
    """Toggle for direct-only vs total (weighted) volume."""
    DIRECT_ONLY = "direct"
    TOTAL = "total"


class VolumeWarningLevel(Enum):
    """Session volume warning classification."""
    OK = "ok"
    BORDERLINE = "borderline"
    EXCESSIVE = "excessive"


def parse_counting_mode(value: Optional[str]) -> CountingMode:
    """Parse counting mode from a request/query value.

    Defaults to EFFECTIVE for missing or unrecognized values.
    """
    if value and value.lower() == "raw":
        return CountingMode.RAW
    return CountingMode.EFFECTIVE


def parse_contribution_mode(value: Optional[str]) -> ContributionMode:
    """Parse contribution mode from a request/query value.

    Defaults to TOTAL for missing or unrecognized values.
    """
    if value and value.lower() == "direct":
        return ContributionMode.DIRECT_ONLY
    return ContributionMode.TOTAL


# Effort factor buckets (RIR-based, discrete buckets)
# RIR 0-1: High effort (near failure) - full credit
# RIR 2-3: Moderate-high effort - slight reduction
# RIR 4-5: Moderate effort - moderate reduction  
# RIR 6+: Low effort - significant reduction (but not eliminated)
EFFORT_FACTOR_BUCKETS: Dict[Tuple[int, int], float] = {
    (0, 1): 1.0,     # Near failure - full stimulus
    (2, 3): 0.85,    # Moderate-high effort
    (4, 5): 0.70,    # Moderate effort
    (6, 10): 0.55,   # Low effort (not "junk" unless explicitly indicated)
}

# Rep range factor buckets (coarse categories)
# Hypertrophy-optimal range (6-20) gets full credit
# Lower rep ranges get slight reduction (still builds muscle)
# Higher rep ranges get slight reduction (more endurance focus)
REP_RANGE_FACTOR_BUCKETS: Dict[Tuple[int, int], float] = {
    (1, 5): 0.85,      # Strength-focused (still hypertrophic, just less optimal)
    (6, 12): 1.0,      # Optimal hypertrophy range
    (13, 20): 1.0,     # Still excellent for hypertrophy
    (21, 30): 0.85,    # Higher rep endurance work
    (31, 100): 0.70,   # Very high rep (diminishing returns)
}

# Muscle contribution weights (primary/secondary/tertiary)
MUSCLE_CONTRIBUTION_WEIGHTS = {
    'primary': 1.0,
    'secondary': 0.5,
    'tertiary': 0.25,
}

# Weekly volume classification thresholds (based on effective sets)
WEEKLY_VOLUME_THRESHOLDS = {
    'low': (0, 10),
    'medium': (10, 20),
    'high': (20, 30),
    'excessive': (30, float('inf')),
}

# Session volume warning thresholds
SESSION_VOLUME_THRESHOLDS = {
    VolumeWarningLevel.OK: (0, 10),
    VolumeWarningLevel.BORDERLINE: (10, 11),
    VolumeWarningLevel.EXCESSIVE: (11, float('inf')),
}

# Default neutral multiplier for missing data
DEFAULT_MULTIPLIER = 1.0


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EffectiveSetResult:
    """Result container for effective set calculation on a single exercise row."""
    raw_sets: float
    effective_sets: float
    effort_factor: float
    rep_range_factor: float
    # Per-muscle effective sets (after contribution weighting)
    muscle_contributions: Dict[str, float]


@dataclass
class SessionVolumeResult:
    """Result container for session-level volume analysis."""
    routine: str
    muscle_volumes: Dict[str, float]  # muscle -> effective sets
    raw_muscle_volumes: Dict[str, float]  # muscle -> raw sets
    warnings: Dict[str, VolumeWarningLevel]  # muscle -> warning level


@dataclass
class WeeklyVolumeResult:
    """Result container for weekly volume analysis."""
    muscle_volumes: Dict[str, float]  # muscle -> total effective sets
    raw_muscle_volumes: Dict[str, float]  # muscle -> total raw sets
    frequency: Dict[str, int]  # muscle -> session count where effective >= 1.0
    avg_sets_per_session: Dict[str, float]
    max_sets_per_session: Dict[str, float]
    volume_class: Dict[str, str]  # muscle -> classification


# =============================================================================
# Core Calculation Functions
# =============================================================================

def get_effort_factor(rir: Optional[int] = None, rpe: Optional[float] = None) -> float:
    """Calculate effort factor from RIR or RPE.
    
    Args:
        rir: Reps In Reserve (0 = failure, higher = easier). Preferred if available.
        rpe: Rate of Perceived Exertion (10 = failure, lower = easier).
    
    Returns:
        Effort multiplier (0.55 to 1.0). Defaults to 1.0 if both missing.
    
    Notes:
        - Prefers RIR when available
        - Converts RPE to RIR if only RPE is provided: RIR = 10 - RPE
        - Uses discrete buckets to avoid over-precision
        - Clamps RIR to valid range [0, 10]
    """
    effective_rir: Optional[int] = None
    
    # Prefer RIR if available
    if rir is not None:
        effective_rir = rir
    elif rpe is not None:
        # Convert RPE to RIR: RPE 10 = RIR 0, RPE 7 = RIR 3, etc.
        effective_rir = int(round(10 - rpe))
    
    # If neither available, return neutral
    if effective_rir is None:
        return DEFAULT_MULTIPLIER
    
    # Clamp to valid range
    effective_rir = max(0, min(10, effective_rir))
    
    # Find matching bucket
    for (low, high), factor in EFFORT_FACTOR_BUCKETS.items():
        if low <= effective_rir <= high:
            return factor
    
    # Fallback (shouldn't reach here due to clamping)
    return DEFAULT_MULTIPLIER


def get_rep_range_factor(
    min_reps: Optional[int] = None, 
    max_reps: Optional[int] = None
) -> float:
    """Calculate rep range factor from min/max rep range.
    
    Args:
        min_reps: Minimum reps in the target range.
        max_reps: Maximum reps in the target range.
    
    Returns:
        Rep range multiplier (0.70 to 1.0). Defaults to 1.0 if unknown.
    
    Notes:
        - Uses coarse categories, not per-rep granularity
        - Based on average of min/max if both provided
        - Hypertrophy-optimal range (6-20) gets full credit
    """
    if min_reps is None and max_reps is None:
        return DEFAULT_MULTIPLIER
    
    # Calculate representative rep count
    if min_reps is not None and max_reps is not None:
        avg_reps = (min_reps + max_reps) / 2.0
    elif max_reps is not None:
        avg_reps = max_reps
    else:
        avg_reps = min_reps  # type: ignore
    
    # Find matching bucket
    for (low, high), factor in REP_RANGE_FACTOR_BUCKETS.items():
        if low <= avg_reps <= high:
            return factor
    
    # Outside all ranges (shouldn't happen with current buckets)
    return DEFAULT_MULTIPLIER


def calculate_effective_sets(
    sets: int,
    rir: Optional[int] = None,
    rpe: Optional[float] = None,
    min_rep_range: Optional[int] = None,
    max_rep_range: Optional[int] = None,
    primary_muscle: Optional[str] = None,
    secondary_muscle: Optional[str] = None,
    tertiary_muscle: Optional[str] = None,
    counting_mode: CountingMode = CountingMode.EFFECTIVE,
    contribution_mode: ContributionMode = ContributionMode.TOTAL,
) -> EffectiveSetResult:
    """Calculate effective sets for a single exercise row.
    
    This is the core calculation that applies:
    1. Effort factor (based on RIR/RPE)
    2. Rep range factor (based on rep targets)
    3. Muscle contribution weighting (primary/secondary/tertiary)
    
    All factors are applied multiplicatively at the per-set level.
    
    Args:
        sets: Raw number of sets performed.
        rir: Reps In Reserve (optional).
        rpe: Rate of Perceived Exertion (optional).
        min_rep_range: Minimum target reps (optional).
        max_rep_range: Maximum target reps (optional).
        primary_muscle: Primary muscle group worked.
        secondary_muscle: Secondary muscle group worked (optional).
        tertiary_muscle: Tertiary muscle group worked (optional).
        counting_mode: RAW or EFFECTIVE set counting.
        contribution_mode: DIRECT_ONLY or TOTAL contribution.
    
    Returns:
        EffectiveSetResult containing raw sets, effective sets, factors,
        and per-muscle contributions.
    """
    raw_sets = float(sets) if sets else 0.0
    
    # In RAW mode, skip all weighting
    if counting_mode == CountingMode.RAW:
        effort_factor = DEFAULT_MULTIPLIER
        rep_range_factor = DEFAULT_MULTIPLIER
        base_effective = raw_sets
    else:
        # Calculate factors
        effort_factor = get_effort_factor(rir, rpe)
        rep_range_factor = get_rep_range_factor(min_rep_range, max_rep_range)
        
        # Apply factors multiplicatively
        base_effective = raw_sets * effort_factor * rep_range_factor
    
    # Calculate per-muscle contributions
    muscle_contributions: Dict[str, float] = {}
    
    muscles = [
        (primary_muscle, MUSCLE_CONTRIBUTION_WEIGHTS['primary']),
        (secondary_muscle, MUSCLE_CONTRIBUTION_WEIGHTS['secondary']),
        (tertiary_muscle, MUSCLE_CONTRIBUTION_WEIGHTS['tertiary']),
    ]
    
    for muscle, weight in muscles:
        if muscle:
            if contribution_mode == ContributionMode.DIRECT_ONLY:
                # Only count primary muscle
                if weight == MUSCLE_CONTRIBUTION_WEIGHTS['primary']:
                    muscle_contributions[muscle] = base_effective
            else:
                # Total contribution mode - apply muscle weighting
                muscle_contributions[muscle] = base_effective * weight
    
    return EffectiveSetResult(
        raw_sets=raw_sets,
        effective_sets=base_effective,
        effort_factor=effort_factor,
        rep_range_factor=rep_range_factor,
        muscle_contributions=muscle_contributions,
    )


def get_session_volume_warning(effective_sets: float) -> VolumeWarningLevel:
    """Get session volume warning level for a muscle.
    
    Args:
        effective_sets: Effective sets for a muscle in a single session.
    
    Returns:
        VolumeWarningLevel indicating if volume is OK, borderline, or excessive.
    
    Notes:
        - Thresholds: ≤10 OK, 10-11 Borderline, >11 Excessive
        - These are soft signals, not errors
        - Does not block execution or override user intent
    """
    for level, (low, high) in SESSION_VOLUME_THRESHOLDS.items():
        if low <= effective_sets < high:
            return level
    
    return VolumeWarningLevel.OK


def get_weekly_volume_class(effective_sets: float) -> str:
    """Classify weekly volume level for a muscle.
    
    Args:
        effective_sets: Total effective sets for a muscle per week.
    
    Returns:
        Classification string: 'low', 'medium', 'high', or 'excessive'.
    
    Notes:
        - Thresholds are static and explicit
        - Classification is informational only, not a target
        - Based on primary effective sets
    """
    for label, (low, high) in WEEKLY_VOLUME_THRESHOLDS.items():
        if low <= effective_sets < high:
            return label
    
    return 'low'


def calculate_training_frequency(
    sessions_with_muscle: List[Tuple[str, float]]
) -> int:
    """Calculate meaningful training frequency for a muscle.
    
    Args:
        sessions_with_muscle: List of (session_id, effective_sets) tuples
            for a specific muscle.
    
    Returns:
        Number of sessions where muscle received >= 1.0 effective sets.
    
    Notes:
        - Multiple exercises in one session count as one frequency hit
        - Ignores sessions with only negligible contribution
        - Sessions with only tertiary contribution count if >= 1.0 effective sets
    """
    return sum(1 for _, eff_sets in sessions_with_muscle if eff_sets >= 1.0)


def calculate_volume_distribution(
    session_volumes: List[float]
) -> Tuple[float, float]:
    """Calculate volume distribution metrics across sessions.
    
    Args:
        session_volumes: List of effective sets per session for a muscle.
    
    Returns:
        Tuple of (average_sets_per_session, max_sets_per_session).
    
    Notes:
        - Based on effective sets
        - If frequency = 1, avg = max
        - If frequency = 0, returns (0.0, 0.0) safely
    """
    if not session_volumes:
        return (0.0, 0.0)
    
    filtered = [v for v in session_volumes if v > 0]
    if not filtered:
        return (0.0, 0.0)
    
    avg_sets = sum(filtered) / len(filtered)
    max_sets = max(filtered)
    
    return (avg_sets, max_sets)


# =============================================================================
# Aggregate Calculation Functions
# =============================================================================

def aggregate_session_volumes(
    exercise_results: List[Tuple[str, EffectiveSetResult]]
) -> SessionVolumeResult:
    """Aggregate effective sets for a single session/routine.
    
    Args:
        exercise_results: List of (routine, EffectiveSetResult) tuples
            for exercises in a session.
    
    Returns:
        SessionVolumeResult with per-muscle volumes and warnings.
    """
    if not exercise_results:
        return SessionVolumeResult(
            routine='',
            muscle_volumes={},
            raw_muscle_volumes={},
            warnings={},
        )
    
    routine = exercise_results[0][0]
    muscle_volumes: Dict[str, float] = {}
    raw_muscle_volumes: Dict[str, float] = {}
    
    for _, result in exercise_results:
        for muscle, eff_sets in result.muscle_contributions.items():
            muscle_volumes[muscle] = muscle_volumes.get(muscle, 0.0) + eff_sets
        
        # Track raw sets per muscle (assuming same contribution structure)
        for muscle, eff_sets in result.muscle_contributions.items():
            # Reverse engineer raw contribution from effective
            if result.effective_sets > 0:
                ratio = eff_sets / result.effective_sets
                raw_contribution = result.raw_sets * ratio
            else:
                raw_contribution = 0.0
            raw_muscle_volumes[muscle] = raw_muscle_volumes.get(muscle, 0.0) + raw_contribution
    
    # Generate warnings
    warnings = {
        muscle: get_session_volume_warning(volume)
        for muscle, volume in muscle_volumes.items()
    }
    
    return SessionVolumeResult(
        routine=routine,
        muscle_volumes=muscle_volumes,
        raw_muscle_volumes=raw_muscle_volumes,
        warnings=warnings,
    )


def aggregate_weekly_volumes(
    session_results: List[SessionVolumeResult],
    all_trained_muscles: Optional[List[str]] = None,
) -> WeeklyVolumeResult:
    """Aggregate session volumes into weekly totals.
    
    Args:
        session_results: List of SessionVolumeResult from individual sessions.
        all_trained_muscles: Optional list of all muscles trained historically
            (to ensure muscles with zero current volume still appear).
    
    Returns:
        WeeklyVolumeResult with weekly totals, frequency, distribution, and classification.
    """
    muscle_volumes: Dict[str, float] = {}
    raw_muscle_volumes: Dict[str, float] = {}
    sessions_per_muscle: Dict[str, List[float]] = {}
    
    # Aggregate across sessions
    for session in session_results:
        for muscle, volume in session.muscle_volumes.items():
            muscle_volumes[muscle] = muscle_volumes.get(muscle, 0.0) + volume
            
            if muscle not in sessions_per_muscle:
                sessions_per_muscle[muscle] = []
            sessions_per_muscle[muscle].append(volume)
        
        for muscle, raw_vol in session.raw_muscle_volumes.items():
            raw_muscle_volumes[muscle] = raw_muscle_volumes.get(muscle, 0.0) + raw_vol
    
    # Include historically trained muscles with zero volume
    if all_trained_muscles:
        for muscle in all_trained_muscles:
            if muscle not in muscle_volumes:
                muscle_volumes[muscle] = 0.0
                raw_muscle_volumes[muscle] = 0.0
                sessions_per_muscle[muscle] = []
    
    # Calculate frequency (sessions with >= 1.0 effective sets)
    frequency: Dict[str, int] = {}
    for muscle, session_vols in sessions_per_muscle.items():
        frequency[muscle] = sum(1 for v in session_vols if v >= 1.0)
    
    # Calculate distribution metrics
    avg_sets_per_session: Dict[str, float] = {}
    max_sets_per_session: Dict[str, float] = {}
    for muscle, session_vols in sessions_per_muscle.items():
        avg, max_vol = calculate_volume_distribution(session_vols)
        avg_sets_per_session[muscle] = avg
        max_sets_per_session[muscle] = max_vol
    
    # Classify weekly volumes
    volume_class: Dict[str, str] = {
        muscle: get_weekly_volume_class(volume)
        for muscle, volume in muscle_volumes.items()
    }
    
    return WeeklyVolumeResult(
        muscle_volumes=muscle_volumes,
        raw_muscle_volumes=raw_muscle_volumes,
        frequency=frequency,
        avg_sets_per_session=avg_sets_per_session,
        max_sets_per_session=max_sets_per_session,
        volume_class=volume_class,
    )


# =============================================================================
# Utility Functions
# =============================================================================

def rpe_to_rir(rpe: float) -> int:
    """Convert RPE to RIR.
    
    Args:
        rpe: Rate of Perceived Exertion (1-10 scale, 10 = failure).
    
    Returns:
        Estimated RIR (Reps In Reserve).
    """
    return int(round(10 - rpe))


def rir_to_rpe(rir: int) -> float:
    """Convert RIR to RPE.
    
    Args:
        rir: Reps In Reserve (0 = failure).
    
    Returns:
        Estimated RPE.
    """
    return 10.0 - rir


def format_volume_summary(
    muscle: str,
    effective_sets: float,
    raw_sets: float,
    frequency: int,
    volume_class: str,
) -> Dict[str, Any]:
    """Format volume data for API response.
    
    Args:
        muscle: Muscle group name.
        effective_sets: Total effective sets.
        raw_sets: Total raw sets.
        frequency: Training frequency (sessions).
        volume_class: Volume classification.
    
    Returns:
        Dictionary suitable for JSON serialization.
    """
    return {
        'muscle_group': muscle,
        'effective_sets': round(effective_sets, 2),
        'raw_sets': round(raw_sets, 2),
        'frequency': frequency,
        'volume_class': volume_class,
        'sets_per_session': round(effective_sets / frequency, 2) if frequency > 0 else 0.0,
    }
