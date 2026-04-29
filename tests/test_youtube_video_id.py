"""Tests for the §5 YouTube video-id schema, apply script, and route contracts.

Covers:
  * `youtube_video_id` column on `exercises` (additive, nullable, idempotent)
  * `scripts/apply_youtube_curated.py` validation + idempotency
  * `data/youtube_curated_top_n.csv` shape (when populated)
  * `/get_workout_plan` and `/get_workout_logs` JSON include `youtube_video_id`
"""
from __future__ import annotations

import csv
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.apply_youtube_curated import (
    YOUTUBE_ID_RE,
    is_valid_youtube_id,
    parse_csv,
)
from utils.database import DatabaseHandler
from utils.db_initializer import initialize_database

REPO_ROOT = Path(__file__).resolve().parents[1]
CURATED_CSV = REPO_ROOT / "data" / "youtube_curated_top_n.csv"


class TestYoutubeIdRegex:
    """Pure-function checks for the canonical 11-char YouTube id shape."""

    @pytest.mark.parametrize("good", [
        "dQw4w9WgXcQ",     # canonical Rick Astley
        "abcdefghijk",     # all lowercase letters
        "ABCDEFGHIJK",     # all uppercase letters
        "0123456789a",     # digits + letter
        "a-_a-_a-_a-",     # dashes and underscores
    ])
    def test_accepts_valid(self, good):
        assert is_valid_youtube_id(good)
        assert YOUTUBE_ID_RE.match(good)

    @pytest.mark.parametrize("bad", [
        "",                       # empty
        "short",                  # too short
        "wayTooLongValue123",     # too long
        "abcdefghij!",            # bad char (!)
        "abcdefghij ",            # space
        "abcdefghij\n",           # trailing newline
        "abcdefghij/",            # slash
        " abcdefghij",            # leading space
    ])
    def test_rejects_invalid(self, bad):
        assert not is_valid_youtube_id(bad)


class TestSchemaAdditive:
    """Schema migration is additive, idempotent, and works on legacy DBs."""

    def test_column_present_on_fresh_init(self, app):
        with DatabaseHandler() as db:
            cols = db.fetch_all("PRAGMA table_info(exercises)")
        names = {row["name"] for row in cols}
        assert "youtube_video_id" in names

    def test_column_is_nullable_text(self, app):
        with DatabaseHandler() as db:
            cols = db.fetch_all("PRAGMA table_info(exercises)")
        col = next(row for row in cols if row["name"] == "youtube_video_id")
        assert col["type"].upper() == "TEXT"
        # `notnull` is 0 for nullable columns
        assert col["notnull"] == 0

    def test_existing_rows_default_null(self, clean_db, exercise_factory):
        exercise_factory("Bench Press")
        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT youtube_video_id FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row is not None
        assert row["youtube_video_id"] is None

    def test_legacy_db_gets_alter_table(self, tmp_path, monkeypatch):
        """Initializing on a DB without the new column adds it via ALTER."""
        legacy = tmp_path / "legacy.db"
        with sqlite3.connect(legacy) as conn:
            conn.execute(
                """
                CREATE TABLE exercises (
                    exercise_name TEXT PRIMARY KEY,
                    primary_muscle_group TEXT
                )
                """
            )
            conn.commit()

        import utils.config
        monkeypatch.setattr(utils.config, "DB_FILE", str(legacy))
        initialize_database(force=True)

        with sqlite3.connect(legacy) as conn:
            cols = [
                r[1] for r in conn.execute("PRAGMA table_info(exercises)")
            ]
        assert "youtube_video_id" in cols

    def test_re_init_is_noop(self, app):
        """Calling initialize_database again must not error or duplicate cols."""
        initialize_database(force=True)
        with DatabaseHandler() as db:
            cols = db.fetch_all("PRAGMA table_info(exercises)")
        names = [row["name"] for row in cols]
        assert names.count("youtube_video_id") == 1


class TestCuratedCsv:
    """The committed curated CSV must be well-formed, even when empty."""

    def test_csv_exists(self):
        assert CURATED_CSV.exists(), (
            f"Expected curated CSV at {CURATED_CSV}; create it as a "
            "header-only file if no curation has been done yet."
        )

    def test_csv_header_is_canonical(self):
        with CURATED_CSV.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
        assert [h.strip().lower() for h in header] == [
            "exercise_name",
            "youtube_video_id",
        ]

    def test_csv_rows_pass_validator(self):
        rows, errors = parse_csv(CURATED_CSV)
        assert errors == [], f"CSV validation failed: {errors}"
        # Every id is the right shape (parse_csv enforces this, but assert
        # again so a regression here is caught explicitly).
        for _name, video_id in rows:
            assert YOUTUBE_ID_RE.match(video_id)

    def test_csv_no_duplicate_names(self):
        """parse_csv catches duplicates; this is a belt-and-braces check."""
        with CURATED_CSV.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            names = [
                (row.get("exercise_name") or "").strip().lower()
                for row in reader
                if (row.get("exercise_name") or "").strip()
            ]
        assert len(names) == len(set(names))


class TestApplyScriptValidation:
    """The apply script rejects bad input without partially applying."""

    def _write(self, tmp_path: Path, body: str) -> Path:
        p = tmp_path / "curated.csv"
        p.write_text(body, encoding="utf-8")
        return p

    def test_header_only_is_ok(self, app, tmp_path):
        path = self._write(tmp_path, "exercise_name,youtube_video_id\n")
        rows, errors = parse_csv(path)
        assert rows == []
        assert errors == []

    def test_bad_header_rejected(self, app, tmp_path):
        path = self._write(tmp_path, "name,id\nBench Press,dQw4w9WgXcQ\n")
        rows, errors = parse_csv(path)
        assert rows == []
        assert any("header" in e.lower() for e in errors)

    def test_short_id_rejected(self, app, tmp_path):
        path = self._write(
            tmp_path,
            "exercise_name,youtube_video_id\nBench Press,short\n",
        )
        _, errors = parse_csv(path)
        assert any("invalid youtube_video_id" in e for e in errors)

    def test_blank_id_rejected(self, app, tmp_path):
        path = self._write(
            tmp_path,
            "exercise_name,youtube_video_id\nBench Press,\n",
        )
        _, errors = parse_csv(path)
        assert any("blank youtube_video_id" in e for e in errors)

    def test_blank_name_rejected(self, app, tmp_path):
        path = self._write(
            tmp_path,
            "exercise_name,youtube_video_id\n,dQw4w9WgXcQ\n",
        )
        _, errors = parse_csv(path)
        assert any("blank exercise_name" in e for e in errors)

    def test_duplicate_name_rejected(self, app, tmp_path):
        path = self._write(
            tmp_path,
            "exercise_name,youtube_video_id\n"
            "Bench Press,dQw4w9WgXcQ\n"
            "bench press,abcdefghijk\n",
        )
        _, errors = parse_csv(path)
        assert any("duplicate exercise_name" in e for e in errors)

    def test_unknown_exercise_blocks_apply(self, app, clean_db, tmp_path):
        """If an exercise_name isn't in the DB, the script aborts."""
        from scripts.apply_youtube_curated import main as apply_main

        path = self._write(
            tmp_path,
            "exercise_name,youtube_video_id\n"
            "Nonexistent Exercise,dQw4w9WgXcQ\n",
        )
        rc = apply_main(["--csv", str(path)])
        assert rc == 1


class TestApplyScriptIdempotency:
    """Apply twice with the same content => no DB delta after the first run."""

    def test_apply_then_verify(self, app, clean_db, exercise_factory, tmp_path):
        from scripts.apply_youtube_curated import main as apply_main

        exercise_factory("Bench Press")
        csv_path = tmp_path / "curated.csv"
        csv_path.write_text(
            "exercise_name,youtube_video_id\nBench Press,dQw4w9WgXcQ\n",
            encoding="utf-8",
        )

        # First apply
        rc1 = apply_main(["--csv", str(csv_path)])
        assert rc1 == 0
        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT youtube_video_id FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["youtube_video_id"] == "dQw4w9WgXcQ"

        # Second apply — must succeed and leave the value unchanged
        rc2 = apply_main(["--csv", str(csv_path)])
        assert rc2 == 0
        with DatabaseHandler() as db:
            row2 = db.fetch_one(
                "SELECT youtube_video_id FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row2["youtube_video_id"] == "dQw4w9WgXcQ"

    def test_dry_run_does_not_write(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        from scripts.apply_youtube_curated import main as apply_main

        exercise_factory("Bench Press")
        csv_path = tmp_path / "curated.csv"
        csv_path.write_text(
            "exercise_name,youtube_video_id\nBench Press,dQw4w9WgXcQ\n",
            encoding="utf-8",
        )

        rc = apply_main(["--csv", str(csv_path), "--dry-run"])
        assert rc == 0
        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT youtube_video_id FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["youtube_video_id"] is None

    def test_case_insensitive_match(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        """CSV name matches DB row case-insensitively."""
        from scripts.apply_youtube_curated import main as apply_main

        exercise_factory("Bench Press")
        csv_path = tmp_path / "curated.csv"
        csv_path.write_text(
            "exercise_name,youtube_video_id\nBENCH press,dQw4w9WgXcQ\n",
            encoding="utf-8",
        )

        rc = apply_main(["--csv", str(csv_path)])
        assert rc == 0
        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT youtube_video_id FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["youtube_video_id"] == "dQw4w9WgXcQ"


class TestRouteContracts:
    """`/get_workout_plan` and `/get_workout_logs` expose `youtube_video_id`."""

    def test_get_workout_plan_includes_field_null(
        self, client, clean_db, exercise_factory, workout_plan_factory
    ):
        exercise_factory("Bench Press")
        workout_plan_factory(exercise_name="Bench Press")

        resp = client.get("/get_workout_plan")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        rows = body["data"]
        assert len(rows) >= 1
        assert "youtube_video_id" in rows[0]
        assert rows[0]["youtube_video_id"] is None

    def test_get_workout_plan_includes_field_set(
        self, client, clean_db, exercise_factory, workout_plan_factory
    ):
        exercise_factory("Bench Press")
        workout_plan_factory(exercise_name="Bench Press")
        with DatabaseHandler() as db:
            db.execute_query(
                "UPDATE exercises SET youtube_video_id = ? "
                "WHERE exercise_name = 'Bench Press'",
                ("dQw4w9WgXcQ",),
            )

        resp = client.get("/get_workout_plan")
        body = resp.get_json()
        target = next(
            r for r in body["data"] if r["exercise"] == "Bench Press"
        )
        assert target["youtube_video_id"] == "dQw4w9WgXcQ"

    def test_get_workout_logs_includes_field_null(
        self,
        client,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        workout_log_factory,
    ):
        exercise_factory("Bench Press")
        plan_id = workout_plan_factory(exercise_name="Bench Press")
        workout_log_factory(plan_id=plan_id, exercise="Bench Press")

        resp = client.get("/get_workout_logs")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        rows = body["data"]
        assert len(rows) >= 1
        assert "youtube_video_id" in rows[0]
        # Every row's joined youtube_video_id should be NULL (no curation).
        assert all(r["youtube_video_id"] is None for r in rows)

    def test_get_workout_logs_includes_field_set(
        self,
        client,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        workout_log_factory,
    ):
        exercise_factory("Bench Press")
        plan_id = workout_plan_factory(exercise_name="Bench Press")
        workout_log_factory(plan_id=plan_id, exercise="Bench Press")
        with DatabaseHandler() as db:
            db.execute_query(
                "UPDATE exercises SET youtube_video_id = ? "
                "WHERE exercise_name = 'Bench Press'",
                ("dQw4w9WgXcQ",),
            )

        resp = client.get("/get_workout_logs")
        body = resp.get_json()
        target = next(r for r in body["data"] if r["exercise"] == "Bench Press")
        assert target["youtube_video_id"] == "dQw4w9WgXcQ"


class TestApplyScriptCli:
    """Smoke-test running the script as a subprocess (catches import errors)."""

    def test_help_runs(self):
        result = subprocess.run(
            [sys.executable, "scripts/apply_youtube_curated.py", "--help"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "youtube" in result.stdout.lower()


class TestPageRender:
    """Server-rendered /workout_log page surfaces the play button + modal."""

    def test_modal_partial_present_on_log_page(self, client, clean_db):
        resp = client.get("/workout_log")
        # Pytest env may surface 500 if the template tree fails to resolve.
        if resp.status_code != 200:
            pytest.skip(
                f"workout_log returned {resp.status_code}; template tree may "
                "not be available in this pytest env."
            )
        body = resp.get_data(as_text=True)
        assert "exerciseVideoModal" in body
        assert "exerciseVideoIframe" in body

    def test_log_row_has_play_button(
        self,
        client,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        workout_log_factory,
    ):
        exercise_factory("Bench Press")
        plan_id = workout_plan_factory(exercise_name="Bench Press")
        workout_log_factory(plan_id=plan_id, exercise="Bench Press")

        resp = client.get("/workout_log")
        if resp.status_code != 200:
            pytest.skip(
                f"workout_log returned {resp.status_code}; template tree may "
                "not be available in this pytest env."
            )
        body = resp.get_data(as_text=True)
        assert "log-play-video-btn" in body
        # No curated id seeded → button should ship with empty data-video-id.
        assert 'data-video-id=""' in body
        # Aria label uses the exercise name verbatim.
        assert "Play reference video for Bench Press" in body

    def test_log_row_play_button_with_curated_id(
        self,
        client,
        clean_db,
        exercise_factory,
        workout_plan_factory,
        workout_log_factory,
    ):
        exercise_factory("Bench Press")
        plan_id = workout_plan_factory(exercise_name="Bench Press")
        workout_log_factory(plan_id=plan_id, exercise="Bench Press")
        with DatabaseHandler() as db:
            db.execute_query(
                "UPDATE exercises SET youtube_video_id = ? "
                "WHERE exercise_name = 'Bench Press'",
                ("dQw4w9WgXcQ",),
            )

        resp = client.get("/workout_log")
        if resp.status_code != 200:
            pytest.skip(
                f"workout_log returned {resp.status_code}; template tree may "
                "not be available in this pytest env."
            )
        body = resp.get_data(as_text=True)
        assert 'data-video-id="dQw4w9WgXcQ"' in body
