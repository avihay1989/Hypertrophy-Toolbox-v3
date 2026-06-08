"""Coverage for the Phase 2 Stage 4 calibration observer + status helper.

These two scripts are the *measurement* half of the Stage 4 calibration window
and the literal evidence pipeline that gates Learned Calibration Phase 2D-D
(see ``docs/user_profile/LEARNED_CALIBRATION_PLAN.md`` §"Phase 2D-D Gate
Review"). They shipped without pytest coverage; this file locks their
read-only / append-once / signal-bar contracts so the gate can trust the
evidence they collect.

Scope is strictly the script behavior of:
  * ``scripts/fatigue_stage4_observer.py`` — ``_direction``, ``_pending_combos``,
    ``_append_csv``, ``observe``, ``analyze``
  * ``scripts/fatigue_stage4_status.py`` — ``main`` JSON output

No fatigue thresholds / bands / landmarks, estimator priority, calibration
formulas, or product behavior are touched. DB access goes only through the
isolated tmp-path test database provided by the shared fixtures.
"""
from __future__ import annotations

import csv
import io
import json
from contextlib import redirect_stdout

from scripts.fatigue_stage4_observer import (
    CSV_FIELDS,
    _append_csv,
    _direction,
    _pending_combos,
    analyze,
    observe,
)
from scripts.fatigue_stage4_status import main as status_main


def _write_csv(path, rows):
    """Write a calibration-log CSV with the canonical header + given rows."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def _row(muscle, engine_band, felt_band="", *, period="this_week", side="logged"):
    return {
        "run_date": "2026-06-09",
        "period": period,
        "muscle": muscle,
        "side": side,
        "engine_band": engine_band,
        "percent_of_mrv": "",
        "score": "0.00",
        "felt_band": felt_band,
        "note": "",
    }


def _silently(fn, *args, **kwargs):
    """Run a chatty observer fn, swallow its stdout, return its value."""
    with redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestDirection:
    """Engine-vs-felt direction math underpinning the signal/noise tally."""

    def test_engine_higher_band_is_engine_high(self):
        assert _direction("heavy", "light") == "engine_high"

    def test_engine_lower_band_is_engine_low(self):
        assert _direction("light", "heavy") == "engine_low"

    def test_equal_bands_agree(self):
        assert _direction("moderate", "moderate") == "agree"

    def test_unknown_engine_band_returns_none(self):
        assert _direction("bogus", "light") is None

    def test_blank_felt_band_returns_none(self):
        assert _direction("light", "") is None


class TestPendingCombos:
    """`(period, muscle)` pairs awaiting a felt label — drives append dedup."""

    def test_missing_file_returns_empty_set(self, tmp_path):
        assert _pending_combos(tmp_path / "absent.csv") == set()

    def test_unfilled_rows_are_pending(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(path, [_row("Chest", "heavy"), _row("Back", "moderate")])
        assert _pending_combos(path) == {
            ("this_week", "Chest"),
            ("this_week", "Back"),
        }

    def test_filled_rows_are_not_pending(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(path, [_row("Chest", "heavy", "moderate")])
        assert _pending_combos(path) == set()

    def test_mixed_filled_and_unfilled(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(
            path,
            [_row("Chest", "heavy", "moderate"), _row("Back", "moderate")],
        )
        assert _pending_combos(path) == {("this_week", "Back")}


class TestAppendCsv:
    def test_creates_file_with_header(self, tmp_path):
        path = tmp_path / "log.csv"
        _append_csv(path, [_row("Chest", "heavy")])
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == CSV_FIELDS
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["muscle"] == "Chest"

    def test_appends_without_duplicate_header(self, tmp_path):
        path = tmp_path / "log.csv"
        _append_csv(path, [_row("Chest", "heavy")])
        _append_csv(path, [_row("Back", "moderate")])
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]
        # 1 header + 2 data rows, header written exactly once.
        assert len(lines) == 3
        assert lines[0].startswith("run_date,")
        assert sum(1 for ln in lines if ln.startswith("run_date,")) == 1

    def test_creates_parent_dir(self, tmp_path):
        path = tmp_path / "nested" / "sub" / "log.csv"
        _append_csv(path, [_row("Chest", "heavy")])
        assert path.exists()


class TestAnalyze:
    """Signal bar: a muscle needs >=2 same-direction disagreements to count."""

    def test_missing_file_returns_zero(self, tmp_path):
        assert _silently(analyze, tmp_path / "absent.csv") == 0

    def test_no_filled_rows_returns_zero(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(path, [_row("Chest", "heavy")])  # felt_band blank
        assert _silently(analyze, path) == 0

    def test_single_disagreement_is_noise(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(path, [_row("Chest", "heavy", "moderate")])
        assert _silently(analyze, path) == 0

    def test_two_same_direction_disagreements_is_signal(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(
            path,
            [
                _row("Chest", "heavy", "moderate", period="this_week"),
                _row("Chest", "heavy", "moderate", period="last_4_weeks"),
            ],
        )
        assert _silently(analyze, path) == 1

    def test_two_opposite_directions_are_not_signal(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(
            path,
            [
                _row("Chest", "heavy", "moderate"),   # engine_high
                _row("Chest", "light", "moderate"),   # engine_low
            ],
        )
        assert _silently(analyze, path) == 0

    def test_agreements_do_not_count(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(
            path,
            [
                _row("Chest", "heavy", "heavy"),
                _row("Chest", "heavy", "heavy"),
            ],
        )
        assert _silently(analyze, path) == 0

    def test_invalid_felt_band_is_not_signal(self, tmp_path):
        path = tmp_path / "log.csv"
        _write_csv(
            path,
            [
                _row("Chest", "heavy", "bogus"),
                _row("Chest", "heavy", "bogus"),
            ],
        )
        assert _silently(analyze, path) == 0


class TestObserveEmptyWorkoutLog:
    """The 2D-D gate invariant: an empty log yields zero evidence, no writes."""

    def test_empty_log_appends_nothing_and_returns_zero(self, app, tmp_path):
        csv_path = tmp_path / "stage4.csv"
        assert _silently(observe, csv_path) == 0
        # No pending rows fabricated, so the file is never created.
        assert not csv_path.exists()

    def test_observe_does_not_write_to_database(self, app, db_handler, tmp_path):
        before = db_handler.fetch_one("SELECT COUNT(*) AS c FROM workout_log")["c"]
        _silently(observe, tmp_path / "stage4.csv")
        after = db_handler.fetch_one("SELECT COUNT(*) AS c FROM workout_log")["c"]
        assert before == after == 0


class TestObserveWithLoggedData:
    def test_logged_data_appends_logged_side_rows(
        self, app, workout_log_factory, tmp_path
    ):
        workout_log_factory()  # one real logged set in the current window
        csv_path = tmp_path / "stage4.csv"
        appended = _silently(observe, csv_path)
        assert appended > 0
        assert csv_path.exists()
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == CSV_FIELDS
            rows = list(reader)
        assert rows, "expected at least one pending row"
        # Stage 4 signal is real-use: every appended row is logged-side, unfilled.
        assert all(r["side"] == "logged" for r in rows)
        assert all(r["felt_band"] == "" for r in rows)

    def test_second_run_does_not_duplicate_pending_rows(
        self, app, workout_log_factory, tmp_path
    ):
        workout_log_factory()
        csv_path = tmp_path / "stage4.csv"
        first = _silently(observe, csv_path)
        assert first > 0
        # Every (period, muscle) now has an unannotated pending row, so a daily
        # re-run must append nothing.
        second = _silently(observe, csv_path)
        assert second == 0


class TestStatusHelper:
    """`fatigue_stage4_status.main` — read-only DB facts for the PS health check."""

    def _run(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = status_main()
        payload = json.loads(buf.getvalue().strip().splitlines()[-1])
        return code, payload

    def test_reports_zero_on_empty_log(self, app):
        code, payload = self._run()
        assert code == 0
        assert payload["db_exists"] is True
        assert payload["workout_log_rows"] == 0
        assert payload["error"] is None

    def test_reports_count_with_logged_rows(self, app, workout_log_factory):
        from utils.database import DatabaseHandler

        workout_log_factory()  # 1st row (+ its plan/exercise)
        # Reuse the same plan so the 2nd row doesn't re-insert a duplicate
        # exercise name (exercise_name is unique).
        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT workout_plan_id AS pid FROM workout_log LIMIT 1"
            )
        workout_log_factory(plan_id=row["pid"])  # 2nd row, shared plan
        _, payload = self._run()
        assert payload["workout_log_rows"] == 2

    def test_returns_exit_code_zero(self, app):
        code, _ = self._run()
        assert code == 0
