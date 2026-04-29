"""Unit tests for the body_composition_snapshots migration (Issue #21)."""
from __future__ import annotations

import sqlite3

import pytest

from utils.database import (
    DatabaseHandler,
    add_body_composition_snapshots_table,
)


EXPECTED_COLUMNS = {
    "id",
    "captured_at",
    "weight_kg",
    "height_cm",
    "neck_cm",
    "waist_cm",
    "hip_cm",
    "age_years",
    "gender",
    "bfp_navy",
    "bfp_bmi",
    "fat_mass_kg",
    "lean_mass_kg",
    "notes",
}


def _columns(db, table):
    return {row["name"] for row in db.fetch_all(f"PRAGMA table_info({table})")}


def _column_info(db, table):
    return {row["name"]: row for row in db.fetch_all(f"PRAGMA table_info({table})")}


def test_body_composition_snapshots_table_is_created(clean_db):
    add_body_composition_snapshots_table()
    assert EXPECTED_COLUMNS <= _columns(clean_db, "body_composition_snapshots")


def test_body_composition_snapshots_required_columns_are_not_null(clean_db):
    add_body_composition_snapshots_table()
    info = _column_info(clean_db, "body_composition_snapshots")
    # NOT NULL columns from the spec (notnull == 1).
    for required in ("captured_at", "weight_kg", "height_cm", "age_years", "gender", "bfp_bmi"):
        assert info[required]["notnull"] == 1, f"{required} must be NOT NULL"
    # Tape values + Navy BFP + derived masses + notes are nullable.
    for nullable in ("neck_cm", "waist_cm", "hip_cm", "bfp_navy", "fat_mass_kg", "lean_mass_kg", "notes"):
        assert info[nullable]["notnull"] == 0, f"{nullable} must be nullable"


def test_body_composition_snapshots_index_on_captured_at_exists(clean_db):
    add_body_composition_snapshots_table()
    indexes = clean_db.fetch_all("PRAGMA index_list(body_composition_snapshots)")
    names = {row["name"] for row in indexes}
    assert "idx_body_composition_snapshots_captured_at" in names


def test_body_composition_snapshots_gender_check_constraint(clean_db):
    add_body_composition_snapshots_table()
    # Valid genders accepted.
    for gender in ("M", "F"):
        clean_db.execute_query(
            """
            INSERT INTO body_composition_snapshots
                (captured_at, weight_kg, height_cm, age_years, gender, bfp_bmi)
            VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
            """,
            (75.0, 175.0, 30, gender, 20.0),
        )
    # Invalid gender rejected.
    with pytest.raises(sqlite3.IntegrityError):
        clean_db.execute_query(
            """
            INSERT INTO body_composition_snapshots
                (captured_at, weight_kg, height_cm, age_years, gender, bfp_bmi)
            VALUES (CURRENT_TIMESTAMP, 75.0, 175.0, 30, 'Other', 20.0)
            """
        )


def test_body_composition_snapshots_migration_is_idempotent(clean_db):
    add_body_composition_snapshots_table()
    clean_db.execute_query(
        """
        INSERT INTO body_composition_snapshots
            (captured_at, weight_kg, height_cm, age_years, gender, bfp_bmi)
        VALUES (CURRENT_TIMESTAMP, 75.0, 175.0, 30, 'M', 20.0)
        """
    )
    # Calling the migration again must not drop the row or raise.
    add_body_composition_snapshots_table()
    row = clean_db.fetch_one(
        "SELECT COUNT(*) AS count FROM body_composition_snapshots"
    )
    assert row["count"] == 1


def test_erase_data_recreates_body_composition_snapshots(client, clean_db):
    clean_db.execute_query(
        """
        INSERT INTO body_composition_snapshots
            (captured_at, weight_kg, height_cm, age_years, gender, bfp_bmi)
        VALUES (CURRENT_TIMESTAMP, 75.0, 175.0, 30, 'M', 20.0)
        """
    )

    response = client.post("/erase-data")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True

    with DatabaseHandler() as db:
        assert EXPECTED_COLUMNS <= _columns(db, "body_composition_snapshots")
        row = db.fetch_one("SELECT COUNT(*) AS count FROM body_composition_snapshots")
        assert row["count"] == 0
