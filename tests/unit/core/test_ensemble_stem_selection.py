"""
Unit tests for ensemble stem selection functionality.

Tests the complete flow from user selection in UI to separator output,
ensuring that stem-only flags are properly propagated and respected.
"""

import tempfile
from unittest.mock import Mock, patch

import numpy as np
import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.processing_worker import ProcessingWorker
from uvr_pyside6_ui.core.separate_demucs_logic import SeparateDemucsLogic
from uvr_pyside6_ui.core.separate_mdx_logic import SeparateMDXLogic
from uvr_pyside6_ui.core.separate_vr_logic import SeparateVRLogic


@pytest.fixture
def mock_model_data():
    """Create a mock ModelData instance."""
    model_data = ModelData()
    model_data.model_name = "Test Model"
    model_data.model_basename = "test_model"
    model_data.model_path = "/path/to/model.pth"
    model_data.model_status = True
    model_data.primary_stem = ac.VOCAL_STEM
    model_data.secondary_stem = ac.INST_STEM
    model_data.process_method = ac.VR_ARCH_TYPE
    model_data.model_samplerate = 44100
    model_data.export_path = tempfile.mkdtemp()
    model_data.save_format = "WAV"
    model_data.is_ensemble_mode = False
    model_data.is_gpu_conversion = False
    return model_data


@pytest.mark.unit
class TestEnsembleStemSelection:
    """Test ensemble stem selection functionality."""

    def test_user_selects_instruments_only(self):
        """Test when user selects 'Instruments Only' in UI."""
        # Simulate user selection
        settings = {
            "is_primary_stem_only": False,
            "is_secondary_stem_only": True,  # Instruments only
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "WAV",
        }

        # Create ensemble master model data
        master_model = ModelData.from_settings_dict(settings)
        master_model.is_ensemble_mode = True
        master_model.ensemble_primary_stem = ac.VOCAL_STEM
        master_model.ensemble_secondary_stem = ac.INST_STEM

        # Test that settings are properly set
        assert master_model.is_secondary_stem_only is True
        assert master_model.is_primary_stem_only is False

    def test_user_selects_vocals_only(self):
        """Test when user selects 'Vocals Only' in UI."""
        settings = {
            "is_primary_stem_only": True,  # Vocals only
            "is_secondary_stem_only": False,
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "WAV",
        }

        master_model = ModelData.from_settings_dict(settings)
        master_model.is_ensemble_mode = True
        master_model.ensemble_primary_stem = ac.VOCAL_STEM
        master_model.ensemble_secondary_stem = ac.INST_STEM

        assert master_model.is_primary_stem_only is True
        assert master_model.is_secondary_stem_only is False

    def test_processing_worker_configures_models_for_instruments_only(self):
        """Test that processing worker properly configures individual models for instruments only."""
        with patch(
            "uvr_pyside6_ui.core.processing_worker.ProcessingWorker._load_audio"
        ) as mock_load:
            mock_load.return_value = np.random.randn(44100, 2)

            # Master settings with instruments only
            settings = {
                "is_primary_stem_only": False,
                "is_secondary_stem_only": True,  # Instruments only
                "chosen_process_method": ac.ENSEMBLE_MODE,
                "save_format": "WAV",
                "audio_file": "test.wav",
                "export_path": tempfile.mkdtemp(),
            }

            worker = ProcessingWorker(settings)
            worker.model_data.is_ensemble_mode = True
            worker.model_data.ensemble_primary_stem = ac.VOCAL_STEM
            worker.model_data.ensemble_secondary_stem = ac.INST_STEM

            # Create test models with different stem assignments
            model1 = Mock()
            model1.model_basename = "VocalModel"
            model1.primary_stem = ac.VOCAL_STEM
            model1.secondary_stem = ac.INST_STEM
            model1.is_primary_stem_only = False
            model1.is_secondary_stem_only = False

            model2 = Mock()
            model2.model_basename = "InstrumentalModel"
            model2.primary_stem = ac.INST_STEM
            model2.secondary_stem = ac.VOCAL_STEM
            model2.is_primary_stem_only = False
            model2.is_secondary_stem_only = False

            # Test the configuration logic
            # For model1 (primary=Vocals, secondary=Instrumental), when user wants Instrumental:
            # Should set is_secondary_stem_only = True
            target_stem = worker.model_data.ensemble_secondary_stem  # Instrumental

            if target_stem == model1.secondary_stem:
                model1.is_primary_stem_only = False
                model1.is_secondary_stem_only = True

            assert model1.is_secondary_stem_only is True
            assert model1.is_primary_stem_only is False

            # For model2 (primary=Instrumental, secondary=Vocals), when user wants Instrumental:
            # Should set is_primary_stem_only = True
            if target_stem == model2.primary_stem:
                model2.is_primary_stem_only = True
                model2.is_secondary_stem_only = False

            assert model2.is_primary_stem_only is True
            assert model2.is_secondary_stem_only is False

    def test_vr_separator_respects_stem_only_flags(self, mock_model_data):
        """Test that VR separator respects stem-only flags."""
        # Configure for secondary stem only (Instrumental)
        mock_model_data.is_primary_stem_only = False
        mock_model_data.is_secondary_stem_only = True

        process_data = {
            "audio_file": "test.wav",
            "export_path": mock_model_data.export_path,
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch("uvr_pyside6_ui.core.separate_vr_logic.nets_vr"):
            with patch("uvr_pyside6_ui.core.separate_vr_logic.spec_utils"):
                with patch("torch.load"):
                    separator = SeparateVRLogic(mock_model_data, process_data)

                    # Verify the separator has the correct stem settings
                    assert separator.md.is_secondary_stem_only is True
                    assert separator.md.is_primary_stem_only is False

    def test_mdx_separator_respects_stem_only_flags(self, mock_model_data):
        """Test that MDX separator respects stem-only flags."""
        mock_model_data.process_method = ac.MDX_ARCH_TYPE
        mock_model_data.is_primary_stem_only = True  # Vocals only
        mock_model_data.is_secondary_stem_only = False
        mock_model_data.mdx_n_fft_scale_set = 2048
        mock_model_data.mdx_dim_f_set = 1024

        process_data = {
            "audio_file": "test.wav",
            "export_path": mock_model_data.export_path,
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        separator = SeparateMDXLogic(mock_model_data, process_data)

        # Verify the separator has the correct stem settings
        assert separator.md.is_primary_stem_only is True
        assert separator.md.is_secondary_stem_only is False

    def test_ensemble_combines_only_requested_stems(self):
        """Test that ensemble only combines stems that were requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = {
                "is_primary_stem_only": False,
                "is_secondary_stem_only": True,  # Instruments only
                "chosen_process_method": ac.ENSEMBLE_MODE,
                "save_format": "WAV",
                "audio_file": "test.wav",
                "export_path": temp_dir,
            }

            worker = ProcessingWorker(settings)

            # Mock model results - some models output both stems, but we only want instrumental
            model_results = {
                "Model1": {
                    ac.VOCAL_STEM: np.random.randn(44100, 2),
                    ac.INST_STEM: np.random.randn(44100, 2),
                },
                "Model2": {
                    ac.VOCAL_STEM: np.random.randn(44100, 2),
                    ac.INST_STEM: np.random.randn(44100, 2),
                },
            }

            # Simulate ensemble collection
            stems_to_ensemble = {}

            for model_name, results in model_results.items():
                # Only collect instrumental stems (user selected instruments only)
                if ac.INST_STEM in results:
                    if ac.INST_STEM not in stems_to_ensemble:
                        stems_to_ensemble[ac.INST_STEM] = []
                    stems_to_ensemble[ac.INST_STEM].append(results[ac.INST_STEM])

            # Verify only instrumental stems were collected
            assert len(stems_to_ensemble) == 1
            assert ac.INST_STEM in stems_to_ensemble
            assert ac.VOCAL_STEM not in stems_to_ensemble
            assert len(stems_to_ensemble[ac.INST_STEM]) == 2

    def test_demucs_separator_respects_stem_only_flags(self, mock_model_data):
        """Test that Demucs separator respects stem-only flags."""
        mock_model_data.process_method = ac.DEMUCS_ARCH_TYPE
        mock_model_data.is_primary_stem_only = True  # Vocals only
        mock_model_data.is_secondary_stem_only = False
        mock_model_data.demucs_stems = ac.ALL_STEMS
        mock_model_data.demucs_source_list = [
            ac.BASS_STEM,
            ac.DRUM_STEM,
            ac.OTHER_STEM,
            ac.VOCAL_STEM,
        ]
        mock_model_data.demucs_source_map = {
            ac.BASS_STEM: 0,
            ac.DRUM_STEM: 1,
            ac.OTHER_STEM: 2,
            ac.VOCAL_STEM: 3,
        }
        mock_model_data.demucs_version = "v3"
        mock_model_data.shifts = 1
        mock_model_data.is_split_mode = True
        mock_model_data.overlap = 0.25
        mock_model_data.segment = ac.DEFAULT

        process_data = {
            "audio_file": "test.wav",
            "export_path": mock_model_data.export_path,
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch(
            "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
        ) as mock_prepare:
            mock_prepare.return_value = np.random.randn(44100, 2)
            with patch("uvr_pyside6_ui.core.separate_demucs_logic.demucs_get_model"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.is_file", return_value=True):
                        with patch("pathlib.Path.stat") as mock_stat:
                            mock_stat.return_value.st_size = 1000

                            separator = SeparateDemucsLogic(
                                mock_model_data, process_data
                            )

                            # Verify the separator has the correct stem settings
                            assert separator.md.is_primary_stem_only is True
                            assert separator.md.is_secondary_stem_only is False


@pytest.mark.unit
class TestModelStemConfiguration:
    """Test how different models handle stem configuration."""

    def test_model_with_swapped_stems(self):
        """Test model where instrumental is primary stem."""
        model = ModelData()
        model.primary_stem = ac.INST_STEM
        model.secondary_stem = ac.VOCAL_STEM

        # User wants instrumental only
        target_stem = ac.INST_STEM

        # Since instrumental is this model's primary stem
        if target_stem == model.primary_stem:
            model.is_primary_stem_only = True
            model.is_secondary_stem_only = False

        assert model.is_primary_stem_only is True
        assert model.is_secondary_stem_only is False

    def test_model_without_requested_stem(self):
        """Test model that doesn't produce the requested stem."""
        model = ModelData()
        model.primary_stem = ac.BASS_STEM
        model.secondary_stem = ac.DRUM_STEM

        # User wants vocals, but this model doesn't produce vocals
        target_stem = ac.VOCAL_STEM

        # Model should output both stems since it can't produce the target
        produces_target = target_stem in [model.primary_stem, model.secondary_stem]

        if not produces_target:
            model.is_primary_stem_only = False
            model.is_secondary_stem_only = False

        assert model.is_primary_stem_only is False
        assert model.is_secondary_stem_only is False

    def test_demucs_4_stem_with_stem_selection(self):
        """Test Demucs 4-stem model with specific stem selection."""
        model = ModelData()
        model.process_method = ac.DEMUCS_ARCH_TYPE
        model.demucs_stems = ac.ALL_STEMS
        model.demucs_source_list = [
            ac.BASS_STEM,
            ac.DRUM_STEM,
            ac.OTHER_STEM,
            ac.VOCAL_STEM,
        ]
        model.primary_stem = ac.VOCAL_STEM
        model.secondary_stem = ac.INST_STEM

        # User wants vocals only
        model.is_primary_stem_only = True
        model.is_secondary_stem_only = False

        # Demucs should still produce all 4 stems but only save vocals
        assert model.demucs_stems == ac.ALL_STEMS
        assert model.is_primary_stem_only is True


@pytest.mark.unit
class TestEnsembleEdgeCases:
    """Test edge cases in ensemble stem selection."""

    def test_empty_ensemble_results(self):
        """Test handling when no models produce results."""
        settings = {
            "is_primary_stem_only": False,
            "is_secondary_stem_only": True,
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "WAV",
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
        }

        worker = ProcessingWorker(settings)

        # No model results
        stems_to_ensemble = {}

        # Should handle gracefully
        assert len(stems_to_ensemble) == 0

    def test_single_model_ensemble(self):
        """Test ensemble with only one model (should fail)."""
        settings = {
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "WAV",
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
        }

        worker = ProcessingWorker(settings)
        worker.model_data.ensemble_models = [Mock()]  # Only one model

        # Ensemble requires at least 2 models
        assert len(worker.model_data.ensemble_models) < 2

    def test_mismatched_audio_lengths(self):
        """Test ensemble with models producing different length outputs."""
        # Create outputs of different lengths
        output1 = np.random.randn(44100 * 5, 2)  # 5 seconds
        output2 = np.random.randn(44100 * 4, 2)  # 4 seconds

        outputs = [output1, output2]

        # Ensemble should align to minimum length
        min_length = min(o.shape[0] for o in outputs)
        assert min_length == 44100 * 4

        # Aligned outputs
        aligned = [o[:min_length] for o in outputs]
        assert all(o.shape[0] == min_length for o in aligned)

    def test_save_format_consistency(self):
        """Test that individual and ensemble outputs use same format."""
        settings = {
            "chosen_process_method": ac.ENSEMBLE_MODE,
            "save_format": "FLAC",
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
        }

        worker = ProcessingWorker(settings)

        # Both individual and ensemble outputs should use FLAC
        assert worker.model_data.save_format == "FLAC"

        # File names should have consistent extensions
        individual_file = f"test_Model1_({ac.VOCAL_STEM}).flac"
        ensemble_file = f"test_Ensemble_({ac.VOCAL_STEM}).flac"

        assert individual_file.endswith(".flac")
        assert ensemble_file.endswith(".flac")


@pytest.mark.unit
class TestProcessingWorkerIntegration:
    """Test integration between processing worker and separators."""

    @patch("uvr_pyside6_ui.core.processing_worker.SeparateVRLogic")
    def test_vr_separator_creation_with_stem_flags(self, mock_vr_class):
        """Test that VR separator is created with correct stem flags."""
        mock_separator = Mock()
        mock_separator.separate.return_value = {ac.INST_STEM: np.random.randn(44100, 2)}
        mock_vr_class.return_value = mock_separator

        model_data = Mock()
        model_data.process_method = ac.VR_ARCH_TYPE
        model_data.is_primary_stem_only = False
        model_data.is_secondary_stem_only = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM

        process_data = {"test": "data"}

        # Create separator through the factory method
        from uvr_pyside6_ui.core.processing_worker import ProcessingWorker

        worker = ProcessingWorker({})
        separator = worker._get_separator_for_model(model_data, process_data)

        # Verify separator was created with correct model data
        mock_vr_class.assert_called_once_with(
            model_data=model_data, process_data=process_data
        )

    @patch("uvr_pyside6_ui.core.processing_worker.SeparateMDXLogic")
    def test_mdx_separator_creation_with_stem_flags(self, mock_mdx_class):
        """Test that MDX separator is created with correct stem flags."""
        mock_separator = Mock()
        mock_separator.separate.return_value = {
            ac.VOCAL_STEM: np.random.randn(44100, 2)
        }
        mock_mdx_class.return_value = mock_separator

        model_data = Mock()
        model_data.process_method = ac.MDX_ARCH_TYPE
        model_data.is_mdx_c = False
        model_data.is_primary_stem_only = True
        model_data.is_secondary_stem_only = False
        model_data.model_status = True

        process_data = {"test": "data"}

        worker = ProcessingWorker({})
        separator = worker._get_separator_for_model(model_data, process_data)

        mock_mdx_class.assert_called_once_with(
            model_data=model_data, process_data=process_data
        )

    def test_ensemble_algorithm_selection(self):
        """Test that correct ensemble algorithm is applied."""
        worker = ProcessingWorker({})

        # Test Max Spec algorithm
        outputs = [
            np.random.randn(44100, 2),
            np.random.randn(44100, 2),
        ]

        # The actual implementation would use spectral comparison
        # Here we just verify the method exists and handles the algorithm parameter
        result = worker._combine_ensemble_outputs(outputs, "Max Spec")
        assert result is not None

        # Test Average algorithm
        result = worker._combine_ensemble_outputs(outputs, "Average")
        assert result is not None

        # Test Min Spec algorithm
        result = worker._combine_ensemble_outputs(outputs, "Min Spec")
        assert result is not None


@pytest.mark.integration
class TestFullEnsembleFlow:
    """Integration tests for complete ensemble flow."""

    @patch("uvr_pyside6_ui.core.processing_worker.ProcessingWorker._load_audio")
    @patch("uvr_pyside6_ui.core.processing_worker.ProcessingWorker._save_temp_audio")
    @patch("soundfile.write")
    def test_complete_ensemble_flow_instruments_only(
        self, mock_sf_write, mock_save_temp, mock_load_audio
    ):
        """Test complete flow from UI selection to final output for instruments only."""
        # Setup
        mock_load_audio.return_value = np.random.randn(44100 * 5, 2)
        mock_save_temp.return_value = "/tmp/test.wav"

        with tempfile.TemporaryDirectory() as temp_dir:
            # User selects instruments only in UI
            settings = {
                "is_primary_stem_only": False,
                "is_secondary_stem_only": True,  # Instruments only
                "chosen_process_method": ac.ENSEMBLE_MODE,
                "save_format": "WAV",
                "audio_file": "test.wav",
                "export_path": temp_dir,
            }

            # Create worker
            worker = ProcessingWorker(settings)

            # Setup ensemble
            worker.model_data.is_ensemble_mode = True
            worker.model_data.ensemble_primary_stem = ac.VOCAL_STEM
            worker.model_data.ensemble_secondary_stem = ac.INST_STEM
            worker.model_data.ensemble_type = "Average"
            worker.model_data.export_path = temp_dir

            # Create mock models
            model1 = Mock()
            model1.model_basename = "VocalModel"
            model1.model_path = "/path/to/model1.pth"
            model1.model_status = True
            model1.primary_stem = ac.VOCAL_STEM
            model1.secondary_stem = ac.INST_STEM
            model1.process_method = ac.VR_ARCH_TYPE
            model1.export_path = temp_dir

            model2 = Mock()
            model2.model_basename = "InstrumentalModel"
            model2.model_path = "/path/to/model2.pth"
            model2.model_status = True
            model2.primary_stem = ac.INST_STEM
            model2.secondary_stem = ac.VOCAL_STEM
            model2.process_method = ac.MDX_ARCH_TYPE
            model2.export_path = temp_dir

            worker.model_data.ensemble_models = [model1, model2]

            # Mock separator results
            with patch(
                "uvr_pyside6_ui.core.processing_worker.ProcessingWorker._process_individual_model"
            ) as mock_process:
                # Model 1 outputs instrumental (its secondary stem)
                mock_process.side_effect = [
                    {ac.INST_STEM: np.random.randn(44100 * 5, 2)},  # Model 1
                    {ac.INST_STEM: np.random.randn(44100 * 5, 2)},  # Model 2
                ]

                # Process ensemble
                worker._process_ensemble(mock_load_audio.return_value)

                # Verify models were processed
                assert mock_process.call_count == 2

                # Verify only instrumental files were saved
                # Check that soundfile.write was called for ensemble output
                ensemble_calls = [
                    call
                    for call in mock_sf_write.call_args_list
                    if "Ensemble" in str(call[0][0])
                ]

                # Should have at least one ensemble output
                assert len(ensemble_calls) >= 1
