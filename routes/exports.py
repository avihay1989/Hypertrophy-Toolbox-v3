from flask import Blueprint, request
from utils.export_utils import (
    create_excel_workbook,
    generate_timestamped_filename,
    stream_excel_response,
)
from utils.export_service import (
    build_summary_sheets,
    collect_excel_sheets,
    export_plan_to_workout_log,
    stream_export_rows,
)
from utils.errors import error_response, success_response
from utils.logger import get_logger

exports_bp = Blueprint('exports', __name__)
logger = get_logger()


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

        sheets_data = collect_excel_sheets(view_mode)

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

        result = export_plan_to_workout_log()
        if not result.ok:
            return error_response(result.code, result.message, result.status_code)

        return success_response(message=result.message)

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

        sheets_data = build_summary_sheets(method)

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

        filename = generate_timestamped_filename(f'workout_export_{export_type}')
        logger.info(f"Starting streaming response for {filename}")

        return stream_excel_response(stream_export_rows(export_type), filename)

    except Exception as e:
        logger.exception(f"Error in streaming export: {e}")
        return error_response(
            "EXPORT_FAILED",
            "Failed to stream export data",
            500
        )
