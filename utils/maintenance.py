"""Maintenance utilities for normalizing and rebuilding isolated muscle mappings."""
from __future__ import annotations

import sqlite3
import time
from typing import Iterable, List, Optional, Tuple

try:  # Prefer package-relative imports when available
    from utils.database import DatabaseHandler
    from utils.logger import get_logger
    from utils.normalization import normalize_advanced_muscles
except ImportError:  # pragma: no cover - fallback for direct invocation
    from database import DatabaseHandler  # type: ignore
    from logger import get_logger  # type: ignore
    from normalization import normalize_advanced_muscles  # type: ignore


NORMALIZE_SQL: tuple[str, ...] = (
    (
        "UPDATE exercises SET advanced_isolated_muscles = "
        "REPLACE(advanced_isolated_muscles,'; ',',');"
    ),
    (
        "UPDATE exercises SET advanced_isolated_muscles = "
        "REPLACE(advanced_isolated_muscles,'; ', ',');"
    ),
    (
        "UPDATE exercises SET advanced_isolated_muscles = "
        "REPLACE(advanced_isolated_muscles,';', ',');"
    ),
)

REBUILD_EIM_SQL: tuple[str, ...] = (
    "DELETE FROM exercise_isolated_muscles;",
    (
        """
        WITH RECURSIVE split(exercise_name, rest, part) AS (
          SELECT exercise_name,
                 REPLACE(COALESCE(advanced_isolated_muscles,''), ';', ',') || ',',
                 ''
          FROM exercises
          WHERE advanced_isolated_muscles IS NOT NULL
            AND TRIM(advanced_isolated_muscles) <> ''

          UNION ALL
          SELECT exercise_name,
                 substr(rest, instr(rest, ',') + 1),
                 TRIM(substr(rest, 1, instr(rest, ',') - 1))
          FROM split
          WHERE rest <> ''
        )
        INSERT INTO exercise_isolated_muscles (exercise_name, muscle)
        SELECT exercise_name, LOWER(part)
        FROM split
        WHERE part <> '';
        """
    ),
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_eim_exercise_muscle ON exercise_isolated_muscles(exercise_name, muscle);",
    "CREATE INDEX IF NOT EXISTS idx_eim_muscle  ON exercise_isolated_muscles(muscle);",
    "CREATE INDEX IF NOT EXISTS idx_eim_ex      ON exercise_isolated_muscles(exercise_name);",
)
logger = get_logger()


def _exec_many(db: DatabaseHandler, statements: Iterable[str]) -> None:
    """Execute multiple statements inside a single transaction."""
    try:
        for sql in statements:
            for attempt in range(5):
                try:
                    db.execute_query(sql, commit=False)
                    break
                except sqlite3.OperationalError as exc:
                    if "locked" in str(exc).lower() and attempt < 4:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    db.connection.rollback()
                    raise
        db.connection.commit()
    except Exception:  # pragma: no cover - defensive rollback
        db.connection.rollback()
        raise


def _normalize_existing_rows(db: DatabaseHandler) -> None:
    """Apply canonical advanced muscle normalization across exercises."""
    rows = db.fetch_all(
        "SELECT rowid AS rid, advanced_isolated_muscles FROM exercises"
    )
    updates: List[Tuple[Optional[str], int]] = []
    for row in rows:
        raw_value = row.get("advanced_isolated_muscles")
        tokens = normalize_advanced_muscles(raw_value)
        formatted = ", ".join(tokens) if tokens else None
        if (raw_value or None) != formatted:
            updates.append((formatted, row["rid"]))

    if updates:
        db.executemany(
            "UPDATE exercises SET advanced_isolated_muscles = ? WHERE rowid = ?",
            updates,
        )


def normalize_and_rebuild_eim() -> None:
    """Normalise legacy CSV labels then rebuild exercise_isolated_muscles."""
    with DatabaseHandler() as db:
        _exec_many(db, NORMALIZE_SQL)
        _normalize_existing_rows(db)
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS exercise_isolated_muscles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              exercise_name TEXT NOT NULL,
              muscle TEXT NOT NULL
            );
            """
        )
        _exec_many(db, REBUILD_EIM_SQL)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "normalize_and_rebuild_eim":
        normalize_and_rebuild_eim()
        logger.info("OK: normalized CSV and rebuilt exercise_isolated_muscles")
    else:
        logger.info("Usage: python -m utils.maintenance normalize_and_rebuild_eim")
