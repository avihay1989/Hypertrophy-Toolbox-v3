"""
Priority 0 Tests: Filter Whitelist Validation (SQL Injection Protection)
"""
import pytest
from routes.filters import ALLOWED_TABLES, ALLOWED_COLUMNS, validate_table_name, validate_column_name
from utils.db_initializer import initialize_database


class TestWhitelistValidation:
    """Test whitelist validation functions."""
    
    def test_validate_table_name_allowed(self):
        """Test that allowed table names pass validation."""
        assert validate_table_name('exercises') is True
        assert validate_table_name('user_selection') is True
        assert validate_table_name('workout_log') is True
        assert validate_table_name('progression_goals') is True
    
    def test_validate_table_name_case_insensitive(self):
        """Test that table name validation is case-insensitive."""
        assert validate_table_name('EXERCISES') is True
        assert validate_table_name('Exercises') is True
        assert validate_table_name('ExErCiSeS') is True
    
    def test_validate_table_name_rejected(self):
        """Test that disallowed table names are rejected."""
        assert validate_table_name('evil_table') is False
        assert validate_table_name('users; DROP TABLE exercises') is False
        assert validate_table_name("' OR '1'='1") is False
        assert validate_table_name('; DELETE FROM exercises') is False
    
    def test_validate_column_name_allowed(self):
        """Test that allowed column names pass validation."""
        assert validate_column_name('primary_muscle_group') is True
        assert validate_column_name('equipment') is True
        assert validate_column_name('difficulty') is True
        assert validate_column_name('exercise_name') is True
    
    def test_validate_column_name_case_insensitive(self):
        """Test that column name validation is case-insensitive."""
        assert validate_column_name('PRIMARY_MUSCLE_GROUP') is True
        assert validate_column_name('Equipment') is True
    
    def test_validate_column_name_rejected(self):
        """Test that disallowed column names are rejected."""
        assert validate_column_name('evil_column') is False
        assert validate_column_name("'; DROP TABLE exercises; --") is False
        assert validate_column_name("1=1") is False
        assert validate_column_name("'; DELETE FROM exercises") is False


class TestFilterExercisesWhitelist:
    """Test filter_exercises endpoint with whitelist validation."""
    
    def test_valid_filters_work(self, client, exercise_factory):
        """Test that valid filters return results."""
        exercise_factory("Bench Press", primary_muscle_group="Chest", equipment="Barbell")
        exercise_factory("Squat", primary_muscle_group="Legs", equipment="Barbell")
        
        response = client.post('/filter_exercises', json={
            "Primary Muscle Group": "Chest"
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert "Bench Press" in data['data']
        assert "Squat" not in data['data']
    
    def test_multi_filter_and_logic(self, client, exercise_factory):
        """Test that multiple filters combine with AND logic."""
        exercise_factory("Bench Press", primary_muscle_group="Chest", equipment="Barbell")
        exercise_factory("Dumbbell Press", primary_muscle_group="Chest", equipment="Dumbbell")
        exercise_factory("Squat", primary_muscle_group="Legs", equipment="Barbell")
        
        response = client.post('/filter_exercises', json={
            "Primary Muscle Group": "Chest",
            "Equipment": "Barbell"
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        exercises = data['data']
        assert "Bench Press" in exercises
        assert "Dumbbell Press" not in exercises
        assert "Squat" not in exercises

    def test_barbell_curl_metadata_repair_keeps_biceps_barbell_filter(self, client, clean_db):
        """Regression: Barbell Curl must appear under Biceps + Barbell filters."""
        clean_db.execute_query(
            """
            INSERT INTO exercises (
                exercise_name,
                primary_muscle_group,
                equipment,
                mechanic
            )
            VALUES (?, ?, ?, ?)
            """,
            ("Barbell Curl", "Biceps", None, "Isolation"),
        )

        initialize_database(force=True)

        response = client.post('/filter_exercises', json={
            "Primary Muscle Group": "Biceps",
            "Equipment": "Barbell"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert "Barbell Curl" in data['data']

    def test_common_exercise_equipment_repairs_fill_blank_values(self, clean_db):
        """Common catalogue rows with blank equipment are repaired on startup."""
        expected_equipment = {
            "Barbell Row": "Barbell",
            "Bench Press": "Barbell",
            "Cable Fly": "Cables",
            "Calf Raise": "Bodyweight",
            "Face Pull": "Cables",
            "Hammer Curl": "Dumbbells",
            "Incline Dumbbell Press": "Dumbbells",
            "Lateral Raise": "Dumbbells",
            "Leg Curl": "Machine",
            "Leg Press": "Machine",
            "Overhead Press": "Barbell",
            "Pull Up": "Bodyweight",
            "Romanian Deadlift": "Barbell",
            "Squat": "Barbell",
            "Tricep Pushdown": "Cables",
        }

        for exercise_name in expected_equipment:
            clean_db.execute_query(
                """
                INSERT INTO exercises (exercise_name, primary_muscle_group, equipment)
                VALUES (?, ?, ?)
                """,
                (exercise_name, "Chest", None),
            )

        initialize_database(force=True)

        for exercise_name, equipment in expected_equipment.items():
            row = clean_db.fetch_one(
                "SELECT equipment FROM exercises WHERE exercise_name = ?",
                (exercise_name,),
            )
            assert row["equipment"] == equipment
    
    def test_invalid_column_name_rejected(self, client):
        """Test that invalid column names return 400 with standardized error."""
        response = client.post('/filter_exercises', json={
            "Evil Column'; DROP TABLE exercises; --": "value"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert 'error' in data
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'invalid filter column' in data['error']['message'].lower()
    
    def test_injection_attempt_rejected(self, client):
        """Test that SQL injection attempts in filter values are rejected (even if column is valid)."""
        # Note: Column name validation should prevent this, but test that values are parameterized
        response = client.post('/filter_exercises', json={
            "Primary Muscle Group": "Chest'; DROP TABLE exercises; --"
        })
        
        # Should return 200 with empty results (value is parameterized, so injection fails)
        # OR 400 if column name is invalid
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.get_json()
            assert data['ok'] is True
            assert data['data'] == []  # No matches for invalid value


class TestGetUniqueValuesWhitelist:
    """Test get_unique_values endpoint with whitelist validation."""
    
    def test_valid_table_column_returns_values(self, client, exercise_factory):
        """Test that valid table/column combinations return values."""
        exercise_factory("Bench Press", primary_muscle_group="Chest")
        exercise_factory("Squat", primary_muscle_group="Legs")
        
        response = client.get('/get_unique_values/exercises/primary_muscle_group')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert 'data' in data
        assert "Chest" in data['data']
        assert "Legs" in data['data']
    
    def test_invalid_table_rejected(self, client):
        """Test that invalid table names return 400."""
        response = client.get('/get_unique_values/evil_table/column')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'Invalid table' in data['error']['message']
    
    def test_invalid_column_rejected(self, client):
        """Test that invalid column names return 400."""
        response = client.get('/get_unique_values/exercises/evil_column')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'Invalid column' in data['error']['message']
    
    def test_sql_injection_in_table_rejected(self, client):
        """Test that SQL injection attempts in table name are rejected."""
        response = client.get('/get_unique_values/exercises;DROP TABLE exercises;/column')
        
        # URL encoding should prevent this, but test path parsing
        # Should return 400 for invalid table name
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
    
    def test_sql_injection_in_column_rejected(self, client):
        """Test that SQL injection attempts in column name are rejected."""
        response = client.get('/get_unique_values/exercises/column;DROP TABLE exercises;--')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'


class TestGetFilteredExercisesWhitelist:
    """Test get_filtered_exercises endpoint with whitelist validation."""
    
    def test_valid_columns_work(self, client, exercise_factory):
        """Test that valid column names in filters work."""
        exercise_factory("Bench Press", equipment="Barbell")
        
        response = client.post('/get_filtered_exercises', json={
            "equipment": "Barbell"
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert "Bench Press" in data['data']
    
    def test_invalid_column_rejected(self, client):
        """Test that invalid column names return 400."""
        response = client.post('/get_filtered_exercises', json={
            "evil_column'; DROP TABLE exercises; --": "value"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'invalid filter column' in data['error']['message'].lower()
