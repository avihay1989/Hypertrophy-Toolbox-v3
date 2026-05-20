"""Schema-migration tests for utils/database.py.

Verifies the idempotent `add_*_table` helpers create the expected columns,
constraints, and indexes — and can be re-run without error against an
already-initialized DB (Flask startup calls them on every boot).
"""
from __future__ import annotations

import sqlite3

import pytest

from utils.database import (
    DatabaseHandler,
    add_body_composition_snapshots_table,
)


BODY_COMP_TABLE = "body_composition_snapshots"
BODY_COMP_INDEX = "idx_body_composition_snapshots_captured_at"
BODY_COMP_COLUMNS = {
    "id",
    "captured_at",
    "bodyweight_kg",
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


def _columns(db: DatabaseHandler, table: str) -> dict[str, sqlite3.Row]:
    return {row["name"]: row for row in db.fetch_all(f"PRAGMA table_info({table})")}


def _table_exists(db: DatabaseHandler, table: str) -> bool:
    row = db.fetch_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return row is not None


def _index_exists(db: DatabaseHandler, index: str) -> bool:
    row = db.fetch_one(
        "SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
        (index,),
    )
    return row is not None


def test_body_composition_snapshots_table_has_expected_columns(clean_db):
    add_body_composition_snapshots_table()
    cols = _columns(clean_db, BODY_COMP_TABLE)
    assert set(cols.keys()) >= BODY_COMP_COLUMNS

    # NOT NULL columns enforced at the schema level.
    not_null = {name for name, info in cols.items() if info["notnull"] == 1}
    assert {"captured_at", "bodyweight_kg", "height_cm", "age_years", "gender", "bfp_bmi"} <= not_null

    # Nullable columns that hold tape-derived / BMI-only / informational data.
    nullable = {name for name, info in cols.items() if info["notnull"] == 0}
    assert {"neck_cm", "waist_cm", "hip_cm", "bfp_navy", "fat_mass_kg", "lean_mass_kg", "notes"} <= nullable


def test_body_composition_snapshots_captured_at_index_exists(clean_db):
    add_body_composition_snapshots_table()
    assert _index_exists(clean_db, BODY_COMP_INDEX)

    index_info = clean_db.fetch_all(f"PRAGMA index_info({BODY_COMP_INDEX})")
    assert [row["name"] for row in index_info] == ["captured_at"]


def test_body_composition_snapshots_migration_is_idempotent(clean_db):
    # Conftest already created the table once; calling again must not raise.
    add_body_composition_snapshots_table()
    add_body_composition_snapshots_table()
    assert _table_exists(clean_db, BODY_COMP_TABLE)
    assert _index_exists(clean_db, BODY_COMP_INDEX)


def test_body_composition_snapshots_accepts_navy_snapshot(clean_db):
    add_body_composition_snapshots_table()
    clean_db.execute_query(
        """
        INSERT INTO body_composition_snapshots (
            captured_at, bodyweight_kg, height_cm, neck_cm, waist_cm, hip_cm,
            age_years, gender, bfp_navy, bfp_bmi, fat_mass_kg, lean_mass_kg, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "2026-05-20T10:00:00Z",
            80.0,
            180.0,
            38.0,
            85.0,
            None,
            34,
            "M",
            16.1,
            20.3,
            12.9,
            67.1,
            "first snapshot",
        ),
    )
    row = clean_db.fetch_one(
        "SELECT bfp_navy, bfp_bmi, gender FROM body_composition_snapshots"
    )
    assert row == {"bfp_navy": 16.1, "bfp_bmi": 20.3, "gender": "M"}


def test_body_composition_snapshots_accepts_bmi_only_snapshot(clean_db):
    add_body_composition_snapshots_table()
    clean_db.execute_query(
        """
        INSERT INTO body_composition_snapshots (
            captured_at, bodyweight_kg, height_cm,
            age_years, gender, bfp_bmi
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("2026-05-20T10:00:00Z", 60.0, 165.0, 30, "F", 27.95),
    )
    row = clean_db.fetch_one(
        "SELECT neck_cm, waist_cm, hip_cm, bfp_navy, bfp_bmi FROM body_composition_snapshots"
    )
    assert row == {
        "neck_cm": None,
        "waist_cm": None,
        "hip_cm": None,
        "bfp_navy": None,
        "bfp_bmi": 27.95,
    }


def test_body_composition_snapshots_rejects_missing_required(clean_db):
    add_body_composition_snapshots_table()
    with pytest.raises(sqlite3.IntegrityError):
        clean_db.execute_query(
            """
            INSERT INTO body_composition_snapshots (
                captured_at, bodyweight_kg, height_cm, age_years, gender
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("2026-05-20T10:00:00Z", 80.0, 180.0, 34, "M"),
        )


def test_erase_data_recreates_body_composition_snapshots_table(client, clean_db):
    clean_db.execute_query(
        """
        INSERT INTO body_composition_snapshots (
            captured_at, bodyweight_kg, height_cm, age_years, gender, bfp_bmi
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("2026-05-20T10:00:00Z", 80.0, 180.0, 34, "M", 20.3),
    )

    response = client.post("/erase-data")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True

    with DatabaseHandler() as db:
        assert _table_exists(db, BODY_COMP_TABLE)
        assert _index_exists(db, BODY_COMP_INDEX)
        count = db.fetch_one(f"SELECT COUNT(*) AS count FROM {BODY_COMP_TABLE}")
        assert count["count"] == 0
