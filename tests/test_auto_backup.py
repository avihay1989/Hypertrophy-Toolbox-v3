"""Tests for utils/auto_backup.py's API-response metadata helper.

`describe_snapshot()` turns the `Path | None` returned by
`create_startup_backup()` into the JSON-safe shape the `/erase-data` route
hands to the frontend's `showAutoBackupBanner()` (Track B WPB.8). It is
intentionally decoupled from the SQLite copy itself so the erase route's
response contract can be exercised without touching a real database file.
"""
from __future__ import annotations

from pathlib import Path

from utils.auto_backup import describe_snapshot


def test_describe_snapshot_returns_none_when_no_snapshot_taken():
    assert describe_snapshot(None) is None


def test_describe_snapshot_returns_filename_only():
    snapshot_path = Path("data") / "auto_backup" / "database_20260704_153012.db"

    result = describe_snapshot(snapshot_path)

    assert result == {"filename": "database_20260704_153012.db"}


def test_describe_snapshot_strips_directory_regardless_of_path_shape():
    # Accepts a bare string path too, not just a Path instance.
    result = describe_snapshot("/some/absolute/dir/database_20260101_000000.db")

    assert result == {"filename": "database_20260101_000000.db"}
