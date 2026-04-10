from flask import Blueprint, render_template, request, jsonify, send_file
from utils.database import DatabaseHandler
from utils.workout_log import get_workout_logs
from utils.errors import success_response, error_response
from utils.logger import get_logger
from io import BytesIO
from datetime import datetime

workout_log_bp = Blueprint('workout_log', __name__)
logger = get_logger()

@workout_log_bp.route("/workout_log")
def workout_log():
    """Render the workout log page."""
    try:
        workout_logs = get_workout_logs()
        return render_template(
            "workout_log.html",
            page_title="Workout Log",
            workout_logs=workout_logs,
            enumerate=enumerate,
        )
    except Exception as e:
        logger.exception("Error loading workout log page")
        return error_response("INTERNAL_ERROR", "Unable to load workout log.", 500)

@workout_log_bp.route("/update_workout_log", methods=["POST"])
def update_workout_log():
    """Update workout log entry."""
    try:
        data = request.get_json()
        log_id = data.get("id")
        updates = data.get("updates", {})

        if not log_id:
            return error_response("VALIDATION_ERROR", "Log ID is required", 400)

        valid_fields = {
            "scored_weight", "scored_min_reps", "scored_max_reps", 
            "scored_rir", "scored_rpe", "last_progression_date"
        }

        valid_updates = {k: v for k, v in updates.items() if k in valid_fields}

        if not valid_updates:
            return error_response("VALIDATION_ERROR", "No valid fields to update", 400)

        set_clause = ", ".join(f"{k} = ?" for k in valid_updates.keys())
        query = f"UPDATE workout_log SET {set_clause} WHERE id = ?"
        params = list(valid_updates.values()) + [log_id]

        with DatabaseHandler() as db:
            # Check if log entry exists
            check_query = "SELECT id FROM workout_log WHERE id = ?"
            existing = db.fetch_one(check_query, (log_id,))
            if not existing:
                return error_response("NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404)
            
            db.execute_query(query, params)

        logger.info(f"Updated workout log {log_id}")
        return jsonify(success_response(message="Workout log updated successfully"))
    except Exception as e:
        logger.exception("Error updating workout log")
        return error_response("INTERNAL_ERROR", "Failed to update workout log", 500)

@workout_log_bp.route('/delete_workout_log', methods=['POST'])
def delete_workout_log():
    try:
        data = request.get_json()
        log_id = data.get('id')
        
        if not log_id:
            return error_response("VALIDATION_ERROR", "No log ID provided", 400)
        
        with DatabaseHandler() as db:
            # Check if log entry exists
            check_query = "SELECT id FROM workout_log WHERE id = ?"
            existing = db.fetch_one(check_query, (log_id,))
            if not existing:
                return error_response("NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404)
            
            query = "DELETE FROM workout_log WHERE id = ?"
            db.execute_query(query, (log_id,))
        
        logger.info(f"Deleted workout log {log_id}")
        return jsonify(success_response(message="Log entry deleted successfully"))
        
    except Exception as e:
        logger.exception(f"Error deleting workout log")
        return error_response("INTERNAL_ERROR", "Failed to delete workout log", 500)

@workout_log_bp.route("/update_progression_date", methods=["POST"])
def update_progression_date():
    """Update the last progression date for a workout log entry."""
    try:
        data = request.get_json()
        log_id = data.get("id")
        new_date = data.get("date")

        if not log_id or not new_date:
            return error_response("VALIDATION_ERROR", "Log ID and date are required", 400)

        query = "UPDATE workout_log SET last_progression_date = ? WHERE id = ?"
        with DatabaseHandler() as db:
            # Check if log entry exists
            check_query = "SELECT id FROM workout_log WHERE id = ?"
            existing = db.fetch_one(check_query, (log_id,))
            if not existing:
                return error_response("NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404)
            
            db.execute_query(query, (new_date, log_id))

        logger.info(f"Updated progression date for log {log_id}")
        return jsonify(success_response(message="Progression date updated successfully"))
    except Exception as e:
        logger.exception("Error updating progression date")
        return error_response("INTERNAL_ERROR", "Failed to update progression date", 500) 

@workout_log_bp.route("/check_progression/<int:log_id>")
def check_progression_route(log_id):
    """Check if progressive overload was achieved for a specific log entry."""
    try:
        query = """
        SELECT 
            planned_min_reps, planned_max_reps, planned_weight,
            scored_min_reps, scored_max_reps, scored_weight,
            planned_rir, scored_rir,
            planned_rpe, scored_rpe
        FROM workout_log 
        WHERE id = ?
        """
        with DatabaseHandler() as db:
            log = db.fetch_one(query, (log_id,))
            if not log:
                return error_response("NOT_FOUND", "Log entry not found", 404)

            is_progressive = (
                (log['scored_rir'] is not None and 
                 log['planned_rir'] is not None and 
                 log['scored_rir'] < log['planned_rir']) or
                
                (log['scored_rpe'] is not None and 
                 log['planned_rpe'] is not None and 
                 log['scored_rpe'] > log['planned_rpe']) or
                
                (log['scored_min_reps'] is not None and 
                 log['planned_min_reps'] is not None and 
                 log['scored_min_reps'] > log['planned_min_reps']) or
                
                (log['scored_max_reps'] is not None and 
                 log['planned_max_reps'] is not None and 
                 log['scored_max_reps'] > log['planned_max_reps']) or
                
                (log['scored_weight'] is not None and 
                 log['planned_weight'] is not None and 
                 log['scored_weight'] > log['planned_weight'])
            )

            return jsonify(success_response(data={
                "is_progressive": is_progressive,
                "status": "Achieved" if is_progressive else "Pending"
            }))

    except Exception as e:
        logger.exception("Error checking progression")
        return error_response("INTERNAL_ERROR", "Failed to check progression status", 500)

@workout_log_bp.route("/get_workout_logs")
def get_logs():
    """Get all workout logs."""
    try:
        query = """
        SELECT 
            wl.*,
            us.routine as plan_routine,
            us.exercise as plan_exercise
        FROM workout_log wl
        LEFT JOIN user_selection us ON wl.workout_plan_id = us.id
        ORDER BY wl.created_at DESC
        """
        with DatabaseHandler() as db:
            results = db.fetch_all(query)
            return jsonify(success_response(data=results))
    except Exception as e:
        logger.exception("Error fetching workout logs")
        return error_response("INTERNAL_ERROR", "Failed to fetch workout logs", 500) 

@workout_log_bp.route('/export_workout_log')
def export_workout_log():
    try:
        # Lazy load pandas - only imported when export is requested
        import pandas as pd
        
        # Get workout log data
        logs = get_workout_logs()
        
        if not logs:
            return error_response("NOT_FOUND", "No workout logs found to export", 404)
        
        # Convert to DataFrame
        df = pd.DataFrame(logs)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Workout Log', index=False)
            
            # Get the workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Workout Log']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#f8f9fa',
                'border': 1
            })
            
            # Format the header row
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Adjust column widths
            for idx, col in enumerate(df.columns):
                worksheet.set_column(idx, idx, max(len(str(col)), df[col].astype(str).str.len().max()) + 2)
        
        # Seek to the beginning of the stream
        output.seek(0)
        
        # Generate filename with timestamp
        filename = f'workout_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        logger.info(f"Exported workout log to {filename}")
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.exception("Error exporting workout log")
        return error_response("INTERNAL_ERROR", "Failed to export workout log", 500)

@workout_log_bp.route('/clear_workout_log', methods=['POST'])
def clear_workout_log():
    """Clear all entries from the workout log."""
    try:
        with DatabaseHandler() as db:
            # Count entries before clearing for the response message
            count_query = "SELECT COUNT(*) as count FROM workout_log"
            result = db.fetch_one(count_query)
            entry_count = result['count'] if result else 0
            
            if entry_count == 0:
                return jsonify(success_response(message="Workout log is already empty"))
            
            # Delete all entries
            delete_query = "DELETE FROM workout_log"
            db.execute_query(delete_query)
            
            logger.info(f"Cleared {entry_count} entries from workout log")
            return jsonify(success_response(
                message=f"Successfully cleared {entry_count} entries from workout log"
            ))
            
    except Exception as e:
        logger.exception("Error clearing workout log")
        return error_response("INTERNAL_ERROR", "Failed to clear workout log", 500) 