"""
Unit tests for download cancellation functionality.

This module tests the enhanced download cancellation features that prevent
regression of the issue where downloads couldn't be cancelled mid-stream.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtTest import QSignalSpy

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.download_worker import DownloadManager, DownloadWorker
from uvr_pyside6_ui.core.model_downloader import download_model_file
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter


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
