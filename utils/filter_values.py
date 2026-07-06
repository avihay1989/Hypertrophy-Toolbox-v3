"""Filter-value query contract used to render workout-plan filters."""

from utils.constants import DIFFICULTY, MECHANIC, UTILITY
from utils.database import DatabaseHandler
from utils.filter_registry import (
    ALLOWED_COLUMNS,
    validate_column_name,
)
from utils.logger import get_logger


logger = get_logger()

ENUM_VALUE_MAP = {
    "mechanic": sorted(set(MECHANIC.values())),
    "utility": sorted(set(UTILITY.values())),
    "difficulty": sorted(set(DIFFICULTY.values())),
}


def _normalized_force_values(rows: list[dict]) -> list[str]:
    """Normalize force values to title case and merge case variants."""
    values = {
        value.strip().title()
        for row in rows
        if (value := row.get("value"))
    }
    return sorted(values)


def fetch_filter_values(column: str) -> list:
    """Return the workout-plan filter values for an exercises column.

    This preserves the historical route helper's forgiving contract: invalid
    columns and database errors are logged and returned as an empty list.
    """
    if not validate_column_name(column):
        logger.warning("Invalid column name in fetch_filter_values: %s", column)
        return []

    safe_column = ALLOWED_COLUMNS.get(column.lower())
    if not safe_column:
        logger.warning("Column not found in whitelist: %s", column)
        return []

    try:
        with DatabaseHandler() as db:
            if safe_column in ENUM_VALUE_MAP:
                # The historical workout-plan helper built this mapping inside
                # each call, so callers received a fresh list.
                return list(ENUM_VALUE_MAP[safe_column])

            if safe_column == "force":
                rows = db.fetch_all(
                    f"SELECT DISTINCT {safe_column} AS value FROM exercises "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY {safe_column}"
                )
                return _normalized_force_values(rows)

            if safe_column == "advanced_isolated_muscles":
                rows = db.fetch_all(
                    "SELECT DISTINCT muscle FROM exercise_isolated_muscles ORDER BY muscle"
                )
                return [row["muscle"] for row in rows]

            if safe_column in {
                "primary_muscle_group",
                "secondary_muscle_group",
                "tertiary_muscle_group",
            }:
                rows = db.fetch_all(
                    f"SELECT DISTINCT {safe_column} AS value FROM exercises "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY {safe_column}"
                )
                return [row["value"] for row in rows]

            if safe_column == "equipment":
                rows = db.fetch_all(
                    f"SELECT DISTINCT TRIM({safe_column}) AS value FROM exercises "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    "ORDER BY value"
                )
                return [row["value"] for row in rows if row.get("value")]

            rows = db.fetch_all(
                f"SELECT DISTINCT {safe_column} AS value FROM exercises "
                f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                f"ORDER BY {safe_column}"
            )
            return [row["value"] for row in rows if row.get("value")]
    except Exception:
        logger.exception("Error fetching workout-plan filter values for %s", column)
        return []
