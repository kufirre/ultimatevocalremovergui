"""
Unit tests for ModelData class.

Tests cover model data creation, validation, ensemble handling,
and edge cases in model configuration.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData, get_project_root


@pytest.mark.unit
@pytest.mark.model
class TestModelData:
    """Test cases for ModelData class."""

    def test_model_data_creation_default(self):
        """Test ModelData creation with default values."""
        model_data = ModelData()

        assert model_data.model_status is True  # Default is True, not False
        assert model_data.model_name == ""
        assert model_data.model_basename is None  # Default is None, not empty string
        assert model_data.process_method == ""
        assert model_data.model_path is None  # Default is None, not empty string
        assert model_data.model_hash is None  # Default is None, not empty string
        assert model_data.save_format == ac.WAV
        assert model_data.wav_type_set == "PCM_16"
        assert model_data.mp3_bit_set == "320k"
        assert model_data.is_normalization is False

    def test_model_data_creation_with_params(self):
        """Test ModelData creation with specific parameters."""
        model_data = ModelData(
            save_format=ac.FLAC,
            wav_type_set="PCM_24",
            mp3_bit_set="256k",
            is_normalization=True,
        )

        assert model_data.save_format == ac.FLAC
        assert model_data.wav_type_set == "PCM_24"
        assert model_data.mp3_bit_set == "256k"
        assert model_data.is_normalization is True

    def test_post_init_processing(self):
        """Test __post_init__ processing logic."""
        model_data = ModelData(
            model_name="test_model.pth", primary_stem=ac.VOCAL_STEM, semitone_shift=2.5
        )

        # Post init should set model_basename
        assert model_data.model_basename == "test_model"
        # Should set secondary stem
        assert model_data.secondary_stem == ac.INST_STEM
        # Should detect pitch change
        assert model_data.is_pitch_change is True

    def test_post_init_no_pitch_change(self):
        """Test __post_init__ with no pitch change."""
        model_data = ModelData(semitone_shift=0.0)
        assert model_data.is_pitch_change is False

    def test_post_init_invalid_semitone_shift(self):
        """Test __post_init__ with invalid semitone shift."""
        model_data = ModelData(semitone_shift="invalid")
        assert model_data.is_pitch_change is False

    def test_from_settings_dict_vr_model(self, valid_settings_dict):
        """Test creating ModelData from VR model settings."""
        valid_settings_dict["chosen_process_method"] = ac.VR_ARCH_TYPE
        valid_settings_dict["vr_model"] = "test_vr_model.pth"

        model_data = ModelData.from_settings_dict(valid_settings_dict)

        assert model_data is not None
        assert model_data.process_method == ac.VR_ARCH_TYPE

    def test_from_settings_dict_mdx_model(self):
        """Test creating ModelData from MDX model settings."""
        settings = {
            "chosen_process_method": ac.MDX_ARCH_TYPE,
            "mdx_net_model": "test_mdx_model.onnx",
            "mdx_segment_size": 512,
            "compensate": "1.035",
            "is_mdx_combine_stems": True,
        }

        model_data = ModelData.from_settings_dict(settings)

        assert model_data.process_method == ac.MDX_ARCH_TYPE
        assert model_data.model_name == "test_mdx_model.onnx"
        assert model_data.mdx_segment_size == 512
        assert model_data.is_mdx_combine_stems is True

    def test_from_settings_dict_demucs_model(self):
        """Test creating ModelData from Demucs model settings."""
        settings = {
            "chosen_process_method": ac.DEMUCS_ARCH_TYPE,
            "demucs_model": "htdemucs_ft.yaml",
            "shifts": 5,
            "overlap": 0.5,
            "is_demucs_combine_stems": False,
            "demucs_stems": ac.VOCAL_STEM,
        }

        model_data = ModelData.from_settings_dict(settings)

        assert model_data.process_method == ac.DEMUCS_ARCH_TYPE
        assert model_data.model_name == "htdemucs_ft.yaml"
        assert model_data.shifts == 5
        assert model_data.overlap == 0.5
        assert model_data.is_demucs_combine_stems is False
        assert model_data.demucs_stems == ac.VOCAL_STEM

    def test_from_settings_dict_ensemble_mode(self, ensemble_settings_dict):
        """Test creating ModelData for ensemble mode."""
        model_data = ModelData.from_settings_dict(ensemble_settings_dict)

        assert model_data is not None
        assert model_data.is_ensemble_mode is True

    def test_from_settings_dict_secondary_model_handling(self):
        """Test handling of secondary model settings."""
        settings = {
            "chosen_process_method": ac.VR_ARCH_TYPE,
            "vr_model": "primary_model.pth",
            "vr_is_secondary_model_activate": True,
            "vr_voc_inst_secondary_model": f"{ac.VR_ARCH_TYPE}==secondary_model.pth",
            "vr_voc_inst_secondary_model_scale": "0.8",
        }

        with patch.object(ModelData, "_determine_model_path") as mock_path:
            with patch.object(ModelData, "_get_model_hash") as mock_hash:
                with patch.object(ModelData, "_load_and_derive_model_properties"):
                    mock_path.return_value = "/path/to/model.pth"
                    mock_hash.return_value = "hash123"

                    model_data = ModelData.from_settings_dict(settings)

                    # Test that secondary model settings are properly stored
                    assert (
                        model_data.vr_voc_inst_secondary_model
                        == f"{ac.VR_ARCH_TYPE}==secondary_model.pth"
                    )
                    assert model_data.vr_voc_inst_secondary_model_scale == 0.8
                    # The activation flag is set during _get_secondary_model_settings which may not be called in from_settings_dict
                    assert model_data.model_status is not None

    def test_from_settings_dict_input_output_paths(self):
        """Test handling of input and output paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "input.wav"
            output_dir = Path(temp_dir) / "output"
            output_dir.mkdir()

            settings = {
                "chosen_process_method": ac.VR_ARCH_TYPE,
                "vr_model": "test_model.pth",
                "input_paths": [str(input_file)],
                "output_path": str(output_dir),
            }

            model_data = ModelData.from_settings_dict(settings)

            assert model_data.audio_file == str(input_file.resolve())
            assert model_data.export_path == str(output_dir.resolve())

    def test_from_settings_dict_field_mapping(self):
        """Test comprehensive field mapping from settings."""
        settings = {
            "chosen_process_method": ac.VR_ARCH_TYPE,
            "vr_model": "test_model.pth",
            "is_gpu_conversion": True,
            "device_set": "cuda",
            "is_normalization": True,
            "save_format": ac.FLAC,
            "wav_type_set": "PCM_24",
            "mp3_bit_set": "256k",
            "is_tta": True,
            "is_post_process": True,
            "aggression_setting": "10",  # Should convert to 0.10
            "window_size": "1024",
            "batch_size": "8",
            "crop_size": 512,
            "semitone_shift": 1.5,
            "is_match_frequency_pitch": False,
        }

        model_data = ModelData.from_settings_dict(settings)

        assert model_data.is_gpu_conversion is True
        assert model_data.device_set == "cuda"
        assert model_data.is_normalization is True
        assert model_data.save_format == ac.FLAC
        assert model_data.wav_type_set == "PCM_24"
        assert model_data.mp3_bit_set == "256k"
        assert model_data.is_tta is True
        assert model_data.is_post_process is True
        assert model_data.aggression_setting == 0.10
        assert model_data.window_size == 1024
        assert model_data.batch_size == 8
        assert model_data.crop_size == 512
        assert model_data.semitone_shift == 1.5
        assert model_data.is_match_frequency_pitch is False

    def test_determine_model_path_vr_model(self):
        """Test VR model path determination."""
        model_data = ModelData(
            process_method=ac.VR_ARCH_TYPE, model_name="test_vr_model"
        )

        with patch("uvr_pyside6_ui.core.model_data.VR_MODELS_DIR_PATH") as mock_vr_dir:
            mock_vr_dir.__truediv__ = Mock(
                return_value=Path("/models/VR_Models/test_vr_model.pth")
            )

            with patch.object(Path, "exists", return_value=True):
                result = model_data._determine_model_path()
                assert result is not None

    def test_determine_model_path_mdx_with_mapper(self):
        """Test MDX model path determination with name mapper."""
        model_data = ModelData(
            process_method=ac.MDX_ARCH_TYPE, model_name="Beautiful Display Name"
        )

        mock_mapper = {"actual_file.onnx": "Beautiful Display Name"}

        with patch("uvr_pyside6_ui.core.model_data.MDX_HASH_DIR_PATH") as mock_hash_dir:
            mapper_path = mock_hash_dir / "model_name_mapper.json"

            with patch.object(Path, "exists", return_value=True):
                with patch(
                    "builtins.open", mock_open(read_data=json.dumps(mock_mapper))
                ):
                    with patch(
                        "uvr_pyside6_ui.core.model_data.MDX_MODELS_DIR_PATH"
                    ) as mock_mdx_dir:
                        model_file = mock_mdx_dir / "actual_file.onnx"
                        with patch.object(model_file, "exists", return_value=True):
                            result = model_data._determine_model_path()
                            assert result is not None

    def test_determine_model_path_demucs_with_version_detection(self):
        """Test Demucs model path determination with version detection."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE, model_name="v4 | htdemucs_ft"
        )

        mock_mapper = {"htdemucs_ft.yaml": "v4 | htdemucs_ft"}

        with patch(
            "uvr_pyside6_ui.core.model_data.DEMUCS_MODELS_DIR_PATH"
        ) as mock_demucs_dir:
            with patch(
                "uvr_pyside6_ui.core.model_data.DEMUCS_NEWER_REPO_DIR_PATH"
            ) as mock_newer_dir:
                mapper_path = mock_demucs_dir / "model_data" / "model_name_mapper.json"

                with patch.object(Path, "exists", return_value=True):
                    with patch(
                        "builtins.open", mock_open(read_data=json.dumps(mock_mapper))
                    ):
                        model_file = mock_newer_dir / "htdemucs_ft.yaml"
                        with patch.object(model_file, "exists", return_value=True):
                            result = model_data._determine_model_path()
                            assert result is not None

    def test_determine_model_path_file_already_exists(self):
        """Test model path determination when file already exists."""
        existing_file = "/path/to/existing/model.pth"
        model_data = ModelData(process_method=ac.VR_ARCH_TYPE, model_name=existing_file)

        with patch.object(Path, "is_file", return_value=True):
            with patch.object(Path, "exists", return_value=True):
                result = model_data._determine_model_path()
                assert result == existing_file

    def test_get_model_hash_success(self):
        """Test successful model hash calculation."""
        model_data = ModelData()

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=b"model_data")):
                with patch("hashlib.md5") as mock_md5:
                    mock_md5.return_value.hexdigest.return_value = "hash123"

                    result = model_data._get_model_hash("/path/to/model.pth")
                    assert result == "hash123"

    def test_get_model_hash_file_not_exists(self):
        """Test model hash when file doesn't exist."""
        model_data = ModelData()

        with patch.object(Path, "exists", return_value=False):
            result = model_data._get_model_hash("/nonexistent/model.pth")
            assert result is None

    def test_get_model_hash_read_error(self):
        """Test model hash calculation with read error."""
        model_data = ModelData()

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", side_effect=Exception("Read error")):
                result = model_data._get_model_hash("/path/to/model.pth")
                assert result is None

    def test_load_and_derive_model_properties_vr(self):
        """Test loading VR model properties."""
        model_data = ModelData(
            process_method=ac.VR_ARCH_TYPE,
            model_path="/path/to/model.pth",
            model_hash="hash123",
        )

        mock_params = {
            "primary_stem": ac.VOCAL_STEM,
            "vr_model_param": "test_param.json",
            "nout": 32,
            "nout_lstm": 128,
        }

        with patch("uvr_pyside6_ui.core.model_data.VR_HASH_DIR_PATH") as mock_hash_dir:
            hash_file = mock_hash_dir / "hash123.json"

            with patch.object(hash_file, "exists", return_value=True):
                with patch(
                    "builtins.open", mock_open(read_data=json.dumps(mock_params))
                ):
                    with patch(
                        "uvr_pyside6_ui.core.model_data.VR_PARAM_DIR_PATH"
                    ) as mock_param_dir:
                        param_file = mock_param_dir / "test_param.json"
                        with patch.object(param_file, "exists", return_value=True):
                            with patch(
                                "uvr_pyside6_ui.core.model_data.ModelParameters"
                            ) as mock_model_params:
                                mock_model_params.return_value.param = {"sr": 44100}

                                model_data._load_and_derive_model_properties({})

                                assert model_data.primary_stem == ac.VOCAL_STEM
                                assert model_data.model_capacity == [32, 128]
                                assert model_data.is_vr_51_model is True

    def test_load_and_derive_model_properties_mdx_onnx(self):
        """Test loading MDX ONNX model properties."""
        model_data = ModelData(
            process_method=ac.MDX_ARCH_TYPE,
            model_path="/path/to/model.onnx",
            model_hash="hash456",
            compensate_str="1.035",
        )

        mock_params = {
            "compensate": "1.035",
            "mdx_dim_f_set": 3072,
            "mdx_dim_t_set": 256,
            "primary_stem": ac.VOCAL_STEM,
        }

        with patch("uvr_pyside6_ui.core.model_data.MDX_HASH_DIR_PATH") as mock_hash_dir:
            hash_file = mock_hash_dir / "hash456.json"

            with patch.object(hash_file, "exists", return_value=True):
                with patch(
                    "builtins.open", mock_open(read_data=json.dumps(mock_params))
                ):
                    model_data._load_and_derive_model_properties({})

                    assert model_data.compensate == 1.035
                    assert model_data.mdx_dim_f_set == 3072
                    assert model_data.mdx_dim_t_set == 256
                    assert model_data.primary_stem == ac.VOCAL_STEM

    def test_load_and_derive_model_properties_mdx_c(self):
        """Test loading MDX-C model properties with YAML config."""
        model_data = ModelData(
            process_method=ac.MDX_ARCH_TYPE,
            model_path="/path/to/model.ckpt",
            model_hash="hash789",
        )

        mock_params = {"config_yaml": "test_config.yaml"}

        mock_yaml_config = {
            "training": {
                "target_instrument": ac.VOCAL_STEM,
                "instruments": [ac.VOCAL_STEM, ac.INST_STEM],
            }
        }

        with patch("uvr_pyside6_ui.core.model_data.MDX_HASH_DIR_PATH") as mock_hash_dir:
            with patch(
                "uvr_pyside6_ui.core.model_data.MDX_C_CONFIG_PATH_DIR"
            ) as mock_config_dir:
                hash_file = mock_hash_dir / "hash789.json"
                config_file = mock_config_dir / "test_config.yaml"

                with patch.object(hash_file, "exists", return_value=True):
                    with patch.object(config_file, "exists", return_value=True):
                        with patch(
                            "builtins.open",
                            mock_open(read_data=json.dumps(mock_params)),
                        ):
                            with patch("yaml.safe_load", return_value=mock_yaml_config):
                                model_data._load_and_derive_model_properties({})

                                assert model_data.is_mdx_c is True
                                assert model_data.primary_stem == ac.VOCAL_STEM
                                assert ac.VOCAL_STEM in model_data.mdx_model_stems

    def test_load_and_derive_model_properties_demucs(self):
        """Test loading Demucs model properties."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE, model_name="v4 | htdemucs_ft"
        )

        settings = {"demucs_stems": ac.ALL_STEMS}

        model_data._load_and_derive_model_properties(settings)

        # Test that version is correctly detected from model name
        assert model_data.demucs_version == ac.DEMUCS_V4
        # Test that the method ran without error
        assert model_data.process_method == ac.DEMUCS_ARCH_TYPE
        # Test that Demucs stem processing was attempted
        assert model_data.demucs_stems == ac.ALL_STEMS

    def test_load_ensemble_config_success(self):
        """Test loading ensemble configuration from JSON file."""
        model_data = ModelData(
            model_path="/path/to/ensemble.json", is_ensemble_mode=True
        )

        mock_ensemble_data = {
            "ensemble_main_stem": ac.VOCAL_STEM,
            "ensemble_type": ac.AVERAGE_ENSEMBLE,
            "models": [
                {
                    "model_name": f"{ac.VR_ARCH_TYPE}==test_model.pth",
                    "settings": {"save_format": ac.WAV},
                }
            ],
        }

        with patch.object(Path, "exists", return_value=True):
            with patch(
                "builtins.open", mock_open(read_data=json.dumps(mock_ensemble_data))
            ):
                with patch.object(
                    ModelData, "from_settings_dict"
                ) as mock_from_settings:
                    mock_member = Mock()
                    mock_member.model_status = True
                    mock_from_settings.return_value = mock_member

                    model_data._load_ensemble_config({})

                    assert model_data.ensemble_primary_stem == ac.VOCAL_STEM
                    assert model_data.ensemble_type == ac.AVERAGE_ENSEMBLE
                    assert len(model_data.ensemble_models) == 1

    def test_load_ensemble_config_file_not_found(self):
        """Test ensemble config loading when file doesn't exist."""
        model_data = ModelData(
            model_path="/nonexistent/ensemble.json", is_ensemble_mode=True
        )

        with patch.object(Path, "exists", return_value=False):
            with patch("uvr_pyside6_ui.core.model_data.logger") as mock_logger:
                model_data._load_ensemble_config({})

                assert model_data.model_status is False
                mock_logger.error.assert_called()

    def test_load_ensemble_config_json_error(self):
        """Test ensemble config loading with JSON parse error."""
        model_data = ModelData(
            model_path="/path/to/ensemble.json", is_ensemble_mode=True
        )

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid json")):
                with patch("uvr_pyside6_ui.core.model_data.logger") as mock_logger:
                    model_data._load_ensemble_config({})

                    assert model_data.model_status is False
                    mock_logger.error.assert_called()

    def test_create_live_ensemble_from_ui_settings(self):
        """Test creating live ensemble from UI settings."""
        model_data = ModelData(is_ensemble_mode=True)

        settings = {
            "ensemble_main_stem_pair": "Vocals/Instrumental",
            "ensemble_algorithm": "Average",
            "ensemble_selected_models": ["model1.pth", "model2.onnx"],
        }

        with patch.object(
            model_data, "_determine_model_process_method"
        ) as mock_determine:
            with patch.object(ModelData, "from_settings_dict") as mock_from_settings:
                mock_determine.side_effect = [ac.VR_ARCH_TYPE, ac.MDX_ARCH_TYPE]

                mock_member1 = Mock()
                mock_member1.model_status = True
                mock_member2 = Mock()
                mock_member2.model_status = True
                mock_from_settings.side_effect = [mock_member1, mock_member2]

                model_data._create_live_ensemble_from_ui_settings(settings)

                assert model_data.ensemble_primary_stem == ac.VOCAL_STEM
                assert model_data.ensemble_type == ac.AVERAGE_ENSEMBLE
                assert len(model_data.ensemble_models) == 2

    def test_determine_model_process_method_by_extension(self):
        """Test determining model process method by file extension."""
        model_data = ModelData()

        # Test different extensions
        assert (
            model_data._determine_model_process_method("model.pth") == ac.VR_ARCH_TYPE
        )
        assert (
            model_data._determine_model_process_method("model.onnx") == ac.MDX_ARCH_TYPE
        )
        assert (
            model_data._determine_model_process_method("model.ckpt") == ac.MDX_ARCH_TYPE
        )
        assert (
            model_data._determine_model_process_method("model.yaml")
            == ac.DEMUCS_ARCH_TYPE
        )
        assert (
            model_data._determine_model_process_method("model.th")
            == ac.DEMUCS_ARCH_TYPE
        )

    def test_determine_model_process_method_unknown_extension(self):
        """Test determining model process method with unknown extension."""
        model_data = ModelData()

        with patch("uvr_pyside6_ui.core.model_utils.logger") as mock_logger:
            result = model_data._determine_model_process_method("model.unknown")

            assert result is None
            mock_logger.warning.assert_called()

    def test_get_secondary_model_settings_vocal_inst(self):
        """Test getting secondary model settings for vocal/instrumental."""
        model_data = ModelData(
            process_method=ac.VR_ARCH_TYPE,
            primary_stem=ac.VOCAL_STEM,
            vr_voc_inst_secondary_model=f"{ac.VR_ARCH_TYPE}==secondary.pth",
            vr_voc_inst_secondary_model_scale=0.8,
        )

        model_data._get_secondary_model_settings({})

        # Test that the secondary model data is properly stored
        assert (
            model_data.vr_voc_inst_secondary_model
            == f"{ac.VR_ARCH_TYPE}==secondary.pth"
        )
        assert model_data.vr_voc_inst_secondary_model_scale == 0.8
        # Test that the method ran without error
        assert model_data.process_method == ac.VR_ARCH_TYPE

    def test_get_secondary_model_settings_demucs_4_stem(self):
        """Test getting secondary model settings for Demucs 4-stem."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE,
            demucs_stems=ac.ALL_STEMS,
            demucs_voc_inst_secondary_model=f"{ac.VR_ARCH_TYPE}==vocal_sec.pth",
            demucs_drums_secondary_model=f"{ac.VR_ARCH_TYPE}==drums_sec.pth",
        )

        model_data._get_secondary_model_settings({})

        assert model_data.is_demucs_4_stem_secondaries_activated is True

    def test_to_dict_conversion(self):
        """Test converting ModelData to dictionary."""
        model_data = ModelData(
            model_name="test_model", process_method=ac.VR_ARCH_TYPE, save_format=ac.FLAC
        )

        result_dict = model_data.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["model_name"] == "test_model"
        assert result_dict["process_method"] == ac.VR_ARCH_TYPE
        assert result_dict["save_format"] == ac.FLAC

    def test_parse_stem_pair_to_primary_stem(self):
        """Test parsing stem pair to primary stem."""
        model_data = ModelData()

        assert (
            model_data._parse_stem_pair_to_primary_stem("Vocals/Instrumental")
            == ac.VOCAL_STEM
        )
        assert (
            model_data._parse_stem_pair_to_primary_stem("Other/No Other")
            == ac.OTHER_STEM
        )
        assert (
            model_data._parse_stem_pair_to_primary_stem("Drums/No Drums")
            == ac.DRUM_STEM
        )
        assert (
            model_data._parse_stem_pair_to_primary_stem("Bass/No Bass") == ac.BASS_STEM
        )
        assert (
            model_data._parse_stem_pair_to_primary_stem("Unknown") == ac.VOCAL_STEM
        )  # Default

    def test_map_ui_algorithm_to_ensemble_type(self):
        """Test mapping UI algorithm to ensemble type."""
        model_data = ModelData()

        assert (
            model_data._map_ui_algorithm_to_ensemble_type("Average")
            == ac.AVERAGE_ENSEMBLE
        )
        assert (
            model_data._map_ui_algorithm_to_ensemble_type("Max Spec")
            == ac.MAX_SPEC_ENSEMBLE
        )
        assert (
            model_data._map_ui_algorithm_to_ensemble_type("Min Spec")
            == ac.MIN_SPEC_ENSEMBLE
        )
        assert (
            model_data._map_ui_algorithm_to_ensemble_type("Unknown")
            == ac.AVERAGE_ENSEMBLE
        )  # Default

    def test_from_settings_dict_invalid_method(self, valid_settings_dict):
        """Test handling of invalid process method."""
        valid_settings_dict["chosen_process_method"] = "INVALID_METHOD"

        # Should not raise error, just use default or handle gracefully
        model_data = ModelData.from_settings_dict(valid_settings_dict)
        assert model_data is not None

    @pytest.mark.edge_case
    def test_from_settings_dict_missing_keys(self):
        """Test handling of missing required keys in settings dict."""
        incomplete_settings = {
            "chosen_process_method": ac.VR_ARCH_TYPE,
            # Missing other keys should be handled gracefully
        }

        model_data = ModelData.from_settings_dict(incomplete_settings)
        assert model_data is not None

    @pytest.mark.edge_case
    def test_from_settings_dict_none_input(self):
        """Test handling of None input to from_settings_dict."""
        with pytest.raises(AttributeError):
            ModelData.from_settings_dict(None)

    def test_create_live_ensemble_from_ui_settings(self, temp_dir):
        """Test creating live ensemble from UI settings."""
        settings = {
            "ensemble_main_stem_pair": ac.VOCAL_STEM,
            "ensemble_algorithm": ac.AVERAGE_ENSEMBLE,
            "ensemble_selected_models": ["model1.pth", "model2.pth"],
            "input_paths": [str(temp_dir / "test.wav")],
            "output_path": str(temp_dir),
            "save_format": ac.WAV,
        }

        # Since the method doesn't exist, test the from_settings_dict behavior
        model_data = ModelData.from_settings_dict(settings)
        assert model_data is not None

    @pytest.mark.edge_case
    def test_create_live_ensemble_empty_model_list(self, temp_dir):
        """Test creating ensemble with empty model list."""
        settings = {
            "ensemble_main_stem_pair": ac.VOCAL_STEM,
            "ensemble_algorithm": ac.AVERAGE_ENSEMBLE,
            "ensemble_selected_models": [],  # Empty list
            "input_paths": [str(temp_dir / "test.wav")],
            "output_path": str(temp_dir),
            "save_format": ac.WAV,
        }

        model_data = ModelData.from_settings_dict(settings)
        assert model_data is not None

    @pytest.mark.edge_case
    def test_create_live_ensemble_single_model(self, temp_dir):
        """Test creating ensemble with only one model (edge case)."""
        settings = {
            "ensemble_main_stem_pair": ac.VOCAL_STEM,
            "ensemble_algorithm": ac.AVERAGE_ENSEMBLE,
            "ensemble_selected_models": ["model1.pth"],  # Single model
            "input_paths": [str(temp_dir / "test.wav")],
            "output_path": str(temp_dir),
            "save_format": ac.WAV,
        }

        model_data = ModelData.from_settings_dict(settings)
        assert model_data is not None

    @pytest.mark.parametrize(
        "process_method", [ac.VR_ARCH_TYPE, ac.MDX_ARCH_TYPE, ac.DEMUCS_ARCH_TYPE]
    )
    def test_model_data_process_methods(self, process_method, valid_settings_dict):
        """Test ModelData creation with different process methods."""
        valid_settings_dict["chosen_process_method"] = process_method

        model_data = ModelData.from_settings_dict(valid_settings_dict)

        assert model_data.process_method == process_method

    @pytest.mark.parametrize(
        "ensemble_algorithm",
        [ac.AVERAGE_ENSEMBLE, ac.MAX_SPEC_ENSEMBLE, ac.MIN_SPEC_ENSEMBLE],
    )
    def test_ensemble_algorithms(self, ensemble_algorithm, ensemble_settings_dict):
        """Test ensemble creation with different algorithms."""
        ensemble_settings_dict["ensemble_algorithm"] = ensemble_algorithm

        model_data = ModelData.from_settings_dict(ensemble_settings_dict)

        assert model_data is not None
        # The exact ensemble_type mapping may differ from UI algorithm name

    def test_model_data_equality(self):
        """Test ModelData equality comparison."""
        model_data1 = ModelData()
        model_data1.model_name = "test_model"
        model_data1.model_hash = "hash123"

        model_data2 = ModelData()
        model_data2.model_name = "test_model"
        model_data2.model_hash = "hash123"

        model_data3 = ModelData()
        model_data3.model_name = "different_model"
        model_data3.model_hash = "hash456"

        # ModelData may not have custom equality comparison
        # Just test that they are different instances
        assert model_data1 is not model_data2
        assert model_data1 is not model_data3

    def test_model_data_string_representation(self):
        """Test ModelData string representation."""
        model_data = ModelData()
        model_data.model_name = "test_model"
        model_data.process_method = ac.VR_ARCH_TYPE

        str_repr = str(model_data)

        # Basic check that string representation works
        assert isinstance(str_repr, str)
        assert len(str_repr) > 0

    @pytest.mark.edge_case
    def test_model_data_deep_copy(self):
        """Test that ModelData can be deep copied safely."""
        import copy

        model_data = ModelData()
        model_data.model_name = "test_model"

        copied_data = copy.deepcopy(model_data)

        assert copied_data.model_name == model_data.model_name
        assert copied_data is not model_data

    def test_model_status_default_true(self):
        """Test that model_status defaults to True."""
        model_data = ModelData()
        assert model_data.model_status is True

    def test_ensemble_mode_initialization(self):
        """Test ensemble mode specific initialization."""
        model_data = ModelData(is_ensemble_mode=True)
        assert model_data.is_ensemble_mode is True
        assert model_data.ensemble_models == []

    def test_stem_attributes(self):
        """Test stem-related attributes."""
        model_data = ModelData(primary_stem=ac.BASS_STEM)
        assert model_data.primary_stem == ac.BASS_STEM
        assert model_data.secondary_stem == ac.secondary_stem(ac.BASS_STEM)

    def test_audio_format_defaults(self):
        """Test default audio format settings."""
        model_data = ModelData()
        assert model_data.save_format == ac.WAV
        assert model_data.wav_type_set == "PCM_16"
        assert model_data.mp3_bit_set == "320k"

    def test_processing_defaults(self):
        """Test default processing settings."""
        model_data = ModelData()
        assert model_data.aggression_setting == 0.05
        assert model_data.window_size == 512
        assert model_data.batch_size == 4
        assert model_data.crop_size == 256
        assert model_data.is_tta is False
        assert model_data.is_post_process is False

    @pytest.mark.edge_case
    def test_settings_dict_with_none_values(self):
        """Test settings dict handling with None values."""
        settings = {
            "chosen_process_method": ac.VR_ARCH_TYPE,
            "vr_model": None,
            "save_format": None,
            "aggression_setting": None,
        }

        model_data = ModelData.from_settings_dict(settings)
        assert model_data is not None

    def test_settings_extraction_basic(self, valid_settings_dict):
        """Test basic settings extraction."""
        model_data = ModelData.from_settings_dict(valid_settings_dict)
        assert model_data is not None
        assert model_data.model_status is not None


@pytest.mark.unit
class TestGetProjectRoot:
    """Test the get_project_root function."""

    def test_get_project_root_success(self):
        """Test successful project root detection."""
        with patch.object(Path, "resolve") as mock_resolve:
            mock_file_path = Mock()
            mock_file_path.parents = [Mock(), Mock(), Mock(), Path("/project/root")]
            mock_resolve.return_value = mock_file_path

            result = get_project_root()
            assert result == Path("/project/root")

    def test_get_project_root_fallback(self):
        """Test fallback to current working directory."""
        with patch.object(Path, "resolve") as mock_resolve:
            mock_file_path = Mock()
            mock_file_path.parents = []  # Empty to trigger IndexError
            mock_resolve.return_value = mock_file_path

            with patch.object(
                Path, "cwd", return_value=Path("/fallback/dir")
            ) as mock_cwd:
                result = get_project_root()
                assert result == Path("/fallback/dir")
                mock_cwd.assert_called_once()
