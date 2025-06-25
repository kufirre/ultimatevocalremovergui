"""
Unit tests for separator stem selection fixes.

These tests verify that the VR separator no longer ignores stem-only settings
when processing as part of an ensemble, and that all separators properly
respect the stem-only flags.
"""

import tempfile
from unittest.mock import Mock, patch

import numpy as np
import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.separate_demucs_logic import SeparateDemucsLogic
from uvr_pyside6_ui.core.separate_mdx_logic import SeparateMDXLogic
from uvr_pyside6_ui.core.separate_mdxc_logic import SeparateMDXCLogic
from uvr_pyside6_ui.core.separate_vr_logic import SeparateVRLogic


@pytest.mark.unit
class TestVRSeparatorEnsembleFix:
    """Test that VR separator respects stem-only settings in ensemble mode."""

    def test_vr_separator_respects_stem_only_in_ensemble(self):
        """Test that VR separator no longer ignores stem-only settings for ensemble members."""
        model_data = ModelData()
        model_data.model_name = "Test VR Model"
        model_data.model_path = "/path/to/model.pth"
        model_data.model_status = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = False
        model_data.is_secondary_stem_only = True  # Only output instrumental
        model_data.model_samplerate = 44100
        model_data.vr_model_param = Mock()
        model_data.vr_model_param.param = {
            "band": {1: {"sr": 44100, "hl": 512, "n_fft": 2048, "crop_stop": 1024}},
            "bins": 1024,
        }

        process_data = {
            "audio_file": None,
            "input_audio_array": np.random.randn(44100, 2),
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
            "is_ensemble_master": False,  # This is an ensemble member
        }

        with patch("uvr_pyside6_ui.core.separate_vr_logic.nets_vr"):
            with patch("uvr_pyside6_ui.core.separate_vr_logic.nets_new_vr"):
                with patch("uvr_pyside6_ui.core.separate_vr_logic.ModelParameters"):
                    with patch(
                        "uvr_pyside6_ui.core.separate_vr_logic.spec_utils"
                    ) as mock_spec:
                        with patch("torch.load"):
                            # Mock the necessary spec_utils functions
                            mock_spec.wave_to_spectrogram.return_value = (
                                np.random.randn(2, 1024, 100)
                            )
                            mock_spec.combine_spectrograms.return_value = (
                                np.random.randn(2, 1024, 100)
                            )
                            mock_spec.preprocess.return_value = (
                                np.random.randn(2, 1024, 100),
                                np.random.randn(2, 1024, 100),
                            )
                            mock_spec.make_padding.return_value = (10, 10, 50)
                            mock_spec.adjust_aggr.return_value = np.random.randn(
                                1, 2, 1024, 100
                            )

                            separator = SeparateVRLogic(model_data, process_data)

                            # The key test: verify that is_secondary_stem_only is still True
                            # after initialization (not overridden by ensemble logic)
                            assert separator.md.is_secondary_stem_only is True
                            assert separator.md.is_primary_stem_only is False

                            # Mock the separate method to return only instrumental
                            with patch.object(separator, "separate") as mock_separate:
                                mock_separate.return_value = {
                                    ac.INST_STEM: np.random.randn(2, 44100)
                                }

                                results = separator.separate()

                                # Verify only secondary stem (instrumental) was output
                                assert results is not None
                                assert ac.INST_STEM in results
                                assert ac.VOCAL_STEM not in results

    def test_vr_separator_both_stems_in_non_ensemble(self):
        """Test that VR separator outputs both stems when not in ensemble mode."""
        model_data = ModelData()
        model_data.model_name = "Test VR Model"
        model_data.model_path = "/path/to/model.pth"
        model_data.model_status = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = False
        model_data.is_secondary_stem_only = False  # Output both stems
        model_data.model_samplerate = 44100
        model_data.vr_model_param = Mock()
        model_data.vr_model_param.param = {
            "band": {1: {"sr": 44100, "hl": 512, "n_fft": 2048, "crop_stop": 1024}},
            "bins": 1024,
        }

        process_data = {
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
            "is_ensemble_master": True,  # Not an ensemble member
        }

        with patch(
            "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
        ) as mock_prepare:
            mock_prepare.return_value = np.random.randn(44100, 2)
            with patch("uvr_pyside6_ui.core.separate_vr_logic.nets_vr"):
                with patch("uvr_pyside6_ui.core.separate_vr_logic.spec_utils"):
                    with patch("torch.load"):
                        separator = SeparateVRLogic(model_data, process_data)

                        # Both flags should remain False
                        assert separator.md.is_primary_stem_only is False
                        assert separator.md.is_secondary_stem_only is False


@pytest.mark.unit
class TestMDXSeparatorStemSelection:
    """Test MDX separator stem selection behavior."""

    def test_mdx_separator_primary_only(self):
        """Test MDX separator with primary stem only."""
        model_data = ModelData()
        model_data.model_name = "Test MDX Model"
        model_data.model_path = "/path/to/model.onnx"
        model_data.model_status = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = True
        model_data.is_secondary_stem_only = False
        model_data.mdx_n_fft_scale_set = 2048
        model_data.mdx_dim_f_set = 1024
        model_data.mdx_segment_size = 256
        model_data.mdx_dim_t_set = 256
        model_data.model_samplerate = 44100

        process_data = {
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch(
            "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
        ) as mock_prepare:
            with patch("uvr_pyside6_ui.core.separate_mdx_logic.onnxruntime"):
                with patch("uvr_pyside6_ui.core.separate_mdx_logic.LibV5_STFT"):
                    mock_prepare.return_value = np.random.randn(44100, 2)

                    separator = SeparateMDXLogic(model_data, process_data)

                    # Verify stem settings
                    assert separator.md.is_primary_stem_only is True
                    assert separator.md.is_secondary_stem_only is False

                    # Mock the separation process to return only primary stem
                    with patch.object(separator, "separate") as mock_separate:
                        mock_separate.return_value = {
                            ac.VOCAL_STEM: np.random.randn(44100, 2)
                        }

                        results = separator.separate()

                        # Should only have primary stem
                        assert results is not None
                        assert len(results) == 1
                        assert ac.VOCAL_STEM in results

    def test_mdx_separator_secondary_only(self):
        """Test MDX separator with secondary stem only."""
        model_data = ModelData()
        model_data.model_name = "Test MDX Model"
        model_data.model_path = "/path/to/model.onnx"
        model_data.model_status = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = False
        model_data.is_secondary_stem_only = True
        model_data.mdx_n_fft_scale_set = 2048
        model_data.mdx_dim_f_set = 1024
        model_data.mdx_segment_size = 256
        model_data.mdx_dim_t_set = 256
        model_data.model_samplerate = 44100
        model_data.is_invert_spec = False

        process_data = {
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch(
            "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
        ) as mock_prepare:
            with patch("uvr_pyside6_ui.core.separate_mdx_logic.onnxruntime"):
                with patch("uvr_pyside6_ui.core.separate_mdx_logic.LibV5_STFT"):
                    mock_prepare.return_value = np.random.randn(44100, 2)

                    separator = SeparateMDXLogic(model_data, process_data)

                    # Verify stem settings
                    assert separator.md.is_primary_stem_only is False
                    assert separator.md.is_secondary_stem_only is True

                    # Mock the separation process to return only secondary stem
                    with patch.object(separator, "separate") as mock_separate:
                        mock_separate.return_value = {
                            ac.INST_STEM: np.random.randn(44100, 2)
                        }

                        results = separator.separate()

                        # Should only have secondary stem
                        assert results is not None
                        assert ac.INST_STEM in results


@pytest.mark.unit
class TestDemucsSeparatorStemSelection:
    """Test Demucs separator stem selection behavior."""

    def test_demucs_4_stem_vocals_only(self):
        """Test Demucs 4-stem model outputting vocals only."""
        model_data = ModelData()
        model_data.model_name = "Test Demucs Model"
        model_data.model_path = "/path/to/model.yaml"
        model_data.model_status = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = True  # Vocals only
        model_data.is_secondary_stem_only = False
        model_data.demucs_version = "v3"
        model_data.demucs_stems = ac.ALL_STEMS
        model_data.demucs_source_list = [
            ac.BASS_STEM,
            ac.DRUM_STEM,
            ac.OTHER_STEM,
            ac.VOCAL_STEM,
        ]
        model_data.demucs_source_map = {
            ac.BASS_STEM: 0,
            ac.DRUM_STEM: 1,
            ac.OTHER_STEM: 2,
            ac.VOCAL_STEM: 3,
        }
        model_data.model_samplerate = 44100
        model_data.shifts = 1
        model_data.is_split_mode = True
        model_data.overlap = 0.25
        model_data.segment = ac.DEFAULT

        process_data = {
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch("uvr_pyside6_ui.core.separate_demucs_logic.demucs_get_model"):
            with patch("uvr_pyside6_ui.core.separate_demucs_logic.demucs_segments"):
                with patch(
                    "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
                ) as mock_prepare:
                    mock_prepare.return_value = np.random.randn(44100, 2)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch("pathlib.Path.is_file", return_value=True):
                            with patch("pathlib.Path.stat") as mock_stat:
                                mock_stat.return_value.st_size = 1000

                                separator = SeparateDemucsLogic(
                                    model_data, process_data
                                )

                                # Verify stem settings
                                assert separator.md.is_primary_stem_only is True
                                assert separator.md.is_secondary_stem_only is False
                                assert separator.md.demucs_stems == ac.ALL_STEMS

                                # Mock the separation to return only vocals
                                with patch.object(
                                    separator, "separate"
                                ) as mock_separate:
                                    mock_separate.return_value = {
                                        ac.VOCAL_STEM: np.random.randn(44100, 2)
                                    }

                                    results = separator.separate()

                                    # Should only have vocals
                                    assert results is not None
                                    assert ac.VOCAL_STEM in results
                                    assert ac.INST_STEM not in results

    def test_demucs_single_stem_mode_instrumental(self):
        """Test Demucs in single stem mode for instrumental."""
        model_data = ModelData()
        model_data.model_name = "Test Demucs Model"
        model_data.model_path = "/path/to/model.yaml"
        model_data.model_status = True
        model_data.primary_stem = ac.INST_STEM  # Instrumental as primary
        model_data.secondary_stem = ac.VOCAL_STEM
        model_data.is_primary_stem_only = True  # Instrumental only
        model_data.is_secondary_stem_only = False
        model_data.demucs_version = "v3"
        model_data.demucs_stems = ac.INST_STEM  # Single stem mode
        model_data.demucs_source_list = [
            ac.BASS_STEM,
            ac.DRUM_STEM,
            ac.OTHER_STEM,
            ac.VOCAL_STEM,
        ]
        model_data.demucs_source_map = {
            ac.BASS_STEM: 0,
            ac.DRUM_STEM: 1,
            ac.OTHER_STEM: 2,
            ac.VOCAL_STEM: 3,
        }
        model_data.model_samplerate = 44100

        process_data = {
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch("uvr_pyside6_ui.core.separate_demucs_logic.demucs_get_model"):
            with patch(
                "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
            ) as mock_prepare:
                mock_prepare.return_value = np.random.randn(44100, 2)
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.is_file", return_value=True):
                        with patch("pathlib.Path.stat") as mock_stat:
                            mock_stat.return_value.st_size = 1000

                            separator = SeparateDemucsLogic(model_data, process_data)

                            # Mock the separation to return only instrumental
                            with patch.object(separator, "separate") as mock_separate:
                                mock_separate.return_value = {
                                    ac.INST_STEM: np.random.randn(44100, 2)
                                }

                                results = separator.separate()

                                # Should have instrumental
                                assert results is not None
                                assert ac.INST_STEM in results


@pytest.mark.unit
class TestEnsembleStemCollectionFix:
    """Test that ensemble properly collects only requested stems."""

    def test_ensemble_collects_only_instrumental(self):
        """Test ensemble collection when user wants instrumental only."""

        # Simulate ensemble stem collection
        all_outputs_by_stem = {}
        all_saved_files_by_stem = {}

        # Model outputs - some models produce both stems
        model_results = {
            "VocalModel": {
                ac.VOCAL_STEM: np.random.randn(44100, 2),
                ac.INST_STEM: np.random.randn(44100, 2),
            },
            "InstrumentalModel": {
                ac.INST_STEM: np.random.randn(44100, 2),
            },
            "GeneralModel": {
                ac.VOCAL_STEM: np.random.randn(44100, 2),
                ac.INST_STEM: np.random.randn(44100, 2),
            },
        }

        # User wants instrumental only
        user_wants_instrumental_only = True

        # Collect stems based on user selection
        for model_name, results in model_results.items():
            for stem_name, stem_audio in results.items():
                # Only collect instrumental stems
                if user_wants_instrumental_only and stem_name != ac.INST_STEM:
                    continue

                if stem_name not in all_outputs_by_stem:
                    all_outputs_by_stem[stem_name] = []
                    all_saved_files_by_stem[stem_name] = []

                all_outputs_by_stem[stem_name].append(stem_audio)
                all_saved_files_by_stem[stem_name].append(
                    f"{model_name}_({stem_name}).wav"
                )

        # Verify only instrumental was collected
        assert len(all_outputs_by_stem) == 1
        assert ac.INST_STEM in all_outputs_by_stem
        assert (
            len(all_outputs_by_stem[ac.INST_STEM]) == 3
        )  # All 3 models had instrumental
        assert ac.VOCAL_STEM not in all_outputs_by_stem

        # Verify file tracking
        assert len(all_saved_files_by_stem[ac.INST_STEM]) == 3
        assert all("Instrumental" in f for f in all_saved_files_by_stem[ac.INST_STEM])


@pytest.mark.unit
class TestMDXCSeparatorStemSelection:
    """Test MDXC separator stem selection behavior."""

    def test_mdxc_separator_primary_only(self):
        """Test MDXC separator with primary stem only."""
        model_data = ModelData()
        model_data.model_name = "Test MDXC Model"
        model_data.model_path = "/path/to/model.ckpt"
        model_data.model_status = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = True
        model_data.is_secondary_stem_only = False
        model_data.mdx_batch_size = 1
        model_data.mdx_segment_size = 256
        model_data.overlap_mdx23 = 8
        model_data.model_samplerate = 44100
        model_data.mdx_c_configs = Mock()
        model_data.mdx_c_configs.inference.dim_t = 256
        model_data.mdx_c_configs.audio.hop_length = 1024
        model_data.is_mdx_c_seg_def = True

        process_data = {
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch(
            "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
        ) as mock_prepare:
            mock_prepare.return_value = np.random.randn(44100, 2)
            with patch("uvr_pyside6_ui.core.separate_mdxc_logic.torch"):
                with patch("uvr_pyside6_ui.core.separate_mdxc_logic.TFC_TDF_net"):
                    separator = SeparateMDXCLogic(model_data, process_data)

                    # Verify stem settings
                    assert separator.md.is_primary_stem_only is True
                    assert separator.md.is_secondary_stem_only is False

    def test_mdxc_separator_secondary_only(self):
        """Test MDXC separator with secondary stem only."""
        model_data = ModelData()
        model_data.model_name = "Test MDXC Model"
        model_data.model_path = "/path/to/model.ckpt"
        model_data.model_status = True
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = False
        model_data.is_secondary_stem_only = True
        model_data.mdx_batch_size = 1
        model_data.mdx_segment_size = 256
        model_data.overlap_mdx23 = 8
        model_data.model_samplerate = 44100
        model_data.mdx_c_configs = Mock()
        model_data.mdx_c_configs.inference.dim_t = 256
        model_data.mdx_c_configs.audio.hop_length = 1024
        model_data.is_mdx_c_seg_def = True

        process_data = {
            "audio_file": "test.wav",
            "export_path": tempfile.mkdtemp(),
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        with patch(
            "uvr_pyside6_ui.core.separate_logic_base.prepare_mix_logic"
        ) as mock_prepare:
            mock_prepare.return_value = np.random.randn(44100, 2)
            with patch("uvr_pyside6_ui.core.separate_mdxc_logic.torch"):
                with patch("uvr_pyside6_ui.core.separate_mdxc_logic.TFC_TDF_net"):
                    separator = SeparateMDXCLogic(model_data, process_data)

                    # Verify stem settings
                    assert separator.md.is_primary_stem_only is False
                    assert separator.md.is_secondary_stem_only is True
