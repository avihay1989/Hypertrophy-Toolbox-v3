#!/usr/bin/env python3
"""
Apply a curated YouTube video-id mapping into the exercises table.

Reads `data/youtube_curated_top_n.csv` (or any path supplied via --csv) and
writes `youtube_video_id` into rows of the `exercises` table whose
`exercise_name` matches a CSV entry (case-insensitive).

Validation is strict and all-or-nothing — the script collects every error
before any DB write, then either commits all updates or aborts without
touching the DB.

Validation rules:
  - Header row must be exactly: exercise_name,youtube_video_id
  - Every `exercise_name` must reference an existing `exercises.exercise_name`
    (case-insensitive).
  - Every `youtube_video_id` must match `^[A-Za-z0-9_-]{11}$` (the canonical
    YouTube video-id shape — 11 chars, alphanumeric + dash + underscore).
  - No duplicate `exercise_name` values (case-insensitive).
  - No blank ids.
  - Empty CSV (header only, no data rows) is allowed; the script reports
    "no rows to apply" and exits 0.

Idempotency: re-running with the same CSV content produces no DB delta —
each row is set to its already-present value.

Usage:
  .venv/Scripts/python.exe scripts/apply_youtube_curated.py
  .venv/Scripts/python.exe scripts/apply_youtube_curated.py --csv path/to/file.csv
  .venv/Scripts/python.exe scripts/apply_youtube_curated.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.database import DatabaseHandler  # noqa: E402

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
EXPECTED_HEADER = ("exercise_name", "youtube_video_id")
DEFAULT_CSV = REPO_ROOT / "data" / "youtube_curated_top_n.csv"


def is_valid_youtube_id(value: str) -> bool:
    return bool(value) and bool(YOUTUBE_ID_RE.match(value))


def parse_csv(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Parse the curated CSV. Returns (rows, errors)."""
    errors: list[str] = []
    rows: list[tuple[str, str]] = []

    if not path.exists():
        errors.append(f"CSV file not found: {path}")
        return rows, errors

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            errors.append(f"CSV is empty (no header): {path}")
            return rows, errors

        header_norm = tuple(col.strip().lower() for col in header)
        if header_norm != EXPECTED_HEADER:
            errors.append(
                f"CSV header must be {','.join(EXPECTED_HEADER)} "
                f"(got: {','.join(header)})"
            )
            return rows, errors

        seen: dict[str, int] = {}
        for line_no, raw in enumerate(reader, start=2):
            if not raw or all(not (cell or "").strip() for cell in raw):
                continue
            if len(raw) != 2:
                errors.append(
                    f"line {line_no}: expected 2 columns, got {len(raw)}"
                )
                continue

            name = (raw[0] or "").strip()
            video_id = (raw[1] or "").strip()

            if not name:
                errors.append(f"line {line_no}: blank exercise_name")
                continue
            if not video_id:
                errors.append(f"line {line_no}: blank youtube_video_id")
                continue
            if not is_valid_youtube_id(video_id):
                errors.append(
                    f"line {line_no}: invalid youtube_video_id "
                    f"{video_id!r} (must match ^[A-Za-z0-9_-]{{11}}$)"
                )
                continue

            key = name.lower()
            if key in seen:
                errors.append(
                    f"line {line_no}: duplicate exercise_name "
                    f"{name!r} (also seen on line {seen[key]})"
                )
                continue
            seen[key] = line_no

            rows.append((name, video_id))

    return rows, errors


def validate_against_db(rows: Iterable[tuple[str, str]]) -> list[str]:
    """Return a list of error strings for rows whose exercise_name is missing."""
    errors: list[str] = []
    with DatabaseHandler() as db:
        for name, _ in rows:
            existing = db.fetch_one(
                "SELECT exercise_name FROM exercises "
                "WHERE exercise_name = ? COLLATE NOCASE",
                (name,),
            )
            if not existing:
                errors.append(
                    f"exercise_name {name!r} not found in exercises table"
                )
    return errors


def apply_rows(rows: list[tuple[str, str]]) -> int:
    """Apply rows to DB. Returns number of rows updated."""
    updated = 0
    with DatabaseHandler() as db:
        for name, video_id in rows:
            db.execute_query(
                "UPDATE exercises SET youtube_video_id = ? "
                "WHERE exercise_name = ? COLLATE NOCASE",
                (video_id, name),
            )
            updated += 1
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply curated YouTube video-id mappings into exercises.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to curated CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate but do not write to the DB.",
    )
    args = parser.parse_args(argv)

    rows, errors = parse_csv(args.csv)
    if errors:
        print(f"FAILED: {len(errors)} validation error(s) in {args.csv}:",
              file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if not rows:
        print(f"OK: {args.csv} has no rows to apply (header-only CSV).")
        return 0

    db_errors = validate_against_db(rows)
    if db_errors:
        print(f"FAILED: {len(db_errors)} row(s) reference unknown exercises:",
              file=sys.stderr)
        for err in db_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"OK (dry-run): {len(rows)} row(s) would be applied.")
        return 0

    updated = apply_rows(rows)
    print(f"OK: applied {updated} row(s) to exercises.youtube_video_id.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
