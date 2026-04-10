"""Tests for effective sets calculation module.

These tests verify the core effective sets calculation logic including:
- Effort factor (RIR/RPE) calculations
- Rep range factor calculations
- Muscle contribution weighting
- Counting mode toggles
- Contribution mode toggles
- Volume classification and warnings
"""
import pytest

from utils.effective_sets import (
    # Enums
    CountingMode,
    ContributionMode,
    VolumeWarningLevel,
    parse_counting_mode,
    parse_contribution_mode,
    # Core functions
    get_effort_factor,
    get_rep_range_factor,
    calculate_effective_sets,
    get_session_volume_warning,
    get_weekly_volume_class,
    calculate_training_frequency,
    calculate_volume_distribution,
    # Aggregation functions
    aggregate_session_volumes,
    aggregate_weekly_volumes,
    # Formatting functions
    format_volume_summary,
    # Data classes
    EffectiveSetResult,
    SessionVolumeResult,
    # Utility functions
    rpe_to_rir,
    rir_to_rpe,
    # Constants
    DEFAULT_MULTIPLIER,
    EFFORT_FACTOR_BUCKETS,
    REP_RANGE_FACTOR_BUCKETS,
    MUSCLE_CONTRIBUTION_WEIGHTS,
)


# =============================================================================
# Query Parsing Tests
# =============================================================================

class TestQueryParsers:
    """Tests for shared query-parameter parsing helpers."""

    def test_parse_counting_mode_raw_variants(self):
        """Raw values should resolve to RAW mode regardless of case."""
        assert parse_counting_mode("raw") == CountingMode.RAW
        assert parse_counting_mode("RAW") == CountingMode.RAW
        assert parse_counting_mode("RaW") == CountingMode.RAW

    def test_parse_counting_mode_defaults_to_effective(self):
        """Missing or invalid values should default to EFFECTIVE."""
        assert parse_counting_mode("effective") == CountingMode.EFFECTIVE
        assert parse_counting_mode("") == CountingMode.EFFECTIVE
        assert parse_counting_mode(None) == CountingMode.EFFECTIVE
        assert parse_counting_mode("invalid") == CountingMode.EFFECTIVE

    def test_parse_contribution_mode_direct_variants(self):
        """Direct values should resolve to DIRECT_ONLY regardless of case."""
        assert parse_contribution_mode("direct") == ContributionMode.DIRECT_ONLY
        assert parse_contribution_mode("DIRECT") == ContributionMode.DIRECT_ONLY
        assert parse_contribution_mode("DiReCt") == ContributionMode.DIRECT_ONLY

    def test_parse_contribution_mode_defaults_to_total(self):
        """Missing or invalid values should default to TOTAL."""
        assert parse_contribution_mode("total") == ContributionMode.TOTAL
        assert parse_contribution_mode("") == ContributionMode.TOTAL
        assert parse_contribution_mode(None) == ContributionMode.TOTAL
        assert parse_contribution_mode("invalid") == ContributionMode.TOTAL


# =============================================================================
# Effort Factor Tests
# =============================================================================

class TestEffortFactor:
    """Tests for RIR/RPE-based effort factor calculation."""
    
    def test_rir_0_returns_full_credit(self):
        """RIR 0 (failure) should give full credit."""
        assert get_effort_factor(rir=0) == 1.0
    
    def test_rir_1_returns_full_credit(self):
        """RIR 1 should give full credit (near failure)."""
        assert get_effort_factor(rir=1) == 1.0
    
    def test_rir_2_3_returns_moderate_high(self):
        """RIR 2-3 should give moderate-high credit."""
        assert get_effort_factor(rir=2) == 0.85
        assert get_effort_factor(rir=3) == 0.85
    
    def test_rir_4_5_returns_moderate(self):
        """RIR 4-5 should give moderate credit."""
        assert get_effort_factor(rir=4) == 0.70
        assert get_effort_factor(rir=5) == 0.70
    
    def test_rir_6_plus_returns_low(self):
        """RIR 6+ should give lower credit but not zero."""
        assert get_effort_factor(rir=6) == 0.55
        assert get_effort_factor(rir=8) == 0.55
        assert get_effort_factor(rir=10) == 0.55
    
    def test_rpe_conversion_when_rir_missing(self):
        """RPE should be converted to RIR when RIR is missing."""
        # RPE 10 = RIR 0
        assert get_effort_factor(rpe=10.0) == 1.0
        # RPE 9 = RIR 1
        assert get_effort_factor(rpe=9.0) == 1.0
        # RPE 8 = RIR 2
        assert get_effort_factor(rpe=8.0) == 0.85
        # RPE 6 = RIR 4
        assert get_effort_factor(rpe=6.0) == 0.70
    
    def test_rir_preferred_over_rpe(self):
        """RIR should be used when both are provided."""
        # RIR 0 (1.0) should override RPE 6 (0.70)
        assert get_effort_factor(rir=0, rpe=6.0) == 1.0
    
    def test_missing_both_returns_neutral(self):
        """Missing both RIR and RPE should return neutral factor."""
        assert get_effort_factor() == DEFAULT_MULTIPLIER
        assert get_effort_factor(rir=None, rpe=None) == DEFAULT_MULTIPLIER
    
    def test_rir_clamped_to_valid_range(self):
        """RIR values outside [0, 10] should be clamped."""
        # Negative RIR clamped to 0
        assert get_effort_factor(rir=-2) == 1.0
        # RIR > 10 clamped to 10
        assert get_effort_factor(rir=15) == 0.55
    
    def test_does_not_penalize_high_rir_too_aggressively(self):
        """High RIR should not be penalized below 0.5."""
        for rir in range(0, 11):
            factor = get_effort_factor(rir=rir)
            assert factor >= 0.5, f"RIR {rir} penalized too aggressively: {factor}"


# =============================================================================
# Rep Range Factor Tests
# =============================================================================

class TestRepRangeFactor:
    """Tests for rep range factor calculation."""
    
    def test_hypertrophy_optimal_range_full_credit(self):
        """6-20 rep range should get full credit."""
        # Range 6-12
        assert get_rep_range_factor(min_reps=6, max_reps=12) == 1.0
        # Range 8-10
        assert get_rep_range_factor(min_reps=8, max_reps=10) == 1.0
        # Range 12-15
        assert get_rep_range_factor(min_reps=12, max_reps=15) == 1.0
        # Range 15-20
        assert get_rep_range_factor(min_reps=15, max_reps=20) == 1.0
    
    def test_strength_range_slight_reduction(self):
        """1-5 rep range should get slight reduction."""
        assert get_rep_range_factor(min_reps=1, max_reps=5) == 0.85
        assert get_rep_range_factor(min_reps=3, max_reps=5) == 0.85
    
    def test_high_rep_endurance_reduction(self):
        """21-30 rep range should get slight reduction."""
        assert get_rep_range_factor(min_reps=21, max_reps=30) == 0.85
        assert get_rep_range_factor(min_reps=25, max_reps=30) == 0.85
    
    def test_very_high_rep_larger_reduction(self):
        """31+ rep range should get larger reduction."""
        assert get_rep_range_factor(min_reps=31, max_reps=50) == 0.70
    
    def test_missing_rep_range_returns_neutral(self):
        """Missing rep range should return neutral factor."""
        assert get_rep_range_factor() == DEFAULT_MULTIPLIER
        assert get_rep_range_factor(min_reps=None, max_reps=None) == DEFAULT_MULTIPLIER
    
    def test_only_max_reps_provided(self):
        """Should use max_reps when only max is provided."""
        assert get_rep_range_factor(max_reps=10) == 1.0
        assert get_rep_range_factor(max_reps=3) == 0.85
    
    def test_only_min_reps_provided(self):
        """Should use min_reps when only min is provided."""
        assert get_rep_range_factor(min_reps=10) == 1.0
        assert get_rep_range_factor(min_reps=3) == 0.85


# =============================================================================
# Effective Sets Calculation Tests
# =============================================================================

class TestCalculateEffectiveSets:
    """Tests for the core effective sets calculation."""
    
    def test_basic_calculation_with_all_factors(self):
        """Test multiplicative application of all factors."""
        result = calculate_effective_sets(
            sets=4,
            rir=2,  # 0.85 effort factor
            min_rep_range=8,
            max_rep_range=12,  # 1.0 rep range factor
            primary_muscle='Chest',
        )
        
        # 4 * 0.85 * 1.0 = 3.4 effective sets
        assert result.raw_sets == 4.0
        assert result.effort_factor == 0.85
        assert result.rep_range_factor == 1.0
        assert result.effective_sets == pytest.approx(3.4)
        assert result.muscle_contributions['Chest'] == pytest.approx(3.4)
    
    def test_muscle_contribution_weighting(self):
        """Test primary/secondary/tertiary muscle weighting."""
        result = calculate_effective_sets(
            sets=4,
            rir=0,  # 1.0 effort
            min_rep_range=8,
            max_rep_range=12,  # 1.0 rep range
            primary_muscle='Chest',
            secondary_muscle='Triceps',
            tertiary_muscle='Front-Shoulder',
        )
        
        assert result.muscle_contributions['Chest'] == pytest.approx(4.0)  # 4 * 1.0
        assert result.muscle_contributions['Triceps'] == pytest.approx(2.0)  # 4 * 0.5
        assert result.muscle_contributions['Front-Shoulder'] == pytest.approx(1.0)  # 4 * 0.25
    
    def test_raw_counting_mode(self):
        """RAW mode should skip all weighting."""
        result = calculate_effective_sets(
            sets=4,
            rir=5,  # Would be 0.70 in effective mode
            min_rep_range=3,
            max_rep_range=5,  # Would be 0.85 in effective mode
            primary_muscle='Chest',
            counting_mode=CountingMode.RAW,
        )
        
        assert result.effort_factor == DEFAULT_MULTIPLIER
        assert result.rep_range_factor == DEFAULT_MULTIPLIER
        assert result.effective_sets == 4.0  # Raw sets unchanged
        assert result.muscle_contributions['Chest'] == 4.0
    
    def test_direct_only_contribution_mode(self):
        """DIRECT_ONLY mode should only count primary muscle."""
        result = calculate_effective_sets(
            sets=4,
            rir=0,
            min_rep_range=8,
            max_rep_range=12,
            primary_muscle='Chest',
            secondary_muscle='Triceps',
            tertiary_muscle='Front-Shoulder',
            contribution_mode=ContributionMode.DIRECT_ONLY,
        )
        
        assert 'Chest' in result.muscle_contributions
        assert 'Triceps' not in result.muscle_contributions
        assert 'Front-Shoulder' not in result.muscle_contributions
        assert result.muscle_contributions['Chest'] == pytest.approx(4.0)
    
    def test_missing_values_default_to_neutral(self):
        """Missing RIR/RPE and rep ranges should use neutral defaults."""
        result = calculate_effective_sets(
            sets=4,
            primary_muscle='Chest',
        )
        
        assert result.effort_factor == DEFAULT_MULTIPLIER
        assert result.rep_range_factor == DEFAULT_MULTIPLIER
        assert result.effective_sets == 4.0
    
    def test_preserves_raw_sets(self):
        """Raw set count should always be preserved."""
        result = calculate_effective_sets(
            sets=4,
            rir=5,
            min_rep_range=3,
            max_rep_range=5,
            primary_muscle='Chest',
        )
        
        assert result.raw_sets == 4.0
        # Effective sets should be different
        assert result.effective_sets != result.raw_sets


# =============================================================================
# Volume Warning Tests
# =============================================================================

class TestSessionVolumeWarning:
    """Tests for session volume warning levels."""
    
    def test_ok_threshold(self):
        """Volume <= 10 should be OK."""
        assert get_session_volume_warning(0) == VolumeWarningLevel.OK
        assert get_session_volume_warning(5) == VolumeWarningLevel.OK
        assert get_session_volume_warning(9.9) == VolumeWarningLevel.OK
    
    def test_borderline_threshold(self):
        """Volume 10-11 should be BORDERLINE."""
        assert get_session_volume_warning(10) == VolumeWarningLevel.BORDERLINE
        assert get_session_volume_warning(10.5) == VolumeWarningLevel.BORDERLINE
    
    def test_excessive_threshold(self):
        """Volume > 11 should be EXCESSIVE."""
        assert get_session_volume_warning(11) == VolumeWarningLevel.EXCESSIVE
        assert get_session_volume_warning(15) == VolumeWarningLevel.EXCESSIVE
        assert get_session_volume_warning(20) == VolumeWarningLevel.EXCESSIVE


class TestWeeklyVolumeClass:
    """Tests for weekly volume classification."""
    
    def test_low_volume(self):
        """Volume < 10 should be classified as low."""
        assert get_weekly_volume_class(0) == 'low'
        assert get_weekly_volume_class(5) == 'low'
        assert get_weekly_volume_class(9.9) == 'low'
    
    def test_medium_volume(self):
        """Volume 10-20 should be classified as medium."""
        assert get_weekly_volume_class(10) == 'medium'
        assert get_weekly_volume_class(15) == 'medium'
        assert get_weekly_volume_class(19.9) == 'medium'
    
    def test_high_volume(self):
        """Volume 20-30 should be classified as high."""
        assert get_weekly_volume_class(20) == 'high'
        assert get_weekly_volume_class(25) == 'high'
        assert get_weekly_volume_class(29.9) == 'high'
    
    def test_excessive_volume(self):
        """Volume >= 30 should be classified as excessive."""
        assert get_weekly_volume_class(30) == 'excessive'
        assert get_weekly_volume_class(50) == 'excessive'


# =============================================================================
# Frequency & Distribution Tests
# =============================================================================

class TestTrainingFrequency:
    """Tests for training frequency calculation."""
    
    def test_counts_sessions_with_meaningful_volume(self):
        """Should count sessions where effective sets >= 1.0."""
        sessions = [
            ('session1', 5.0),
            ('session2', 3.0),
            ('session3', 0.5),  # Below threshold
        ]
        assert calculate_training_frequency(sessions) == 2
    
    def test_ignores_negligible_contributions(self):
        """Sessions with < 1.0 effective sets should not count."""
        sessions = [
            ('session1', 0.25),
            ('session2', 0.5),
            ('session3', 0.9),
        ]
        assert calculate_training_frequency(sessions) == 0
    
    def test_empty_list_returns_zero(self):
        """Empty session list should return zero frequency."""
        assert calculate_training_frequency([]) == 0


class TestVolumeDistribution:
    """Tests for volume distribution metrics."""
    
    def test_calculates_average_and_max(self):
        """Should correctly calculate avg and max per session."""
        sessions = [4.0, 6.0, 5.0]
        avg, max_vol = calculate_volume_distribution(sessions)
        assert avg == pytest.approx(5.0)
        assert max_vol == 6.0
    
    def test_single_session(self):
        """Single session should have avg = max."""
        sessions = [5.0]
        avg, max_vol = calculate_volume_distribution(sessions)
        assert avg == max_vol == 5.0
    
    def test_empty_list_returns_zeros(self):
        """Empty list should return (0, 0) safely."""
        avg, max_vol = calculate_volume_distribution([])
        assert avg == 0.0
        assert max_vol == 0.0
    
    def test_filters_zero_volumes(self):
        """Should ignore zero-volume sessions."""
        sessions = [4.0, 0.0, 6.0]
        avg, max_vol = calculate_volume_distribution(sessions)
        assert avg == pytest.approx(5.0)  # (4 + 6) / 2
        assert max_vol == 6.0


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Tests for utility conversion functions."""
    
    def test_rpe_to_rir_conversion(self):
        """RPE to RIR conversion should be 10 - RPE."""
        assert rpe_to_rir(10.0) == 0
        assert rpe_to_rir(9.0) == 1
        assert rpe_to_rir(8.0) == 2
        assert rpe_to_rir(7.0) == 3
        assert rpe_to_rir(6.0) == 4
    
    def test_rir_to_rpe_conversion(self):
        """RIR to RPE conversion should be 10 - RIR."""
        assert rir_to_rpe(0) == 10.0
        assert rir_to_rpe(1) == 9.0
        assert rir_to_rpe(2) == 8.0
        assert rir_to_rpe(3) == 7.0


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and failure-safe defaults."""
    
    def test_zero_sets_handled_safely(self):
        """Zero sets should not cause errors."""
        result = calculate_effective_sets(
            sets=0,
            rir=0,
            primary_muscle='Chest',
        )
        assert result.raw_sets == 0.0
        assert result.effective_sets == 0.0
    
    def test_none_muscle_skipped(self):
        """None/empty muscle groups should be skipped safely."""
        result = calculate_effective_sets(
            sets=4,
            primary_muscle='Chest',
            secondary_muscle=None,
            tertiary_muscle='',
        )
        assert 'Chest' in result.muscle_contributions
        assert None not in result.muscle_contributions
        assert '' not in result.muscle_contributions
    
    def test_negative_rir_clamped(self):
        """Negative RIR should be clamped to 0."""
        factor = get_effort_factor(rir=-5)
        assert factor == 1.0  # Same as RIR 0
    
    def test_never_returns_zero_factor(self):
        """Factors should never be zero (would eliminate sets entirely)."""
        # Test all effort factor buckets
        for rir in range(0, 15):
            factor = get_effort_factor(rir=rir)
            assert factor > 0, f"RIR {rir} returned zero factor"
        
        # Test all rep range buckets
        for reps in [3, 8, 15, 25, 40]:
            factor = get_rep_range_factor(min_reps=reps, max_reps=reps)
            assert factor > 0, f"Rep range {reps} returned zero factor"


# =============================================================================
# Integration-style Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_calculation_chain(self):
        """Test complete calculation from raw input to classified output."""
        # Simulate a bench press set: 4x8-12 @ RIR 2
        result = calculate_effective_sets(
            sets=4,
            rir=2,
            min_rep_range=8,
            max_rep_range=12,
            primary_muscle='Chest',
            secondary_muscle='Triceps',
            tertiary_muscle='Front-Shoulder',
        )
        
        # Verify factors applied correctly
        assert result.effort_factor == 0.85  # RIR 2-3 bucket
        assert result.rep_range_factor == 1.0  # Optimal range
        
        # Verify effective sets
        base_effective = 4 * 0.85 * 1.0  # 3.4
        assert result.effective_sets == pytest.approx(base_effective)
        
        # Verify muscle contributions
        assert result.muscle_contributions['Chest'] == pytest.approx(3.4)
        assert result.muscle_contributions['Triceps'] == pytest.approx(1.7)
        assert result.muscle_contributions['Front-Shoulder'] == pytest.approx(0.85)
        
        # Classify the chest volume (session level)
        warning = get_session_volume_warning(3.4)
        assert warning == VolumeWarningLevel.OK
    
    def test_mode_consistency(self):
        """Verify both modes produce consistent structures."""
        raw_result = calculate_effective_sets(
            sets=4,
            rir=2,
            primary_muscle='Chest',
            counting_mode=CountingMode.RAW,
        )
        
        eff_result = calculate_effective_sets(
            sets=4,
            rir=2,
            primary_muscle='Chest',
            counting_mode=CountingMode.EFFECTIVE,
        )
        
        # Both should have same structure
        assert raw_result.raw_sets == eff_result.raw_sets
        assert 'Chest' in raw_result.muscle_contributions
        assert 'Chest' in eff_result.muscle_contributions
        
        # But different effective values
        assert raw_result.effective_sets > eff_result.effective_sets


# =============================================================================
# Aggregate Session Volumes Tests
# =============================================================================

class TestAggregateSessionVolumes:
    """Tests for aggregate_session_volumes function."""

    def test_empty_list_returns_empty_result(self):
        """Empty exercise list should return empty session result."""
        result = aggregate_session_volumes([])
        assert result.routine == ''
        assert result.muscle_volumes == {}
        assert result.raw_muscle_volumes == {}
        assert result.warnings == {}

    def test_single_exercise_aggregation(self):
        """Single exercise should produce correct muscle volumes."""
        ex_result = calculate_effective_sets(
            sets=4, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
            secondary_muscle='Triceps',
        )
        result = aggregate_session_volumes([('Push', ex_result)])

        assert result.routine == 'Push'
        assert result.muscle_volumes['Chest'] == pytest.approx(4.0)
        assert result.muscle_volumes['Triceps'] == pytest.approx(2.0)

    def test_multiple_exercises_same_muscle_summed(self):
        """Multiple exercises targeting same muscle should sum volumes."""
        ex1 = calculate_effective_sets(
            sets=3, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        ex2 = calculate_effective_sets(
            sets=3, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        result = aggregate_session_volumes([('Push', ex1), ('Push', ex2)])

        assert result.muscle_volumes['Chest'] == pytest.approx(6.0)

    def test_warnings_generated_per_muscle(self):
        """Warnings should be generated for each muscle."""
        ex_result = calculate_effective_sets(
            sets=12, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        result = aggregate_session_volumes([('Push', ex_result)])

        assert result.warnings['Chest'] == VolumeWarningLevel.EXCESSIVE

    def test_raw_muscle_volumes_tracked(self):
        """Raw muscle volumes should be tracked alongside effective."""
        ex_result = calculate_effective_sets(
            sets=4, rir=3,  # 0.85 effort factor
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        result = aggregate_session_volumes([('Push', ex_result)])

        # Raw should be higher than effective
        assert result.raw_muscle_volumes['Chest'] > result.muscle_volumes['Chest']
        assert result.raw_muscle_volumes['Chest'] == pytest.approx(4.0)

    def test_routine_name_from_first_exercise(self):
        """Routine name should come from first exercise tuple."""
        ex = calculate_effective_sets(sets=3, rir=0, primary_muscle='Chest')
        result = aggregate_session_volumes([('Workout A', ex)])
        assert result.routine == 'Workout A'

    def test_ok_warning_for_low_volume(self):
        """Low volume muscle should get OK warning level."""
        ex = calculate_effective_sets(
            sets=3, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Biceps',
        )
        result = aggregate_session_volumes([('Pull', ex)])
        assert result.warnings['Biceps'] == VolumeWarningLevel.OK


# =============================================================================
# Aggregate Weekly Volumes Tests
# =============================================================================

class TestAggregateWeeklyVolumes:
    """Tests for aggregate_weekly_volumes function."""

    def test_empty_sessions_returns_empty(self):
        """No sessions should return empty weekly result."""
        result = aggregate_weekly_volumes([])
        assert result.muscle_volumes == {}
        assert result.frequency == {}
        assert result.volume_class == {}

    def test_single_session_aggregation(self):
        """Single session should produce correct weekly totals."""
        ex = calculate_effective_sets(
            sets=4, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        session = aggregate_session_volumes([('Push', ex)])
        result = aggregate_weekly_volumes([session])

        assert result.muscle_volumes['Chest'] == pytest.approx(4.0)
        assert result.frequency['Chest'] == 1
        assert result.volume_class['Chest'] == 'low'

    def test_multiple_sessions_summed(self):
        """Multiple sessions should sum weekly volumes."""
        ex1 = calculate_effective_sets(
            sets=4, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        ex2 = calculate_effective_sets(
            sets=4, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        s1 = aggregate_session_volumes([('Push A', ex1)])
        s2 = aggregate_session_volumes([('Push B', ex2)])
        result = aggregate_weekly_volumes([s1, s2])

        assert result.muscle_volumes['Chest'] == pytest.approx(8.0)
        assert result.frequency['Chest'] == 2

    def test_frequency_ignores_negligible_sessions(self):
        """Sessions with < 1.0 effective sets should not count for frequency."""
        ex_high = calculate_effective_sets(
            sets=4, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        # Tertiary contribution only: 4 * 1.0 * 1.0 * 0.25 = 1.0 (just at threshold)
        ex_low = calculate_effective_sets(
            sets=1, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Back',
            tertiary_muscle='Chest',
        )
        s1 = aggregate_session_volumes([('A', ex_high)])
        s2 = aggregate_session_volumes([('B', ex_low)])
        result = aggregate_weekly_volumes([s1, s2])

        # Session 1: 4.0 effective for Chest (counts)
        # Session 2: 0.25 effective for Chest (does NOT count)
        assert result.frequency['Chest'] == 1

    def test_volume_class_classification(self):
        """Volume class should reflect weekly totals."""
        exercises = [
            calculate_effective_sets(
                sets=6, rir=0,
                min_rep_range=8, max_rep_range=12,
                primary_muscle='Chest',
            )
            for _ in range(4)
        ]
        sessions = [
            aggregate_session_volumes([(f'Day {i}', ex)])
            for i, ex in enumerate(exercises)
        ]
        result = aggregate_weekly_volumes(sessions)

        # 6 * 4 = 24 effective sets -> high
        assert result.volume_class['Chest'] == 'high'

    def test_avg_and_max_sets_per_session(self):
        """Should calculate correct avg and max sets per session."""
        ex1 = calculate_effective_sets(
            sets=4, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        ex2 = calculate_effective_sets(
            sets=6, rir=0,
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        s1 = aggregate_session_volumes([('A', ex1)])
        s2 = aggregate_session_volumes([('B', ex2)])
        result = aggregate_weekly_volumes([s1, s2])

        assert result.avg_sets_per_session['Chest'] == pytest.approx(5.0)
        assert result.max_sets_per_session['Chest'] == pytest.approx(6.0)

    def test_historically_trained_muscles_included(self):
        """Muscles in all_trained_muscles list should appear even with zero volume."""
        result = aggregate_weekly_volumes([], all_trained_muscles=['Chest', 'Back'])

        assert 'Chest' in result.muscle_volumes
        assert 'Back' in result.muscle_volumes
        assert result.muscle_volumes['Chest'] == 0.0
        assert result.frequency['Chest'] == 0
        assert result.volume_class['Chest'] == 'low'

    def test_raw_volumes_tracked_across_sessions(self):
        """Raw volumes should be summed across sessions."""
        ex = calculate_effective_sets(
            sets=4, rir=3,  # 0.85 effort
            min_rep_range=8, max_rep_range=12,
            primary_muscle='Chest',
        )
        s1 = aggregate_session_volumes([('A', ex)])
        s2 = aggregate_session_volumes([('B', ex)])
        result = aggregate_weekly_volumes([s1, s2])

        assert result.raw_muscle_volumes['Chest'] == pytest.approx(8.0)


# =============================================================================
# Format Volume Summary Tests
# =============================================================================

class TestFormatVolumeSummary:
    """Tests for format_volume_summary function."""

    def test_basic_formatting(self):
        """Should produce dict with all expected keys."""
        result = format_volume_summary(
            muscle='Chest',
            effective_sets=12.0,
            raw_sets=15.0,
            frequency=3,
            volume_class='medium',
        )

        assert result['muscle_group'] == 'Chest'
        assert result['effective_sets'] == 12.0
        assert result['raw_sets'] == 15.0
        assert result['frequency'] == 3
        assert result['volume_class'] == 'medium'
        assert result['sets_per_session'] == pytest.approx(4.0)

    def test_sets_per_session_calculation(self):
        """sets_per_session should be effective_sets / frequency."""
        result = format_volume_summary(
            muscle='Back',
            effective_sets=10.0,
            raw_sets=12.0,
            frequency=2,
            volume_class='medium',
        )
        assert result['sets_per_session'] == pytest.approx(5.0)

    def test_zero_frequency_returns_zero_sets_per_session(self):
        """Zero frequency should return 0.0 for sets_per_session."""
        result = format_volume_summary(
            muscle='Chest',
            effective_sets=0.0,
            raw_sets=0.0,
            frequency=0,
            volume_class='low',
        )
        assert result['sets_per_session'] == 0.0

    def test_values_rounded_to_two_decimals(self):
        """Numeric values should be rounded to 2 decimal places."""
        result = format_volume_summary(
            muscle='Chest',
            effective_sets=3.33333,
            raw_sets=4.66666,
            frequency=3,
            volume_class='low',
        )
        assert result['effective_sets'] == 3.33
        assert result['raw_sets'] == 4.67
        assert result['sets_per_session'] == pytest.approx(1.11)
