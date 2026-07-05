"""Dry-run for Fatigue Meter Phase 2 Stage 1 catalog cleanup.

Targets exercises with NULL/blank primary_muscle_group and reports what
keyword inference + Unassigned fallback would assign. Read-only.
"""
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.constants import MUSCLE_ALIAS, MUSCLE_GROUPS


_lookup: dict[str, str] = {}
for alias, canonical in MUSCLE_ALIAS.items():
    _lookup[alias.lower()] = canonical
for canonical in MUSCLE_GROUPS:
    _lookup.setdefault(canonical.lower(), canonical)

ALIAS_LOOKUP = sorted(_lookup.items(), key=lambda kv: -len(kv[0]))


def infer(name: str) -> str:
    n = name.lower()
    for alias, canonical in ALIAS_LOOKUP:
        if re.search(r'\b' + re.escape(alias) + r'\b', n):
            return canonical
    return 'Unassigned'


def main() -> None:
    conn = sqlite3.connect('data/database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """SELECT exercise_name, equipment FROM exercises
           WHERE primary_muscle_group IS NULL OR TRIM(primary_muscle_group) = ''"""
    )
    rows = cur.fetchall()

    assignments = Counter()
    samples: dict[str, list[str]] = {}
    for r in rows:
        target = infer(r['exercise_name'])
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
