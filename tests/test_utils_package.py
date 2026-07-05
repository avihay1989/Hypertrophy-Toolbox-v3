"""Boundary tests for the intentionally empty :mod:`utils` package facade."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_importing_utils_does_not_restore_the_legacy_facade():
    repo_root = Path(__file__).resolve().parents[1]
    script = """
import sys

sys.path.insert(0, '.')
import utils

legacy_exports = {
    'DB_FILE',
    'DatabaseHandler',
    'initialize_database',
    'get_exercises',
    'add_exercise',
    'delete_exercise',
    'fetch_unique_values',
    'save_exercise',
    'remove_exercise_by_name',
    'calculate_weekly_summary',
    'calculate_session_summary',
    'calculate_exercise_categories',
    'calculate_isolated_muscles_stats',
    'get_volume_class',
    'get_volume_label',
    'get_volume_tooltip',
    'get_category_tooltip',
    'get_subcategory_tooltip',
    'check_progression',
    'generate_starter_plan',
}
legacy_modules = {
    'utils.config',
    'utils.database',
    'utils.db_initializer',
    'utils.exercise_manager',
    'utils.plan_generator',
    'utils.session_summary',
    'utils.volume_classifier',
    'utils.weekly_summary',
    'utils.workout_log',
}

assert legacy_exports.isdisjoint(vars(utils))
assert legacy_modules.isdisjoint(sys.modules)
assert not hasattr(utils, '__all__')
"""

    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
