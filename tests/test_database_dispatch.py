"""Regression tests for DatabaseHandler write-lock dispatch (Track A8).

``execute_query`` / ``executemany`` used to classify statements by their
leading keyword only, so CTE-prefixed writes (``WITH ... INSERT/UPDATE/
DELETE``) — including ``utils.maintenance.REBUILD_EIM_SQL`` — skipped
``_DB_LOCK`` and ran on the read path. The lock-dispatch tests here fail
against that pre-fix behavior.
"""

import threading

import pytest

import utils.config
import utils.database
from utils.database import DatabaseHandler
from utils.maintenance import REBUILD_EIM_SQL


class RecordingLock:
    """RLock stand-in that counts acquire/release calls."""

    def __init__(self):
        self._lock = threading.RLock()
        self.acquires = 0
        self.releases = 0

    def acquire(self, *args, **kwargs):
        self.acquires += 1
        return self._lock.acquire(*args, **kwargs)

    def release(self):
        self.releases += 1
        return self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc_info):
        self.release()
        return False


@pytest.fixture
def dispatch_handler(tmp_path, monkeypatch):
    """Handler bound to a throwaway DB with the tables the tests touch."""
    db_path = str(tmp_path / "dispatch.db")
    monkeypatch.setattr(utils.config, "DB_FILE", db_path)
    handler = DatabaseHandler(db_path)
    handler.execute_query("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    handler.execute_query("INSERT INTO t (name) VALUES ('seed')")
    handler.execute_query(
        "CREATE TABLE exercises (exercise_name TEXT, advanced_isolated_muscles TEXT)"
    )
    handler.execute_query(
        "CREATE TABLE exercise_isolated_muscles ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, exercise_name TEXT, muscle TEXT)"
    )
    handler.execute_query(
        "INSERT INTO exercises (exercise_name, advanced_isolated_muscles) "
        "VALUES ('Bench Press', 'chest, triceps')"
    )
    yield handler
    handler.close()


@pytest.fixture
def recording_lock(monkeypatch):
    """Swap the module-level write lock for a counting stand-in.

    Ordered after ``dispatch_handler`` in test signatures so that handler
    setup (which also touches ``_DB_LOCK``) is not counted.
    """
    lock = RecordingLock()
    monkeypatch.setattr(utils.database, "_DB_LOCK", lock)
    return lock


WRITE_STATEMENTS = [
    pytest.param(
        "INSERT INTO t (name) VALUES ('x')",
        id="plain-insert",
    ),
    pytest.param(
        "WITH src(name) AS (SELECT 'cte') INSERT INTO t (name) SELECT name FROM src",
        id="with-insert",
    ),
    pytest.param(
        "WITH ids(i) AS (SELECT 1) UPDATE t SET name = 'y' "
        "WHERE id IN (SELECT i FROM ids)",
        id="with-update",
    ),
    pytest.param(
        "WITH ids(i) AS (SELECT 1) DELETE FROM t WHERE id IN (SELECT i FROM ids)",
        id="with-delete",
    ),
    pytest.param(
        "-- leading comment\nWITH src(name) AS (SELECT 'c') "
        "INSERT INTO t (name) SELECT name FROM src",
        id="comment-then-with-insert",
    ),
]

READ_STATEMENTS = [
    pytest.param("SELECT name FROM t", id="plain-select"),
    pytest.param(
        "WITH src(name) AS (SELECT 'cte') SELECT name FROM src",
        id="with-select",
    ),
    pytest.param(
        "WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM seq "
        "WHERE n < 3) SELECT n FROM seq",
        id="with-recursive-select",
    ),
]


class TestExecuteQueryLockDispatch:
    @pytest.mark.parametrize("statement", WRITE_STATEMENTS)
    def test_write_statements_acquire_lock(
        self, dispatch_handler, recording_lock, statement
    ):
        dispatch_handler.execute_query(statement)
        assert recording_lock.acquires == 1
        assert recording_lock.releases == 1

    @pytest.mark.parametrize("statement", READ_STATEMENTS)
    def test_read_statements_skip_lock(
        self, dispatch_handler, recording_lock, statement
    ):
        dispatch_handler.execute_query(statement)
        assert recording_lock.acquires == 0

    def test_cte_insert_still_writes_rows(self, dispatch_handler, recording_lock):
        dispatch_handler.execute_query(
            "WITH src(name) AS (SELECT 'cte-row') "
            "INSERT INTO t (name) SELECT name FROM src"
        )
        row = dispatch_handler.fetch_one(
            "SELECT COUNT(*) AS n FROM t WHERE name = 'cte-row'"
        )
        assert row["n"] == 1

    def test_rebuild_eim_statement_acquires_lock(
        self, dispatch_handler, recording_lock
    ):
        """The real maintenance CTE insert must take the write path."""
        cte_inserts = [
            sql for sql in REBUILD_EIM_SQL if sql.strip().upper().startswith("WITH")
        ]
        assert len(cte_inserts) == 1
        dispatch_handler.execute_query(cte_inserts[0])
        assert recording_lock.acquires == 1
        assert recording_lock.releases == 1
        row = dispatch_handler.fetch_one(
            "SELECT COUNT(*) AS n FROM exercise_isolated_muscles"
        )
        assert row["n"] == 2  # 'chest' + 'triceps' split from the seed row


class TestExecutemanyLockDispatch:
    def test_cte_insert_acquires_lock(self, dispatch_handler, recording_lock):
        dispatch_handler.executemany(
            "WITH src(name) AS (SELECT ?) INSERT INTO t (name) SELECT name FROM src",
            [("a",), ("b",)],
        )
        assert recording_lock.acquires == 1
        assert recording_lock.releases == 1
        row = dispatch_handler.fetch_one(
            "SELECT COUNT(*) AS n FROM t WHERE name IN ('a', 'b')"
        )
        assert row["n"] == 2


class TestCteWriteConcurrency:
    def test_cte_write_blocks_while_lock_held(self, dispatch_handler, recording_lock):
        """A CTE write must wait on _DB_LOCK like any other write."""
        statement = (
            "WITH src(name) AS (SELECT 'blocked') "
            "INSERT INTO t (name) SELECT name FROM src"
        )
        done = threading.Event()

        def worker():
            dispatch_handler.execute_query(statement)
            done.set()

        recording_lock.acquire()  # simulate another writer holding the lock
        try:
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            assert not done.wait(timeout=0.5), (
                "CTE write completed without waiting for the write lock"
            )
        finally:
            recording_lock.release()
        assert done.wait(timeout=5), "CTE write did not complete after lock release"
        thread.join(timeout=5)


class TestStatementOperation:
    """Unit cases for the CTE-aware classifier itself."""

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("SELECT 1", "SELECT"),
            ("INSERT INTO t VALUES (1)", "INSERT"),
            ("  update t set name = 'x'", "UPDATE"),
            ("WITH a AS (SELECT 1) SELECT * FROM a", "SELECT"),
            ("WITH a AS (SELECT 1) INSERT INTO t SELECT * FROM a", "INSERT"),
            ("with a as (select 1) insert into t select * from a", "INSERT"),
            ("WITH a AS (SELECT 1), b AS (SELECT 2) UPDATE t SET name = 'x'", "UPDATE"),
            ("WITH RECURSIVE a(n) AS (SELECT 1) DELETE FROM t", "DELETE"),
            (
                "/* block */ -- line\nWITH a AS (SELECT 1) INSERT INTO t SELECT 1",
                "INSERT",
            ),
            # Unbalanced parens inside a string literal must not derail the scan
            ("WITH a AS (SELECT '(((') INSERT INTO t SELECT 1", "INSERT"),
            # Quoted identifier that collides with a verb keyword
            ('WITH "select" AS (SELECT 1) INSERT INTO t SELECT 1', "INSERT"),
            ("", "UNKNOWN"),
            ("   ", "UNKNOWN"),
        ],
    )
    def test_classification(self, query, expected):
        assert utils.database._statement_operation(query) == expected
