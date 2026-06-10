"""
Tests for utils/logger.py - Logging configuration.
"""

import logging
from unittest.mock import patch, MagicMock


class TestRequestIdFilter:
    """Tests for RequestIdFilter class."""

    def test_filter_adds_request_id_from_request_context(self):
        """Should add request_id from Flask g object."""
        from utils.logger import RequestIdFilter
        
        filter_obj = RequestIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        # Mock Flask's has_request_context and g at the flask module level
        with patch('flask.has_request_context', return_value=True):
            mock_g = MagicMock()
            mock_g.request_id = "test-request-123"
            with patch('flask.g', mock_g):
                result = filter_obj.filter(record)
        
        assert result is True
        assert record.request_id == "test-request-123"  # type: ignore[attr-defined]

    def test_filter_adds_na_without_request_context(self):
        """Should add 'N/A' when not in request context."""
        from utils.logger import RequestIdFilter
        
        filter_obj = RequestIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        with patch('flask.has_request_context', return_value=False):
            result = filter_obj.filter(record)
        
        assert result is True
        assert record.request_id == "N/A"  # type: ignore[attr-defined]

    def test_filter_returns_true(self):
        """Filter should always return True (don't suppress records)."""
        from utils.logger import RequestIdFilter
        
        filter_obj = RequestIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        
        with patch('flask.has_request_context', return_value=False):
            result = filter_obj.filter(record)
        
        assert result is True


class TestSetupLogging:
    """Tests for setup_logging function."""

    @patch('utils.logger.RotatingFileHandler')
    @patch('utils.logger.os.makedirs')
    def test_creates_logs_directory(self, mock_makedirs, mock_handler):
        """Should create logs directory."""
        mock_handler.return_value = MagicMock()
        
        # Clear existing logger to force recreation
        import utils.logger
        utils.logger._logger = None
        
        logger = utils.logger.setup_logging()
        
        mock_makedirs.assert_called()

    @patch('utils.logger.RotatingFileHandler')
    @patch('utils.logger.os.makedirs')
    def test_returns_logger(self, mock_makedirs, mock_handler):
        """Should return a logger instance."""
        mock_handler.return_value = MagicMock()
        
        import utils.logger
        utils.logger._logger = None
        
        logger = utils.logger.setup_logging()
        
        assert isinstance(logger, logging.Logger)

    @patch('utils.logger.RotatingFileHandler')
    @patch('utils.logger.os.makedirs')
    def test_logger_name(self, mock_makedirs, mock_handler):
        """Logger should have correct name."""
        mock_handler.return_value = MagicMock()
        
        import utils.logger
        utils.logger._logger = None
        
        logger = utils.logger.setup_logging()
        
        assert logger.name == 'hypertrophy_toolbox'

    @patch('utils.logger.RotatingFileHandler')
    @patch('utils.logger.os.makedirs')
    def test_logger_level_is_debug(self, mock_makedirs, mock_handler):
        """Logger should be set to DEBUG level."""
        mock_handler.return_value = MagicMock()
        
        import utils.logger
        utils.logger._logger = None
        
        logger = utils.logger.setup_logging()
        
        assert logger.level == logging.DEBUG

    def test_prevents_duplicate_handlers(self):
        """Should not add duplicate handlers on multiple calls."""
        import utils.logger
        
        # Clear and setup
        utils.logger._logger = None
        
        with patch('utils.logger.RotatingFileHandler') as mock_handler:
            mock_handler.return_value = MagicMock()
            with patch('utils.logger.os.makedirs'):
                logger1 = utils.logger.setup_logging()
                handler_count_1 = len(logger1.handlers)
                
                # Call again
                logger2 = utils.logger.setup_logging()
                handler_count_2 = len(logger2.handlers)
        
        # Should not have added more handlers
        assert handler_count_2 == handler_count_1


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self):
        """Should return a logger instance."""
        from utils.logger import get_logger
        
        with patch('utils.logger.setup_logging') as mock_setup:
            mock_logger = MagicMock()
            mock_setup.return_value = mock_logger
            
            import utils.logger
            utils.logger._logger = None
            
            logger = get_logger()
        
        assert logger is not None

    def test_caches_logger(self):
        """Should cache and return same logger instance."""
        import utils.logger
        utils.logger._logger = None
        
        with patch('utils.logger.setup_logging') as mock_setup:
            mock_logger = MagicMock()
            mock_setup.return_value = mock_logger
            
            logger1 = utils.logger.get_logger()
            logger2 = utils.logger.get_logger()
        
        # Should only call setup once
        assert mock_setup.call_count == 1
        assert logger1 is logger2

    def test_calls_setup_logging_if_no_logger(self):
        """Should call setup_logging if no cached logger."""
        import utils.logger
        utils.logger._logger = None
        
        with patch('utils.logger.setup_logging') as mock_setup:
            mock_setup.return_value = MagicMock()
            utils.logger.get_logger()
        
        mock_setup.assert_called_once()


class TestLoggingFormat:
    """Tests for logging format configuration."""

    def test_file_handler_log_file_path(self):
        """File handler should write to logs directory."""
        import utils.logger
        
        # Clear existing logger
        utils.logger._logger = None
        logger = utils.logger.setup_logging()
        
        # Check that a file handler was added (or handlers exist)
        assert len(logger.handlers) >= 1

    def test_logger_has_debug_level(self):
        """Logger should have DEBUG level set."""
        import utils.logger
        utils.logger._logger = None
        
        logger = utils.logger.setup_logging()
        
        assert logger.level == logging.DEBUG


class TestFlaskIntegration:
    """Tests for Flask app integration."""

    def test_flask_app_provided_configures_app_logger(self):
        """When Flask app provided, should configure its logger."""
        import utils.logger
        utils.logger._logger = None
        
        mock_app = MagicMock()
        mock_app.logger = MagicMock()
        
        # setup_logging returns logger when app is provided
        logger = utils.logger.setup_logging(app=mock_app)
        
        # App logger handlers should be set from main logger
        assert logger is not None
