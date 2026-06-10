"""
Tests for utils/config.py - Application configuration.
"""

import os
from unittest.mock import patch


class TestConfigPaths:
    """Tests for configuration path constants."""

    def test_base_dir_is_absolute(self):
        """BASE_DIR should be an absolute path."""
        from utils.config import BASE_DIR
        assert os.path.isabs(BASE_DIR)

    def test_base_dir_exists(self):
        """BASE_DIR should point to existing directory."""
        from utils.config import BASE_DIR
        assert os.path.exists(BASE_DIR)

    def test_data_dir_under_base(self):
        """DATA_DIR should be under BASE_DIR."""
        from utils.config import BASE_DIR, DATA_DIR
        assert DATA_DIR.startswith(BASE_DIR)
        assert DATA_DIR.endswith("data")

    def test_logs_dir_under_base(self):
        """LOGS_DIR should be under BASE_DIR."""
        from utils.config import BASE_DIR, LOGS_DIR
        assert LOGS_DIR.startswith(BASE_DIR)
        assert LOGS_DIR.endswith("logs")

    def test_data_dir_created(self):
        """DATA_DIR should exist (created on import)."""
        from utils.config import DATA_DIR
        assert os.path.isdir(DATA_DIR)

    def test_logs_dir_created(self):
        """LOGS_DIR should exist (created on import)."""
        from utils.config import LOGS_DIR
        assert os.path.isdir(LOGS_DIR)


class TestDbFile:
    """Tests for DB_FILE configuration."""

    def test_db_file_has_default(self):
        """DB_FILE should have a default value."""
        from utils.config import DB_FILE
        assert DB_FILE is not None
        assert DB_FILE.endswith("database.db")

    def test_db_file_in_data_dir(self):
        """Default DB_FILE should be in DATA_DIR."""
        from utils.config import DB_FILE, DATA_DIR
        assert os.path.dirname(DB_FILE) == DATA_DIR

    @patch.dict(os.environ, {"DB_FILE": "/custom/path/test.db"})
    def test_db_file_env_override(self):
        """DB_FILE should be overridable via environment variable."""
        # Need to reimport to pick up env var
        import importlib
        import utils.config
        importlib.reload(utils.config)
        
        assert utils.config.DB_FILE == "/custom/path/test.db"
        
        # Restore original
        del os.environ["DB_FILE"]
        importlib.reload(utils.config)


class TestAppConstants:
    """Tests for application constants."""

    def test_app_title_defined(self):
        """APP_TITLE should be defined."""
        from utils.config import APP_TITLE
        assert APP_TITLE == "Workout Tracker"

    def test_app_title_is_string(self):
        """APP_TITLE should be a string."""
        from utils.config import APP_TITLE
        assert isinstance(APP_TITLE, str)


class TestExportConfiguration:
    """Tests for export configuration constants."""

    def test_max_export_rows_default(self):
        """MAX_EXPORT_ROWS should have reasonable default."""
        from utils.config import MAX_EXPORT_ROWS
        assert MAX_EXPORT_ROWS == 1000000

    def test_max_export_rows_is_int(self):
        """MAX_EXPORT_ROWS should be an integer."""
        from utils.config import MAX_EXPORT_ROWS
        assert isinstance(MAX_EXPORT_ROWS, int)

    def test_export_batch_size_default(self):
        """EXPORT_BATCH_SIZE should have reasonable default."""
        from utils.config import EXPORT_BATCH_SIZE
        assert EXPORT_BATCH_SIZE == 10000

    def test_export_batch_size_is_int(self):
        """EXPORT_BATCH_SIZE should be an integer."""
        from utils.config import EXPORT_BATCH_SIZE
        assert isinstance(EXPORT_BATCH_SIZE, int)

    def test_max_filename_length_defined(self):
        """MAX_FILENAME_LENGTH should be defined."""
        from utils.config import MAX_FILENAME_LENGTH
        assert MAX_FILENAME_LENGTH == 200

    def test_streaming_threshold_defined(self):
        """STREAMING_THRESHOLD should be 5MB."""
        from utils.config import STREAMING_THRESHOLD
        assert STREAMING_THRESHOLD == 5 * 1024 * 1024

    @patch.dict(os.environ, {"MAX_EXPORT_ROWS": "500000"})
    def test_max_export_rows_env_override(self):
        """MAX_EXPORT_ROWS should be overridable via environment."""
        import importlib
        import utils.config
        importlib.reload(utils.config)
        
        assert utils.config.MAX_EXPORT_ROWS == 500000
        
        # Restore original
        del os.environ["MAX_EXPORT_ROWS"]
        importlib.reload(utils.config)

    @patch.dict(os.environ, {"EXPORT_BATCH_SIZE": "5000"})
    def test_export_batch_size_env_override(self):
        """EXPORT_BATCH_SIZE should be overridable via environment."""
        import importlib
        import utils.config
        importlib.reload(utils.config)
        
        assert utils.config.EXPORT_BATCH_SIZE == 5000
        
        # Restore original
        del os.environ["EXPORT_BATCH_SIZE"]
        importlib.reload(utils.config)


class TestDirectoryCreation:
    """Tests for automatic directory creation."""

    def test_data_dir_is_directory(self):
        """DATA_DIR should be a directory."""
        from utils.config import DATA_DIR
        assert os.path.isdir(DATA_DIR)

    def test_logs_dir_is_directory(self):
        """LOGS_DIR should be a directory."""
        from utils.config import LOGS_DIR
        assert os.path.isdir(LOGS_DIR)
