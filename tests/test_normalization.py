from utils.normalization import (
    clean_token,
    normalize_difficulty,
    normalize_equipment,
    normalize_exercise_row,
    normalize_force,
    normalize_mechanic,
    normalize_muscle,
    normalize_utility,
    split_csv,
    to_title,
)


def test_normalize_force_synonyms():
    assert normalize_force('pull & push') == 'Push/Pull'
    assert normalize_force('Push') == 'Push'
    assert normalize_force(None) is None
    assert normalize_force('Explosive') == 'Explosive'


def test_normalize_mechanic_and_utility():
    assert normalize_mechanic('isolation') == 'Isolation'
    assert normalize_mechanic('Hybrid') == 'Hybrid'
    assert normalize_utility('basic or auxiliary') == 'Basic'
    assert normalize_utility('auxiliary') == 'Auxiliary'


def test_normalize_difficulty_and_equipment():
    assert normalize_difficulty('BEGINNER') == 'Beginner'
    assert normalize_equipment('smith machine') == 'Smith_Machine'
    assert normalize_equipment('barbell') == 'Barbell'
    assert normalize_equipment(None) is None


def test_normalize_muscle_aliases():
    assert normalize_muscle('Deltoid; Anterior') == 'Front-Shoulder'
    assert normalize_muscle('latissimus dorsi') == 'Latissimus Dorsi'
    assert normalize_muscle('Obliques') == 'External Obliques'


def test_split_csv_and_clean_token():
    assert split_csv(' a , b , , c ') == ['a', 'b', 'c']
    assert clean_token('  Mixed   CASE  ') == 'Mixed CASE'
    assert to_title('neutral grip') == 'Neutral Grip'


def test_normalize_exercise_row_deduplicates_isolations():
    raw = {
        'exercise_name': '  incline press  ',
        'primary_muscle_group': 'chest',
        'secondary_muscle_group': 'Triceps',
        'tertiary_muscle_group': 'front shoulder',
        'advanced_isolated_muscles': 'Gluteus Maximus, glutes,  ',
        'utility': 'basic or auxiliary',
        'grips': 'neutral, overhand',
        'stabilizers': None,
        'synergists': None,
        'force': 'pull & push',
        'equipment': 'smith-machine',
        'mechanic': 'isolation',
        'difficulty': 'ADVANCED',
    }

    normalised = normalize_exercise_row(raw)

    assert normalised['exercise_name'] == 'incline press'
    assert normalised['primary_muscle_group'] == 'Chest'
    assert normalised['secondary_muscle_group'] == 'Triceps'
    assert normalised['tertiary_muscle_group'] == 'Front-Shoulder'
    assert normalised['advanced_isolated_muscles'] == 'gluteus-maximus'
    assert normalised['force'] == 'Push/Pull'
    assert normalised['utility'] == 'Basic'
    assert normalised['mechanic'] == 'Isolation'
    assert normalised['difficulty'] == 'Advanced'
    assert normalised['equipment'] == 'Smith_Machine'
    assert normalised['grips'] == 'Neutral, Overhand'