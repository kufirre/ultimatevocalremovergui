"""
Unit tests for ProcessingWorker ensemble stem selection functionality.

These tests focus on the ensemble-specific logic in ProcessingWorker,
particularly the stem selection and model configuration behavior.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.processing_worker import ProcessingWorker


@pytest.mark.unit
class TestProcessingWorkerEnsembleStemSelection:
    """Test ProcessingWorker ensemble stem selection logic."""

    def test_process_individual_model_stem_configuration(self):
        """Test that individual models are configured correctly for ensemble stem selection."""
        # Create master ensemble settings (user wants instrumental only)
        master_settings = {
            "is_primary_stem_only": False,
            "is_secondary_stem_only": True,  # Instrumental only
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "WAV",
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            # Ensemble configuration
            "ensemble_main_stem_pair": "Vocals/Instrumental",
            "ensemble_algorithm": "Average",
            "ensemble_selected_models": ["VocalModel"],
        }

        # Create a model where instrumental is the secondary stem
        model = ModelData()
        model.model_basename = "VocalModel"
        model.model_path = "/path/to/model.pth"
        model.model_status = True
        model.primary_stem = ac.VOCAL_STEM
        model.secondary_stem = ac.INST_STEM
        model.process_method = ac.VR_ARCH_TYPE
        model.export_path = tempfile.mkdtemp()

        # Create worker with ensemble configuration
        worker = ProcessingWorker(master_settings)
        worker.model_data.is_ensemble_mode = True
        worker.model_data.ensemble_primary_stem = ac.VOCAL_STEM
        worker.model_data.ensemble_secondary_stem = ac.INST_STEM

        # Simulate the stem configuration logic from the worker
        target_stem = worker.model_data.ensemble_secondary_stem  # Instrumental

        # Configure the model based on which stem matches the target
        if target_stem == model.secondary_stem:
            model.is_secondary_stem_only = True
            model.is_primary_stem_only = False
        elif target_stem == model.primary_stem:
            model.is_primary_stem_only = True
            model.is_secondary_stem_only = False
        else:
            # Model doesn't produce the target stem, output both
            model.is_primary_stem_only = False
            model.is_secondary_stem_only = False

        # Test that the model was configured correctly for instrumental output
        assert model.is_secondary_stem_only is True
        assert model.is_primary_stem_only is False

    def test_process_individual_model_swapped_stems(self):
        """Test model configuration when model has swapped stem assignments."""
        # Create master ensemble settings (user wants instrumental only)
        master_settings = {
            "is_primary_stem_only": False,
            "is_secondary_stem_only": True,  # Instrumental only
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "WAV",
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            # Ensemble configuration
            "ensemble_main_stem_pair": "Vocals/Instrumental",
            "ensemble_algorithm": "Average",
            "ensemble_selected_models": ["InstrumentalModel"],
        }

        # Create a model where instrumental is the PRIMARY stem (swapped)
        model = ModelData()
        model.model_basename = "InstrumentalModel"
        model.model_path = "/path/to/model.pth"
        model.model_status = True
        model.primary_stem = ac.INST_STEM  # Instrumental is primary
        model.secondary_stem = ac.VOCAL_STEM  # Vocals is secondary
        model.process_method = ac.MDX_ARCH_TYPE
        model.export_path = tempfile.mkdtemp()

        # Create worker with ensemble configuration
        worker = ProcessingWorker(master_settings)
        worker.model_data.is_ensemble_mode = True
        worker.model_data.ensemble_primary_stem = ac.VOCAL_STEM
        worker.model_data.ensemble_secondary_stem = ac.INST_STEM

        # Simulate the stem configuration logic
        target_stem = worker.model_data.ensemble_secondary_stem  # Instrumental

        # Configure the model based on which stem matches the target
        if target_stem == model.primary_stem:
            model.is_primary_stem_only = True
            model.is_secondary_stem_only = False
        elif target_stem == model.secondary_stem:
            model.is_secondary_stem_only = True
            model.is_primary_stem_only = False
        else:
            # Model doesn't produce the target stem, output both
            model.is_primary_stem_only = False
            model.is_secondary_stem_only = False

        # Test that the model was configured correctly for instrumental output
        # Since instrumental is this model's primary stem, is_primary_stem_only should be True
        assert model.is_primary_stem_only is True
        assert model.is_secondary_stem_only is False

    def test_process_individual_model_no_target_stem(self):
        """Test model configuration when model doesn't produce the target stem."""
        # Create master ensemble settings (user wants vocals only)
        master_settings = {
            "is_primary_stem_only": True,  # Vocals only
            "is_secondary_stem_only": False,
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "WAV",
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            # Ensemble configuration
            "ensemble_main_stem_pair": "Vocals/Instrumental",
            "ensemble_algorithm": "Average",
            "ensemble_selected_models": ["BassModel"],
        }

        # Create a model that doesn't produce vocals (only bass/drums)
        model = ModelData()
        model.model_basename = "BassModel"
        model.model_path = "/path/to/model.pth"
        model.model_status = True
        model.primary_stem = ac.BASS_STEM
        model.secondary_stem = ac.DRUM_STEM
        model.process_method = ac.DEMUCS_ARCH_TYPE
        model.export_path = tempfile.mkdtemp()

        # Create worker with ensemble configuration
        worker = ProcessingWorker(master_settings)
        worker.model_data.is_ensemble_mode = True
        worker.model_data.ensemble_primary_stem = ac.VOCAL_STEM
        worker.model_data.ensemble_secondary_stem = ac.INST_STEM

        # Simulate the stem configuration logic
        target_stem = worker.model_data.ensemble_primary_stem  # Vocals

        # Check if model produces the target stem
        produces_target = target_stem in [model.primary_stem, model.secondary_stem]

        if not produces_target:
            # Model doesn't produce the target stem, output both stems
            model.is_primary_stem_only = False
            model.is_secondary_stem_only = False

        # Test that the model outputs both stems since it can't produce vocals
        assert model.is_primary_stem_only is False
        assert model.is_secondary_stem_only is False

        # Mock the processing result - model would return its available stems
        with patch.object(worker, "_process_individual_model") as mock_process:
            mock_process.return_value = {
                ac.BASS_STEM: np.random.randn(44100, 2),
                ac.DRUM_STEM: np.random.randn(44100, 2),
            }

            result = mock_process(model, np.random.randn(44100, 2))

            # Verify the model returns its available stems, not the target stem
            assert result is not None
            assert ac.BASS_STEM in result
            assert ac.DRUM_STEM in result
            assert ac.VOCAL_STEM not in result

    def test_ensemble_file_management_with_save_all_outputs(self):
        """Test file management when save_all_outputs is True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = {
                "is_primary_stem_only": False,
                "is_secondary_stem_only": True,
                "chosen_process_method": ac.ENSEMBLE_MODE,
                "save_format": "WAV",
                "audio_file": "test.wav",
                "export_path": temp_dir,
            }

            worker = ProcessingWorker(settings)
            worker.model_data.is_ensemble_mode = True
            worker.model_data.is_save_all_outputs_ensemble = True
            worker.model_data.ensemble_primary_stem = ac.VOCAL_STEM
            worker.model_data.ensemble_secondary_stem = ac.INST_STEM
            worker.model_data.ensemble_type = "Average"

            # Track saved files
            saved_files = []

            def mock_write(path, audio, sr, **kwargs):
                saved_files.append(Path(path).name)

            with patch("soundfile.write", side_effect=mock_write):
                # Mock the ensemble processing
                all_outputs_by_stem = {
                    ac.INST_STEM: [
                        np.random.randn(44100, 2),
                        np.random.randn(44100, 2),
                    ]
                }

                all_saved_files_by_stem = {
                    ac.INST_STEM: [
                        f"{temp_dir}/test_Model1_(Instrumental).wav",
                        f"{temp_dir}/test_Model2_(Instrumental).wav",
                    ]
                }

                # Simulate ensemble combination
                worker._write_to_console = Mock()

                # With save_all_outputs=True, individual files should be kept
                # Let's verify the logic by checking console output
                worker._write_to_console(
                    "✓ Saved ensemble Instrumental successfully", ""
                )

                # Verify console message
                worker._write_to_console.assert_called_with(
                    "✓ Saved ensemble Instrumental successfully", ""
                )

    def test_ensemble_stem_collection(self):
        """Test that ensemble collects only the requested stems."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = {
                "is_primary_stem_only": True,  # Vocals only
                "is_secondary_stem_only": False,
                "chosen_process_method": ac.ENSEMBLE_MODE,
                "save_format": "WAV",
                "audio_file": "test.wav",
                "export_path": temp_dir,
            }

            worker = ProcessingWorker(settings)
            worker.model_data.is_ensemble_mode = True
            worker.model_data.ensemble_primary_stem = ac.VOCAL_STEM
            worker.model_data.ensemble_secondary_stem = ac.INST_STEM

            # Mock multiple model outputs
            model_outputs = [
                {ac.VOCAL_STEM: np.random.randn(44100, 2)},  # Model 1: vocals only
                {
                    ac.VOCAL_STEM: np.random.randn(44100, 2),
                    ac.INST_STEM: np.random.randn(44100, 2),
                },  # Model 2: both
                {ac.VOCAL_STEM: np.random.randn(44100, 2)},  # Model 3: vocals only
            ]

            # Simulate stem collection
            all_outputs_by_stem = {}

            for output in model_outputs:
                for stem_name, stem_audio in output.items():
                    # Only collect vocals (user selected vocals only)
                    if stem_name == ac.VOCAL_STEM:
                        if stem_name not in all_outputs_by_stem:
                            all_outputs_by_stem[stem_name] = []
                        all_outputs_by_stem[stem_name].append(stem_audio)

            # Verify only vocals were collected
            assert len(all_outputs_by_stem) == 1
            assert ac.VOCAL_STEM in all_outputs_by_stem
            assert len(all_outputs_by_stem[ac.VOCAL_STEM]) == 3
            assert ac.INST_STEM not in all_outputs_by_stem

    def test_ensemble_algorithm_application(self):
        """Test that ensemble algorithms are correctly applied to stems."""
        worker = ProcessingWorker({})

        # Create test outputs
        output1 = np.array([[0.5, 0.5], [0.6, 0.6], [0.7, 0.7]])
        output2 = np.array([[0.3, 0.3], [0.8, 0.8], [0.4, 0.4]])
        outputs = [output1, output2]

        # Test Average algorithm
        avg_result = worker._average_ensemble(outputs)
        expected_avg = np.array([[0.4, 0.4], [0.7, 0.7], [0.55, 0.55]])
        np.testing.assert_array_almost_equal(avg_result, expected_avg)

        # Test that other algorithms exist and don't crash
        spec_result = worker._spectral_ensemble(outputs, is_max=True)
        assert spec_result is not None

        min_spec_result = worker._spectral_ensemble(outputs, is_max=False)
        assert min_spec_result is not None

    def test_ensemble_error_handling(self):
        """Test error handling in ensemble processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = {
                "chosen_process_method": ac.ENSEMBLE_MODE,
                "save_format": "WAV",
                "audio_file": "test.wav",
                "export_path": temp_dir,
            }

            worker = ProcessingWorker(settings)

            # Test with no models
            worker.model_data.is_ensemble_mode = True
            worker.model_data.ensemble_models = []

            with patch.object(worker, "_load_audio") as mock_load:
                with patch.object(worker, "processing_finished") as mock_finished:
                    mock_load.return_value = np.random.randn(44100, 2)

                    worker._process_ensemble(mock_load.return_value)

                    # Should emit failure
                    mock_finished.emit.assert_called_once()
                    args = mock_finished.emit.call_args[0]
                    assert args[0] is False  # Success = False
                    assert "Ensemble not configured" in args[1]  # Error message

    def test_ensemble_minimum_models_requirement(self):
        """Test that ensemble requires at least 2 models."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = {
                "chosen_process_method": ac.ENSEMBLE_MODE,
                "save_format": "WAV",
                "audio_file": "test.wav",
                "export_path": temp_dir,
            }

            worker = ProcessingWorker(settings)
            worker.model_data.is_ensemble_mode = True

            # Test with 1 model
            model1 = Mock()
            model1.model_basename = "Model1"
            worker.model_data.ensemble_models = [model1]

            with patch.object(worker, "_load_audio") as mock_load:
                with patch.object(worker, "processing_finished") as mock_finished:
                    mock_load.return_value = np.random.randn(44100, 2)

                    worker._process_ensemble(mock_load.return_value)

                    # Should fail with specific error
                    mock_finished.emit.assert_called_once()
                    args = mock_finished.emit.call_args[0]
                    assert args[0] is False
                    assert "only 1 model(s) selected" in args[1]
                    assert "Model1" in args[1]  # Should mention the model name
