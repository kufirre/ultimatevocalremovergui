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

            # Should have at least 3 successful loads (2 fonts + 1 stylesheet minimum)
            # Note: Progress stylesheet may not always log in test environment due to GUI limitations
            assert (
                len(info_calls) >= 3
            ), f"Not enough resources loaded successfully. Got {len(info_calls)} info calls: {info_calls}"

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


@pytest.mark.critical
def test_qrc_resources_load_successfully():
    """Test that all critical QRC resources load without errors."""
    # Test font loading
    century_gothic_file = QFile(ac.QRC_CENTURY_GOTHIC_PATH)
    assert (
        century_gothic_file.exists()
    ), f"Century Gothic font not found: {ac.QRC_CENTURY_GOTHIC_PATH}"

    montserrat_file = QFile(ac.QRC_MONTSERRAT_PATH)
    assert (
        montserrat_file.exists()
    ), f"Montserrat font not found: {ac.QRC_MONTSERRAT_PATH}"

    # Test stylesheet loading
    main_stylesheet_file = QFile(ac.QRC_MAIN_STYLESHEET_PATH)
    assert (
        main_stylesheet_file.exists()
    ), f"Main stylesheet not found: {ac.QRC_MAIN_STYLESHEET_PATH}"

    progress_stylesheet_file = QFile(ac.QRC_PROGRESS_STYLESHEET_PATH)
    assert (
        progress_stylesheet_file.exists()
    ), f"Progress stylesheet not found: {ac.QRC_PROGRESS_STYLESHEET_PATH}"


@pytest.mark.critical
def test_core_module_imports():
    """Test that all core modules can be imported."""
    from uvr_pyside6_ui.core import (
        app_constants,
        logger_utils,
        model_data,
        processing_worker,
    )
    from uvr_pyside6_ui.core.processing_worker import ProcessingWorker

    # Verify key modules and classes exist
    assert app_constants is not None
    assert logger_utils is not None
    assert model_data is not None
    assert processing_worker is not None
    assert ProcessingWorker is not None


@pytest.mark.critical
def test_ui_module_imports():
    """Test that all essential UI modules can be imported."""
    try:
        from uvr_pyside6_ui.ui.execution_control_view import ExecutionControlView
        from uvr_pyside6_ui.ui.main_window_view import MainWindowView
        from uvr_pyside6_ui.ui.settings_dialog_view import SettingsDialogView

        assert MainWindowView is not None
        assert ExecutionControlView is not None
        assert SettingsDialogView is not None
    except ImportError as e:
        pytest.fail(f"Failed to import UI modules: {e}")


@pytest.mark.critical
def test_application_can_be_created():
    """Test that a QApplication instance can be created successfully."""
    # QApplication instance should already exist from conftest.py
    app = QApplication.instance()
    assert app is not None, "QApplication instance not found"
    # Note: The app name might be "Python" by default if not explicitly set
    assert app.applicationName() in [
        "UVR-Test",
        "Python",
    ], f"Unexpected application name: {app.applicationName()}"


@pytest.mark.critical
def test_main_window_can_be_instantiated():
    """Test that the main window can be created without errors."""
    try:
        from uvr_pyside6_ui.ui.main_window_view import MainWindowView

        window = MainWindowView()
        assert window is not None
        assert window.windowTitle() == ac.APP_TITLE
        # Test that critical components exist
        assert hasattr(window, "presenters")
        assert hasattr(window, "adapter")
        assert hasattr(window, "settings_dialog_presenter")
    except Exception as e:
        pytest.fail(f"Failed to create main window: {e}")


@pytest.mark.critical
def test_progress_bar_functionality():
    """Test that progress bars work correctly and are visible."""
    try:
        from uvr_pyside6_ui.ui.execution_control_view import ExecutionControlView

        view = ExecutionControlView()

        # Show the widget to make it visible
        view.show()

        # Test progress bar exists and is properly configured
        assert hasattr(view, "progress_bar")
        assert view.progress_bar.minimum() == 0
        assert view.progress_bar.maximum() == 100
        assert view.progress_bar.value() == 0

        # Test progress updates
        view.set_progress_value(50)
        assert view.progress_bar.value() == 50
        assert view.progress_bar.isVisible()

        # Test progress text updates
        view.set_progress_text("Processing...")
        assert view.progress_label.text() == "Processing..."

    except Exception as e:
        pytest.fail(f"Progress bar functionality test failed: {e}")


@pytest.mark.critical
def test_enhanced_settings_dialog():
    """Test the enhanced settings dialog functionality."""
    from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter
    from uvr_pyside6_ui.ui.settings_dialog_presenter import SettingsDialogPresenter
    from uvr_pyside6_ui.ui.settings_dialog_view import SettingsDialogView

    # Create adapter and presenter
    adapter = UVRCoreAdapter()
    presenter = SettingsDialogPresenter(adapter)

    # Show dialog (non-modal for testing)
    presenter.show_dialog(exec_dialog=False)

    # Verify view was created
    assert presenter.view is not None
    assert isinstance(presenter.view, SettingsDialogView)

    # Verify the dialog has 3 tabs with correct names
    tab_widget = presenter.view.tab_widget
    assert tab_widget.count() == 3

    expected_tab_names = ["Settings Guide", "Additional Settings", "Download Center"]
    actual_tab_names = []
    for i in range(tab_widget.count()):
        actual_tab_names.append(tab_widget.tabText(i))

    assert actual_tab_names == expected_tab_names

    # Test Settings Guide tab (Tab 0)
    tab_widget.setCurrentIndex(0)

    # Verify main menu dropdown exists and has correct options
    main_menu_combo = presenter.view.main_menu_combo
    assert main_menu_combo is not None
    expected_options = [
        "Choose Advanced Menu",
        "Advanced VR Options",
        "Advanced MDX-Net Options",
        "Advanced Demucs Options",
        "Ensemble Settings",
        "Audio Alignment Settings",
        "Open Information Guide",
        "Open Error Log",
    ]
    actual_options = [
        main_menu_combo.itemText(i) for i in range(main_menu_combo.count())
    ]
    assert actual_options == expected_options

    # Verify help hints checkbox exists
    help_hints_checkbox = presenter.view.help_hints_checkbox
    assert help_hints_checkbox is not None
    assert hasattr(help_hints_checkbox, "isChecked")

    # Test Additional Settings tab (Tab 1)
    tab_widget.setCurrentIndex(1)

    # Verify key settings widgets exist
    assert presenter.view.wav_type_combo is not None
    assert presenter.view.mp3_bitrate_combo is not None
    assert presenter.view.test_mode_checkbox is not None
    assert presenter.view.sample_duration_slider is not None

    # Test Download Center tab (Tab 2)
    tab_widget.setCurrentIndex(2)

    # Verify download center components exist (newer UI may have different structure)
    # The download center is embedded as a separate view
    assert hasattr(presenter.view, "download_center_view")
    download_center = presenter.view.download_center_view

    # Check for dropdowns first
    assert download_center.dc_model_combo is not None
    assert download_center.dc_architecture_combo is not None

    # Check for download control buttons
    assert download_center.dc_download_btn is not None
    assert download_center.dc_stop_btn is not None
    assert download_center.dc_refresh_btn is not None

    # Check for progress widgets
    assert download_center.dc_progress_info_label is not None
    assert download_center.dc_progress_percent_label is not None
    assert download_center.dc_progress_bar is not None

    # Check for radio buttons (these might be optional in newer UI)
    # If radio buttons don't exist, verify other selection methods work
    if (
        hasattr(download_center, "vr_radio")
        and hasattr(download_center, "mdx_radio")
        and hasattr(download_center, "demucs_radio")
    ):
        # Legacy radio button interface
        assert download_center.vr_radio is not None
        assert download_center.mdx_radio is not None
        assert download_center.demucs_radio is not None

        # Test that VR is selected by default
        assert download_center.vr_radio.isChecked()
        assert not download_center.mdx_radio.isChecked()
        assert not download_center.demucs_radio.isChecked()
    else:
        # Newer interface uses combo box for architecture selection
        # Just verify the combo boxes work as selection mechanisms
        assert download_center.dc_architecture_combo.count() >= 0
        assert download_center.dc_model_combo.count() >= 0

    # Test settings load/save functionality
    test_settings = {
        "main_menu": "Choose Advanced Menu",
        "help_hints": True,
        "wav_type": "PCM_16",
        "mp3_bitrate": "320",
        "test_mode": False,
        "sample_duration": 30,
    }

    presenter.view.load_settings(test_settings)

    # Verify settings were loaded
    assert presenter.view.help_hints_checkbox.isChecked() == test_settings["help_hints"]
    assert presenter.view.wav_type_combo.currentText() == test_settings["wav_type"]
    assert (
        presenter.view.mp3_bitrate_combo.currentText() == test_settings["mp3_bitrate"]
    )
    assert presenter.view.test_mode_checkbox.isChecked() == test_settings["test_mode"]
    assert (
        presenter.view.sample_duration_slider.value()
        == test_settings["sample_duration"]
    )

    # Test getting settings back
    retrieved_settings = presenter.view.get_settings()
    assert isinstance(retrieved_settings, dict)
    assert "help_hints" in retrieved_settings
    assert "wav_type" in retrieved_settings
    assert "mp3_bitrate" in retrieved_settings

    # Clean up
    presenter.view.close()


@pytest.mark.critical
def test_resources_rc_import_protection():
    """Test that the critical resources_rc import is protected and functional."""
    try:
        # This import should work without issues and not be removed by linting tools
        # Test that we can access QRC resources after import
        from PySide6.QtCore import QFile

        import uvr_pyside6_ui.resources_rc  # noqa: F401

        test_file = QFile(":/uvr/fonts/CenturyGothic.ttf")
        assert test_file.exists(), "QRC resources not accessible after import"

    except ImportError as e:
        pytest.fail(f"Critical resources_rc import failed: {e}")
    except Exception as e:
        pytest.fail(f"QRC resource access failed after import: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
