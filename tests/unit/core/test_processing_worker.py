"""
Unit tests for RealProcessingWorker class.

Tests cover processing workflow, ensemble logic, audio processing,
error handling, and edge cases in audio separation.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.processing_worker import ProcessingThread, RealProcessingWorker


@pytest.mark.unit
@pytest.mark.worker
class TestRealProcessingWorker:
    """Test cases for RealProcessingWorker class."""

    def test_worker_initialization_valid_settings(self, valid_settings_dict):
        """Test worker initialization with valid settings."""
        with patch.object(ModelData, "from_settings_dict") as mock_model_data:
            mock_model_data.return_value = Mock(spec=ModelData)
            mock_model_data.return_value.model_status = True

            worker = RealProcessingWorker(valid_settings_dict)

            assert worker.settings == valid_settings_dict
            assert worker._is_running is True
            assert worker.model_data is not None
            assert worker.progress_value == 0

    def test_worker_initialization_invalid_settings(self):
        """Test worker initialization with invalid settings."""
        invalid_settings = {"invalid": "data"}

        with patch.object(ModelData, "from_settings_dict") as mock_model_data:
            mock_model_data.side_effect = Exception("Invalid settings")

            worker = RealProcessingWorker(invalid_settings)

            assert worker.model_data is None

    def test_run_missing_model_data(self, valid_settings_dict):
        """Test run method with missing model data."""
        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = None

        # Mock the signal emission
        worker.processing_finished = Mock()

        worker.run()

        worker.processing_finished.emit.assert_called_once()
        args = worker.processing_finished.emit.call_args[0]
        assert args[0] is False  # Success = False
        assert "Error: ModelData object is None" in args[1]

    def test_run_invalid_model_status(self, valid_settings_dict, mock_model_data):
        """Test run method with invalid model status."""
        mock_model_data.model_status = False
        mock_model_data.model_name = "test_model"

        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = mock_model_data
        worker.processing_finished = Mock()

        worker.run()

        worker.processing_finished.emit.assert_called_once()
        args = worker.processing_finished.emit.call_args[0]
        assert args[0] is False
        assert "Model data initialization failed" in args[1]

    def test_run_missing_audio_file(self, valid_settings_dict, mock_model_data):
        """Test run method with missing audio file."""
        mock_model_data.model_status = True
        mock_model_data.is_ensemble_mode = False
        mock_model_data.audio_file = "/nonexistent/file.wav"

        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = mock_model_data
        worker.processing_finished = Mock()

        # Mock all separator logic functions as callable
        with patch("uvr_pyside6_ui.core.processing_worker.SeperateVRLogic", Mock()):
            with patch(
                "uvr_pyside6_ui.core.processing_worker.SeperateMDXLogic", Mock()
            ):
                with patch(
                    "uvr_pyside6_ui.core.processing_worker.SeperateMDXCLogic", Mock()
                ):
                    with patch(
                        "uvr_pyside6_ui.core.processing_worker.SeperateDemucsLogic",
                        Mock(),
                    ):
                        with patch(
                            "uvr_pyside6_ui.core.processing_worker.clear_gpu_cache_logic",
                            Mock(),
                        ):
                            with patch(
                                "uvr_pyside6_ui.core.processing_worker.prepare_mix_logic",
                                Mock(),
                            ):
                                with patch(
                                    "uvr_pyside6_ui.core.processing_worker.write_audio_logic",
                                    Mock(),
                                ):
                                    with patch.object(
                                        Path, "exists", return_value=False
                                    ):
                                        worker.run()

        worker.processing_finished.emit.assert_called_once()
        args = worker.processing_finished.emit.call_args[0]
        assert args[0] is False
        assert "Input file missing or invalid" in args[1]

    def test_run_missing_export_path(
        self, valid_settings_dict, mock_model_data, mock_audio_file
    ):
        """Test run method with invalid export path."""
        mock_model_data.model_status = True
        mock_model_data.is_ensemble_mode = False
        mock_model_data.audio_file = str(mock_audio_file)
        mock_model_data.export_path = "/nonexistent/directory"

        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = mock_model_data
        worker.processing_finished = Mock()

        # Mock all separator logic functions as callable
        with patch("uvr_pyside6_ui.core.processing_worker.SeperateVRLogic", Mock()):
            with patch(
                "uvr_pyside6_ui.core.processing_worker.SeperateMDXLogic", Mock()
            ):
                with patch(
                    "uvr_pyside6_ui.core.processing_worker.SeperateMDXCLogic", Mock()
                ):
                    with patch(
                        "uvr_pyside6_ui.core.processing_worker.SeperateDemucsLogic",
                        Mock(),
                    ):
                        with patch(
                            "uvr_pyside6_ui.core.processing_worker.clear_gpu_cache_logic",
                            Mock(),
                        ):
                            with patch(
                                "uvr_pyside6_ui.core.processing_worker.prepare_mix_logic",
                                Mock(),
                            ):
                                with patch(
                                    "uvr_pyside6_ui.core.processing_worker.write_audio_logic",
                                    Mock(),
                                ):
                                    with patch.object(
                                        Path, "exists", return_value=True
                                    ):
                                        with patch.object(
                                            Path, "is_dir", return_value=False
                                        ):
                                            worker.run()

        worker.processing_finished.emit.assert_called_once()
        args = worker.processing_finished.emit.call_args[0]
        assert args[0] is False
        assert "Export directory invalid" in args[1]

    def test_run_ensemble_processing(
        self, ensemble_settings_dict, mock_model_data, mock_audio_file, temp_dir
    ):
        """Test ensemble processing workflow."""
        # Setup ensemble model data
        mock_model_data.model_status = True
        mock_model_data.is_ensemble_mode = True
        mock_model_data.is_ensemble_member = False
        mock_model_data.audio_file = str(mock_audio_file)
        mock_model_data.export_path = str(temp_dir)
        mock_model_data.ensemble_models = []  # Empty models to trigger warning
        mock_model_data.model_basename = "Test_Ensemble"
        mock_model_data.process_method = ac.ENSEMBLE_MODE

        worker = RealProcessingWorker(ensemble_settings_dict)
        worker.model_data = mock_model_data
        worker.processing_finished = Mock()
        worker.progress_updated = Mock()

        # Run the test - should handle empty ensemble models
        worker.run()

        # Should finish with error due to empty ensemble models
        worker.processing_finished.emit.assert_called_once()

    def test_process_ensemble_no_models(self, valid_settings_dict):
        """Test ensemble processing with no models."""
        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = Mock()
        worker.model_data.ensemble_models = []
        worker.processing_finished = Mock()

        worker._process_ensemble(np.random.rand(2, 1000).astype(np.float32))

        worker.processing_finished.emit.assert_called_once()
        args = worker.processing_finished.emit.call_args[0]
        assert args[0] is False
        assert "Ensemble not configured" in args[1]

    def test_combine_ensemble_outputs_average(self, valid_settings_dict):
        """Test ensemble output combination using average algorithm."""
        worker = RealProcessingWorker(valid_settings_dict)

        # Create test audio outputs
        output1 = np.random.rand(2, 1000).astype(np.float32)
        output2 = np.random.rand(2, 1000).astype(np.float32)
        outputs = [output1, output2]

        result = worker._combine_ensemble_outputs(outputs, ac.AVERAGE_ENSEMBLE)

        assert result is not None
        assert result.shape == (2, 1000)

        # Verify it's approximately the average
        expected_average = (output1 + output2) / 2
        np.testing.assert_allclose(result, expected_average, rtol=1e-5)

    def test_combine_ensemble_outputs_empty_list(self, valid_settings_dict):
        """Test ensemble combination with empty output list."""
        worker = RealProcessingWorker(valid_settings_dict)

        result = worker._combine_ensemble_outputs([], ac.AVERAGE_ENSEMBLE)

        assert result is None

    def test_combine_ensemble_outputs_single_output(self, valid_settings_dict):
        """Test ensemble combination with single output (edge case)."""
        worker = RealProcessingWorker(valid_settings_dict)

        output = np.random.rand(2, 1000).astype(np.float32)
        outputs = [output]

        result = worker._combine_ensemble_outputs(outputs, ac.AVERAGE_ENSEMBLE)

        assert result is None

    def test_average_ensemble_mismatched_shapes(self, valid_settings_dict):
        """Test average ensemble with mismatched audio shapes."""
        worker = RealProcessingWorker(valid_settings_dict)

        output1 = np.random.rand(2, 1000).astype(np.float32)
        output2 = np.random.rand(2, 2000).astype(np.float32)  # Different length
        outputs = [output1, output2]

        result = worker._average_ensemble(outputs)

        # Should align to minimum length
        assert result.shape == (2, 1000)

    @pytest.mark.edge_case
    def test_average_ensemble_mono_audio(self, valid_settings_dict):
        """Test average ensemble with mono audio arrays."""
        worker = RealProcessingWorker(valid_settings_dict)

        output1 = np.random.rand(1000).astype(np.float32)  # Mono
        output2 = np.random.rand(1000).astype(np.float32)  # Mono
        outputs = [output1, output2]

        result = worker._average_ensemble(outputs)

        assert result.shape == (1000,)

    def test_spectral_ensemble_max(self, valid_settings_dict):
        """Test spectral ensemble with max algorithm."""
        worker = RealProcessingWorker(valid_settings_dict)

        # Create test outputs
        output1 = np.random.rand(2, 1000).astype(np.float32) * 0.5
        output2 = np.random.rand(2, 1000).astype(np.float32) * 0.3
        outputs = [output1, output2]

        with patch(
            "uvr_pyside6_ui.core.processing_worker.spec_utils"
        ) as mock_spec_utils:
            # Mock spectrogram conversion
            mock_spec = np.random.rand(2, 513, 100).astype(np.complex64)
            mock_spec_utils.wave_to_spectrogram_old.return_value = mock_spec
            mock_spec_utils.spectrogram_to_wave_old.return_value = np.random.rand(
                2, 1000
            ).astype(np.float32)

            result = worker._spectral_ensemble(outputs, is_max=True)

            assert result is not None

            # Verify spectral processing was called
            assert mock_spec_utils.wave_to_spectrogram_old.call_count == 2
            assert mock_spec_utils.spectrogram_to_wave_old.call_count == 1

    def test_spectral_ensemble_no_spec_utils(self, valid_settings_dict):
        """Test spectral ensemble when spec_utils is not available."""
        worker = RealProcessingWorker(valid_settings_dict)

        output1 = np.random.rand(2, 1000).astype(np.float32)
        output2 = np.random.rand(2, 1000).astype(np.float32)
        outputs = [output1, output2]

        with patch("uvr_pyside6_ui.core.processing_worker.spec_utils", None):
            result = worker._spectral_ensemble(outputs, is_max=True)

            assert result is None

    def test_align_spectrograms_successful(self, valid_settings_dict):
        """Test successful spectrogram alignment."""
        worker = RealProcessingWorker(valid_settings_dict)

        # Create spectrograms with different time frames
        spec1 = np.random.rand(2, 513, 100).astype(np.complex64)
        spec2 = np.random.rand(2, 513, 120).astype(np.complex64)  # Longer
        spec3 = np.random.rand(2, 513, 80).astype(np.complex64)  # Shorter

        spectrograms = [spec1, spec2, spec3]

        aligned = worker._align_spectrograms(spectrograms)

        assert aligned is not None
        assert len(aligned) == 3
        # All should be aligned to max length (120)
        for spec in aligned:
            assert spec.shape == (2, 513, 120)

    @pytest.mark.edge_case
    def test_align_spectrograms_shape_mismatch(self, valid_settings_dict):
        """Test spectrogram alignment with incompatible shapes."""
        worker = RealProcessingWorker(valid_settings_dict)

        spec1 = np.random.rand(2, 513, 100).astype(np.complex64)
        spec2 = np.random.rand(1, 513, 100).astype(np.complex64)  # Different channels

        spectrograms = [spec1, spec2]

        with patch.object(worker, "_write_to_console"):
            aligned = worker._align_spectrograms(spectrograms)

            assert aligned is None

    def test_create_process_data_default(
        self, valid_settings_dict, mock_model_data, mock_audio_file, temp_dir
    ):
        """Test creation of process data dictionary."""
        mock_model_data.audio_file = str(mock_audio_file)
        mock_model_data.export_path = str(temp_dir)
        mock_model_data.is_4_stem_ensemble = False
        mock_model_data.model_basename = "test_model"

        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = mock_model_data

        process_data = worker._create_process_data()

        assert process_data["audio_file"] == str(mock_audio_file)
        assert process_data["export_path"] == str(temp_dir)
        assert process_data["audio_file_base"] == mock_audio_file.stem
        assert process_data["is_4_stem_ensemble"] is False
        assert callable(process_data["set_progress_bar"])
        assert callable(process_data["write_to_console"])

    def test_create_process_data_with_input_audio(
        self, valid_settings_dict, mock_model_data, temp_dir
    ):
        """Test process data creation with input audio array."""
        mock_model_data.export_path = str(temp_dir)
        mock_model_data.audio_file = str(temp_dir / "test.wav")  # Valid string path

        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = mock_model_data

        input_audio = np.random.rand(2, 1000).astype(np.float32)
        process_data = worker._create_process_data(input_audio)

        assert process_data["audio_file"] is None
        assert np.array_equal(process_data["input_audio_array"], input_audio)
        assert (
            process_data["audio_file_base"] == "test"
        )  # Uses filename from audio_file path

    def test_create_process_data_for_chained_model(
        self, valid_settings_dict, mock_model_data, temp_dir
    ):
        """Test process data creation for chained models."""
        mock_model_data.audio_file = str(temp_dir / "test.wav")
        mock_model_data.export_path = str(temp_dir)
        mock_model_data.model_basename = "primary_model"

        worker = RealProcessingWorker(valid_settings_dict)
        worker.model_data = mock_model_data

        chained_model = Mock(spec=ModelData)
        chained_model.model_basename = "secondary_model"

        input_audio = np.random.rand(2, 1000).astype(np.float32)

        process_data = worker._create_process_data_for_chained_model(
            chained_model, input_audio
        )

        assert process_data["input_audio_array"] is input_audio
        assert process_data["audio_file"] is None
        assert "primary_model_then_secondary_model" in process_data["audio_file_base"]

    def test_set_progress_bar_callback(self, valid_settings_dict):
        """Test progress bar callback functionality."""
        worker = RealProcessingWorker(valid_settings_dict)
        worker.progress_updated = Mock()

        worker._set_progress_bar_callback(0.5, "Test message")

        worker.progress_updated.emit.assert_called_once_with(50, "Test message")
        assert worker.progress_value == 50

    @pytest.mark.edge_case
    def test_set_progress_bar_callback_out_of_bounds(self, valid_settings_dict):
        """Test progress bar callback with out-of-bounds values."""
        worker = RealProcessingWorker(valid_settings_dict)
        worker.progress_updated = Mock()

        # Test values outside 0-1 range
        worker._set_progress_bar_callback(1.5, "Over 100%")
        worker.progress_updated.emit.assert_called_with(100, "Over 100%")

        worker._set_progress_bar_callback(-0.1, "Negative")
        worker.progress_updated.emit.assert_called_with(0, "Negative")

    def test_write_to_console(self, valid_settings_dict):
        """Test console writing functionality."""
        worker = RealProcessingWorker(valid_settings_dict)
        worker.progress_updated = Mock()
        worker.progress_value = 50

        worker._write_to_console("Test message", "Prefix: ")

        worker.progress_updated.emit.assert_called_once_with(50, "Prefix: Test message")

    def test_write_to_console_no_base_text(self, valid_settings_dict):
        """Test console writing without base text."""
        worker = RealProcessingWorker(valid_settings_dict)
        worker.progress_updated = Mock()
        worker.progress_value = 30

        worker._write_to_console("Test message")

        worker.progress_updated.emit.assert_called_once_with(30, "Test message")

    def test_stop_processing(self, valid_settings_dict):
        """Test stopping the processing worker."""
        worker = RealProcessingWorker(valid_settings_dict)

        assert worker._is_running is True

        worker.stop()

        assert worker._is_running is False

    def test_get_separator_for_model_invalid(self, valid_settings_dict):
        """Test separator creation with invalid model."""
        worker = RealProcessingWorker(valid_settings_dict)
        worker._write_to_console = Mock()

        model_data = Mock(spec=ModelData)
        model_data.model_status = False
        model_data.model_name = "invalid_model"

        process_data = {"test": "data"}

        separator = worker._get_separator_for_model(model_data, process_data)

        assert separator is None
        worker._write_to_console.assert_called_once()


@pytest.mark.unit
@pytest.mark.worker
class TestProcessingThread:
    """Test cases for ProcessingThread class."""

    def test_thread_initialization(self, valid_settings_dict):
        """Test processing thread initialization."""
        thread = ProcessingThread(valid_settings_dict)

        assert thread.settings_dict == valid_settings_dict
        assert thread.worker is None

    def test_thread_run_successful(self, valid_settings_dict):
        """Test successful thread execution."""
        thread = ProcessingThread(valid_settings_dict)
        thread.progress_updated = Mock()
        thread.processing_finished = Mock()

        # Mock worker creation and execution
        mock_worker = Mock(spec=RealProcessingWorker)
        mock_worker.progress_updated = Mock()
        mock_worker.processing_finished = Mock()

        with patch(
            "uvr_pyside6_ui.core.processing_worker.RealProcessingWorker",
            return_value=mock_worker,
        ):
            thread.run()

            assert thread.worker is mock_worker
            mock_worker.run.assert_called_once()

    def test_thread_run_with_exception(self, valid_settings_dict):
        """Test thread execution with exception."""
        thread = ProcessingThread(valid_settings_dict)
        thread.processing_finished = Mock()

        with patch(
            "uvr_pyside6_ui.core.processing_worker.RealProcessingWorker"
        ) as mock_worker_class:
            mock_worker_class.side_effect = Exception("Test error")

            thread.run()

            thread.processing_finished.emit.assert_called_once()
            args = thread.processing_finished.emit.call_args[0]
            assert args[0] is False
            assert "Thread error" in args[1]

    def test_thread_stop_processing(self, valid_settings_dict):
        """Test stopping thread processing."""
        thread = ProcessingThread(valid_settings_dict)

        # Set up a mock worker
        mock_worker = Mock(spec=RealProcessingWorker)
        thread.worker = mock_worker

        thread.stop_processing()

        mock_worker.stop.assert_called_once()

    def test_thread_stop_processing_no_worker(self, valid_settings_dict):
        """Test stopping thread when no worker exists."""
        thread = ProcessingThread(valid_settings_dict)

        # Should not raise an exception
        thread.stop_processing()

        assert thread.worker is None
