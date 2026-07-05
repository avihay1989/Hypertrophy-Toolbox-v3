"""Dry-run for Fatigue Meter Phase 2 §10 #5 movement_pattern cleanup.

Targets exercises with NULL/blank movement_pattern and reports what
classify_exercise + 'unassigned' sentinel fallback would assign. Read-only.
"""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.movement_patterns import classify_exercise


SENTINEL = 'unassigned'
STAGE1_MUSCLE_SENTINEL = 'Unassigned'


def infer(name: str, primary_muscle: str | None, mechanic: str | None) -> str:
    muscle_for_inf = None if (primary_muscle == STAGE1_MUSCLE_SENTINEL or not primary_muscle) else primary_muscle
    pattern, _ = classify_exercise(name, muscle_for_inf, mechanic)
    if pattern is None:
        return SENTINEL
    return pattern.value


def main() -> None:
    conn = sqlite3.connect('data/database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """SELECT exercise_name, primary_muscle_group, mechanic FROM exercises
           WHERE movement_pattern IS NULL OR TRIM(movement_pattern) = ''"""
    )
    rows = cur.fetchall()

    assignments: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for r in rows:
        target = infer(r['exercise_name'], r['primary_muscle_group'], r['mechanic'])
        assignments[target] += 1
        samples.setdefault(target, []).append(r['exercise_name'])

    print(f'-- Dry-run cleanup: {len(rows)} rows targeted --')
    header = f'{"target":25s} {"count":>6s}  examples'
    print(header)
    print('-' * 80)
    for target, n in assignments.most_common():
        ex = ', '.join(samples[target][:2])
        print(f'{target:25s} {n:>6d}  {ex}')
    print('-' * 80)
    print(f'Total: {sum(assignments.values())}')


if __name__ == '__main__':
    main()
