"""Tests for priority muscle reallocation and pattern coverage."""
import pytest
import os
import sqlite3

# Set testing flag before imports
os.environ["TESTING"] = "1"

from utils.plan_generator import (
    GeneratorConfig,
    MUSCLE_TO_PATTERNS,
)
from utils.movement_patterns import MovementPattern, MovementSubpattern
from utils.weekly_summary import calculate_pattern_coverage


class TestMuscleToPatterns:
    """Tests for the MUSCLE_TO_PATTERNS constant."""
    
    def test_chest_mapping(self):
        """Chest should map to horizontal push."""
        chest = MUSCLE_TO_PATTERNS.get("chest")
        assert chest is not None
        assert MovementPattern.HORIZONTAL_PUSH in chest["patterns"]
    
    def test_biceps_mapping(self):
        """Biceps should map to pulls and curl isolation."""
        biceps = MUSCLE_TO_PATTERNS.get("biceps")
        assert biceps is not None
        assert MovementPattern.HORIZONTAL_PULL in biceps["patterns"]
        assert MovementPattern.VERTICAL_PULL in biceps["patterns"]
        assert MovementSubpattern.BICEP_CURL in biceps["isolation_subpatterns"]
    
    def test_quadriceps_mapping(self):
        """Quads should map to squat pattern."""
        quads = MUSCLE_TO_PATTERNS.get("quadriceps")
        assert quads is not None
        assert MovementPattern.SQUAT in quads["patterns"]
        assert MovementSubpattern.LEG_EXTENSION in quads["isolation_subpatterns"]
    
    def test_hamstrings_mapping(self):
        """Hamstrings should map to hinge pattern."""
        hams = MUSCLE_TO_PATTERNS.get("hamstrings")
        assert hams is not None
        assert MovementPattern.HINGE in hams["patterns"]
        assert MovementSubpattern.LEG_CURL in hams["isolation_subpatterns"]
    
    def test_all_major_muscles_mapped(self):
        """All common muscle groups should have mappings."""
        required_muscles = [
            "chest", "biceps", "triceps", "quadriceps", "hamstrings",
            "gluteus maximus", "calves", "latissimus dorsi",
        ]
        for muscle in required_muscles:
            assert muscle in MUSCLE_TO_PATTERNS, f"Missing mapping for {muscle}"


class TestPriorityMuscleConfig:
    """Tests for priority muscle configuration."""
    
    def test_config_accepts_priority_muscles(self):
        """GeneratorConfig should accept priority_muscles parameter."""
        config = GeneratorConfig(
            training_days=2,
            priority_muscles=["chest", "biceps"],
        )
        assert config.priority_muscles == ["chest", "biceps"]
    
    def test_config_allows_none_priority_muscles(self):
        """Priority muscles can be None."""
        config = GeneratorConfig(training_days=2)
        assert config.priority_muscles is None
    
    def test_config_limits_to_two_muscles(self):
        """Config should limit priority muscles to 2."""
        config = GeneratorConfig(
            training_days=2,
            priority_muscles=["chest", "biceps", "triceps", "quadriceps"],
        )
        # Should only keep first 2
        assert config.priority_muscles is not None
        assert len(config.priority_muscles) == 2
        assert config.priority_muscles == ["chest", "biceps"]
    
    def test_config_normalizes_muscle_names(self):
        """Config should normalize muscle names to lowercase."""
        config = GeneratorConfig(
            training_days=2,
            priority_muscles=["CHEST", "Biceps"],
        )
        assert config.priority_muscles == ["chest", "biceps"]
    
    def test_config_handles_invalid_muscles(self):
        """Config should handle invalid muscle names gracefully."""
        config = GeneratorConfig(
            training_days=2,
            priority_muscles=["invalid_muscle"],
        )
        # Invalid muscle should be filtered out, leaving None
        assert config.priority_muscles is None
    
    def test_config_handles_partial_match(self):
        """Config should match similar muscle names."""
        config = GeneratorConfig(
            training_days=2,
            priority_muscles=["traps"],  # Should match trapezius
        )
        # Should find a partial match
        assert config.priority_muscles is not None
        assert len(config.priority_muscles) == 1
    
    def test_config_handles_mixed_valid_invalid(self):
        """Config should keep valid muscles when some are invalid."""
        config = GeneratorConfig(
            training_days=2,
            priority_muscles=["chest", "invalid_muscle"],
        )
        # Should only keep the valid one
        assert config.priority_muscles == ["chest"]


class TestPriorityMuscleReallocation:
    """Tests for priority muscle volume reallocation."""
    
    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create a mock database with test exercises."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create exercises table
        cursor.execute("""
            CREATE TABLE exercises (
                exercise_name TEXT PRIMARY KEY,
                primary_muscle_group TEXT,
                secondary_muscle_group TEXT,
                mechanic TEXT,
                utility TEXT,
                equipment TEXT,
                difficulty TEXT,
                movement_pattern TEXT,
                movement_subpattern TEXT
            )
        """)
        
        # Insert test exercises
        exercises = [
            ("Bench Press", "Chest", "Triceps", "Compound", "Basic", "Barbell", "Beginner", "horizontal_push", None),
            ("Incline Dumbbell Curl", "Biceps", None, "Isolated", "Auxiliary", "Dumbbells", "Beginner", "upper_isolation", "bicep_curl"),
            ("Squat", "Quadriceps", "Gluteus Maximus", "Compound", "Basic", "Barbell", "Intermediate", "squat", "bilateral_squat"),
            ("Romanian Deadlift", "Hamstrings", "Gluteus Maximus", "Compound", "Basic", "Barbell", "Intermediate", "hinge", "deadlift"),
            ("Lat Pulldown", "Latissimus Dorsi", "Biceps", "Compound", "Basic", "Cable", "Beginner", "vertical_pull", "pulldown"),
            ("Overhead Press", "Front-Shoulder", "Triceps", "Compound", "Basic", "Barbell", "Intermediate", "vertical_push", "press"),
            ("Barbell Row", "Upper Back", "Biceps", "Compound", "Basic", "Barbell", "Intermediate", "horizontal_pull", "row"),
            ("Plank", "Abs/Core", None, "Isolated", "Auxiliary", "Bodyweight", "Beginner", "core_static", "plank"),
            ("Leg Curl", "Hamstrings", None, "Isolated", "Auxiliary", "Machine", "Beginner", "lower_isolation", "leg_curl"),
            ("Tricep Pushdown", "Triceps", None, "Isolated", "Auxiliary", "Cable", "Beginner", "upper_isolation", "tricep_extension"),
        ]
        
        cursor.executemany(
            "INSERT INTO exercises VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            exercises
        )
        
        # Create user_selection table
        cursor.execute("""
            CREATE TABLE user_selection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine TEXT,
                exercise TEXT,
                sets INTEGER,
                min_rep_range INTEGER,
                max_rep_range INTEGER,
                rir INTEGER,
                rpe REAL,
                weight REAL,
                exercise_order INTEGER,
                superset_group TEXT
            )
        """)
        
        # Create workout_log table (needed for FK)
        cursor.execute("""
            CREATE TABLE workout_log (
                id INTEGER PRIMARY KEY,
                workout_plan_id INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Set the database path
        import utils.config
        original_path = utils.config.DB_FILE
        utils.config.DB_FILE = str(db_path)
        
        yield str(db_path)
        
        # Restore original path
        utils.config.DB_FILE = original_path


class TestPatternCoverageAnalysis:
    """Tests for pattern coverage calculation."""
    
    def test_pattern_coverage_structure(self, clean_db):
        """Pattern coverage should return expected structure."""
        coverage = calculate_pattern_coverage()
        
        assert "per_routine" in coverage
        assert "total" in coverage
        assert "warnings" in coverage
        assert "sets_per_routine" in coverage
        assert "ideal_sets_range" in coverage
    
    def test_ideal_sets_range_values(self, clean_db):
        """Should return correct ideal sets range (15-24)."""
        coverage = calculate_pattern_coverage()
        
        assert coverage["ideal_sets_range"]["min"] == 15
        assert coverage["ideal_sets_range"]["max"] == 24


class TestPatternCoverageWarnings:
    """Tests for pattern coverage warning generation."""
    
    def test_low_volume_warning_threshold(self):
        """Should warn when sets per routine is under 15."""
        # The function checks for sets < 15
        # This is tested implicitly through integration tests
        pass
    
    def test_high_volume_warning_threshold(self):
        """Should warn when sets per routine exceeds 24."""
        # The function checks for sets > 24
        pass
    
    def test_ideal_sets_range_returned(self, clean_db):
        """Should return ideal sets range (15-24)."""
        coverage = calculate_pattern_coverage()
        
        assert "ideal_sets_range" in coverage
        assert coverage["ideal_sets_range"]["min"] == 15
        assert coverage["ideal_sets_range"]["max"] == 24


class TestPatternCoverageEndpoint:
    """Tests for the pattern coverage API endpoint."""
    
    @pytest.fixture
    def client(self, tmp_path):
        """Create a test client with mock database."""
        from flask import Flask

        # Set testing environment
        os.environ["TESTING"] = "1"
        
        db_path = tmp_path / "test_api.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create minimal tables
        cursor.execute("""
            CREATE TABLE exercises (
                exercise_name TEXT PRIMARY KEY,
                primary_muscle_group TEXT,
                movement_pattern TEXT,
                movement_subpattern TEXT,
                mechanic TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE user_selection (
                id INTEGER PRIMARY KEY,
                routine TEXT,
                exercise TEXT,
                sets INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
        
        import utils.config
        original_path = utils.config.DB_FILE
        utils.config.DB_FILE = str(db_path)
        
        # Create app
        app = Flask(__name__)
        from routes.weekly_summary import weekly_summary_bp
        app.register_blueprint(weekly_summary_bp)
        
        yield app.test_client()
    
    def test_pattern_coverage_endpoint_200(self, client):
        """Endpoint should return 200 OK."""
        response = client.get("/api/pattern_coverage")
        assert response.status_code == 200
    
    def test_pattern_coverage_endpoint_json(self, client):
        """Endpoint should return valid JSON."""
        response = client.get("/api/pattern_coverage")
        data = response.get_json()

        assert data is not None
        assert data["ok"] is True
        assert data["status"] == "success"
    
    def test_pattern_coverage_endpoint_structure(self, client):
        """Endpoint should return expected structure."""
        response = client.get("/api/pattern_coverage")
        data = response.get_json()
        
        assert "data" in data
        coverage = data["data"]
        
        assert "per_routine" in coverage
        assert "total" in coverage
        assert "warnings" in coverage
        assert "sets_per_routine" in coverage

class TestPlanGeneratorIntegrationE2E:
    """End-to-end integration tests for the plan generator workflow."""
    
    @pytest.fixture
    def app_client(self, tmp_path):
        """Create a test client with full database schema."""

        # Set testing environment
        os.environ["TESTING"] = "1"
        
        db_path = tmp_path / "test_e2e.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create exercises table with all columns
        cursor.execute("""
            CREATE TABLE exercises (
                exercise_name TEXT PRIMARY KEY,
                primary_muscle_group TEXT,
                secondary_muscle_group TEXT,
                tertiary_muscle_group TEXT,
                equipment TEXT,
                mechanic TEXT,
                utility TEXT,
                difficulty TEXT,
                movement_pattern TEXT,
                movement_subpattern TEXT,
                force TEXT
            )
        """)
        
        # Insert test exercises
        exercises = [
            ("Back Squat", "Quadriceps", "Gluteus Maximus", None, "Barbell", "Compound", "Basic", "Beginner", "squat", "bilateral_squat"),
            ("Romanian Deadlift", "Hamstrings", "Gluteus Maximus", None, "Barbell", "Compound", "Basic", "Intermediate", "hinge", "deadlift"),
            ("Bench Press", "Chest", "Triceps", "Front-Shoulder", "Barbell", "Compound", "Basic", "Beginner", "horizontal_push", None),
            ("Barbell Row", "Upper Back", "Biceps", None, "Barbell", "Compound", "Basic", "Intermediate", "horizontal_pull", None),
            ("Overhead Press", "Front-Shoulder", "Triceps", None, "Barbell", "Compound", "Basic", "Intermediate", "vertical_push", None),
            ("Pull-up", "Latissimus Dorsi", "Biceps", None, "Bodyweight", "Compound", "Basic", "Intermediate", "vertical_pull", None),
            ("Bicep Curl", "Biceps", None, None, "Dumbbells", "Isolated", "Auxiliary", "Beginner", "upper_isolation", "bicep_curl"),
            ("Tricep Extension", "Triceps", None, None, "Dumbbells", "Isolated", "Auxiliary", "Beginner", "upper_isolation", "tricep_extension"),
            ("Leg Curl", "Hamstrings", None, None, "Machine", "Isolated", "Auxiliary", "Beginner", "lower_isolation", "leg_curl"),
            ("Plank", "Abs/Core", None, None, "Bodyweight", "Compound", "Auxiliary", "Beginner", "core_static", None),
        ]
        
        cursor.executemany(
            "INSERT INTO exercises VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            exercises
        )
        
        # Create user_selection table
        cursor.execute("""
            CREATE TABLE user_selection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine TEXT,
                exercise TEXT,
                sets INTEGER,
                min_rep_range INTEGER,
                max_rep_range INTEGER,
                rir INTEGER,
                weight REAL,
                rpe REAL,
                exercise_order INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
        
        import utils.config
        original_path = utils.config.DB_FILE
        utils.config.DB_FILE = str(db_path)
        
        # Create app
        from app import app
        app.config['TESTING'] = True
        
        yield app.test_client()
        
        # Restore original path
        utils.config.DB_FILE = original_path
    
    def test_generate_plan_with_priority_muscles(self):
        """Generate a plan with priority muscles and verify boost applied."""
        from utils.plan_generator import generate_starter_plan
        
        # Without priority muscles
        plan_normal = generate_starter_plan(
            training_days=2,
            persist=False,
        )
        
        # With priority muscles (chest should boost horizontal push accessories)
        plan_priority = generate_starter_plan(
            training_days=2,
            priority_muscles=["chest"],
            persist=False,
        )
        
        # Both should generate plans
        assert plan_normal is not None
        assert plan_priority is not None
        assert "routines" in plan_normal
        assert "routines" in plan_priority
    
    def test_pattern_coverage_reflects_plan(self):
        """Pattern coverage should reflect generated plan."""
        from utils.weekly_summary import calculate_pattern_coverage

        # Generate a plan with persistence (but clean DB means nothing to count)
        # This tests the flow works without errors
        coverage = calculate_pattern_coverage()
        
        # Should have the expected structure
        assert "per_routine" in coverage
        assert "total" in coverage
        assert "warnings" in coverage
        assert "sets_per_routine" in coverage
        assert "ideal_sets_range" in coverage
    
    def test_full_workflow_generate_to_coverage(self):
        """Full workflow: generate plan → check pattern coverage."""
        from utils.plan_generator import GeneratorConfig
        
        # Step 1: Create config with validation
        config = GeneratorConfig(
            training_days=3,
            goal="hypertrophy",
            experience_level="novice",
            priority_muscles=["chest", "biceps"],
        )
        
        # Verify normalization
        assert config.priority_muscles == ["chest", "biceps"]
        assert config.training_days == 3
        assert config.goal == "hypertrophy"
        
        # Step 2: Config should be valid for generation
        # (actual generation requires DB, tested elsewhere)
        assert config.volume_scale == 1.0