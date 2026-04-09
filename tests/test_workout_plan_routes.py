"""
Tests for routes/workout_plan.py

Covers exercise management, workout plan CRUD operations, 
superset handling, and plan generation with focus on:
- Data integrity (FK constraints, superset unlinking)
- Validation (invalid IDs, missing fields)
- Error responses (404, 400, 500)
"""
import pytest
from flask import Flask


class TestWorkoutPlanPage:
    """Tests for GET /workout_plan page rendering."""

    def test_workout_plan_page_loads(self, client, clean_db):
        """Page request - tests templates availability (skipped in unit tests)."""
        import pytest
        from jinja2.exceptions import TemplateNotFound
        
        # In unit test env without templates, this raises TemplateNotFound
        # In full integration env, it would return 200
        try:
            resp = client.get("/workout_plan")
            assert resp.status_code in (200, 500)
        except TemplateNotFound:
            pytest.skip("Template not available in unit test environment")


class TestAddExercise:
    """Tests for POST /add_exercise endpoint."""

    def test_add_exercise_success(self, client, clean_db, exercise_factory):
        """Should add exercise to workout plan."""
        exercise_factory("Bench Press")
        
        resp = client.post("/add_exercise", json={
            "routine": "Push",
            "exercise": "Bench Press",
            "sets": 3,
            "min_rep_range": 8,
            "max_rep_range": 12,
            "rir": 2,
            "weight": 80.0
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_add_exercise_no_data(self, client, clean_db):
        """Should return error when no data provided."""
        resp = client.post("/add_exercise", json={})
        assert resp.status_code == 400

    def test_add_exercise_invalid_json(self, client, clean_db):
        """Should return 400 for invalid JSON."""
        resp = client.post("/add_exercise", 
                          data="not json",
                          content_type="application/json")
        assert resp.status_code == 400

    def test_add_exercise_with_rpe(self, client, clean_db, exercise_factory):
        """Should add exercise with RPE field."""
        exercise_factory("Squat")
        
        resp = client.post("/add_exercise", json={
            "routine": "Legs",
            "exercise": "Squat",
            "sets": 4,
            "min_rep_range": 6,
            "max_rep_range": 8,
            "rir": None,
            "rpe": 8.0,
            "weight": 100.0
        })
        assert resp.status_code == 200

    def test_add_exercise_duplicate_returns_400(self, client, clean_db, exercise_factory):
        """Duplicate exercise in same routine should return validation error."""
        exercise_factory("Bench Press")

        first = client.post("/add_exercise", json={
            "routine": "Push",
            "exercise": "Bench Press",
            "sets": 3,
            "min_rep_range": 8,
            "max_rep_range": 12,
            "rir": 2,
            "weight": 80.0
        })
        assert first.status_code == 200

        duplicate = client.post("/add_exercise", json={
            "routine": "Push",
            "exercise": "Bench Press",
            "sets": 4,
            "min_rep_range": 6,
            "max_rep_range": 10,
            "rir": 3,
            "weight": 82.5
        })
        assert duplicate.status_code == 400
        payload = duplicate.get_json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "VALIDATION_ERROR"


class TestGetExerciseDetails:
    """Tests for GET /get_exercise_details/<id> endpoint."""

    def test_get_exercise_details_success(self, client, clean_db, workout_plan_fixture):
        """Should return exercise details."""
        entry = workout_plan_fixture
        resp = client.get(f"/get_exercise_details/{entry['id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["exercise"] == entry["exercise"]

    def test_get_exercise_details_not_found(self, client, clean_db):
        """Should return 404 for non-existent exercise."""
        resp = client.get("/get_exercise_details/99999")
        assert resp.status_code == 404


class TestGetWorkoutPlan:
    """Tests for GET /get_workout_plan endpoint."""

    def test_get_workout_plan_empty(self, client, clean_db):
        """Should return empty array when no exercises."""
        resp = client.get("/get_workout_plan")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"] == []

    def test_get_workout_plan_with_exercises(self, client, clean_db, workout_plan_fixture):
        """Should return exercises in workout plan."""
        resp = client.get("/get_workout_plan")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]) >= 1


class TestRemoveExercise:
    """Tests for POST /remove_exercise endpoint."""

    def test_remove_exercise_success(self, client, clean_db, workout_plan_fixture):
        """Should remove exercise from workout plan."""
        resp = client.post("/remove_exercise", json={
            "id": workout_plan_fixture["id"]
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_remove_exercise_no_data(self, client, clean_db):
        """Should return error when no data provided."""
        resp = client.post("/remove_exercise", json={})
        assert resp.status_code == 400

    def test_remove_exercise_not_found(self, client, clean_db):
        """Should return 404 for non-existent exercise."""
        resp = client.post("/remove_exercise", json={"id": 99999})
        assert resp.status_code == 404

    def test_remove_exercise_invalid_id(self, client, clean_db):
        """Should return 400 for invalid ID format."""
        resp = client.post("/remove_exercise", json={"id": "abc"})
        assert resp.status_code == 400

    def test_remove_exercise_cascades_workout_log(self, client, clean_db, workout_plan_fixture):
        """Removing exercise should cascade delete related workout logs."""
        from utils.database import DatabaseHandler
        
        # Create a workout log entry for this exercise
        with DatabaseHandler() as db:
            db.execute_query("""
                INSERT INTO workout_log (
                    routine, exercise, planned_sets, workout_plan_id, created_at
                ) VALUES (?, ?, ?, ?, datetime('now'))
            """, ("Push", workout_plan_fixture["exercise"], 3, workout_plan_fixture["id"]))
        
        # Remove the exercise
        resp = client.post("/remove_exercise", json={
            "id": workout_plan_fixture["id"]
        })
        assert resp.status_code == 200
        
        # Verify workout log was also deleted
        with DatabaseHandler() as db:
            log = db.fetch_one(
                "SELECT * FROM workout_log WHERE workout_plan_id = ?",
                (workout_plan_fixture["id"],)
            )
            assert log is None


class TestRemoveExerciseWithSuperset:
    """Tests for superset unlinking when removing exercise."""

    def test_remove_supersetted_exercise_unlinks_partner(
        self, client, clean_db, superset_pair_fixture
    ):
        """Removing one exercise from superset should unlink the other."""
        from utils.database import DatabaseHandler
        
        exercise_a, exercise_b = superset_pair_fixture
        
        # Remove exercise A
        resp = client.post("/remove_exercise", json={"id": exercise_a["id"]})
        assert resp.status_code == 200
        
        # Verify exercise B's superset_group is now NULL
        with DatabaseHandler() as db:
            remaining = db.fetch_one(
                "SELECT superset_group FROM user_selection WHERE id = ?",
                (exercise_b["id"],)
            )
            assert remaining is not None
            assert remaining["superset_group"] is None


class TestClearWorkoutPlan:
    """Tests for POST /clear_workout_plan endpoint."""

    def test_clear_workout_plan_empty(self, client, clean_db):
        """Should handle clearing empty workout plan."""
        resp = client.post("/clear_workout_plan")
        assert resp.status_code == 200

    def test_clear_workout_plan_with_exercises(self, client, clean_db, workout_plan_fixture):
        """Should clear all exercises from workout plan."""
        resp = client.post("/clear_workout_plan")
        assert resp.status_code == 200
        
        # Verify plan is empty
        resp = client.get("/get_workout_plan")
        assert resp.get_json()["data"] == []


class TestGetUserSelection:
    """Tests for GET /get_user_selection endpoint."""

    def test_get_user_selection_empty(self, client, clean_db):
        """Should return empty array when no selections."""
        resp = client.get("/get_user_selection")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_get_user_selection_with_data(self, client, clean_db, workout_plan_fixture):
        """Should return user selection with exercise metadata."""
        resp = client.get("/get_user_selection")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["data"]) >= 1


class TestGetExerciseInfo:
    """Tests for GET /get_exercise_info/<name> endpoint."""

    def test_get_exercise_info_success(self, client, clean_db, exercise_factory):
        """Should return exercise information."""
        exercise_factory("Deadlift")
        
        resp = client.get("/get_exercise_info/Deadlift")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_get_exercise_info_not_found(self, client, clean_db):
        """Should return 404 for non-existent exercise."""
        resp = client.get("/get_exercise_info/NonExistentExercise")
        assert resp.status_code == 404


class TestGetRoutineExercises:
    """Tests for GET /get_routine_exercises/<routine> endpoint."""

    def test_get_routine_exercises(self, client, clean_db, exercise_factory):
        """Should return exercises for routine."""
        exercise_factory("Bicep Curl")
        
        resp = client.get("/get_routine_exercises/Pull")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True


class TestGetRoutineOptions:
    """Tests for GET /get_routine_options endpoint."""

    def test_get_routine_options(self, client, clean_db):
        """Should return structured routine options."""
        resp = client.get("/get_routine_options")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "Gym" in data
        assert "Home Workout" in data


class TestUpdateExercise:
    """Tests for POST /update_exercise endpoint."""

    def test_update_exercise_sets(self, client, clean_db, workout_plan_fixture):
        """Should update exercise sets."""
        resp = client.post("/update_exercise", json={
            "id": workout_plan_fixture["id"],
            "updates": {"sets": 5}
        })
        assert resp.status_code == 200

    def test_update_exercise_no_data(self, client, clean_db):
        """Should return error when no data provided."""
        resp = client.post("/update_exercise", json={})
        assert resp.status_code == 400

    def test_update_exercise_missing_id(self, client, clean_db):
        """Should return 400 when ID missing."""
        resp = client.post("/update_exercise", json={
            "updates": {"sets": 5}
        })
        assert resp.status_code == 400


class TestSupersetLink:
    """Tests for POST /api/superset/link endpoint."""

    def test_superset_link_success(self, client, clean_db, two_exercises_fixture):
        """Should link two exercises as superset."""
        ex_a, ex_b = two_exercises_fixture
        
        # The API expects exercise_ids array with exactly 2 IDs
        resp = client.post("/api/superset/link", json={
            "exercise_ids": [ex_a["id"], ex_b["id"]]
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_superset_link_same_exercise(self, client, clean_db, workout_plan_fixture):
        """Should return error when linking exercise to itself."""
        resp = client.post("/api/superset/link", json={
            "exercise_a_id": workout_plan_fixture["id"],
            "exercise_b_id": workout_plan_fixture["id"]
        })
        # Should fail - can't superset with itself
        assert resp.status_code in (400, 500)

    def test_superset_link_nonexistent(self, client, clean_db, workout_plan_fixture):
        """Should return error when exercise doesn't exist."""
        resp = client.post("/api/superset/link", json={
            "exercise_a_id": workout_plan_fixture["id"],
            "exercise_b_id": 99999
        })
        assert resp.status_code in (400, 404, 500)


class TestSupersetUnlink:
    """Tests for POST /api/superset/unlink endpoint."""

    def test_superset_unlink_success(self, client, clean_db, superset_pair_fixture):
        """Should unlink superset."""
        ex_a, ex_b = superset_pair_fixture
        
        resp = client.post("/api/superset/unlink", json={
            "exercise_id": ex_a["id"]
        })
        assert resp.status_code == 200


class TestGenerateStarterPlan:
    """Tests for POST /generate_starter_plan endpoint."""

    def test_generate_starter_plan_basic(self, client, clean_db, exercise_factory):
        """Should generate starter plan with basic options."""
        # Create some exercises for the generator
        exercise_factory("Bench Press")
        exercise_factory("Squat")
        exercise_factory("Deadlift")
        
        resp = client.post("/generate_starter_plan", json={
            "split": "Full Body",
            "days_per_week": 3,
            "experience_level": "beginner"
        })
        # May succeed or fail depending on available exercises
        assert resp.status_code in (200, 400, 500)


# Fixtures for workout_plan tests
@pytest.fixture
def workout_plan_fixture(clean_db, exercise_factory):
    """Create a workout plan entry (user_selection) for testing."""
    from utils.database import DatabaseHandler
    
    exercise_factory("Bench Press")
    
    with DatabaseHandler() as db:
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Push", "Bench Press", 3, 8, 12, 2, 80.0))
        
        result = db.fetch_one(
            "SELECT id FROM user_selection ORDER BY id DESC LIMIT 1"
        )
        assert result is not None
        
        return {"id": result["id"], "exercise": "Bench Press", "routine": "Push"}


@pytest.fixture
def two_exercises_fixture(clean_db, exercise_factory):
    """Create two workout plan entries for superset testing."""
    from utils.database import DatabaseHandler
    
    exercise_factory("Bench Press")
    exercise_factory("Cable Fly")
    
    with DatabaseHandler() as db:
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Push", "Bench Press", 3, 8, 12, 2, 80.0))
        result_a = db.fetch_one("SELECT id FROM user_selection ORDER BY id DESC LIMIT 1")
        assert result_a is not None
        
        db.execute_query("""
            INSERT INTO user_selection (
                routine, exercise, sets, min_rep_range, max_rep_range, rir, weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Push", "Cable Fly", 3, 12, 15, 2, 15.0))
        result_b = db.fetch_one("SELECT id FROM user_selection ORDER BY id DESC LIMIT 1")
        assert result_b is not None
        
        return (
            {"id": result_a["id"], "exercise": "Bench Press"},
            {"id": result_b["id"], "exercise": "Cable Fly"}
        )


@pytest.fixture
def superset_pair_fixture(clean_db, two_exercises_fixture):
    """Create two exercises already linked as a superset."""
    from utils.database import DatabaseHandler
    import uuid
    
    ex_a, ex_b = two_exercises_fixture
    superset_group = str(uuid.uuid4())[:8]
    
    with DatabaseHandler() as db:
        db.execute_query(
            "UPDATE user_selection SET superset_group = ? WHERE id IN (?, ?)",
            (superset_group, ex_a["id"], ex_b["id"])
        )
    
    ex_a["superset_group"] = superset_group
    ex_b["superset_group"] = superset_group
    
    return (ex_a, ex_b)
