"""Create an isolated, deterministic SQLite DB for the Chromium E2E suite.

The app honors ``DB_FILE``. Playwright's ``webServer.command`` runs this script
before starting the Flask app (``prepare_e2e_db.py --output <db> && python
app.py``) and points ``DB_FILE`` at the same output, so the whole suite runs
against a throwaway DB derived from the committed seed
(``e2e/fixtures/database.visual.seed.db``) — never the developer's live
``data/database.db``. Seeding lives in the web-server command (not
``globalSetup``) because Playwright starts ``webServer`` before ``globalSetup``,
which would otherwise race the app's first DB open.

The result is reproducible on every run: the full exercise catalog is preserved,
all user-state (profile, reference lifts, plan, logs, calibration, backups) is
emptied. Tests therefore start from an identical clean slate and never depend on
whatever happens to be in a developer's local database.

Reuses the snapshot + migration helpers from ``prepare_visual_db.py`` so there is
a single committed seed/prep pattern.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "e2e" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prepare_visual_db import apply_migrations, snapshot_database  # noqa: E402

DEFAULT_SEED = REPO_ROOT / "e2e" / "fixtures" / "database.visual.seed.db"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "e2e" / "database.e2e.db"

# Tables wiped so every suite run starts from an identical empty user-state.
# The exercise catalog (`exercises`, `exercise_isolated_muscles`) and any other
# lookup data are deliberately preserved. Wipes are guarded by table existence,
# so a seed/schema that lacks one of these is a no-op rather than an error.
USER_STATE_TABLES = (
    "user_profile",
    "user_profile_lifts",
    "user_profile_preferences",
    "user_selection",
    "workout_log",
    "progression_goals",
    "body_composition_snapshots",
    "muscle_volumes",
    "volume_plans",
    "program_backup_items",
    "program_backups",
    "learned_strength_calibrations",
    "user_calibration_settings",
)


def wipe_user_state(database_path: Path) -> None:
    con = sqlite3.connect(str(database_path))
    try:
        existing = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in USER_STATE_TABLES:
            if table in existing:
                con.execute(f"DELETE FROM {table}")
        con.commit()
    finally:
        con.close()


def _ensure_calibration_tables(database_path: Path) -> None:
    """Create the learned-calibration tables in the seed DB.

    ``apply_migrations`` (shared with the visual prep) predates the learned
    calibration feature, so it does not create these. The Profile page now reads
    ``user_calibration_settings`` on every render, so a seed missing the table
    500s the whole page. Create them here so the E2E DB is self-sufficient and
    does not rely on app startup having run first.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import utils.config

    utils.config.DB_FILE = str(database_path)
    from utils.database import add_strength_calibration_tables

    add_strength_calibration_tables()


def prepare(source: Path, output: Path) -> Path:
    output = output.resolve()
    snapshot_database(source.resolve(), output)
    # apply_migrations brings a possibly-older seed up to the current schema
    # (body_composition, etc.); the calibration tables need a separate call.
    apply_migrations(output)
    _ensure_calibration_tables(output)
    wipe_user_state(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(prepare(args.source, args.output))


if __name__ == "__main__":
    main()
