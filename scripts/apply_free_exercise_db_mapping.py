#!/usr/bin/env python3
"""Apply a reviewed free-exercise-db image mapping into exercises.media_path.

Reads `data/free_exercise_db_mapping.csv` (or any path supplied via
``--csv``) and writes ``media_path`` into rows of the ``exercises`` table
whose ``exercise_name`` matches a CSV entry (case-insensitive) AND whose
``review_status`` is one of ``{confirmed, manual}``.

Validation is strict and **all-or-nothing** — the script collects every
error before any DB write, then either commits all updates or aborts
without touching the DB.

CSV columns (in order):
    exercise_name, suggested_fed_id, suggested_image_path, score, review_status

review_status semantics:
    auto       — automated match below the human-review threshold; ignored.
    confirmed  — human-confirmed automated match; applied.
    manual     — human-curated mapping; applied.
    rejected   — human-rejected; ignored.

Rules enforced:

  - Header row must exactly match the canonical column list above.
  - ``exercise_name`` references an existing ``exercises.exercise_name``
    (case-insensitive). Missing names abort the whole apply.
  - For confirmed/manual rows: ``suggested_image_path`` is non-empty,
    matches the path-shape rules in :mod:`utils.media_path`, AND resolves
    to a real file under the vendor base directory.
  - For auto/rejected rows: ``suggested_image_path`` may be blank. If it
    is non-blank, it must still be shape-valid (so a future review can
    flip ``review_status`` without re-validating shape).
  - No duplicate ``exercise_name`` values (case-insensitive).
  - ``review_status`` must be one of the four canonical values.

Idempotency: re-running with the same CSV content produces no DB delta —
each confirmed/manual row is set to its already-present value.

Usage::

    .venv/Scripts/python.exe scripts/apply_free_exercise_db_mapping.py
    .venv/Scripts/python.exe scripts/apply_free_exercise_db_mapping.py --csv path/to/file.csv
    .venv/Scripts/python.exe scripts/apply_free_exercise_db_mapping.py --dry-run
    .venv/Scripts/python.exe scripts/apply_free_exercise_db_mapping.py --vendor-base /tmp/assets
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.database import DatabaseHandler  # noqa: E402
from utils.media_path import (  # noqa: E402
    VENDOR_BASE_REL,
    explain_media_path_shape_failure,
    is_valid_media_path_shape,
    media_path_resolves,
)

EXPECTED_HEADER: tuple[str, ...] = (
    "exercise_name",
    "suggested_fed_id",
    "suggested_image_path",
    "score",
    "review_status",
)
APPLY_STATUSES = frozenset({"confirmed", "manual"})
IGNORE_STATUSES = frozenset({"auto", "rejected"})
ALL_STATUSES = APPLY_STATUSES | IGNORE_STATUSES

DEFAULT_CSV = REPO_ROOT / "data" / "free_exercise_db_mapping.csv"
DEFAULT_VENDOR_BASE = REPO_ROOT / VENDOR_BASE_REL


@dataclass(frozen=True)
class MappingRow:
    """A parsed mapping row that has cleared per-row CSV-level checks."""

    exercise_name: str
    suggested_fed_id: str
    suggested_image_path: str
    score: str
    review_status: str
    line_no: int

    @property
    def applies(self) -> bool:
        return self.review_status in APPLY_STATUSES


def parse_csv(path: Path) -> tuple[list[MappingRow], list[str]]:
    """Parse the mapping CSV. Returns (rows, errors).

    On any header-level failure, returns an empty rows list. Otherwise
    returns *all* well-formed rows (whether they apply or not) plus any
    per-row errors collected. Callers should not write to the DB if the
    error list is non-empty.
    """
    errors: list[str] = []
    rows: list[MappingRow] = []

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

        seen_names: dict[str, int] = {}
        for line_no, raw in enumerate(reader, start=2):
            if not raw or all(not (cell or "").strip() for cell in raw):
                continue
            if len(raw) != len(EXPECTED_HEADER):
                errors.append(
                    f"line {line_no}: expected {len(EXPECTED_HEADER)} "
                    f"columns, got {len(raw)}"
                )
                continue

            exercise_name = (raw[0] or "").strip()
            suggested_fed_id = (raw[1] or "").strip()
            suggested_image_path = (raw[2] or "").strip()
            score = (raw[3] or "").strip()
            review_status = (raw[4] or "").strip().lower()

            if not exercise_name:
                errors.append(f"line {line_no}: blank exercise_name")
                continue

            if review_status not in ALL_STATUSES:
                errors.append(
                    f"line {line_no}: review_status {review_status!r} "
                    f"must be one of {sorted(ALL_STATUSES)}"
                )
                continue

            if review_status in APPLY_STATUSES:
                if not suggested_image_path:
                    errors.append(
                        f"line {line_no}: blank suggested_image_path is "
                        f"not allowed for review_status={review_status!r}"
                    )
                    continue
                shape_err = explain_media_path_shape_failure(
                    suggested_image_path
                )
                if shape_err is not None:
                    errors.append(
                        f"line {line_no}: invalid suggested_image_path "
                        f"{suggested_image_path!r} ({shape_err})"
                    )
                    continue
            elif suggested_image_path:
                # auto/rejected with a non-blank path: still validate shape
                # so a future review flip can rely on stored shape being
                # well-formed.
                shape_err = explain_media_path_shape_failure(
                    suggested_image_path
                )
                if shape_err is not None:
                    errors.append(
                        f"line {line_no}: invalid suggested_image_path "
                        f"{suggested_image_path!r} ({shape_err})"
                    )
                    continue

            if score:
                try:
                    float(score)
                except ValueError:
                    errors.append(
                        f"line {line_no}: score {score!r} must be numeric"
                    )
                    continue

            key = exercise_name.lower()
            if key in seen_names:
                errors.append(
                    f"line {line_no}: duplicate exercise_name "
                    f"{exercise_name!r} (also seen on line {seen_names[key]})"
                )
                continue
            seen_names[key] = line_no

            rows.append(
                MappingRow(
                    exercise_name=exercise_name,
                    suggested_fed_id=suggested_fed_id,
                    suggested_image_path=suggested_image_path,
                    score=score,
                    review_status=review_status,
                    line_no=line_no,
                )
            )

    return rows, errors


def validate_against_db(rows: Iterable[MappingRow]) -> list[str]:
    """Return error strings for rows whose exercise_name is missing in DB.

    Every row is checked, not just confirmed/manual ones — a typo in an
    auto/rejected row still indicates a stale catalogue reference that
    the human reviewer should fix before re-running.
    """
    errors: list[str] = []
    with DatabaseHandler() as db:
        for row in rows:
            existing = db.fetch_one(
                "SELECT exercise_name FROM exercises "
                "WHERE exercise_name = ? COLLATE NOCASE",
                (row.exercise_name,),
            )
            if not existing:
                errors.append(
                    f"line {row.line_no}: exercise_name "
                    f"{row.exercise_name!r} not found in exercises table"
                )
    return errors


def validate_assets(
    rows: Iterable[MappingRow], vendor_base: Path
) -> list[str]:
    """Return error strings for confirmed/manual rows whose asset is missing."""
    errors: list[str] = []
    for row in rows:
        if not row.applies:
            continue
        if not media_path_resolves(row.suggested_image_path, vendor_base):
            errors.append(
                f"line {row.line_no}: asset for "
                f"{row.exercise_name!r} not found at "
                f"{vendor_base}/{row.suggested_image_path}"
            )
    return errors


def apply_rows(rows: Iterable[MappingRow]) -> int:
    """Apply confirmed/manual rows in a single transaction. Returns rows updated.

    Each `UPDATE` runs with `commit=False` so the per-statement commits are
    suppressed; `DatabaseHandler.__exit__` commits once on clean exit, or
    rolls back if anything in the loop raises. Pre-apply validation catches
    expected errors before we get here, but this guards against unexpected
    mid-loop DB failures (e.g. SQLITE_BUSY) leaving the catalogue half-written.
    """
    updated = 0
    with DatabaseHandler() as db:
        for row in rows:
            if not row.applies:
                continue
            db.execute_query(
                "UPDATE exercises SET media_path = ? "
                "WHERE exercise_name = ? COLLATE NOCASE",
                (row.suggested_image_path, row.exercise_name),
                commit=False,
            )
            updated += 1
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply free-exercise-db image mappings into exercises.media_path.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to mapping CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--vendor-base",
        type=Path,
        default=DEFAULT_VENDOR_BASE,
        help=(
            "Vendor asset base directory used to resolve "
            "suggested_image_path (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate but do not write to the DB.",
    )
    args = parser.parse_args(argv)

    rows, errors = parse_csv(args.csv)
    if errors:
        print(
            f"FAILED: {len(errors)} validation error(s) in {args.csv}:",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if not rows:
        print(f"OK: {args.csv} has no rows to apply (header-only CSV).")
        return 0

    db_errors = validate_against_db(rows)
    if db_errors:
        print(
            f"FAILED: {len(db_errors)} row(s) reference unknown exercises:",
            file=sys.stderr,
        )
        for err in db_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    asset_errors = validate_assets(rows, args.vendor_base)
    if asset_errors:
        print(
            f"FAILED: {len(asset_errors)} confirmed/manual row(s) reference "
            "missing asset files:",
            file=sys.stderr,
        )
        for err in asset_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    apply_count = sum(1 for r in rows if r.applies)
    if args.dry_run:
        print(
            f"OK (dry-run): {apply_count} row(s) would be applied "
            f"({len(rows) - apply_count} ignored as auto/rejected)."
        )
        return 0

    updated = apply_rows(rows)
    ignored = len(rows) - updated
    print(
        f"OK: applied {updated} row(s) to exercises.media_path "
        f"({ignored} ignored as auto/rejected)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
