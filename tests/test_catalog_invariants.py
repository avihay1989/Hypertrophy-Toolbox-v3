"""Live-DB invariants for the shipped exercise catalog.

These tests read data/database.db directly (the same pattern as
test_volume_taxonomy.py) because the invariants gate the real shipped
catalog, not seeded fixtures.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = REPO_ROOT / "data" / "database.db"


def _connect() -> sqlite3.Connection:
    assert LIVE_DB.exists(), f"Live DB is required for catalog invariants: {LIVE_DB}"
    conn = sqlite3.connect(LIVE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def test_catalog_primary_muscle_group_has_no_nulls():
    """Fatigue Meter Phase 2 Stage 1 (D2.13) — every catalog row must have a
    non-NULL, non-blank primary_muscle_group so per-muscle accumulation does
    not silently drop rows into an unassigned bucket due to missing data.
    """
    with _connect() as conn:
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


def test_catalog_movement_pattern_has_no_nulls():
    """Fatigue Meter Phase 2 §10 #5 — every catalog row must have a non-NULL,
    non-blank movement_pattern so fatigue's pattern-weight resolution and the
    plan-generator's blueprint-slot matching never hit a NULL path for a
    shipped exercise. Unresolved rows carry the 'unassigned' sentinel.
    """
    with _connect() as conn:
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
