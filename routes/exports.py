from flask import Blueprint, request
from utils.database import DatabaseHandler
from utils.export_utils import (
    create_excel_workbook,
    generate_timestamped_filename,
    stream_excel_response,
    MAX_EXPORT_ROWS
)
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
    calculate_weekly_summary
)
from utils.errors import error_response, success_response
from utils.logger import get_logger

exports_bp = Blueprint('exports', __name__)
logger = get_logger()

# Muscle name mapping from database values to scientific/advanced display names
# Matches the DB_TO_ADVANCED mapping in filter-view-mode.js
DB_TO_ADVANCED_MUSCLE = {
    # Shoulders
    'Front-Shoulder': 'Anterior Deltoid',
    'Middle-Shoulder': 'Lateral Deltoid',
    'Rear-Shoulder': 'Posterior Deltoid',
    'Shoulders': 'Anterior Deltoid',
    
    # Chest
    'Chest': 'Upper / Lower Pectoralis',
    'Upper Chest': 'Upper Pectoralis',
    'Lower Pectoralis': 'Lower Pectoralis',
    'Upper Pectoralis': 'Upper Pectoralis',
    
    # Arms
    'Biceps': 'Long / Short Head Bicep',
    'Long Head Bicep': 'Long Head Bicep',
    'Short Head Bicep': 'Short Head Bicep',
    'Triceps': 'Lateral / Long / Medial Head Triceps',
    'Lateral Head Triceps': 'Lateral Head Triceps',
    'Long Head Triceps': 'Long Head Triceps',
    'Medial Head Triceps': 'Medial Head Triceps',
    'Forearms': 'Wrist Flexors / Extensors',
    'Wrist Flexors': 'Wrist Flexors',
    'Wrist Extensors': 'Wrist Extensors',
    
    # Core
    'Abs/Core': 'Upper / Lower Abdominals',
    'Core': 'Upper / Lower Abdominals',
    'Rectus Abdominis': 'Upper / Lower Abdominals',
    'External Obliques': 'Obliques',
    'Obliques': 'Obliques',
    
    # Back
    'Trapezius': 'Upper / Lower Trapezius',
    'Upper Traps': 'Upper Trapezius',
    'Middle-Traps': 'Lower Trapezius',
    'Latissimus Dorsi': 'Latissimus Dorsi',
    'Lats': 'Latissimus Dorsi',
    'Upper Back': 'Upper Back',
    'Lower Back': 'Lower Back',
    'Erectors': 'Lower Back',
    
    # Lower Body
    'Gluteus Maximus': 'Gluteus Maximus',
    'Glutes': 'Gluteus Maximus / Medius',
    'Hip-Adductors': 'Inner Thigh',
    'Quadriceps': 'Rectus Femoris / Outer Quadricep',
    'Hamstrings': 'Lateral / Medial Hamstrings',
    'Calves': 'Gastrocnemius / Soleus',
    'Gastrocnemius': 'Gastrocnemius',
    'Soleus': 'Soleus',
    
    # Misc
    'Neck': 'Neck',
    'Serratus': 'Serratus Anterior',
}

# Columns that contain muscle names and should be transformed in advanced view
MUSCLE_COLUMNS = ['primary_muscle_group', 'secondary_muscle_group', 'tertiary_muscle_group']

# Column configuration for export matching UI table order
# Maps database column names to display names for each view mode
WORKOUT_PLAN_COLUMNS = {
    # Column order matching UI table (excluding non-exportable columns like checkbox, actions)
    'order': [
        'routine',
        'exercise', 
        'primary_muscle_group',
        'secondary_muscle_group',
        'tertiary_muscle_group',
        'advanced_isolated_muscles',
        'utility',
        'movement_pattern',
        'movement_subpattern',
        'sets',
        'min_rep_range',
        'max_rep_range',
        'rir',
        'rpe',
        'weight',
        'execution_style',
        'grips',
        'stabilizers',
        'synergists',
        'superset_group',
        'exercise_order',
    ],
    # Display names for simple view (user-friendly)
    'simple': {
        'routine': 'Routine',
        'exercise': 'Exercise',
        'primary_muscle_group': 'Primary Muscle',
        'secondary_muscle_group': 'Secondary Muscle',
        'tertiary_muscle_group': 'Tertiary Muscle',
        'advanced_isolated_muscles': 'Isolated Muscles',
        'utility': 'Utility',
        'movement_pattern': 'Movement Pattern',
        'movement_subpattern': 'Movement Subpattern',
        'sets': 'Sets',
        'min_rep_range': 'Min Rep',
        'max_rep_range': 'Max Rep',
        'rir': 'RIR',
        'rpe': 'RPE',
        'weight': 'Weight',
        'execution_style': 'Style',
        'grips': 'Grips',
        'stabilizers': 'Stabilizers',
        'synergists': 'Synergists',
        'superset_group': 'Superset Group',
        'exercise_order': 'Exercise Order',
    },
    # Display names for advanced/scientific view
    'advanced': {
        'routine': 'Routine',
        'exercise': 'Exercise',
        'primary_muscle_group': 'Primary Muscle Group',
        'secondary_muscle_group': 'Secondary Muscle Group',
        'tertiary_muscle_group': 'Tertiary Muscle Group',
        'advanced_isolated_muscles': 'Advanced Isolated Muscles',
        'utility': 'Utility',
        'movement_pattern': 'Movement Pattern',
        'movement_subpattern': 'Movement Subpattern',
        'sets': 'Sets',
        'min_rep_range': 'Min Rep Range',
        'max_rep_range': 'Max Rep Range',
        'rir': 'RIR',
        'rpe': 'RPE',
        'weight': 'Weight',
        'execution_style': 'Execution Style',
        'grips': 'Grips',
        'stabilizers': 'Stabilizers',
        'synergists': 'Synergists',
        'superset_group': 'Superset Group',
        'exercise_order': 'Exercise Order',
    }
}


def _weekly_summary_to_rows(summary_dict):
    """Convert weekly summary dict {muscle: stats} to list of row dicts for export."""
    if isinstance(summary_dict, list):
        return summary_dict
    return [
        {"muscle_group": muscle, **stats}
        for muscle, stats in summary_dict.items()
    ]


def transform_muscle_value(value, view_mode):
    """
    Transform a muscle name value based on view mode.
    
    In advanced mode, transforms simple names like 'Chest' to scientific names
    like 'Upper / Lower Pectoralis'.
    
    Args:
        value: The muscle name value from the database
        view_mode: 'simple' or 'advanced'
        
    Returns:
        Transformed value (or original if no transformation needed)
    """
    if view_mode != 'advanced' or not value:
        return value
    
    return DB_TO_ADVANCED_MUSCLE.get(value, value)


def reorder_and_rename_columns(data, column_config, view_mode='simple'):
    """
    Reorder columns to match UI table order and rename based on view mode.
    Also transforms muscle name values in advanced mode.
    
    Args:
        data: List of row dictionaries from database
        column_config: Configuration dict with 'order' and view mode mappings
        view_mode: 'simple' or 'advanced'
        
    Returns:
        List of row dictionaries with columns reordered and renamed
    """
    if not data:
        return data
    
    column_order = column_config['order']
    display_names = column_config.get(view_mode, column_config.get('simple', {}))
    
    reordered_data = []
    for row in data:
        new_row = {}
        for col in column_order:
            if col in row:
                display_name = display_names.get(col, col)
                value = row[col]
                # Transform muscle values in advanced mode
                if col in MUSCLE_COLUMNS:
                    value = transform_muscle_value(value, view_mode)
                new_row[display_name] = value
        # Add any remaining columns not in the defined order (at the end)
        for key, value in row.items():
            display_name = display_names.get(key, key)
            if display_name not in new_row and key not in ['id', 'sort_order']:
                new_row[display_name] = value
        reordered_data.append(new_row)
    
    return reordered_data

# Removed verbose before_request logging - using logger only

def calculate_volume_for_category(category, muscle_group):
    """Calculate total volume for a muscle group category."""
    try:
        with DatabaseHandler() as db:
            query = """
            SELECT SUM(scored_weight * scored_max_reps * planned_sets) as total_volume
            FROM workout_log wl
            JOIN exercises e ON wl.exercise = e.exercise_name
            WHERE (
                e.primary_muscle_group = ? 
                OR e.secondary_muscle_group = ?
                OR e.tertiary_muscle_group = ?
                OR EXISTS (
                    SELECT 1
                    FROM exercise_isolated_muscles m
                    WHERE m.exercise_name = e.exercise_name
                      AND m.muscle = ?
                )
            )
            AND scored_weight IS NOT NULL
            AND scored_max_reps IS NOT NULL
            AND planned_sets IS NOT NULL
            """
            result = db.fetch_one(query, (muscle_group, muscle_group, muscle_group, muscle_group))
            return result['total_volume'] if result and result['total_volume'] else 0
    except Exception as e:
        logger.exception("Error calculating volume for muscle_group=%s: %s", muscle_group, e)
        return 0

def calculate_frequency_for_category(category, muscle_group):
    """Calculate training frequency for a muscle group category."""
    try:
        with DatabaseHandler() as db:
            query = """
            SELECT COUNT(DISTINCT date(created_at)) as frequency
            FROM workout_log wl
            JOIN exercises e ON wl.exercise = e.exercise_name
            WHERE (
                e.primary_muscle_group = ? 
                OR e.secondary_muscle_group = ?
                OR e.tertiary_muscle_group = ?
                OR EXISTS (
                    SELECT 1
                    FROM exercise_isolated_muscles m
                    WHERE m.exercise_name = e.exercise_name
                      AND m.muscle = ?
                )
            )
            AND created_at >= date('now', '-7 days')
            """
            result = db.fetch_one(query, (muscle_group, muscle_group, muscle_group, muscle_group))
            return result['frequency'] if result and result['frequency'] else 0
    except Exception as e:
        logger.exception("Error calculating frequency for muscle_group=%s: %s", muscle_group, e)
        return 0

# Test route to verify blueprint is working
# Test route removed - no longer needed

def _recalculate_exercise_order(db):
    """Check dataset state and recalculate sequential order if needed."""
    from routes.workout_plan import column_exists
    if not column_exists(db, 'user_selection', 'exercise_order'):
        return
        
    # Check current state of exercise_order
    total_check = db.fetch_one("SELECT COUNT(*) as count FROM user_selection")
    order_check = db.fetch_one("SELECT COUNT(DISTINCT exercise_order) as distinct_count, COUNT(*) as total_count FROM user_selection WHERE exercise_order IS NOT NULL")
    
    # Recalculate if all values are the same (like all "1") or NULL
    needs_recalc = False
    if total_check and total_check['count'] > 0:
        if order_check and order_check['distinct_count'] == 1:
            logger.info(f"All exercise_order values are the same ({order_check['distinct_count']} distinct). Recalculating...")
            needs_recalc = True
        elif order_check and order_check['total_count'] < total_check['count']:
            logger.info(f"Some exercise_order values are NULL. Initializing...")
            needs_recalc = True
    
    if needs_recalc:
        logger.info(f"Recalculating exercise_order for {total_check['count']} rows")
        ordered_rows = db.fetch_all("""
            SELECT id FROM user_selection 
            ORDER BY routine, exercise, id
        """)
        logger.info(f"Found {len(ordered_rows)} rows to update")
        
        # Semantic change: N+1 update loop changed to atomic batch.
        # This changes behavior from partial-success logging per-row to all-or-nothing batch update.
        batch_params = [(index, row['id']) for index, row in enumerate(ordered_rows, start=1)]
        try:
            db.executemany(
                "UPDATE user_selection SET exercise_order = ? WHERE id = ?",
                batch_params
            )
            updated_count = len(batch_params)
        except Exception as e:
            logger.error(f"Error performing batch update for exercise_order: {e}")
            updated_count = 0
        
        verify = db.fetch_one("SELECT COUNT(DISTINCT exercise_order) as distinct_count FROM user_selection WHERE exercise_order IS NOT NULL")
        logger.info(f"exercise_order recalculated: {updated_count} rows updated, {verify['distinct_count'] if verify else 0} distinct values")


def _build_export_query(db):
    """Build the SQL query for the user selection export based on available columns."""
    from routes.workout_plan import column_exists
    has_superset = column_exists(db, 'user_selection', 'superset_group')
    has_order = column_exists(db, 'user_selection', 'exercise_order')
    
    if has_superset and has_order:
        return """
            WITH superset_min_order AS (
                SELECT superset_group, routine, MIN(exercise_order) as min_order
                FROM user_selection
                WHERE superset_group IS NOT NULL
                GROUP BY superset_group, routine
            )
            SELECT 
                us.routine, us.exercise, e.primary_muscle_group, e.secondary_muscle_group,
                e.tertiary_muscle_group, e.advanced_isolated_muscles, e.utility,
                e.movement_pattern, e.movement_subpattern, us.sets, us.min_rep_range,
                us.max_rep_range, us.rir, us.rpe, us.weight, us.execution_style,
                e.grips, e.stabilizers, e.synergists, us.superset_group, us.exercise_order,
                CASE WHEN us.superset_group IS NOT NULL THEN smo.min_order ELSE us.exercise_order END as sort_order
            FROM user_selection us
            LEFT JOIN exercises e ON us.exercise = e.exercise_name
            LEFT JOIN superset_min_order smo ON us.superset_group = smo.superset_group AND us.routine = smo.routine
            ORDER BY us.routine, sort_order, CASE WHEN us.superset_group IS NOT NULL THEN 0 ELSE 1 END,
                     us.superset_group, us.exercise_order, us.exercise
        """
    elif has_order:
        return """
            SELECT 
                us.routine, us.exercise, e.primary_muscle_group, e.secondary_muscle_group,
                e.tertiary_muscle_group, e.advanced_isolated_muscles, e.utility,
                e.movement_pattern, e.movement_subpattern, us.sets, us.min_rep_range,
                us.max_rep_range, us.rir, us.rpe, us.weight, us.execution_style,
                e.grips, e.stabilizers, e.synergists, us.superset_group, us.exercise_order
            FROM user_selection us
            LEFT JOIN exercises e ON us.exercise = e.exercise_name
            ORDER BY us.routine, us.exercise_order, us.exercise
        """
    else:
        return """
            SELECT 
                us.routine, us.exercise, e.primary_muscle_group, e.secondary_muscle_group,
                e.tertiary_muscle_group, e.advanced_isolated_muscles, e.utility,
                e.movement_pattern, e.movement_subpattern, us.sets, us.min_rep_range,
                us.max_rep_range, us.rir, us.rpe, us.weight, us.execution_style,
                e.grips, e.stabilizers, e.synergists, us.superset_group
            FROM user_selection us
            LEFT JOIN exercises e ON us.exercise = e.exercise_name
            ORDER BY us.routine, us.exercise
        """


def _fetch_all_sheets(db, view_mode):
    """Fetch data for all export sheets and return a mapping of sheet name to data."""
    sheets_data = {}
    
    # 1. Workout Plan
    logger.info("Fetching workout plan data")
    user_selection_query = _build_export_query(db)
    user_selection = db.fetch_all(user_selection_query)
    if user_selection:
        sheets_data['Workout Plan'] = reorder_and_rename_columns(user_selection, WORKOUT_PLAN_COLUMNS, view_mode)
        logger.info(f"Fetched {len(user_selection)} workout plan rows")
        
    # 2. Workout Log
    logger.info("Fetching workout log data")
    workout_log = db.fetch_all(f"SELECT * FROM workout_log ORDER BY created_at DESC LIMIT {MAX_EXPORT_ROWS}")
    if workout_log:
        sheets_data['Workout Log'] = workout_log
        logger.info(f"Fetched {len(workout_log)} workout log rows")
        
    # 3. Weekly Summary
    logger.info("Calculating weekly summary")
    weekly_summary_raw = calculate_weekly_summary('Total')
    if weekly_summary_raw:
        weekly_summary = _weekly_summary_to_rows(weekly_summary_raw)
        sheets_data['Weekly Summary'] = weekly_summary
        logger.info(f"Generated {len(weekly_summary)} weekly summary rows")
        
    # 4. Session Summary
    logger.info("Fetching session summary data")
    session_summary_query = f"""
        SELECT 
            date(wl.created_at) as session_date, wl.routine, wl.exercise,
            e.primary_muscle_group, e.secondary_muscle_group, e.tertiary_muscle_group, e.advanced_isolated_muscles,
            wl.planned_sets, wl.planned_min_reps, wl.planned_max_reps, wl.planned_weight, wl.planned_rir, wl.planned_rpe,
            wl.scored_weight, wl.scored_max_reps, wl.scored_rir, wl.scored_rpe
        FROM workout_log wl
        LEFT JOIN exercises e ON wl.exercise = e.exercise_name
        WHERE (wl.scored_weight IS NOT NULL OR wl.scored_max_reps IS NOT NULL OR wl.planned_weight IS NOT NULL OR wl.planned_sets IS NOT NULL)
        AND wl.routine IS NOT NULL
        ORDER BY wl.created_at DESC
        LIMIT {MAX_EXPORT_ROWS}
    """
    session_summary = db.fetch_all(session_summary_query)
    if session_summary:
        sheets_data['Session Summary'] = session_summary
        logger.info(f"Fetched {len(session_summary)} session summary rows")
        
    # 5. Progression Goals
    logger.info("Fetching progression goals")
    progression_goals = db.fetch_all("""
        SELECT exercise, goal_type, current_value, target_value, goal_date, completed, created_at
        FROM progression_goals ORDER BY created_at DESC
    """)
    if progression_goals:
        sheets_data['Progression Goals'] = progression_goals
        logger.info(f"Fetched {len(progression_goals)} progression goals")
        
    # 6. Categories Summary
    logger.info("Calculating exercise categories")
    categories = calculate_exercise_categories()
    if categories:
        sheets_data['Categories'] = categories
        logger.info(f"Generated {len(categories)} category rows")
        
    # 7. Isolated Muscles Stats
    logger.info("Calculating isolated muscles stats")
    isolated_muscles = calculate_isolated_muscles_stats()
    if isolated_muscles:
        sheets_data['Isolated Muscles'] = isolated_muscles
        logger.info(f"Generated {len(isolated_muscles)} isolated muscle rows")
        
    return sheets_data


@exports_bp.route("/export_to_excel", methods=['GET'])
def export_to_excel():
    """
    Export all data to Excel using memory-efficient approach.
    
    Query Parameters:
        view_mode: 'simple' or 'advanced' - determines column naming
    
    This replaces pandas with direct XlsxWriter usage for better
    memory efficiency and performance on large datasets.
    """
    try:
        # Get view mode from query parameter (default to simple)
        view_mode = request.args.get('view_mode', 'simple')
        if view_mode not in ('simple', 'advanced'):
            view_mode = 'simple'
        
        logger.info(
            "Starting Excel export",
            extra={
                'export_type': 'excel',
                'format': 'workout_data',
                'view_mode': view_mode
            }
        )
        
        with DatabaseHandler() as db:
            _recalculate_exercise_order(db)
            sheets_data = _fetch_all_sheets(db, view_mode)
            
        # Generate filename with timestamp
        filename = generate_timestamped_filename('workout_tracker_summary')
        
        logger.info(f"Creating Excel workbook with {len(sheets_data)} sheets: {list(sheets_data.keys())}")
        
        try:
            response = create_excel_workbook(sheets_data, filename)
            
            # Ensure response has data
            if hasattr(response, 'data') and (not response.data or len(response.data) == 0):
                logger.error("Response data is empty!")
                raise ValueError("Generated Excel file is empty")
            
            # Calculate total rows across all sheets
            total_rows = sum(len(data) for data in sheets_data.values())
            
            logger.info(
                "Excel export completed successfully",
                extra={
                    'export_type': 'excel',
                    'export_filename': filename,
                    'sheet_count': len(sheets_data),
                    'total_rows': total_rows,
                    'sheets': list(sheets_data.keys())
                }
            )
            return response
        except Exception as create_error:
            logger.exception(f"Error in create_excel_workbook: {create_error}")
            raise
        
    except Exception as e:
        logger.exception(f"Error exporting to Excel: {e}")
        # Return JSON error response properly
        return error_response(
            "EXPORT_FAILED",
            "Failed to export data to Excel. Please try again.",
            500
        )

@exports_bp.route("/export_to_workout_log", methods=["POST"])
def export_to_workout_log():
    """Export current workout plan to workout log."""
    try:
        logger.info("Starting workout plan export to workout log")
        
        query = """
        SELECT id, routine, exercise, sets, min_rep_range, max_rep_range, 
               rir, rpe, weight
        FROM user_selection
        """
        
        insert_query = """
        INSERT INTO workout_log (
            workout_plan_id, routine, exercise, planned_sets, planned_min_reps,
            planned_max_reps, planned_rir, planned_rpe, planned_weight, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        with DatabaseHandler() as db:
            workout_plan = db.fetch_all(query)

            if not workout_plan:
                logger.warning("No exercises found in workout plan to export")
                return error_response(
                    "NO_DATA",
                    "No exercises to export",
                    400
                )

            exported_count = 0
            skipped_count = 0
            for exercise in workout_plan:
                # Check if this exercise already exists in the workout log
                existing = db.fetch_one(
                    "SELECT id FROM workout_log WHERE workout_plan_id = ?",
                    (exercise["id"],)
                )
                if existing:
                    skipped_count += 1
                    continue

                params = (
                    exercise["id"], exercise["routine"], exercise["exercise"],
                    exercise["sets"], exercise["min_rep_range"], exercise["max_rep_range"],
                    exercise["rir"], exercise["rpe"], exercise["weight"]
                )
                db.execute_query(insert_query, params)
                exported_count += 1

            if exported_count == 0 and skipped_count > 0:
                logger.info(f"All {skipped_count} exercises already in workout log")
                return success_response(
                    message=f"All exercises already exist in the workout log ({skipped_count} skipped)"
                )

            logger.info(f"Successfully exported {exported_count} exercises to workout log (skipped {skipped_count} duplicates)")
        
        return success_response(
            message=f"Workout plan exported successfully ({exported_count} exercises)"
        )
            
    except Exception as e:
        logger.exception(f"Error exporting workout plan: {e}")
        return error_response(
            "EXPORT_FAILED",
            "Failed to export workout plan",
            500
        ) 

@exports_bp.route("/export_summary", methods=["POST"])
def export_summary():
    """
    Export summary data based on specified parameters.
    
    Memory-efficient implementation without pandas.
    """
    try:
        params = request.get_json() or {}
        method = params.get('method', 'Total')
        
        logger.info(f"Starting summary export with method: {method}")
        sheets_data = {}
        
        # Export Weekly Summary
        logger.info("Calculating weekly summary")
        weekly_data_raw = calculate_weekly_summary(method)
        if weekly_data_raw:
            weekly_data = _weekly_summary_to_rows(weekly_data_raw)
            sheets_data['Weekly Summary'] = weekly_data
            logger.info(f"Generated {len(weekly_data)} weekly summary rows")
        
        # Export Categories
        logger.info("Calculating exercise categories")
        categories = calculate_exercise_categories()
        if categories:
            sheets_data['Categories'] = categories
            logger.info(f"Generated {len(categories)} category rows")
        
        if not sheets_data:
            logger.warning("No data available for export; returning empty workbook")

        # Generate filename with method and timestamp
        base_name = f'workout_summary_{method}'
        filename = generate_timestamped_filename(base_name)
        
        logger.info(f"Creating Excel workbook with {len(sheets_data)} sheets")
        response = create_excel_workbook(sheets_data, filename)
        logger.info("Summary export completed successfully")
        
        return response
        
    except Exception as e:
        logger.exception(f"Error exporting summary: {e}")
        return error_response(
            "EXPORT_FAILED",
            "Failed to export summary data",
            500
        )


@exports_bp.route("/export_large_dataset", methods=["POST"])
def export_large_dataset():
    """
    Stream export for large datasets to prevent memory issues.
    
    This endpoint uses a generator to stream data directly to the client,
    preventing the entire dataset from being loaded into memory at once.
    """
    try:
        params = request.get_json() or {}
        export_type = params.get('type', 'all')  # 'all', 'workout_log', 'session_summary'
        
        logger.info(f"Starting streaming export for type: {export_type}")
        
        def data_generator():
            """Generator that yields (sheet_name, data) tuples for streaming."""
            with DatabaseHandler() as db:
                if export_type in ['all', 'workout_log']:
                    # Stream workout log in batches
                    logger.info("Streaming workout log data")
                    query = f"""
                    SELECT * FROM workout_log 
                    ORDER BY created_at DESC
                    LIMIT {MAX_EXPORT_ROWS}
                    """
                    workout_log = db.fetch_all(query)
                    if workout_log:
                        yield ('Workout Log', workout_log)
                
                if export_type in ['all', 'session_summary']:
                    # Stream session summary
                    logger.info("Streaming session summary data")
                    query = f"""
                    SELECT 
                        date(wl.created_at) as session_date,
                        wl.routine,
                        wl.exercise,
                        e.primary_muscle_group,
                        e.secondary_muscle_group,
                        wl.planned_sets,
                        wl.planned_min_reps,
                        wl.planned_max_reps,
                        wl.planned_weight,
                        wl.scored_weight,
                        wl.scored_max_reps
                    FROM workout_log wl
                    LEFT JOIN exercises e ON wl.exercise = e.exercise_name
                    WHERE wl.scored_weight IS NOT NULL
                       OR wl.scored_max_reps IS NOT NULL
                    ORDER BY wl.created_at DESC
                    LIMIT {MAX_EXPORT_ROWS}
                    """
                    session_data = db.fetch_all(query)
                    if session_data:
                        yield ('Session Summary', session_data)
                
                if export_type == 'all':
                    # Add summary sheets
                    logger.info("Generating summary sheets")
                    weekly_raw = calculate_weekly_summary('Total')
                    if weekly_raw:
                        yield ('Weekly Summary', _weekly_summary_to_rows(weekly_raw))
                    
                    categories = calculate_exercise_categories()
                    if categories:
                        yield ('Categories', categories)
        
        filename = generate_timestamped_filename(f'workout_export_{export_type}')
        logger.info(f"Starting streaming response for {filename}")
        
        return stream_excel_response(data_generator(), filename)
        
    except Exception as e:
        logger.exception(f"Error in streaming export: {e}")
        return error_response(
            "EXPORT_FAILED",
            "Failed to stream export data",
            500
        )
 
