"""Apply the Fatigue Meter Phase 2 Stage 1 catalog cleanup.

Per locked D2.13 (hybrid) — fill the 633 NULL/blank primary_muscle_group rows
in the exercises table using name-keyword inference against the existing
muscle taxonomy (utils.constants.MUSCLE_ALIAS + MUSCLE_GROUPS), falling back
to the 'Unassigned' bucket when no muscle keyword is present in the name.

Idempotent: a second run touches zero rows because all NULL/blank rows are
filled.

This script is intentionally isolated (no Flask, no DatabaseHandler) so it
can be re-run against any DB snapshot for verification.
"""
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.config import DB_FILE
from utils.constants import MUSCLE_ALIAS, MUSCLE_GROUPS


UNASSIGNED = 'Unassigned'


def _build_lookup() -> list[tuple[str, str]]:
    lookup: dict[str, str] = {}
    for alias, canonical in MUSCLE_ALIAS.items():
        lookup[alias.lower()] = canonical
    for canonical in MUSCLE_GROUPS:
        lookup.setdefault(canonical.lower(), canonical)
    return sorted(lookup.items(), key=lambda kv: -len(kv[0]))


def infer_primary_muscle(name: str, lookup: list[tuple[str, str]]) -> str:
    n = name.lower()
    for alias, canonical in lookup:
        if re.search(r'\b' + re.escape(alias) + r'\b', n):
            return canonical
    return UNASSIGNED


def main() -> int:
    lookup = _build_lookup()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT exercise_name FROM exercises
               WHERE primary_muscle_group IS NULL OR TRIM(primary_muscle_group) = ''"""
        )
        targets = [r['exercise_name'] for r in cur.fetchall()]
        if not targets:
            print('No NULL/blank primary_muscle_group rows. Nothing to do.')
            return 0

        assignments = Counter()
        updates = []
        for name in targets:
            target = infer_primary_muscle(name, lookup)
            assignments[target] += 1
            updates.append((target, name))

        cur.executemany(
            'UPDATE exercises SET primary_muscle_group = ? WHERE exercise_name = ?',
            updates,
        )
        conn.commit()

        print(f'-- Applied cleanup: {len(updates)} rows updated --')
        for target, n in assignments.most_common():
            print(f'  {target:25s} {n}')

        cur.execute(
            """SELECT COUNT(*) FROM exercises
               WHERE primary_muscle_group IS NULL OR TRIM(primary_muscle_group) = ''"""
        )
        remaining = cur.fetchone()[0]
        print(f'-- Post-cleanup NULL/blank count: {remaining} --')
        return 0 if remaining == 0 else 1
    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
