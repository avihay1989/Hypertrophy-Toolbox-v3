"""Behavior contracts for the WP2.2 plan-generator decomposition."""

import pytest

import utils.plan_generator as plan_generator
from utils.movement_patterns import MovementPattern, MovementSubpattern, SlotDefinition
from utils.plan_generator import (
    ExerciseRow,
    ExerciseSelector,
    GeneratedPlan,
    GeneratorConfig,
    PlanGenerator,
)


def _exercise_row(name: str, order: int) -> ExerciseRow:
    return ExerciseRow(
        routine="Routine A",
        exercise=name,
        sets=3,
        min_rep_range=8,
        max_rep_range=12,
        rir=2,
        rpe=8.0,
        weight=20.0,
        exercise_order=order,
        pattern=MovementPattern.SQUAT.value,
        role="main",
    )


def test_score_exercise_preserves_component_order_and_values(monkeypatch):
    config = GeneratorConfig(
        preferred_exercises={MovementPattern.SQUAT.value: ["Back Squat"]},
    )
    selector = ExerciseSelector(config)
    selector._used_exercises.add("Back Squat")
    slot = SlotDefinition(
        MovementPattern.SQUAT,
        "main",
        MovementSubpattern.BILATERAL_SQUAT,
    )
    exercise = {
        "exercise_name": "Back Squat",
        "movement_pattern": MovementPattern.SQUAT.value,
        "movement_subpattern": MovementSubpattern.BILATERAL_SQUAT.value,
        "utility": "Basic",
        "mechanic": "Compound",
    }
    monkeypatch.setattr(plan_generator.random, "uniform", lambda _low, _high: 0)

    assert selector._score_exercise(exercise, slot, "Routine A") == 220


def test_score_exercise_non_match_skips_random_tie_break(monkeypatch):
    selector = ExerciseSelector(GeneratorConfig())
    slot = SlotDefinition(MovementPattern.SQUAT, "main")
    exercise = {
        "exercise_name": "Barbell Bench Press",
        "movement_pattern": MovementPattern.HORIZONTAL_PUSH.value,
        "primary_muscle_group": "Chest",
        "mechanic": "Compound",
    }

    def fail_if_called(_low, _high):
        raise AssertionError("non-matches must return before the random tie-break")

    monkeypatch.setattr(plan_generator.random, "uniform", fail_if_called)

    assert selector._score_exercise(exercise, slot, "Routine A") == -1000


def test_priority_boost_preserves_accessory_first_allocation(monkeypatch):
    config = GeneratorConfig(priority_muscles=["chest"])
    generator = PlanGenerator(config)
    chest_accessory = ExerciseRow(
        "Routine A",
        "Chest Fly",
        3,
        8,
        12,
        2,
        8.0,
        10.0,
        1,
        MovementPattern.UPPER_ISOLATION.value,
        "accessory",
    )
    chest_main = ExerciseRow(
        "Routine A",
        "Bench Press",
        4,
        6,
        10,
        2,
        8.0,
        40.0,
        2,
        MovementPattern.HORIZONTAL_PUSH.value,
        "main",
    )
    routines = {"Routine A": [chest_accessory, chest_main]}
    monkeypatch.setattr(
        generator,
        "_exercise_targets_priority_muscle",
        lambda name, _muscles: name in {"Chest Fly", "Bench Press"},
    )

    assert generator._apply_priority_muscle_boost(routines) is routines
    assert chest_accessory.sets == 4
    assert chest_main.sets == 4


def test_persist_logs_row_failure_and_continues_with_next_order(monkeypatch):
    class RecordingDB:
        def __init__(self):
            self.insert_orders = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def fetch_one(self, query, params=()):
            assert "MAX(exercise_order)" in query
            return {"max_order": 10}

        def execute_query(self, query, params=()):
            if "INSERT INTO user_selection" not in query:
                return None
            self.insert_orders.append(params[-1])
            if params[1] == "Broken Exercise":
                raise RuntimeError("row insert failed")
            return None

    db = RecordingDB()
    monkeypatch.setattr(plan_generator, "DatabaseHandler", lambda: db)
    config = GeneratorConfig(persist=True, overwrite=True)
    generator = PlanGenerator(config)
    plan = GeneratedPlan(
        routines={
            "Routine A": [
                _exercise_row("Broken Exercise", 1),
                _exercise_row("Working Exercise", 2),
            ]
        },
        config=config,
    )

    assert generator.persist(plan) == {"Routine A": 1}
    assert db.insert_orders == [11, 12]


def test_persist_reraises_failure_outside_individual_row_insert(monkeypatch):
    class FailingDB:
        def __enter__(self):
            raise RuntimeError("database unavailable")

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(plan_generator, "DatabaseHandler", FailingDB)
    config = GeneratorConfig(persist=True)
    generator = PlanGenerator(config)
    plan = GeneratedPlan(routines={}, config=config)

    with pytest.raises(RuntimeError, match="database unavailable"):
        generator.persist(plan)


def test_persistence_result_keeps_public_error_shape(monkeypatch):
    config = GeneratorConfig(persist=True)
    generator = PlanGenerator(config)
    plan = GeneratedPlan(routines={}, config=config)
    result = {}

    def fail_persistence(_plan):
        raise RuntimeError("write failed")

    monkeypatch.setattr(generator, "persist", fail_persistence)

    plan_generator._add_persistence_result(
        generator,
        plan,
        result,
        should_persist=True,
    )

    assert result == {"persisted": False, "persist_error": "write failed"}
