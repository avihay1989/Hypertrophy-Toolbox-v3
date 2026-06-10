"""
Tests for Program Backup / Program Library functionality.

Tests cover:
1. Creating backups saves active program data
2. Restoring backups (replace mode)
3. Restoring skips missing exercises
4. Deleting backups removes them
5. Erase/reset integration with auto-backup
"""
import pytest
import sqlite3
from datetime import datetime
import utils.program_backup as program_backup_module
from utils.program_backup import (
    create_backup,
    list_backups,
    get_backup_details,
    restore_backup,
    delete_backup,
    create_auto_backup_before_erase,
    get_latest_auto_backup,
    get_active_program_count,
    BACKUP_SCHEMA_VERSION,
)
from utils.database import DatabaseHandler
from routes.workout_plan import initialize_exercise_order, column_exists


class TestProgramBackup:
    """Test suite for program backup functionality."""
    
    # -------------------------------------------------------------------------
    # Test 1: Create backup saves active program data
    # -------------------------------------------------------------------------
    
    def test_create_backup_saves_active_program_data(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that creating a backup correctly captures active program data."""
        # Seed exercises
        ex1 = exercise_factory("Bench Press", primary_muscle_group="Chest")
        ex2 = exercise_factory("Squat", primary_muscle_group="Quadriceps")
        ex3 = exercise_factory("Deadlift", primary_muscle_group="Back")
        
        # Seed active program selections
        workout_plan_factory(exercise_name=ex1, routine="Workout A", sets=3, min_rep_range=6, max_rep_range=8, weight=100.0)
        workout_plan_factory(exercise_name=ex2, routine="Workout A", sets=4, min_rep_range=8, max_rep_range=10, weight=120.0)
        workout_plan_factory(exercise_name=ex3, routine="Workout B", sets=3, min_rep_range=5, max_rep_range=5, weight=150.0)
        
        # Create backup
        backup = create_backup(name="Test Backup", note="Test note")
        
        # Assert backup exists
        assert backup is not None
        assert backup['id'] is not None
        assert backup['name'] == "Test Backup"
        assert backup['note'] == "Test note"
        assert backup['backup_type'] == "manual"
        assert backup['schema_version'] == BACKUP_SCHEMA_VERSION
        assert backup['item_count'] == 3  # Three exercises
        
        # Verify backup items match expected fields
        details = get_backup_details(backup['id'])
        assert details is not None
        assert len(details['items']) == 3
        
        # Check specific item fields
        item_exercises = {item['exercise'] for item in details['items']}
        assert item_exercises == {"Bench Press", "Squat", "Deadlift"}
        
        # Verify all fields are captured
        bench_item = next(item for item in details['items'] if item['exercise'] == "Bench Press")
        assert bench_item['routine'] == "Workout A"
        assert bench_item['sets'] == 3
        assert bench_item['min_rep_range'] == 6
        assert bench_item['max_rep_range'] == 8
        assert bench_item['weight'] == 100.0
    
    def test_create_backup_with_empty_program(self, clean_db):
        """Test that creating a backup with empty program creates empty backup."""
        backup = create_backup(name="Empty Backup")
        
        assert backup is not None
        assert backup['item_count'] == 0
        
        details = get_backup_details(backup['id'])
        assert details is not None
        assert len(details['items']) == 0
    
    def test_create_backup_requires_name(self, clean_db):
        """Test that backup name is required."""
        with pytest.raises(ValueError, match="Backup name is required"):
            create_backup(name="")
        
        with pytest.raises(ValueError, match="Backup name is required"):
            create_backup(name="   ")
    
    def test_list_backups_returns_all_backups(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that list_backups returns all created backups."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        # Create multiple backups
        create_backup(name="Backup 1")
        create_backup(name="Backup 2")
        create_backup(name="Backup 3")
        
        backups = list_backups()
        
        assert len(backups) == 3
        names = {b['name'] for b in backups}
        assert names == {"Backup 1", "Backup 2", "Backup 3"}
    
    # -------------------------------------------------------------------------
    # Test 2: Restore backup (replace mode)
    # -------------------------------------------------------------------------
    
    def test_restore_backup_replaces_active_program(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that restoring a backup replaces the current active program."""
        # Create initial exercises and program
        ex1 = exercise_factory("Bench Press", primary_muscle_group="Chest")
        ex2 = exercise_factory("Squat", primary_muscle_group="Quadriceps")
        
        workout_plan_factory(exercise_name=ex1, routine="Workout A", sets=3, weight=100.0)
        workout_plan_factory(exercise_name=ex2, routine="Workout A", sets=4, weight=120.0)
        
        # Create backup
        backup = create_backup(name="Original Program")
        
        # Mutate active program
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM user_selection")
            # Add different exercises
            ex3 = exercise_factory("Deadlift", primary_muscle_group="Back")
            workout_plan_factory(exercise_name=ex3, routine="Workout B", sets=5, weight=180.0)
        
        # Verify mutation
        assert get_active_program_count() == 1
        
        # Restore backup
        result = restore_backup(backup['id'])
        
        assert result['restored_count'] == 2
        assert result['backup_name'] == "Original Program"
        assert len(result['skipped']) == 0
        
        # Verify active program equals backup snapshot
        with DatabaseHandler() as db:
            rows = db.fetch_all("SELECT exercise, sets, weight FROM user_selection ORDER BY exercise")
            assert len(rows) == 2
            
            exercises = {row['exercise']: row for row in rows}
            assert "Bench Press" in exercises
            assert "Squat" in exercises
            assert exercises["Bench Press"]['sets'] == 3
            assert exercises["Bench Press"]['weight'] == 100.0
            assert exercises["Squat"]['sets'] == 4
            assert exercises["Squat"]['weight'] == 120.0

    def test_restore_rollback_preserves_active_program_on_failure(
        self,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """Test that restore rolls back cleanly when an insert fails."""
        ex1 = exercise_factory("Exercise A", primary_muscle_group="Chest")
        ex2 = exercise_factory("Exercise B", primary_muscle_group="Back")
        ex3 = exercise_factory("Exercise C", primary_muscle_group="Legs")
        ex4 = exercise_factory("Exercise D", primary_muscle_group="Shoulders")

        workout_plan_factory(exercise_name=ex1, routine="Workout A", sets=3, weight=100.0)
        workout_plan_factory(exercise_name=ex2, routine="Workout A", sets=4, weight=110.0)
        workout_plan_factory(exercise_name=ex3, routine="Workout A", sets=5, weight=120.0)

        backup = create_backup(name="Rollback Program")

        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM user_selection")
            workout_plan_factory(exercise_name=ex3, routine="Workout B", sets=2, weight=130.0)
            workout_plan_factory(exercise_name=ex4, routine="Workout B", sets=2, weight=140.0)

        original_execute_query = DatabaseHandler.execute_query
        insert_calls = {"count": 0}

        def flaky_execute_query(self, query, params=None, *, commit=True):
            if "INSERT INTO user_selection" in query:
                insert_calls["count"] += 1
                if insert_calls["count"] == 3:
                    raise sqlite3.Error("forced")
            return original_execute_query(self, query, params, commit=commit)

        monkeypatch.setattr(DatabaseHandler, "execute_query", flaky_execute_query)

        with pytest.raises(sqlite3.Error, match="forced"):
            restore_backup(backup["id"])

        with DatabaseHandler() as db:
            rows = db.fetch_all("SELECT exercise, sets, weight FROM user_selection ORDER BY exercise")
            assert len(rows) == 2
            exercises = {row["exercise"] for row in rows}
            assert exercises == {"Exercise C", "Exercise D"}
            assert "Exercise A" not in exercises
            assert "Exercise B" not in exercises
    
    # -------------------------------------------------------------------------
    # Test 3: Restore skips missing exercises
    # -------------------------------------------------------------------------
    
    def test_restore_skips_missing_exercises(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that restore skips exercises that are missing from catalog."""
        # Create exercises and backup
        ex1 = exercise_factory("Bench Press", primary_muscle_group="Chest")
        ex2 = exercise_factory("Squat", primary_muscle_group="Quadriceps")
        ex3 = exercise_factory("Overhead Press", primary_muscle_group="Shoulders")
        
        workout_plan_factory(exercise_name=ex1, routine="Workout A", sets=3)
        workout_plan_factory(exercise_name=ex2, routine="Workout A", sets=4)
        workout_plan_factory(exercise_name=ex3, routine="Workout A", sets=3)
        
        backup = create_backup(name="Full Program")
        
        # Remove one exercise from catalog (simulates missing exercise)
        with DatabaseHandler() as db:
            # First clear user_selection to avoid FK constraint
            db.execute_query("DELETE FROM user_selection")
            # Delete exercise from catalog
            db.execute_query("DELETE FROM exercises WHERE exercise_name = ?", ("Overhead Press",))
        
        # Restore backup
        result = restore_backup(backup['id'])
        
        # Should not fail
        assert result['restored_count'] == 2  # Only 2 of 3 restored
        assert "Overhead Press" in result['skipped']
        
        # Verify only valid exercises were restored
        with DatabaseHandler() as db:
            rows = db.fetch_all("SELECT exercise FROM user_selection")
            exercises = {row['exercise'] for row in rows}
            assert exercises == {"Bench Press", "Squat"}
            assert "Overhead Press" not in exercises
    
    def test_restore_nonexistent_backup_raises_error(self, clean_db):
        """Test that restoring a non-existent backup raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            restore_backup(99999)

    def test_restore_commits_once_on_success(self, clean_db, exercise_factory, workout_plan_factory, monkeypatch):
        """Test that restore closes an active transaction exactly once on success.

        The counter only increments when ``in_transaction`` is True at commit time,
        so DatabaseHandler.__exit__'s idempotent post-commit does not inflate the
        count. A regression to per-statement commits would bump this well past 1.
        """
        ex1 = exercise_factory("Bench Press", primary_muscle_group="Chest")
        ex2 = exercise_factory("Squat", primary_muscle_group="Quadriceps")
        ex3 = exercise_factory("Deadlift", primary_muscle_group="Back")

        workout_plan_factory(exercise_name=ex1, routine="Workout A", sets=3, weight=100.0)
        workout_plan_factory(exercise_name=ex2, routine="Workout A", sets=4, weight=120.0)
        workout_plan_factory(exercise_name=ex3, routine="Workout B", sets=5, weight=150.0)

        backup = create_backup(name="Commit Count Program")

        commit_calls = {"count": 0}

        class CommitCountingConnection:
            def __init__(self, connection):
                self._connection = connection

            def commit(self):
                if self._connection.in_transaction:
                    commit_calls["count"] += 1
                return self._connection.commit()

            def rollback(self):
                return self._connection.rollback()

            def execute(self, *args, **kwargs):
                return self._connection.execute(*args, **kwargs)

            def close(self):
                return self._connection.close()

            def __getattr__(self, name):
                return getattr(self._connection, name)

        class CommitCountingDatabaseHandler(DatabaseHandler):
            def __init__(self, database_path=None):
                super().__init__(database_path)
                self.connection = CommitCountingConnection(self.connection)

        monkeypatch.setattr("utils.program_backup.DatabaseHandler", CommitCountingDatabaseHandler)

        result = restore_backup(backup["id"])

        assert result["restored_count"] == 3
        assert commit_calls["count"] == 1

    # -------------------------------------------------------------------------
    # Test 4: Delete backup removes it
    # -------------------------------------------------------------------------
    
    def test_delete_backup_removes_backup_and_items(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that deleting a backup removes both header and items."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        backup = create_backup(name="To Delete")
        backup_id = backup['id']
        
        # Verify backup exists
        assert get_backup_details(backup_id) is not None
        
        # Delete backup
        result = delete_backup(backup_id)
        assert result is True
        
        # Verify backup and items are gone
        assert get_backup_details(backup_id) is None
        
        # Verify items are also deleted
        with DatabaseHandler() as db:
            items = db.fetch_all(
                "SELECT * FROM program_backup_items WHERE backup_id = ?",
                (backup_id,)
            )
            assert len(items) == 0
    
    def test_delete_nonexistent_backup_returns_false(self, clean_db):
        """Test that deleting a non-existent backup returns False."""
        result = delete_backup(99999)
        assert result is False
    
    # -------------------------------------------------------------------------
    # Test 5: Erase/reset integration
    # -------------------------------------------------------------------------
    
    def test_auto_backup_created_before_erase(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that auto-backup is created when active program has data."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise", routine="Workout A")
        
        # Verify active program has data
        assert get_active_program_count() == 1
        
        # Create auto-backup
        auto_backup = create_auto_backup_before_erase()
        
        assert auto_backup is not None
        assert auto_backup['backup_type'] == "auto"
        assert auto_backup['item_count'] == 1
        assert "Pre-Erase Auto-Backup" in auto_backup['name']
    
    def test_auto_backup_skipped_when_program_empty(self, clean_db):
        """Test that auto-backup is skipped when active program is empty."""
        assert get_active_program_count() == 0
        
        auto_backup = create_auto_backup_before_erase()
        
        assert auto_backup is None

    def test_two_auto_backups_same_second_both_succeed(
        self,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """Test that same-second auto-backups get distinct names."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        class SameSecondDatetime:
            calls = 0

            @classmethod
            def now(cls):
                cls.calls += 1
                return datetime(2026, 4, 24, 12, 0, 0, cls.calls)

        monkeypatch.setattr(program_backup_module, "datetime", SameSecondDatetime)

        first = create_auto_backup_before_erase()
        second = create_auto_backup_before_erase()

        assert first is not None
        assert second is not None
        assert first["name"] != second["name"]

        auto_backups = [backup for backup in list_backups() if backup["backup_type"] == "auto"]
        assert len(auto_backups) == 2

    def test_auto_backup_retention_keeps_latest_n(
        self,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """Test that auto-backup retention keeps only the latest ten."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        class AdvancingDatetime:
            calls = 0

            @classmethod
            def now(cls):
                cls.calls += 1
                return datetime(2026, 4, 24, 12, 0, 0, cls.calls)

        monkeypatch.setattr(program_backup_module, "datetime", AdvancingDatetime)

        for _ in range(12):
            create_auto_backup_before_erase()

        auto_backups = [backup for backup in list_backups() if backup["backup_type"] == "auto"]
        assert len(auto_backups) == 10

        names = {backup["name"] for backup in auto_backups}
        assert "Pre-Erase Auto-Backup (2026-04-24 12:00:00.000001)" not in names
        assert "Pre-Erase Auto-Backup (2026-04-24 12:00:00.000004)" not in names
        assert "Pre-Erase Auto-Backup (2026-04-24 12:00:00.000034)" in names

    def test_auto_backup_retention_ignores_manual(
        self,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """Test that pruning auto-backups does not remove manual backups."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        for index in range(12):
            create_backup(name=f"Manual {index}")

        class AdvancingDatetime:
            calls = 0

            @classmethod
            def now(cls):
                cls.calls += 1
                return datetime(2026, 4, 24, 12, 0, 0, cls.calls)

        monkeypatch.setattr(program_backup_module, "datetime", AdvancingDatetime)

        for _ in range(3):
            create_auto_backup_before_erase()

        backups = list_backups()
        manual_backups = [backup for backup in backups if backup["backup_type"] == "manual"]
        auto_backups = [backup for backup in backups if backup["backup_type"] == "auto"]

        assert len(manual_backups) == 12
        assert len(auto_backups) == 3

    def test_auto_backup_prune_cascades_items(
        self,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """Test that pruned auto-backups do not leave orphaned item rows."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        class AdvancingDatetime:
            calls = 0

            @classmethod
            def now(cls):
                cls.calls += 1
                return datetime(2026, 4, 24, 12, 0, 0, cls.calls)

        monkeypatch.setattr(program_backup_module, "datetime", AdvancingDatetime)

        for _ in range(12):
            create_auto_backup_before_erase()

        with DatabaseHandler() as db:
            orphaned = db.fetch_one(
                """
                SELECT COUNT(*) AS count
                  FROM program_backup_items
                 WHERE backup_id NOT IN (SELECT id FROM program_backups)
                """
            )

        assert orphaned["count"] == 0

    def test_create_plus_prune_atomic_on_failure(
        self,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        monkeypatch,
    ):
        """Test that a prune failure rolls back the newly created auto-backup."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        existing_count = len(list_backups())

        def fail_prune(*args, **kwargs):
            raise sqlite3.Error("forced prune failure")

        monkeypatch.setattr(program_backup_module, "prune_auto_backups", fail_prune)

        with pytest.raises(sqlite3.Error, match="forced prune failure"):
            create_auto_backup_before_erase()

        assert len(list_backups()) == existing_count
    
    def test_backups_survive_table_drop(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that backups survive when user_selection is dropped."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        # Create backup
        backup = create_backup(name="Survivor Backup")
        
        # Simulate erase by dropping user_selection
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM workout_log")
            db.execute_query("DELETE FROM user_selection")
        
        # Verify backup still exists
        backups = list_backups()
        assert len(backups) == 1
        assert backups[0]['name'] == "Survivor Backup"
        
        # Verify backup details are intact
        details = get_backup_details(backup['id'])
        assert details is not None
        assert len(details['items']) == 1
    
    def test_get_latest_auto_backup(self, clean_db, exercise_factory, workout_plan_factory):
        """Test that get_latest_auto_backup returns most recent auto-backup."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        # Create multiple auto-backups
        create_backup(name="Auto 1", backup_type="auto")
        create_backup(name="Auto 2", backup_type="auto")
        create_backup(name="Manual", backup_type="manual")
        
        latest = get_latest_auto_backup()
        
        assert latest is not None
        assert latest['backup_type'] == "auto"
        # Should be the most recent auto-backup (Auto 2)
        assert latest['name'] == "Auto 2"


class TestProgramBackupAPI:
    """Test suite for program backup API endpoints."""

    def test_backup_center_page_renders(self, client, clean_db):
        """The dedicated backup page should render successfully."""
        response = client.get('/backup')

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Backup Center" in body
        assert "Save Current Program" in body
        assert "programLibraryModal" not in body
    
    def test_api_list_backups(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test GET /api/backups returns list of backups."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        create_backup(name="API Test Backup")
        
        response = client.get('/api/backups')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == "API Test Backup"
    
    def test_api_create_backup(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test POST /api/backups creates a backup."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        response = client.post('/api/backups', 
            json={'name': 'New Backup', 'note': 'Test note'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['data']['name'] == "New Backup"
        assert data['data']['item_count'] == 1
    
    def test_api_create_backup_requires_name(self, client, clean_db):
        """Test POST /api/backups requires name."""
        response = client.post('/api/backups',
            json={'note': 'No name'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert 'name' in data['error']['message'].lower()
    
    def test_api_get_backup_details(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test GET /api/backups/<id> returns backup details."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        backup = create_backup(name="Detail Test")
        
        response = client.get(f'/api/backups/{backup["id"]}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['data']['name'] == "Detail Test"
        assert 'items' in data['data']
        assert len(data['data']['items']) == 1
    
    def test_api_get_backup_not_found(self, client, clean_db):
        """Test GET /api/backups/<id> returns 404 for missing backup."""
        response = client.get('/api/backups/99999')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['ok'] is False
    
    def test_api_restore_backup(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test POST /api/backups/<id>/restore restores backup."""
        ex1 = exercise_factory("Original Exercise")
        workout_plan_factory(exercise_name=ex1)
        
        backup = create_backup(name="Restore Test")
        
        # Clear and add new data
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM user_selection")
        
        response = client.post(f'/api/backups/{backup["id"]}/restore',
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['data']['restored_count'] == 1
    
    def test_api_delete_backup(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test DELETE /api/backups/<id> deletes backup."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        backup = create_backup(name="To Delete")
        
        response = client.delete(f'/api/backups/{backup["id"]}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        
        # Verify backup is gone
        assert get_backup_details(backup['id']) is None

    def test_api_patch_backup_updates_name(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test PATCH /api/backups/<id> updates the backup name."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        backup = create_backup(name="Before", note="Original note")

        response = client.patch(
            f'/api/backups/{backup["id"]}',
            json={'name': 'After'},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['data']['name'] == 'After'
        assert data['data']['note'] == 'Original note'

        refreshed = get_backup_details(backup['id'])
        assert refreshed['name'] == 'After'

    def test_api_patch_backup_updates_note(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test PATCH /api/backups/<id> updates the backup note."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        backup = create_backup(name="Before", note="Original note")

        response = client.patch(
            f'/api/backups/{backup["id"]}',
            json={'note': 'Updated note'},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['data']['name'] == 'Before'
        assert data['data']['note'] == 'Updated note'

        refreshed = get_backup_details(backup['id'])
        assert refreshed['note'] == 'Updated note'

    def test_api_patch_backup_rejects_empty_name(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test PATCH /api/backups/<id> rejects an empty name."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        backup = create_backup(name="Before")

        response = client.patch(
            f'/api/backups/{backup["id"]}',
            json={'name': ''},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_api_patch_backup_rejects_oversized_name(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test PATCH /api/backups/<id> rejects a name longer than 100 characters."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        backup = create_backup(name="Before")

        response = client.patch(
            f'/api/backups/{backup["id"]}',
            json={'name': 'x' * 101},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_api_patch_backup_rejects_oversized_note(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test PATCH /api/backups/<id> rejects a note longer than 500 characters."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        backup = create_backup(name="Before")

        response = client.patch(
            f'/api/backups/{backup["id"]}',
            json={'note': 'x' * 501},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_api_patch_backup_not_found(self, client, clean_db):
        """Test PATCH /api/backups/<id> returns 404 when the backup does not exist."""
        response = client.patch(
            '/api/backups/99999',
            json={'name': 'Missing'},
            content_type='application/json'
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_api_patch_preserves_created_at_and_id(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test PATCH /api/backups/<id> keeps immutable fields unchanged."""
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")

        backup = create_backup(name="Before", note="Original note")
        original = get_backup_details(backup['id'])

        response = client.patch(
            f'/api/backups/{backup["id"]}',
            json={'name': 'After'},
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['id'] == original['id']
        assert data['data']['backup_type'] == original['backup_type']

        refreshed = get_backup_details(backup['id'])
        assert refreshed['id'] == original['id']
        assert refreshed['created_at'] == original['created_at']
        assert refreshed['backup_type'] == original['backup_type']


class TestEraseDataDeletesBackups:
    """Test the erase-data endpoint deletes all data including backups."""
    
    def test_erase_data_deletes_backups(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test that /erase-data deletes all backups (full reset)."""
        # Setup: Create exercise and add to workout plan
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        # Create some backups
        create_backup(name="Manual Backup 1")
        create_backup(name="Manual Backup 2")
        
        # Verify backups exist
        backups_before = list_backups()
        assert len(backups_before) == 2
        
        # Call erase-data
        response = client.post('/erase-data')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        
        # Verify all backups are deleted
        backups_after = list_backups()
        assert len(backups_after) == 0
    
    def test_erase_data_on_empty_database(self, client, clean_db):
        """Test that /erase-data works on empty database."""
        # Ensure program is empty
        assert get_active_program_count() == 0
        
        # Call erase-data
        response = client.post('/erase-data')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data.get('data') is None
    
    def test_erase_data_reinitializes_tables(self, client, clean_db, exercise_factory, workout_plan_factory):
        """Test that /erase-data properly reinitializes all tables."""
        # Setup: Create exercise and workout plan
        exercise_factory("Test Exercise")
        workout_plan_factory(exercise_name="Test Exercise")
        
        # Create a backup
        create_backup(name="Test Backup")
        
        # Call erase-data
        response = client.post('/erase-data')
        assert response.status_code == 200
        
        # Verify workout plan is cleared
        assert get_active_program_count() == 0
        
        # Verify backups are cleared
        backups = list_backups()
        assert len(backups) == 0
        
        # Verify we can create new backups (tables were reinitialized)
        exercise_factory("New Exercise")
        workout_plan_factory(exercise_name="New Exercise")
        new_backup = create_backup(name="New Backup After Erase")
        assert new_backup is not None
        assert new_backup['item_count'] == 1


# Columns that the program backup snapshot owns and is responsible for restoring
# row-for-row (see utils/program_backup.py create_backup / restore_backup). The
# active program's surrogate ``id`` is intentionally excluded: restore re-inserts
# rows, so ids are not preserved and are not part of the backup contract.
_BACKUP_OWNED_COLUMNS = (
    "routine", "exercise", "sets", "min_rep_range", "max_rep_range",
    "rir", "rpe", "weight", "exercise_order", "superset_group",
)
# Subset captured by a backup taken before the ``exercise_order`` startup ALTER.
_BASE_OWNED_COLUMNS = tuple(c for c in _BACKUP_OWNED_COLUMNS if c != "exercise_order")


def _none_safe_key(row):
    """Sort key that tolerates NULL (None) values mixed with real values."""
    return tuple((value is None, value) for value in row)


def _snapshot_user_selection(db, columns=_BACKUP_OWNED_COLUMNS):
    """Return a deterministically ordered list of user_selection rows.

    Ordering is by value (not by id) so two snapshots can be compared row-for-row
    regardless of the surrogate ids assigned on insert/restore.
    """
    select_cols = ", ".join(columns)
    rows = db.fetch_all(f"SELECT {select_cols} FROM user_selection")
    return sorted(
        (tuple(row[col] for col in columns) for row in rows),
        key=_none_safe_key,
    )


def _seed_known_program(exercise_factory):
    """Seed a known multi-routine program with ordering, RIR/RPE, rep ranges,
    weights, and a superset pair. Returns the inserted row tuples (backup-owned
    columns) for reference.
    """
    rows = [
        # routine, exercise, sets, min, max, rir, rpe, weight, order, superset
        ("Upper A", "Bench Press", 3, 6, 8, 2, 8.0, 100.0, 1, "ss-1"),
        ("Upper A", "Incline Press", 3, 8, 10, 1, 9.0, 60.0, 2, "ss-1"),
        ("Upper A", "Barbell Row", 4, 8, 12, 2, 7.5, 80.0, 3, None),
        ("Lower B", "Squat", 4, 5, 5, 3, 7.0, 140.0, 4, None),
        ("Lower B", "Deadlift", 2, 3, 5, 1, 9.5, 180.0, 5, None),
    ]
    for name in {row[1] for row in rows}:
        exercise_factory(name)
    with DatabaseHandler() as db:
        # Honor pre-ALTER schemas where exercise_order has not been added yet.
        has_order = column_exists(db, "user_selection", "exercise_order")
        for row in rows:
            if has_order:
                db.execute_query(
                    """
                    INSERT INTO user_selection
                        (routine, exercise, sets, min_rep_range, max_rep_range,
                         rir, rpe, weight, exercise_order, superset_group)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            else:
                db.execute_query(
                    """
                    INSERT INTO user_selection
                        (routine, exercise, sets, min_rep_range, max_rep_range,
                         rir, rpe, weight, superset_group)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row[:8] + (row[9],),
                )
    return rows


class TestUserSelectionBackupIntegrity:
    """Row-for-row integrity of the user_selection backup/restore round-trip.

    Backup scope is intentionally ``user_selection`` program state only (routines
    and planned selections), per CLAUDE.md §1. These tests assert that every
    backup-owned column survives a snapshot → mutate → restore round-trip exactly.
    They deliberately do not assert that workout_log / profile / calibration rows
    survive: restore intentionally deletes workout_log when replacing the program.
    """

    def test_restore_preserves_user_selection_row_for_row(self, clean_db, exercise_factory):
        """Full program restore reproduces every backup-owned column exactly."""
        _seed_known_program(exercise_factory)

        with DatabaseHandler() as db:
            before = _snapshot_user_selection(db)
        assert len(before) == 5

        backup = create_backup(name="Integrity Program")

        # Erase the active program (workout_log first to respect FK intent).
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM workout_log")
            db.execute_query("DELETE FROM user_selection")
        assert get_active_program_count() == 0

        result = restore_backup(backup["id"])
        assert result["restored_count"] == 5
        assert result["skipped"] == []

        with DatabaseHandler() as db:
            after = _snapshot_user_selection(db)

        assert after == before

    def test_restore_over_non_empty_program_matches_snapshot(self, clean_db, exercise_factory):
        """Restore over a different non-empty program yields exactly the snapshot."""
        _seed_known_program(exercise_factory)

        with DatabaseHandler() as db:
            before = _snapshot_user_selection(db)

        backup = create_backup(name="Integrity Program")

        # Replace the active program with a different, non-empty program.
        exercise_factory("Leg Press")
        intervening = ("Intervening", "Leg Press", 5, 12, 15, 0, 10.0, 200.0, 9, "zz-9")
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM workout_log")
            db.execute_query("DELETE FROM user_selection")
            db.execute_query(
                """
                INSERT INTO user_selection
                    (routine, exercise, sets, min_rep_range, max_rep_range,
                     rir, rpe, weight, exercise_order, superset_group)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                intervening,
            )
        assert get_active_program_count() == 1

        result = restore_backup(backup["id"])
        assert result["restored_count"] == 5

        with DatabaseHandler() as db:
            after = _snapshot_user_selection(db)

        assert after == before
        assert intervening not in after  # intervening program fully replaced

    def test_restore_backup_taken_before_exercise_order_alter(self, clean_db, exercise_factory):
        """A backup captured before the exercise_order startup ALTER restores cleanly.

        Simulates the documented startup migration path (CLAUDE.md §5
        "exercise_order column"): the column is added to an existing DB via ALTER.
        A backup taken while the column was absent must still restore its
        base-owned columns (including superset_group) row-for-row, with
        exercise_order left NULL on the restored rows.
        """
        # Pre-ALTER state: user_selection without the exercise_order column.
        with DatabaseHandler() as db:
            db.execute_query("ALTER TABLE user_selection DROP COLUMN exercise_order")
            assert not column_exists(db, "user_selection", "exercise_order")

        _seed_known_program(exercise_factory)

        with DatabaseHandler() as db:
            before = _snapshot_user_selection(db, columns=_BASE_OWNED_COLUMNS)
        assert len(before) == 5

        # Backup is taken while exercise_order is absent.
        backup = create_backup(name="Pre-ALTER Program")
        details = get_backup_details(backup["id"])
        assert all(item["exercise_order"] is None for item in details["items"])

        # Startup ALTER runs on the upgraded DB, re-adding exercise_order.
        assert initialize_exercise_order() is True
        with DatabaseHandler() as db:
            assert column_exists(db, "user_selection", "exercise_order")

        # Erase and restore the pre-ALTER backup into the post-ALTER schema.
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM workout_log")
            db.execute_query("DELETE FROM user_selection")

        result = restore_backup(backup["id"])
        assert result["restored_count"] == 5
        assert result["skipped"] == []

        with DatabaseHandler() as db:
            after = _snapshot_user_selection(db, columns=_BASE_OWNED_COLUMNS)
            order_values = db.fetch_all("SELECT exercise_order FROM user_selection")

        assert after == before
        assert all(row["exercise_order"] is None for row in order_values)
