"""Invariants for a test-scoped snapshot of the shipped exercise catalog."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def _connect(catalog_db_path: str) -> sqlite3.Connection:
    uri = Path(catalog_db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def test_catalog_primary_muscle_group_has_no_nulls(catalog_db_path: str):
    """Fatigue Meter Phase 2 Stage 1 (D2.13) — every catalog row must have a
    non-NULL, non-blank primary_muscle_group so per-muscle accumulation does
    not silently drop rows into an unassigned bucket due to missing data.
    """
    with _connect(catalog_db_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n
              FROM exercises
             WHERE primary_muscle_group IS NULL
                OR TRIM(primary_muscle_group) = ''
            """
        ).fetchone()
    assert row["n"] == 0, (
        f"Expected 0 NULL/blank primary_muscle_group rows in exercises, found {row['n']}. "
        "Re-run scripts/fatigue_stage1_cleanup.py to restore the invariant."
    )


def test_catalog_movement_pattern_has_no_nulls(catalog_db_path: str):
    """Fatigue Meter Phase 2 §10 #5 — every catalog row must have a non-NULL,
    non-blank movement_pattern so fatigue's pattern-weight resolution and the
    plan-generator's blueprint-slot matching never hit a NULL path for a
    shipped exercise. Unresolved rows carry the 'unassigned' sentinel.
    """
    with _connect(catalog_db_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n
              FROM exercises
             WHERE movement_pattern IS NULL
                OR TRIM(movement_pattern) = ''
            """
        ).fetchone()
    assert row["n"] == 0, (
        f"Expected 0 NULL/blank movement_pattern rows in exercises, found {row['n']}. "
        "Re-run scripts/fatigue_movement_pattern_cleanup.py to restore the invariant."
    )
