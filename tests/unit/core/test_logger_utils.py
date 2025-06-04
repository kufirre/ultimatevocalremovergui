"""
Unit tests for logger_utils module.

Tests cover the UVRLogger class, logging configuration,
logger creation, and level management functionality.
"""

import logging
import os
from unittest.mock import Mock, patch

import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.logger_utils import UVRLogger, get_logger


@pytest.mark.unit
class TestUVRLogger:
    """Test cases for UVRLogger class."""

    def setup_method(self):
        """Reset logger state before each test."""
        UVRLogger._loggers = {}
        UVRLogger._configured = False
        # Reset logging to default state
        logging.disable(logging.NOTSET)

    def teardown_method(self):
        """Clean up after each test."""
        UVRLogger._loggers = {}
        UVRLogger._configured = False
        logging.disable(logging.NOTSET)

    def test_configure_logging_default(self):
        """Test configure_logging with default parameters."""
        with patch("logging.basicConfig") as mock_basic_config:
            UVRLogger.configure_logging()

            assert UVRLogger._configured is True
            mock_basic_config.assert_called_once()

            # Check that basicConfig was called with expected parameters
            call_args = mock_basic_config.call_args
            assert "level" in call_args.kwargs
            assert "format" in call_args.kwargs
            assert "datefmt" in call_args.kwargs
            assert call_args.kwargs["force"] is True

    def test_configure_logging_custom_level(self):
        """Test configure_logging with custom log level."""
        with patch("logging.basicConfig") as mock_basic_config:
            UVRLogger.configure_logging(log_level="DEBUG")

            assert UVRLogger._configured is True
            mock_basic_config.assert_called_once()

            call_args = mock_basic_config.call_args
            assert call_args.kwargs["level"] == logging.DEBUG

    def test_configure_logging_from_environment(self):
        """Test configure_logging uses environment variable."""
        with patch.dict(os.environ, {"UVR_LOG_LEVEL": "ERROR"}):
            with patch("logging.basicConfig") as mock_basic_config:
                UVRLogger.configure_logging()

                call_args = mock_basic_config.call_args
                assert call_args.kwargs["level"] == logging.ERROR

    def test_configure_logging_disable_console(self):
        """Test configure_logging with console disabled."""
        with patch("logging.basicConfig") as mock_basic_config:
            with patch("logging.disable") as mock_disable:
                UVRLogger.configure_logging(log_level="INFO", enable_console=False)

                mock_basic_config.assert_called_once()
                mock_disable.assert_called_once_with(logging.CRITICAL)

    def test_configure_logging_debug_level_keeps_console(self):
        """Test that DEBUG level keeps console even when disabled."""
        with patch("logging.basicConfig") as mock_basic_config:
            with patch("logging.disable") as mock_disable:
                UVRLogger.configure_logging(log_level="DEBUG", enable_console=False)

                mock_basic_config.assert_called_once()
                mock_disable.assert_not_called()

    def test_configure_logging_only_once(self):
        """Test that configure_logging only runs once."""
        with patch("logging.basicConfig") as mock_basic_config:
            UVRLogger.configure_logging()
            UVRLogger.configure_logging()  # Second call

            # Should only be called once
            assert mock_basic_config.call_count == 1

    def test_get_logger_creates_new_logger(self):
        """Test get_logger creates new logger instances."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = UVRLogger.get_logger("test_module")

            assert logger == mock_logger
            assert "test_module" in UVRLogger._loggers
            mock_get_logger.assert_called_once_with("uvr.test_module")

    def test_get_logger_returns_cached_logger(self):
        """Test get_logger returns cached logger for same name."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger1 = UVRLogger.get_logger("test_module")
            logger2 = UVRLogger.get_logger("test_module")

            assert logger1 == logger2
            assert mock_get_logger.call_count == 1  # Only called once

    def test_get_logger_auto_configures(self):
        """Test get_logger auto-configures logging if not configured."""
        with patch.object(UVRLogger, "configure_logging") as mock_configure:
            with patch("logging.getLogger") as mock_get_logger:
                mock_get_logger.return_value = Mock()

                UVRLogger.get_logger("test_module")

                mock_configure.assert_called_once()

    def test_get_logger_doesnt_auto_configure_if_configured(self):
        """Test get_logger doesn't auto-configure if already configured."""
        UVRLogger._configured = True

        with patch.object(UVRLogger, "configure_logging") as mock_configure:
            with patch("logging.getLogger") as mock_get_logger:
                mock_get_logger.return_value = Mock()

                UVRLogger.get_logger("test_module")

                mock_configure.assert_not_called()

    def test_set_level_updates_all_loggers(self):
        """Test set_level updates all existing loggers."""
        # Create some loggers first
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger1 = Mock()
            mock_logger2 = Mock()
            mock_get_logger.side_effect = [mock_logger1, mock_logger2]

            UVRLogger.get_logger("module1")
            UVRLogger.get_logger("module2")

            # Mock root logger
            mock_root_logger = Mock()
            with patch("logging.getLogger", return_value=mock_root_logger) as mock_root:
                UVRLogger.set_level("WARNING")

                mock_logger1.setLevel.assert_called_once_with(logging.WARNING)
                mock_logger2.setLevel.assert_called_once_with(logging.WARNING)
                mock_root_logger.setLevel.assert_called_once_with(logging.WARNING)

    def test_set_level_invalid_level_defaults_to_info(self):
        """Test set_level with invalid level defaults to INFO."""
        mock_logger = Mock()
        UVRLogger._loggers["test"] = mock_logger

        with patch("logging.getLogger") as mock_root:
            mock_root_logger = Mock()
            mock_root.return_value = mock_root_logger

            UVRLogger.set_level("INVALID_LEVEL")

            mock_logger.setLevel.assert_called_once_with(logging.INFO)
            mock_root_logger.setLevel.assert_called_once_with(logging.INFO)

    def test_disable_logging(self):
        """Test disable_logging disables all logging."""
        with patch("logging.disable") as mock_disable:
            UVRLogger.disable_logging()

            mock_disable.assert_called_once_with(logging.CRITICAL)

    def test_enable_logging(self):
        """Test enable_logging re-enables logging."""
        with patch("logging.disable") as mock_disable:
            UVRLogger.enable_logging()

            mock_disable.assert_called_once_with(logging.NOTSET)

    def test_logger_name_prefix(self):
        """Test that all loggers get 'uvr.' prefix."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_get_logger.return_value = Mock()

            UVRLogger.get_logger("model_data")
            UVRLogger.get_logger("processing_worker")

            expected_calls = [(("uvr.model_data",),), (("uvr.processing_worker",),)]
            assert mock_get_logger.call_args_list == expected_calls

    @pytest.mark.parametrize(
        "log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    def test_configure_logging_valid_levels(self, log_level):
        """Test configure_logging with all valid log levels."""
        with patch("logging.basicConfig") as mock_basic_config:
            UVRLogger.configure_logging(log_level=log_level)

            call_args = mock_basic_config.call_args
            expected_level = getattr(logging, log_level)
            assert call_args.kwargs["level"] == expected_level

    def test_logging_format_constants(self):
        """Test that logging uses constants from app_constants."""
        with patch("logging.basicConfig") as mock_basic_config:
            UVRLogger.configure_logging()

            call_args = mock_basic_config.call_args
            assert call_args.kwargs["format"] == ac.LOG_FORMAT
            assert call_args.kwargs["datefmt"] == ac.LOG_DATE_FORMAT


@pytest.mark.unit
class TestConvenienceFunction:
    """Test cases for convenience functions."""

    def test_get_logger_function(self):
        """Test the convenience get_logger function."""
        with patch.object(UVRLogger, "get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = get_logger("test_module")

            assert logger == mock_logger
            mock_get_logger.assert_called_once_with("test_module")


@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def setup_method(self):
        """Reset logger state before each test."""
        UVRLogger._loggers = {}
        UVRLogger._configured = False
        logging.disable(logging.NOTSET)

    def teardown_method(self):
        """Clean up after each test."""
        UVRLogger._loggers = {}
        UVRLogger._configured = False
        logging.disable(logging.NOTSET)

    def test_end_to_end_logging(self):
        """Test complete logging workflow."""
        # Configure logging
        UVRLogger.configure_logging(log_level="DEBUG")

        # Get a logger
        logger = UVRLogger.get_logger("test_integration")

        # Verify logger properties
        assert logger.name == "uvr.test_integration"
        assert UVRLogger._configured is True
        assert "test_integration" in UVRLogger._loggers

    def test_multiple_loggers_same_configuration(self):
        """Test that multiple loggers share the same configuration."""
        UVRLogger.configure_logging(log_level="WARNING")

        logger1 = UVRLogger.get_logger("module1")
        logger2 = UVRLogger.get_logger("module2")

        # Both should be different instances but same configuration
        assert logger1 != logger2
        assert logger1.name == "uvr.module1"
        assert logger2.name == "uvr.module2"

    def test_level_change_affects_all_loggers(self):
        """Test that changing level affects all existing loggers."""
        logger1 = UVRLogger.get_logger("module1")
        logger2 = UVRLogger.get_logger("module2")

        # Change level
        UVRLogger.set_level("ERROR")

        # Both loggers should have new level
        assert logger1.level == logging.ERROR
        assert logger2.level == logging.ERROR

    @pytest.mark.edge_case
    def test_configure_after_getting_loggers(self):
        """Test configuring logging after getting loggers."""
        # Get logger first (will auto-configure)
        logger = UVRLogger.get_logger("test_module")

        # Try to configure again
        UVRLogger.configure_logging(log_level="ERROR")

        # Should still be configured and working
        assert UVRLogger._configured is True
        assert logger.name == "uvr.test_module"

    def test_environment_variable_override(self):
        """Test that environment variable overrides default log level."""
        with patch.dict(os.environ, {"UVR_LOG_LEVEL": "CRITICAL"}):
            UVRLogger.configure_logging()

            logger = UVRLogger.get_logger("test_env")

            # Should use CRITICAL level from environment
            assert logging.getLogger().level == logging.CRITICAL

    def test_logger_caching_persistence(self):
        """Test that logger caching persists across multiple calls."""
        # Get same logger multiple times
        logger1 = UVRLogger.get_logger("persistent")
        logger2 = UVRLogger.get_logger("persistent")
        logger3 = UVRLogger.get_logger("persistent")

        # All should be the same instance
        assert logger1 is logger2
        assert logger2 is logger3
        assert len(UVRLogger._loggers) == 1

    @pytest.mark.edge_case
    def test_empty_logger_name(self):
        """Test handling of empty logger name."""
        logger = UVRLogger.get_logger("")

        assert logger.name == "uvr."
        assert "" in UVRLogger._loggers

    @pytest.mark.edge_case
    def test_logger_name_with_special_characters(self):
        """Test logger name with special characters."""
        special_name = "test.module-with_special.chars"
        logger = UVRLogger.get_logger(special_name)

        assert logger.name == f"uvr.{special_name}"
        assert special_name in UVRLogger._loggers
