import pytest

from utils.exercise_manager import save_exercise, add_exercise
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
    calculate_weekly_summary,
)
from utils.effective_sets import CountingMode, ContributionMode


@pytest.mark.usefixtures('clean_db')
def test_weighted_weekly_summary(db_handler):
    """Test weekly summary with effective sets calculation.
    
    This test verifies that:
    1. Effective sets are calculated correctly with effort/rep range factors
    2. Raw sets are preserved for backward compatibility
    3. Muscle contribution weighting works correctly
    """
    save_exercise(
        {
            'exercise_name': 'Bench Press',
            'primary_muscle_group': 'Chest',
            'secondary_muscle_group': 'Triceps',
            'tertiary_muscle_group': 'Front Shoulder',
            'advanced_isolated_muscles': 'anterior-deltoid, upper-pectoralis',
            'utility': 'basic',
            'grips': 'overhand',
            'stabilizers': None,
            'synergists': None,
            'force': 'push',
            'equipment': 'barbell',
            'mechanic': 'compound',
            'difficulty': 'intermediate',
        }
    )

    response = add_exercise(
        routine='Push Day',
        exercise='Bench Press',
        sets=4,
        min_rep_range=6,
        max_rep_range=8,
        rir=2,  # RIR 2 = 0.85 effort factor
        weight=80.0,
        rpe=8.0,
    )
    assert 'successfully' in response.lower()

    # Test default effective sets mode
    summary = calculate_weekly_summary()
    assert 'Chest' in summary
    chest = summary['Chest']
    
    # With RIR 2 (0.85 factor) and rep range 6-8 (1.0 factor):
    # Effective sets = 4 * 0.85 * 1.0 = 3.4
    assert chest['weekly_sets'] == pytest.approx(3.4)  # Effective sets (primary metric)
    assert chest['raw_weekly_sets'] == pytest.approx(4.0)  # Raw sets preserved
    assert chest['effective_weekly_sets'] == pytest.approx(3.4)  # Explicit effective
    assert chest['sets_per_session'] == pytest.approx(3.4)
    assert chest['status'] == 'low'
    
    # Reps and volume also use effective sets
    # Avg reps = (6+8)/2 = 7, effective sets = 3.4
    assert chest['total_reps'] == pytest.approx(3.4 * 7)  # 23.8
    assert chest['total_volume'] == pytest.approx(3.4 * 7 * 80)  # 1904.0

    # Triceps gets 0.5 muscle contribution + effort factor
    triceps = summary['Triceps']
    # 4 * 0.85 * 1.0 * 0.5 = 1.7
    assert triceps['weekly_sets'] == pytest.approx(1.7)
    assert triceps['raw_weekly_sets'] == pytest.approx(2.0)  # Raw: 4 * 0.5
    
    # Front-Shoulder gets 0.25 muscle contribution
    front_shoulder = summary['Front-Shoulder']
    # 4 * 0.85 * 1.0 * 0.25 = 0.85
    assert front_shoulder['weekly_sets'] == pytest.approx(0.85)
    assert front_shoulder['raw_weekly_sets'] == pytest.approx(1.0)  # Raw: 4 * 0.25

    # Verify mode indicators
    assert chest['counting_mode'] == 'effective'
    assert chest['contribution_mode'] == 'total'

    categories = calculate_exercise_categories()
    category_map = {(row['category'], row['subcategory']): row['total_exercises'] for row in categories}
    assert category_map[('Mechanic', 'Compound')] == 1
    assert category_map[('Utility', 'Basic')] == 1
    assert category_map[('Force', 'Push')] == 1

    isolated = calculate_isolated_muscles_stats()
    iso_map = {row['isolated_muscle']: row for row in isolated}
    assert iso_map['anterior-deltoid']['exercise_count'] == 1
    assert iso_map['anterior-deltoid']['total_sets'] == pytest.approx(4.0)  # Raw sets for isolated


@pytest.mark.usefixtures('clean_db')
def test_weekly_summary_raw_mode(db_handler):
    """Test weekly summary in RAW counting mode (backward compatibility)."""
    save_exercise(
        {
            'exercise_name': 'Bench Press',
            'primary_muscle_group': 'Chest',
            'secondary_muscle_group': 'Triceps',
            'tertiary_muscle_group': 'Front Shoulder',
            'advanced_isolated_muscles': 'anterior-deltoid, upper-pectoralis',
            'utility': 'basic',
            'grips': 'overhand',
            'stabilizers': None,
            'synergists': None,
            'force': 'push',
            'equipment': 'barbell',
            'mechanic': 'compound',
            'difficulty': 'intermediate',
        }
    )

    add_exercise(
        routine='Push Day',
        exercise='Bench Press',
        sets=4,
        min_rep_range=6,
        max_rep_range=8,
        rir=2,
        weight=80.0,
        rpe=8.0,
    )

    # Test RAW mode - should match legacy behavior
    summary = calculate_weekly_summary(counting_mode=CountingMode.RAW)
    chest = summary['Chest']
    
    # RAW mode skips effort/rep range weighting
    assert chest['weekly_sets'] == pytest.approx(4.0)  # Raw sets
    assert chest['raw_weekly_sets'] == pytest.approx(4.0)
    
    triceps = summary['Triceps']
    assert triceps['weekly_sets'] == pytest.approx(2.0)  # 4 * 0.5 muscle contribution
    
    assert summary['Front-Shoulder']['weekly_sets'] == pytest.approx(1.0)  # 4 * 0.25


@pytest.mark.usefixtures('clean_db')
def test_weekly_summary_effective_sets_invariant_across_modes(db_handler):
    """effective_weekly_sets should not change when display mode switches to RAW."""
    save_exercise(
        {
            'exercise_name': 'Incline Press',
            'primary_muscle_group': 'Chest',
            'secondary_muscle_group': None,
            'tertiary_muscle_group': None,
            'advanced_isolated_muscles': None,
            'utility': 'basic',
            'grips': 'overhand',
            'stabilizers': None,
            'synergists': None,
            'force': 'push',
            'equipment': 'barbell',
            'mechanic': 'compound',
            'difficulty': 'intermediate',
        }
    )

    add_exercise(
        routine='Push Day',
        exercise='Incline Press',
        sets=12,
        min_rep_range=8,
        max_rep_range=10,
        rir=2,
        weight=100.0,
        rpe=8.0,
    )

    effective_mode = calculate_weekly_summary(counting_mode=CountingMode.EFFECTIVE)
    raw_mode = calculate_weekly_summary(counting_mode=CountingMode.RAW)

    expected_effective_sets = 12 * 0.85 * 1.0  # RIR 2 + 8-10 reps
    assert effective_mode['Chest']['effective_weekly_sets'] == pytest.approx(expected_effective_sets)
    assert raw_mode['Chest']['effective_weekly_sets'] == pytest.approx(expected_effective_sets)


@pytest.mark.usefixtures('clean_db')
def test_weekly_summary_direct_only_mode(db_handler):
    """Test weekly summary in DIRECT_ONLY contribution mode."""
    save_exercise(
        {
            'exercise_name': 'Bench Press',
            'primary_muscle_group': 'Chest',
            'secondary_muscle_group': 'Triceps',
            'tertiary_muscle_group': 'Front Shoulder',
            'advanced_isolated_muscles': 'anterior-deltoid, upper-pectoralis',
            'utility': 'basic',
            'grips': 'overhand',
            'stabilizers': None,
            'synergists': None,
            'force': 'push',
            'equipment': 'barbell',
            'mechanic': 'compound',
            'difficulty': 'intermediate',
        }
    )

    add_exercise(
        routine='Push Day',
        exercise='Bench Press',
        sets=4,
        min_rep_range=6,
        max_rep_range=8,
        rir=2,
        weight=80.0,
        rpe=8.0,
    )

    # Test DIRECT_ONLY mode - only primary muscle gets credit
    summary = calculate_weekly_summary(contribution_mode=ContributionMode.DIRECT_ONLY)
    
    # Chest (primary) should get full effective sets
    assert 'Chest' in summary
    chest = summary['Chest']
    assert chest['weekly_sets'] == pytest.approx(3.4)  # 4 * 0.85 * 1.0
    
    # Secondary and tertiary muscles should NOT appear
    assert 'Triceps' not in summary
    assert 'Front-Shoulder' not in summary
