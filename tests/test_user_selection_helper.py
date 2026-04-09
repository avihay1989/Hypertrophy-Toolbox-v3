"""Tests for the legacy utils.user_selection helper."""

from utils.user_selection import get_user_selection


def test_get_user_selection_returns_joined_metadata(clean_db, exercise_factory):
    exercise_factory("Bench Press", primary_muscle_group="Chest", utility="Basic")
    clean_db.execute_query(
        """
        INSERT INTO user_selection (
            routine, exercise, sets, min_rep_range, max_rep_range, rir, weight, superset_group
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Push", "Bench Press", 3, 8, 12, 2, 80.0, "SS-1"),
    )

    results = get_user_selection()

    assert len(results) == 1
    assert results[0]["exercise"] == "Bench Press"
    assert results[0]["primary_muscle_group"] == "Chest"
    assert results[0]["utility"] == "Basic"
    assert results[0]["superset_group"] == "SS-1"


def test_get_user_selection_returns_empty_list_when_no_rows(clean_db):
    assert get_user_selection() == []
