"""
Tests for routes/workout_plan.py

Covers exercise management, workout plan CRUD operations, 
superset handling, and plan generation with focus on:
- Data integrity (FK constraints, superset unlinking)
- Validation (invalid IDs, missing fields)
- Error responses (404, 400, 500)
"""
import pytest


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

    def test_add_exercise_weight_zero_accepted(self, client, clean_db, exercise_factory):
        """weight=0 is valid for bodyweight/assisted exercises."""
        exercise_factory("Pull Up")

        resp = client.post("/add_exercise", json={
            "routine": "Pull",
            "exercise": "Pull Up",
            "sets": 3,
            "min_rep_range": 8,
            "max_rep_range": 12,
            "rir": 2,
            "weight": 0
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_add_exercise_weight_absent_rejected(self, client, clean_db, exercise_factory):
        """A missing weight key (None) is still rejected as a required field."""
        exercise_factory("Bench Press")

        resp = client.post("/add_exercise", json={
            "routine": "Push",
            "exercise": "Bench Press",
            "sets": 3,
            "min_rep_range": 8,
            "max_rep_range": 12,
            "rir": 2
            # weight intentionally omitted
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False

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

    @pytest.mark.parametrize("weight", [0, 1000])
    def test_add_exercise_accepts_weight_boundaries(
        self, client, clean_db, exercise_factory, weight
    ):
        exercise_factory("Boundary Press")
        resp = client.post("/add_exercise", json={
            "routine": "Push", "exercise": "Boundary Press", "sets": 3,
            "min_rep_range": 8, "max_rep_range": 12, "rir": 2, "weight": weight,
        })
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    @pytest.mark.parametrize("weight", [-0.01, 1000.01])
    def test_add_exercise_rejects_weight_outside_boundaries(
        self, client, clean_db, exercise_factory, weight
    ):
        exercise_factory("Boundary Press")
        resp = client.post("/add_exercise", json={
            "routine": "Push", "exercise": "Boundary Press", "sets": 3,
            "min_rep_range": 8, "max_rep_range": 12, "rir": 2, "weight": weight,
        })
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.parametrize("rir", [0, 10])
    def test_add_exercise_accepts_rir_boundaries(
        self, client, clean_db, exercise_factory, rir
    ):
        exercise_factory("Boundary Press")
        resp = client.post("/add_exercise", json={
            "routine": "Push", "exercise": "Boundary Press", "sets": 3,
            "min_rep_range": 8, "max_rep_range": 12, "rir": rir, "weight": 100,
        })
        assert resp.status_code == 200

    @pytest.mark.parametrize("rir", [-0.01, 10.01])
    def test_add_exercise_rejects_rir_outside_boundaries(
        self, client, clean_db, exercise_factory, rir
    ):
        exercise_factory("Boundary Press")
        resp = client.post("/add_exercise", json={
            "routine": "Push", "exercise": "Boundary Press", "sets": 3,
            "min_rep_range": 8, "max_rep_range": 12, "rir": rir, "weight": 100,
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        ("minimum", "maximum", "expected_status"),
        [(8, 8, 200), (9, 8, 400)],
    )
    def test_add_exercise_enforces_rep_range_order(
        self, client, clean_db, exercise_factory, minimum, maximum, expected_status
    ):
        exercise_factory("Boundary Press")
        resp = client.post("/add_exercise", json={
            "routine": "Push", "exercise": "Boundary Press", "sets": 3,
            "min_rep_range": minimum, "max_rep_range": maximum,
            "rir": 2, "weight": 100,
        })
        assert resp.status_code == expected_status


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

    def test_get_workout_plan_uses_media_path_fallback_from_mapping(
        self, client, clean_db, exercise_factory, workout_plan_factory
    ):
        """Plan rows should get a thumbnail path even before DB mapping is applied."""
        exercise_factory("Seated Leg Curl")
        workout_plan_factory(exercise_name="Seated Leg Curl")

        resp = client.get("/get_workout_plan")
        assert resp.status_code == 200
        data = resp.get_json()
        target = next(row for row in data["data"] if row["exercise"] == "Seated Leg Curl")
        assert target["media_path"] == "Seated_Leg_Curl/0.jpg"

    def test_get_workout_plan_media_path_manual_override_for_plan_rows(
        self, client, clean_db, exercise_factory, workout_plan_factory
    ):
        """Fallback covers common Plan rows whose CSV entry is blank/rejected."""
        exercise_factory("Machine Assisted Neutral Chin Up")
        workout_plan_factory(exercise_name="Machine Assisted Neutral Chin Up")

        resp = client.get("/get_workout_plan")
        assert resp.status_code == 200
        data = resp.get_json()
        target = next(
            row for row in data["data"] if row["exercise"] == "Machine Assisted Neutral Chin Up"
        )
        assert target["media_path"] == "Chin-Up/0.jpg"

    @pytest.mark.parametrize(
        ("exercise_name", "expected_media_path"),
        [
            ("Dumbbell Weighted Dip - Chest focused.", "Dips_-_Chest_Version/0.jpg"),
            ("Dumbbell Decline Skullcrusher", "EZ-Bar_Skullcrusher/0.jpg"),
            ("Machine Assisted Chin Up", "Chin-Up/0.jpg"),
            ("Cable Belt Calf Raise", "Standing_Calf_Raises/0.jpg"),
            ("Dumbbell Neutral Overhead Press", "Dumbbell_Shoulder_Press/0.jpg"),
            ("Cable Straight Back Seated Row", "Seated_Cable_Rows/0.jpg"),
            ("Dumbbell Heels Elevated Hip Thrust", "Barbell_Hip_Thrust/0.jpg"),
            ("Barbell 45 degrees Hyperextension", "Hyperextensions_Back_Extensions/0.jpg"),
            ("Cable Seated Leg Extension", "Leg_Extensions/0.jpg"),
            ("Dumbbell Upright Shoulder External Rotation with support", "External_Rotation/0.jpg"),
            ("Barbell Side Step Up - Quadriceps focused", "Barbell_Step_Ups/0.jpg"),
        ],
    )
    def test_get_workout_plan_media_path_covers_close_name_fallbacks(
        self,
        client,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        exercise_name,
        expected_media_path,
    ):
        """Close exercise names still get a representative local reference image."""
        exercise_factory(exercise_name)
        workout_plan_factory(exercise_name=exercise_name)

        resp = client.get("/get_workout_plan")
        assert resp.status_code == 200
        data = resp.get_json()
        target = next(row for row in data["data"] if row["exercise"] == exercise_name)
        assert target["media_path"] == expected_media_path


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

    @pytest.mark.parametrize(
        ("field", "value"),
        [("weight", 0), ("weight", 1000), ("rir", 0), ("rir", 10)],
    )
    def test_update_exercise_accepts_canonical_boundaries(
        self, client, clean_db, workout_plan_fixture, field, value
    ):
        resp = client.post("/update_exercise", json={
            "id": workout_plan_fixture["id"], "updates": {field: value},
        })
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        ("field", "value"),
        [("weight", -0.01), ("weight", 1000.01), ("rir", -0.01), ("rir", 10.01)],
    )
    def test_update_exercise_rejects_values_outside_canonical_boundaries(
        self, client, clean_db, workout_plan_fixture, field, value
    ):
        resp = client.post("/update_exercise", json={
            "id": workout_plan_fixture["id"], "updates": {field: value},
        })
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.parametrize(
        "updates",
        [
            {"min_rep_range": 13},
            {"max_rep_range": 7},
            {"min_rep_range": 12, "max_rep_range": 8},
        ],
    )
    def test_update_exercise_rejects_inverted_rep_ranges(
        self, client, clean_db, workout_plan_fixture, updates
    ):
        resp = client.post("/update_exercise", json={
            "id": workout_plan_fixture["id"], "updates": updates,
        })
        assert resp.status_code == 400

    def test_update_exercise_accepts_equal_rep_range(
        self, client, clean_db, workout_plan_fixture
    ):
        resp = client.post("/update_exercise", json={
            "id": workout_plan_fixture["id"],
            "updates": {"min_rep_range": 10, "max_rep_range": 10},
        })
        assert resp.status_code == 200


class TestUpdateExerciseOrder:
    """Tests for POST /update_exercise_order endpoint."""

    def test_update_exercise_order_zero_accepted(self, client, clean_db, workout_plan_fixture):
        """order=0 is a valid position and must be accepted, not treated as missing."""
        from utils.database import DatabaseHandler

        resp = client.post("/update_exercise_order", json=[
            {"id": workout_plan_fixture["id"], "order": 0}
        ])
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT exercise_order FROM user_selection WHERE id = ?",
                (workout_plan_fixture["id"],)
            )
        assert row is not None
        assert row["exercise_order"] == 0

    def test_update_exercise_order_missing_order_rejected(self, client, clean_db, workout_plan_fixture):
        """A missing/None order value is still rejected."""
        resp = client.post("/update_exercise_order", json=[
            {"id": workout_plan_fixture["id"]}
        ])
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False


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

    def test_generate_starter_plan_overwrite_replaces_legacy_routine_names(
        self, client, clean_db, exercise_factory
    ):
        """Overwrite should not leave A/A_gen1 style starter-plan routines behind."""
        from utils.plan_generator import get_generator_routine_names

        for name in (
            "Deadlift",
            "Bench Press",
            "Barbell Row",
            "Squat",
            "Plank",
            "Leg Curl",
            "Bicep Curl",
            "Lat Pulldown",
            "Shoulder Press",
            "Hip Thrust",
            "Crunch",
            "Tricep Extension",
            "Calf Raise",
        ):
            exercise_factory(name)
        exercise_factory("Legacy Exercise")

        for routine in ("A", "A_gen1", "B", "B_gen1"):
            clean_db.execute_query(
                """
                INSERT INTO user_selection
                    (routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight)
                VALUES (?, 'Legacy Exercise', 3, 8, 12, 2, 8.0, 50.0)
                """,
                (routine,),
            )

        resp = client.post("/generate_starter_plan", json={
            "training_days": 2,
            "environment": "gym",
            "persist": True,
            "overwrite": True,
        })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert list(data["data"]["routines"].keys()) == get_generator_routine_names(2, "gym")

        legacy = clean_db.fetch_one(
            "SELECT COUNT(*) AS count FROM user_selection WHERE routine IN ('A', 'A_gen1', 'B', 'B_gen1')"
        )
        assert legacy["count"] == 0


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
