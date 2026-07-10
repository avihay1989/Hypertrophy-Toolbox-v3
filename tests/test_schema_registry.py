"""Contracts for the canonical schema initializer and owned-table registry."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from routes import workout_plan
from utils import schema_registry


def test_run_all_initializers_preserves_startup_order(monkeypatch):
    calls = []

    def record_base(*, force):
        calls.append(("initialize_database", force))

    monkeypatch.setattr(schema_registry, "initialize_database", record_base)
    for name in (
        "add_progression_goals_table",
        "add_volume_tracking_tables",
        "add_user_profile_tables",
        "add_body_composition_snapshots_table",
        "add_strength_calibration_tables",
        "add_fatigue_context_settings_table",
        "initialize_exercise_order",
        "initialize_backup_tables",
    ):
        monkeypatch.setattr(
            schema_registry,
            name,
            lambda name=name: calls.append((name, None)),
        )

    schema_registry.run_all_initializers(force_base=True)

    assert calls == [
        ("initialize_database", True),
        ("add_progression_goals_table", None),
        ("add_volume_tracking_tables", None),
        ("add_user_profile_tables", None),
        ("add_body_composition_snapshots_table", None),
        ("add_strength_calibration_tables", None),
        ("add_fatigue_context_settings_table", None),
        ("initialize_exercise_order", None),
        ("initialize_backup_tables", None),
    ]


def test_run_all_initializers_defaults_to_non_forced_base(monkeypatch):
    force_values = []
    monkeypatch.setattr(
        schema_registry,
        "initialize_database",
        lambda *, force: force_values.append(force),
    )
    for name in (
        "add_progression_goals_table",
        "add_volume_tracking_tables",
        "add_user_profile_tables",
        "add_body_composition_snapshots_table",
        "add_strength_calibration_tables",
        "add_fatigue_context_settings_table",
        "initialize_exercise_order",
        "initialize_backup_tables",
    ):
        monkeypatch.setattr(schema_registry, name, lambda: None)

    schema_registry.run_all_initializers()

    assert force_values == [False]


def test_run_all_initializers_propagates_backup_table_failure(monkeypatch):
    for name in (
        "initialize_database",
        "add_progression_goals_table",
        "add_volume_tracking_tables",
        "add_user_profile_tables",
        "add_body_composition_snapshots_table",
        "add_strength_calibration_tables",
        "add_fatigue_context_settings_table",
        "initialize_exercise_order",
    ):
        if name == "initialize_database":
            monkeypatch.setattr(schema_registry, name, lambda *, force: None)
        else:
            monkeypatch.setattr(schema_registry, name, lambda: None)

    def fail_backup_initialization():
        raise RuntimeError("backup DDL failed")

    monkeypatch.setattr(
        schema_registry,
        "initialize_backup_tables",
        fail_backup_initialization,
    )

    with pytest.raises(RuntimeError, match="backup DDL failed"):
        schema_registry.run_all_initializers()


def test_drop_all_owned_tables_uses_fk_safe_registry_order():
    db = MagicMock()
    expected_order = (
        "program_backup_items",
        "program_backups",
        "ignored_calibration_transfers",
        "exercise_transfer_ratios",
        "learned_strength_calibrations",
        "user_calibration_settings",
        "fatigue_context_settings",
        "user_profile_preferences",
        "user_profile_lifts",
        "user_profile",
        "body_composition_snapshots",
        "user_selection",
        "progression_goals",
        "muscle_volumes",
        "volume_plans",
        "workout_log",
    )

    schema_registry.drop_all_owned_tables(db)

    assert schema_registry.OWNED_TABLES_DROP_ORDER == expected_order
    assert [call.args[0] for call in db.execute_query.call_args_list] == [
        f"DROP TABLE IF EXISTS {table}"
        for table in expected_order
    ]
    assert "exercises" not in expected_order
    assert "exercise_isolated_muscles" not in expected_order


def test_workout_plan_keeps_schema_helper_reexports():
    assert workout_plan.column_exists is schema_registry.column_exists
    assert workout_plan.table_exists is schema_registry.table_exists
    assert workout_plan.initialize_exercise_order is schema_registry.initialize_exercise_order
