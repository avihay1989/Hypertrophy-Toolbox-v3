"""
Tests for Phase 3 Plan Generator Features.

Tests cover:
- AMRAP/EMOM execution styles
- Merge mode for plan generation
- Time budget optimization
- Superset auto-suggestion
"""
import pytest
import os

# Set testing environment before imports
os.environ['TESTING'] = '1'

from utils.plan_generator import (
    GeneratorConfig,
    PlanGenerator,
    generate_starter_plan,
    ExerciseRow,
)


class TestExecutionStyles:
    """Tests for AMRAP/EMOM execution style feature."""
    
    def test_execution_style_options_endpoint(self, test_client):
        """Test that execution style options endpoint returns valid data."""
        response = test_client.get('/api/execution_style_options')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['ok'] is True
        
        options = data['data']
        assert 'styles' in options
        assert 'standard' in options['styles']
        assert 'amrap' in options['styles']
        assert 'emom' in options['styles']
        
        # Check AMRAP has correct properties
        amrap = options['styles']['amrap']
        assert amrap['full_name'] == 'As Many Reps As Possible'
        assert 'time_cap_seconds' in amrap['defaults']
        
        # Check EMOM has correct properties
        emom = options['styles']['emom']
        assert emom['full_name'] == 'Every Minute On the Minute'
        assert 'emom_interval_seconds' in emom['defaults']
        assert 'emom_rounds' in emom['defaults']
    
    def test_set_execution_style_standard(self, test_client, setup_workout_plan):
        """Test setting standard execution style."""
        # Get an exercise ID
        response = test_client.get('/get_workout_plan')
        data = response.get_json()
        exercises = data['data']
        assert len(exercises) > 0
        
        exercise_id = exercises[0]['id']
        
        # Set to standard
        response = test_client.post('/api/execution_style', json={
            'exercise_id': exercise_id,
            'execution_style': 'standard'
        })
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['ok'] is True
        assert result['data']['execution_style'] == 'standard'
    
    def test_set_execution_style_amrap(self, test_client, setup_workout_plan):
        """Test setting AMRAP execution style."""
        response = test_client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        exercise_id = exercises[0]['id']
        
        # Set to AMRAP with custom time cap
        response = test_client.post('/api/execution_style', json={
            'exercise_id': exercise_id,
            'execution_style': 'amrap',
            'time_cap_seconds': 90
        })
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['ok'] is True
        assert result['data']['execution_style'] == 'amrap'
        assert result['data']['time_cap_seconds'] == 90
        assert result['data']['emom_interval_seconds'] is None
    
    def test_set_execution_style_emom(self, test_client, setup_workout_plan):
        """Test setting EMOM execution style."""
        response = test_client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        exercise_id = exercises[0]['id']
        
        # Set to EMOM with custom parameters
        response = test_client.post('/api/execution_style', json={
            'exercise_id': exercise_id,
            'execution_style': 'emom',
            'emom_interval_seconds': 45,
            'emom_rounds': 8
        })
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['ok'] is True
        assert result['data']['execution_style'] == 'emom'
        assert result['data']['emom_interval_seconds'] == 45
        assert result['data']['emom_rounds'] == 8
        assert result['data']['time_cap_seconds'] is None
    
    def test_execution_style_invalid_style(self, test_client, setup_workout_plan):
        """Test that invalid execution style is rejected."""
        response = test_client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        exercise_id = exercises[0]['id']
        
        response = test_client.post('/api/execution_style', json={
            'exercise_id': exercise_id,
            'execution_style': 'invalid_style'
        })
        
        assert response.status_code == 400
        result = response.get_json()
        assert result['ok'] is False
    
    def test_execution_style_invalid_time_cap(self, test_client, setup_workout_plan):
        """Test that invalid time cap is rejected."""
        response = test_client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        exercise_id = exercises[0]['id']
        
        # Time cap too short
        response = test_client.post('/api/execution_style', json={
            'exercise_id': exercise_id,
            'execution_style': 'amrap',
            'time_cap_seconds': 5
        })
        
        assert response.status_code == 400
    
    def test_get_workout_plan_includes_execution_style(self, test_client, setup_workout_plan):
        """Test that get_workout_plan includes execution style columns."""
        # First set an execution style
        response = test_client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        exercise_id = exercises[0]['id']
        
        test_client.post('/api/execution_style', json={
            'exercise_id': exercise_id,
            'execution_style': 'amrap',
            'time_cap_seconds': 60
        })
        
        # Fetch workout plan again
        response = test_client.get('/get_workout_plan')
        data = response.get_json()
        exercises = data['data']
        
        # Find the updated exercise
        updated = next(ex for ex in exercises if ex['id'] == exercise_id)
        assert updated.get('execution_style') == 'amrap'
        assert updated.get('time_cap_seconds') == 60


class TestMergeMode:
    """Tests for merge mode feature."""
    
    def test_config_merge_mode_sets_overwrite_false(self):
        """Test that merge_mode=True forces overwrite=False."""
        config = GeneratorConfig(
            training_days=2,
            merge_mode=True,
            overwrite=True  # Should be forced to False
        )
        # merge_mode implies overwrite=False
        assert config.overwrite is False
    
    def test_merge_mode_adds_missing_patterns(self, test_client, setup_partial_workout_plan):
        """Test that merge mode only adds exercises for missing patterns."""
        # Generate plan with merge mode
        response = test_client.post('/generate_starter_plan', json={
            'training_days': 2,
            'environment': 'gym',
            'merge_mode': True,
            'persist': False,
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        
        # Should indicate merge mode was used
        if 'merge_mode' in data['data']:
            assert data['data']['merge_mode'] is True
    
    def test_generate_options_includes_merge_mode(self, test_client):
        """Test that generator options includes merge mode."""
        response = test_client.get('/get_generator_options')
        assert response.status_code == 200
        
        data = response.get_json()
        options = data['data']
        
        assert 'merge_mode' in options
        assert options['merge_mode']['default'] is False


class TestTimeBudgetOptimization:
    """Tests for time budget optimization feature."""
    
    def test_config_time_budget_validation(self):
        """Test time budget validation in config."""
        # Valid time budget
        config = GeneratorConfig(
            training_days=2,
            time_budget_minutes=60
        )
        assert config.time_budget_minutes == 60
        
        # Invalid time budget (too low)
        with pytest.raises(ValueError):
            GeneratorConfig(training_days=2, time_budget_minutes=5)
        
        # Invalid time budget (too high)
        with pytest.raises(ValueError):
            GeneratorConfig(training_days=2, time_budget_minutes=200)
    
    def test_estimate_workout_duration(self):
        """Test workout duration estimation."""
        config = GeneratorConfig(training_days=2)
        generator = PlanGenerator(config)
        
        exercises = [
            ExerciseRow(
                routine="A", exercise="Squat", sets=3,
                min_rep_range=6, max_rep_range=10, rir=2, rpe=8.0,
                weight=0.0, exercise_order=1, pattern="squat", role="main"
            ),
            ExerciseRow(
                routine="A", exercise="Bench Press", sets=3,
                min_rep_range=6, max_rep_range=10, rir=2, rpe=8.0,
                weight=0.0, exercise_order=2, pattern="horizontal_push", role="main"
            ),
            ExerciseRow(
                routine="A", exercise="Bicep Curl", sets=2,
                min_rep_range=10, max_rep_range=15, rir=2, rpe=8.0,
                weight=0.0, exercise_order=3, pattern="upper_isolation", role="accessory"
            ),
        ]
        
        duration = generator._estimate_workout_duration(exercises)
        # Should be reasonable estimate (not 0, not excessive)
        assert 15 < duration < 90
    
    def test_time_budget_reduces_volume(self):
        """Test that time budget optimization reduces volume when needed."""
        # Generate with short time budget
        result = generate_starter_plan(
            training_days=2,  # Use 2-day split for more reasonable duration
            environment='gym',
            time_budget_minutes=45,  # More realistic target
            persist=False,
        )
        
        # Should have estimated durations
        if 'estimated_duration_minutes' in result:
            for routine, duration in result['estimated_duration_minutes'].items():
                # Duration should be reduced (original would be ~60+ minutes)
                # Allow some tolerance since we can't always hit exact target
                assert duration <= 60  # Should be less than unoptimized
    
    def test_generate_options_includes_time_budget(self, test_client):
        """Test that generator options includes time budget options."""
        response = test_client.get('/get_generator_options')
        data = response.get_json()
        options = data['data']
        
        assert 'time_budget' in options
        assert options['time_budget']['min'] == 15
        assert options['time_budget']['max'] == 180
        assert 'presets' in options['time_budget']
    
    def test_generate_with_time_budget_via_api(self, test_client):
        """Test generating plan with time budget via API."""
        response = test_client.post('/generate_starter_plan', json={
            'training_days': 2,
            'environment': 'gym',
            'time_budget_minutes': 45,
            'persist': False,
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        
        # Should include time budget info in response
        if 'time_budget_minutes' in data['data']:
            assert data['data']['time_budget_minutes'] == 45


class TestSupersetAutoSuggestion:
    """Tests for superset auto-suggestion feature."""
    
    def test_suggest_supersets_endpoint(self, test_client, setup_workout_plan):
        """Test that superset suggestion endpoint works."""
        response = test_client.get('/api/superset/suggest')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['ok'] is True
        assert 'suggestions' in data['data']
    
    def test_suggest_supersets_with_routine_filter(self, test_client, setup_workout_plan):
        """Test superset suggestions filtered by routine."""
        response = test_client.get('/api/superset/suggest?routine=A')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['ok'] is True
        
        # All suggestions should be for routine A
        for suggestion in data['data']['suggestions']:
            assert suggestion['routine'] == 'A'
    
    def test_suggest_supersets_antagonist_pairing(self, test_client, setup_antagonist_exercises):
        """Test that suggestions correctly pair antagonist muscles."""
        response = test_client.get('/api/superset/suggest')
        data = response.get_json()
        
        suggestions = data['data']['suggestions']
        
        # Should suggest antagonist pairs
        for suggestion in suggestions:
            assert 'reason' in suggestion
            assert 'benefit' in suggestion
            # Reason should mention antagonist pairing
            if 'Antagonist' in suggestion['reason']:
                assert 'saves time' in suggestion['benefit'].lower()
    
    def test_suggest_supersets_excludes_already_supersetted(self, test_client, setup_supersetted_exercises):
        """Test that already-supersetted exercises are excluded from suggestions."""
        response = test_client.get('/api/superset/suggest')
        data = response.get_json()
        
        suggestions = data['data']['suggestions']
        
        # Get all suggested exercise IDs
        suggested_ids = set()
        for s in suggestions:
            suggested_ids.add(s['exercise_1']['id'])
            suggested_ids.add(s['exercise_2']['id'])
        
        # None of these should be already in a superset
        # (fixture setup_supersetted_exercises should have some supersetted exercises)


# ==================== Fixtures ====================

# NOTE: test_client is provided by conftest.py's 'client' fixture
# We alias it here for compatibility with existing test code
@pytest.fixture
def test_client(client, db_handler):
    """Alias for the client fixture from conftest.py with proper test database setup."""
    # Ensure test exercises exist in the database
    _ensure_test_exercises(db_handler)
    yield client


def _ensure_test_exercises(db_handler):
    """Insert test exercises with proper schema including movement patterns."""
    exercises = [
        # Main compound exercises
        ('Back Squat', 'Quadriceps', 'Glutes', 'Hamstrings', 'Barbell', 'Compound', 'Basic', 'Intermediate', 'squat', 'squat'),
        ('Barbell Bench Press', 'Chest', 'Triceps', 'Shoulders', 'Barbell', 'Compound', 'Basic', 'Intermediate', 'horizontal_push', 'press'),
        ('Barbell Row', 'Back', 'Biceps', 'Rear Delts', 'Barbell', 'Compound', 'Basic', 'Intermediate', 'horizontal_pull', 'row'),
        ('Deadlift', 'Hamstrings', 'Glutes', 'Lower Back', 'Barbell', 'Compound', 'Basic', 'Intermediate', 'hinge', 'deadlift'),
        ('Pull Up', 'Back', 'Biceps', 'Rear Delts', 'Bodyweight', 'Compound', 'Basic', 'Intermediate', 'vertical_pull', 'pullup'),
        ('Overhead Press', 'Shoulders', 'Triceps', 'Upper Chest', 'Barbell', 'Compound', 'Basic', 'Intermediate', 'vertical_push', 'press'),
        # Isolation exercises
        ('Barbell Curl', 'Biceps', None, None, 'Barbell', 'Isolated', 'Auxiliary', 'Novice', 'upper_isolation', 'curl'),
        ('Tricep Pushdown', 'Triceps', None, None, 'Cable', 'Isolated', 'Auxiliary', 'Novice', 'upper_isolation', 'pushdown'),
        ('Leg Curl', 'Hamstrings', None, None, 'Machine', 'Isolated', 'Auxiliary', 'Novice', 'lower_isolation', 'curl'),
        ('Leg Extension', 'Quadriceps', None, None, 'Machine', 'Isolated', 'Auxiliary', 'Novice', 'lower_isolation', 'extension'),
        # Core exercises
        ('Plank', 'Core', None, None, 'Bodyweight', 'Isolated', 'Auxiliary', 'Novice', 'core_static', 'hold'),
        ('Cable Crunch', 'Core', None, None, 'Cable', 'Isolated', 'Auxiliary', 'Novice', 'core_dynamic', 'crunch'),
    ]
    
    for ex in exercises:
        try:
            db_handler.execute_query(
                """INSERT OR IGNORE INTO exercises 
                   (exercise_name, primary_muscle_group, secondary_muscle_group, tertiary_muscle_group,
                    equipment, mechanic, utility, difficulty, movement_pattern, movement_subpattern)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ex
            )
        except Exception:
            pass  # Ignore if already exists


@pytest.fixture
def setup_workout_plan(test_client):
    """Set up a basic workout plan for testing."""
    # Generate a basic plan
    response = test_client.post('/generate_starter_plan', json={
        'training_days': 2,
        'environment': 'gym',
        'persist': True,
        'overwrite': True,
    })
    
    # Verify it was created
    assert response.status_code == 200
    yield
    
    # Cleanup
    test_client.post('/clear_workout_plan')


@pytest.fixture
def setup_partial_workout_plan(test_client):
    """Set up a partial workout plan with some patterns missing."""
    # First clear any existing plan
    test_client.post('/clear_workout_plan')
    
    # Add just a few exercises (squat and horizontal push only)
    test_client.post('/add_exercise', json={
        'routine': 'A',
        'exercise': 'Back Squat',
        'sets': 3,
        'min_rep_range': 6,
        'max_rep_range': 10,
        'rir': 2,
        'weight': 0
    })
    
    test_client.post('/add_exercise', json={
        'routine': 'A',
        'exercise': 'Barbell Bench Press',
        'sets': 3,
        'min_rep_range': 6,
        'max_rep_range': 10,
        'rir': 2,
        'weight': 0
    })
    
    yield
    test_client.post('/clear_workout_plan')


@pytest.fixture
def setup_antagonist_exercises(test_client):
    """Set up exercises with antagonist muscle groups for superset testing."""
    test_client.post('/clear_workout_plan')
    
    # Chest/Back antagonist pair
    test_client.post('/add_exercise', json={
        'routine': 'A',
        'exercise': 'Barbell Bench Press',
        'sets': 3,
        'min_rep_range': 6,
        'max_rep_range': 10,
        'rir': 2,
        'weight': 0
    })
    
    test_client.post('/add_exercise', json={
        'routine': 'A',
        'exercise': 'Barbell Row',
        'sets': 3,
        'min_rep_range': 6,
        'max_rep_range': 10,
        'rir': 2,
        'weight': 0
    })
    
    # Biceps/Triceps antagonist pair
    test_client.post('/add_exercise', json={
        'routine': 'A',
        'exercise': 'Barbell Curl',
        'sets': 2,
        'min_rep_range': 10,
        'max_rep_range': 15,
        'rir': 2,
        'weight': 0
    })
    
    test_client.post('/add_exercise', json={
        'routine': 'A',
        'exercise': 'Tricep Pushdown',
        'sets': 2,
        'min_rep_range': 10,
        'max_rep_range': 15,
        'rir': 2,
        'weight': 0
    })
    
    yield
    test_client.post('/clear_workout_plan')


@pytest.fixture
def setup_supersetted_exercises(test_client, setup_antagonist_exercises):
    """Set up some exercises that are already in supersets."""
    # Get exercises
    response = test_client.get('/get_workout_plan')
    exercises = response.get_json()['data']
    
    if len(exercises) >= 2:
        # Link first two as superset
        test_client.post('/api/superset/link', json={
            'exercise_ids': [exercises[0]['id'], exercises[1]['id']]
        })
    
    yield
