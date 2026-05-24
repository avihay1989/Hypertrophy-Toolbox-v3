"""Apply the Fatigue Meter Phase 2 §10 #5 movement_pattern cleanup.

Per Stage 1's hybrid pattern — fill the NULL/blank movement_pattern rows in
the exercises table using name-keyword inference (via
utils.movement_patterns.classify_exercise, which does longest-keyword-first
name matching with primary_muscle_group as a secondary fallback), falling
back to the 'unassigned' sentinel when neither name nor muscle resolves.

Rows whose primary_muscle_group is the Stage 1 'Unassigned' sentinel are
treated as having no muscle hint for fallback purposes, so muscle-based
inference does not propagate the Stage 1 sentinel into bogus patterns.

Idempotent: a second run touches zero rows because all NULL/blank rows are
filled.

This script is intentionally isolated (no Flask, no DatabaseHandler) so it
can be re-run against any DB snapshot for verification.
"""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.config import DB_FILE
from utils.movement_patterns import classify_exercise


SENTINEL = 'unassigned'
STAGE1_MUSCLE_SENTINEL = 'Unassigned'


def infer_movement_pattern(name: str, primary_muscle: str | None, mechanic: str | None) -> str:
    muscle_for_inf = None if (primary_muscle == STAGE1_MUSCLE_SENTINEL or not primary_muscle) else primary_muscle
    pattern, _sub = classify_exercise(name, muscle_for_inf, mechanic)
    if pattern is None:
        return SENTINEL
    return pattern.value


def main() -> int:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT exercise_name, primary_muscle_group, mechanic FROM exercises
               WHERE movement_pattern IS NULL OR TRIM(movement_pattern) = ''"""
        )
        targets = cur.fetchall()
        if not targets:
            print('No NULL/blank movement_pattern rows. Nothing to do.')
            return 0

        assignments = Counter()
        updates = []
        for r in targets:
            target = infer_movement_pattern(r['exercise_name'], r['primary_muscle_group'], r['mechanic'])
            assignments[target] += 1
            updates.append((target, r['exercise_name']))

        cur.executemany(
            'UPDATE exercises SET movement_pattern = ? WHERE exercise_name = ?',
            updates,
        )
        conn.commit()

        print(f'-- Applied cleanup: {len(updates)} rows updated --')
        for target, n in assignments.most_common():
            print(f'  {target:25s} {n}')

        cur.execute(
            """SELECT COUNT(*) FROM exercises
               WHERE movement_pattern IS NULL OR TRIM(movement_pattern) = ''"""
        )
        remaining = cur.fetchone()[0]
        print(f'-- Post-cleanup NULL/blank count: {remaining} --')
        return 0 if remaining == 0 else 1
    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
