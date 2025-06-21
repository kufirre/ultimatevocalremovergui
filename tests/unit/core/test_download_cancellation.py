"""
Unit tests for download cancellation functionality.

This module tests the enhanced download cancellation features that prevent
regression of the issue where downloads couldn't be cancelled mid-stream.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtTest import QSignalSpy

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.download_worker import DownloadManager, DownloadWorker
from uvr_pyside6_ui.core.model_downloader import download_model_file
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter
from uvr_pyside6_ui.ui.download_center_presenter import DownloadCenterPresenter


@pytest.mark.unit
@pytest.mark.download
@pytest.mark.cancellation
class TestDownloadCancellation:
    """Test cases for download cancellation functionality."""

    def test_download_cancellation_before_start(self):
        """Test cancellation before download starts."""

        # Create a cancellation callback that immediately returns True
        def immediate_cancel():
            return True

        with patch("requests.get") as mock_get:
            success, message, config_path = download_model_file(
                model_name="Test Model",
                download_url="https://example.com/model.pth",
                model_type=ac.VR_ARCH_MODELS_KEY,
                cancellation_callback=immediate_cancel,
            )

            # Should be cancelled before any network request
            assert success is False
            assert "cancelled" in message.lower()
            assert config_path is None
            mock_get.assert_not_called()

    def test_download_worker_cancellation_integration(self):
        """Test cancellation through DownloadWorker."""
        worker = DownloadWorker(
            "Test Model", "https://example.com/model.pth", ac.VR_ARCH_MODELS_KEY
        )

        finished_spy = QSignalSpy(worker.finished)

        # Mock the download function to check cancellation
        def mock_download(*args, **kwargs):
            cancellation_callback = kwargs.get("cancellation_callback")
            if cancellation_callback and cancellation_callback():
                return False, "Download cancelled by user", None
            return True, "/path/to/model.pth", None

        with patch(
            "uvr_pyside6_ui.core.download_worker.model_downloader.download_model_file",
            side_effect=mock_download,
        ):
            # Cancel before run
            worker.cancel()
            worker.run()

            # Should emit finished signal with cancellation
            assert finished_spy.count() == 1
            signal_args = finished_spy.at(0)
            assert signal_args[0] is False  # success
            assert "cancelled" in signal_args[3].lower()  # message


@pytest.mark.regression
@pytest.mark.download
@pytest.mark.cancellation
class TestDownloadCancellationRegression:
    """Regression tests to prevent download cancellation issues from reoccurring."""

    def test_cancellation_prevents_stuck_downloads(self):
        """Test that cancellation prevents downloads from getting stuck."""

        # Create a mock download function that simulates a slow download
        def slow_download_function(
            url, local_path, progress_callback=None, cancellation_callback=None
        ):
            # Simulate slow download with cancellation check
            for i in range(10):
                if cancellation_callback and cancellation_callback():
                    return "Download cancelled by user request"
                time.sleep(0.01)  # Simulate work
                if progress_callback:
                    progress_callback("test_model", i * 10)
            return str(local_path)  # Success

        # Patch the download function
        with patch(
            "src.uvr_pyside6_ui.core.model_downloader.download_model_file",
            side_effect=slow_download_function,
        ):
            # Create a download manager and start a download
            manager = DownloadManager()

            # Start download
            worker = manager.start_download(
                model_name="test_model.pth",
                download_url="http://example.com/test_model.pth",
                model_type="VR Arch",
            )

            # Let it start
            time.sleep(0.02)

            # Cancel the download
            manager.cancel_all_downloads()

            # Wait for completion
            time.sleep(0.1)

            # Verify the worker was cancelled
            assert worker._is_cancelled


class TestAdapterDownloadCancellation:
    """Test the UVRCoreAdapter download cancellation functionality."""

    def test_adapter_cancel_downloads_method(self):
        """Test that the adapter's cancel_downloads method works."""
        adapter = UVRCoreAdapter()

        # Test that the method exists and can be called
        adapter.cancel_downloads()

        # Verify the download manager has the cancel method
        assert hasattr(adapter.download_manager, "cancel_all_downloads")

        # Test with mock to verify the call is passed through
        with patch.object(
            adapter.download_manager, "cancel_all_downloads"
        ) as mock_cancel:
            adapter.cancel_downloads()
            mock_cancel.assert_called_once()

    def test_multi_file_demucs_download_cancellation(self):
        """Test that multi-file Demucs downloads can be cancelled properly."""
        # Create adapter
        adapter = UVRCoreAdapter()

        # Mock the download manager
        mock_download_manager = MagicMock()
        adapter.download_manager = mock_download_manager

        # Set up a multi-file Demucs download
        multi_file_info = {
            "model1.th": "url1",
            "model2.th": "url2",
            "config.yaml": "url3",
        }

        # Start multi-file download
        adapter.download_model("Demucs", "htdemucs_ft", multi_file_info)

        # Verify state was set up
        assert adapter._multi_file_download_state is not None
        assert adapter._multi_file_download_state["total_files"] == 3
        assert adapter._multi_file_download_state["model_display_name"] == "htdemucs_ft"

        # Mock the download finished signal
        download_finished_signal = MagicMock()
        adapter.download_finished.connect(download_finished_signal)

        # Cancel the download
        adapter.cancel_downloads()

        # Verify cancellation was requested
        mock_download_manager.cancel_all_downloads.assert_called_once()

        # Verify cancellation signal was emitted
        download_finished_signal.assert_called_once()
        args = download_finished_signal.call_args[0]
        assert args[0] == "Demucs"  # model_type
        assert args[1] == "htdemucs_ft"  # model_name
        assert args[2] is False  # success = False
        assert "cancelled" in args[3].lower()  # message contains "cancelled"

        # Verify state was reset
        assert adapter._multi_file_download_state is None

    def test_multi_file_cancellation_emits_signal(self):
        """Test that multi-file download cancellation emits proper signal."""
        adapter = UVRCoreAdapter()

        # Set up multi-file download state
        adapter._multi_file_download_state = {
            "model_type_ui_name": "Demucs",
            "model_display_name": "test_model",
            "all_file_paths": [],
        }

        # Mock the cleanup method to avoid file operations
        with patch.object(adapter, "_cleanup_multi_file_download"):
            # Connect to signal
            signal_received = []
            adapter.download_finished.connect(
                lambda mt, mn, success, msg: signal_received.append(
                    (mt, mn, success, msg)
                )
            )

            # Cancel downloads
            adapter.cancel_downloads()

            # Verify signal was emitted
            assert len(signal_received) == 1
            signal_args = signal_received[0]
            assert signal_args[0] == "Demucs"  # model_type_ui_name
            assert signal_args[1] == "test_model"  # model_display_name
            assert signal_args[2] is False  # success
            assert "cancelled by user" in signal_args[3]  # message

    def test_single_file_downloads_not_affected(self):
        """Test that single file downloads (VR/MDX) are not affected by multi-file logic."""
        adapter = UVRCoreAdapter()

        # Mock download manager
        mock_download_manager = MagicMock()
        adapter.download_manager = mock_download_manager

        # Test single file VR download
        adapter.download_model(
            "VR Arch", "test_vr_model", "http://example.com/model.pth"
        )

        # Verify no multi-file state was created
        assert adapter._multi_file_download_state is None

        # Verify download was started normally
        mock_download_manager.start_download.assert_called_once()


class TestDownloadCancellationUI:
    """Test UI behavior for download cancellation."""

    def test_cancellation_message_shows_cancelled_not_failed(self):
        """Test that user cancellation shows 'cancelled' message, not 'failed'."""
        # Create presenter with mocked dependencies
        adapter = MagicMock()
        settings_file = Path("/tmp/test_settings.json")
        presenter = DownloadCenterPresenter(adapter, settings_file)

        # Mock the view
        mock_view = MagicMock()
        presenter.view = mock_view
        presenter._is_download_in_progress = True

        # Simulate cancellation message
        cancellation_message = "🚫 Download cancelled by user"
        presenter._on_adapter_download_finished(
            "Demucs", "test_model", False, cancellation_message
        )

        # Verify UI shows cancellation, not failure
        mock_view.dc_progress_info_label.setText.assert_called_with(
            "🚫 Download cancelled"
        )
        mock_view.dc_progress_percent_label.setText.assert_called_with("Cancelled")

    def test_actual_failure_shows_failed_message(self):
        """Test that actual download failures show 'failed' message."""
        # Create presenter with mocked dependencies
        adapter = MagicMock()
        settings_file = Path("/tmp/test_settings.json")
        presenter = DownloadCenterPresenter(adapter, settings_file)

        # Mock the view
        mock_view = MagicMock()
        presenter.view = mock_view
        presenter._is_download_in_progress = True

        # Simulate actual failure message
        failure_message = "Network error: 404 Not Found"
        presenter._on_adapter_download_finished(
            "Demucs", "test_model", False, failure_message
        )

        # Verify UI shows failure
        mock_view.dc_progress_info_label.setText.assert_called_with(
            "❌ Download failed"
        )
        mock_view.dc_progress_percent_label.setText.assert_called_with("Failed")

    @patch("uvr_pyside6_ui.ui.download_center_presenter.logger")
    def test_cancellation_logged_as_info_not_error(self, mock_logger):
        """Test that cancellation is logged as INFO, not ERROR."""
        # Create presenter with mocked dependencies
        adapter = MagicMock()
        settings_file = Path("/tmp/test_settings.json")
        presenter = DownloadCenterPresenter(adapter, settings_file)

        # Mock the view
        mock_view = MagicMock()
        presenter.view = mock_view
        presenter._is_download_in_progress = True

        # Simulate cancellation
        cancellation_message = "🚫 Download cancelled by user"
        presenter._on_adapter_download_finished(
            "Demucs", "test_model", False, cancellation_message
        )

        # Verify cancellation is logged as INFO
        mock_logger.info.assert_called_with(
            "Download cancelled for test_model: 🚫 Download cancelled by user"
        )
        # Verify no error logging for cancellation
        mock_logger.error.assert_not_called()

    def test_stop_button_calls_adapter_cancel(self):
        """Test that stop button calls adapter.cancel_downloads()."""
        # Create presenter
        adapter = MagicMock()
        settings_file = Path("/tmp/test_settings.json")
        presenter = DownloadCenterPresenter(adapter, settings_file)

        # Simulate stop button click
        presenter._on_dc_stop_button_clicked()

        # Verify adapter cancel was called
        adapter.cancel_downloads.assert_called_once()


class TestMultiFileDownloadCleanup:
    """Test multi-file download coordination and cleanup."""

    def test_file_path_prediction_works(self):
        """Test that file paths are predicted correctly for cleanup."""
        adapter = UVRCoreAdapter()

        # Mock the project models directory
        with patch.object(adapter, "_get_project_models_dir") as mock_get_dir:
            mock_get_dir.return_value = Path("/test/models")

            # Test Demucs v3/v4 model path prediction (the problematic case)
            demucs_v4_path = adapter._predict_download_path(
                "test_model", "test.yaml", ac.DEMUCS_MODELS_KEY, True
            )
            assert demucs_v4_path == Path(
                "/test/models/Demucs_Models/v3_v4_repo/test.yaml"
            )

            # Test regular Demucs model path prediction
            demucs_path = adapter._predict_download_path(
                "test_model", "test.th", ac.DEMUCS_MODELS_KEY, False
            )
            assert demucs_path == Path("/test/models/Demucs_Models/test.th")

    def test_multi_file_state_initialization(self):
        """Test that multi-file download state is set up correctly."""
        adapter = UVRCoreAdapter()

        # Mock dependencies
        with patch.object(
            adapter, "_get_project_models_dir"
        ) as mock_get_dir, patch.object(
            adapter.download_manager, "start_download"
        ) as mock_start:

            mock_get_dir.return_value = Path("/test/models")

            # Simulate multi-file Demucs download
            download_info = {
                "model1.th": "url1",
                "model2.th": "url2",
                "config.yaml": "url3",
            }

            adapter.download_model("Demucs", "htdemucs_v4_ft", download_info)

            # Verify state was set up correctly
            state = adapter._multi_file_download_state
            assert state is not None
            assert state["total_files"] == 3
            assert state["model_display_name"] == "htdemucs_v4_ft"
            assert len(state["all_file_paths"]) == 3

    def test_cleanup_removes_tracked_files(self):
        """Test that cleanup removes tracked files properly."""
        adapter = UVRCoreAdapter()

        # Create temporary files to simulate downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            test_file1 = temp_path / "test1.th"
            test_file2 = temp_path / "test2.yaml"
            test_file1.write_text("test")
            test_file2.write_text("test")

            # Set up state with files to clean
            state = {"downloaded_files": [test_file1], "all_file_paths": [test_file2]}

            # Test cleanup
            adapter._cleanup_multi_file_download(state)

            # Verify files were removed
            assert not test_file1.exists()
            assert not test_file2.exists()

    def test_yaml_cleanup_prevents_model_not_found_error(self):
        """Test that YAML files are cleaned up to prevent 'model not found' errors."""
        adapter = UVRCoreAdapter()

        # Create temporary directory structure like real models directory
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            demucs_dir = models_dir / "Demucs_Models" / "v3_v4_repo"
            demucs_dir.mkdir(parents=True)

            # Create a YAML file that would cause "model not found" issues
            yaml_file = demucs_dir / "htdemucs_v4_ft.yaml"
            yaml_file.write_text("test config")

            # Simulate cleanup of cancelled download
            state = {"downloaded_files": [], "all_file_paths": [yaml_file]}

            adapter._cleanup_multi_file_download(state)

            # Verify YAML file was removed
            assert not yaml_file.exists()

    def test_download_finished_handler_prevents_state_issues(self):
        """Test that download finished handler properly handles state after cancellation."""
        adapter = UVRCoreAdapter()

        # Set up multi-file download state
        adapter._multi_file_download_state = {
            "total_files": 2,
            "completed_files": 0,
            "failed_files": 0,
            "model_type_ui_name": "Demucs",
            "model_display_name": "test_model",
            "downloaded_files": [],
            "all_file_paths": [],
        }

        # Cancel downloads (this should reset the state)
        adapter.cancel_downloads()

        # Verify state was reset
        assert adapter._multi_file_download_state is None

        # Now simulate a download finished event that might come after cancellation
        # This should not cause errors (the main protection we want)
        signal_received = []
        adapter.download_finished.connect(
            lambda mt, mn, success, msg: signal_received.append((mt, mn, success, msg))
        )

        try:
            adapter._on_download_finished(
                success=False,
                model_path="/test/model.th",
                config_path="",
                message="Download cancelled",
                model_type="Demucs",
            )
            # If we get here without exception, the handler is robust
            handler_is_robust = True
        except Exception:
            handler_is_robust = False

        # The main protection is that no exception occurs
        assert (
            handler_is_robust
        ), "Download finished handler should not crash after cancellation"


class TestDownloadCancellationIntegration:
    """Integration tests for the complete cancellation workflow."""

    def test_complete_cancellation_workflow(self):
        """Test the complete workflow from adapter to presenter."""
        # Create real adapter and presenter
        adapter = UVRCoreAdapter()
        settings_file = Path("/tmp/test_settings.json")
        presenter = DownloadCenterPresenter(adapter, settings_file)

        # Mock view and download manager
        mock_view = MagicMock()
        mock_download_manager = MagicMock()
        presenter.view = mock_view
        adapter.download_manager = mock_download_manager

        # Set up multi-file download
        adapter._multi_file_download_state = {
            "model_type_ui_name": "Demucs",
            "model_display_name": "htdemucs_v4_ft",
            "all_file_paths": [],
        }

        # Connect signals
        adapter.download_finished.connect(presenter._on_adapter_download_finished)

        # Simulate cancellation workflow
        presenter._on_dc_stop_button_clicked()  # User clicks stop

        # Verify the workflow completed
        # 1. Download manager cancellation called
        mock_download_manager.cancel_all_downloads.assert_called_once()

        # 2. UI shows cancellation message (from the signal handler)
        mock_view.dc_progress_info_label.setText.assert_any_call(
            "🚫 Download cancelled"
        )
