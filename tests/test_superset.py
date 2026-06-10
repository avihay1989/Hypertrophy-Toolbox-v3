"""
Tests for the Superset feature.

Tests the ability to link/unlink exercises as supersets within the same routine.
"""


class TestSupersetLinkEndpoint:
    """Tests for POST /api/superset/link endpoint."""
    
    def test_link_superset_success(self, client, exercise_factory, workout_plan_factory):
        """Test successfully linking 2 exercises as a superset."""
        # Create 2 exercises in the same routine
        exercise_factory("Barbell Squat", primary_muscle_group="Quadriceps", equipment="Barbell")
        exercise_factory("Calf Raises", primary_muscle_group="Calves", equipment="Machine")
        
        id1 = workout_plan_factory(exercise_name="Barbell Squat", routine="A")
        id2 = workout_plan_factory(exercise_name="Calf Raises", routine="A")
        
        response = client.post('/api/superset/link', json={
            'exercise_ids': [id1, id2]
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert 'superset_group' in data['data']
        assert data['data']['superset_group'].startswith('SS-A-')
        assert len(data['data']['exercises']) == 2
    
    def test_link_superset_different_routines_fails(self, client, exercise_factory, workout_plan_factory):
        """Test that linking exercises from different routines fails."""
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        exercise_factory("Lat Pulldown", primary_muscle_group="Lats")
        
        id1 = workout_plan_factory(exercise_name="Bench Press", routine="A")
        id2 = workout_plan_factory(exercise_name="Lat Pulldown", routine="B")
        
        response = client.post('/api/superset/link', json={
            'exercise_ids': [id1, id2]
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert 'same routine' in data['error']['message'].lower()
    
    def test_link_superset_requires_exactly_two_exercises(self, client, exercise_factory, workout_plan_factory):
        """Test that exactly 2 exercise IDs are required."""
        exercise_factory("Exercise1", primary_muscle_group="Chest")
        
        id1 = workout_plan_factory(exercise_name="Exercise1", routine="A")
        
        # Test with 1 exercise
        response = client.post('/api/superset/link', json={
            'exercise_ids': [id1]
        })
        assert response.status_code == 400
        assert 'exactly 2' in response.get_json()['error']['message'].lower()
        
        # Test with 3 exercises
        exercise_factory("Exercise2", primary_muscle_group="Chest")
        exercise_factory("Exercise3", primary_muscle_group="Chest")
        id2 = workout_plan_factory(exercise_name="Exercise2", routine="A")
        id3 = workout_plan_factory(exercise_name="Exercise3", routine="A")
        
        response = client.post('/api/superset/link', json={
            'exercise_ids': [id1, id2, id3]
        })
        assert response.status_code == 400
    
    def test_link_superset_already_in_superset_fails(self, client, exercise_factory, workout_plan_factory):
        """Test that an exercise already in a superset cannot be linked again."""
        exercise_factory("Ex1", primary_muscle_group="Chest")
        exercise_factory("Ex2", primary_muscle_group="Chest")
        exercise_factory("Ex3", primary_muscle_group="Chest")
        
        id1 = workout_plan_factory(exercise_name="Ex1", routine="A")
        id2 = workout_plan_factory(exercise_name="Ex2", routine="A")
        id3 = workout_plan_factory(exercise_name="Ex3", routine="A")
        
        # First link Ex1 and Ex2
        response = client.post('/api/superset/link', json={
            'exercise_ids': [id1, id2]
        })
        assert response.status_code == 200
        
        # Try to link Ex1 with Ex3 (Ex1 is already in a superset)
        response = client.post('/api/superset/link', json={
            'exercise_ids': [id1, id3]
        })
        assert response.status_code == 400
        assert 'already in a superset' in response.get_json()['error']['message'].lower()
    
    def test_link_superset_exercise_not_found(self, client):
        """Test linking with non-existent exercise IDs."""
        response = client.post('/api/superset/link', json={
            'exercise_ids': [99999, 99998]
        })
        assert response.status_code == 404


class TestSupersetUnlinkEndpoint:
    """Tests for POST /api/superset/unlink endpoint."""
    
    def test_unlink_superset_by_exercise_id(self, client, exercise_factory, workout_plan_factory):
        """Test unlinking a superset by providing an exercise ID."""
        exercise_factory("ExA", primary_muscle_group="Chest")
        exercise_factory("ExB", primary_muscle_group="Chest")
        
        id1 = workout_plan_factory(exercise_name="ExA", routine="A")
        id2 = workout_plan_factory(exercise_name="ExB", routine="A")
        
        # First link them
        client.post('/api/superset/link', json={'exercise_ids': [id1, id2]})
        
        # Now unlink by exercise_id
        response = client.post('/api/superset/unlink', json={
            'exercise_id': id1
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert len(data['data']['unlinked_ids']) == 2
        assert id1 in data['data']['unlinked_ids']
        assert id2 in data['data']['unlinked_ids']
    
    def test_unlink_exercise_not_in_superset(self, client, exercise_factory, workout_plan_factory):
        """Test unlinking an exercise that's not in a superset."""
        exercise_factory("Solo", primary_muscle_group="Chest")
        id1 = workout_plan_factory(exercise_name="Solo", routine="A")
        
        response = client.post('/api/superset/unlink', json={
            'exercise_id': id1
        })
        
        assert response.status_code == 400
        assert 'not in a superset' in response.get_json()['error']['message'].lower()
    
    def test_unlink_requires_exercise_id_or_superset_group(self, client):
        """Test that either exercise_id or superset_group is required."""
        response = client.post('/api/superset/unlink', 
                               json={'some_other_field': 'value'},
                               content_type='application/json')
        
        assert response.status_code == 400
        assert 'required' in response.get_json()['error']['message'].lower()


class TestSupersetInWorkoutPlan:
    """Tests for superset data in get_workout_plan endpoint."""
    
    def test_get_workout_plan_includes_superset_group(self, client, exercise_factory, workout_plan_factory):
        """Test that get_workout_plan returns superset_group field."""
        exercise_factory("Push1", primary_muscle_group="Chest")
        exercise_factory("Push2", primary_muscle_group="Triceps")
        
        id1 = workout_plan_factory(exercise_name="Push1", routine="Push")
        id2 = workout_plan_factory(exercise_name="Push2", routine="Push")
        
        # Link as superset
        client.post('/api/superset/link', json={'exercise_ids': [id1, id2]})
        
        # Get workout plan
        response = client.get('/get_workout_plan')
        assert response.status_code == 200
        
        data = response.get_json()
        exercises = data['data']
        
        # Find the linked exercises
        linked = [e for e in exercises if e.get('superset_group')]
        assert len(linked) == 2
        assert linked[0]['superset_group'] == linked[1]['superset_group']


class TestSupersetRemoveExercise:
    """Tests for removing exercises that are part of a superset."""
    
    def test_remove_exercise_unlinks_partner(self, client, exercise_factory, workout_plan_factory):
        """Test that removing one exercise from a superset unlinks the partner."""
        exercise_factory("Removed", primary_muscle_group="Chest")
        exercise_factory("Kept", primary_muscle_group="Chest")
        
        id1 = workout_plan_factory(exercise_name="Removed", routine="A")
        id2 = workout_plan_factory(exercise_name="Kept", routine="A")
        
        # Link as superset
        client.post('/api/superset/link', json={'exercise_ids': [id1, id2]})
        
        # Remove one exercise
        response = client.post('/remove_exercise', json={'id': id1})
        assert response.status_code == 200
        
        # Verify the partner is still there but no longer in a superset
        response = client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        
        assert len(exercises) == 1
        assert exercises[0]['id'] == id2
        assert exercises[0].get('superset_group') is None


class TestSupersetBackupRestore:
    """Tests for superset data persistence in backup/restore."""
    
    def test_backup_includes_superset_group(self, client, exercise_factory, workout_plan_factory):
        """Test that program backup includes superset_group data."""
        exercise_factory("BackupEx1", primary_muscle_group="Chest")
        exercise_factory("BackupEx2", primary_muscle_group="Chest")
        
        id1 = workout_plan_factory(exercise_name="BackupEx1", routine="A")
        id2 = workout_plan_factory(exercise_name="BackupEx2", routine="A")
        
        # Link as superset
        link_response = client.post('/api/superset/link', json={'exercise_ids': [id1, id2]})
        assert link_response.status_code == 200
        superset_group = link_response.get_json()['data']['superset_group']
        
        # Create backup (using correct endpoint)
        backup_response = client.post('/api/backups', json={'name': 'superset_test_backup'})
        assert backup_response.status_code == 200
        backup_id = backup_response.get_json()['data']['id']
        
        # Clear workout plan
        client.post('/clear_workout_plan')
        
        # Restore backup (using correct endpoint)
        restore_response = client.post(f'/api/backups/{backup_id}/restore')
        assert restore_response.status_code == 200
        
        # Verify superset is restored
        response = client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        
        linked = [e for e in exercises if e.get('superset_group')]
        assert len(linked) == 2
        # The superset_group value should be preserved
        assert linked[0]['superset_group'] == linked[1]['superset_group']


class TestSupersetWithPlanGenerator:
    """Tests for superset preservation with plan generation."""
    
    def test_generate_plan_overwrite_clears_supersets(self, client, exercise_factory, workout_plan_factory):
        """Test that generating a plan with overwrite=True clears supersets in affected routines."""
        # Create exercises
        exercise_factory("Ex1", primary_muscle_group="Chest")
        exercise_factory("Ex2", primary_muscle_group="Chest")
        
        # Add to routine A and create a superset
        id1 = workout_plan_factory(exercise_name="Ex1", routine="A")
        id2 = workout_plan_factory(exercise_name="Ex2", routine="A")
        
        link_response = client.post('/api/superset/link', json={'exercise_ids': [id1, id2]})
        assert link_response.status_code == 200
        
        # Generate a plan with overwrite=True for routine A
        # This should clear the existing routine and thus the supersets
        from utils.plan_generator import generate_starter_plan
        result = generate_starter_plan(
            training_days=1,
            environment="gym",
            persist=True,
            overwrite=True,
        )
        
        # Verify the old superset exercises are gone (overwritten)
        response = client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        
        # The old exercises should be replaced
        old_ids = {id1, id2}
        current_ids = {e['id'] for e in exercises}
        # Old IDs should not be in current plan (they were overwritten)
        assert old_ids.isdisjoint(current_ids), "Old superset exercises should be overwritten"
    
    def test_generate_plan_no_overwrite_preserves_existing_supersets(self, client, exercise_factory, workout_plan_factory):
        """Test that generating a plan with overwrite=False preserves supersets in other routines."""
        # Create exercises
        exercise_factory("Existing1", primary_muscle_group="Chest")
        exercise_factory("Existing2", primary_muscle_group="Chest")
        
        # Add to routine X (not A/B/C which the generator uses) and create a superset
        id1 = workout_plan_factory(exercise_name="Existing1", routine="X")
        id2 = workout_plan_factory(exercise_name="Existing2", routine="X")
        
        link_response = client.post('/api/superset/link', json={'exercise_ids': [id1, id2]})
        assert link_response.status_code == 200
        superset_group = link_response.get_json()['data']['superset_group']
        
        # Generate a plan with overwrite=False
        # This should NOT affect routine X's supersets
        from utils.plan_generator import generate_starter_plan
        result = generate_starter_plan(
            training_days=1,
            environment="gym",
            persist=True,
            overwrite=False,  # Don't overwrite
        )
        
        # Verify the superset in routine X is still intact
        response = client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        
        routine_x_exercises = [e for e in exercises if e.get('routine') == 'X']
        assert len(routine_x_exercises) == 2
        
        supersetted = [e for e in routine_x_exercises if e.get('superset_group')]
        assert len(supersetted) == 2
        assert supersetted[0]['superset_group'] == superset_group
        assert supersetted[1]['superset_group'] == superset_group


class TestSupersetReorder:
    """Tests for superset preservation when reordering exercises."""
    
    def test_reorder_preserves_superset_group(self, client, exercise_factory, workout_plan_factory):
        """Test that reordering exercises preserves their superset_group values."""
        exercise_factory("ReorderEx1", primary_muscle_group="Chest")
        exercise_factory("ReorderEx2", primary_muscle_group="Chest")
        exercise_factory("ReorderEx3", primary_muscle_group="Back")
        
        id1 = workout_plan_factory(exercise_name="ReorderEx1", routine="A")
        id2 = workout_plan_factory(exercise_name="ReorderEx2", routine="A")
        id3 = workout_plan_factory(exercise_name="ReorderEx3", routine="A")
        
        # Link first two as superset
        link_response = client.post('/api/superset/link', json={'exercise_ids': [id1, id2]})
        assert link_response.status_code == 200
        superset_group = link_response.get_json()['data']['superset_group']
        
        # Reorder exercises (simulate drag & drop)
        reorder_response = client.post('/update_exercise_order', json=[
            {'id': id3, 'order': 1},  # Move Ex3 to first
            {'id': id1, 'order': 2},  # Ex1 second
            {'id': id2, 'order': 3},  # Ex2 third
        ])
        assert reorder_response.status_code == 200
        
        # Verify superset is still intact
        response = client.get('/get_workout_plan')
        exercises = response.get_json()['data']
        
        ex1_data = next(e for e in exercises if e['id'] == id1)
        ex2_data = next(e for e in exercises if e['id'] == id2)
        ex3_data = next(e for e in exercises if e['id'] == id3)
        
        # Superset should still be linked
        assert ex1_data.get('superset_group') == superset_group
        assert ex2_data.get('superset_group') == superset_group
        # Ex3 was never in a superset
        assert ex3_data.get('superset_group') is None