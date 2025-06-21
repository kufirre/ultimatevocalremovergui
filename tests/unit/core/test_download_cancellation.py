"""
Unit tests for download cancellation functionality.

This module tests the enhanced download cancellation features that prevent
regression of the issue where downloads couldn't be cancelled mid-stream.
"""

from unittest.mock import Mock, mock_open, patch

import pytest
from PySide6.QtTest import QSignalSpy

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.download_worker import DownloadWorker
from uvr_pyside6_ui.core.model_downloader import download_model_file


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
        """
        CRITICAL Regression test: Downloads should be cancellable to prevent stuck states.
        """
        cancel_after_attempts = 3
        attempt_count = 0

        def eventual_cancel():
            nonlocal attempt_count
            attempt_count += 1
            return attempt_count >= cancel_after_attempts

        # Mock response
        mock_response = Mock()
        mock_response.headers = {"content-length": "999999999"}
        mock_response.iter_content.return_value = [b"x" * 8192] * 1000
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.unlink"):
                        success, message, config_path = download_model_file(
                            model_name="Large Model",
                            download_url="https://example.com/huge_model.pth",
                            model_type=ac.VR_ARCH_MODELS_KEY,
                            cancellation_callback=eventual_cancel,
                        )

                        # Should be cancelled before completion
                        assert success is False
                        assert "cancelled" in message.lower()
                        assert attempt_count == cancel_after_attempts
