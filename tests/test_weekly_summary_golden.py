"""Durable golden fixtures for the weekly-summary protected calculation zone (WP2.3).

These goldens pin the EXACT current output of the load-bearing public calculations in
``utils/weekly_summary.py`` so the WP2.3 in-module helper extraction (and any future touch
to this protected calc zone) is guarded by an equality test rather than a hand-checked PR
diff. The golden is generated from current behavior and checked into
``tests/goldens/weekly_summary_golden.json``.

Regenerate intentionally (only when a behavior change is authorized and reviewed) with::

    GENERATE_GOLDEN=1 .venv/Scripts/python.exe -m pytest \
        tests/test_weekly_summary_golden.py -q

Coverage is deliberately broad (see the product-risk review for WP2.3):

* Effective-vs-Raw side-by-side shape across the full ``counting_mode`` x
  ``contribution_mode`` matrix.
* Muscle contribution weighting (primary 1.0 / secondary 0.5 / tertiary 0.25).
* Frequency's ``>= 1.0`` threshold locked ABOVE and BELOW, where the per-routine total
  accumulates across multiple exercises BEFORE the threshold test (M5).
* Falsy-routine ("null routine") behavior (OD4, DEFERRED): a muscle sourced only from a
  falsy routine contributes volume but drops out of frequency / session counts (M2). The
  schema is ``routine TEXT NOT NULL``, so the reachable falsy case is the empty string
  ``''`` — exactly what ``if routine:`` and pattern coverage's ``.get('routine', ...)``
  branch on. This golden LOCKS that drop-from-frequency behavior; it must NOT be "fixed"
  into a WPB.4 ``Unassigned`` bucket here.
* DIRECT_ONLY is per-contribution, not per-muscle: a muscle that is secondary in one
  exercise and primary in another is credited only via its primary instance (S3).
* Pattern coverage: the empty-pattern ``_infer_pattern`` fallback branches (M3), and the
  global warning verdicts — push-dominant / pull-dominant / balanced / isolation-skew and
  the strict 15/24 volume boundaries — each locked in their own reseeded DB state (M4/S1/S2),
  because pattern coverage takes no mode toggles and a warning is one verdict per DB state.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from utils.effective_sets import CountingMode, ContributionMode
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
    calculate_pattern_coverage,
    calculate_weekly_summary,
)

GOLDEN_PATH = Path(__file__).parent / "goldens" / "weekly_summary_golden.json"


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------
def _reset(db) -> None:
    """Wipe the tables the summary calcs read, in FK-safe order."""
    for table in ("workout_log", "user_selection", "exercise_isolated_muscles", "exercises"):
        db.execute_query(f"DELETE FROM {table}")


def _add_ex(
    db,
    name,
    primary=None,
    secondary=None,
    tertiary=None,
    mechanic=None,
    utility=None,
    force=None,
    difficulty=None,
    pattern=None,
    subpattern=None,
) -> None:
    db.execute_query(
        """
        INSERT INTO exercises (
            exercise_name, primary_muscle_group, secondary_muscle_group,
            tertiary_muscle_group, mechanic, utility, force, difficulty,
            movement_pattern, movement_subpattern
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, primary, secondary, tertiary, mechanic, utility, force, difficulty, pattern, subpattern),
    )


def _add_sel(db, routine, exercise, sets, min_rep, max_rep, rir, weight) -> None:
    db.execute_query(
        """
        INSERT INTO user_selection (
            routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        (routine, exercise, sets, min_rep, max_rep, rir, weight),
    )


def _add_iso(db, exercise, muscle) -> None:
    db.execute_query(
        "INSERT INTO exercise_isolated_muscles (exercise_name, muscle) VALUES (?, ?)",
        (exercise, muscle),
    )


# ---------------------------------------------------------------------------
# Scenario seeds
# ---------------------------------------------------------------------------
def _seed_weekly_main(db) -> None:
    """Rich seed exercising weekly-summary across every load-bearing branch."""
    _add_ex(db, "Bench Press", "Chest", "Triceps", "Front-Shoulder", "Compound", "Basic", "Push", "Intermediate", "horizontal_push")
    _add_ex(db, "Incline Press", "Chest", None, None, "Compound", "Basic", "Push", "Intermediate", "horizontal_push")
    _add_ex(db, "Back Squat", "Quadriceps", "Gluteus Maximus", None, "Compound", "Basic", "Push", "Intermediate", "squat")
    _add_ex(db, "Barbell Row", "Upper Back", "Biceps", None, "Compound", "Basic", "Pull", "Intermediate", "horizontal_pull")
    _add_ex(db, "Biceps Curl", "Biceps", None, None, "Isolated", "Auxiliary", "Pull", "Beginner", "upper_isolation", "bicep_curl")
    _add_ex(db, "Calf Raise", "Calves", None, None, "Isolated", "Auxiliary", "Push", "Beginner", "lower_isolation")
    _add_ex(db, "Triceps Pushdown", "Triceps", None, None, "Isolated", "Auxiliary", "Push", "Beginner", "upper_isolation")
    _add_ex(db, "Rear Delt A", "Rear-Shoulder", None, None, "Isolated", "Auxiliary", "Pull", "Beginner", "upper_isolation")
    _add_ex(db, "Rear Delt B", "Rear-Shoulder", None, None, "Isolated", "Auxiliary", "Pull", "Beginner", "upper_isolation")
    _add_ex(db, "Forearm A", "Forearms", None, None, "Isolated", "Auxiliary", "Pull", "Beginner", "upper_isolation")
    _add_ex(db, "Forearm B", "Forearms", None, None, "Isolated", "Auxiliary", "Pull", "Beginner", "upper_isolation")

    # Chest across two routines -> frequency 2. Triceps secondary here (S3).
    _add_sel(db, "Push A", "Bench Press", 10, 8, 10, 2, 80.0)
    _add_sel(db, "Push B", "Incline Press", 15, 8, 10, 2, 70.0)
    # Triceps primary here; in DIRECT_ONLY only this instance credits Triceps (S3).
    _add_sel(db, "Push A", "Triceps Pushdown", 5, 8, 10, 2, 30.0)
    _add_sel(db, "Legs A", "Back Squat", 8, 8, 10, 2, 100.0)
    _add_sel(db, "Pull A", "Barbell Row", 6, 8, 10, 2, 60.0)
    _add_sel(db, "Pull A", "Biceps Curl", 4, 8, 10, 2, 20.0)
    # Falsy (empty-string) routine: Calves sourced ONLY here -> volume but no frequency (M2/OD4).
    _add_sel(db, "", "Calf Raise", 6, 8, 10, 2, 50.0)
    # Frequency accumulation ABOVE threshold: two 0.85 contributions sum to 1.7 >= 1.0 (M5).
    _add_sel(db, "Freq A", "Rear Delt A", 1, 8, 10, 2, 10.0)
    _add_sel(db, "Freq A", "Rear Delt B", 1, 8, 10, 2, 10.0)
    # Frequency accumulation BELOW threshold: two 0.385 contributions sum to 0.77 < 1.0 (M5).
    _add_sel(db, "Freq B", "Forearm A", 1, 30, 40, 8, 10.0)
    _add_sel(db, "Freq B", "Forearm B", 1, 30, 40, 8, 10.0)

    _add_iso(db, "Bench Press", "anterior-deltoid")
    _add_iso(db, "Bench Press", "upper-pectoralis")


def _seed_pattern_infer(db) -> None:
    """Empty movement_pattern rows spanning every _infer_pattern outcome (M3)."""
    rows = [
        # (exercise, primary_muscle, mechanic, expected inference)
        ("Infer Quad", "Quadriceps", "Compound"),        # 'quad' -> squat
        ("Infer Glute", "Gluteus Maximus", "Compound"),  # 'glute' (not quad) -> hinge
        ("Infer Chest", "Chest", "Compound"),            # 'chest' -> horizontal_push
        ("Infer Lat C", "Latissimus Dorsi", "Compound"),  # 'lat' + compound -> vertical_pull
        ("Infer Lat I", "Latissimus Dorsi", "Isolated"),   # 'lat' + non-compound -> horizontal_pull
        ("Infer Back I", "Upper Back", "Isolated"),        # 'back' + non-compound -> horizontal_pull
        ("Infer Bicep", "Biceps", "Isolated"),           # 'bicep' -> upper_isolation
        ("Infer Tricep", "Triceps", "Isolated"),         # 'tricep' -> upper_isolation
        ("Infer Calf", "Calves", "Isolated"),            # 'calf' -> lower_isolation
        ("Infer Ham", "Hamstrings", "Isolated"),         # 'hamstring' -> lower_isolation
        ("Infer Core", "Abs/Core", "Isolated"),          # 'core'/'abs' -> core_dynamic
        ("Infer Other", "Neck", "Isolated"),             # no match -> other
    ]
    for name, primary, mechanic in rows:
        _add_ex(db, name, primary, mechanic=mechanic, pattern=None)
        _add_sel(db, "Infer R", name, 3, 8, 10, 2, 20.0)


def _seed_pattern_push_dominant(db) -> None:
    """push/pull ratio > 1.5 -> 'Push-dominant program' (M4)."""
    _add_ex(db, "PD Bench", "Chest", mechanic="Compound", pattern="horizontal_push")
    _add_ex(db, "PD OHP", "Front-Shoulder", mechanic="Compound", pattern="vertical_push")
    _add_ex(db, "PD Row", "Upper Back", mechanic="Compound", pattern="horizontal_pull")
    _add_sel(db, "Push R", "PD Bench", 10, 8, 10, 2, 80.0)
    _add_sel(db, "Push R", "PD OHP", 8, 8, 10, 2, 50.0)
    _add_sel(db, "Push R", "PD Row", 4, 8, 10, 2, 60.0)


def _seed_pattern_pull_dominant(db) -> None:
    """push/pull ratio < 0.67 -> 'Pull-dominant program' (M4)."""
    _add_ex(db, "PL Row", "Upper Back", mechanic="Compound", pattern="horizontal_pull")
    _add_ex(db, "PL Pulldown", "Latissimus Dorsi", mechanic="Compound", pattern="vertical_pull")
    _add_ex(db, "PL Bench", "Chest", mechanic="Compound", pattern="horizontal_push")
    _add_sel(db, "Pull R", "PL Row", 10, 8, 10, 2, 60.0)
    _add_sel(db, "Pull R", "PL Pulldown", 8, 8, 10, 2, 55.0)
    _add_sel(db, "Pull R", "PL Bench", 4, 8, 10, 2, 80.0)


def _seed_pattern_balanced(db) -> None:
    """All six core patterns present, balanced push/pull, no isolation -> zero warnings."""
    specs = [
        ("Bal Squat", "Quadriceps", "squat", 4),
        ("Bal Hinge", "Hamstrings", "hinge", 4),
        ("Bal HPush", "Chest", "horizontal_push", 4),
        ("Bal HPull", "Upper Back", "horizontal_pull", 4),
        ("Bal VPush", "Front-Shoulder", "vertical_push", 3),
        ("Bal VPull", "Latissimus Dorsi", "vertical_pull", 3),
    ]
    for name, primary, pattern, sets in specs:
        _add_ex(db, name, primary, mechanic="Compound", pattern=pattern)
        _add_sel(db, "Bal R", name, sets, 8, 10, 2, 60.0)


def _seed_pattern_isolation_skew(db) -> None:
    """isolation > 1.5 x compound -> 'High isolation-to-compound ratio' (M4)."""
    _add_ex(db, "IS Curl", "Biceps", mechanic="Isolated", pattern="upper_isolation")
    _add_ex(db, "IS LegCurl", "Hamstrings", mechanic="Isolated", pattern="lower_isolation")
    _add_ex(db, "IS Squat", "Quadriceps", mechanic="Compound", pattern="squat")
    _add_sel(db, "Iso R", "IS Curl", 20, 8, 10, 2, 20.0)
    _add_sel(db, "Iso R", "IS LegCurl", 20, 8, 10, 2, 40.0)
    _add_sel(db, "Iso R", "IS Squat", 4, 8, 10, 2, 100.0)


def _seed_pattern_volume_boundaries(db) -> None:
    """Strict 15/24 volume boundaries and >=2 volume-warning routines (S1/S2)."""
    _add_ex(db, "Vol Push", "Chest", mechanic="Compound", pattern="horizontal_push")
    # ORDER BY us.routine -> Vol 14, Vol 15, Vol 24, Vol 25.
    _add_sel(db, "Vol 14", "Vol Push", 14, 8, 10, 2, 80.0)  # < 15 -> low_volume
    _add_sel(db, "Vol 15", "Vol Push", 15, 8, 10, 2, 80.0)  # boundary -> no warning
    _add_sel(db, "Vol 24", "Vol Push", 24, 8, 10, 2, 80.0)  # boundary -> no warning
    _add_sel(db, "Vol 25", "Vol Push", 25, 8, 10, 2, 80.0)  # > 24 -> high_volume


# ---------------------------------------------------------------------------
# Output collection + canonicalization
# ---------------------------------------------------------------------------
_MODE_MATRIX = [
    ("effective_total", CountingMode.EFFECTIVE, ContributionMode.TOTAL),
    ("raw_total", CountingMode.RAW, ContributionMode.TOTAL),
    ("effective_direct", CountingMode.EFFECTIVE, ContributionMode.DIRECT_ONLY),
    ("raw_direct", CountingMode.RAW, ContributionMode.DIRECT_ONLY),
]


def _collect(db) -> dict:
    """Build the full result tree the golden pins."""
    results: dict = {}

    _reset(db)
    _seed_weekly_main(db)
    weekly = {}
    for key, counting, contribution in _MODE_MATRIX:
        weekly[key] = calculate_weekly_summary(
            counting_mode=counting, contribution_mode=contribution
        )
    results["weekly_main"] = {
        "weekly_summary": weekly,
        "pattern_coverage": calculate_pattern_coverage(),
        "exercise_categories": calculate_exercise_categories(),
        "isolated_muscles": calculate_isolated_muscles_stats(),
    }

    pattern_scenarios = [
        ("pattern_infer", _seed_pattern_infer),
        ("pattern_push_dominant", _seed_pattern_push_dominant),
        ("pattern_pull_dominant", _seed_pattern_pull_dominant),
        ("pattern_balanced", _seed_pattern_balanced),
        ("pattern_isolation_skew", _seed_pattern_isolation_skew),
        ("pattern_volume_boundaries", _seed_pattern_volume_boundaries),
    ]
    for name, seed in pattern_scenarios:
        _reset(db)
        seed(db)
        results[name] = {"pattern_coverage": calculate_pattern_coverage()}

    return results


def _canonical(obj):
    """Normalize to the JSON value space so comparison is order- and key-type stable.

    Mirrors ``json.dumps`` key coercion (e.g. an empty-string vs None routine key) and
    turns tuples into lists, so ``_canonical(fresh) == json.loads(golden)`` compares
    exactly what is persisted. round(x, 2) floats round-trip through JSON unchanged.
    """
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if key is None:
                skey = "null"
            elif isinstance(key, bool):
                skey = "true" if key else "false"
            elif isinstance(key, str):
                skey = key
            else:
                skey = str(key)
            out[skey] = _canonical(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [_canonical(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# The golden test
# ---------------------------------------------------------------------------
@pytest.mark.usefixtures("clean_db")
def test_weekly_summary_golden(db_handler):
    """Weekly-summary + pattern-coverage output must match the checked-in golden exactly.

    This is the WP2.3 guard: any drift in the protected weekly-summary calc zone (effective
    vs raw shape, frequency counts, rounding, mode toggles, warning order, falsy-routine
    behavior) fails here. Do not regenerate the golden to make a drift pass without an
    authorized, product-risk-reviewed behavior change.
    """
    fresh = _canonical(_collect(db_handler))

    if os.environ.get("GENERATE_GOLDEN") == "1":
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(
            json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        pytest.skip("Regenerated golden fixture (GENERATE_GOLDEN=1).")

    assert GOLDEN_PATH.exists(), (
        f"Missing golden fixture {GOLDEN_PATH}. Regenerate with GENERATE_GOLDEN=1."
    )
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert fresh == expected
