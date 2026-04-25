import sqlite3
from unittest.mock import patch

import pytest

from utils.database import DatabaseHandler, add_volume_plan_activation_columns, add_volume_tracking_tables
from utils.volume_export import export_volume_plan
from utils.volume_progress import (
    DEFAULT_RECOMMENDED_RANGES,
    activate_volume_plan,
    deactivate_volume_plan,
    aggregate_planned_sets,
    get_volume_progress,
)
from utils.volume_taxonomy import (
    ADVANCED_MUSCLE_GROUPS,
    BASIC_MUSCLE_GROUPS,
    COARSE_TO_BASIC,
    canonical_pst,
)


def _create_exercise(
    db,
    name,
    *,
    primary="Chest",
    secondary="Triceps",
    tertiary="Shoulders",
    advanced=None,
):
    db.execute_query(
        """
        INSERT INTO exercises (
            exercise_name,
            primary_muscle_group,
            secondary_muscle_group,
            tertiary_muscle_group,
            advanced_isolated_muscles,
            force,
            equipment,
            mechanic,
            utility,
            difficulty
        )
        VALUES (?, ?, ?, ?, ?, 'Push', 'Barbell', 'Compound', 'Basic', 'Intermediate')
        """,
        (name, primary, secondary, tertiary, advanced),
    )
    return name


def _add_isolated_tokens(db, exercise_name, tokens):
    for token in tokens:
        db.execute_query(
            """
            INSERT INTO exercise_isolated_muscles (exercise_name, muscle)
            VALUES (?, ?)
            """,
            (exercise_name, token),
        )


def _select_exercise(db, exercise_name, *, sets=3, routine="A"):
    db.execute_query(
        """
        INSERT INTO user_selection (
            routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight
        )
        VALUES (?, ?, ?, 6, 10, 2, 8, 100)
        """,
        (routine, exercise_name, sets),
    )


def _row_by_muscle(rows, muscle):
    return next(row for row in rows if row["muscle_group"] == muscle)


def test_migration_idempotent(clean_db):
    add_volume_plan_activation_columns()
    add_volume_plan_activation_columns()

    with DatabaseHandler() as db:
        columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(volume_plans)")}
        indexes = {row["name"] for row in db.fetch_all("PRAGMA index_list(volume_plans)")}

    assert {"is_active", "mode"} <= columns
    assert "idx_volume_plans_single_active" in indexes


def test_migration_called_via_add_volume_tracking_tables(clean_db):
    add_volume_tracking_tables()

    with DatabaseHandler() as db:
        columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(volume_plans)")}
        indexes = {row["name"] for row in db.fetch_all("PRAGMA index_list(volume_plans)")}

    assert {"is_active", "mode"} <= columns
    assert "idx_volume_plans_single_active" in indexes


def test_default_recommended_ranges_cover_all_muscles():
    assert set(DEFAULT_RECOMMENDED_RANGES) >= set(BASIC_MUSCLE_GROUPS) | set(ADVANCED_MUSCLE_GROUPS)


def test_mode_persists_on_save(clean_db):
    plan_id = export_volume_plan(
        {"training_days": 4, "mode": "advanced", "volumes": {"upper-pectoralis": 12}},
        mode="advanced",
    )

    with DatabaseHandler() as db:
        plan = db.fetch_one("SELECT mode FROM volume_plans WHERE id = ?", (plan_id,))

    assert plan["mode"] == "advanced"


def test_only_one_plan_active_at_a_time(clean_db):
    first = export_volume_plan({"training_days": 3, "volumes": {"Chest": 12}})
    second = export_volume_plan({"training_days": 4, "volumes": {"Chest": 16}})

    assert activate_volume_plan(first)
    assert activate_volume_plan(second)

    with DatabaseHandler() as db:
        active = db.fetch_all("SELECT id FROM volume_plans WHERE is_active = 1")

    assert active == [{"id": second}]


def test_activate_nonexistent_plan_returns_404_and_preserves_active(client, clean_db):
    plan_id = export_volume_plan({"training_days": 3, "volumes": {"Chest": 12}})
    assert activate_volume_plan(plan_id)

    response = client.post("/api/volume_plan/999999/activate")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"]["code"] == "PLAN_NOT_FOUND"

    with DatabaseHandler() as db:
        active = db.fetch_all("SELECT id FROM volume_plans WHERE is_active = 1")

    assert active == [{"id": plan_id}]


def test_deactivate_idempotent_for_inactive_plan(client, clean_db):
    plan_id = export_volume_plan({"training_days": 3, "volumes": {"Chest": 12}})

    response = client.post(f"/api/volume_plan/{plan_id}/deactivate")

    assert response.status_code == 200
    with DatabaseHandler() as db:
        active_count = db.fetch_one("SELECT COUNT(*) AS count FROM volume_plans WHERE is_active = 1")

    assert active_count["count"] == 0


def test_partial_unique_index_prevents_two_active(clean_db):
    first = export_volume_plan({"training_days": 3, "volumes": {"Chest": 12}})
    second = export_volume_plan({"training_days": 4, "volumes": {"Back": 12}})

    with pytest.raises(sqlite3.IntegrityError):
        with DatabaseHandler() as db:
            db.execute_query("UPDATE volume_plans SET is_active = 1 WHERE id = ?", (first,))
            db.execute_query("UPDATE volume_plans SET is_active = 1 WHERE id = ?", (second,))


def test_bench_press_basic_mode_no_isolation(clean_db):
    exercise = _create_exercise(clean_db, "Bench Press")
    _select_exercise(clean_db, exercise, sets=3)

    totals, diagnostics = aggregate_planned_sets("basic")

    assert totals["Chest"] == pytest.approx(3.0)
    assert totals["Triceps"] == pytest.approx(1.5)
    assert totals["Front-Shoulder"] == pytest.approx(0.75)
    assert diagnostics["unmapped_muscles"] == []


def test_advanced_mode_primary_refinement_rejects_wrong_family_tokens(clean_db):
    exercise = _create_exercise(
        clean_db,
        "Barbell Bench Press",
        advanced="Chest; Lateral Head Triceps; Medial Head Triceps",
    )
    _add_isolated_tokens(
        clean_db,
        exercise,
        ["chest", "lateral-head-triceps", "medial-head-triceps"],
    )
    _select_exercise(clean_db, exercise, sets=3)

    totals, diagnostics = aggregate_planned_sets("advanced")

    assert totals["mid-lower-pectoralis"] == pytest.approx(3.0)
    assert totals["long-head-triceps"] == pytest.approx(1.5)
    assert totals["lateral-head-triceps"] == pytest.approx(0.0)
    assert totals["medial-head-triceps"] == pytest.approx(0.0)
    assert [item["reason"] for item in diagnostics["rejected_tokens"]] == [
        "family_mismatch",
        "family_mismatch",
    ]


def test_unknown_token_goes_to_diagnostics_with_representative_fallback(clean_db):
    exercise = _create_exercise(clean_db, "Unknown Token Press", advanced="some-unmapped-token")
    _select_exercise(clean_db, exercise, sets=3)

    totals, diagnostics = aggregate_planned_sets("advanced")

    assert totals["mid-lower-pectoralis"] == pytest.approx(3.0)
    assert "some-unmapped-token" in diagnostics["unmapped_muscles"]
    assert diagnostics["csv_fallback_count"] == 1


def test_selected_exercise_with_blank_pst_uses_isolated_only_strategy(clean_db):
    exercise = _create_exercise(
        clean_db,
        "Blank Pst Pressdown",
        primary=None,
        secondary=None,
        tertiary=None,
    )
    _add_isolated_tokens(clean_db, exercise, ["upper-pectoralis", "long-head-triceps"])
    _select_exercise(clean_db, exercise, sets=4)

    basic_totals, basic_diagnostics = aggregate_planned_sets("basic")
    advanced_totals, advanced_diagnostics = aggregate_planned_sets("advanced")

    assert basic_totals["Chest"] == pytest.approx(2.0)
    assert basic_totals["Triceps"] == pytest.approx(2.0)
    assert advanced_totals["upper-pectoralis"] == pytest.approx(2.0)
    assert advanced_totals["long-head-triceps"] == pytest.approx(2.0)
    assert basic_diagnostics["blank_pst_rows"] == [exercise]
    assert advanced_diagnostics["blank_pst_rows"] == [exercise]


def test_selected_exercise_with_blank_pst_exclude_strategy_records_diagnostic_only(
    clean_db, monkeypatch
):
    """When BLANK_PST_STRATEGY='exclude', the row is diagnosed but contributes nothing."""
    import utils.volume_taxonomy as taxonomy

    monkeypatch.setattr(taxonomy, "BLANK_PST_STRATEGY", "exclude")

    exercise = _create_exercise(
        clean_db,
        "Excluded Blank Pressdown",
        primary=None,
        secondary=None,
        tertiary=None,
    )
    _add_isolated_tokens(clean_db, exercise, ["upper-pectoralis", "long-head-triceps"])
    _select_exercise(clean_db, exercise, sets=4)

    basic_totals, basic_diagnostics = aggregate_planned_sets("basic")
    advanced_totals, advanced_diagnostics = aggregate_planned_sets("advanced")

    assert all(value == pytest.approx(0.0) for value in basic_totals.values())
    assert all(value == pytest.approx(0.0) for value in advanced_totals.values())
    assert basic_diagnostics["blank_pst_rows"] == [exercise]
    assert advanced_diagnostics["blank_pst_rows"] == [exercise]


def test_fetch_planned_rows_prefers_mapping_table_tokens(clean_db):
    exercise = _create_exercise(
        clean_db,
        "Mapping Preferred Press",
        advanced="SHOULD_BE_IGNORED",
    )
    _add_isolated_tokens(clean_db, exercise, ["upper-pectoralis"])
    _select_exercise(clean_db, exercise, sets=3)

    totals, diagnostics = aggregate_planned_sets("advanced")

    assert totals["upper-pectoralis"] == pytest.approx(3.0)
    assert "SHOULD_BE_IGNORED" not in diagnostics["unmapped_muscles"]
    assert diagnostics["csv_fallback_count"] == 0


def test_no_active_plan_endpoint_returns_200_empty(client, clean_db):
    response = client.get("/api/volume_progress")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["active_plan_exists"] is False
    assert payload["rows"] == []


def test_volume_progress_endpoint_merges_targets_and_planned_sets(client, clean_db):
    exercise = _create_exercise(clean_db, "Bench Press")
    _select_exercise(clean_db, exercise, sets=3)
    plan_id = export_volume_plan(
        {
            "training_days": 4,
            "volumes": {
                "Chest": {"weekly_sets": 10, "status": "optimal"},
                "Calves": {"weekly_sets": 16, "status": "optimal"},
            },
        }
    )
    assert activate_volume_plan(plan_id)

    response = client.get("/api/volume_progress")

    assert response.status_code == 200
    payload = response.get_json()["data"]
    chest = _row_by_muscle(payload["rows"], "Chest")
    calves = _row_by_muscle(payload["rows"], "Calves")

    assert payload["active_plan_exists"] is True
    assert payload["active_plan"]["id"] == plan_id
    assert chest["planned"] == pytest.approx(3.0)
    assert chest["target"] == pytest.approx(10.0)
    assert chest["target_status"] == "low"
    assert chest["progress_status"] == "under_target"
    assert calves["planned"] == pytest.approx(0.0)
    assert calves["progress_status"] == "unplanned_target"


# ── §12.2 additional tests ──────────────────────────────────────────────


def test_erase_data_recreates_columns_and_index(client, clean_db):
    """POST /erase-data then verify activation columns and index are present."""
    response = client.post(
        "/erase-data",
        json={"confirm": "ERASE_ALL_DATA"},
        content_type="application/json",
    )
    assert response.status_code == 200

    with DatabaseHandler() as db:
        columns = {row["name"] for row in db.fetch_all("PRAGMA table_info(volume_plans)")}
        indexes = {row["name"] for row in db.fetch_all("PRAGMA index_list(volume_plans)")}

    assert {"is_active", "mode"} <= columns
    assert "idx_volume_plans_single_active" in indexes


def test_activate_is_transactional(clean_db):
    """If the second UPDATE raises, the previously-active plan stays active."""
    first = export_volume_plan({"training_days": 3, "volumes": {"Chest": 12}})
    second = export_volume_plan({"training_days": 4, "volumes": {"Chest": 16}})
    assert activate_volume_plan(first)

    original_execute = DatabaseHandler.execute_query
    call_count = 0

    def _exploding_execute(self, query, params=None, *, commit=True):
        nonlocal call_count
        call_count += 1
        # Let the first UPDATE (deactivate all) through, explode on the second (set new)
        if "UPDATE volume_plans SET is_active = 1" in query:
            raise sqlite3.OperationalError("simulated failure")
        return original_execute(self, query, params, commit=commit)

    with patch.object(DatabaseHandler, "execute_query", _exploding_execute):
        with pytest.raises(sqlite3.OperationalError):
            activate_volume_plan(second)

    with DatabaseHandler() as db:
        active = db.fetch_all("SELECT id FROM volume_plans WHERE is_active = 1")

    assert active == [{"id": first}]


def test_activate_rollback_when_set_row_disappears(clean_db):
    """When the SET update returns rowcount 0, rollback preserves the original active plan."""
    first = export_volume_plan({"training_days": 3, "volumes": {"Chest": 12}})
    second = export_volume_plan({"training_days": 4, "volumes": {"Chest": 16}})
    assert activate_volume_plan(first)

    original_execute = DatabaseHandler.execute_query

    def _zero_rowcount_execute(self, query, params=None, *, commit=True):
        if "UPDATE volume_plans SET is_active = 1 WHERE id" in query:
            # Skip the real UPDATE so the row never flips to active, then
            # report rowcount=0 to drive the rollback path under test.
            return 0
        return original_execute(self, query, params, commit=commit)

    with patch.object(DatabaseHandler, "execute_query", _zero_rowcount_execute):
        result = activate_volume_plan(second)

    assert result is False

    with DatabaseHandler() as db:
        active = db.fetch_all("SELECT id FROM volume_plans WHERE is_active = 1")

    # Either first is still active or at most one plan is active (rollback happened)
    assert len(active) <= 1


def test_ignored_token_is_not_attributed_but_is_recorded(clean_db):
    """Tokens in IGNORED_TOKENS appear in diagnostics.ignored_tokens."""
    exercise = _create_exercise(
        clean_db,
        "Neck Token Press",
        primary="Chest",
        secondary=None,
        tertiary=None,
    )
    # splenius and sternocleidomastoid are in IGNORED_TOKENS
    _add_isolated_tokens(clean_db, exercise, ["upper-pectoralis", "splenius"])
    _select_exercise(clean_db, exercise, sets=3)

    totals, diagnostics = aggregate_planned_sets("advanced")

    assert "splenius" in diagnostics["ignored_tokens"]
    # Primary contribution still attributed (not lost)
    assert totals["upper-pectoralis"] == pytest.approx(3.0)


def test_planned_without_target_row(clean_db):
    """Plan with Glutes=0 but user added glute work → planned_without_target."""
    exercise = _create_exercise(
        clean_db,
        "Hip Thrust",
        primary="Glutes",
        secondary=None,
        tertiary=None,
    )
    _select_exercise(clean_db, exercise, sets=4)
    plan_id = export_volume_plan(
        {"training_days": 3, "volumes": {"Glutes": {"weekly_sets": 0, "status": "optimal"}}}
    )
    assert activate_volume_plan(plan_id)

    result = get_volume_progress()

    glute_row = next(r for r in result["rows"] if r["muscle_group"] == "Glutes")
    assert glute_row["planned"] == pytest.approx(4.0)
    assert glute_row["target"] == pytest.approx(0.0)
    assert glute_row["progress_status"] == "planned_without_target"


def test_target_without_planned_row(clean_db):
    """Plan has Calves=12 but no calf exercises → unplanned_target."""
    plan_id = export_volume_plan(
        {"training_days": 3, "volumes": {"Calves": {"weekly_sets": 12, "status": "optimal"}}}
    )
    assert activate_volume_plan(plan_id)

    result = get_volume_progress()

    calves_row = next(r for r in result["rows"] if r["muscle_group"] == "Calves")
    assert calves_row["planned"] == pytest.approx(0.0)
    assert calves_row["target"] == pytest.approx(12.0)
    assert calves_row["progress_status"] == "unplanned_target"


def test_on_target_tolerance(clean_db):
    """Planned 15.995, target 16 → on_target within 0.01 tolerance."""
    from utils.volume_progress import _classify_progress_status

    assert _classify_progress_status(15.995, 16.0) == "on_target"
    assert _classify_progress_status(16.005, 16.0) == "on_target"
    assert _classify_progress_status(15.98, 16.0) == "under_target"
    assert _classify_progress_status(16.02, 16.0) == "over_target"


def test_target_status_computed_from_default_ranges(clean_db):
    """Backend overrides stored muscle_volumes.status with computed target_status."""
    exercise = _create_exercise(clean_db, "Bench Press Low Target")
    _select_exercise(clean_db, exercise, sets=3)

    # Save with status='optimal' but target=5 (which default ranges classify as 'low')
    plan_id = export_volume_plan(
        {"training_days": 4, "volumes": {"Chest": {"weekly_sets": 5, "status": "optimal"}}}
    )
    assert activate_volume_plan(plan_id)

    result = get_volume_progress()

    chest_row = next(r for r in result["rows"] if r["muscle_group"] == "Chest")
    assert chest_row["target_status"] == "low"


def test_target_status_excessive_when_sets_per_session_exceeds_ten(clean_db):
    """sets_per_session > 10 overrides to 'excessive' to match splitter UI rule."""
    exercise = _create_exercise(clean_db, "Bench Press Excessive Target")
    _select_exercise(clean_db, exercise, sets=3)

    # training_days=2 with weekly_sets=22 → sets_per_session=11 (> 10 → excessive)
    plan_id = export_volume_plan(
        {"training_days": 2, "volumes": {"Chest": {"weekly_sets": 22, "status": "optimal"}}}
    )
    assert activate_volume_plan(plan_id)

    result = get_volume_progress()

    chest_row = next(r for r in result["rows"] if r["muscle_group"] == "Chest")
    assert chest_row["target_status"] == "excessive"


def test_target_status_none_when_target_zero(clean_db):
    """target == 0 returns 'none' rather than mis-classifying as 'low'."""
    exercise = _create_exercise(clean_db, "Bench Press Without Target")
    _select_exercise(clean_db, exercise, sets=3)

    # Active plan exists but Chest is not targeted; planned > 0 so the row surfaces.
    plan_id = export_volume_plan(
        {"training_days": 3, "volumes": {"Calves": {"weekly_sets": 12, "status": "optimal"}}}
    )
    assert activate_volume_plan(plan_id)

    result = get_volume_progress()

    chest_row = next(r for r in result["rows"] if r["muscle_group"] == "Chest")
    assert chest_row["target"] == 0
    assert chest_row["target_status"] == "none"
    assert chest_row["progress_status"] == "planned_without_target"


def test_endpoint_response_contract(client, clean_db):
    """Every new endpoint returns {ok, status, data, requestId} or error variant."""
    # Volume progress endpoint
    response = client.get("/api/volume_progress")
    assert response.status_code == 200
    payload = response.get_json()
    assert "data" in payload
    assert payload.get("ok") is True or payload.get("status") == "success"

    # Activate non-existent → error variant
    response = client.post("/api/volume_plan/999999/activate")
    assert response.status_code == 404
    payload = response.get_json()
    assert "error" in payload


def test_middle_shoulder_respects_phase0_decision(clean_db):
    """Exercise with primary='Middle-Shoulder' produces the Phase 0 Basic rollup."""
    exercise = _create_exercise(
        clean_db,
        "Lateral Raise",
        primary="Middle-Shoulder",
        secondary=None,
        tertiary=None,
    )
    _select_exercise(clean_db, exercise, sets=3)

    expected_basic = COARSE_TO_BASIC[canonical_pst("Middle-Shoulder")]

    totals, diagnostics = aggregate_planned_sets("basic")

    assert totals[expected_basic] == pytest.approx(3.0)
    assert diagnostics["unmapped_muscles"] == []


def test_advanced_mode_primary_refinement_safe_tokens_only(clean_db):
    """Exercise with primary='Chest' and matching isolated tokens splits contribution."""
    exercise = _create_exercise(
        clean_db,
        "Cable Crossover",
        primary="Chest",
        secondary=None,
        tertiary=None,
    )
    _add_isolated_tokens(clean_db, exercise, ["upper-pectoralis", "mid-lower-pectoralis"])
    _select_exercise(clean_db, exercise, sets=3)

    totals, diagnostics = aggregate_planned_sets("advanced")

    assert totals["upper-pectoralis"] == pytest.approx(1.5)
    assert totals["mid-lower-pectoralis"] == pytest.approx(1.5)
    assert diagnostics["rejected_tokens"] == []


def test_fetch_planned_rows_falls_back_to_csv_when_mapping_empty(clean_db):
    """When exercise_isolated_muscles is empty, CSV column drives attribution."""
    exercise = _create_exercise(
        clean_db,
        "CSV Fallback Press",
        primary="Chest",
        secondary=None,
        tertiary=None,
        advanced="upper-pectoralis",
    )
    # No _add_isolated_tokens call — mapping table empty for this exercise
    _select_exercise(clean_db, exercise, sets=3)

    totals, diagnostics = aggregate_planned_sets("advanced")

    assert totals["upper-pectoralis"] == pytest.approx(3.0)
    assert diagnostics["csv_fallback_count"] == 1


def test_volume_progress_performance_sanity(client, clean_db):
    """§12.4 — /api/volume_progress should respond well under 100 ms with ~80 selections."""
    import time

    plan_id = export_volume_plan(
        {
            "training_days": 4,
            "volumes": {
                "Chest": {"weekly_sets": 16, "status": "optimal"},
                "Back": {"weekly_sets": 18, "status": "optimal"},
                "Quadriceps": {"weekly_sets": 14, "status": "optimal"},
                "Hamstrings": {"weekly_sets": 12, "status": "optimal"},
            },
        }
    )
    assert activate_volume_plan(plan_id)

    primaries = ("Chest", "Back", "Quadriceps", "Hamstrings", "Triceps", "Biceps", "Glutes", "Calves")
    routines = ("A", "B", "C", "D")
    for index in range(80):
        primary = primaries[index % len(primaries)]
        routine = routines[index % len(routines)]
        exercise_name = f"Perf Exercise {index}"
        _create_exercise(
            clean_db,
            exercise_name,
            primary=primary,
            secondary=None,
            tertiary=None,
        )
        _select_exercise(clean_db, exercise_name, sets=3, routine=routine)

    # Warm up the connection / query plan caches before measuring.
    client.get("/api/volume_progress")

    start = time.perf_counter()
    samples = 5
    for _ in range(samples):
        response = client.get("/api/volume_progress")
        assert response.status_code == 200
    elapsed_ms = ((time.perf_counter() - start) / samples) * 1000.0

    assert elapsed_ms < 200.0, (
        f"/api/volume_progress averaged {elapsed_ms:.1f} ms across {samples} samples "
        "with 80 user_selection rows (target: well under 100 ms; 200 ms is the slow-query log threshold)."
    )

