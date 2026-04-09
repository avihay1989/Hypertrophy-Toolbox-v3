import sqlite3

from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()


def get_user_selection():
    """
    Fetches user selection data along with muscle group information
    from the exercises table.
    :return: List of dictionaries containing user selection and muscle groups.
    """
    query = """
    SELECT
        us.id,
        us.routine,
        us.exercise,
        us.sets,
        us.min_rep_range,
        us.max_rep_range,
        us.rir,
        us.weight,
        us.superset_group,
        e.primary_muscle_group,
        e.secondary_muscle_group,
        e.tertiary_muscle_group,
        e.advanced_isolated_muscles,
        e.utility,
        e.grips,
        e.stabilizers,
        e.synergists
    FROM user_selection us
    JOIN exercises e ON us.exercise = e.exercise_name;
    """
    try:
        with DatabaseHandler() as db:
            results = db.fetch_all(query)

        if not results:
            logger.debug("No user selection data found.")
        else:
            logger.debug("User selection data retrieved successfully.")

        return results

    except sqlite3.OperationalError as oe:
        logger.warning("Operational error in database: %s", oe)
        return []
    except sqlite3.Error as e:
        logger.exception("Database error while fetching user selection: %s", e)
        return []
    except Exception as ex:
        logger.exception("Unexpected error while fetching user selection: %s", ex)
        return []
