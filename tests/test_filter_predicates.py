"""
Tests for utils/filter_predicates.py - SQL query building and filtering.

SECURITY CRITICAL: These tests verify SQL injection prevention and
proper query parameterization.
"""

from unittest.mock import patch, MagicMock
from utils.filter_predicates import (
    FilterPredicates,
    filter_exercises,
    get_exercises,
    build_filter_query,
)


class TestFilterPredicatesConstants:
    """Tests for FilterPredicates class constants."""

    def test_valid_filter_fields_not_empty(self):
        """VALID_FILTER_FIELDS should contain expected fields."""
        assert len(FilterPredicates.VALID_FILTER_FIELDS) > 0
        assert "equipment" in FilterPredicates.VALID_FILTER_FIELDS
        assert "mechanic" in FilterPredicates.VALID_FILTER_FIELDS
        assert "force" in FilterPredicates.VALID_FILTER_FIELDS
        assert "difficulty" in FilterPredicates.VALID_FILTER_FIELDS

    def test_partial_match_fields_subset_of_valid(self):
        """PARTIAL_MATCH_FIELDS should be subset of VALID_FILTER_FIELDS."""
        for field in FilterPredicates.PARTIAL_MATCH_FIELDS:
            assert field in FilterPredicates.VALID_FILTER_FIELDS

    def test_muscle_group_fields_use_partial_match(self):
        """Muscle group fields should use partial matching."""
        assert "primary_muscle_group" in FilterPredicates.PARTIAL_MATCH_FIELDS
        assert "secondary_muscle_group" in FilterPredicates.PARTIAL_MATCH_FIELDS
        assert "tertiary_muscle_group" in FilterPredicates.PARTIAL_MATCH_FIELDS
        assert "advanced_isolated_muscles" in FilterPredicates.PARTIAL_MATCH_FIELDS


class TestBuildFilterQuery:
    """Tests for build_filter_query method."""

    def test_no_filters_returns_base_query_with_order(self):
        """No filters should return base query with ORDER BY."""
        query, params = FilterPredicates.build_filter_query(None)
        assert "ORDER BY exercise_name ASC" in query
        assert params == []

    def test_empty_filters_returns_base_query(self):
        """Empty filters dict should return base query."""
        query, params = FilterPredicates.build_filter_query({})
        assert "ORDER BY exercise_name ASC" in query
        assert params == []

    def test_single_exact_match_filter(self):
        """Single exact match filter should use LOWER() comparison."""
        filters = {"equipment": "Barbell"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert "LOWER(equipment) = LOWER(?)" in query
        assert "Barbell" in params

    def test_single_partial_match_filter(self):
        """Single partial match filter should use LIKE."""
        filters = {"primary_muscle_group": "Chest"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert "primary_muscle_group LIKE ?" in query
        assert "%Chest%" in params

    def test_multiple_filters_use_and(self):
        """Multiple filters should be joined with AND."""
        filters = {"equipment": "Barbell", "mechanic": "Compound"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert " AND " in query
        assert len(params) == 2

    def test_invalid_filter_field_ignored(self):
        """Invalid filter fields should be silently ignored."""
        filters = {"invalid_field": "value", "equipment": "Barbell"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert "invalid_field" not in query
        assert "equipment" in query.lower()
        assert len(params) == 1

    def test_empty_value_filter_ignored(self):
        """Empty string values should be ignored."""
        filters = {"equipment": "", "mechanic": "Compound"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert "equipment" not in query.lower() or "mechanic" in query.lower()
        # mechanic should still be included
        assert any("mechanic" in q.lower() for q in query.split())

    def test_none_value_filter_ignored(self):
        """None values should be ignored."""
        filters = {"equipment": None, "mechanic": "Compound"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert len([p for p in params if p]) == 1

    # ─────────────────────────────────────────────────────────────────────
    # SQL Injection Prevention Tests (Security Critical)
    # ─────────────────────────────────────────────────────────────────────
    def test_sql_injection_in_value_parameterized(self):
        """SQL injection attempts in values should be parameterized."""
        malicious_values = [
            "'; DROP TABLE exercises; --",
            "1 OR 1=1",
            "\" OR \"\"=\"",
            "'; DELETE FROM exercises WHERE '1'='1",
            "UNION SELECT * FROM users --",
        ]
        for malicious in malicious_values:
            filters = {"equipment": malicious}
            query, params = FilterPredicates.build_filter_query(filters)
            # Value should be in params, not embedded in query
            assert malicious in params
            assert malicious not in query

    def test_sql_injection_in_field_name_rejected(self):
        """SQL injection in field names should be rejected (field not in whitelist)."""
        filters = {"equipment; DROP TABLE exercises; --": "value"}
        query, params = FilterPredicates.build_filter_query(filters)
        # Should be ignored since not in VALID_FILTER_FIELDS
        assert "DROP TABLE" not in query
        assert params == []

    def test_parameterized_queries_not_string_interpolation(self):
        """Queries should use ? placeholders, not string interpolation."""
        filters = {"equipment": "Test", "mechanic": "Compound"}
        query, params = FilterPredicates.build_filter_query(filters)
        # Should have ? placeholders
        assert query.count("?") == len(params)
        # Values should NOT appear directly in query
        assert "Test" not in query
        assert "Compound" not in query

    # ─────────────────────────────────────────────────────────────────────
    # Advanced isolated muscles special handling
    # ─────────────────────────────────────────────────────────────────────
    def test_advanced_isolated_muscles_uses_exists_subquery(self):
        """advanced_isolated_muscles should use EXISTS subquery."""
        filters = {"advanced_isolated_muscles": "biceps"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert "EXISTS" in query
        assert "exercise_isolated_muscles" in query
        assert "%biceps%" in params

    def test_advanced_isolated_muscles_mapping_table(self):
        """advanced_isolated_muscles should query mapping table."""
        filters = {"advanced_isolated_muscles": "deltoid"}
        query, params = FilterPredicates.build_filter_query(filters)
        assert "m.muscle LIKE ?" in query
        assert "m.exercise_name = exercises.exercise_name" in query

    # ─────────────────────────────────────────────────────────────────────
    # Custom base query
    # ─────────────────────────────────────────────────────────────────────
    def test_custom_base_query(self):
        """Should work with custom base query."""
        custom = "SELECT * FROM exercises WHERE active = 1"
        filters = {"equipment": "Dumbbell"}
        query, params = FilterPredicates.build_filter_query(filters, base_query=custom)
        assert query.startswith(custom)
        assert "equipment" in query.lower()

    def test_base_query_preserved(self):
        """Base query should be preserved at start."""
        custom = "SELECT exercise_name, equipment FROM exercises WHERE 1=1"
        query, params = FilterPredicates.build_filter_query(None, base_query=custom)
        assert query.startswith(custom)


class TestValidateFilterField:
    """Tests for validate_filter_field method."""

    def test_valid_fields_return_true(self):
        """Valid filter fields should return True."""
        assert FilterPredicates.validate_filter_field("equipment") is True
        assert FilterPredicates.validate_filter_field("mechanic") is True
        assert FilterPredicates.validate_filter_field("force") is True
        assert FilterPredicates.validate_filter_field("difficulty") is True

    def test_invalid_fields_return_false(self):
        """Invalid filter fields should return False."""
        assert FilterPredicates.validate_filter_field("invalid") is False
        assert FilterPredicates.validate_filter_field("") is False
        assert FilterPredicates.validate_filter_field("DROP TABLE") is False

    def test_sql_injection_attempts_rejected(self):
        """SQL injection attempts should be rejected."""
        assert FilterPredicates.validate_filter_field("equipment; DROP TABLE") is False
        assert FilterPredicates.validate_filter_field("1=1 OR equipment") is False


class TestSanitizeFilters:
    """Tests for sanitize_filters method."""

    def test_removes_invalid_fields(self):
        """Should remove invalid fields."""
        filters = {"equipment": "Barbell", "invalid": "value"}
        sanitized = FilterPredicates.sanitize_filters(filters)
        assert "equipment" in sanitized
        assert "invalid" not in sanitized

    def test_removes_empty_values(self):
        """Should remove empty string values."""
        filters = {"equipment": "Barbell", "mechanic": ""}
        sanitized = FilterPredicates.sanitize_filters(filters)
        assert "equipment" in sanitized
        assert "mechanic" not in sanitized

    def test_preserves_valid_filters(self):
        """Should preserve all valid filters with values."""
        filters = {
            "equipment": "Barbell",
            "mechanic": "Compound",
            "force": "Push"
        }
        sanitized = FilterPredicates.sanitize_filters(filters)
        assert len(sanitized) == 3
        assert sanitized == filters

    def test_empty_input_returns_empty(self):
        """Empty input should return empty dict."""
        assert FilterPredicates.sanitize_filters({}) == {}

    def test_all_invalid_returns_empty(self):
        """All invalid fields should return empty dict."""
        filters = {"invalid1": "value1", "invalid2": "value2"}
        sanitized = FilterPredicates.sanitize_filters(filters)
        assert sanitized == {}


class TestFilterExercises:
    """Tests for filter_exercises function (with database mocking)."""

    @patch('utils.filter_predicates.DatabaseHandler')
    def test_filter_exercises_with_tuple_results(self, mock_db_class):
        """Should handle tuple results from database."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = [("Exercise1",), ("Exercise2",)]
        mock_db_class.return_value = mock_db

        result = FilterPredicates.filter_exercises({"equipment": "Barbell"})
        
        assert result == ["Exercise1", "Exercise2"]

    @patch('utils.filter_predicates.DatabaseHandler')
    def test_filter_exercises_with_dict_results(self, mock_db_class):
        """Should handle dict results from database."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = [
            {"exercise_name": "Exercise1"},
            {"exercise_name": "Exercise2"}
        ]
        mock_db_class.return_value = mock_db

        result = FilterPredicates.filter_exercises({"equipment": "Barbell"})
        
        assert result == ["Exercise1", "Exercise2"]

    @patch('utils.filter_predicates.DatabaseHandler')
    def test_filter_exercises_empty_results(self, mock_db_class):
        """Should return empty list when no results."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = []
        mock_db_class.return_value = mock_db

        result = FilterPredicates.filter_exercises({"equipment": "NonExistent"})
        
        assert result == []

    @patch('utils.filter_predicates.DatabaseHandler')
    def test_filter_exercises_handles_exception(self, mock_db_class):
        """Should return empty list on database error."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.side_effect = Exception("Database error")
        mock_db_class.return_value = mock_db

        result = FilterPredicates.filter_exercises({"equipment": "Barbell"})
        
        assert result == []

    @patch('utils.filter_predicates.DatabaseHandler')
    def test_filter_exercises_filters_null_names(self, mock_db_class):
        """Should filter out None exercise names."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = [("Exercise1",), (None,), ("Exercise2",)]
        mock_db_class.return_value = mock_db

        result = FilterPredicates.filter_exercises({})
        
        assert result == ["Exercise1", "Exercise2"]
        assert None not in result


class TestGetExercisesAlias:
    """Tests for get_exercises alias function."""

    @patch.object(FilterPredicates, 'filter_exercises')
    def test_get_exercises_calls_filter_exercises(self, mock_filter):
        """get_exercises should delegate to filter_exercises."""
        mock_filter.return_value = ["Exercise1"]
        
        result = FilterPredicates.get_exercises({"equipment": "Barbell"})
        
        mock_filter.assert_called_once_with({"equipment": "Barbell"})
        assert result == ["Exercise1"]


class TestBackwardCompatibilityFunctions:
    """Tests for module-level backward compatibility functions."""

    def test_filter_exercises_function_exists(self):
        """Module-level filter_exercises should exist."""
        assert callable(filter_exercises)

    def test_get_exercises_function_exists(self):
        """Module-level get_exercises should exist."""
        assert callable(get_exercises)

    def test_build_filter_query_function_exists(self):
        """Module-level build_filter_query should exist."""
        assert callable(build_filter_query)

    def test_build_filter_query_delegates_to_class(self):
        """Module-level build_filter_query should match class method."""
        filters = {"equipment": "Barbell"}
        
        class_result = FilterPredicates.build_filter_query(filters)
        func_result = build_filter_query(filters)
        
        assert class_result == func_result


class TestComplexFilterScenarios:
    """Tests for complex filter combinations."""

    def test_multiple_muscle_group_filters(self):
        """Multiple muscle group filters should all use LIKE."""
        filters = {
            "primary_muscle_group": "Chest",
            "secondary_muscle_group": "Triceps",
        }
        query, params = FilterPredicates.build_filter_query(filters)
        assert query.count("LIKE ?") == 2
        assert "%Chest%" in params
        assert "%Triceps%" in params

    def test_mixed_exact_and_partial_filters(self):
        """Mix of exact and partial match filters."""
        filters = {
            "equipment": "Barbell",  # Exact
            "primary_muscle_group": "Chest",  # Partial
        }
        query, params = FilterPredicates.build_filter_query(filters)
        assert "LOWER(equipment) = LOWER(?)" in query
        assert "primary_muscle_group LIKE ?" in query

    def test_all_filter_types_combined(self):
        """All filter types used together."""
        filters = {
            "equipment": "Barbell",
            "mechanic": "Compound",
            "force": "Push",
            "primary_muscle_group": "Chest",
            "advanced_isolated_muscles": "pectoralis",
        }
        query, params = FilterPredicates.build_filter_query(filters)
        # Should have conditions for all filters
        assert len(params) == 5
        assert "EXISTS" in query  # For advanced_isolated_muscles
        assert "LIKE" in query  # For muscle groups
        assert "LOWER" in query  # For exact match fields
