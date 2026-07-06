from flask import Blueprint, jsonify, request
from utils.filter_predicates import FilterPredicates
from utils.database import DatabaseHandler
from utils.errors import success_response, error_response
from utils.logger import get_logger
from utils.constants import DIFFICULTY, MECHANIC, UTILITY
# The SQL-name allowlists and validators are owned by utils.filter_registry.
# Re-exported here (unchanged names) so existing callers/tests that do
# `from routes.filters import ALLOWED_COLUMNS, validate_column_name` keep working.
from utils.filter_registry import (  # noqa: F401  (re-exported)
    ALLOWED_TABLES,
    ALLOWED_COLUMNS,
    validate_table_name,
    validate_column_name,
)

filters_bp = Blueprint('filters', __name__)
logger = get_logger()

# =============================================================================
# SIMPLE/ADVANCED VIEW MODE MUSCLE MAPPING
# =============================================================================

# Maps simple muscle keys (from frontend simple mode) to database values
# Used when filtering by primary/secondary/tertiary muscle groups
SIMPLE_TO_DB_MUSCLE = {
    # Shoulders
    'front-shoulders': ['Front-Shoulder'],
    'middle-shoulders': ['Middle-Shoulder'],
    'rear-shoulders': ['Rear-Shoulder'],
    
    # Chest
    'chest': ['Chest'],
    
    # Arms
    'biceps': ['Biceps'],
    'triceps': ['Triceps'],
    'forearms': ['Forearms'],
    
    # Core
    'abs': ['Abs/Core', 'Rectus Abdominis'],
    'obliques': ['External Obliques'],
    
    # Back
    'traps': ['Trapezius', 'Upper Traps'],
    'traps-middle': ['Middle-Traps'],
    'lats': ['Latissimus Dorsi'],
    'upper-back': ['Upper Back'],
    'lower-back': ['Lower Back'],
    
    # Lower Body
    'glutes': ['Gluteus Maximus', 'Hip-Adductors'],
    'quads': ['Quadriceps'],
    'hamstrings': ['Hamstrings'],
    'calves': ['Calves'],
}

# Maps simple muscle keys to advanced isolated muscle values (for Advanced Isolated Muscles filter)
SIMPLE_TO_ADVANCED_ISOLATED = {
    'front-shoulders': ['anterior-deltoid'],
    'middle-shoulders': ['lateral-deltoid'],
    'rear-shoulders': ['posterior-deltoid'],
    'chest': ['upper-pectoralis', 'lower-pectoralis'],
    'biceps': ['long-head-bicep', 'short-head-bicep'],
    'triceps': ['lateral-head-triceps', 'long-head-triceps', 'medial-head-triceps'],
    'forearms': ['wrist-extensors', 'wrist-flexors'],
    'abs': ['upper-abdominals', 'lower-abdominals'],
    'obliques': ['obliques'],
    'traps': ['upper-trapezius'],
    'traps-middle': [],  # No advanced breakdown
    'lower-back': [],
    'lats': [],
    'upper-back': [],
    'glutes': ['gluteus-maximus', 'gluteus-medius'],
    'quads': ['rectus-femoris', 'outer-quadricep', 'quadriceps', 'inner-thigh'],
    'hamstrings': ['lateral-hamstrings', 'medial-hamstrings'],
    'calves': ['soleus', 'gastrocnemius', 'tibialis'],
}

# Reverse mapping: Advanced/scientific muscle key → Simple parent key
# Generated from SIMPLE_TO_ADVANCED_ISOLATED
ADVANCED_TO_SIMPLE_MUSCLE = {}
for simple_key, advanced_keys in SIMPLE_TO_ADVANCED_ISOLATED.items():
    for adv_key in advanced_keys:
        ADVANCED_TO_SIMPLE_MUSCLE[adv_key] = simple_key

# Define standard filter mapping - supports both display names and snake_case keys
FILTER_MAPPING = {
    # Display names (from data-filter-key attribute)
    "Primary Muscle Group": "primary_muscle_group",
    "Secondary Muscle Group": "secondary_muscle_group",
    "Tertiary Muscle Group": "tertiary_muscle_group",
    "Advanced Isolated Muscles": "advanced_isolated_muscles",
    "Force": "force",
    "Equipment": "equipment",
    "Mechanic": "mechanic",
    "Utility": "utility",
    "Grips": "grips",
    "Stabilizers": "stabilizers",
    "Synergists": "synergists",
    "Difficulty": "difficulty",
    # Snake_case keys (from select element id fallback)
    "primary_muscle_group": "primary_muscle_group",
    "secondary_muscle_group": "secondary_muscle_group",
    "tertiary_muscle_group": "tertiary_muscle_group",
    "advanced_isolated_muscles": "advanced_isolated_muscles",
    "equipment": "equipment",
    "mechanic": "mechanic",
    "utility": "utility",
    "grips": "grips",
    "stabilizers": "stabilizers",
    "synergists": "synergists",
    "difficulty": "difficulty",
}

ENUM_VALUE_MAP = {
    'mechanic': sorted(set(MECHANIC.values())),
    'utility': sorted(set(UTILITY.values())),
    'difficulty': sorted(set(DIFFICULTY.values())),
}

def expand_simple_muscle_value(field: str, value: str) -> tuple:
    """
    Expand a simple or advanced mode muscle value to database values.
    
    Args:
        field: The database field name (primary_muscle_group, etc.)
        value: The filter value (could be simple key, advanced key, or direct DB value)
        
    Returns:
        Tuple of (expanded_values: list, is_mapped_key: bool)
    """
    # Check if this is a simple key
    if value in SIMPLE_TO_DB_MUSCLE:
        if field == 'advanced_isolated_muscles':
            # For isolated muscles, use the advanced mapping
            return SIMPLE_TO_ADVANCED_ISOLATED.get(value, [value]), True
        else:
            # For primary/secondary/tertiary, use the DB mapping
            return SIMPLE_TO_DB_MUSCLE.get(value, [value]), True
    
    # Check if this is an advanced/scientific key
    if value in ADVANCED_TO_SIMPLE_MUSCLE:
        if field == 'advanced_isolated_muscles':
            # For isolated muscles, the advanced key is the DB value
            return [value], True
        else:
            # For primary/secondary/tertiary, map advanced → simple → DB
            simple_key = ADVANCED_TO_SIMPLE_MUSCLE[value]
            return SIMPLE_TO_DB_MUSCLE.get(simple_key, [value]), True
    
    # Not a mapped key - return as-is
    return [value], False


@filters_bp.route("/filter_exercises", methods=["POST"])
def filter_exercises():
    filters = None
    try:
        filters = request.get_json()
        if not filters:
            return error_response("VALIDATION_ERROR", "No filters provided", 400)

        logger.debug(f"Received filters: {filters}")

        # Convert frontend names to database column names and expand simple values
        sanitized_filters = {}
        expanded_muscle_filters = {}  # For filters that need OR logic
        
        for key, value in filters.items():
            db_field = FILTER_MAPPING.get(key)
            
            #  NEW CODE VERIFICATION: Check if field is in mapping
            if db_field is None:
                logger.warning(f"New code guard: unknown filter field rejected: {key}")
                return error_response("VALIDATION_ERROR", f"Invalid filter column: {key}", 400)
            
            if value:  # Only include non-empty values
                # Validate column is whitelisted
                if validate_column_name(db_field):
                    # Check if this is a muscle field that might need expansion
                    if db_field in ('primary_muscle_group', 'secondary_muscle_group', 
                                    'tertiary_muscle_group', 'advanced_isolated_muscles'):
                        expanded_values, is_simple = expand_simple_muscle_value(db_field, value)
                        if is_simple and len(expanded_values) > 1:
                            # Multiple values - store for special handling
                            expanded_muscle_filters[db_field] = expanded_values
                        elif is_simple and len(expanded_values) == 1:
                            # Single expanded value
                            sanitized_filters[db_field] = expanded_values[0]
                        elif is_simple and len(expanded_values) == 0:
                            # No mapping (like traps-middle with no advanced breakdown)
                            # Skip this filter as it won't match anything
                            continue
                        else:
                            sanitized_filters[db_field] = value
                    else:
                        sanitized_filters[db_field] = value
                else:
                    logger.warning(f"Invalid column in filter: {db_field}")
                    return error_response("VALIDATION_ERROR", f"Invalid filter column: {key}", 400)

        logger.debug(f"Sanitized filters: {sanitized_filters}")
        logger.debug(f"Expanded muscle filters: {expanded_muscle_filters}")
        
        # Build custom query if we have expanded muscle filters
        if expanded_muscle_filters:
            exercise_names = filter_exercises_with_expanded_muscles(
                sanitized_filters, expanded_muscle_filters
            )
        else:
            # Apply filters and get results
            exercise_names = FilterPredicates.get_exercises(filters=sanitized_filters)
        
        logger.info(
            "Exercises filtered",
            extra={
                'filter_count': len(sanitized_filters) + len(expanded_muscle_filters),
                'filter_fields': list(sanitized_filters.keys()) + list(expanded_muscle_filters.keys()),
                'result_count': len(exercise_names)
            }
        )

        return jsonify(success_response(data=exercise_names))
    except Exception as e:
        logger.exception(
            "Error filtering exercises",
            extra={'filter_count': len(filters) if filters else 0}
        )
        return error_response("INTERNAL_ERROR", "Failed to filter exercises", 500)


def filter_exercises_with_expanded_muscles(
    single_filters: dict, 
    multi_value_filters: dict
) -> list:
    """
    Filter exercises with support for multiple values per muscle field (OR logic).
    
    Args:
        single_filters: Filters with single values
        multi_value_filters: Muscle filters with multiple values (OR logic needed)
        
    Returns:
        List of matching exercise names
    """
    query = "SELECT exercise_name FROM exercises WHERE 1=1"
    params = []
    
    # Add single filters (AND logic)
    for field, value in single_filters.items():
        if field == 'advanced_isolated_muscles':
            query += """
                AND EXISTS (
                    SELECT 1 FROM exercise_isolated_muscles m
                    WHERE m.exercise_name = exercises.exercise_name
                    AND m.muscle LIKE ?
                )
            """
            params.append(f"%{value}%")
        elif field in ('primary_muscle_group', 'secondary_muscle_group', 'tertiary_muscle_group'):
            query += f" AND {field} LIKE ?"
            params.append(f"%{value}%")
        else:
            query += f" AND LOWER({field}) = LOWER(?)"
            params.append(value)
    
    # Add multi-value muscle filters (OR within each field)
    for field, values in multi_value_filters.items():
        if not values:
            continue
            
        if field == 'advanced_isolated_muscles':
            # Build OR conditions for isolated muscles
            or_conditions = []
            for val in values:
                or_conditions.append("""
                    EXISTS (
                        SELECT 1 FROM exercise_isolated_muscles m
                        WHERE m.exercise_name = exercises.exercise_name
                        AND m.muscle LIKE ?
                    )
                """)
                params.append(f"%{val}%")
            query += f" AND ({' OR '.join(or_conditions)})"
        else:
            # Build OR conditions for muscle group columns
            or_conditions = []
            for val in values:
                or_conditions.append(f"{field} LIKE ?")
                params.append(f"%{val}%")
            query += f" AND ({' OR '.join(or_conditions)})"
    
    query += " ORDER BY exercise_name ASC"
    
    try:
        with DatabaseHandler() as db:
            results = db.fetch_all(query, params if params else None)
            if not results:
                return []
            # Handle dict rows (Row objects from sqlite3)
            if isinstance(results[0], dict):
                return [row["exercise_name"] for row in results if row.get("exercise_name")]
            # Handle tuple rows
            return [str(row[0]) for row in results if row[0]]  # type: ignore[index]
    except Exception as e:
        logger.exception("Error in filter_exercises_with_expanded_muscles")
        return []

@filters_bp.route("/get_all_exercises")
def get_all_exercises():
    """Get all exercises without any filters."""
    try:
        exercise_names = FilterPredicates.get_exercises()
        return jsonify(success_response(data=exercise_names))
    except Exception as e:
        logger.exception("Error in get_all_exercises")
        return error_response("INTERNAL_ERROR", "Failed to fetch exercises", 500) 

@filters_bp.route("/get_unique_values/<table>/<column>")
def get_unique_values(table, column):
    """Get unique values for a given column in a table."""
    try:
        # Validate table and column names against whitelist
        if not validate_table_name(table):
            logger.warning(f"Invalid table name: {table}")
            return error_response("VALIDATION_ERROR", f"Invalid table: {table}", 400)
        
        if not validate_column_name(column):
            logger.warning(f"Invalid column name: {column}")
            return error_response("VALIDATION_ERROR", f"Invalid column: {column}", 400)
        
        # Get safe table and column names from whitelist
        safe_table = ALLOWED_TABLES.get(table.lower())
        safe_column = ALLOWED_COLUMNS.get(column.lower())
        
        if not safe_table or not safe_column:
            return error_response("VALIDATION_ERROR", "Invalid table or column", 400)
        
        # Use parameterized query with safe names
        with DatabaseHandler() as db:
            if safe_table == 'exercises' and safe_column == 'advanced_isolated_muscles':
                records = db.fetch_all(
                    "SELECT DISTINCT muscle FROM exercise_isolated_muscles ORDER BY muscle"
                )
                values = [row['muscle'] for row in records]
                return jsonify(success_response(data=values))

            if safe_column in ENUM_VALUE_MAP:
                return jsonify(success_response(data=ENUM_VALUE_MAP[safe_column]))

            # Force column: query DB and normalize to title case to merge variants
            if safe_column == 'force':
                query = (
                    f"SELECT DISTINCT {safe_column} AS value FROM {safe_table} "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY {safe_column}"
                )
                rows = db.fetch_all(query)
                # Normalize to title case and dedupe (merges 'push'/'Push', 'pull'/'Pull')
                seen = set()
                values = []
                for row in rows:
                    val = row['value']
                    if val:
                        normalized = val.strip().title()
                        if normalized not in seen:
                            seen.add(normalized)
                            values.append(normalized)
                return jsonify(success_response(data=sorted(values)))

            if safe_column in {
                'primary_muscle_group',
                'secondary_muscle_group',
                'tertiary_muscle_group',
            }:
                query = (
                    f"SELECT DISTINCT {safe_column} AS value FROM {safe_table} "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY {safe_column}"
                )
                rows = db.fetch_all(query)
                values = [row['value'] for row in rows]
                return jsonify(success_response(data=values))

            if safe_column == 'equipment':
                query = (
                    f"SELECT DISTINCT TRIM({safe_column}) AS value FROM {safe_table} "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY value"
                )
                rows = db.fetch_all(query)
                values = [row['value'] for row in rows if row.get('value')]
                return jsonify(success_response(data=values))

            query = (
                f"SELECT DISTINCT {safe_column} AS value FROM {safe_table} "
                f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                f"ORDER BY {safe_column}"
            )
            results = db.fetch_all(query)
            values = [row['value'] for row in results if row.get('value')]
            return jsonify(success_response(data=values))
    except Exception as e:
        logger.exception(f"Error fetching unique values for {table}.{column}")
        return error_response("INTERNAL_ERROR", "Failed to fetch unique values", 500) 

@filters_bp.route("/get_filtered_exercises", methods=["POST"])
def get_filtered_exercises():
    """Get exercises based on multiple filter criteria."""
    try:
        filters = request.get_json()
        if not filters:
            return error_response("VALIDATION_ERROR", "No filters provided", 400)
        
        query = """
        SELECT exercise_name
        FROM exercises
        WHERE 1=1
        """
        params = []
        
        for field, value in filters.items():
            # Validate column name is whitelisted
            if not validate_column_name(field):
                logger.warning(f"Invalid column in filter: {field}")
                return error_response("VALIDATION_ERROR", f"Invalid filter column: {field}", 400)
            
            if value:
                safe_column = ALLOWED_COLUMNS.get(field.lower())
                # Special handling for advanced_isolated_muscles - use mapping table
                if safe_column == "advanced_isolated_muscles":
                    query += """
                        AND EXISTS (
                            SELECT 1
                            FROM exercise_isolated_muscles m
                            WHERE m.exercise_name = exercises.exercise_name
                              AND m.muscle LIKE ?
                        )
                    """
                    params.append(f"%{value}%")
                else:
                    query += f" AND {safe_column} LIKE ?"
                    params.append(f"%{value}%")
                
        query += " ORDER BY exercise_name ASC"
        
        with DatabaseHandler() as db:
            results = db.fetch_all(query, params)
            exercises = [row['exercise_name'] for row in results]
            return jsonify(success_response(data=exercises))
    except Exception as e:
        logger.exception("Error filtering exercises")
        return error_response("INTERNAL_ERROR", "Failed to filter exercises", 500) 