#!/usr/bin/env python3
"""Test suite for critical application startup functionality.

This module tests core functionality that must work for the application to start properly,
including QRC resource loading, font loading, and stylesheet loading.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QFile, QIODevice, QResource
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

import uvr_pyside6_ui.resources_rc  # noqa: F401 - Required to register QRC resources
from uvr_pyside6_ui.core import app_constants as ac


@pytest.mark.unit
@pytest.mark.critical
class TestApplicationStartup:
    """Test critical application startup functionality."""

    def test_qrc_resources_are_accessible(self):
        """Test that all required QRC resources are accessible."""
        # Critical resources that must be available
        critical_resources = [
            ac.QRC_CENTURY_GOTHIC_PATH,
            ac.QRC_MONTSERRAT_PATH,
            ac.QRC_MAIN_STYLESHEET_PATH,
            ac.QRC_PROGRESS_STYLESHEET_PATH,
        ]

        for resource_path in critical_resources:
            # Test with QFile
            qfile = QFile(resource_path)
            assert qfile.exists(), f"QRC resource not found: {resource_path}"

            # Test with QResource
            qresource = QResource(resource_path)
            assert qresource.isValid(), f"QRC resource invalid: {resource_path}"
            assert qresource.size() > 0, f"QRC resource empty: {resource_path}"

    def test_fonts_can_be_loaded(self):
        """Test that fonts can be loaded from QRC resources."""
        app = QApplication.instance() or QApplication(sys.argv)

        # Test Century Gothic font
        font_id = QFontDatabase.addApplicationFont(ac.QRC_CENTURY_GOTHIC_PATH)
        assert font_id != -1, f"Failed to load font: {ac.QRC_CENTURY_GOTHIC_PATH}"

        # Test Montserrat font
        font_id = QFontDatabase.addApplicationFont(ac.QRC_MONTSERRAT_PATH)
        assert font_id != -1, f"Failed to load font: {ac.QRC_MONTSERRAT_PATH}"

    def test_stylesheets_can_be_read(self):
        """Test that stylesheets can be read from QRC resources."""
        # Test main stylesheet
        qss_file = QFile(ac.QRC_MAIN_STYLESHEET_PATH)
        assert qss_file.open(
            QIODevice.ReadOnly | QIODevice.Text
        ), f"Cannot open stylesheet: {ac.QRC_MAIN_STYLESHEET_PATH}"

        content = qss_file.readAll()
        assert len(content) > 0, "Main stylesheet is empty"
        qss_file.close()

        # Test progress bar stylesheet
        progress_qss_file = QFile(ac.QRC_PROGRESS_STYLESHEET_PATH)
        assert progress_qss_file.open(
            QIODevice.ReadOnly | QIODevice.Text
        ), f"Cannot open progress stylesheet: {ac.QRC_PROGRESS_STYLESHEET_PATH}"

        progress_content = progress_qss_file.readAll()
        assert len(progress_content) > 0, "Progress stylesheet is empty"
        progress_qss_file.close()

    def test_resources_rc_module_is_importable(self):
        """Test that the resources_rc module can be imported."""
        try:
            import uvr_pyside6_ui.resources_rc

            assert uvr_pyside6_ui.resources_rc is not None
        except ImportError as e:
            pytest.fail(f"Cannot import resources_rc module: {e}")

    @patch("uvr_pyside6_ui.main.logger")
    def test_main_run_function_loads_resources_without_warnings(self, mock_logger):
        """Test that the main run function loads resources without warnings."""
        # Mock QApplication to prevent actual GUI startup
        with patch("uvr_pyside6_ui.main.QApplication") as mock_qapp, patch(
            "uvr_pyside6_ui.main.MainWindowView"
        ) as mock_window, patch("sys.exit"):

            mock_app_instance = MagicMock()
            mock_qapp.return_value = mock_app_instance
            mock_window_instance = MagicMock()
            mock_window.return_value = mock_window_instance

            # Import and run the main function
            from uvr_pyside6_ui.main import run

            # This should complete without errors
            try:
                run()
            except SystemExit:
                pass  # Expected due to sys.exit() call

            # Verify that success messages were logged (no warnings)
            info_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "Successfully loaded" in str(call)
            ]

            # Should have 4 successful loads (2 fonts + 2 stylesheets)
            assert len(info_calls) >= 4, "Not all resources loaded successfully"

            # Verify no warning calls about failed resource loading
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if "Failed to" in str(call)
            ]
            assert (
                len(warning_calls) == 0
            ), f"Resource loading warnings: {warning_calls}"


@pytest.mark.integration
class TestCriticalPathIntegration:
    """Integration tests for critical application paths."""

    def test_application_can_initialize_gui_components(self):
        """Test that the application can initialize core GUI components."""
        app = QApplication.instance() or QApplication(sys.argv)

        # This should not raise any exceptions
        try:
            from uvr_pyside6_ui.ui.main_window_view import MainWindowView

            window = MainWindowView()
            assert window is not None
            # Don't show the window in tests
        except Exception as e:
            pytest.fail(f"Failed to initialize main window: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
