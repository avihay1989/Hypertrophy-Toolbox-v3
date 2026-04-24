"""Create an isolated SQLite snapshot for visual-regression runs.

The app honors the DB_FILE environment variable. Run this script before P0b
capture, then point Playwright's web server at the printed DB path. By default
it snapshots the committed visual seed DB so normal E2E database mutations do
not change visual baselines:

    python e2e/scripts/prepare_visual_db.py
    $env:DB_FILE = "<printed path>"
    npx playwright test e2e/visual.spec.ts --project=chromium --update-snapshots
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = REPO_ROOT / "e2e" / "fixtures" / "database.visual.seed.db"
DEFAULT_SOURCE = DEFAULT_SEED if DEFAULT_SEED.exists() else REPO_ROOT / "data" / "database.db"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "visual" / "database.visual.db"


def _remove_sqlite_sidecars(database_path: Path) -> None:
    for candidate in (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
        Path(f"{database_path}-journal"),
    ):
        candidate.unlink(missing_ok=True)


def snapshot_database(source: Path, output: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Source database not found: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)
    _remove_sqlite_sidecars(output)

    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(output)) as dst:
        src.backup(dst)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    snapshot_database(args.source.resolve(), args.output.resolve())
    print(args.output.resolve())


if __name__ == "__main__":
    main()
