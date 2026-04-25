import sqlite3

from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()

def export_volume_plan(volume_data, mode: str = "basic"):
    """
    Export volume data to the workout plan database
    """
    try:
        requested_mode = volume_data.get("mode") if mode == "basic" and volume_data.get("mode") else mode
        plan_mode = "advanced" if (requested_mode or "").lower() == "advanced" else "basic"
        training_days = max(int(volume_data.get("training_days", 3)), 1)
        with DatabaseHandler() as db:
            db.execute_query(
                '''
                    INSERT INTO volume_plans (training_days, mode, created_at)
                    VALUES (?, ?, datetime('now'))
                ''',
                (training_days, plan_mode),
                commit=False,
            )
            plan_id = db.cursor.lastrowid

            for muscle, data in volume_data['volumes'].items():
                if isinstance(data, dict):
                    weekly_sets = data.get("weekly_sets", 0)
                    status = data.get("status", "optimal")
                else:
                    weekly_sets = data
                    status = "optimal"

                db.execute_query(
                    '''
                        INSERT INTO muscle_volumes
                        (plan_id, muscle_group, weekly_sets, sets_per_session, status)
                        VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        plan_id,
                        muscle,
                        weekly_sets,
                        round(float(weekly_sets or 0) / training_days, 1),
                        status,
                    ),
                    commit=False,
                )

            return plan_id

    except sqlite3.Error as e:
        logger.exception("Database error exporting volume plan: %s", e)
        return None
