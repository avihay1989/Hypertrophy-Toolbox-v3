"""Tests for the central filter allowlist registry (WP1.1).

Covers three things:
1. Table/column validators reject malicious / unknown names and accept known ones.
2. `routes.filters` still re-exports the same objects (backward-compat contract).
3. The registry vocabulary reconciles EXACTLY with
   `FilterPredicates.VALID_FILTER_FIELDS` via the documented grouping frozensets,
   so future drift in either list fails a test instead of silently diverging.
"""
import routes.filters as filters_route
from utils import filter_registry as reg
from utils.filter_predicates import FilterPredicates


class TestTableValidation:
    def test_known_tables_accepted(self):
        for table in ("exercises", "user_selection", "workout_log", "progression_goals"):
            assert reg.validate_table_name(table) is True

    def test_case_insensitive(self):
        assert reg.validate_table_name("EXERCISES") is True
        assert reg.validate_column_name("PRIMARY_MUSCLE_GROUP") is True

    def test_malicious_table_names_rejected(self):
        for bad in (
            "evil_table",
            "exercises; DROP TABLE exercises;--",
            "exercises,user_selection",
            "sqlite_master",
            "",
            "1=1",
        ):
            assert reg.validate_table_name(bad) is False

    def test_malicious_column_names_rejected(self):
        for bad in (
            "evil_column",
            "column; DROP TABLE exercises;--",
            "weight OR 1=1",
            "",
            "*",
        ):
            assert reg.validate_column_name(bad) is False


class TestReExportContract:
    def test_route_reexports_are_registry_objects(self):
        # Existing callers/tests import these from routes.filters; they must be
        # the very same objects the registry owns.
        assert filters_route.ALLOWED_TABLES is reg.ALLOWED_TABLES
        assert filters_route.ALLOWED_COLUMNS is reg.ALLOWED_COLUMNS
        assert filters_route.validate_table_name is reg.validate_table_name
        assert filters_route.validate_column_name is reg.validate_column_name


class TestVocabularyReconciliation:
    """The allowlist and the filter-predicate field set are DIFFERENT on
    purpose; assert the documented relationship rather than a union."""

    def test_exercises_filter_columns_are_allowed_columns(self):
        # Every real (non-virtual) filter field must be a safe column.
        assert reg.EXERCISES_FILTER_COLUMNS <= set(reg.ALLOWED_COLUMNS)

    def test_valid_filter_fields_equals_exercises_columns_plus_virtual(self):
        assert set(FilterPredicates.VALID_FILTER_FIELDS) == (
            reg.EXERCISES_FILTER_COLUMNS | reg.VIRTUAL_FILTER_FIELDS
        )

    def test_virtual_fields_absent_from_allowed_columns(self):
        # target_muscles is filterable but has no physical column.
        assert reg.VIRTUAL_FILTER_FIELDS.isdisjoint(set(reg.ALLOWED_COLUMNS))

    def test_non_filter_columns_partition(self):
        # ALLOWED_COLUMNS partitions cleanly into filter columns + non-filter columns.
        assert (reg.EXERCISES_FILTER_COLUMNS | reg.NON_FILTER_ALLOWED_COLUMNS) == set(
            reg.ALLOWED_COLUMNS
        )
        assert reg.EXERCISES_FILTER_COLUMNS.isdisjoint(reg.NON_FILTER_ALLOWED_COLUMNS)

    def test_non_filter_columns_are_not_filter_fields(self):
        # exercise_name + user_selection columns are queryable but not filter fields.
        assert reg.NON_FILTER_ALLOWED_COLUMNS.isdisjoint(
            set(FilterPredicates.VALID_FILTER_FIELDS)
        )
