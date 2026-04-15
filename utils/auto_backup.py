"""Automatic snapshot of the live SQLite database for disaster recovery."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import utils.config
from utils.logger import get_logger

logger = get_logger()

AUTO_BACKUP_DIRNAME = "auto_backup"
AUTO_BACKUP_KEEP = 7
MIN_EXERCISES_TO_BACKUP = 100


def _backup_dir(live_db_path: Path) -> Path:
    return live_db_path.parent / AUTO_BACKUP_DIRNAME


def _rotate(backup_dir: Path, keep: int) -> None:
    snapshots = sorted(
        backup_dir.glob("database_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in snapshots[keep:]:
        try:
            old.unlink()
            logger.debug("Rotated out old backup %s", old.name)
        except OSError:
            logger.exception("Failed to remove old backup %s", old)


def create_startup_backup() -> Path | None:
    """Copy the live DB to data/auto_backup/database_<timestamp>.db.

    Skips when TESTING=1, when the live DB is missing, or when it looks empty
    (<100 exercises). Uses the SQLite online-backup API so it is safe even
    while other connections are open. Rotates to keep the newest N snapshots.
    Returns the created path, or None if skipped.
    """
    if os.getenv("TESTING") == "1":
        return None

    live_db_path = Path(utils.config.DB_FILE).resolve()
    if not live_db_path.exists():
        return None

    try:
        src = sqlite3.connect(str(live_db_path))
        try:
            row = src.execute("SELECT COUNT(*) FROM exercises").fetchone()
            exercise_count = int(row[0]) if row else 0
        except sqlite3.Error:
            exercise_count = 0
        if exercise_count < MIN_EXERCISES_TO_BACKUP:
            src.close()
            logger.debug(
                "Skipping auto-backup: live DB has %s exercises (< %s)",
                exercise_count,
                MIN_EXERCISES_TO_BACKUP,
            )
            return None

        backup_dir = _backup_dir(live_db_path)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = backup_dir / f"database_{timestamp}.db"

        dst = sqlite3.connect(str(dest_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        _rotate(backup_dir, AUTO_BACKUP_KEEP)
        logger.info(
            "Auto-backup written to %s (%s exercises)", dest_path, exercise_count
        )
        return dest_path
    except (sqlite3.Error, OSError):
        logger.exception("Auto-backup failed")
        return None
