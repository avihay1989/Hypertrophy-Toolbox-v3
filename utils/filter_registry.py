"""Central filter allowlist and table/column validators.

Single owner of the SQL-name safety whitelists used for dynamic table/column
interpolation by the filter routes (`/get_unique_values/<table>/<column>`,
`/get_filtered_exercises`) and by `routes.workout_plan.fetch_unique_values`.
`routes.filters` re-exports `ALLOWED_TABLES`, `ALLOWED_COLUMNS`,
`validate_table_name`, and `validate_column_name` from here so existing callers
and tests (`from routes.filters import ALLOWED_COLUMNS, validate_column_name`)
keep working unchanged.

Relationship to ``FilterPredicates.VALID_FILTER_FIELDS`` (do NOT union them)
---------------------------------------------------------------------------
These two vocabularies are intentionally different and serve different purposes:

* ``ALLOWED_COLUMNS`` is the **SQL-injection safety whitelist** — every column
  name that may be interpolated into a dynamic ``SELECT``. It spans exercises
  columns *and* ``user_selection`` columns (``routine``, ``sets``, ``weight`` …)
  plus ``exercise_name``. Its job is to make dynamic identifiers safe, not to
  define what is filterable.
* ``FilterPredicates.VALID_FILTER_FIELDS`` is the set of fields the exercise
  **filter-predicate builder** accepts. It is the exercises filter columns
  (``EXERCISES_FILTER_COLUMNS`` below) **plus** the virtual field
  ``target_muscles`` (a computed/mapped filter with no physical ``exercises``
  column) and **minus** ``exercise_name`` and the ``user_selection`` columns
  (queryable, but not exercise filters).

The grouping frozensets below encode these intentional differences explicitly so
that vocabulary drift is caught by the parity tests in
``tests/test_filter_registry.py`` rather than silently papered over by a union.
"""

# Whitelist for safe table names (prevents SQL injection).
ALLOWED_TABLES = {
    'exercises': 'exercises',
    'user_selection': 'user_selection',
    'workout_log': 'workout_log',
    'progression_goals': 'progression_goals',
}

# Whitelist for safe column names (prevents SQL injection).
ALLOWED_COLUMNS = {
    # Exercises table columns
    'primary_muscle_group': 'primary_muscle_group',
    'secondary_muscle_group': 'secondary_muscle_group',
    'tertiary_muscle_group': 'tertiary_muscle_group',
    'advanced_isolated_muscles': 'advanced_isolated_muscles',
    'force': 'force',
    'equipment': 'equipment',
    'mechanic': 'mechanic',
    'utility': 'utility',
    'grips': 'grips',
    'stabilizers': 'stabilizers',
    'synergists': 'synergists',
    'difficulty': 'difficulty',
    'exercise_name': 'exercise_name',
    # User selection columns
    'routine': 'routine',
    'exercise': 'exercise',
    'sets': 'sets',
    'min_rep_range': 'min_rep_range',
    'max_rep_range': 'max_rep_range',
    'rir': 'rir',
    'rpe': 'rpe',
    'weight': 'weight',
}


def validate_table_name(table: str) -> bool:
    """Validate that table name is in the whitelist (case-insensitive)."""
    return table.lower() in {k.lower(): v for k, v in ALLOWED_TABLES.items()}


def validate_column_name(column: str) -> bool:
    """Validate that column name is in the whitelist (case-insensitive)."""
    return column.lower() in {k.lower(): v for k, v in ALLOWED_COLUMNS.items()}


# ---------------------------------------------------------------------------
# Explicit reconciliation with FilterPredicates.VALID_FILTER_FIELDS.
# These are documentation + parity-test anchors, not a second source of truth
# for the allowlist above. See the module docstring.
# ---------------------------------------------------------------------------

# Exercises columns that are also exercise filter fields (the overlap between
# ALLOWED_COLUMNS and VALID_FILTER_FIELDS).
EXERCISES_FILTER_COLUMNS = frozenset({
    'primary_muscle_group',
    'secondary_muscle_group',
    'tertiary_muscle_group',
    'advanced_isolated_muscles',
    'force',
    'equipment',
    'mechanic',
    'utility',
    'grips',
    'stabilizers',
    'synergists',
    'difficulty',
})

# Virtual filter field(s): valid for filtering but with no physical exercises
# column, so intentionally absent from ALLOWED_COLUMNS.
VIRTUAL_FILTER_FIELDS = frozenset({'target_muscles'})

# Columns that are safe to query but are NOT exercise filter fields
# (exercise_name plus the user_selection columns).
NON_FILTER_ALLOWED_COLUMNS = frozenset({
    'exercise_name',
    'routine',
    'exercise',
    'sets',
    'min_rep_range',
    'max_rep_range',
    'rir',
    'rpe',
    'weight',
})
