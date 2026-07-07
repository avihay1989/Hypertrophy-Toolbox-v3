"""Characterization tests for the two extracted filter-value contracts."""

from routes import workout_plan as workout_plan_route
from utils.constants import MECHANIC
from utils import filter_values
from utils.filter_values import fetch_filter_values


class TestWorkoutPlanFilterValues:
    def test_invalid_column_keeps_forgiving_empty_list_contract(self, app):
        assert fetch_filter_values("not_a_column") == []

    def test_enum_values_come_from_canonical_constants(self, app):
        assert fetch_filter_values("mechanic") == sorted(set(MECHANIC.values()))

    def test_enum_results_are_fresh(self, app):
        first = fetch_filter_values("mechanic")
        first.append("Mutated")

        assert "Mutated" not in fetch_filter_values("mechanic")

    def test_force_values_are_title_cased_and_deduplicated(
        self, app, exercise_factory
    ):
        exercise_factory("Lower Push", force="push")
        exercise_factory("Upper Push", force=" Push ")
        exercise_factory("Pull", force="pull")

        assert fetch_filter_values("force") == ["Pull", "Push"]

    def test_equipment_values_are_trimmed(self, app, exercise_factory):
        exercise_factory("Trimmed", equipment="  Cable  ")
        exercise_factory("Clean", equipment="Barbell")

        assert fetch_filter_values("equipment") == ["Barbell", "Cable"]

    def test_advanced_muscles_use_mapping_table(self, app, clean_db):
        clean_db.execute_query(
            "INSERT INTO exercises (exercise_name) VALUES (?)", ("Curl",)
        )
        clean_db.execute_query(
            "INSERT INTO exercise_isolated_muscles (exercise_name, muscle) "
            "VALUES (?, ?)",
            ("Curl", "long-head-bicep"),
        )

        assert fetch_filter_values("advanced_isolated_muscles") == [
            "long-head-bicep"
        ]

    def test_route_level_name_remains_a_compatibility_wrapper(self, monkeypatch):
        monkeypatch.setattr(
            workout_plan_route,
            "fetch_filter_values",
            lambda column: [f"value-for-{column}"],
        )

        assert workout_plan_route.fetch_unique_values("force") == [
            "value-for-force"
        ]

    def test_database_failure_keeps_forgiving_empty_list_contract(
        self, monkeypatch
    ):
        class BrokenDatabase:
            def __enter__(self):
                raise RuntimeError("database unavailable")

            def __exit__(self, *args):
                return False

        monkeypatch.setattr(filter_values, "DatabaseHandler", BrokenDatabase)

        assert fetch_filter_values("equipment") == []
