"""Database connection helpers and lightweight data-access abstraction."""
from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Iterable, Mapping, Sequence
from datetime import date as _date, datetime as _datetime
from pathlib import Path
from typing import Any, Optional, Union

from utils.config import DB_FILE
import utils.config  # For dynamic DB_FILE access in tests
from utils.logger import get_logger

logger = get_logger()


_SQLITE_CONVERTERS_REGISTERED = False
_RECOVERY_ATTEMPTS: dict[str, bool] = {}

# Thread-safe lock for database operations to prevent concurrent write corruption
_DB_LOCK = threading.RLock()

# Guard against double initialization during Flask auto-reload
_INITIALIZATION_COMPLETE: dict[str, bool] = {}
DATA_DIR = Path(DB_FILE).resolve().parent


def _register_sqlite_converters() -> None:
    """Register custom adapters/converters to silence deprecated defaults."""
    global _SQLITE_CONVERTERS_REGISTERED
    if _SQLITE_CONVERTERS_REGISTERED:
        return

    def _adapt_datetime(value: _datetime) -> str:
        return value.isoformat(sep=" ")

    def _adapt_date(value: _date) -> str:
        return value.isoformat()

    def _parse_timestamp(raw: bytes) -> Union[_datetime, str]:
        text = raw.decode("utf-8") if raw is not None else ""
        if not text:
            return text
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return _datetime.strptime(text, fmt)
            except ValueError:
                continue
        return text

    def _parse_date(raw: bytes) -> Union[_date, str]:
        text = raw.decode("utf-8") if raw is not None else ""
        if not text:
            return text
        try:
            return _date.fromisoformat(text)
        except ValueError:
            return text

    sqlite3.register_adapter(_datetime, _adapt_datetime)
    sqlite3.register_adapter(_date, _adapt_date)
    sqlite3.register_converter("timestamp", _parse_timestamp)
    sqlite3.register_converter("datetime", _parse_timestamp)
    sqlite3.register_converter("date", _parse_date)
    _SQLITE_CONVERTERS_REGISTERED = True


_register_sqlite_converters()


def _configure_connection(connection: sqlite3.Connection) -> sqlite3.Connection:
    """Apply the required PRAGMAs for every new connection."""
    import os
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    # Increase busy timeout to 30 seconds to handle concurrent access better
    connection.execute("PRAGMA busy_timeout = 30000;")
    
    # Use WAL mode only in production, not in debug mode
    # WAL mode + Flask auto-reloader = database corruption
    is_debug = os.getenv('FLASK_DEBUG', '1') == '1' or os.getenv('FLASK_ENV') == 'development'
    if not is_debug:
        connection.execute("PRAGMA journal_mode = WAL;")
    else:
        # Use DELETE mode (default) in development - safer with auto-reloader
        connection.execute("PRAGMA journal_mode = DELETE;")
    
    # Use FULL synchronous mode in development for maximum safety against corruption
    # NORMAL is faster but less safe during crashes/interruptions
    if is_debug:
        connection.execute("PRAGMA synchronous = FULL;")
    else:
        connection.execute("PRAGMA synchronous = NORMAL;")
    
    return connection


def _should_attempt_recovery(exc: sqlite3.DatabaseError, database_path: str) -> bool:
    """Return True when the exception indicates corruption and we have not retried yet."""
    message = str(exc).lower()
    if not message:
        return False
    corruption_markers = (
        "malformed",
        "not a database",
        "encrypted",
    )
    if not any(marker in message for marker in corruption_markers):
        return False
    already_attempted = _RECOVERY_ATTEMPTS.get(database_path)
    return not already_attempted


def _attempt_database_recovery(database_path: str) -> bool:
    """Quarantine the corrupted database file and restore a safe copy when available."""
    db_path = Path(database_path)
    _RECOVERY_ATTEMPTS[database_path] = True
    logger.error(
        "SQLite database at %s appears corrupted; attempting automatic recovery",
        db_path,
    )

    wal_suffixes = ("-wal", "-shm")
    for suffix in wal_suffixes:
        sidecar = db_path.with_name(db_path.name + suffix)
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError:
                logger.warning("Unable to remove sidecar file %s during recovery", sidecar)

    if db_path.exists():
        timestamp = _datetime.now().strftime("%Y%m%d_%H%M%S")
        corrupted_path = db_path.with_name(f"{db_path.name}.corrupted_{timestamp}")
        try:
            db_path.rename(corrupted_path)
            logger.warning("Renamed corrupted database to %s", corrupted_path)
        except OSError:
            logger.exception("Failed to quarantine corrupted database file %s", db_path)
            return False

    logger.warning("A fresh empty database will be created on next initialization")
    return True


def get_db_connection(database_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a new SQLite connection with the canonical configuration.
    
    Thread-safe: Acquires a global lock when connecting to prevent
    concurrent connection setup issues during Flask auto-reload.
    """
    # Use dynamic config lookup to support test overrides
    db_path = str(Path(database_path or utils.config.DB_FILE))
    attempted_recovery = False
    
    with _DB_LOCK:
        while True:
            try:
                connection = sqlite3.connect(
                    db_path,
                    detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                    check_same_thread=False,
                    timeout=30.0,  # Wait up to 30 seconds for database lock
                )
                try:
                    return _configure_connection(connection)
                except sqlite3.DatabaseError as exc:
                    connection.close()
                    raise exc
            except sqlite3.DatabaseError as exc:
                if not attempted_recovery and _should_attempt_recovery(exc, db_path):
                    attempted_recovery = True
                    if _attempt_database_recovery(db_path):
                        continue
                raise


class DatabaseHandler:
    """Context-friendly helper around SQLite connections.
    
    Thread-safe: Uses a global lock for write operations to prevent
    concurrent write corruption, especially during Flask auto-reload.
    """

    def __init__(self, database_path: Optional[str] = None) -> None:
        # Use dynamic config lookup to support test overrides
        self.database_path = database_path or utils.config.DB_FILE
        self.connection: sqlite3.Connection = get_db_connection(self.database_path)
        self.cursor: sqlite3.Cursor = self.connection.cursor()
        self._owns_lock = False

    # -- Core query helpers -------------------------------------------------
    def execute_query(
        self,
        query: str,
        params: Optional[Union[Sequence[Any], Mapping[str, Any], Any]] = None,
        *,
        commit: bool = True,
    ) -> int:
        """Execute a single statement and optionally commit.
        
        Thread-safe: Acquires a global lock for write operations.
        """
        prepared = self._prepare_params(params)
        start_time = time.time()
        
        # Determine if this is a write operation that needs locking
        operation = query.strip().split()[0].upper() if query else "UNKNOWN"
        is_write = operation in ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE")
        
        try:
            # Acquire lock for write operations to prevent concurrent write corruption
            if is_write:
                _DB_LOCK.acquire()
                self._owns_lock = True
            
            if prepared is None:
                self.cursor.execute(query)
            else:
                self.cursor.execute(query, prepared)
            if commit:
                self.connection.commit()
            
            # Calculate query duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log slow queries as WARNING
            if duration_ms > 100:
                logger.warning(
                    f"Slow query detected",
                    extra={
                        'duration_ms': round(duration_ms, 2),
                        'operation': operation,
                        'query': query[:200],  # Truncate to 200 chars
                        'params': str(prepared)[:100] if prepared else None,
                        'rowcount': self.cursor.rowcount
                    }
                )
            else:
                logger.debug(
                    f"SQL exec: {query[:120]} | params={prepared}",
                    extra={
                        'duration_ms': round(duration_ms, 2),
                        'operation': operation
                    }
                )
            
            return self.cursor.rowcount
        except sqlite3.Error as exc:  # pragma: no cover - logged for observability
            duration_ms = (time.time() - start_time) * 1000
            if commit:
                self.connection.rollback()
            logger.error(
                f"SQL error",
                extra={
                    'duration_ms': round(duration_ms, 2),
                    'query': query[:200],
                    'params': str(prepared)[:100] if prepared else None
                },
                exc_info=True
            )
            raise
        finally:
            # Always release the lock if we acquired it
            if is_write and self._owns_lock:
                self._owns_lock = False
                _DB_LOCK.release()

    def executemany(
        self,
        query: str,
        param_sets: Iterable[Union[Sequence[Any], Mapping[str, Any], Any]],
        *,
        commit: bool = True,
    ) -> int:
        """Execute the same statement for multiple parameter sets.
        
        Thread-safe: Acquires a global lock for write operations.
        """
        prepared_sets = list(self._prepare_params(params, for_many=True) for params in param_sets)
        start_time = time.time()
        
        # executemany is typically a write operation
        operation = query.strip().split()[0].upper() if query else "UNKNOWN"
        is_write = operation in ("INSERT", "UPDATE", "DELETE", "REPLACE")
        
        try:
            if is_write:
                _DB_LOCK.acquire()
                self._owns_lock = True
            
            self.cursor.executemany(query, prepared_sets)
            if commit:
                self.connection.commit()
            
            # Calculate query duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log batch operations
            logger.debug(
                f"SQL executemany: {query[:120]}",
                extra={
                    'duration_ms': round(duration_ms, 2),
                    'rowcount': self.cursor.rowcount
                }
            )
            
            return self.cursor.rowcount
        except sqlite3.Error as exc:  # pragma: no cover - logged for observability
            duration_ms = (time.time() - start_time) * 1000
            if commit:
                self.connection.rollback()
            logger.error(
                f"SQL executemany error",
                extra={
                    'duration_ms': round(duration_ms, 2),
                    'query': query[:200]
                },
                exc_info=True
            )
            raise
        finally:
            # Always release the lock if we acquired it
            if is_write and self._owns_lock:
                self._owns_lock = False
                _DB_LOCK.release()

    def fetch_one(
        self,
        query: str,
        params: Optional[Union[Sequence[Any], Mapping[str, Any], Any]] = None,
    ) -> Optional[dict[str, Any]]:
        prepared = self._prepare_params(params)
        start_time = time.time()
        
        if prepared is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, prepared)
        row = self.cursor.fetchone()
        
        # Calculate query duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log slow queries
        if duration_ms > 100:
            logger.warning(
                f"Slow query detected (fetch_one)",
                extra={
                    'duration_ms': round(duration_ms, 2),
                    'operation': 'SELECT',
                    'query': query[:200],
                    'params': str(prepared)[:100] if prepared else None,
                    'result': 'found' if row else 'not found'
                }
            )
        
        return dict(row) if row is not None else None

    def fetch_all(
        self,
        query: str,
        params: Optional[Union[Sequence[Any], Mapping[str, Any], Any]] = None,
    ) -> list[dict[str, Any]]:
        prepared = self._prepare_params(params)
        start_time = time.time()
        
        if prepared is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, prepared)
        rows = self.cursor.fetchall()
        
        # Calculate query duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log slow queries
        if duration_ms > 100:
            logger.warning(
                f"Slow query detected (fetch_all)",
                extra={
                    'duration_ms': round(duration_ms, 2),
                    'operation': 'SELECT',
                    'query': query[:200],
                    'params': str(prepared)[:100] if prepared else None,
                    'row_count': len(rows)
                }
            )
        
        return [dict(row) for row in rows]

    # -- Lifetime management -------------------------------------------------
    def close(self) -> None:
        if getattr(self, "connection", None):
            try:
                # Checkpoint WAL file before closing (if WAL mode is active)
                # This helps prevent corruption on unclean shutdowns
                self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except sqlite3.Error:
                # Ignore errors if not in WAL mode
                pass
            self.connection.close()
            logger.debug("SQLite connection closed")
            self.connection = None  # type: ignore[assignment]
            self.cursor = None  # type: ignore[assignment]

    def __enter__(self) -> "DatabaseHandler":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if getattr(self, "connection", None):
                if exc_type:
                    self.connection.rollback()
                else:
                    self.connection.commit()
        finally:
            self.close()

    # -- Internal helpers ---------------------------------------------------
    @staticmethod
    def _prepare_params(
        params: Optional[Union[Sequence[Any], Mapping[str, Any], Any]],
        *,
        for_many: bool = False,
    ) -> Optional[Union[Sequence[Any], Mapping[str, Any]]]:
        if params is None:
            return () if for_many else None
        if isinstance(params, Mapping):
            return params
        if isinstance(params, Sequence) and not isinstance(params, (str, bytes, bytearray)):
            return tuple(params)
        return (params,)

    # -- Convenience DDL helpers --------------------------------------------
    def add_progression_goals_table(self) -> None:
        """Ensure the progression_goals table exists."""
        ddl = """
            CREATE TABLE IF NOT EXISTS progression_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise TEXT NOT NULL,
                goal_type TEXT NOT NULL,
                current_value REAL,
                target_value REAL,
                goal_date DATE NOT NULL,
                created_at DATETIME NOT NULL,
                completed BOOLEAN DEFAULT 0,
                completed_at DATETIME
            )
        """
        self.execute_query(ddl)


def add_progression_goals_table() -> None:
    """Module-level helper to create the progression goals table."""
    with DatabaseHandler() as db:
        db.add_progression_goals_table()


def add_volume_tracking_tables() -> None:
    """Ensure the volume tracking supporting tables exist."""
    ddl_volume_plans = """
        CREATE TABLE IF NOT EXISTS volume_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            training_days INTEGER NOT NULL,
            created_at DATETIME NOT NULL
        )
    """
    ddl_muscle_volumes = """
        CREATE TABLE IF NOT EXISTS muscle_volumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            muscle_group TEXT NOT NULL,
            weekly_sets INTEGER NOT NULL,
            sets_per_session REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES volume_plans (id) ON DELETE CASCADE
        )
    """
    with DatabaseHandler() as db:
        db.execute_query(ddl_volume_plans)
        db.execute_query(ddl_muscle_volumes)
