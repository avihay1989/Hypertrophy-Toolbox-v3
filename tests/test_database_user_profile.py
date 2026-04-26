import sqlite3

import pytest

from utils.database import (
    DatabaseHandler,
    add_user_profile_tables,
    upsert_user_profile_demographics,
    upsert_user_profile_lift,
    upsert_user_profile_preference,
)


PROFILE_TABLES = {
    "user_profile": {
        "id",
        "gender",
        "age",
        "height_cm",
        "weight_kg",
        "experience_years",
        "updated_at",
    },
    "user_profile_lifts": {"id", "lift_key", "weight_kg", "reps", "updated_at"},
    "user_profile_preferences": {"id", "tier", "rep_range", "updated_at"},
}


def _columns(db, table):
    return {row["name"] for row in db.fetch_all(f"PRAGMA table_info({table})")}


def test_user_profile_tables_are_created_with_expected_columns(clean_db):
    add_user_profile_tables()

    for table, expected_columns in PROFILE_TABLES.items():
        assert expected_columns <= _columns(clean_db, table)

    lifts_indexes = clean_db.fetch_all("PRAGMA index_list(user_profile_lifts)")
    lift_unique_indexes = [row for row in lifts_indexes if row["unique"]]
    lift_index_columns = [
        column["name"]
        for index in lift_unique_indexes
        for column in clean_db.fetch_all(f"PRAGMA index_info({index['name']})")
    ]
    assert "lift_key" in lift_index_columns

    preference_indexes = clean_db.fetch_all("PRAGMA index_list(user_profile_preferences)")
    preference_unique_indexes = [row for row in preference_indexes if row["unique"]]
    preference_index_columns = [
        column["name"]
        for index in preference_unique_indexes
        for column in clean_db.fetch_all(f"PRAGMA index_info({index['name']})")
    ]
    assert "tier" in preference_index_columns


def test_user_profile_constraints_enforce_single_profile_and_valid_preferences(clean_db):
    clean_db.execute_query(
        """
        INSERT INTO user_profile (
            id, gender, age, height_cm, weight_kg, experience_years, updated_at
        )
        VALUES (1, 'Other', 30, 180, 80, 5, CURRENT_TIMESTAMP)
        """
    )

    with pytest.raises(sqlite3.IntegrityError):
        clean_db.execute_query(
            """
            INSERT INTO user_profile (
                id, gender, age, height_cm, weight_kg, experience_years, updated_at
            )
            VALUES (2, 'Other', 30, 180, 80, 5, CURRENT_TIMESTAMP)
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        clean_db.execute_query(
            """
            INSERT INTO user_profile_preferences (tier, rep_range, updated_at)
            VALUES ('main', 'moderate', CURRENT_TIMESTAMP)
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        clean_db.execute_query(
            """
            INSERT INTO user_profile_preferences (tier, rep_range, updated_at)
            VALUES ('complex', 'medium', CURRENT_TIMESTAMP)
            """
        )


def test_user_profile_upserts_update_without_replacing_rows(clean_db):
    upsert_user_profile_demographics(
        gender="Other",
        age=30,
        height_cm=180,
        weight_kg=80,
        experience_years=5,
        db=clean_db,
    )
    upsert_user_profile_demographics(
        gender="M",
        age=31,
        height_cm=181,
        weight_kg=82,
        experience_years=6,
        db=clean_db,
    )
    profile = clean_db.fetch_one("SELECT id, gender, age FROM user_profile")
    assert profile == {"id": 1, "gender": "M", "age": 31}

    upsert_user_profile_lift("barbell_bench_press", 100, 5, db=clean_db)
    first_lift = clean_db.fetch_one(
        "SELECT id FROM user_profile_lifts WHERE lift_key = ?",
        ("barbell_bench_press",),
    )
    upsert_user_profile_lift("barbell_bench_press", 105, 4, db=clean_db)
    updated_lift = clean_db.fetch_one(
        """
        SELECT id, weight_kg, reps
        FROM user_profile_lifts
        WHERE lift_key = ?
        """,
        ("barbell_bench_press",),
    )
    assert updated_lift == {"id": first_lift["id"], "weight_kg": 105.0, "reps": 4}

    upsert_user_profile_preference("complex", "heavy", db=clean_db)
    first_preference = clean_db.fetch_one(
        "SELECT id FROM user_profile_preferences WHERE tier = ?",
        ("complex",),
    )
    upsert_user_profile_preference("complex", "moderate", db=clean_db)
    updated_preference = clean_db.fetch_one(
        """
        SELECT id, rep_range
        FROM user_profile_preferences
        WHERE tier = ?
        """,
        ("complex",),
    )
    assert updated_preference == {"id": first_preference["id"], "rep_range": "moderate"}


def test_erase_data_recreates_user_profile_tables(client, clean_db):
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
    clean_db.execute_query(
        """
        INSERT INTO user_profile_preferences (tier, rep_range, updated_at)
        VALUES ('complex', 'heavy', CURRENT_TIMESTAMP)
        """
    )

    response = client.post("/erase-data")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True

    with DatabaseHandler() as db:
        for table, expected_columns in PROFILE_TABLES.items():
            assert expected_columns <= _columns(db, table)
            row = db.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
            assert row["count"] == 0
