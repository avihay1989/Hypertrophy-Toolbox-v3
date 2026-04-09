import sqlite3

from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()

def export_volume_plan(volume_data):
    """
    Export volume data to the workout plan database
    """
    try:
        with DatabaseHandler() as db:
            db.execute_query(
                '''
                    INSERT INTO volume_plans (training_days, created_at)
                    VALUES (?, datetime('now'))
                ''',
                (volume_data['training_days'],),
                commit=False,
            )
            plan_id = db.cursor.lastrowid

            for muscle, data in volume_data['volumes'].items():
                db.execute_query(
                    '''
                        INSERT INTO muscle_volumes
                        (plan_id, muscle_group, weekly_sets, sets_per_session, status)
                        VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        plan_id,
                        muscle,
                        data,
                        round(data / volume_data['training_days'], 1),
                        'optimal',
                    ),
                    commit=False,
                )

            return plan_id

    except sqlite3.Error as e:
        logger.exception("Database error exporting volume plan: %s", e)
        return None
