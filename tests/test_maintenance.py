"""
Tests for utils/maintenance.py - Database maintenance and normalization.
"""

import pytest
from unittest.mock import patch, MagicMock
import sqlite3
from utils.maintenance import (
    _exec_many,
    _normalize_existing_rows,
    normalize_and_rebuild_eim,
    NORMALIZE_SQL,
    REBUILD_EIM_SQL,
)


class TestNormalizeSqlConstants:
    """Tests for SQL statement constants."""

    def test_normalize_sql_defined(self):
        """NORMALIZE_SQL should contain normalization statements."""
        assert len(NORMALIZE_SQL) > 0
        for sql in NORMALIZE_SQL:
            assert "UPDATE exercises" in sql
            assert "advanced_isolated_muscles" in sql

    def test_rebuild_eim_sql_defined(self):
        """REBUILD_EIM_SQL should contain rebuild statements."""
        assert len(REBUILD_EIM_SQL) > 0
        # Should include delete, insert, and index creation
        combined = " ".join(REBUILD_EIM_SQL)
        assert "DELETE FROM exercise_isolated_muscles" in combined
        assert "INSERT INTO exercise_isolated_muscles" in combined
        assert "CREATE" in combined and "INDEX" in combined


class TestExecMany:
    """Tests for _exec_many function."""

    def test_executes_all_statements(self):
        """Should execute all statements."""
        mock_db = MagicMock()
        statements = ["SELECT 1", "SELECT 2", "SELECT 3"]
        
        _exec_many(mock_db, statements)
        
        assert mock_db.execute_query.call_count == 3
        mock_db.connection.commit.assert_called_once()

    def test_uses_transaction(self):
        """Should commit after all statements."""
        mock_db = MagicMock()
        statements = ["SELECT 1", "SELECT 2"]
        
        _exec_many(mock_db, statements)
        
        # execute_query called with commit=False
        for call_args in mock_db.execute_query.call_args_list:
            assert call_args[1].get('commit') is False
        # Single commit at the end
        mock_db.connection.commit.assert_called_once()

    def test_rollback_on_error(self):
        """Should rollback on non-locked error."""
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = Exception("Some error")
        
        with pytest.raises(Exception):
            _exec_many(mock_db, ["SELECT 1"])
        
        mock_db.connection.rollback.assert_called()

    def test_retries_on_database_locked(self):
        """Should retry up to 5 times on database locked error."""
        mock_db = MagicMock()
        locked_error = sqlite3.OperationalError("database is locked")
        # Fail 3 times, then succeed
        mock_db.execute_query.side_effect = [
            locked_error,
            locked_error,
            locked_error,
            None,  # Success
        ]
        
        _exec_many(mock_db, ["SELECT 1"])
        
        # Should have tried 4 times (3 failures + 1 success)
        assert mock_db.execute_query.call_count == 4

    def test_raises_after_max_retries_on_locked(self):
        """Should raise after 5 retry attempts on locked database."""
        mock_db = MagicMock()
        locked_error = sqlite3.OperationalError("database is locked")
        mock_db.execute_query.side_effect = locked_error
        
        with pytest.raises(sqlite3.OperationalError):
            _exec_many(mock_db, ["SELECT 1"])
        
        # Should have tried 5 times
        assert mock_db.execute_query.call_count == 5
        mock_db.connection.rollback.assert_called()

    def test_handles_empty_statements(self):
        """Should handle empty statement list."""
        mock_db = MagicMock()
        
        _exec_many(mock_db, [])
        
        mock_db.execute_query.assert_not_called()
        mock_db.connection.commit.assert_called_once()


class TestNormalizeExistingRows:
    """Tests for _normalize_existing_rows function."""

    @patch('utils.maintenance.normalize_advanced_muscles')
    def test_normalizes_rows(self, mock_normalize):
        """Should normalize advanced_isolated_muscles values."""
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            {"rid": 1, "advanced_isolated_muscles": "bicep; tricep"},
            {"rid": 2, "advanced_isolated_muscles": "chest"},
        ]
        mock_normalize.side_effect = [
            ["bicep", "tricep"],  # Normalized version
            ["chest"],
        ]
        
        _normalize_existing_rows(mock_db)
        
        mock_db.fetch_all.assert_called_once()
        assert mock_normalize.call_count == 2

    @patch('utils.maintenance.normalize_advanced_muscles')
    def test_updates_only_changed_rows(self, mock_normalize):
        """Should only update rows that changed."""
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            {"rid": 1, "advanced_isolated_muscles": "bicep, tricep"},  # Already normalized
            {"rid": 2, "advanced_isolated_muscles": "chest; back"},  # Needs normalizing
        ]
        mock_normalize.side_effect = [
            ["bicep", "tricep"],  # Same as input (comma-separated)
            ["chest", "back"],  # Different from input (had semicolons)
        ]
        
        _normalize_existing_rows(mock_db)
        
        # executemany should be called with updates
        mock_db.executemany.assert_called()

    @patch('utils.maintenance.normalize_advanced_muscles')
    def test_handles_null_values(self, mock_normalize):
        """Should handle null advanced_isolated_muscles."""
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            {"rid": 1, "advanced_isolated_muscles": None},
        ]
        mock_normalize.return_value = []
        
        _normalize_existing_rows(mock_db)
        
        # Should not raise


class TestNormalizeAndRebuildEim:
    """Tests for normalize_and_rebuild_eim function."""

    @patch('utils.maintenance._normalize_existing_rows')
    @patch('utils.maintenance._exec_many')
    @patch('utils.maintenance.DatabaseHandler')
    def test_executes_all_phases(self, mock_db_class, mock_exec_many, mock_normalize):
        """Should execute normalize SQL, normalize rows, and rebuild EIM."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_class.return_value = mock_db
        
        normalize_and_rebuild_eim()
        
        # Should call _exec_many twice (NORMALIZE_SQL and REBUILD_EIM_SQL)
        assert mock_exec_many.call_count == 2
        
        # Should normalize existing rows
        mock_normalize.assert_called_once_with(mock_db)
        
        # Should create table
        mock_db.execute_query.assert_called()

    @patch('utils.maintenance._normalize_existing_rows')
    @patch('utils.maintenance._exec_many')
    @patch('utils.maintenance.DatabaseHandler')
    def test_creates_eim_table(self, mock_db_class, mock_exec_many, mock_normalize):
        """Should create exercise_isolated_muscles table if not exists."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_class.return_value = mock_db
        
        normalize_and_rebuild_eim()
        
        # Check that CREATE TABLE was called
        create_call = mock_db.execute_query.call_args
        assert "CREATE TABLE IF NOT EXISTS exercise_isolated_muscles" in create_call[0][0]

    @patch('utils.maintenance._normalize_existing_rows')
    @patch('utils.maintenance._exec_many')
    @patch('utils.maintenance.DatabaseHandler')
    def test_order_of_operations(self, mock_db_class, mock_exec_many, mock_normalize):
        """Should execute in correct order: normalize SQL, normalize rows, create table, rebuild."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db_class.return_value = mock_db
        
        call_order = []
        
        def track_exec_many(db, statements):
            statements_str = " ".join(str(s) for s in statements)
            if "DELETE" in statements_str:
                call_order.append("rebuild")
            else:
                call_order.append("normalize_sql")
        
        mock_exec_many.side_effect = track_exec_many
        mock_normalize.side_effect = lambda db: call_order.append("normalize_rows")
        
        def track_execute(sql, *args, **kwargs):
            if "CREATE TABLE" in sql:
                call_order.append("create_table")
            return None
        
        mock_db.execute_query.side_effect = track_execute
        
        normalize_and_rebuild_eim()
        
        # Verify order
        assert call_order.index("normalize_sql") < call_order.index("normalize_rows")
        assert call_order.index("create_table") < call_order.index("rebuild")


class TestRebuildEimSqlLogic:
    """Tests for the REBUILD_EIM_SQL logic."""

    def test_delete_statement_present(self):
        """First statement should delete existing mappings."""
        assert REBUILD_EIM_SQL[0] == "DELETE FROM exercise_isolated_muscles;"

    def test_cte_splits_muscles_correctly(self):
        """CTE should handle comma and semicolon separation."""
        insert_sql = REBUILD_EIM_SQL[1]
        assert "WITH RECURSIVE" in insert_sql
        assert "REPLACE" in insert_sql  # Handles semicolons
        assert "TRIM" in insert_sql  # Trims whitespace
        assert "LOWER" in insert_sql  # Lowercases values

    def test_index_creation_statements(self):
        """Should have index creation statements."""
        index_statements = [s for s in REBUILD_EIM_SQL if "CREATE" in s and "INDEX" in s]
        assert len(index_statements) >= 2  # At least unique and regular index


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_exec_many_with_generator(self):
        """Should work with generator input."""
        mock_db = MagicMock()
        
        def gen_statements():
            yield "SELECT 1"
            yield "SELECT 2"
        
        _exec_many(mock_db, gen_statements())
        
        assert mock_db.execute_query.call_count == 2

    @patch('utils.maintenance.normalize_advanced_muscles')
    def test_normalize_handles_empty_db(self, mock_normalize):
        """Should handle empty exercises table."""
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = []
        
        _normalize_existing_rows(mock_db)
        
        mock_normalize.assert_not_called()
        mock_db.executemany.assert_not_called()
