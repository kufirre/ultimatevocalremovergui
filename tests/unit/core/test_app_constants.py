"""
Unit tests for app_constants module.

Tests cover all constants, mappings, functions, and classes defined
in the app_constants module to ensure consistency and correctness.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from uvr_pyside6_ui.core import app_constants as ac


@pytest.mark.unit
@pytest.mark.model
class TestAppConstants:
    """Test cases for app constants and mappings."""

    def test_model_type_keys_exist(self):
        """Test that all model type keys are properly defined."""
        assert ac.VR_ARCH_MODELS_KEY == "VR Arch"
        assert ac.MDX_NET_MODELS_KEY == "MDX-Net"
        assert ac.DEMUCS_MODELS_KEY == "Demucs"
        assert ac.ENSEMBLE_MODELS_KEY == "Ensemble"

    def test_model_subdirs_mapping(self):
        """Test model subdirectories mapping is correct."""
        expected_subdirs = {
            "VR Arch": "VR_Models",
            "MDX-Net": "MDX_Net_Models", 
            "Demucs": "Demucs_Models",
            "Ensemble": None
        }
        assert ac.MODEL_TYPE_SUBDIRS == expected_subdirs

    def test_online_catalog_map_structure(self):
        """Test online catalog mapping structure."""
        assert isinstance(ac.ONLINE_CATALOG_MAP, dict)
        for model_type, download_lists in ac.ONLINE_CATALOG_MAP.items():
            assert model_type in ac.MODEL_TYPE_SUBDIRS
            assert isinstance(download_lists, list)

    def test_ensemble_options_exist(self):
        """Test ensemble configuration options are defined."""
        assert len(ac.ENSEMBLE_MAIN_STEM_OPTIONS) > 0
        assert "Vocals/Instrumental" in ac.ENSEMBLE_MAIN_STEM_OPTIONS
        assert "4 Stem Ensemble" in ac.ENSEMBLE_MAIN_STEM_OPTIONS
        
        assert len(ac.ENSEMBLE_ALGORITHM_OPTIONS) > 0
        assert "Average/Average" in ac.ENSEMBLE_ALGORITHM_OPTIONS
        assert "Max Spec/Min Spec" in ac.ENSEMBLE_ALGORITHM_OPTIONS

    def test_processing_method_constants(self):
        """Test processing method constants are defined."""
        assert ac.VR_ARCH_TYPE == 'VR Arc'
        assert ac.MDX_ARCH_TYPE == 'MDX-Net'
        assert ac.DEMUCS_ARCH_TYPE == 'Demucs'
        assert ac.ENSEMBLE_MODE == 'Ensemble Mode'

    def test_stem_constants(self):
        """Test stem constants are properly defined."""
        expected_stems = [
            ac.VOCAL_STEM, ac.INST_STEM, ac.OTHER_STEM,
            ac.BASS_STEM, ac.DRUM_STEM, ac.GUITAR_STEM, ac.PIANO_STEM
        ]
        for stem in expected_stems:
            assert isinstance(stem, str)
            assert len(stem) > 0

    def test_non_accom_stems(self):
        """Test non-accompaniment stems list."""
        assert ac.VOCAL_STEM in ac.NON_ACCOM_STEMS
        assert ac.BASS_STEM in ac.NON_ACCOM_STEMS
        assert ac.DRUM_STEM in ac.NON_ACCOM_STEMS
        assert ac.OTHER_STEM in ac.NON_ACCOM_STEMS
        assert ac.INST_STEM not in ac.NON_ACCOM_STEMS

    def test_secondary_stem_function(self):
        """Test secondary stem mapping function."""
        assert ac.secondary_stem(ac.VOCAL_STEM) == ac.INST_STEM
        assert ac.secondary_stem(ac.INST_STEM) == ac.VOCAL_STEM
        assert ac.secondary_stem(ac.OTHER_STEM) == f'No {ac.OTHER_STEM}'
        assert ac.secondary_stem(ac.BASS_STEM) == f'No {ac.BASS_STEM}'
        assert ac.secondary_stem(ac.DRUM_STEM) == f'No {ac.DRUM_STEM}'
        assert ac.secondary_stem('Unknown') == 'No Unknown'

    def test_audio_format_constants(self):
        """Test audio format constants."""
        assert ac.WAV == 'WAV'
        assert ac.FLAC == 'FLAC'
        assert ac.MP3 == 'MP3'

    def test_demucs_version_constants(self):
        """Test Demucs version constants."""
        assert ac.DEMUCS_V1 == 'v1'
        assert ac.DEMUCS_V2 == 'v2'
        assert ac.DEMUCS_V3 == 'v3'
        assert ac.DEMUCS_V4 == 'v4'

    def test_demucs_source_mappers(self):
        """Test Demucs source mapping dictionaries."""
        # Test 4-source mapper
        assert len(ac.DEMUCS_4_SOURCE_MAPPER) == 4
        assert ac.DEMUCS_4_SOURCE_MAPPER[ac.BASS_STEM] == 0
        assert ac.DEMUCS_4_SOURCE_MAPPER[ac.DRUM_STEM] == 1
        assert ac.DEMUCS_4_SOURCE_MAPPER[ac.OTHER_STEM] == 2
        assert ac.DEMUCS_4_SOURCE_MAPPER[ac.VOCAL_STEM] == 3

        # Test 2-source mapper
        assert len(ac.DEMUCS_2_SOURCE_MAPPER) == 2
        assert ac.DEMUCS_2_SOURCE_MAPPER[ac.INST_STEM] == 0
        assert ac.DEMUCS_2_SOURCE_MAPPER[ac.VOCAL_STEM] == 1

        # Test 6-source mapper
        assert len(ac.DEMUCS_6_SOURCE_MAPPER) == 6
        assert ac.DEMUCS_6_SOURCE_MAPPER[ac.GUITAR_STEM] == 4
        assert ac.DEMUCS_6_SOURCE_MAPPER[ac.PIANO_STEM] == 5

    def test_platform_constants(self):
        """Test platform and system constants."""
        assert isinstance(ac.OPERATING_SYSTEM, str)
        assert isinstance(ac.SYSTEM_ARCH, str)
        assert isinstance(ac.SYSTEM_PROC, str)
        assert isinstance(ac.IS_MACOS, bool)
        assert isinstance(ac.IS_WINDOWS, bool)
        assert isinstance(ac.IS_LINUX, bool)

    def test_device_constants(self):
        """Test device constants for ML processing."""
        assert ac.CPU_DEVICE == 'cpu'
        assert ac.CUDA_DEVICE == 'cuda'
        assert ac.MPS_DEVICE == 'mps'

    def test_execution_provider_constants(self):
        """Test ONNX execution provider constants."""
        assert ac.CPU_EXECUTION_PROVIDER == 'CPUExecutionProvider'
        assert ac.CUDA_EXECUTION_PROVIDER == 'CUDAExecutionProvider'

    def test_file_extension_constants(self):
        """Test file extension constants."""
        assert ac.ONNX_EXT == '.onnx'
        assert ac.CKPT_EXT == '.ckpt'
        assert ac.PTH_EXT == '.pth'
        assert ac.YAML_EXT == '.yaml'
        assert ac.WAV_EXT == '.wav'
        assert ac.FLAC_EXT == '.flac'
        assert ac.MP3_EXT == '.mp3'

    def test_default_values(self):
        """Test default configuration values."""
        assert ac.DEFAULT_SAMPLE_RATE == 44100
        assert ac.VR_WINDOW_SIZE_DEFAULT == 512
        assert ac.VR_AGGRESSION_DEFAULT == 5
        assert ac.MDX_SEGMENT_SIZE_DEFAULT == 256
        assert ac.MDX_OVERLAP_DEFAULT == 0.25

    def test_ensemble_algorithm_types(self):
        """Test specific ensemble algorithm types."""
        assert ac.AVERAGE_ENSEMBLE == "Average"
        assert ac.MAX_SPEC_ENSEMBLE == "Max Spec"
        assert ac.MIN_SPEC_ENSEMBLE == "Min Spec"
        assert ac.DEMUCS_ENSEMBLE_TYPE == "Demucs Ensemble"

    def test_ui_constants(self):
        """Test UI-related constants."""
        assert ac.APP_TITLE == "UVR - PySide6 Edition"
        assert ac.APP_VERSION == "0.1.0"
        assert ac.FUSION_STYLE == "Fusion"

    def test_status_messages(self):
        """Test status message constants."""
        status_messages = [
            ac.STATUS_READY, ac.STATUS_IDLE, ac.STATUS_COMPLETED,
            ac.STATUS_FAILED, ac.STATUS_PROCESSING, ac.STATUS_STARTING
        ]
        for message in status_messages:
            assert isinstance(message, str)
            assert len(message) > 0

    def test_error_constants(self):
        """Test error message constants."""
        assert isinstance(ac.ERROR_MAPPER, dict)
        assert "WINDOW_SIZE_ERROR" in ac.ERROR_MAPPER
        assert "GENERAL_PROCESSING_ERROR" in ac.ERROR_MAPPER

    def test_quality_settings(self):
        """Test audio quality setting constants."""
        quality_settings = [
            ac.QUALITY_PCM_16, ac.QUALITY_PCM_24, ac.QUALITY_PCM_32,
            ac.QUALITY_FLOAT, ac.QUALITY_DOUBLE
        ]
        for quality in quality_settings:
            assert isinstance(quality, str)
            assert len(quality) > 0

    def test_log_level_constants(self):
        """Test logging level constants."""
        log_levels = [
            ac.LOG_LEVEL_DEBUG, ac.LOG_LEVEL_INFO, ac.LOG_LEVEL_WARNING,
            ac.LOG_LEVEL_ERROR, ac.LOG_LEVEL_CRITICAL
        ]
        for level in log_levels:
            assert isinstance(level, str)
            assert len(level) > 0

    def test_fallback_catalog_structure(self):
        """Test fallback online catalog structure."""
        assert isinstance(ac.FALLBACK_ONLINE_CATALOG, dict)
        assert ac.ONLINE_VR_DOWNLOAD_LIST_KEY in ac.FALLBACK_ONLINE_CATALOG
        assert ac.ONLINE_MDX_DOWNLOAD_LIST_KEY in ac.FALLBACK_ONLINE_CATALOG
        assert ac.ONLINE_DEMUCS_DOWNLOAD_LIST_KEY in ac.FALLBACK_ONLINE_CATALOG

    @pytest.mark.parametrize("stem", [
        ac.VOCAL_STEM, ac.INST_STEM, ac.OTHER_STEM, 
        ac.BASS_STEM, ac.DRUM_STEM, ac.GUITAR_STEM, ac.PIANO_STEM
    ])
    def test_stem_secondary_mapping(self, stem):
        """Test secondary stem mapping for all defined stems."""
        secondary = ac.secondary_stem(stem)
        assert isinstance(secondary, str)
        assert len(secondary) > 0


@pytest.mark.unit
@pytest.mark.model  
class TestDummyModelParameters:
    """Test cases for DummyModelParameters class."""

    def test_dummy_model_parameters_default_init(self):
        """Test DummyModelParameters initialization with defaults."""
        params = ac.DummyModelParameters()
        
        assert hasattr(params, 'param')
        assert isinstance(params.param, dict)
        assert 'bins' in params.param
        assert params.param['bins'] == 0
        assert 'band' in params.param
        assert isinstance(params.param['band'], dict)

    def test_dummy_model_parameters_band_structure(self):
        """Test band structure in default parameters."""
        params = ac.DummyModelParameters()
        
        assert 1 in params.param['band']
        band_1 = params.param['band'][1]
        assert 'sr' in band_1
        assert band_1['sr'] == 44100
        assert 'hl' in band_1
        assert 'n_fft' in band_1
        assert 'crop_stop' in band_1

    def test_dummy_model_parameters_with_valid_json_file(self):
        """Test loading parameters from a valid JSON file."""
        test_params = {
            'bins': 1024,
            'band': {
                "1": {'sr': 48000, 'hl': 2048, 'n_fft': 4096, 'crop_stop': 1}
            },
            'pre_filter_start': 100,
            'pre_filter_stop': 8000
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_params, f)
            temp_path = f.name
        
        try:
            params = ac.DummyModelParameters(temp_path)
            
            assert params.param['bins'] == 1024
            assert params.param['band']["1"]['sr'] == 48000
            assert params.param['pre_filter_start'] == 100
            assert params.param['pre_filter_stop'] == 8000
        finally:
            Path(temp_path).unlink()

    def test_dummy_model_parameters_with_nonexistent_file(self):
        """Test handling of nonexistent file path."""
        params = ac.DummyModelParameters("/nonexistent/path.json")
        
        # Should fall back to defaults
        assert params.param['bins'] == 0
        assert 1 in params.param['band']

    def test_dummy_model_parameters_with_invalid_json(self):
        """Test handling of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_path = f.name
        
        try:
            with patch('builtins.print') as mock_print:
                params = ac.DummyModelParameters(temp_path)
                
                # Should fall back to defaults and print warning
                assert params.param['bins'] == 0
                mock_print.assert_called_once()
                assert "Warning" in mock_print.call_args[0][0]
        finally:
            Path(temp_path).unlink()

    def test_dummy_model_parameters_with_string_input(self):
        """Test handling of string input that's not a file path."""
        params = ac.DummyModelParameters("just a string")
        
        # Should use defaults since string is not a valid file path
        assert params.param['bins'] == 0
        assert 1 in params.param['band']

    @pytest.mark.edge_case
    def test_dummy_model_parameters_with_none(self):
        """Test handling of None input."""
        params = ac.DummyModelParameters(None)
        
        assert params.param['bins'] == 0
        assert 1 in params.param['band']

    def test_dummy_model_parameters_param_structure(self):
        """Test complete parameter structure is correct."""
        params = ac.DummyModelParameters()
        
        required_keys = ['bins', 'band', 'pre_filter_start', 'pre_filter_stop', 'aggr_correction']
        for key in required_keys:
            assert key in params.param

    def test_dummy_model_parameters_json_merge(self):
        """Test that JSON parameters properly merge with defaults."""
        test_params = {'bins': 2048}  # Only override bins
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_params, f)
            temp_path = f.name
        
        try:
            params = ac.DummyModelParameters(temp_path)
            
            # Should have overridden bins but kept other defaults
            assert params.param['bins'] == 2048
            assert 'band' in params.param  # Default should remain
            assert params.param['pre_filter_start'] == 0  # Default should remain
        finally:
            Path(temp_path).unlink()


@pytest.mark.unit
class TestConstantConsistency:
    """Test consistency between related constants."""

    def test_model_subdirs_keys_match_model_types(self):
        """Test that MODEL_SUBDIRS keys match model type constants."""
        expected_keys = {
            ac.VR_ARCH_MODELS_KEY,
            ac.MDX_NET_MODELS_KEY, 
            ac.DEMUCS_MODELS_KEY,
            ac.ENSEMBLE_MODELS_KEY
        }
        assert set(ac.MODEL_SUBDIRS.keys()) == expected_keys

    def test_online_catalog_map_keys_match_model_types(self):
        """Test that ONLINE_CATALOG_MAP keys match model type constants."""
        expected_keys = {
            ac.VR_ARCH_MODELS_KEY,
            ac.MDX_NET_MODELS_KEY,
            ac.DEMUCS_MODELS_KEY, 
            ac.ENSEMBLE_MODELS_KEY
        }
        assert set(ac.ONLINE_CATALOG_MAP.keys()) == expected_keys

    def test_demucs_source_lists_consistency(self):
        """Test consistency between Demucs source lists and mappers."""
        # 4-source list should match 4-source mapper keys
        assert set(ac.DEMUCS_4_SOURCE_LIST) == set(ac.DEMUCS_4_SOURCE_MAPPER.keys())
        
        # 2-source list should match 2-source mapper keys  
        assert set(ac.DEMUCS_2_SOURCE_LIST) == set(ac.DEMUCS_2_SOURCE_MAPPER.keys())

    def test_stem_constants_no_duplicates(self):
        """Test that stem constants have no duplicates."""
        all_stems = [
            ac.VOCAL_STEM, ac.INST_STEM, ac.OTHER_STEM,
            ac.BASS_STEM, ac.DRUM_STEM, ac.GUITAR_STEM, ac.PIANO_STEM
        ]
        assert len(all_stems) == len(set(all_stems))

    def test_file_extensions_format(self):
        """Test that file extensions are properly formatted."""
        extensions = [
            ac.ONNX_EXT, ac.CKPT_EXT, ac.PTH_EXT, ac.YAML_EXT,
            ac.WAV_EXT, ac.FLAC_EXT, ac.MP3_EXT, ac.JSON_EXT,
            ac.TH_EXT, ac.GZ_EXT
        ]
        for ext in extensions:
            assert ext.startswith('.')
            assert len(ext) > 1

    def test_url_constants_format(self):
        """Test that URL constants are properly formatted."""
        urls = [
            ac.DOWNLOAD_CHECKS_URL,
            ac.MODEL_REPO_URL_BASE,
            ac.DEMUCS_URL_BASE,
            ac.DEMUCS_CONFIG_URL_BASE
        ]
        for url in urls:
            assert url.startswith('http')
            assert '://' in url 