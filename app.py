
from flask import Flask, render_template, url_for, jsonify, request, make_response, g
from utils.db_initializer import initialize_database
from utils.database import DatabaseHandler, add_progression_goals_table, add_volume_tracking_tables
from routes.workout_log import workout_log_bp
from routes.weekly_summary import weekly_summary_bp
from routes.session_summary import session_summary_bp
from routes.exports import exports_bp
from routes.filters import filters_bp
from routes.workout_plan import workout_plan_bp, initialize_exercise_order
from routes.main import main_bp
from routes.progression_plan import progression_plan_bp
from routes.volume_splitter import volume_splitter_bp
from routes.program_backup import program_backup_bp, init_backup_tables
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.logger import setup_logging
from utils.errors import error_response, register_error_handlers, is_xhr_request
from utils.request_id import add_request_id_middleware
import time
import sys

app = Flask(__name__)
app.url_map.strict_slashes = False  # This makes Flask handle URLs with or without trailing slashes
app.wsgi_app = ProxyFix(app.wsgi_app)

# Production optimizations when running as frozen executable
if getattr(sys, 'frozen', False):
    # Enable Jinja2 template caching (auto_reload=False, cache_size increased)
    app.jinja_env.auto_reload = False
    app.config['TEMPLATES_AUTO_RELOAD'] = False
    # Disable debug mode for production
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    # Enable response compression hints
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files

# Setup structured logging
logger = setup_logging(app)

# Add request ID middleware for tracking and correlation
add_request_id_middleware(app)

# Register standardized error handlers
register_error_handlers(app)

# Initialize the database
logger.info("Initializing database...")
initialize_database()
logger.info("Adding progression goals table...")
add_progression_goals_table()
logger.info("Adding volume tracking tables...")
add_volume_tracking_tables()
logger.info("Initializing exercise order...")
initialize_exercise_order()
logger.info("Initializing backup tables...")
init_backup_tables()
logger.info("Database initialization complete")

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(workout_log_bp)
app.register_blueprint(weekly_summary_bp)
app.register_blueprint(session_summary_bp)

app.register_blueprint(exports_bp)

app.register_blueprint(filters_bp)
app.register_blueprint(workout_plan_bp)
app.register_blueprint(progression_plan_bp)
app.register_blueprint(volume_splitter_bp)
app.register_blueprint(program_backup_bp)

# Log registered routes (debug level only)
logger.debug("Registered routes:")
for rule in app.url_map.iter_rules():
    methods = ', '.join(sorted(rule.methods)) if rule.methods else ''
    logger.debug(f"{rule.endpoint}: {rule.rule} [{methods}]")

@app.template_filter('datetime')
def format_datetime(value, format='%d-%m-%Y'):
    if value and value != 'None':
        try:
            if isinstance(value, str):
                # Parse the date string (assuming it's in ISO format)
                date_obj = datetime.strptime(value, '%Y-%m-%d')
            else:
                date_obj = value
            return date_obj.strftime(format)
        except (ValueError, TypeError):
            return value
    return ''

@app.before_request
def clear_trailing():
    from flask import redirect, request
    rp = request.path 
    if rp != '/' and rp.endswith('/'):
        return redirect(rp[:-1])

@app.before_request
def start_timer():
    """Store request start time for performance logging."""
    g.start_time = time.time()

@app.context_processor
def inject_scale_level():
    """Inject UI scale level into all templates from cookie."""
    scale = request.cookies.get('ui-scale-level', '6')
    # Validate scale is 1-8
    try:
        scale_int = int(scale)
        if scale_int < 1 or scale_int > 8:
            scale = '6'
    except (ValueError, TypeError):
        scale = '6'
    
    zoom_values = {'1': '0.75', '2': '0.8', '3': '0.85', '4': '0.9', '5': '0.95', '6': '1', '7': '1.1', '8': '1.2'}
    return {
        'ui_scale_level': scale,
        'ui_zoom_value': zoom_values.get(scale, '1')
    }

# Test routes removed - no longer needed

@app.route('/erase-data', methods=['POST'])
def erase_data():
    try:
        # Drop ALL tables including backup tables (full reset)
        with DatabaseHandler() as db:
            tables = [
                'program_backup_items',  # Drop child table first (FK constraint)
                'program_backups',        # Then parent backup table
                'user_selection',
                'progression_goals',
                'muscle_volumes',
                'volume_plans',
                'workout_log'
            ]
            
            for table in tables:
                db.execute_query(f"DROP TABLE IF EXISTS {table}")
        
        # Reinitialize database - force=True to bypass the initialization guard
        # since we just dropped the tables
        logger.info("Reinitializing database...")
        initialize_database(force=True)
        logger.info("Adding progression goals table...")
        add_progression_goals_table()
        logger.info("Adding volume tracking tables...")
        add_volume_tracking_tables()
        logger.info("Initializing exercise order...")
        initialize_exercise_order()
        logger.info("Reinitializing backup tables...")
        init_backup_tables()
        
        from utils.errors import success_response
        
        response_message = 'All data has been erased and tables reinitialized successfully.'
        
        return jsonify(success_response(
            data=None,
            message=response_message
        ))
    except Exception as e:
        logger.exception("Error erasing data")
        return error_response("INTERNAL_ERROR", "Failed to erase data", 500)

@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors gracefully without logging stack traces for common requests."""
    # Don't log full exception for common missing resources like favicon
    if request.path == '/favicon.ico':
        # Return a simple 204 No Content response for favicon
        from flask import make_response
        return make_response('', 204)
    
    logger.warning(f"404 Not Found: {request.path}")
    if is_xhr_request():
        return error_response("NOT_FOUND", "The requested resource was not found", 404)

    html = (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head><meta charset='utf-8'><title>Not Found</title></head>"
        "<body><h1>Not Found</h1><p>The requested resource was not found.</p></body>"
        "</html>"
    )
    from flask import make_response
    response = make_response(html, 404)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

# Global error handler for unhandled exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler that logs stack traces."""
    import sys
    import traceback
    # Don't log 404 errors as exceptions
    if isinstance(e, Exception) and "404" in str(e):
        return handle_404(e)
    
    # Log to both logger and stderr for export routes
    if hasattr(e, '__class__'):
        print(f"=== EXCEPTION: {e.__class__.__name__}: {e} ===", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
    
    logger.exception(f"Unhandled exception: {e}")
    
    if is_xhr_request():
        return error_response("INTERNAL_ERROR", "An unexpected error occurred", 500)

    html = (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head><meta charset='utf-8'><title>Internal Server Error</title></head>"
        "<body><h1>Internal Server Error</h1><p>An unexpected error occurred.</p></body>"
        "</html>"
    )
    response = make_response(html, 500)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

if __name__ == "__main__":
    import atexit
    import signal
    import os
    
    # Register cleanup on graceful shutdown
    def cleanup_on_exit():
        """Cleanup resources on application exit."""
        try:
            # Checkpoint any open WAL files
            with DatabaseHandler() as db:
                db.connection.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            logger.info("Database cleanup completed on exit")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    atexit.register(cleanup_on_exit)
    
    # Handle SIGTERM (Ctrl+C) gracefully
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, cleaning up...")
        cleanup_on_exit()
        import sys
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Use use_reloader=False to prevent the double-process issue that causes
    # database corruption. The auto-reloader spawns a child process that
    # re-runs all startup code, leading to concurrent database writes.
    # For development with auto-reload, use: flask run --reload
    use_reloader = os.getenv('FLASK_USE_RELOADER', '0') == '1'
    
    # Security: Debug mode controlled by environment variable, defaults to False
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    
    app.run(debug=debug_mode, use_reloader=use_reloader)
