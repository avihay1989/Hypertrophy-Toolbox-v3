"""Durable golden fixtures for the fatigue protected calculation zone (WP2.4).

These goldens pin the EXACT current output of the load-bearing PUBLIC calculations in
``utils/fatigue.py`` so the WP2.4 package split (moving the four banner-delimited concerns
into ``utils/_fatigue/`` while ``utils/fatigue.py`` stays a re-export facade) is guarded by an
equality test rather than a hand-checked PR diff. Every target function is a PURE function
(no DB, no Flask), so the golden is built by calling them directly with deterministic seeded
inputs — ``compute_period_window`` is always given an explicit ``today`` so the window math never
depends on the wall clock.

Regenerate intentionally (only when a behavior change is authorized and product-risk reviewed)::

    GENERATE_GOLDEN=1 .venv/Scripts/python.exe -m pytest tests/test_fatigue_golden.py -q

Coverage is deliberately broad (see the WP2.4 product-risk review). It straddles EVERY band /
bucket boundary and locks the sort tie-break chain, so a genuine calc or tie-break change fails
here even though the mechanical Phase B move keeps ``tests/test_fatigue.py`` green:

* ``calculate_set_fatigue`` across all pattern weights (incl. None / empty / unknown / trimmed),
  every load-multiplier bucket boundary (incl. the ``>0`` rep guards coercing 0/negative to None),
  and every RIR bucket (incl. None / negative).
* ``aggregate_session_fatigue`` / ``aggregate_weekly_fatigue`` incl. ``_coerce_sets`` float / numeric
  string / invalid coercion, no-dedup duplicates, and the alias-key precedence where a
  present-but-None ``min_reps`` wins over a present ``min_rep_range``.
* ``classify_session_fatigue`` / ``classify_weekly_fatigue`` at and just below every band boundary.
* ``canonicalize_muscle_for_fatigue`` alias / Unassigned-stays-own-bucket / unknown-passthrough /
  null-empty branches.
* ``aggregate_muscles_for_session`` primary/secondary/tertiary weighting, cross-exercise AND
  within-exercise self-overlap summing, alias fold, Unassigned isolation, null-primary routing.
* ``classify_muscle_fatigue`` for all 12 landmarked muscles at MEV / MAV_low (a NON-boundary) /
  MAV_high / MRV, plus the six missing-from-landmarks labels + Unassigned -> None.
* ``muscle_percent_of_mrv`` and the full ``summarize_muscle_bars`` ordering incl. the
  ``-score`` and muscle-name tie-break levels (equal %MRV unequal score; equal %MRV equal score).
* ``normalize_period`` / ``compute_period_window`` (Sat / Mon / Sun anchors, last_4_weeks,
  this_session with mixed / empty / all-unparseable dates) / ``filter_rows_by_date_window``
  (inclusive, one-sided, custom date_field, null drops) / ``adapt_logged_row`` (incl. the
  scored_weight-only gate) / ``aggregate_logged_muscles`` / ``compute_sfr``.
* The literal ``PERIOD_LABELS`` / ``VALID_PERIODS`` user-facing vocab, so a copy-drift in the move
  is caught directly, not only via behavior.
"""
from __future__ import annotations

import dataclasses
import json
import os
from datetime import date
from pathlib import Path

from utils.fatigue import (
    MUSCLE_VOLUME_LANDMARKS,
    PATTERN_WEIGHTS,
    PERIOD_LABELS,
    VALID_PERIODS,
    SessionFatigueResult,
    adapt_logged_row,
    aggregate_logged_muscles,
    aggregate_muscles_for_session,
    aggregate_session_fatigue,
    aggregate_weekly_fatigue,
    calculate_set_fatigue,
    canonicalize_muscle_for_fatigue,
    classify_muscle_fatigue,
    classify_session_fatigue,
    classify_weekly_fatigue,
    compute_period_window,
    compute_sfr,
    filter_rows_by_date_window,
    muscle_percent_of_mrv,
    normalize_period,
    summarize_muscle_bars,
)

GOLDEN_PATH = Path(__file__).parent / "goldens" / "fatigue_golden.json"


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def _ser(obj):
    """Serialize to the JSON value space (dataclasses -> dict, dates -> iso, tuples -> list)."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _ser(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {(_key(k)): _ser(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_ser(v) for v in obj]
    return obj


def _key(key):
    if key is None:
        return "null"
    if isinstance(key, bool):
        return "true" if key else "false"
    if isinstance(key, str):
        return key
    return str(key)


# ---------------------------------------------------------------------------
# Scenario collection
# ---------------------------------------------------------------------------
def _collect_set_fatigue() -> dict:
    out: dict = {}

    # Every pattern weight (fixed min=8,max=12,rir=2) + None / empty / whitespace / unknown / trim.
    by_pattern = {}
    pattern_inputs = list(PATTERN_WEIGHTS.keys()) + [
        "__none__", "__empty__", "__ws__", "not_a_pattern", "  HORIZONTAL_PUSH  ",
    ]
    for label in pattern_inputs:
        if label == "__none__":
            arg = None
        elif label == "__empty__":
            arg = ""
        elif label == "__ws__":
            arg = "   "
        else:
            arg = label
        by_pattern[label] = calculate_set_fatigue(arg, 8, 12, 2)
    out["by_pattern"] = by_pattern

    # Every load-multiplier bucket boundary via rep-range avg (fixed pattern upper_isolation, rir=5).
    by_load = {}
    load_cases = {
        "avg3_le5": (1, 5),
        "avg5_boundary": (4, 6),
        "avg8_le10": (6, 10),
        "avg10_boundary": (10, 10),
        "avg13_le15": (11, 15),
        "avg15_boundary": (14, 16),
        "avg18_le20": (16, 20),
        "avg20_boundary": (18, 22),
        "avg25_gt20": (21, 30),
        "hi_only": (None, 8),
        "lo_only": (12, None),
        "both_none": (None, None),
        "min_zero_coerced_none": (0, 10),
        "min_negative_coerced_none": (-3, 10),
        "max_zero_coerced_none": (10, 0),
    }
    for name, (lo, hi) in load_cases.items():
        by_load[name] = calculate_set_fatigue("upper_isolation", lo, hi, 5)
    out["by_load"] = by_load

    # Every RIR bucket (fixed pattern upper_isolation, min=8,max=12).
    by_rir = {}
    for rir in (0, 1, 2, 3, 4, 5, 10, "__none__", -1):
        arg = None if rir == "__none__" else rir
        by_rir[str(rir)] = calculate_set_fatigue("upper_isolation", 8, 12, arg)
    out["by_rir"] = by_rir

    return out


def _collect_session() -> dict:
    out: dict = {}

    out["empty"] = aggregate_session_fatigue([])
    out["single_alias_keys"] = aggregate_session_fatigue([
        {"sets": 3, "movement_pattern": "vertical_push",
         "min_rep_range": 8, "max_rep_range": 12, "rir": 2}
    ])
    out["two_exercises"] = aggregate_session_fatigue([
        {"sets": 3, "movement_pattern": "vertical_push",
         "min_reps": 8, "max_reps": 12, "rir": 2},
        {"sets": 2, "movement_pattern": "upper_isolation",
         "min_reps": 12, "max_reps": 15, "rir": 5},
    ])
    dup = {"sets": 3, "movement_pattern": "upper_isolation",
           "min_reps": 12, "max_reps": 15, "rir": 5}
    out["duplicate_not_deduped"] = aggregate_session_fatigue([dup, dup])

    # _coerce_sets coercion matrix (each a one-row aggregate).
    coerce = {}
    for name, sets in {
        "zero": 0, "negative": -2, "none": None, "not_a_number": "not-a-number",
        "numeric_string": "3", "float_truncates": 2.9,
    }.items():
        coerce[name] = aggregate_session_fatigue([
            {"sets": sets, "movement_pattern": "hinge",
             "min_reps": 1, "max_reps": 5, "rir": 0}
        ])
    out["coerce_sets"] = coerce

    # Alias precedence: present-but-None min_reps must win over a present min_rep_range (-> default).
    out["alias_present_none_wins"] = aggregate_session_fatigue([
        {"sets": 2, "movement_pattern": "upper_isolation",
         "min_reps": None, "max_reps": None,
         "min_rep_range": 8, "max_rep_range": 12, "rir": 2}
    ])

    # Worked example: 6x vertical_push -> ~32.18 moderate.
    out["worked_example"] = aggregate_session_fatigue([
        {"sets": 3, "movement_pattern": "vertical_push",
         "min_reps": 8, "max_reps": 12, "rir": 2}
        for _ in range(6)
    ])
    return out


def _collect_weekly() -> dict:
    out: dict = {}
    out["empty"] = aggregate_weekly_fatigue([])
    sessions = [
        SessionFatigueResult(score=32.18, band="moderate", exercise_count=6, set_count=18),
        SessionFatigueResult(score=12.0, band="light", exercise_count=4, set_count=12),
    ]
    out["two_sessions_sum"] = aggregate_weekly_fatigue(sessions)
    boundary = [
        SessionFatigueResult(score=79.0, band="heavy", exercise_count=5, set_count=15),
        SessionFatigueResult(score=81.0, band="very_heavy", exercise_count=5, set_count=15),
    ]
    out["boundary_160"] = aggregate_weekly_fatigue(boundary)
    return out


def _collect_classify() -> dict:
    session_scores = [0, 19.99, 20.0, 35.0, 49.99, 50.0, 65.0, 79.99, 80.0, 100.0]
    weekly_scores = [0, 79.99, 80.0, 150.0, 199.99, 200.0, 260.0, 319.99, 320.0, 400.0]
    return {
        "session": {str(s): classify_session_fatigue(s) for s in session_scores},
        "weekly": {str(s): classify_weekly_fatigue(s) for s in weekly_scores},
    }


def _collect_canonicalize() -> dict:
    labels = [
        "Chest", "Gluteus Maximus", "Latissimus Dorsi", "Rectus Abdominis",
        "External Obliques", "Abs/Core", "Trapezius", "Upper Traps", "Upper Back",
        "Back", "Shoulders", "Front-Shoulder", "Rear-Shoulder", "Middle-Shoulder",
        "Unassigned", "Hypothetical-Future-Muscle",
        "__none__", "__empty__", "__ws__",
    ]
    out = {}
    for label in labels:
        if label == "__none__":
            arg = None
        elif label == "__empty__":
            arg = ""
        elif label == "__ws__":
            arg = "   "
        else:
            arg = label
        out[label] = canonicalize_muscle_for_fatigue(arg)
    return out


def _collect_muscles_session() -> dict:
    out: dict = {}
    out["primary_only"] = aggregate_muscles_for_session([{
        "sets": 3, "movement_pattern": "horizontal_push",
        "min_reps": 8, "max_reps": 12, "rir": 2,
        "primary_muscle_group": "Chest",
        "secondary_muscle_group": None, "tertiary_muscle_group": None,
    }])
    out["pst_weighting"] = aggregate_muscles_for_session([{
        "sets": 2, "movement_pattern": "vertical_push",
        "min_reps": 6, "max_reps": 8, "rir": 0,
        "primary_muscle_group": "Middle-Shoulder",
        "secondary_muscle_group": "Triceps", "tertiary_muscle_group": "Chest",
    }])
    out["cross_exercise_overlap"] = aggregate_muscles_for_session([
        {"sets": 3, "movement_pattern": "horizontal_push",
         "min_reps": 8, "max_reps": 12, "rir": 2, "primary_muscle_group": "Chest"},
        {"sets": 2, "movement_pattern": "upper_isolation",
         "min_reps": 12, "max_reps": 15, "rir": 1,
         "primary_muscle_group": "Triceps", "secondary_muscle_group": "Chest"},
    ])
    # Within-exercise self-overlap: same muscle primary + secondary -> 1.0 + 0.5 into one bucket.
    out["within_exercise_self_overlap"] = aggregate_muscles_for_session([{
        "sets": 2, "movement_pattern": "horizontal_push",
        "min_reps": 8, "max_reps": 12, "rir": 2,
        "primary_muscle_group": "Chest", "secondary_muscle_group": "Chest",
    }])
    out["alias_fold"] = aggregate_muscles_for_session([
        {"sets": 2, "movement_pattern": "lower_isolation",
         "min_reps": 8, "max_reps": 10, "rir": 2, "primary_muscle_group": "Gluteus Maximus"},
        {"sets": 2, "movement_pattern": "lower_isolation",
         "min_reps": 8, "max_reps": 10, "rir": 2, "primary_muscle_group": "Glutes"},
    ])
    out["zero_sets_skipped"] = aggregate_muscles_for_session([{
        "sets": 0, "movement_pattern": "horizontal_push",
        "min_reps": 8, "max_reps": 12, "rir": 2, "primary_muscle_group": "Chest",
    }])
    out["null_secondary_tertiary"] = aggregate_muscles_for_session([{
        "sets": 1, "movement_pattern": "upper_isolation",
        "min_reps": 10, "max_reps": 10, "rir": 2,
        "primary_muscle_group": "Biceps",
        "secondary_muscle_group": None, "tertiary_muscle_group": "",
    }])
    out["unassigned_primary"] = aggregate_muscles_for_session([{
        "sets": 3, "movement_pattern": "core_static",
        "min_reps": 10, "max_reps": 10, "rir": 3, "primary_muscle_group": "Unassigned",
    }])
    out["null_primary_routes_unassigned"] = aggregate_muscles_for_session([{
        "sets": 1, "movement_pattern": "upper_isolation",
        "min_reps": 10, "max_reps": 10, "rir": 2, "primary_muscle_group": None,
    }])
    out["unassigned_and_abdominals_separate"] = aggregate_muscles_for_session([
        {"sets": 3, "movement_pattern": "core_static",
         "min_reps": 10, "max_reps": 10, "rir": 3, "primary_muscle_group": "Unassigned"},
        {"sets": 3, "movement_pattern": "core_static",
         "min_reps": 10, "max_reps": 10, "rir": 3, "primary_muscle_group": "Rectus Abdominis"},
    ])
    out["empty"] = aggregate_muscles_for_session([])
    return out


def _collect_classify_muscle() -> dict:
    out: dict = {}
    for muscle, (mev, mav_low, mav_high, mrv) in MUSCLE_VOLUME_LANDMARKS.items():
        out[muscle] = {
            "below_mev_0": classify_muscle_fatigue(muscle, 0.0),
            "at_mev": classify_muscle_fatigue(muscle, mev),
            "at_mav_low_nonboundary": classify_muscle_fatigue(muscle, mav_low),
            "at_mav_high": classify_muscle_fatigue(muscle, mav_high),
            "at_mrv": classify_muscle_fatigue(muscle, mrv),
            "above_mrv": classify_muscle_fatigue(muscle, mrv + 1),
        }
    for muscle in ("Front-Shoulder", "Rear-Shoulder", "Lower Back",
                   "Hip-Adductors", "Middle-Traps", "Neck", "Unassigned"):
        out[muscle] = {"any": classify_muscle_fatigue(muscle, 50.0)}
    return out


def _collect_percent_of_mrv() -> dict:
    return {
        "chest_50": muscle_percent_of_mrv("Chest", 11.0),
        "chest_150": muscle_percent_of_mrv("Chest", 33.0),
        "unassigned_none": muscle_percent_of_mrv("Unassigned", 50.0),
        "lower_back_none": muscle_percent_of_mrv("Lower Back", 50.0),
    }


def _collect_summarize_bars() -> dict:
    out: dict = {}
    out["landmarked_by_percent_desc"] = summarize_muscle_bars(
        {"Biceps": 6.5, "Chest": 11.0, "Triceps": 9.0}
    )
    out["unassigned_to_bottom"] = summarize_muscle_bars({
        "Chest": 5.0, "Unassigned": 9999.0, "Lower Back": 9999.0, "Biceps": 13.0,
    })
    # Equal %MRV (Chest 11/22=50%, Triceps 9/18=50%), unequal score -> -score tiebreak.
    out["equal_percent_unequal_score"] = summarize_muscle_bars(
        {"Triceps": 9.0, "Chest": 11.0}
    )
    # Equal %MRV AND equal score (Chest & Calves both MRV 22, score 11) -> muscle name asc.
    out["equal_percent_equal_score_name_asc"] = summarize_muscle_bars(
        {"Chest": 11.0, "Calves": 11.0}
    )
    out["empty"] = summarize_muscle_bars({})
    return out


def _collect_period() -> dict:
    out: dict = {}
    out["valid_periods"] = list(VALID_PERIODS)
    out["period_labels"] = dict(PERIOD_LABELS)

    normalize = {}
    for value in list(VALID_PERIODS) + [
        "__none__", "__empty__", "garbage", "1month", "WEEK", "  THIS_WEEK  ",
    ]:
        if value == "__none__":
            arg = None
        elif value == "__empty__":
            arg = ""
        else:
            arg = value
        normalize[value] = normalize_period(arg)
    out["normalize"] = normalize

    windows = {}
    windows["this_week_saturday"] = compute_period_window("this_week", date(2026, 5, 23))
    windows["this_week_monday"] = compute_period_window("this_week", date(2026, 5, 18))
    windows["this_week_sunday"] = compute_period_window("this_week", date(2026, 5, 24))
    windows["last_4_weeks"] = compute_period_window("last_4_weeks", date(2026, 5, 23))
    windows["this_session_mixed"] = compute_period_window(
        "this_session", date(2026, 5, 23),
        ["2026-05-20 09:00:00", "2026-05-22 18:30:00", "2026-05-18"],
    )
    windows["this_session_empty"] = compute_period_window("this_session", date(2026, 5, 23), [])
    windows["this_session_none"] = compute_period_window("this_session", date(2026, 5, 23), None)
    windows["this_session_all_unparseable"] = compute_period_window(
        "this_session", date(2026, 5, 23), ["garbage", None, ""],
    )
    windows["unknown_falls_back"] = compute_period_window("garbage", date(2026, 5, 23))
    out["windows"] = windows
    return out


def _collect_filter_rows() -> dict:
    out: dict = {}
    rows = [
        {"created_at": "2026-05-17", "id": 1},
        {"created_at": "2026-05-18", "id": 2},
        {"created_at": "2026-05-24", "id": 3},
        {"created_at": "2026-05-25", "id": 4},
    ]
    out["inclusive"] = filter_rows_by_date_window(rows, date(2026, 5, 18), date(2026, 5, 24))
    out["start_only"] = filter_rows_by_date_window(rows, date(2026, 5, 24), None)
    out["end_only"] = filter_rows_by_date_window(rows, None, date(2026, 5, 18))
    null_rows = [
        {"created_at": None}, {"created_at": "garbage"}, {"created_at": "2026-05-20 12:00:00"},
    ]
    out["null_dates_dropped"] = filter_rows_by_date_window(
        null_rows, date(2026, 5, 18), date(2026, 5, 24)
    )
    out["both_none_empty"] = filter_rows_by_date_window([{"created_at": "2026-05-20"}], None, None)
    custom = [{"logged_on": "2026-05-20", "id": 9}, {"logged_on": "2026-06-01", "id": 10}]
    out["custom_date_field"] = filter_rows_by_date_window(
        custom, date(2026, 5, 1), date(2026, 5, 31), date_field="logged_on"
    )
    return out


def _collect_adapt_logged() -> dict:
    base = {
        "planned_sets": 3,
        "planned_min_reps": 6, "planned_max_reps": 8, "planned_rir": 3,
        "scored_min_reps": 7, "scored_max_reps": 8, "scored_rir": 2,
        "scored_weight": 100.0,
        "movement_pattern": "horizontal_push",
        "primary_muscle_group": "Chest",
        "secondary_muscle_group": "Triceps",
        "tertiary_muscle_group": "Front-Shoulder",
    }
    out: dict = {}
    out["scored_precedence"] = adapt_logged_row(dict(base))
    out["fallback_to_planned"] = adapt_logged_row({
        **base, "scored_rir": None, "scored_min_reps": None, "scored_max_reps": None,
        "scored_weight": 100.0,
    })
    out["all_scored_null_skipped"] = adapt_logged_row({
        **base, "scored_rir": None, "scored_min_reps": None,
        "scored_max_reps": None, "scored_weight": None,
    })
    # Only scored_weight non-null -> row still counts as logged (sets == planned_sets).
    out["only_scored_weight_counts"] = adapt_logged_row({
        **base, "scored_rir": None, "scored_min_reps": None,
        "scored_max_reps": None, "scored_weight": 80.0,
    })
    return out


def _collect_logged_muscles() -> dict:
    out: dict = {}
    out["logged_rows_aggregate"] = aggregate_logged_muscles([{
        "planned_sets": 3, "scored_rir": 2, "scored_min_reps": 8, "scored_max_reps": 12,
        "scored_weight": 100.0, "movement_pattern": "horizontal_push",
        "primary_muscle_group": "Chest",
    }])
    out["skipped_row_zero"] = aggregate_logged_muscles([{
        "planned_sets": 3, "planned_rir": 2, "planned_min_reps": 8, "planned_max_reps": 12,
        "scored_rir": None, "scored_min_reps": None, "scored_max_reps": None,
        "scored_weight": None, "movement_pattern": "horizontal_push",
        "primary_muscle_group": "Chest",
    }])
    out["empty"] = aggregate_logged_muscles([])
    out["unassigned_stays_separate"] = aggregate_logged_muscles([{
        "planned_sets": 2, "scored_rir": 2, "scored_min_reps": 10, "scored_max_reps": 10,
        "scored_weight": 0.0, "movement_pattern": "core_static",
        "primary_muscle_group": "Unassigned",
    }])
    return out


def _collect_sfr() -> dict:
    return {
        "both_positive": compute_sfr(10.0, 5.0),
        "fatigue_zero": compute_sfr(10.0, 0.0),
        "fatigue_none": compute_sfr(10.0, None),
        "stimulus_zero": compute_sfr(0.0, 5.0),
        "stimulus_none": compute_sfr(None, 5.0),
        "negative_fatigue": compute_sfr(10.0, -1.0),
        "negative_stimulus": compute_sfr(-4.0, 5.0),
    }


def _collect() -> dict:
    return {
        "set_fatigue": _collect_set_fatigue(),
        "session": _collect_session(),
        "weekly": _collect_weekly(),
        "classify": _collect_classify(),
        "canonicalize": _collect_canonicalize(),
        "muscles_session": _collect_muscles_session(),
        "classify_muscle": _collect_classify_muscle(),
        "percent_of_mrv": _collect_percent_of_mrv(),
        "summarize_bars": _collect_summarize_bars(),
        "period": _collect_period(),
        "filter_rows": _collect_filter_rows(),
        "adapt_logged": _collect_adapt_logged(),
        "logged_muscles": _collect_logged_muscles(),
        "sfr": _collect_sfr(),
    }


# ---------------------------------------------------------------------------
# The golden test
# ---------------------------------------------------------------------------
def test_fatigue_golden():
    """Fatigue pure-calc output must match the checked-in golden exactly.

    This is the WP2.4 guard: any drift in the protected fatigue calc zone (multipliers, bands,
    landmarks, %MRV, period-window date math, sort tie-break order, labels) fails here. Do not
    regenerate the golden to make a drift pass without an authorized, product-risk-reviewed
    behavior change.
    """
    fresh = _ser(_collect())

    if os.environ.get("GENERATE_GOLDEN") == "1":
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(
            json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        import pytest

        pytest.skip("Regenerated golden fixture (GENERATE_GOLDEN=1).")

    assert GOLDEN_PATH.exists(), (
        f"Missing golden fixture {GOLDEN_PATH}. Regenerate with GENERATE_GOLDEN=1."
    )
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert fresh == expected
