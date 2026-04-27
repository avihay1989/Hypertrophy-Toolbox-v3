XHR_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def assert_success(payload):
    assert payload["ok"] is True
    assert payload["status"] == "success"


def assert_error(payload, code):
    assert payload["ok"] is False
    assert payload["status"] == "error"
    assert payload["error"]["code"] == code


def test_user_profile_page_renders_with_saved_values(client, clean_db):
    clean_db.execute_query(
        """
        INSERT INTO user_profile (
            id, gender, age, height_cm, weight_kg, experience_years, updated_at
        )
        VALUES (1, 'Other', 30, 180, 80, 5, CURRENT_TIMESTAMP)
        """
    )
    clean_db.execute_query(
        """
        INSERT INTO user_profile_lifts (lift_key, weight_kg, reps, updated_at)
        VALUES ('barbell_bench_press', 100, 5, CURRENT_TIMESTAMP)
        """
    )

    response = client.get("/user_profile")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "User Profile" in html
    assert "Barbell or Dumbbell Bench Press" in html
    assert 'id="nav-user-profile"' in html
    assert 'value="100.0"' in html


def test_save_user_profile_upserts_demographics(client, clean_db):
    response = client.post(
        "/api/user_profile",
        json={
            "gender": "Other",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 80,
            "experience_years": 5,
        },
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["id"] == 1
    assert payload["data"]["age"] == 30

    response = client.post(
        "/api/user_profile",
        json={"gender": "M", "age": 31},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    row = clean_db.fetch_one("SELECT id, gender, age FROM user_profile")
    assert row == {"id": 1, "gender": "M", "age": 31}


def test_save_user_profile_rejects_invalid_ranges(client, clean_db):
    response = client.post(
        "/api/user_profile",
        json={"age": 101},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_save_user_profile_lifts_accepts_many_and_clears_nulls(client, clean_db):
    response = client.post(
        "/api/user_profile/lifts",
        json=[
            {"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5},
            {"lift_key": "bodyweight_pullups", "weight_kg": 0, "reps": 12},
        ],
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert len(payload["data"]) == 2

    response = client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": None, "reps": None}],
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    row = clean_db.fetch_one(
        "SELECT weight_kg, reps FROM user_profile_lifts WHERE lift_key = ?",
        ("barbell_bench_press",),
    )
    assert row == {"weight_kg": None, "reps": None}


def test_save_user_profile_lifts_rejects_unknown_lift_key(client, clean_db):
    response = client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "benchish", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_save_user_profile_preferences_upserts_tiers(client, clean_db):
    response = client.post(
        "/api/user_profile/preferences",
        json={"complex": "heavy", "accessory": "moderate", "isolated": "light"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["complex"] == "heavy"

    response = client.post(
        "/api/user_profile/preferences",
        json={"complex": "moderate"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    row = clean_db.fetch_one(
        "SELECT rep_range FROM user_profile_preferences WHERE tier = ?",
        ("complex",),
    )
    assert row["rep_range"] == "moderate"


def test_save_user_profile_preferences_rejects_invalid_values(client, clean_db):
    response = client.post(
        "/api/user_profile/preferences",
        json={"complex": "medium"},
        headers=XHR_HEADERS,
    )

    assert response.status_code == 400
    assert_error(response.get_json(), "VALIDATION_ERROR")


def test_estimate_endpoint_returns_profile_estimate(
    client, clean_db, exercise_factory
):
    exercise_factory(
        "EZ Bar Preacher Curl",
        primary_muscle_group="Biceps",
        equipment="Barbell",
        mechanic="Isolation",
    )
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bicep_curl", "weight_kg": 35, "reps": 8}],
        headers=XHR_HEADERS,
    )

    response = client.get(
        "/api/user_profile/estimate?exercise=EZ%20Bar%20Preacher%20Curl",
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["source"] == "profile"
    assert payload["data"]["reason"] == "profile"
    assert payload["data"]["weight"] == 11.25


def test_estimate_endpoint_prefers_last_logged_set(
    client, clean_db, exercise_factory, workout_plan_factory, workout_log_factory
):
    exercise_factory("Barbell Bench Press", primary_muscle_group="Chest", equipment="Barbell")
    client.post(
        "/api/user_profile/lifts",
        json=[{"lift_key": "barbell_bench_press", "weight_kg": 100, "reps": 5}],
        headers=XHR_HEADERS,
    )
    plan_id = workout_plan_factory(exercise_name="Barbell Bench Press", weight=80)
    workout_log_factory(
        plan_id=plan_id,
        exercise="Barbell Bench Press",
        planned_sets=4,
        planned_weight=80,
        scored_weight=82.5,
    )

    response = client.get(
        "/api/user_profile/estimate?exercise=Barbell%20Bench%20Press",
        headers=XHR_HEADERS,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["source"] == "log"
    assert payload["data"]["reason"] == "log"
    assert payload["data"]["weight"] == 82.5
    assert payload["data"]["sets"] == 4


def test_estimate_endpoint_returns_default_for_missing_exercise(client, clean_db):
    response = client.get("/api/user_profile/estimate", headers=XHR_HEADERS)

    assert response.status_code == 200
    payload = response.get_json()
    assert_success(payload)
    assert payload["data"]["source"] == "default"
    assert payload["data"]["reason"] == "default_missing"
