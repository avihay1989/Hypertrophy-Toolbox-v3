"""
Tests for utils/volume_classifier.py - Volume classification utilities.
"""

import pytest
from utils.volume_classifier import (
    get_volume_class,
    get_volume_label,
    get_effective_volume_label,
    get_volume_tooltip,
    get_session_warning_tooltip,
    get_category_tooltip,
    get_subcategory_tooltip,
)
from utils.effective_sets import VolumeWarningLevel


class TestGetVolumeClass:
    """Tests for get_volume_class function (raw sets based)."""

    def test_low_volume_below_10(self):
        """Sets < 10 should be low-volume."""
        assert get_volume_class(0) == "low-volume"
        assert get_volume_class(5) == "low-volume"
        assert get_volume_class(9) == "low-volume"
        assert get_volume_class(9.9) == "low-volume"

    def test_medium_volume_10_to_19(self):
        """Sets 10-19 should be medium-volume."""
        assert get_volume_class(10) == "medium-volume"
        assert get_volume_class(15) == "medium-volume"
        assert get_volume_class(19) == "medium-volume"
        assert get_volume_class(19.9) == "medium-volume"

    def test_high_volume_20_to_29(self):
        """Sets 20-29 should be high-volume."""
        assert get_volume_class(20) == "high-volume"
        assert get_volume_class(25) == "high-volume"
        assert get_volume_class(29) == "high-volume"
        assert get_volume_class(29.9) == "high-volume"

    def test_ultra_volume_30_plus(self):
        """Sets >= 30 should be ultra-volume."""
        assert get_volume_class(30) == "ultra-volume"
        assert get_volume_class(50) == "ultra-volume"
        assert get_volume_class(100) == "ultra-volume"

    def test_handles_float_values(self):
        """Should handle float values correctly."""
        assert get_volume_class(9.5) == "low-volume"
        assert get_volume_class(10.5) == "medium-volume"
        assert get_volume_class(20.5) == "high-volume"
        assert get_volume_class(30.5) == "ultra-volume"


class TestGetVolumeLabel:
    """Tests for get_volume_label function."""

    def test_low_volume_label(self):
        """Sets < 10 should return 'Low Volume'."""
        assert get_volume_label(0) == "Low Volume"
        assert get_volume_label(5) == "Low Volume"
        assert get_volume_label(9) == "Low Volume"

    def test_medium_volume_label(self):
        """Sets 10-19 should return 'Medium Volume'."""
        assert get_volume_label(10) == "Medium Volume"
        assert get_volume_label(15) == "Medium Volume"
        assert get_volume_label(19) == "Medium Volume"

    def test_high_volume_label(self):
        """Sets 20-29 should return 'High Volume'."""
        assert get_volume_label(20) == "High Volume"
        assert get_volume_label(25) == "High Volume"
        assert get_volume_label(29) == "High Volume"

    def test_excessive_volume_label(self):
        """Sets >= 30 should return 'Excessive Volume'."""
        assert get_volume_label(30) == "Excessive Volume"
        assert get_volume_label(50) == "Excessive Volume"


class TestGetEffectiveVolumeLabel:
    """Tests for get_effective_volume_label function."""

    def test_low_effective_volume(self):
        """Low effective sets should return 'Low Volume'."""
        assert get_effective_volume_label(0) == "Low Volume"
        assert get_effective_volume_label(9) == "Low Volume"

    def test_medium_effective_volume(self):
        """Medium effective sets should return 'Medium Volume'."""
        assert get_effective_volume_label(10) == "Medium Volume"
        assert get_effective_volume_label(19) == "Medium Volume"

    def test_high_effective_volume(self):
        """High effective sets should return 'High Volume'."""
        assert get_effective_volume_label(20) == "High Volume"
        assert get_effective_volume_label(29) == "High Volume"

    def test_excessive_effective_volume(self):
        """Excessive effective sets should return 'Excessive Volume'."""
        assert get_effective_volume_label(30) == "Excessive Volume"
        assert get_effective_volume_label(50) == "Excessive Volume"


class TestGetVolumeTooltip:
    """Tests for get_volume_tooltip function."""

    def test_tooltip_includes_label_and_sets(self):
        """Tooltip should include volume label and current sets."""
        tooltip = get_volume_tooltip("Low Volume", 5)
        assert "Low Volume" in tooltip
        assert "5.0" in tooltip

    def test_tooltip_ranges(self):
        """Tooltip should show correct ranges for each label."""
        assert "Below 10 sets" in get_volume_tooltip("Low Volume", 5)
        assert "10-19 sets" in get_volume_tooltip("Medium Volume", 15)
        assert "20-29 sets" in get_volume_tooltip("High Volume", 25)
        assert "30+ sets" in get_volume_tooltip("Excessive Volume", 35)

    def test_tooltip_unknown_label(self):
        """Unknown label should show 'Unknown'."""
        tooltip = get_volume_tooltip("Invalid", 10)
        assert "Unknown" in tooltip

    def test_tooltip_format(self):
        """Tooltip should follow expected format."""
        tooltip = get_volume_tooltip("High Volume", 25.5)
        assert "High Volume: 20-29 sets (Current: 25.5 sets)" == tooltip


class TestGetSessionWarningTooltip:
    """Tests for get_session_warning_tooltip function."""

    def test_ok_warning_tooltip(self):
        """OK warning level should show positive message."""
        tooltip = get_session_warning_tooltip(5.0)
        assert "OK" in tooltip
        assert "5.0" in tooltip
        assert "productive limits" in tooltip.lower()

    def test_borderline_warning_tooltip(self):
        """Borderline warning should indicate approaching limits."""
        # This depends on get_session_volume_warning thresholds
        tooltip = get_session_warning_tooltip(9.5)
        assert "9.5" in tooltip or "effective sets" in tooltip.lower()

    def test_excessive_warning_tooltip(self):
        """Excessive warning should indicate exceeding limits."""
        tooltip = get_session_warning_tooltip(15.0)
        assert "15.0" in tooltip or "effective sets" in tooltip.lower()

    def test_tooltip_includes_effective_sets_value(self):
        """Tooltip should include the effective sets value."""
        tooltip = get_session_warning_tooltip(7.5)
        assert "7.5" in tooltip


class TestGetCategoryTooltip:
    """Tests for get_category_tooltip function."""

    def test_mechanic_tooltip(self):
        """Mechanic category should have joint involvement description."""
        tooltip = get_category_tooltip('Mechanic')
        assert "joint" in tooltip.lower()

    def test_utility_tooltip(self):
        """Utility category should have exercise role description."""
        tooltip = get_category_tooltip('Utility')
        assert "role" in tooltip.lower()

    def test_force_tooltip(self):
        """Force category should have force direction description."""
        tooltip = get_category_tooltip('Force')
        assert "force" in tooltip.lower() or "direction" in tooltip.lower()

    def test_unknown_category_returns_empty(self):
        """Unknown category should return empty string."""
        assert get_category_tooltip('Unknown') == ''
        assert get_category_tooltip('') == ''


class TestGetSubcategoryTooltip:
    """Tests for get_subcategory_tooltip function."""

    # Mechanic subcategories
    def test_compound_subcategory_tooltip(self):
        """Compound (Mechanic) should describe multi-joint exercises."""
        tooltip = get_subcategory_tooltip('Mechanic', 'Compound')
        assert "multi-joint" in tooltip.lower() or "squats" in tooltip.lower()

    def test_isolated_subcategory_tooltip(self):
        """Isolated (Mechanic) should describe single-joint exercises."""
        tooltip = get_subcategory_tooltip('Mechanic', 'Isolated')
        assert "single-joint" in tooltip.lower()

    # Utility subcategories
    def test_auxiliary_subcategory_tooltip(self):
        """Auxiliary (Utility) should describe supportive exercises."""
        tooltip = get_subcategory_tooltip('Utility', 'Auxiliary')
        assert "support" in tooltip.lower()

    def test_basic_subcategory_tooltip(self):
        """Basic (Utility) should describe foundational exercises."""
        tooltip = get_subcategory_tooltip('Utility', 'Basic')
        assert "foundation" in tooltip.lower() or "major" in tooltip.lower()

    # Force subcategories
    def test_push_subcategory_tooltip(self):
        """Push (Force) should describe pushing motions."""
        tooltip = get_subcategory_tooltip('Force', 'Push')
        assert "push" in tooltip.lower()

    def test_pull_subcategory_tooltip(self):
        """Pull (Force) should describe pulling motions."""
        tooltip = get_subcategory_tooltip('Force', 'Pull')
        assert "pull" in tooltip.lower()

    # Unknown combinations
    def test_unknown_category_returns_empty(self):
        """Unknown category should return empty string."""
        assert get_subcategory_tooltip('Unknown', 'Compound') == ''

    def test_unknown_subcategory_returns_empty(self):
        """Unknown subcategory should return empty string."""
        assert get_subcategory_tooltip('Mechanic', 'Unknown') == ''

    def test_both_unknown_returns_empty(self):
        """Both unknown should return empty string."""
        assert get_subcategory_tooltip('Unknown', 'Unknown') == ''


class TestVolumeClassificationConsistency:
    """Tests to ensure volume classification is consistent across functions."""

    def test_class_and_label_align_low(self):
        """Low volume class and label should align."""
        for sets in [0, 5, 9]:
            assert "low" in get_volume_class(sets)
            assert "Low" in get_volume_label(sets)

    def test_class_and_label_align_medium(self):
        """Medium volume class and label should align."""
        for sets in [10, 15, 19]:
            assert "medium" in get_volume_class(sets)
            assert "Medium" in get_volume_label(sets)

    def test_class_and_label_align_high(self):
        """High volume class and label should align."""
        for sets in [20, 25, 29]:
            assert "high" in get_volume_class(sets)
            assert "High" in get_volume_label(sets)

    def test_class_and_label_align_ultra(self):
        """Ultra/Excessive volume class and label should align at 30+ sets."""
        for sets in [30, 40, 50]:
            assert "ultra" in get_volume_class(sets)
            assert "Excessive" in get_volume_label(sets)


class TestBoundaryConditions:
    """Tests for boundary conditions in volume classification."""

    def test_exact_boundary_10(self):
        """Exactly 10 sets should be medium volume."""
        assert get_volume_class(10) == "medium-volume"
        assert get_volume_label(10) == "Medium Volume"

    def test_exact_boundary_20(self):
        """Exactly 20 sets should be high volume."""
        assert get_volume_class(20) == "high-volume"
        assert get_volume_label(20) == "High Volume"

    def test_exact_boundary_30(self):
        """Exactly 30 sets should be ultra/excessive volume."""
        assert get_volume_class(30) == "ultra-volume"
        assert get_volume_label(30) == "Excessive Volume"

    def test_just_below_boundaries(self):
        """Values just below boundaries should be in lower category."""
        assert get_volume_class(9.99) == "low-volume"
        assert get_volume_class(19.99) == "medium-volume"
        assert get_volume_class(29.99) == "high-volume"

    def test_negative_sets_treated_as_low(self):
        """Negative sets (invalid) should still be low volume."""
        assert get_volume_class(-5) == "low-volume"
        assert get_volume_label(-5) == "Low Volume"
