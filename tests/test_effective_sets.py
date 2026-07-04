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
    # Utility functions
    rpe_to_rir,
    rir_to_rpe,
    # Constants
    DEFAULT_MULTIPLIER,
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
