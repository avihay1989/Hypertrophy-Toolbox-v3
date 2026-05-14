#!/usr/bin/env python3
"""Curate the free-exercise-db mapping CSV: flip auto rows to confirmed.

Reads ``data/free_exercise_db_mapping.csv`` and writes back a version
where rows that pass a strict structural-equivalence check have their
``review_status`` flipped from ``auto`` to ``confirmed``. Re-running on
the curated CSV is a no-op (idempotent).

The structural-equivalence rule is deliberately conservative — the
mapper's name+equipment+muscle score is correlated with correctness but
high-score false matches exist (e.g. ``Barbell Decline Bench Press`` →
``Barbell_Incline_Bench_Press`` at score 100). The rule used here:

  After lenient token normalization (lowercase, plural-strip, alias
  collapse for ``band/bands`` etc., stopword removal, punctuation noise
  removed), the **full** upstream name (including any ``" - <variant>"``
  suffix) must produce the **same token set** as the local name.

That excludes any row where local has a position/direction/grip modifier
the upstream lacks (or vice versa). The match must agree on every
non-noise token.

Rows that pass the rule AND have ``score >= --confirm-floor`` (default
60) AND a non-blank ``suggested_image_path`` AND an existing on-disk
asset are flipped to ``confirmed``. Everything else is left untouched.

The script does not write to the DB. Run
``scripts/apply_free_exercise_db_mapping.py --dry-run`` afterwards to
verify the curated CSV.

Usage::

    .venv/Scripts/python.exe scripts/curate_free_exercise_db_mapping.py
    .venv/Scripts/python.exe scripts/curate_free_exercise_db_mapping.py --dry-run
    .venv/Scripts/python.exe scripts/curate_free_exercise_db_mapping.py --confirm-floor 80
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CSV = REPO_ROOT / "data" / "free_exercise_db_mapping.csv"
DEFAULT_VENDOR_JSON = REPO_ROOT / "static" / "vendor" / "free-exercise-db" / "exercises.json"
DEFAULT_VENDOR_BASE = REPO_ROOT / "static" / "vendor" / "free-exercise-db" / "exercises"

CSV_HEADER: tuple[str, ...] = (
    "exercise_name",
    "suggested_fed_id",
    "suggested_image_path",
    "score",
    "review_status",
)

NOISE_RE = re.compile(r"[\-_/,()\[\]]+")
WHITESPACE_RE = re.compile(r"\s+")

LOCAL_CUE_SUFFIX_RE = re.compile(
    r"\s*-\s*(?:quadriceps|quads|glutes|hamstrings|chest|"
    r"shoulders|back|biceps|triceps|calves|core|abs|lats)"
    r"\s+focused\s*$",
    flags=re.IGNORECASE,
)

STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "with", "of", "for", "grip", "medium",
})

TOKEN_ALIASES: dict[str, str] = {
    "bands": "band", "banded": "band",
    "dumbbells": "dumbbell", "dumbell": "dumbbell",
    "dumbells": "dumbbell", "db": "dumbbell",
    "kettlebells": "kettlebell",
    "cables": "cable",
    "machines": "machine",
    "crunches": "crunch",
    "curls": "curl", "presses": "press", "squats": "squat",
    "raises": "raise", "rows": "row",
    "extensions": "extension",
    "flyes": "fly", "flies": "fly", "flys": "fly",
    "climbers": "climber", "ups": "up", "dips": "dip",
    "pulldowns": "pulldown", "pullups": "pullup", "pull-ups": "pullup",
    "deadlifts": "deadlift", "lunges": "lunge", "shrugs": "shrug",
    "adductions": "adduction", "kickbacks": "kickback",
    "mornings": "morning",
}


def _strip_local_cue_suffix(name: str) -> str:
    """Strip the local catalogue's ' - <muscle> focused' cue suffix.

    The starter-plan generator labels variants like ``"Barbell Step Up -
    Quadriceps focused"`` where the suffix is a coaching cue, not a
    distinct exercise. Upstream has no such suffix, so unstripped names
    fail token equality. The upstream-side ``" - <variant>"`` suffix is
    already handled by the mapper before write; this is the local-side
    analogue.
    """
    return LOCAL_CUE_SUFFIX_RE.sub("", name)


def normalize_tokens(name: str) -> frozenset[str]:
    """Lowercase, strip punctuation noise, drop stopwords, alias, plural-trim."""
    if not name:
        return frozenset()
    cleaned = NOISE_RE.sub(" ", _strip_local_cue_suffix(name).lower())
    out: list[str] = []
    for raw in WHITESPACE_RE.split(cleaned):
        if not raw or raw in STOPWORDS:
            continue
        if raw in TOKEN_ALIASES:
            out.append(TOKEN_ALIASES[raw])
            continue
        if len(raw) > 3 and raw.endswith("s"):
            out.append(raw[:-1])
        else:
            out.append(raw)
    return frozenset(out)


@dataclass(frozen=True)
class CsvRow:
    exercise_name: str
    suggested_fed_id: str
    suggested_image_path: str
    score: str
    review_status: str

    def to_tuple(self) -> tuple[str, str, str, str, str]:
        return (
            self.exercise_name,
            self.suggested_fed_id,
            self.suggested_image_path,
            self.score,
            self.review_status,
        )


def load_csv(path: Path) -> list[CsvRow]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if tuple(header or ()) != CSV_HEADER:
            raise SystemExit(
                f"FAILED: unexpected CSV header in {path}: got {header!r}, "
                f"expected {list(CSV_HEADER)!r}"
            )
        rows: list[CsvRow] = []
        for raw in reader:
            if len(raw) != len(CSV_HEADER):
                raise SystemExit(
                    f"FAILED: column count mismatch in {path}: {raw!r}"
                )
            rows.append(CsvRow(*raw))
    return rows


def load_upstream_index(path: Path) -> dict[str, str]:
    """Map upstream fed_id -> upstream exercise name."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {entry["id"]: entry.get("name", "") for entry in data}


@dataclass(frozen=True)
class CurationStats:
    total: int
    already_confirmed: int
    flipped_to_confirmed: int
    left_auto: int
    other_status: int


def curate(
    rows: list[CsvRow],
    fed_id_to_name: dict[str, str],
    vendor_base: Path,
    confirm_floor: int,
) -> tuple[list[CsvRow], CurationStats, list[tuple[CsvRow, str]]]:
    """Return (new_rows, stats, flipped) — does not mutate input."""
    out: list[CsvRow] = []
    flipped: list[tuple[CsvRow, str]] = []
    already_confirmed = 0
    flipped_count = 0
    left_auto = 0
    other_status = 0
    for row in rows:
        status = row.review_status
        if status == "confirmed":
            already_confirmed += 1
            out.append(row)
            continue
        if status not in ("auto",):
            other_status += 1
            out.append(row)
            continue
        if not row.suggested_image_path or not row.suggested_fed_id:
            left_auto += 1
            out.append(row)
            continue
        try:
            score_int = int(row.score)
        except ValueError:
            left_auto += 1
            out.append(row)
            continue
        if score_int < confirm_floor:
            left_auto += 1
            out.append(row)
            continue
        upstream_name = fed_id_to_name.get(row.suggested_fed_id)
        if not upstream_name:
            left_auto += 1
            out.append(row)
            continue
        if normalize_tokens(row.exercise_name) != normalize_tokens(upstream_name):
            left_auto += 1
            out.append(row)
            continue
        asset_path = vendor_base / row.suggested_image_path
        if not asset_path.is_file():
            left_auto += 1
            out.append(row)
            continue
        out.append(CsvRow(
            exercise_name=row.exercise_name,
            suggested_fed_id=row.suggested_fed_id,
            suggested_image_path=row.suggested_image_path,
            score=row.score,
            review_status="confirmed",
        ))
        flipped.append((row, upstream_name))
        flipped_count += 1
    stats = CurationStats(
        total=len(rows),
        already_confirmed=already_confirmed,
        flipped_to_confirmed=flipped_count,
        left_auto=left_auto,
        other_status=other_status,
    )
    return out, stats, flipped


def write_csv(rows: list[CsvRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow(row.to_tuple())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Curate the free-exercise-db mapping CSV.",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        help="Path to mapping CSV (read and written).")
    parser.add_argument("--vendor-json", type=Path, default=DEFAULT_VENDOR_JSON,
                        help="Path to vendored exercises.json.")
    parser.add_argument("--vendor-base", type=Path, default=DEFAULT_VENDOR_BASE,
                        help="Vendor asset base directory.")
    parser.add_argument("--confirm-floor", type=int, default=60,
                        help="Minimum mapper score to consider for confirm (default 60).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute and report; do not write the CSV.")
    parser.add_argument("--verbose", action="store_true",
                        help="Print every flipped row.")
    args = parser.parse_args(argv)

    if not args.csv.is_file():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 2
    if not args.vendor_json.is_file():
        print(f"ERROR: vendor JSON not found: {args.vendor_json}", file=sys.stderr)
        return 2
    if not args.vendor_base.is_dir():
        print(f"ERROR: vendor base dir not found: {args.vendor_base}", file=sys.stderr)
        return 2

    rows = load_csv(args.csv)
    fed_id_to_name = load_upstream_index(args.vendor_json)
    new_rows, stats, flipped = curate(rows, fed_id_to_name, args.vendor_base, args.confirm_floor)

    print(f"input rows:            {stats.total}")
    print(f"  already confirmed:   {stats.already_confirmed}")
    print(f"  flipped to confirmed: {stats.flipped_to_confirmed}")
    print(f"  left as auto:        {stats.left_auto}")
    print(f"  other status:        {stats.other_status}")
    total_confirmed = stats.already_confirmed + stats.flipped_to_confirmed
    print(f"total confirmed after curation: {total_confirmed}")

    if args.verbose:
        print()
        print("=== Flipped rows ===")
        for row, upstream in flipped:
            print(f"  {row.score:>3} | {row.exercise_name!r} -> {upstream!r}")

    if args.dry_run:
        print()
        print(f"DRY-RUN: not writing {args.csv}")
        return 0

    write_csv(new_rows, args.csv)
    print()
    print(f"wrote curated CSV to {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
