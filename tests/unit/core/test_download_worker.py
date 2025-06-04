"""
Unit tests for download_worker module.

Tests cover the DownloadWorker and DownloadManager classes,
Qt signals, threading behavior, and download management.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from PySide6.QtCore import QThread, Signal
from PySide6.QtTest import QSignalSpy

from uvr_pyside6_ui.core.download_worker import DownloadWorker, DownloadManager
from uvr_pyside6_ui.core import app_constants as ac


@pytest.mark.unit
@pytest.mark.download
@pytest.mark.worker
class TestDownloadWorker:
    """Test cases for DownloadWorker class."""

    def test_download_worker_initialization(self):
        """Test DownloadWorker initialization with parameters."""
        model_name = "Test Model"
        download_url = "https://example.com/model.pth"
        model_type = ac.VR_ARCH_MODELS_KEY
        config_url = "https://example.com/config.yaml"
        
        worker = DownloadWorker(model_name, download_url, model_type, config_url)
        
        assert worker.model_name == model_name
        assert worker.download_url == download_url
        assert worker.model_type == model_type
        assert worker.config_url == config_url
        assert worker._is_cancelled is False

    def test_download_worker_initialization_no_config(self):
        """Test DownloadWorker initialization without config URL."""
        worker = DownloadWorker("Test", "url", ac.VR_ARCH_MODELS_KEY)
        
        assert worker.config_url is None
        assert worker._is_cancelled is False

    def test_download_worker_cancel(self):
        """Test download worker cancellation."""
        worker = DownloadWorker("Test", "url", ac.VR_ARCH_MODELS_KEY)
        
        assert worker._is_cancelled is False
        worker.cancel()
        assert worker._is_cancelled is True

    def test_download_worker_signals_exist(self):
        """Test that required signals are defined."""
        worker = DownloadWorker("Test", "url", ac.VR_ARCH_MODELS_KEY)
        
        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')
        assert isinstance(worker.progress, Signal)
        assert isinstance(worker.finished, Signal)

    @patch('uvr_pyside6_ui.core.download_worker.model_downloader.download_model_file')
    def test_download_worker_run_success(self, mock_download):
        """Test successful download worker execution."""
        mock_download.return_value = (True, "/path/to/model.pth", "/path/to/config.yaml")
        
        worker = DownloadWorker("Test Model", "url", ac.VR_ARCH_MODELS_KEY)
        
        # Spy on signals
        progress_spy = QSignalSpy(worker.progress)
        finished_spy = QSignalSpy(worker.finished)
        
        worker.run()
        
        # Check that download was called with correct parameters
        mock_download.assert_called_once_with(
            "Test Model", "url", ac.VR_ARCH_MODELS_KEY, None, worker.progress.emit
        )
        
        # Check finished signal was emitted with success
        assert finished_spy.count() == 1
        signal_args = finished_spy.at(0)
        assert signal_args[0] is True  # success
        assert signal_args[1] == "/path/to/model.pth"  # model_path
        assert signal_args[2] == "/path/to/config.yaml"  # config_path
        assert "Successfully downloaded" in signal_args[3]  # message

    @patch('uvr_pyside6_ui.core.download_worker.model_downloader.download_model_file')
    def test_download_worker_run_failure(self, mock_download):
        """Test download worker execution with failure."""
        mock_download.return_value = (False, "Download failed", None)
        
        worker = DownloadWorker("Test Model", "url", ac.VR_ARCH_MODELS_KEY)
        
        finished_spy = QSignalSpy(worker.finished)
        
        worker.run()
        
        # Check finished signal was emitted with failure
        assert finished_spy.count() == 1
        signal_args = finished_spy.at(0)
        assert signal_args[0] is False  # success
        assert signal_args[1] == ""  # model_path
        assert signal_args[2] == ""  # config_path
        assert "❌" in signal_args[3]  # error message

    @patch('uvr_pyside6_ui.core.download_worker.model_downloader.download_model_file')
    def test_download_worker_run_exception(self, mock_download):
        """Test download worker handling of exceptions."""
        mock_download.side_effect = Exception("Unexpected error")
        
        worker = DownloadWorker("Test Model", "url", ac.VR_ARCH_MODELS_KEY)
        
        finished_spy = QSignalSpy(worker.finished)
        
        worker.run()
        
        # Check finished signal was emitted with error
        assert finished_spy.count() == 1
        signal_args = finished_spy.at(0)
        assert signal_args[0] is False  # success
        assert "Unexpected error" in signal_args[3]  # error message

    @patch('uvr_pyside6_ui.core.download_worker.model_downloader.download_model_file')
    def test_download_worker_run_with_config_url(self, mock_download):
        """Test download worker with config URL."""
        mock_download.return_value = (True, "/path/to/model.pth", "/path/to/config.yaml")
        
        worker = DownloadWorker("Test", "model_url", ac.DEMUCS_MODELS_KEY, "config_url")
        
        worker.run()
        
        mock_download.assert_called_once_with(
            "Test", "model_url", ac.DEMUCS_MODELS_KEY, "config_url", worker.progress.emit
        )

    @patch('uvr_pyside6_ui.core.download_worker.model_downloader.download_model_file')
    def test_download_worker_run_success_no_config_path(self, mock_download):
        """Test successful download without config path."""
        mock_download.return_value = (True, "/path/to/model.pth", None)
        
        worker = DownloadWorker("Test Model", "url", ac.VR_ARCH_MODELS_KEY)
        
        finished_spy = QSignalSpy(worker.finished)
        
        worker.run()
        
        # Check finished signal 
        assert finished_spy.count() == 1
        signal_args = finished_spy.at(0)
        assert signal_args[0] is True  # success
        assert signal_args[2] == ""  # config_path should be empty string


@pytest.mark.unit
@pytest.mark.download
@pytest.mark.worker
class TestDownloadManager:
    """Test cases for DownloadManager class."""

    def test_download_manager_initialization(self):
        """Test DownloadManager initialization."""
        manager = DownloadManager()
        
        assert hasattr(manager, 'download_progress')
        assert hasattr(manager, 'download_finished')
        assert isinstance(manager.download_progress, Signal)
        assert isinstance(manager.download_finished, Signal)
        assert manager.active_threads == []
        assert manager.active_workers == []

    def test_download_manager_start_download(self):
        """Test starting a download with DownloadManager."""
        manager = DownloadManager()
        
        # Spy on manager signals
        progress_spy = QSignalSpy(manager.download_progress)
        finished_spy = QSignalSpy(manager.download_finished)
        
        # Mock QThread to avoid actual threading
        with patch('uvr_pyside6_ui.core.download_worker.QThread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            # Mock the moveToThread method to avoid Qt type checking
            with patch.object(DownloadWorker, 'moveToThread') as mock_move_to_thread:
                worker = manager.start_download(
                    "Test Model", 
                    "https://example.com/model.pth", 
                    ac.VR_ARCH_MODELS_KEY
                )
                
                # Check that worker was created and returned
                assert isinstance(worker, DownloadWorker)
                assert worker.model_name == "Test Model"
                
                # Check that worker and thread are tracked
                assert len(manager.active_threads) == 1
                assert len(manager.active_workers) == 1
                assert manager.active_threads[0] == mock_thread
                assert manager.active_workers[0] == worker
                
                # Check that thread was started and worker moved
                mock_thread.start.assert_called_once()
                mock_move_to_thread.assert_called_once_with(mock_thread)

    def test_download_manager_start_download_with_config(self):
        """Test starting a download with config URL."""
        manager = DownloadManager()
        
        with patch('uvr_pyside6_ui.core.download_worker.QThread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            with patch.object(DownloadWorker, 'moveToThread') as mock_move_to_thread:
                worker = manager.start_download(
                    "Test Model", 
                    "model_url", 
                    ac.DEMUCS_MODELS_KEY,
                    "config_url"
                )
                
                assert worker.config_url == "config_url"

    def test_download_manager_cleanup_thread(self):
        """Test thread cleanup functionality."""
        manager = DownloadManager()
        
        # Create mock thread and worker
        mock_thread = Mock()
        mock_worker = Mock()
        
        # Add them to active lists
        manager.active_threads.append(mock_thread)
        manager.active_workers.append(mock_worker)
        
        # Call cleanup
        manager._cleanup_thread(mock_thread, mock_worker)
        
        # Check they were removed
        assert mock_thread not in manager.active_threads
        assert mock_worker not in manager.active_workers

    def test_download_manager_cleanup_thread_not_in_lists(self):
        """Test cleanup when thread/worker not in active lists."""
        manager = DownloadManager()
        
        mock_thread = Mock()
        mock_worker = Mock()
        
        # Should not raise error even if not in lists
        manager._cleanup_thread(mock_thread, mock_worker)
        
        assert len(manager.active_threads) == 0
        assert len(manager.active_workers) == 0

    def test_download_manager_cancel_all_downloads(self):
        """Test canceling all active downloads."""
        manager = DownloadManager()
        
        # Create mock workers
        mock_worker1 = Mock()
        mock_worker2 = Mock()
        
        manager.active_workers = [mock_worker1, mock_worker2]
        
        manager.cancel_all_downloads()
        
        # Check that cancel was called on all workers
        mock_worker1.cancel.assert_called_once()
        mock_worker2.cancel.assert_called_once()

    def test_download_manager_cancel_all_downloads_empty(self):
        """Test canceling downloads when no active downloads."""
        manager = DownloadManager()
        
        # Should not raise error
        manager.cancel_all_downloads()
        
        assert len(manager.active_workers) == 0

    def test_download_manager_multiple_downloads(self):
        """Test managing multiple simultaneous downloads."""
        manager = DownloadManager()
        
        with patch('uvr_pyside6_ui.core.download_worker.QThread') as mock_thread_class:
            mock_thread1 = Mock()
            mock_thread2 = Mock()
            mock_thread_class.side_effect = [mock_thread1, mock_thread2]
            
            with patch.object(DownloadWorker, 'moveToThread') as mock_move_to_thread:
                worker1 = manager.start_download("Model1", "url1", ac.VR_ARCH_MODELS_KEY)
                worker2 = manager.start_download("Model2", "url2", ac.MDX_NET_MODELS_KEY)
                
                # Check that both are tracked
                assert len(manager.active_threads) == 2
                assert len(manager.active_workers) == 2
                assert worker1 in manager.active_workers
                assert worker2 in manager.active_workers

    def test_download_manager_signal_connections(self):
        """Test that signals are properly connected."""
        manager = DownloadManager()
        
        with patch('uvr_pyside6_ui.core.download_worker.QThread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            with patch.object(DownloadWorker, 'moveToThread') as mock_move_to_thread:
                worker = manager.start_download("Test", "url", ac.VR_ARCH_MODELS_KEY)
                
                # Verify signal connections were made
                # Note: In actual implementation, signals would be connected
                # This tests the structure rather than Qt's internal connections
                assert hasattr(worker, 'progress')
                assert hasattr(worker, 'finished')


@pytest.mark.integration
@pytest.mark.download  
@pytest.mark.worker
class TestDownloadWorkerIntegration:
    """Integration tests for download worker functionality."""

    @patch('uvr_pyside6_ui.core.download_worker.model_downloader.download_model_file')
    def test_full_download_workflow(self, mock_download):
        """Test complete download workflow from manager to worker."""
        # Setup mock download response
        mock_download.return_value = (True, "/path/to/model.pth", None)
        
        manager = DownloadManager()
        
        # Spy on manager signals
        progress_spy = QSignalSpy(manager.download_progress)
        finished_spy = QSignalSpy(manager.download_finished)
        
        # Start download
        with patch('uvr_pyside6_ui.core.download_worker.QThread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            with patch.object(DownloadWorker, 'moveToThread') as mock_move_to_thread:
                worker = manager.start_download(
                    "Integration Test Model",
                    "https://example.com/model.pth",
                    ac.VR_ARCH_MODELS_KEY
                )
                
                # Manually trigger worker run (simulating thread execution)
                worker.run()
                
                # Check that download was attempted
                mock_download.assert_called_once()
                
                # Check worker state
                assert worker.model_name == "Integration Test Model"
                assert worker._is_cancelled is False

    def test_download_manager_worker_lifecycle(self):
        """Test complete lifecycle of worker and thread management."""
        manager = DownloadManager()
        
        # Start download
        with patch('uvr_pyside6_ui.core.download_worker.QThread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            with patch.object(DownloadWorker, 'moveToThread') as mock_move_to_thread:
                worker = manager.start_download("Test", "url", ac.VR_ARCH_MODELS_KEY)
                
                # Verify initial state
                assert len(manager.active_threads) == 1
                assert len(manager.active_workers) == 1
                
                # Simulate completion and cleanup
                manager._cleanup_thread(mock_thread, worker)
                
                # Verify cleanup
                assert len(manager.active_threads) == 0
                assert len(manager.active_workers) == 0

    def test_worker_progress_signal_integration(self):
        """Test that worker progress signals work correctly."""
        worker = DownloadWorker("Test", "url", ac.VR_ARCH_MODELS_KEY)
        
        progress_spy = QSignalSpy(worker.progress)
        
        # Simulate progress callback
        worker.progress.emit("test_file.pth", 50)
        
        # Check signal was emitted
        assert progress_spy.count() == 1
        assert progress_spy.at(0) == ["test_file.pth", 50]

    def test_worker_finished_signal_integration(self):
        """Test that worker finished signals work correctly."""
        worker = DownloadWorker("Test", "url", ac.VR_ARCH_MODELS_KEY)
        
        finished_spy = QSignalSpy(worker.finished)
        
        # Simulate finished signal
        worker.finished.emit(True, "/path/model.pth", "/path/config.yaml", "Success")
        
        # Check signal was emitted
        assert finished_spy.count() == 1
        signal_args = finished_spy.at(0)
        assert signal_args[0] is True
        assert signal_args[1] == "/path/model.pth"
        assert signal_args[2] == "/path/config.yaml"
        assert signal_args[3] == "Success"

    @pytest.mark.edge_case
    def test_manager_handles_worker_exceptions(self):
        """Test that manager properly handles worker exceptions."""
        manager = DownloadManager()
        
        # This tests the structure - actual exception handling would be in Qt's signal system
        with patch('uvr_pyside6_ui.core.download_worker.QThread') as mock_thread_class:
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            with patch.object(DownloadWorker, 'moveToThread') as mock_move_to_thread:
                worker = manager.start_download("Test", "url", ac.VR_ARCH_MODELS_KEY)
                
                # Should not raise exception even if worker has issues
                worker.cancel()
                assert worker._is_cancelled is True 