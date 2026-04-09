"""
Tests for utils/database_indexes.py - Database index management.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sqlite3
from utils.database_indexes import (
    create_performance_indexes,
    optimize_database,
    analyze_query_plan,
    get_index_list,
)


class TestCreatePerformanceIndexes:
    """Tests for create_performance_indexes function."""

    @patch('utils.database_indexes.DatabaseHandler')
    def test_creates_expected_indexes(self, mock_db_class):
        """Should attempt to create commonly used indexes."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_one.return_value = None  # Index doesn't exist
        mock_db_class.return_value = mock_db
        
        create_performance_indexes()
        
        # Should have created multiple indexes
        assert mock_db.execute_query.call_count > 0
        
        # Check common index names were created
        all_calls = [str(c) for c in mock_db.execute_query.call_args_list]
        combined_calls = " ".join(all_calls)
        assert "exercises" in combined_calls
        assert "CREATE INDEX" in combined_calls

    @patch('utils.database_indexes.DatabaseHandler')
    def test_skips_existing_indexes(self, mock_db_class):
        """Should skip indexes that already exist."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        # All indexes exist
        mock_db.fetch_one.return_value = {"name": "existing_index"}
        mock_db_class.return_value = mock_db
        
        create_performance_indexes()
        
        # Should only have checked, not created
        create_calls = [c for c in mock_db.execute_query.call_args_list 
                       if "CREATE INDEX" in str(c)]
        assert len(create_calls) == 0

    @patch('utils.database_indexes.DatabaseHandler')
    def test_handles_sqlite_error(self, mock_db_class):
        """Should continue on SQLite error for individual index."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_one.return_value = None
        mock_db.execute_query.side_effect = sqlite3.Error("Index error")
        mock_db_class.return_value = mock_db
        
        # Should not raise, just log and continue
        create_performance_indexes()

    @patch('utils.database_indexes.DatabaseHandler')
    def test_checks_index_existence_before_create(self, mock_db_class):
        """Should check if index exists before creating."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_one.return_value = None
        mock_db_class.return_value = mock_db
        
        create_performance_indexes()
        
        # Should have called fetch_one to check for existing indexes
        check_calls = [c for c in mock_db.fetch_one.call_args_list 
                      if "sqlite_master" in str(c)]
        assert len(check_calls) > 0


class TestOptimizeDatabase:
    """Tests for optimize_database function."""

    @patch('utils.database_indexes.get_db_connection')
    def test_runs_analyze(self, mock_get_conn):
        """Should run ANALYZE command."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        optimize_database()
        
        mock_conn.execute.assert_any_call("ANALYZE")

    @patch('utils.database_indexes.get_db_connection')
    def test_runs_pragma_optimize(self, mock_get_conn):
        """Should run PRAGMA optimize."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        optimize_database()
        
        mock_conn.execute.assert_any_call("PRAGMA optimize")

    @patch('utils.database_indexes.get_db_connection')
    def test_commits_changes(self, mock_get_conn):
        """Should commit changes."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        optimize_database()
        
        mock_conn.commit.assert_called_once()

    @patch('utils.database_indexes.get_db_connection')
    def test_closes_connection(self, mock_get_conn):
        """Should close connection in finally block."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        optimize_database()
        
        mock_conn.close.assert_called_once()

    @patch('utils.database_indexes.get_db_connection')
    def test_closes_connection_on_error(self, mock_get_conn):
        """Should close connection even on error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("Optimization error")
        mock_get_conn.return_value = mock_conn
        
        # Should not raise
        optimize_database()
        
        mock_conn.close.assert_called_once()

    @patch('utils.database_indexes._DB_LOCK')
    @patch('utils.database_indexes.get_db_connection')
    def test_uses_global_lock_for_maintenance_commands(self, mock_get_conn, mock_lock):
        """Should hold the shared DB lock while running maintenance commands."""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        optimize_database()

        mock_lock.acquire.assert_called_once()
        mock_lock.release.assert_called_once()

    @patch('utils.database_indexes.get_db_connection')
    def test_rolls_back_on_error(self, mock_get_conn):
        """Should roll back maintenance work if SQLite raises an error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("Optimization error")
        mock_get_conn.return_value = mock_conn

        optimize_database()

        mock_conn.rollback.assert_called_once()


class TestAnalyzeQueryPlan:
    """Tests for analyze_query_plan function."""

    @patch('utils.database_indexes.DatabaseHandler')
    def test_returns_query_plan(self, mock_db_class):
        """Should return query execution plan."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = [
            {"id": 0, "parent": 0, "detail": "SCAN TABLE exercises"},
            {"id": 1, "parent": 0, "detail": "SEARCH TABLE exercises USING INDEX idx_primary"}
        ]
        mock_db_class.return_value = mock_db
        
        result = analyze_query_plan("SELECT * FROM exercises WHERE primary_muscle_group = ?", ("Chest",))
        
        assert len(result) == 2
        assert "SCAN" in str(result[0]) or "detail" in result[0]

    @patch('utils.database_indexes.DatabaseHandler')
    def test_prepends_explain_query_plan(self, mock_db_class):
        """Should prepend EXPLAIN QUERY PLAN to query."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = []
        mock_db_class.return_value = mock_db
        
        analyze_query_plan("SELECT * FROM exercises")
        
        call_args = mock_db.fetch_all.call_args[0][0]
        assert call_args.startswith("EXPLAIN QUERY PLAN")
        assert "SELECT * FROM exercises" in call_args

    @patch('utils.database_indexes.DatabaseHandler')
    def test_passes_params(self, mock_db_class):
        """Should pass query parameters."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = []
        mock_db_class.return_value = mock_db
        
        analyze_query_plan("SELECT * FROM exercises WHERE id = ?", (1,))
        
        call_args = mock_db.fetch_all.call_args
        assert call_args[0][1] == (1,)

    @patch('utils.database_indexes.DatabaseHandler')
    def test_handles_query_without_params(self, mock_db_class):
        """Should handle query without parameters."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = []
        mock_db_class.return_value = mock_db
        
        analyze_query_plan("SELECT COUNT(*) FROM exercises")
        
        # Should call without params arg
        mock_db.fetch_all.assert_called_once()


class TestGetIndexList:
    """Tests for get_index_list function."""

    @patch('utils.database_indexes.DatabaseHandler')
    def test_returns_index_list(self, mock_db_class):
        """Should return list of all indexes."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = [
            {"name": "idx_exercises_primary", "tbl_name": "exercises", "sql": "CREATE INDEX..."},
            {"name": "idx_exercises_equipment", "tbl_name": "exercises", "sql": "CREATE INDEX..."},
        ]
        mock_db_class.return_value = mock_db
        
        result = get_index_list()
        
        assert len(result) == 2
        assert result[0]["name"] == "idx_exercises_primary"
        assert result[1]["name"] == "idx_exercises_equipment"

    @patch('utils.database_indexes.DatabaseHandler')
    def test_excludes_sqlite_internal_indexes(self, mock_db_class):
        """Should query to exclude sqlite_% internal indexes."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = []
        mock_db_class.return_value = mock_db
        
        get_index_list()
        
        query = mock_db.fetch_all.call_args[0][0]
        assert "NOT LIKE 'sqlite_%'" in query

    @patch('utils.database_indexes.DatabaseHandler')
    def test_orders_by_table_and_name(self, mock_db_class):
        """Should order results by table name and index name."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = []
        mock_db_class.return_value = mock_db
        
        get_index_list()
        
        query = mock_db.fetch_all.call_args[0][0]
        assert "ORDER BY tbl_name, name" in query

    @patch('utils.database_indexes.DatabaseHandler')
    def test_returns_empty_list_when_no_indexes(self, mock_db_class):
        """Should return empty list when no indexes exist."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_all.return_value = []
        mock_db_class.return_value = mock_db
        
        result = get_index_list()
        
        assert result == []


class TestIndexDefinitions:
    """Tests for the index definitions in create_performance_indexes."""

    @patch('utils.database_indexes.DatabaseHandler')
    def test_creates_primary_muscle_index(self, mock_db_class):
        """Should create index on primary_muscle_group."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_one.return_value = None
        mock_db_class.return_value = mock_db
        
        create_performance_indexes()
        
        calls = [str(c) for c in mock_db.execute_query.call_args_list]
        assert any("primary_muscle_group" in c for c in calls)

    @patch('utils.database_indexes.DatabaseHandler')
    def test_creates_equipment_index(self, mock_db_class):
        """Should create index on equipment."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_one.return_value = None
        mock_db_class.return_value = mock_db
        
        create_performance_indexes()
        
        calls = [str(c) for c in mock_db.execute_query.call_args_list]
        assert any("equipment" in c for c in calls)

    @patch('utils.database_indexes.DatabaseHandler')
    def test_creates_composite_indexes(self, mock_db_class):
        """Should create composite indexes for common filter combinations."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_one.return_value = None
        mock_db_class.return_value = mock_db
        
        create_performance_indexes()
        
        calls = [str(c) for c in mock_db.execute_query.call_args_list]
        # Should have composite indexes (contain comma)
        composite_calls = [c for c in calls if ", " in c and "CREATE INDEX" in c]
        assert len(composite_calls) > 0

    @patch('utils.database_indexes.DatabaseHandler')
    def test_creates_user_selection_indexes(self, mock_db_class):
        """Should create indexes for user_selection table."""
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.fetch_one.return_value = None
        mock_db_class.return_value = mock_db
        
        create_performance_indexes()
        
        calls = [str(c) for c in mock_db.execute_query.call_args_list]
        assert any("user_selection" in c for c in calls)
