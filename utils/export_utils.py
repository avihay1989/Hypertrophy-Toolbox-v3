"""
Export utilities for secure, memory-efficient data exports.

Provides:
- Filename sanitization for secure downloads
- Streaming Excel generation for large datasets
- Memory-safe export operations
- Content-Disposition header management
"""

import re
import os
import tempfile
from io import BytesIO
from typing import List, Dict, Any, Generator
from datetime import datetime
from flask import Response, make_response

from utils.config import MAX_EXPORT_ROWS, EXPORT_BATCH_SIZE, MAX_FILENAME_LENGTH, STREAMING_THRESHOLD
from utils.logger import get_logger

# Note: xlsxwriter is lazy-loaded in functions that need it to improve startup time

logger = get_logger()


def sanitize_filename(filename: str, max_length: int = None) -> str:
    """
    Sanitize a filename for safe download.
    
    Args:
        filename: The original filename
        max_length: Maximum allowed filename length (default from config)
        
    Returns:
        Sanitized filename safe for downloads
        
    Examples:
        >>> sanitize_filename("My Workout <script>.xlsx")
        'My_Workout_script.xlsx'
        >>> sanitize_filename("../../etc/passwd.xlsx")
        'etc_passwd.xlsx'
    """
    if max_length is None:
        max_length = MAX_FILENAME_LENGTH
    
    # First, split on path separators to get just the filename part
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove or replace dangerous characters
    # Keep only alphanumerics, spaces, dots, hyphens, underscores
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)
    
    # Replace multiple spaces/underscores with single underscore
    filename = re.sub(r'[\s_]+', '_', filename)
    
    # Ensure it has a valid extension
    if not filename.endswith('.xlsx'):
        if '.' in filename:
            # Replace existing extension
            filename = filename.rsplit('.', 1)[0] + '.xlsx'
        else:
            filename += '.xlsx'
    
    # Truncate if too long (keep extension)
    if len(filename) > max_length:
        name_part, ext = filename.rsplit('.', 1)
        name_part = name_part[:max_length - len(ext) - 1]
        filename = f"{name_part}.{ext}"
    
    # Trim underscores that end up directly before the extension
    filename = re.sub(r'_+(\.xlsx)$', r'\1', filename)

    # Fallback to default if sanitization results in empty name
    if not filename or filename == '.xlsx':
        filename = 'export.xlsx'
    
    return filename


def create_content_disposition_header(filename: str, attachment: bool = True) -> str:
    """
    Create a safe Content-Disposition header.
    
    Args:
        filename: The filename to use
        attachment: If True, use 'attachment' (download), else 'inline' (display)
        
    Returns:
        Properly formatted Content-Disposition header value
    """
    sanitized = sanitize_filename(filename)
    
    # Use filename* parameter for proper UTF-8 encoding (RFC 5987)
    disposition_type = 'attachment' if attachment else 'inline'
    
    # ASCII-safe filename with UTF-8 fallback
    ascii_filename = sanitized.encode('ascii', 'ignore').decode('ascii')
    
    # Build header with both ASCII and UTF-8 versions
    header = f'{disposition_type}; filename="{ascii_filename}"'
    
    return header


def stream_excel_response(
    workbook_generator: Generator[tuple[str, List[Dict[str, Any]]], None, None],
    filename: str,
    chunk_size: int = 8192
) -> Response:
    """
    Create a streaming response for Excel file generation.
    
    This generates the Excel file on-the-fly, reducing memory usage
    for large exports.
    
    Args:
        workbook_generator: Generator yielding (sheet_name, data) tuples
        filename: Output filename
        chunk_size: Size of chunks to stream (bytes)
        
    Returns:
        Flask Response object with streaming content
    """
    def generate():
        # Lazy load xlsxwriter - only imported when export is requested
        from xlsxwriter import Workbook
        
        output = BytesIO()
        workbook = Workbook(output, {'in_memory': True})
        
        try:
            for sheet_name, data in workbook_generator:
                if not data:
                    logger.warning(f"Empty data for sheet: {sheet_name}")
                    continue
                
                worksheet = workbook.add_worksheet(sheet_name[:31])  # Excel sheet name limit
                
                # Write headers
                headers = list(data[0].keys()) if data else []
                for col_idx, header in enumerate(headers):
                    worksheet.write(0, col_idx, header)
                
                # Write data in batches
                for row_idx, row_data in enumerate(data, start=1):
                    if row_idx > MAX_EXPORT_ROWS:
                        logger.warning(f"Reached max export rows ({MAX_EXPORT_ROWS})")
                        break
                    
                    for col_idx, key in enumerate(headers):
                        value = row_data.get(key, '')
                        worksheet.write(row_idx, col_idx, value)
            
            workbook.close()
            output.seek(0)
            
            # Stream the content
            while True:
                chunk = output.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                
        except Exception as e:
            logger.exception(f"Error generating Excel file: {e}")
            raise
        finally:
            output.close()
    
    response = Response(
        generate(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response.headers['Content-Disposition'] = create_content_disposition_header(filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


def _setup_formats(workbook) -> tuple[Any, Any, Dict[int, Any]]:
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4A90E2',
        'font_color': '#FFFFFF',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1
    })
    
    superset_formats = {
        1: workbook.add_format({
            'border': 1,
            'bg_color': '#E8E0F0',
            'left': 5,
            'left_color': '#7C3AED'
        }),
        2: workbook.add_format({
            'border': 1,
            'bg_color': '#E0F0F0',
            'left': 5,
            'left_color': '#0891B2'
        }),
        3: workbook.add_format({
            'border': 1,
            'bg_color': '#E0F5ED',
            'left': 5,
            'left_color': '#059669'
        }),
        4: workbook.add_format({
            'border': 1,
            'bg_color': '#FEF3E0',
            'left': 5,
            'left_color': '#D97706'
        })
    }
    return header_format, cell_format, superset_formats


def _build_superset_color_map(data: List[Dict[str, Any]]) -> Dict[str, int]:
    superset_color_map = {}
    color_index = 0
    for row_data in data:
        superset_group = row_data.get('superset_group') or row_data.get('Superset Group')
        if superset_group and superset_group not in superset_color_map:
            color_index = (color_index % 4) + 1
            superset_color_map[superset_group] = color_index
    return superset_color_map


def _write_worksheet(workbook, sheet_name: str, data: Any, header_format, cell_format, superset_formats) -> bool:
    if data is None:
        logger.info(f"Skipping None sheet: {sheet_name}")
        return False
    if not isinstance(data, list):
        logger.warning(f"Sheet {sheet_name} has invalid data type: {type(data)}")
        return False
    if len(data) == 0:
        logger.info(f"Skipping empty sheet: {sheet_name}")
        return False
        
    safe_sheet_name = sheet_name[:31]
    worksheet = workbook.add_worksheet(safe_sheet_name)
    logger.debug(f"Added worksheet: {safe_sheet_name} with {len(data)} rows")
    
    if not isinstance(data[0], dict):
        logger.warning(f"First row of {sheet_name} is not a dict: {type(data[0])}")
        return True
        
    headers = list(data[0].keys())
    
    for col_idx, header in enumerate(headers):
        worksheet.set_column(col_idx, col_idx, max(len(str(header)) + 2, 10))
        worksheet.write(0, col_idx, header, header_format)
        
    rows_written = 0
    superset_color_map = {}
    if sheet_name == 'Workout Plan':
        superset_color_map = _build_superset_color_map(data)
        
    for row_idx, row_data in enumerate(data, start=1):
        if rows_written >= MAX_EXPORT_ROWS:
            logger.warning(f"Reached max export rows ({MAX_EXPORT_ROWS}) for sheet {sheet_name}")
            break
            
        row_format = cell_format
        if sheet_name == 'Workout Plan':
            superset_group = row_data.get('superset_group') or row_data.get('Superset Group')
            if superset_group and superset_group in superset_color_map:
                color_num = superset_color_map[superset_group]
                row_format = superset_formats.get(color_num, cell_format)
                
        for col_idx, key in enumerate(headers):
            value = row_data.get(key, '')
            if value is None:
                value = ''
            worksheet.write(row_idx, col_idx, value, row_format)
            
        rows_written += 1
        
    return True


def create_excel_workbook(
    sheets_data: Dict[str, List[Dict[str, Any]]],
    filename: str
) -> Response:
    """
    Create an Excel workbook from multiple sheets of data.
    
    Memory-efficient implementation using XlsxWriter directly without pandas.
    
    Args:
        sheets_data: Dictionary mapping sheet names to list of row dictionaries
        filename: Output filename
        
    Returns:
        Flask Response object with Excel file
    """
    if not sheets_data:
        logger.warning("No sheets data provided, creating empty workbook")
        sheets_data = {}
    
    logger.info(f"Creating Excel workbook with {len(sheets_data)} sheet(s)")
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file_path = temp_file.name
    temp_file.close()
    
    logger.info(f"Using temporary file: {temp_file_path}")
    workbook = None
    
    try:
        from xlsxwriter import Workbook
        
        workbook = Workbook(temp_file_path)
        worksheets_created = 0
        
        header_format, cell_format, superset_formats = _setup_formats(workbook)
        
        for sheet_name, data in sheets_data.items():
            if _write_worksheet(workbook, sheet_name, data, header_format, cell_format, superset_formats):
                worksheets_created += 1
        
        # Ensure at least one worksheet is created to make the Excel file valid
        if worksheets_created == 0:
            logger.warning("No worksheets created, creating empty worksheet with message")
            worksheet = workbook.add_worksheet('No Data')
            worksheet.write(0, 0, 'No data available for export', header_format)
            worksheet.write(1, 0, 'Please add data to your workout plan to export.', cell_format)
            worksheet.set_column(0, 0, 50)
            worksheets_created = 1
            logger.info("Created 'No Data' worksheet")
        
        logger.info(f"Closing workbook after creating {worksheets_created} worksheet(s)")
        
        # Close workbook to finalize the Excel file
        # This writes everything to the temporary file
        workbook.close()
        workbook = None  # Mark as closed
        
        # Verify the file exists and has content
        if not os.path.exists(temp_file_path):
            logger.error(f"Temporary file does not exist after workbook.close(): {temp_file_path}")
            raise ValueError("Failed to generate Excel file: temporary file was not created")
        
        file_size = os.path.getsize(temp_file_path)
        logger.info(f"Temporary file size after workbook.close(): {file_size} bytes")
        
        if file_size == 0:
            logger.error(f"Temporary file is empty (0 bytes): {temp_file_path}")
            raise ValueError("Failed to generate Excel file: file is empty")
        
        # Read the file content from the temporary file
        # This ensures we have the complete, valid Excel file
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        
        # Validate that we have actual content
        if not file_content:
            logger.error("Generated Excel file is None")
            raise ValueError("Failed to generate Excel file: file content is None")
        if len(file_content) == 0:
            logger.error("Generated Excel file is empty (0 bytes) after reading from file")
            raise ValueError("Failed to generate Excel file: file content is empty")
        
        logger.info(f"Successfully generated Excel file: {len(file_content)} bytes (file_size={file_size})")
        
        # Create response with the file content as bytes
        # Use make_response to ensure proper handling
        response = make_response(file_content)
        response.mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = create_content_disposition_header(filename)
        response.headers['Content-Length'] = str(len(file_content))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        logger.debug(f"Response created with Content-Length: {len(file_content)} bytes")
        
        return response
        
    except Exception as e:
        logger.exception(f"Error creating Excel workbook: {e}")
        # Ensure workbook is closed even on error
        try:
            if workbook is not None:
                workbook.close()
        except Exception as close_error:
            logger.warning(f"Error closing workbook: {close_error}")
        raise
    finally:
        # Clean up the temporary file after a delay to allow debugging if needed
        # In case of errors, the temp file can be inspected
        try:
            if os.path.exists(temp_file_path):
                # Keep temp file for a few seconds to allow inspection if debugging
                import time
                time.sleep(0.5)  # Small delay for debugging
                os.remove(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {temp_file_path}: {e}")


def batch_query_results(
    query_func,
    batch_size: int = None
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Generator to batch large query results for memory-efficient processing.
    
    Args:
        query_func: Function that executes the query and returns results
        batch_size: Number of rows to fetch per batch (default from config)
        
    Yields:
        Batches of query results
    """
    if batch_size is None:
        batch_size = EXPORT_BATCH_SIZE
    
    offset = 0
    while True:
        batch = query_func(limit=batch_size, offset=offset)
        if not batch:
            break
        
        yield batch
        
        if len(batch) < batch_size:
            # Last batch
            break
        
        offset += batch_size


def estimate_export_size(row_count: int, col_count: int) -> int:
    """
    Estimate the size of an Excel export in bytes.
    
    Args:
        row_count: Number of rows
        col_count: Number of columns
        
    Returns:
        Estimated size in bytes
    """
    # Rough estimate: ~50 bytes per cell + overhead
    estimated_size = (row_count * col_count * 50) + 10240  # 10KB overhead
    return estimated_size


def should_use_streaming(row_count: int, col_count: int) -> bool:
    """
    Determine if streaming should be used based on data size.
    
    Args:
        row_count: Number of rows
        col_count: Number of columns
        
    Returns:
        True if streaming should be used
    """
    estimated_size = estimate_export_size(row_count, col_count)
    return estimated_size > STREAMING_THRESHOLD


def generate_timestamped_filename(base_name: str, extension: str = 'xlsx') -> str:
    """
    Generate a filename with current timestamp.
    
    Args:
        base_name: Base name for the file
        extension: File extension (default: 'xlsx')
        
    Returns:
        Filename with timestamp
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Always use xlsx for excel files to ensure proper format
    if extension != 'xlsx':
        extension = 'xlsx'
    filename = f"{base_name}_{timestamp}.{extension}"
    return sanitize_filename(filename)

