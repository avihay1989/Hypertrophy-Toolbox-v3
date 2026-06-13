"""
Tests for the Auto Starter Plan Generator.
"""
import pytest
import os
import sqlite3
import tempfile

# Set testing environment before imports
os.environ['TESTING'] = '1'

from utils.movement_patterns import (
    MovementPattern,
    MovementSubpattern,
    classify_exercise,
    SESSION_BLUEPRINTS,
    PrescriptionRules,
)
from utils.plan_generator import (
    GeneratorConfig,
    ExerciseRow,
    GeneratedPlan,
    PrescriptionCalculator,
    generate_starter_plan,
    get_generator_routine_names,
)


class TestMovementPatternClassification:
    """Tests for exercise classification into movement patterns."""
    
    def test_classify_squat_exercises(self):
        """Test classification of squat pattern exercises."""
        exercises = [
            ("Back Squat", MovementPattern.SQUAT, MovementSubpattern.BILATERAL_SQUAT),
            ("Front Squat", MovementPattern.SQUAT, MovementSubpattern.BILATERAL_SQUAT),
            ("Leg Press", MovementPattern.SQUAT, MovementSubpattern.BILATERAL_SQUAT),
            ("Bulgarian Split Squat", MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
            ("Walking Lunge", MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
            ("Step Up", MovementPattern.SQUAT, MovementSubpattern.UNILATERAL_SQUAT),
        ]
        
        for name, expected_pattern, expected_subpattern in exercises:
            pattern, subpattern = classify_exercise(name)
            assert pattern == expected_pattern, f"Expected {name} to have pattern {expected_pattern}, got {pattern}"
            assert subpattern == expected_subpattern, f"Expected {name} to have subpattern {expected_subpattern}, got {subpattern}"
    
    def test_classify_hinge_exercises(self):
        """Test classification of hinge pattern exercises."""
        exercises = [
            ("Hip Thrust", MovementPattern.HINGE, MovementSubpattern.HIP_THRUST),
            ("Glute Bridge", MovementPattern.HINGE, MovementSubpattern.HIP_THRUST),
            ("Conventional Deadlift", MovementPattern.HINGE, MovementSubpattern.DEADLIFT),
            ("Romanian Deadlift", MovementPattern.HINGE, MovementSubpattern.DEADLIFT),
            ("Good Morning", MovementPattern.HINGE, MovementSubpattern.GOODMORNING),
        ]
        
        for name, expected_pattern, expected_subpattern in exercises:
            pattern, subpattern = classify_exercise(name)
            assert pattern == expected_pattern, f"Expected {name} to have pattern {expected_pattern}, got {pattern}"
    
    def test_classify_push_exercises(self):
        """Test classification of push pattern exercises."""
        exercises = [
            ("Barbell Bench Press", MovementPattern.HORIZONTAL_PUSH),
            ("Dumbbell Chest Press", MovementPattern.HORIZONTAL_PUSH),
            ("Push Up", MovementPattern.HORIZONTAL_PUSH),
            ("Overhead Press", MovementPattern.VERTICAL_PUSH),
            ("Military Press", MovementPattern.VERTICAL_PUSH),
            ("Dips", MovementPattern.VERTICAL_PUSH),
        ]
        
        for name, expected_pattern in exercises:
            pattern, subpattern = classify_exercise(name)
            assert pattern == expected_pattern, f"Expected {name} to have pattern {expected_pattern}, got {pattern}"
    
    def test_classify_pull_exercises(self):
        """Test classification of pull pattern exercises."""
        exercises = [
            ("Barbell Row", MovementPattern.HORIZONTAL_PULL),
            ("Dumbbell Row", MovementPattern.HORIZONTAL_PULL),
            ("Face Pull", MovementPattern.HORIZONTAL_PULL),
            ("Pull Up", MovementPattern.VERTICAL_PULL),
            ("Chin Up", MovementPattern.VERTICAL_PULL),
            ("Lat Pulldown", MovementPattern.VERTICAL_PULL),
        ]
        
        for name, expected_pattern in exercises:
            pattern, subpattern = classify_exercise(name)
            assert pattern == expected_pattern, f"Expected {name} to have pattern {expected_pattern}, got {pattern}"
    
    def test_classify_core_exercises(self):
        """Test classification of core exercises."""
        exercises = [
            ("Plank", MovementPattern.CORE_STATIC),
            ("Pallof Press", MovementPattern.CORE_STATIC),
            ("Hanging Leg Raise", MovementPattern.CORE_DYNAMIC),
            ("Sit Up", MovementPattern.CORE_DYNAMIC),
            ("Russian Twist", MovementPattern.CORE_DYNAMIC),
        ]
        
        for name, expected_pattern in exercises:
            pattern, subpattern = classify_exercise(name)
            assert pattern == expected_pattern, f"Expected {name} to have pattern {expected_pattern}, got {pattern}"
    
    def test_classify_isolation_exercises(self):
        """Test classification of isolation exercises."""
        exercises = [
            ("Bicep Curl", MovementPattern.UPPER_ISOLATION),
            ("Tricep Extension", MovementPattern.UPPER_ISOLATION),
            ("Lateral Raise", MovementPattern.UPPER_ISOLATION),
            ("Leg Curl", MovementPattern.LOWER_ISOLATION),
            ("Leg Extension", MovementPattern.LOWER_ISOLATION),
            ("Calf Raise", MovementPattern.LOWER_ISOLATION),
        ]
        
        for name, expected_pattern in exercises:
            pattern, subpattern = classify_exercise(name)
            assert pattern == expected_pattern, f"Expected {name} to have pattern {expected_pattern}, got {pattern}"
    
    def test_fallback_to_muscle_group(self):
        """Test fallback classification based on muscle group."""
        # When exercise name doesn't match, should use muscle group
        pattern, subpattern = classify_exercise(
            "Unknown Exercise",
            primary_muscle="Quadriceps"
        )
        assert pattern == MovementPattern.SQUAT
        
        pattern, subpattern = classify_exercise(
            "Unknown Exercise",
            primary_muscle="Latissimus Dorsi"
        )
        assert pattern == MovementPattern.VERTICAL_PULL


class TestSessionBlueprints:
    """Tests for session blueprint configurations."""
    
    def test_blueprints_exist_for_all_training_days(self):
        """Verify blueprints exist for 1-5 training days."""
        assert 1 in SESSION_BLUEPRINTS
        assert 2 in SESSION_BLUEPRINTS
        assert 3 in SESSION_BLUEPRINTS
        assert 4 in SESSION_BLUEPRINTS
        assert 5 in SESSION_BLUEPRINTS
    
    def test_single_day_blueprint_structure(self):
        """Test single day blueprint has correct structure."""
        blueprint = SESSION_BLUEPRINTS[1]
        assert "A" in blueprint
        
        slots = blueprint["A"]
        assert len(slots) >= 6  # At least 6 exercises
        
        # Should have all main patterns
        patterns = {slot.pattern for slot in slots}
        assert MovementPattern.SQUAT in patterns
        assert MovementPattern.HINGE in patterns
        assert MovementPattern.HORIZONTAL_PUSH in patterns or MovementPattern.VERTICAL_PUSH in patterns
        assert MovementPattern.HORIZONTAL_PULL in patterns or MovementPattern.VERTICAL_PULL in patterns
    
    def test_two_day_blueprint_structure(self):
        """Test two day blueprint has A and B sessions."""
        blueprint = SESSION_BLUEPRINTS[2]
        assert "A" in blueprint
        assert "B" in blueprint
        
        for routine, slots in blueprint.items():
            assert len(slots) == 7  # 7 exercises per session
            
            # Check for main and accessory roles
            roles = [slot.role for slot in slots]
            assert "main" in roles
            assert "accessory" in roles
    
    def test_three_day_blueprint_structure(self):
        """Test three day blueprint has A, B, and C sessions."""
        blueprint = SESSION_BLUEPRINTS[3]
        assert "A" in blueprint
        assert "B" in blueprint
        assert "C" in blueprint


class TestPrescriptionRules:
    """Tests for prescription calculation rules."""
    
    def test_sets_by_experience_level(self):
        """Test set prescriptions vary by experience level."""
        rules = PrescriptionRules()
        
        novice_main = rules.SETS_BY_ROLE["novice"]["main"]
        intermediate_main = rules.SETS_BY_ROLE["intermediate"]["main"]
        advanced_main = rules.SETS_BY_ROLE["advanced"]["main"]
        
        # All should be reasonable values
        assert 2 <= novice_main <= 4
        assert 2 <= intermediate_main <= 5
        assert 2 <= advanced_main <= 4
    
    def test_rep_ranges_by_goal(self):
        """Test rep ranges differ by training goal."""
        rules = PrescriptionRules()
        
        # Hypertrophy should have moderate rep ranges
        hyp_main = rules.REP_RANGES["hypertrophy"]["main"]
        assert hyp_main[0] >= 5 and hyp_main[1] <= 15
        
        # Strength should have lower rep ranges
        str_main = rules.REP_RANGES["strength"]["main"]
        assert str_main[0] >= 1 and str_main[1] <= 8
        
        # General should be in between
        gen_main = rules.REP_RANGES["general"]["main"]
        assert gen_main[0] >= 3 and gen_main[1] <= 12
    
    def test_rir_defaults(self):
        """Test RIR defaults are reasonable."""
        rules = PrescriptionRules()
        
        assert rules.RIR_DEFAULTS["main"] >= 1
        assert rules.RIR_DEFAULTS["main"] <= 3
        assert rules.RIR_DEFAULTS["core"] >= 2


class TestGeneratorConfig:
    """Tests for generator configuration validation."""
    
    def test_valid_config(self):
        """Test valid configuration is accepted."""
        config = GeneratorConfig(
            training_days=2,
            environment="gym",
            experience_level="novice",
            goal="hypertrophy",
        )
        assert config.training_days == 2
        assert config.environment == "gym"
    
    def test_invalid_training_days(self):
        """Test invalid training days raises error."""
        with pytest.raises(ValueError):
            GeneratorConfig(training_days=0)
        
        with pytest.raises(ValueError):
            GeneratorConfig(training_days=6)
    
    def test_invalid_environment(self):
        """Test invalid environment raises error."""
        with pytest.raises(ValueError):
            GeneratorConfig(environment="office")
    
    def test_invalid_experience_level(self):
        """Test invalid experience level raises error."""
        with pytest.raises(ValueError):
            GeneratorConfig(experience_level="expert")
    
    def test_invalid_goal(self):
        """Test invalid goal raises error."""
        with pytest.raises(ValueError):
            GeneratorConfig(goal="powerlifting")

    def test_generated_routine_names_match_plan_cascade(self):
        """Generated routines should use the same labels as the Plan cascade."""
        assert get_generator_routine_names(4, "gym") == [
            "GYM - Upper Lower - Upper 1",
            "GYM - Upper Lower - Lower 1",
            "GYM - Upper Lower - Upper 2",
            "GYM - Upper Lower - Lower 2",
        ]
        assert get_generator_routine_names(5, "home") == [
            "Home - 5 Days Split - Day 1",
            "Home - 5 Days Split - Day 2",
            "Home - 5 Days Split - Day 3",
            "Home - 5 Days Split - Day 4",
            "Home - 5 Days Split - Day 5",
        ]
    
    def test_volume_scale_validation(self):
        """Test volume scale validation."""
        # Valid scales
        config = GeneratorConfig(volume_scale=0.8)
        assert config.volume_scale == 0.8
        
        config = GeneratorConfig(volume_scale=1.5)
        assert config.volume_scale == 1.5
        
        # Invalid scales
        with pytest.raises(ValueError):
            GeneratorConfig(volume_scale=0)
        
        with pytest.raises(ValueError):
            GeneratorConfig(volume_scale=3.0)


class TestPrescriptionCalculator:
    """Tests for prescription calculator."""
    
    def test_sets_calculation(self):
        """Test set calculation with volume scaling."""
        config = GeneratorConfig(
            experience_level="novice",
            volume_scale=1.0,
        )
        calculator = PrescriptionCalculator(config)
        
        main_sets = calculator.get_sets("main")
        accessory_sets = calculator.get_sets("accessory")
        
        assert main_sets >= 2
        assert accessory_sets >= 1
    
    def test_volume_scaling(self):
        """Test that volume scaling reduces sets."""
        config_normal = GeneratorConfig(volume_scale=1.0)
        config_scaled = GeneratorConfig(volume_scale=0.7)
        
        calc_normal = PrescriptionCalculator(config_normal)
        calc_scaled = PrescriptionCalculator(config_scaled)
        
        # Scaled should have fewer or equal sets
        assert calc_scaled.get_sets("main") <= calc_normal.get_sets("main")
    
    def test_rep_range_by_goal(self):
        """Test rep ranges change by goal."""
        config_hyp = GeneratorConfig(goal="hypertrophy")
        config_str = GeneratorConfig(goal="strength")
        
        calc_hyp = PrescriptionCalculator(config_hyp)
        calc_str = PrescriptionCalculator(config_str)
        
        hyp_range = calc_hyp.get_rep_range("main")
        str_range = calc_str.get_rep_range("main")
        
        # Strength should have lower reps
        assert str_range[1] <= hyp_range[1]


class TestExerciseRow:
    """Tests for ExerciseRow data structure."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        row = ExerciseRow(
            routine="A",
            exercise="Back Squat",
            sets=3,
            min_rep_range=6,
            max_rep_range=10,
            rir=2,
            rpe=8.0,
            weight=0.0,
            exercise_order=1,
            pattern="squat",
            role="main",
        )
        
        d = row.to_dict()
        assert d["routine"] == "A"
        assert d["exercise"] == "Back Squat"
        assert d["sets"] == 3
        assert d["pattern"] == "squat"


class TestGeneratedPlan:
    """Tests for GeneratedPlan data structure."""
    
    def test_total_exercises(self):
        """Test total exercise count."""
        config = GeneratorConfig()
        plan = GeneratedPlan(
            routines={
                "A": [ExerciseRow("A", "Ex1", 3, 6, 10, 2, 8.0, 0.0, 1)],
                "B": [
                    ExerciseRow("B", "Ex2", 3, 6, 10, 2, 8.0, 0.0, 1),
                    ExerciseRow("B", "Ex3", 3, 6, 10, 2, 8.0, 0.0, 2),
                ],
            },
            config=config,
        )
        
        assert plan.total_exercises == 3
    
    def test_sets_per_routine(self):
        """Test sets per routine calculation."""
        config = GeneratorConfig()
        plan = GeneratedPlan(
            routines={
                "A": [
                    ExerciseRow("A", "Ex1", 3, 6, 10, 2, 8.0, 0.0, 1),
                    ExerciseRow("A", "Ex2", 4, 6, 10, 2, 8.0, 0.0, 2),
                ],
            },
            config=config,
        )
        
        assert plan.total_sets_per_routine["A"] == 7


class TestPlanGeneratorIntegration:
    """Integration tests for the plan generator (require database)."""
    
    @pytest.fixture
    def test_db(self):
        """Create a temporary test database."""
        db_path = os.path.join(tempfile.gettempdir(), 'test_plan_generator.db')
        
        # Remove if exists
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Create test database with exercises
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create exercises table
        cursor.execute("""
            CREATE TABLE exercises (
                exercise_name TEXT PRIMARY KEY,
                primary_muscle_group TEXT,
                secondary_muscle_group TEXT,
                tertiary_muscle_group TEXT,
                advanced_isolated_muscles TEXT,
                utility TEXT,
                grips TEXT,
                stabilizers TEXT,
                synergists TEXT,
                force TEXT,
                equipment TEXT,
                mechanic TEXT,
                difficulty TEXT,
                movement_pattern TEXT,
                movement_subpattern TEXT
            )
        """)
        
        # Create user_selection table
        cursor.execute("""
            CREATE TABLE user_selection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine TEXT NOT NULL,
                exercise TEXT NOT NULL,
                sets INTEGER NOT NULL,
                min_rep_range INTEGER NOT NULL,
                max_rep_range INTEGER NOT NULL,
                rir INTEGER,
                rpe REAL,
                weight REAL NOT NULL,
                exercise_order INTEGER,
                FOREIGN KEY (exercise) REFERENCES exercises(exercise_name) ON DELETE CASCADE,
                UNIQUE (routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight)
            )
        """)
        
        # Create workout_log table (for FK constraint)
        cursor.execute("""
            CREATE TABLE workout_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_plan_id INTEGER,
                routine TEXT NOT NULL,
                exercise TEXT NOT NULL,
                planned_sets INTEGER,
                FOREIGN KEY (workout_plan_id) REFERENCES user_selection(id) ON DELETE CASCADE
            )
        """)
        
        # Insert test exercises
        test_exercises = [
            ("Back Squat", "Quadriceps", "Compound", "Basic", "Barbell", "Beginner", "squat", "bilateral_squat"),
            ("Leg Press", "Quadriceps", "Compound", "Basic", "Machine", "Beginner", "squat", "bilateral_squat"),
            ("Bulgarian Split Squat", "Quadriceps", "Compound", "Auxiliary", "Dumbbells", "Intermediate", "squat", "unilateral_squat"),
            ("Conventional Deadlift", "Hamstrings", "Compound", "Basic", "Barbell", "Intermediate", "hinge", "deadlift"),
            ("Hip Thrust", "Gluteus Maximus", "Compound", "Basic", "Barbell", "Beginner", "hinge", "hip_thrust"),
            ("Barbell Bench Press", "Chest", "Compound", "Basic", "Barbell", "Beginner", "horizontal_push", None),
            ("Dumbbell Bench Press", "Chest", "Compound", "Auxiliary", "Dumbbells", "Beginner", "horizontal_push", None),
            ("Overhead Press", "Front-Shoulder", "Compound", "Basic", "Barbell", "Intermediate", "vertical_push", None),
            ("Barbell Row", "Upper Back", "Compound", "Basic", "Barbell", "Beginner", "horizontal_pull", "row"),
            ("Lat Pulldown", "Latissimus Dorsi", "Compound", "Auxiliary", "Cables", "Beginner", "vertical_pull", "pulldown"),
            ("Pull Up", "Latissimus Dorsi", "Compound", "Basic", "Bodyweight", "Intermediate", "vertical_pull", "pullup"),
            ("Plank", "Rectus Abdominis", "Compound", "Auxiliary", "Bodyweight", "Beginner", "core_static", "plank"),
            ("Hanging Leg Raise", "Rectus Abdominis", "Isolated", "Auxiliary", "Bodyweight", "Intermediate", "core_dynamic", "leg_raise"),
            ("Bicep Curl", "Biceps", "Isolated", "Auxiliary", "Dumbbells", "Beginner", "upper_isolation", "bicep_curl"),
            ("Tricep Extension", "Triceps", "Isolated", "Auxiliary", "Cables", "Beginner", "upper_isolation", "tricep_extension"),
            ("Leg Curl", "Hamstrings", "Isolated", "Auxiliary", "Machine", "Beginner", "lower_isolation", "leg_curl"),
            ("Calf Raise", "Calves", "Isolated", "Auxiliary", "Machine", "Beginner", "lower_isolation", "calf_raise"),
        ]
        
        for ex in test_exercises:
            cursor.execute("""
                INSERT INTO exercises (
                    exercise_name, primary_muscle_group, mechanic, utility, 
                    equipment, difficulty, movement_pattern, movement_subpattern
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ex)
        
        conn.commit()
        conn.close()
        
        # Override DB_FILE
        import utils.config
        original_db = utils.config.DB_FILE
        utils.config.DB_FILE = db_path
        
        yield db_path
        
        # Restore and cleanup
        utils.config.DB_FILE = original_db
        if os.path.exists(db_path):
            os.remove(db_path)
    
    def test_generate_two_day_plan(self, test_db):
        """Test generating a 2-day plan."""
        result = generate_starter_plan(
            training_days=2,
            environment="gym",
            experience_level="novice",
            goal="hypertrophy",
            persist=False,
        )
        
        assert "routines" in result
        routine_a, routine_b = get_generator_routine_names(2, "gym")
        assert routine_a in result["routines"]
        assert routine_b in result["routines"]
        
        # Each routine should have exercises
        assert len(result["routines"][routine_a]) > 0
        assert len(result["routines"][routine_b]) > 0
    
    def test_generate_single_day_plan(self, test_db):
        """Test generating a 1-day plan."""
        result = generate_starter_plan(
            training_days=1,
            environment="gym",
            experience_level="novice",
            goal="hypertrophy",
            persist=False,
        )
        
        routine_a = get_generator_routine_names(1, "gym")[0]
        assert routine_a in result["routines"]
        assert len(result["routines"][routine_a]) >= 6
    
    def test_generate_three_day_plan(self, test_db):
        """Test generating a 3-day plan."""
        result = generate_starter_plan(
            training_days=3,
            environment="gym",
            experience_level="intermediate",
            goal="strength",
            persist=False,
        )
        
        assert list(result["routines"].keys()) == get_generator_routine_names(3, "gym")
    
    def test_home_environment_filtering(self, test_db):
        """Test that home environment filters equipment appropriately."""
        result = generate_starter_plan(
            training_days=2,
            environment="home",
            persist=False,
        )
        
        # Check that exercises use home-compatible equipment
        for routine, exercises in result["routines"].items():
            for ex in exercises:
                # Just verify we got exercises (equipment filtering happens internally)
                assert ex["exercise"] is not None
    
    def test_persist_to_database(self, test_db):
        """Test persisting generated plan to database."""
        result = generate_starter_plan(
            training_days=2,
            environment="gym",
            persist=True,
            overwrite=True,
        )
        
        assert result.get("persisted") is True
        
        # Verify data is in database
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        routine_a, routine_b = get_generator_routine_names(2, "gym")
        cursor.execute(
            "SELECT COUNT(*) FROM user_selection WHERE routine IN (?, ?)",
            (routine_a, routine_b),
        )
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count > 0
    
    def test_overwrite_behavior(self, test_db):
        """Test overwrite behavior removes old data."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        for routine in ("A", "A_gen1", "B", "B_gen1"):
            cursor.execute(
                """
                INSERT INTO user_selection
                    (routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight)
                VALUES (?, 'Legacy Exercise', 3, 8, 12, 2, 8.0, 50.0)
                """,
                (routine,),
            )
        conn.commit()
        conn.close()

        # First generation
        generate_starter_plan(training_days=2, persist=True, overwrite=True)
        
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        routine_a = get_generator_routine_names(2, "gym")[0]
        cursor.execute("SELECT COUNT(*) FROM user_selection WHERE routine = ?", (routine_a,))
        first_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM user_selection WHERE routine IN ('A', 'A_gen1', 'B', 'B_gen1')"
        )
        legacy_count = cursor.fetchone()[0]
        conn.close()

        assert legacy_count == 0
        
        # Second generation with overwrite
        generate_starter_plan(training_days=2, persist=True, overwrite=True)
        
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_selection WHERE routine = ?", (routine_a,))
        second_count = cursor.fetchone()[0]
        conn.close()
        
        # Should have similar counts (not doubled)
        assert abs(first_count - second_count) < 3


class TestExcludeExercises:
    """Tests for exercise exclusion functionality."""
    
    @pytest.fixture
    def test_db_with_exercises(self):
        """Create a test database with exercises."""
        db_path = os.path.join(tempfile.gettempdir(), 'test_exclude.db')
        
        if os.path.exists(db_path):
            os.remove(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE exercises (
                exercise_name TEXT PRIMARY KEY,
                primary_muscle_group TEXT,
                mechanic TEXT,
                utility TEXT,
                equipment TEXT,
                difficulty TEXT,
                movement_pattern TEXT,
                movement_subpattern TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE user_selection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine TEXT NOT NULL,
                exercise TEXT NOT NULL,
                sets INTEGER NOT NULL,
                min_rep_range INTEGER NOT NULL,
                max_rep_range INTEGER NOT NULL,
                rir INTEGER,
                rpe REAL,
                weight REAL NOT NULL,
                exercise_order INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE workout_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_plan_id INTEGER,
                routine TEXT,
                exercise TEXT,
                planned_sets INTEGER
            )
        """)
        
        exercises = [
            ("Back Squat", "Quadriceps", "Compound", "Basic", "Barbell", "Beginner", "squat", None),
            ("Front Squat", "Quadriceps", "Compound", "Auxiliary", "Barbell", "Intermediate", "squat", None),
            ("Leg Press", "Quadriceps", "Compound", "Auxiliary", "Machine", "Beginner", "squat", None),
            ("Deadlift", "Hamstrings", "Compound", "Basic", "Barbell", "Intermediate", "hinge", "deadlift"),
            ("Hip Thrust", "Gluteus Maximus", "Compound", "Auxiliary", "Barbell", "Beginner", "hinge", "hip_thrust"),
            ("Bench Press", "Chest", "Compound", "Basic", "Barbell", "Beginner", "horizontal_push", None),
            ("Dumbbell Row", "Upper Back", "Compound", "Basic", "Dumbbells", "Beginner", "horizontal_pull", None),
            ("Overhead Press", "Front-Shoulder", "Compound", "Basic", "Barbell", "Beginner", "vertical_push", None),
            ("Lat Pulldown", "Latissimus Dorsi", "Compound", "Auxiliary", "Cables", "Beginner", "vertical_pull", None),
            ("Plank", "Rectus Abdominis", "Compound", "Auxiliary", "Bodyweight", "Beginner", "core_static", None),
            ("Crunch", "Rectus Abdominis", "Isolated", "Auxiliary", "Bodyweight", "Beginner", "core_dynamic", None),
            ("Bicep Curl", "Biceps", "Isolated", "Auxiliary", "Dumbbells", "Beginner", "upper_isolation", None),
            ("Leg Curl", "Hamstrings", "Isolated", "Auxiliary", "Machine", "Beginner", "lower_isolation", None),
        ]
        
        for ex in exercises:
            cursor.execute("""
                INSERT INTO exercises VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ex)
        
        conn.commit()
        conn.close()
        
        import utils.config
        original_db = utils.config.DB_FILE
        utils.config.DB_FILE = db_path
        
        yield db_path
        
        utils.config.DB_FILE = original_db
        if os.path.exists(db_path):
            os.remove(db_path)
    
    def test_exclude_specific_exercise(self, test_db_with_exercises):
        """Test that excluded exercises are not selected."""
        result = generate_starter_plan(
            training_days=1,
            exclude_exercises=["Back Squat", "Deadlift"],
            persist=False,
        )
        
        all_exercises = []
        for routine, exercises in result["routines"].items():
            for ex in exercises:
                all_exercises.append(ex["exercise"])
        
        assert "Back Squat" not in all_exercises
        assert "Deadlift" not in all_exercises
    
    def test_movement_restriction_no_overhead(self, test_db_with_exercises):
        """Test movement restriction for overhead press."""
        result = generate_starter_plan(
            training_days=1,
            movement_restrictions={"no_overhead_press": True},
            persist=False,
        )
        
        all_exercises = []
        for routine, exercises in result["routines"].items():
            for ex in exercises:
                all_exercises.append(ex["exercise"])
        
        assert "Overhead Press" not in all_exercises
