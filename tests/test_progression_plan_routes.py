"""Route contract tests for the Tier 4A progression endpoint wrappers."""
from datetime import datetime

from utils.database import DatabaseHandler

XHR_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def assert_success_envelope(payload):
    assert payload["ok"] is True
    assert payload["status"] == "success"


def assert_error_envelope(payload, code, message):
    assert payload["ok"] is False
    assert payload["status"] == "error"
    assert payload["error"]["code"] == code
    assert payload["message"] == message


def insert_progression_goal(exercise, goal_type, current_value, target_value, goal_date):
    with DatabaseHandler() as db:
        db.execute_query(
            """
            INSERT INTO progression_goals (
                exercise, goal_type, current_value, target_value, goal_date, created_at, completed
            ) VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                exercise,
                goal_type,
                current_value,
                target_value,
                goal_date,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        row = db.fetch_one("SELECT last_insert_rowid() AS id")

    assert row is not None
    return row["id"]


def test_get_exercise_suggestions_returns_wrapped_start_training_when_no_history(client, clean_db):
    response = client.post(
        "/get_exercise_suggestions",
        json={"exercise": "Bench Press", "is_novice": True},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success_envelope(payload)
    assert isinstance(payload["data"], list)
    assert payload["data"][0]["type"] == "technique"
    assert "Start Training" in payload["data"][0]["title"]


def test_get_exercise_suggestions_uses_plan_values_when_no_log_history(
    client, clean_db, exercise_factory, workout_plan_factory
):
    exercise_factory("Bench Press")
    workout_plan_factory(
        exercise_name="Bench Press",
        routine="Push",
        sets=4,
        min_rep_range=8,
        max_rep_range=12,
        weight=80.0,
    )

    response = client.post(
        "/get_exercise_suggestions",
        json={"exercise": "Bench Press", "is_novice": True},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success_envelope(payload)
    suggestions = {item["type"]: item for item in payload["data"]}

    assert "technique" in suggestions
    assert suggestions["weight"]["current_value"] == 80.0
    assert suggestions["weight"]["suggested_value"] == 82.5
    assert suggestions["reps"]["current_value"] == 12
    assert suggestions["reps"]["suggested_value"] == 14
    assert suggestions["sets"]["current_value"] == 4
    assert suggestions["sets"]["suggested_value"] == 5


def test_get_exercise_suggestions_returns_validation_error_for_missing_exercise(client, clean_db):
    response = client.post(
        "/get_exercise_suggestions",
        json={},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert_error_envelope(payload, "VALIDATION_ERROR", "exercise is required")


def test_get_current_value_returns_wrapped_latest_weight_value(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    exercise_factory("Bench Press")
    plan_id = workout_plan_factory(
        exercise_name="Bench Press",
        routine="Push",
        weight=80.0,
        min_rep_range=8,
        max_rep_range=12,
    )
    workout_log_factory(
        plan_id=plan_id,
        routine="Push",
        exercise="Bench Press",
        planned_weight=80.0,
        scored_weight=82.5,
        planned_min_reps=8,
        planned_max_reps=12,
        scored_min_reps=8,
        scored_max_reps=10,
    )

    response = client.post(
        "/get_current_value",
        json={"exercise": "Bench Press", "goal_type": "weight"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success_envelope(payload)
    assert payload["data"]["current_value"] == 82.5


def test_get_current_value_falls_back_to_plan_when_log_history_is_empty(
    client, clean_db, exercise_factory, workout_plan_factory
):
    exercise_factory("Bench Press")
    workout_plan_factory(
        exercise_name="Bench Press",
        routine="Push",
        sets=4,
        min_rep_range=8,
        max_rep_range=12,
        weight=80.0,
    )

    expected_values = {
        "weight": 80.0,
        "reps": 12,
        "sets": 4,
    }

    for goal_type, expected_value in expected_values.items():
        response = client.post(
            "/get_current_value",
            json={"exercise": "Bench Press", "goal_type": goal_type},
            headers=XHR_HEADERS,
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert_success_envelope(payload)
        assert payload["data"]["current_value"] == expected_value


def test_get_current_value_returns_wrapped_na_for_unsupported_goal_type(client, clean_db):
    response = client.post(
        "/get_current_value",
        json={"exercise": "Bench Press", "goal_type": "tempo"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success_envelope(payload)
    assert payload["data"]["current_value"] == "N/A"


def test_get_current_value_returns_validation_error_for_missing_exercise(client, clean_db):
    response = client.post(
        "/get_current_value",
        json={"goal_type": "weight"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert_error_envelope(payload, "VALIDATION_ERROR", "exercise is required")


def test_save_progression_goal_returns_wrapped_json_for_xhr_and_creates_goal(client, clean_db):
    response = client.post(
        "/save_progression_goal",
        json={
            "exercise": "Bench Press",
            "goal_type": "weight",
            "current_value": 80.0,
            "target_value": 82.5,
            "goal_date": "2026-12-31",
        },
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success_envelope(payload)
    assert payload["message"] == "Goal saved successfully"
    assert isinstance(payload["data"]["goal_id"], int)

    with DatabaseHandler() as db:
        saved_goal = db.fetch_one(
            """
            SELECT exercise, goal_type, current_value, target_value, goal_date, completed
            FROM progression_goals
            ORDER BY id DESC
            LIMIT 1
            """
        )

    assert saved_goal is not None
    assert saved_goal["exercise"] == "Bench Press"
    assert saved_goal["goal_type"] == "weight"
    assert saved_goal["current_value"] == 80.0
    assert saved_goal["target_value"] == 82.5
    assert saved_goal["goal_date"].isoformat() == "2026-12-31"
    assert saved_goal["completed"] == 0


def test_save_progression_goal_redirects_for_form_post_success(client, clean_db):
    response = client.post(
        "/save_progression_goal",
        data={
            "exercise": "Bench Press",
            "goal_type": "weight",
            "current_value": "80.0",
            "target_value": "82.5",
            "goal_date": "2026-12-31",
        },
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/progression")


def test_save_progression_goal_returns_validation_error_for_missing_required_data(client, clean_db):
    response = client.post(
        "/save_progression_goal",
        json={
            "exercise": "Bench Press",
            "goal_type": "weight",
            "current_value": 80.0,
        },
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert_error_envelope(payload, "VALIDATION_ERROR", "Missing required data")


def test_save_progression_goal_returns_validation_error_for_invalid_json(client, clean_db):
    response = client.post(
        "/save_progression_goal",
        data="not json",
        headers=XHR_HEADERS,
        content_type="application/json",
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert_error_envelope(payload, "VALIDATION_ERROR", "Invalid JSON data")


def test_delete_progression_goal_deletes_row_and_returns_wrapped_message(client, clean_db):
    goal_id = insert_progression_goal("Bench Press", "weight", 80.0, 82.5, "2026-12-31")

    response = client.delete(
        f"/delete_progression_goal/{goal_id}",
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success_envelope(payload)
    assert payload["message"] == "Goal deleted successfully"

    with DatabaseHandler() as db:
        deleted_goal = db.fetch_one(
            "SELECT id FROM progression_goals WHERE id = ?",
            (goal_id,),
        )

    assert deleted_goal is None


def test_delete_progression_goal_returns_wrapped_404_for_missing_goal(client, clean_db):
    response = client.delete(
        "/delete_progression_goal/99999",
        headers=XHR_HEADERS,
    )

    assert response.status_code == 404
    payload = response.get_json()
    assert_error_envelope(payload, "NOT_FOUND", "Goal not found")


def test_complete_progression_goal_marks_goal_completed_and_returns_wrapped_message(client, clean_db):
    goal_id = insert_progression_goal("Bench Press", "reps", 10.0, 12.0, "2026-12-31")

    response = client.post(
        f"/complete_progression_goal/{goal_id}",
        json={},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success_envelope(payload)
    assert payload["message"] == "Goal marked as completed"

    with DatabaseHandler() as db:
        completed_goal = db.fetch_one(
            "SELECT completed FROM progression_goals WHERE id = ?",
            (goal_id,),
        )

    assert completed_goal is not None
    assert completed_goal["completed"] == 1


def test_complete_progression_goal_returns_wrapped_404_for_missing_goal(client, clean_db):
    response = client.post(
        "/complete_progression_goal/99999",
        json={},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 404
    payload = response.get_json()
    assert_error_envelope(payload, "NOT_FOUND", "Goal not found")
