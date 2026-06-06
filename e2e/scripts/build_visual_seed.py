"""Regenerate the committed visual-regression seed DB.

Produces ``e2e/fixtures/database.visual.seed.db``: the full exercise catalog
with free-exercise-db ``media_path`` values applied, **plus** a small,
deterministic plan (``user_selection``) and matching ``workout_log`` rows. The
visual specs need this populated state so the workout-plan / workout-log tables
render real rows with thumbnails, and so the data-driven analyze pages
(weekly-summary, session-summary, progression) render a representative
populated app rather than empty states.

Why this script exists: the prior seed (refreshed in de89c89) carried the
catalog only — 0 ``user_selection`` rows and no ``media_path`` column — so the
visual specs rendered empty tables and the thumbnails spec could not run. The
visual seed must *itself* contain the visual state; ``prepare_visual_db.py``
only adds the empty ``media_path`` column during migration, it never populates
it. This generator bakes both the media mapping and the deterministic plan into
the committed fixture.

Determinism: the plan/log content is fixed (curated exercise list, fixed
sets/reps/weights, fixed timestamps) so re-running produces a byte-stable
fixture. The media mapping comes from the reviewed
``data/free_exercise_db_mapping.csv`` (same path the production apply script
uses), validated against on-disk vendor assets.

Source is the existing committed seed (catalog) — **never** the live
``data/database.db``. The build happens in a throwaway temp DB; the fixture is
overwritten only on success.

    .venv/Scripts/python.exe e2e/scripts/build_visual_seed.py
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURE = REPO_ROOT / "e2e" / "fixtures" / "database.visual.seed.db"

# A single deterministic routine of recognizable, muscle-varied compound lifts.
# Every name must resolve to a confirmed/manual media mapping (asserted at build
# time) so each plan/log row renders a real thumbnail.
ROUTINE = "GYM - Full Body - Workout A"
FROZEN_TS = "2026-04-18 09:00:00"  # aligns with the spec's frozen client clock
# (exercise, sets, min_rep, max_rep, rir, weight)
PLAN: tuple[tuple[str, int, int, int, int, float], ...] = (
    ("Barbell Bench Press", 3, 8, 12, 2, 60.0),
    ("Barbell Bent Over Row", 3, 8, 12, 2, 70.0),
    ("Barbell Squat", 3, 6, 10, 2, 100.0),
    ("Barbell Deadlift", 3, 5, 8, 2, 120.0),
    ("Barbell Curl", 3, 10, 15, 1, 30.0),
    ("Barbell Seated Military Press", 3, 8, 12, 2, 40.0),
)
# Rows with logged (scored) performance — the rest stay planned-only so the log
# page shows a realistic mix of scored and un-scored entries.
SCORED_COUNT = 3


def _add_media_column(con: sqlite3.Connection) -> None:
    cols = {row[1] for row in con.execute("PRAGMA table_info(exercises)")}
    if "media_path" not in cols:
        con.execute("ALTER TABLE exercises ADD COLUMN media_path TEXT")


def _apply_media_mapping(con: sqlite3.Connection) -> int:
    """Populate exercises.media_path from the reviewed mapping CSV.

    Reuses the production apply script's CSV parse (shape validation + dedup)
    and the on-disk asset check, but applies only mappings whose exercise is
    present in *this* seed's catalog. The mapping CSV is curated against the
    fuller production catalog, so it legitimately references exercises this
    smaller seed does not contain; the strict all-or-nothing apply script would
    abort on those. Filtering here keeps the seed media production-faithful for
    the subset it actually holds.
    """
    from scripts.apply_free_exercise_db_mapping import DEFAULT_CSV, DEFAULT_VENDOR_BASE, parse_csv
    from utils.media_path import media_path_resolves

    rows, errors = parse_csv(DEFAULT_CSV)
    if errors:
        raise SystemExit(
            "media mapping CSV failed shape validation:\n  " + "\n  ".join(errors)
        )

    catalog = {
        row[0].lower()
        for row in con.execute("SELECT exercise_name FROM exercises")
    }
    applied = 0
    for row in rows:
        if not row.applies or row.exercise_name.lower() not in catalog:
            continue
        if not media_path_resolves(row.suggested_image_path, DEFAULT_VENDOR_BASE):
            raise SystemExit(
                f"asset missing for {row.exercise_name!r}: {row.suggested_image_path}"
            )
        con.execute(
            "UPDATE exercises SET media_path = ? WHERE exercise_name = ? COLLATE NOCASE",
            (row.suggested_image_path, row.exercise_name),
        )
        applied += 1
    return applied


def _insert_plan_and_logs(con: sqlite3.Connection) -> None:
    con.execute("DELETE FROM user_selection")
    con.execute("DELETE FROM workout_log")

    for order, (exercise, sets, lo, hi, rir, weight) in enumerate(PLAN, start=1):
        media = con.execute(
            "SELECT media_path FROM exercises WHERE exercise_name = ? COLLATE NOCASE",
            (exercise,),
        ).fetchone()
        if not media or not media[0]:
            raise SystemExit(
                f"plan exercise {exercise!r} has no media_path after mapping — "
                "pick a confirmed/manual mapped exercise"
            )
        cur = con.execute(
            """
            INSERT INTO user_selection
                (routine, exercise, sets, min_rep_range, max_rep_range, rir,
                 weight, execution_style, exercise_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'standard', ?)
            """,
            (ROUTINE, exercise, sets, lo, hi, rir, weight, order),
        )
        plan_id = cur.lastrowid
        scored = order <= SCORED_COUNT
        con.execute(
            """
            INSERT INTO workout_log
                (workout_plan_id, routine, exercise, planned_sets,
                 planned_min_reps, planned_max_reps, planned_rir, planned_weight,
                 scored_weight, scored_min_reps, scored_max_reps, scored_rir,
                 created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id, ROUTINE, exercise, sets, lo, hi, rir, weight,
                weight if scored else None,
                10 if scored else None,
                10 if scored else None,
                1 if scored else None,
                FROZEN_TS,
            ),
        )


def build(output: Path) -> None:
    if not FIXTURE.exists():
        raise SystemExit(f"catalog source not found: {FIXTURE}")

    tmpdir = Path(tempfile.mkdtemp(prefix="visual_seed_"))
    build_db = tmpdir / "build.db"
    shutil.copy(FIXTURE, build_db)

    con = sqlite3.connect(str(build_db))
    try:
        _add_media_column(con)
        applied = _apply_media_mapping(con)
        _insert_plan_and_logs(con)
        con.commit()
        plan_n = con.execute("SELECT COUNT(*) FROM user_selection").fetchone()[0]
        log_n = con.execute("SELECT COUNT(*) FROM workout_log").fetchone()[0]
    finally:
        con.close()

    for sidecar in (output, Path(f"{output}-wal"), Path(f"{output}-shm")):
        sidecar.unlink(missing_ok=True)
    shutil.move(str(build_db), str(output))
    shutil.rmtree(tmpdir, ignore_errors=True)
    print(
        f"{output}: media_path applied to {applied} exercises, "
        f"{plan_n} plan rows, {log_n} log rows"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=FIXTURE)
    args = parser.parse_args()
    build(args.output.resolve())


if __name__ == "__main__":
    main()
