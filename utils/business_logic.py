from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()


class BusinessLogic:
    """
    Contains the business logic for calculating summaries and other core operations.
    """

    def __init__(self):
        self.db_handler = None

    def calculate_weekly_summary(self, method="Total"):
        """
        Calculate the weekly summary based on the provided method.

        :param method: Calculation method - "Total", "Fractional", or "Direct".
        :return: Query results from the database.
        """
        try:
            # Initialize database handler
            if not self.db_handler:
                self.db_handler = DatabaseHandler()

            # Fetch and execute query
            query = self._get_query_for_method(method)
            results = self.db_handler.fetch_all(query)
            return results
        except ValueError as ve:
            logger.warning("ValueError in calculate_weekly_summary: %s", ve)
            return []
        except Exception as e:
            logger.exception("Unexpected error in calculate_weekly_summary: %s", e)
            return []
        finally:
            if self.db_handler:
                self.db_handler.close()
                self.db_handler = None

    def _get_query_for_method(self, method):
        """
        Get the SQL query for the given calculation method.

        :param method: Calculation method - "Total", "Fractional", or "Direct".
        :return: SQL query string.
        """
        base_query = """
            SELECT muscle_group,
                   ROUND(SUM(total_sets), 2) AS total_sets,
                   ROUND(SUM(total_reps), 2) AS total_reps,
                   ROUND(SUM(total_weight), 2) AS total_weight
            FROM (
                {subqueries}
            ) AS combined
            WHERE muscle_group IS NOT NULL
            GROUP BY muscle_group
        """

        subqueries = {
            "Total": """
                SELECT e.primary_muscle_group AS muscle_group,
                       SUM(us.sets) AS total_sets,
                       SUM(us.sets * us.max_rep_range) AS total_reps,
                       SUM(us.sets * us.weight) AS total_weight
                FROM user_selection us
                JOIN exercises e ON us.exercise = e.exercise_name
                GROUP BY e.primary_muscle_group
                UNION ALL
                SELECT e.secondary_muscle_group AS muscle_group,
                       SUM(us.sets * 0.5) AS total_sets,
                       SUM(us.sets * us.max_rep_range * 0.5) AS total_reps,
                       SUM(us.sets * us.weight * 0.5) AS total_weight
                FROM user_selection us
                JOIN exercises e ON us.exercise = e.exercise_name
                WHERE e.secondary_muscle_group IS NOT NULL
                GROUP BY e.secondary_muscle_group
                UNION ALL
                SELECT e.tertiary_muscle_group AS muscle_group,
                       SUM(us.sets * 0.33) AS total_sets,
                       SUM(us.sets * us.max_rep_range * 0.33) AS total_reps,
                       SUM(us.sets * us.weight * 0.33) AS total_weight
                FROM user_selection us
                JOIN exercises e ON us.exercise = e.exercise_name
                WHERE e.tertiary_muscle_group IS NOT NULL
                GROUP BY e.tertiary_muscle_group
            """,
            "Fractional": """
                SELECT e.primary_muscle_group AS muscle_group,
                       SUM(us.sets * 0.5) AS total_sets,
                       SUM(us.sets * us.max_rep_range * 0.5) AS total_reps,
                       SUM(us.sets * us.weight * 0.5) AS total_weight
                FROM user_selection us
                JOIN exercises e ON us.exercise = e.exercise_name
                GROUP BY e.primary_muscle_group
                UNION ALL
                SELECT e.secondary_muscle_group AS muscle_group,
                       SUM(us.sets * 0.25) AS total_sets,
                       SUM(us.sets * us.max_rep_range * 0.25) AS total_reps,
                       SUM(us.sets * us.weight * 0.25) AS total_weight
                FROM user_selection us
                JOIN exercises e ON us.exercise = e.exercise_name
                WHERE e.secondary_muscle_group IS NOT NULL
                GROUP BY e.secondary_muscle_group
            """,
            "Direct": """
                SELECT e.primary_muscle_group AS muscle_group,
                       SUM(us.sets) AS total_sets,
                       SUM(us.sets * us.max_rep_range) AS total_reps,
                       SUM(us.sets * us.weight) AS total_weight
                FROM user_selection us
                JOIN exercises e ON us.exercise = e.exercise_name
                GROUP BY e.primary_muscle_group
            """
        }

        if method not in subqueries:
            raise ValueError(f"Unknown calculation method: {method}")

        query = base_query.format(subqueries=subqueries[method])
        return query
