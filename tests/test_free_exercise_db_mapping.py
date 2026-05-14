"""Tests for §4 free-exercise-db `media_path` schema, validator, and apply script.

Checkpoint 1 covers the data/import layer only. UI thumbnail rendering
and route-contract assertions land in later checkpoints.

Coverage:
  * `media_path` column on `exercises` (additive, nullable, idempotent,
    ALTER on legacy DBs).
  * `utils.media_path` shape validator accept/reject cases per §4.3.
  * `scripts/apply_free_exercise_db_mapping.py` validation + apply
    atomicity + idempotency.
  * `data/free_exercise_db_mapping.csv` header shape.
"""
from __future__ import annotations

import csv
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.apply_free_exercise_db_mapping import (
    EXPECTED_HEADER,
    main as apply_main,
    parse_csv,
)
from utils.database import DatabaseHandler
from utils.db_initializer import initialize_database
from utils.media_path import (
    ALLOWED_EXTENSIONS,
    explain_media_path_shape_failure,
    is_valid_media_path_shape,
    media_path_resolves,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPING_CSV = REPO_ROOT / "data" / "free_exercise_db_mapping.csv"


# ---------------------------------------------------------------------------
# Shape validator
# ---------------------------------------------------------------------------


class TestMediaPathShapeValidator:
    """Pure-function checks for the §4.3 path-shape rules."""

    @pytest.mark.parametrize("good", [
        "Squat_Barbell/0.jpg",
        "Some_Exercise/2.png",
        "dir/sub/img.webp",
        "Bench_Press/0.JPG",       # case-insensitive extension
        "Curl/3.jpeg",
        "Flat_DB_Press/0.gif",
        "x.png",                   # single segment
    ])
    def test_accepts_valid(self, good):
        assert is_valid_media_path_shape(good)
        assert explain_media_path_shape_failure(good) is None

    @pytest.mark.parametrize("bad,reason_substr", [
        ("", "non-empty"),
        ("/abs/path/0.jpg", "relative"),
        ("\\abs\\path\\0.jpg", "relative"),
        ("../../../etc/passwd", ".."),
        ("../etc/passwd.jpg", ".."),
        ("path/with/../evil.jpg", ".."),
        ("path/with/..//evil.jpg", ".."),
        ("dir//file.jpg", "empty segment"),
        ("dir\\img.jpg", "backslash"),
        ("dir/img.exe", "extension"),
        ("dir/img", "extension"),
        ("dir/img.JPGX", "extension"),
        ("dir/img.", "extension"),
        # Windows drive / colon prefixes — must reject in pure shape rules,
        # not just at filesystem-resolve time.
        ("C:/temp/0.jpg", ":"),
        ("C:temp/0.jpg", ":"),
        ("dir/C:bad.jpg", ":"),
        # Single-dot segments — normalise away on Path.resolve(), so they
        # would silently work; reject up-front to keep DB values canonical.
        ("./dir/0.jpg", "."),
        ("dir/./0.jpg", "."),
    ])
    def test_rejects_invalid(self, bad, reason_substr):
        assert not is_valid_media_path_shape(bad)
        explanation = explain_media_path_shape_failure(bad)
        assert explanation is not None
        assert reason_substr in explanation

    @pytest.mark.parametrize("non_string", [None, 0, 1.5, [], {}, b"x.jpg"])
    def test_rejects_non_string(self, non_string):
        assert not is_valid_media_path_shape(non_string)
        assert explain_media_path_shape_failure(non_string) is not None

    def test_allowed_extensions_match_spec(self):
        assert set(ALLOWED_EXTENSIONS) == {"jpg", "jpeg", "png", "gif", "webp"}


class TestMediaPathResolves:
    """`media_path_resolves()` checks shape + filesystem existence."""

    def _seed(self, base: Path, rel: str) -> None:
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"\x89PNG\r\n\x1a\n")  # any bytes

    def test_resolves_when_file_exists(self, tmp_path):
        self._seed(tmp_path, "Squat/0.jpg")
        assert media_path_resolves("Squat/0.jpg", tmp_path) is True

    def test_returns_false_when_file_missing(self, tmp_path):
        assert media_path_resolves("Squat/0.jpg", tmp_path) is False

    def test_returns_false_for_invalid_shape(self, tmp_path):
        # Even if we somehow seeded it, shape rules cut it off first.
        assert media_path_resolves("../escape.jpg", tmp_path) is False

    def test_returns_false_for_directory(self, tmp_path):
        (tmp_path / "Squat").mkdir()
        assert media_path_resolves("Squat/0.jpg", tmp_path) is False

    def test_default_vendor_base_is_repo_relative(self):
        # The repo currently has no vendored assets in checkpoint 1, so the
        # default base resolves but the file does not exist. The contract is
        # "False without raising".
        assert media_path_resolves("nope/missing.jpg") is False


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------


class TestSchemaAdditive:
    """`media_path` is added to fresh DBs and migrated onto legacy DBs."""

    def test_column_present_on_fresh_init(self, app):
        with DatabaseHandler() as db:
            cols = db.fetch_all("PRAGMA table_info(exercises)")
        names = {row["name"] for row in cols}
        assert "media_path" in names

    def test_column_is_nullable_text(self, app):
        with DatabaseHandler() as db:
            cols = db.fetch_all("PRAGMA table_info(exercises)")
        col = next(row for row in cols if row["name"] == "media_path")
        assert col["type"].upper() == "TEXT"
        assert col["notnull"] == 0

    def test_existing_rows_default_null(self, clean_db, exercise_factory):
        exercise_factory("Bench Press")
        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT media_path FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row is not None
        assert row["media_path"] is None

    def test_legacy_db_gets_alter_table(self, tmp_path, monkeypatch):
        """Initializing on a DB without media_path adds it via ALTER."""
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
        assert "media_path" in cols
        # Re-init must remain a no-op even with ALTER having already run.
        initialize_database(force=True)
        with sqlite3.connect(legacy) as conn:
            cols2 = [
                r[1] for r in conn.execute("PRAGMA table_info(exercises)")
            ]
        assert cols2.count("media_path") == 1

    def test_re_init_is_noop(self, app):
        initialize_database(force=True)
        with DatabaseHandler() as db:
            cols = db.fetch_all("PRAGMA table_info(exercises)")
        names = [row["name"] for row in cols]
        assert names.count("media_path") == 1


# ---------------------------------------------------------------------------
# Mapping CSV (committed scaffold)
# ---------------------------------------------------------------------------


class TestMappingCsv:
    def test_csv_exists(self):
        assert MAPPING_CSV.exists()

    def test_csv_header_is_canonical(self):
        with MAPPING_CSV.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
        assert tuple(h.strip().lower() for h in header) == EXPECTED_HEADER

    def test_csv_passes_validator(self):
        rows, errors = parse_csv(MAPPING_CSV)
        assert errors == [], f"CSV validation failed: {errors}"

    def test_csv_no_duplicate_names(self):
        with MAPPING_CSV.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            names = [
                (row.get("exercise_name") or "").strip().lower()
                for row in reader
                if (row.get("exercise_name") or "").strip()
            ]
        assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# Apply script — CSV-level validation
# ---------------------------------------------------------------------------


class TestApplyScriptValidation:
    """parse_csv rejects malformed input without partially applying."""

    def _write(self, tmp_path: Path, body: str) -> Path:
        p = tmp_path / "mapping.csv"
        p.write_text(body, encoding="utf-8")
        return p

    HEADER = (
        "exercise_name,suggested_fed_id,suggested_image_path,"
        "score,review_status\n"
    )

    def test_header_only_is_ok(self, tmp_path):
        path = self._write(tmp_path, self.HEADER)
        rows, errors = parse_csv(path)
        assert rows == []
        assert errors == []

    def test_missing_file_rejected(self, tmp_path):
        rows, errors = parse_csv(tmp_path / "does-not-exist.csv")
        assert rows == []
        assert any("not found" in e for e in errors)

    def test_empty_file_rejected(self, tmp_path):
        path = self._write(tmp_path, "")
        rows, errors = parse_csv(path)
        assert rows == []
        assert any("no header" in e.lower() for e in errors)

    def test_bad_header_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            "name,fed_id,image,score,status\n"
            "Bench Press,bp,Bench/0.jpg,0.9,confirmed\n",
        )
        rows, errors = parse_csv(path)
        assert rows == []
        assert any("header" in e.lower() for e in errors)

    def test_wrong_column_count_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            self.HEADER + "Bench Press,bp,Bench/0.jpg,confirmed\n",
        )
        _, errors = parse_csv(path)
        assert any("expected 5 columns" in e for e in errors)

    def test_blank_name_rejected(self, tmp_path):
        path = self._write(
            tmp_path, self.HEADER + ",bp,Bench/0.jpg,0.9,confirmed\n"
        )
        _, errors = parse_csv(path)
        assert any("blank exercise_name" in e for e in errors)

    def test_unknown_review_status_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            self.HEADER + "Bench Press,bp,Bench/0.jpg,0.9,maybe\n",
        )
        _, errors = parse_csv(path)
        assert any("review_status" in e for e in errors)

    def test_blank_path_blocks_confirmed(self, tmp_path):
        path = self._write(
            tmp_path, self.HEADER + "Bench Press,bp,,0.9,confirmed\n"
        )
        _, errors = parse_csv(path)
        assert any("blank suggested_image_path" in e for e in errors)

    def test_blank_path_blocks_manual(self, tmp_path):
        path = self._write(
            tmp_path, self.HEADER + "Bench Press,bp,,0.9,manual\n"
        )
        _, errors = parse_csv(path)
        assert any("blank suggested_image_path" in e for e in errors)

    def test_blank_path_allowed_for_auto(self, tmp_path):
        path = self._write(
            tmp_path, self.HEADER + "Bench Press,bp,,0.4,auto\n"
        )
        rows, errors = parse_csv(path)
        assert errors == []
        assert len(rows) == 1
        assert rows[0].applies is False

    def test_blank_path_allowed_for_rejected(self, tmp_path):
        path = self._write(
            tmp_path, self.HEADER + "Bench Press,bp,,0.4,rejected\n"
        )
        rows, errors = parse_csv(path)
        assert errors == []
        assert len(rows) == 1
        assert rows[0].applies is False

    @pytest.mark.parametrize("bad_path", [
        "/abs/path/0.jpg",
        "\\abs\\path\\0.jpg",
        "../escape.jpg",
        "dir//file.jpg",
        "dir\\img.jpg",
        "dir/img.exe",
        "dir/img",
        "dir/img.JPGX",
    ])
    def test_invalid_path_rejected_for_confirmed(self, tmp_path, bad_path):
        path = self._write(
            tmp_path,
            self.HEADER + f"Bench Press,bp,{bad_path},0.9,confirmed\n",
        )
        _, errors = parse_csv(path)
        assert any("invalid suggested_image_path" in e for e in errors)

    def test_invalid_path_rejected_even_for_auto(self, tmp_path):
        # auto/rejected with a non-blank path: shape is still required.
        path = self._write(
            tmp_path,
            self.HEADER + "Bench Press,bp,/abs/0.jpg,0.4,auto\n",
        )
        _, errors = parse_csv(path)
        assert any("invalid suggested_image_path" in e for e in errors)

    def test_non_numeric_score_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            self.HEADER + "Bench Press,bp,Bench/0.jpg,banana,confirmed\n",
        )
        _, errors = parse_csv(path)
        assert any("score" in e and "numeric" in e for e in errors)

    def test_blank_score_allowed(self, tmp_path):
        path = self._write(
            tmp_path,
            self.HEADER + "Bench Press,bp,Bench/0.jpg,,manual\n",
        )
        rows, errors = parse_csv(path)
        assert errors == []
        assert len(rows) == 1

    def test_duplicate_name_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            self.HEADER
            + "Bench Press,bp,Bench/0.jpg,0.9,confirmed\n"
            + "bench press,bp2,Bench/1.jpg,0.85,manual\n",
        )
        _, errors = parse_csv(path)
        assert any("duplicate exercise_name" in e for e in errors)


# ---------------------------------------------------------------------------
# Apply script — DB / asset-level atomicity (no partial apply on failure)
# ---------------------------------------------------------------------------


class TestApplyAtomicity:
    """Errors at any layer must abort the whole apply with no DB writes."""

    HEADER = TestApplyScriptValidation.HEADER

    def _seed_asset(self, base: Path, rel: str) -> None:
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")

    def _write_csv(self, tmp_path: Path, body: str) -> Path:
        p = tmp_path / "mapping.csv"
        p.write_text(self.HEADER + body, encoding="utf-8")
        return p

    def test_unknown_exercise_blocks_apply(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")
        self._seed_asset(vendor, "Squat/0.jpg")

        csv_path = self._write_csv(
            tmp_path,
            "Bench Press,bp,Bench/0.jpg,0.9,confirmed\n"
            "Nonexistent Exercise,sq,Squat/0.jpg,0.9,confirmed\n",
        )

        rc = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc == 1

        # Bench Press appears in the CSV but the run aborted, so no write.
        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT media_path FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["media_path"] is None

    def test_missing_asset_blocks_apply(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        exercise_factory("Squat")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")
        # Squat asset deliberately missing.

        csv_path = self._write_csv(
            tmp_path,
            "Bench Press,bp,Bench/0.jpg,0.9,confirmed\n"
            "Squat,sq,Squat/0.jpg,0.9,manual\n",
        )

        rc = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc == 1

        with DatabaseHandler() as db:
            rows = db.fetch_all(
                "SELECT exercise_name, media_path FROM exercises "
                "ORDER BY exercise_name"
            )
        # No DB write happened, even though Bench Press would have been valid.
        assert all(r["media_path"] is None for r in rows)

    def test_invalid_csv_blocks_apply(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")

        # Bad path on a confirmed row → CSV-layer rejection.
        csv_path = self._write_csv(
            tmp_path,
            "Bench Press,bp,/leading/slash.jpg,0.9,confirmed\n",
        )
        rc = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc == 1

        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT media_path FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["media_path"] is None

    def test_dry_run_does_not_write(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")

        csv_path = self._write_csv(
            tmp_path, "Bench Press,bp,Bench/0.jpg,0.9,confirmed\n"
        )
        rc = apply_main([
            "--csv", str(csv_path),
            "--vendor-base", str(vendor),
            "--dry-run",
        ])
        assert rc == 0

        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT media_path FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["media_path"] is None

    def test_midloop_db_error_rolls_back_all_rows(
        self, app, clean_db, exercise_factory, tmp_path, monkeypatch
    ):
        """An unexpected DB error inside the apply loop must roll back every prior row."""
        exercise_factory("Bench Press")
        exercise_factory("Squat")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")
        self._seed_asset(vendor, "Squat/0.jpg")

        csv_path = self._write_csv(
            tmp_path,
            "Bench Press,bp,Bench/0.jpg,0.9,confirmed\n"
            "Squat,sq,Squat/0.jpg,0.9,confirmed\n",
        )

        original_execute = DatabaseHandler.execute_query
        update_counter = {"n": 0}

        def flaky(self, query, params=None, *, commit=True):
            if query.strip().upper().startswith("UPDATE EXERCISES"):
                update_counter["n"] += 1
                if update_counter["n"] == 2:
                    raise sqlite3.OperationalError("simulated mid-loop failure")
            return original_execute(self, query, params, commit=commit)

        monkeypatch.setattr(DatabaseHandler, "execute_query", flaky)

        with pytest.raises(sqlite3.OperationalError):
            apply_main([
                "--csv", str(csv_path), "--vendor-base", str(vendor),
            ])

        # Restore so the assertion query runs cleanly.
        monkeypatch.setattr(DatabaseHandler, "execute_query", original_execute)

        with DatabaseHandler() as db:
            rows = db.fetch_all(
                "SELECT exercise_name, media_path FROM exercises "
                "ORDER BY exercise_name"
            )
        # Bench Press would have been written first; its update must have
        # rolled back when the second update raised.
        assert all(r["media_path"] is None for r in rows), (
            f"expected all media_path values to roll back, got {rows!r}"
        )


# ---------------------------------------------------------------------------
# Apply script — happy path + idempotency
# ---------------------------------------------------------------------------


class TestApplyHappyPath:
    HEADER = TestApplyScriptValidation.HEADER

    def _seed_asset(self, base: Path, rel: str) -> None:
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")

    def _write_csv(self, tmp_path: Path, body: str) -> Path:
        p = tmp_path / "mapping.csv"
        p.write_text(self.HEADER + body, encoding="utf-8")
        return p

    def test_confirmed_row_writes_path(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")

        csv_path = self._write_csv(
            tmp_path, "Bench Press,bp,Bench/0.jpg,0.95,confirmed\n"
        )
        rc = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc == 0

        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT media_path FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["media_path"] == "Bench/0.jpg"

    def test_auto_and_rejected_rows_skipped(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        exercise_factory("Squat")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")

        # Auto/rejected are valid rows but never written. The auto row's path
        # is shape-validated even though it's ignored.
        csv_path = self._write_csv(
            tmp_path,
            "Bench Press,bp,Bench/0.jpg,0.4,auto\n"
            "Squat,sq,,0.0,rejected\n",
        )
        rc = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc == 0

        with DatabaseHandler() as db:
            rows = db.fetch_all(
                "SELECT exercise_name, media_path FROM exercises "
                "ORDER BY exercise_name"
            )
        assert all(r["media_path"] is None for r in rows)

    def test_idempotent_apply(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")

        csv_path = self._write_csv(
            tmp_path, "Bench Press,bp,Bench/0.jpg,0.9,manual\n"
        )

        rc1 = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc1 == 0

        rc2 = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc2 == 0

        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT media_path FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["media_path"] == "Bench/0.jpg"

    def test_case_insensitive_exercise_match(
        self, app, clean_db, exercise_factory, tmp_path
    ):
        exercise_factory("Bench Press")
        vendor = tmp_path / "vendor"
        self._seed_asset(vendor, "Bench/0.jpg")

        csv_path = self._write_csv(
            tmp_path, "BENCH press,bp,Bench/0.jpg,0.9,confirmed\n"
        )
        rc = apply_main([
            "--csv", str(csv_path), "--vendor-base", str(vendor),
        ])
        assert rc == 0

        with DatabaseHandler() as db:
            row = db.fetch_one(
                "SELECT media_path FROM exercises "
                "WHERE exercise_name = 'Bench Press'"
            )
        assert row["media_path"] == "Bench/0.jpg"


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


class TestSafeMediaPathJinjaFilter:
    """`safe_media_path` filter revalidates path-shape rules at render time."""

    def test_filter_returns_value_for_valid_path(self, app):
        with app.app_context():
            f = app.jinja_env.filters["safe_media_path"]
            assert f("Squat_Barbell/0.jpg") == "Squat_Barbell/0.jpg"

    def test_filter_returns_none_for_invalid_path(self, app):
        with app.app_context():
            f = app.jinja_env.filters["safe_media_path"]
            for bad in (
                None,
                "",
                "/abs/path/0.jpg",
                "../etc/passwd",
                "dir/with/..//evil.jpg",
                "dir\\img.jpg",
                "C:/temp/0.jpg",
                "dir/img.exe",
                "dir/img",
                123,
            ):
                assert f(bad) is None, f"Expected None for {bad!r}"


class TestRouteContracts:
    """`/get_workout_plan` and `/get_workout_logs` expose `media_path`."""

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
        assert "media_path" in rows[0]
        assert rows[0]["media_path"] is None

    def test_get_workout_plan_includes_field_set(
        self, client, clean_db, exercise_factory, workout_plan_factory
    ):
        exercise_factory("Bench Press")
        workout_plan_factory(exercise_name="Bench Press")
        with DatabaseHandler() as db:
            db.execute_query(
                "UPDATE exercises SET media_path = ? "
                "WHERE exercise_name = 'Bench Press'",
                ("Bench_Press/0.jpg",),
            )

        resp = client.get("/get_workout_plan")
        body = resp.get_json()
        target = next(
            r for r in body["data"] if r["exercise"] == "Bench Press"
        )
        assert target["media_path"] == "Bench_Press/0.jpg"

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
        assert "media_path" in rows[0]
        assert all(r["media_path"] is None for r in rows)

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
                "UPDATE exercises SET media_path = ? "
                "WHERE exercise_name = 'Bench Press'",
                ("Bench_Press/0.jpg",),
            )

        resp = client.get("/get_workout_logs")
        body = resp.get_json()
        target = next(
            r for r in body["data"] if r["exercise"] == "Bench Press"
        )
        assert target["media_path"] == "Bench_Press/0.jpg"


class TestApplyScriptCli:
    def test_help_runs(self):
        result = subprocess.run(
            [
                sys.executable,
                "scripts/apply_free_exercise_db_mapping.py",
                "--help",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "media_path" in result.stdout.lower() or "free-exercise-db" in result.stdout.lower()
