"""Characterization coverage for the WP1.4 superset service boundary."""
import subprocess
import sys
import time

import pytest


@pytest.mark.parametrize(
    "imports",
    [
        "import routes.workout_plan; import utils.supersets",
        "import utils.supersets; import routes.workout_plan",
    ],
)
def test_superset_modules_import_in_either_order(imports):
    completed = subprocess.run(
        [sys.executable, "-c", imports],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_route_helper_imports_remain_compatible():
    from routes import workout_plan
    from utils import supersets

    assert (
        workout_plan._validate_superset_link_request
        is supersets._validate_superset_link_request
    )
    assert workout_plan._apply_superset_link is supersets._apply_superset_link
    assert (
        workout_plan._group_exercises_by_routine
        is supersets._group_exercises_by_routine
    )
    assert (
        workout_plan._find_antagonist_pairings
        is supersets._find_antagonist_pairings
    )


def test_link_preserves_timestamp_id_and_database_row_order(
    client,
    exercise_factory,
    workout_plan_factory,
    monkeypatch,
):
    first = exercise_factory("First Exercise")
    second = exercise_factory("Second Exercise")
    first_id = workout_plan_factory(exercise_name=first, routine="A")
    second_id = workout_plan_factory(exercise_name=second, routine="A")
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000.9)

    response = client.post(
        "/api/superset/link",
        # Reversed input characterizes the historical unordered SQL result.
        json={"exercise_ids": [str(second_id), float(first_id)]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['data']['superset_group'] == "SS-A-1700000000"
    assert [row['id'] for row in payload['data']['exercises']] == [
        first_id,
        second_id,
    ]
    assert payload['message'] == (
        "Linked 'First Exercise' and 'Second Exercise' as superset"
    )


def test_unlink_invalid_truthy_exercise_id_keeps_generic_500(client):
    """The endpoint historically lets int() failure reach its generic catch."""
    response = client.post(
        "/api/superset/unlink", json={"exercise_id": "not-an-integer"}
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload['error']['code'] == "INTERNAL_ERROR"
    assert payload['error']['message'] == "Failed to unlink superset"


def test_antagonist_pairing_preserves_first_match_and_pair_order():
    from utils.supersets import _find_antagonist_pairings

    exercises = [
        {
            "id": 1,
            "exercise": "Chest One",
            "primary_muscle_group": "Chest",
            "superset_group": None,
        },
        {
            "id": 2,
            "exercise": "Back One",
            "primary_muscle_group": "Upper Back",
            "superset_group": None,
        },
        {
            "id": 3,
            "exercise": "Back Two",
            "primary_muscle_group": "Latissimus Dorsi",
            "superset_group": None,
        },
        {
            "id": 4,
            "exercise": "Chest Two",
            "primary_muscle_group": "Chest",
            "superset_group": None,
        },
        {
            "id": 5,
            "exercise": "Excluded Chest",
            "primary_muscle_group": "Chest",
            "superset_group": "SS-existing",
        },
    ]

    suggestions = _find_antagonist_pairings("A", exercises)

    assert [
        (item['exercise_1']['id'], item['exercise_2']['id'])
        for item in suggestions
    ] == [(1, 2), (3, 4)]
    assert suggestions[0] == {
        "routine": "A",
        "exercise_1": {"id": 1, "name": "Chest One", "muscle": "Chest"},
        "exercise_2": {
            "id": 2,
            "name": "Back One",
            "muscle": "Upper Back",
        },
        "reason": (
            "Antagonist pair: Chest / Upper Back - allows one muscle to rest "
            "while the other works"
        ),
        "benefit": "Saves time without compromising performance",
    }
