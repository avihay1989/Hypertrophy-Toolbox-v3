import pytest

from utils.normalization import normalize_muscle


@pytest.fixture
def normalized_plan(clean_db, exercise_factory, workout_plan_factory):
    """Seed the database with alias-heavy muscle data and normalise it."""
    exercise_name = exercise_factory(
        "Rear Delt Fly",
        primary_muscle_group="rear delts",
        secondary_muscle_group="mid traps",
        tertiary_muscle_group="glutes",
        utility="auxiliary",
        mechanic="isolation",
    )
    workout_plan_factory(
        exercise_name=exercise_name,
        routine="PPL - Pull",
        sets=4,
        min_rep_range=10,
        max_rep_range=12,
        weight=25,
    )

    canonical_primary = normalize_muscle("rear delts")
    canonical_secondary = normalize_muscle("mid traps")
    canonical_tertiary = normalize_muscle("glutes")
    canonical_isolated = [
        muscle
        for muscle in (
            normalize_muscle("rear delts"),
            normalize_muscle("mid traps"),
            normalize_muscle("tfl"),
        )
        if muscle
    ]

    clean_db.execute_query(
        """
        UPDATE exercises
        SET primary_muscle_group = ?,
            secondary_muscle_group = ?,
            tertiary_muscle_group = ?,
            advanced_isolated_muscles = ?
        WHERE exercise_name = ?
        """,
        (
            canonical_primary,
            canonical_secondary,
            canonical_tertiary,
            ", ".join(canonical_isolated),
            exercise_name,
        ),
    )

    clean_db.execute_query(
        "DELETE FROM exercise_isolated_muscles WHERE exercise_name = ?",
        (exercise_name,),
    )
    for muscle in canonical_isolated:
        clean_db.execute_query(
            "INSERT INTO exercise_isolated_muscles (exercise_name, muscle) VALUES (?, ?)",
            (exercise_name, muscle),
        )

    return exercise_name


def _extract_muscles_from_summary(response_json, key):
    return {entry[key] for entry in response_json}


def test_session_summary_uses_canonical_muscles(client, normalized_plan):  # noqa: PT019 fixture unused
    response = client.get("/session_summary", headers={"Accept": "application/json"})
    assert response.status_code == 200
    payload = response.get_json()
    muscles = _extract_muscles_from_summary(payload["data"]["session_summary"], "muscle_group")
    assert "Rear-Shoulder" in muscles
    assert "rear delts" not in muscles


def test_weekly_summary_uses_canonical_muscles(client, normalized_plan):  # noqa: PT019 fixture unused
    response = client.get("/weekly_summary", headers={"Accept": "application/json"})
    assert response.status_code == 200
    payload = response.get_json()
    muscles = _extract_muscles_from_summary(payload["data"]["weekly_summary"], "muscle_group")
    assert "Rear-Shoulder" in muscles
    assert "rear delts" not in muscles


def test_workout_plan_endpoint_returns_canonical_muscles(client, normalized_plan):  # noqa: PT019 fixture unused
    response = client.get("/get_workout_plan")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    entry = next(row for row in payload["data"] if row["exercise"] == normalized_plan)
    assert entry["primary_muscle_group"] == "Rear-Shoulder"
    assert entry["secondary_muscle_group"] == "Middle-Traps"
    assert entry["tertiary_muscle_group"] == "Gluteus Maximus"
    assert entry["advanced_isolated_muscles"] == "Rear-Shoulder, Middle-Traps, Tfl"


def test_get_exercise_details_returns_normalized_fields(client, clean_db, normalized_plan):
    plan_row = clean_db.fetch_one(
        "SELECT id FROM user_selection WHERE exercise = ?",
        (normalized_plan,),
    )
    response = client.get(f"/get_exercise_details/{plan_row['id']}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    data = payload["data"]
    assert data["primary_muscle_group"] == "Rear-Shoulder"
    assert data["secondary_muscle_group"] == "Middle-Traps"
    assert data["tertiary_muscle_group"] == "Gluteus Maximus"
    assert data["advanced_isolated_muscles"] == "Rear-Shoulder, Middle-Traps, Tfl"


def test_filters_unique_values_return_canonical_muscles(client, normalized_plan):
    response = client.get("/get_unique_values/exercises/primary_muscle_group")
    assert response.status_code == 200
    payload = response.get_json()
    values = payload["data"]
    assert "Rear-Shoulder" in values
    assert all(value != "rear delts" for value in values)


def test_filters_unique_values_return_canonical_isolated_muscles(client, normalized_plan):
    response = client.get("/get_unique_values/exercises/advanced_isolated_muscles")
    assert response.status_code == 200
    payload = response.get_json()
    values = payload["data"]
    assert {"Rear-Shoulder", "Middle-Traps", "Tfl"}.issubset(set(values))
    assert all(value.lower() != "rear delts" for value in values)
