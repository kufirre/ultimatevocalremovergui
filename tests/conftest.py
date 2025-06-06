"""
Global pytest fixtures and test configuration for UVR PySide6 application.

This module provides shared fixtures for testing PySide6 GUI components,
audio processing, and model management functionality.
"""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setApplicationName("UVR-Test")
    yield app
    # Don't quit here - let pytest-qt handle it


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_audio_file(temp_dir):
    """Create a mock audio file for testing."""
    audio_file = temp_dir / "test_audio.wav"
    audio_file.touch()
    return audio_file


@pytest.fixture
def mock_stereo_audio():
    """Create mock stereo audio data."""
    return np.random.rand(2, 44100).astype(np.float32)


@pytest.fixture
def mock_mono_audio():
    """Create mock mono audio data."""
    return np.random.rand(44100).astype(np.float32)


@pytest.fixture
def mock_model_paths(temp_dir):
    """Create mock model directory structure."""
    models_dir = temp_dir / "models"
    vr_dir = models_dir / "VR_Models"
    mdx_dir = models_dir / "MDX_Net_Models"
    demucs_dir = models_dir / "Demucs_Models"

    for directory in [vr_dir, mdx_dir, demucs_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "models_dir": models_dir,
        "vr_dir": vr_dir,
        "mdx_dir": mdx_dir,
        "demucs_dir": demucs_dir,
    }


@pytest.fixture
def valid_settings_dict(temp_dir, mock_audio_file):
    """Create a valid settings dictionary for testing."""
    return {
        "chosen_process_method": ac.VR_ARCH_TYPE,
        "vr_model": "test_vr_model.pth",
        "mdx_net_model": "test_mdx_model.onnx",
        "demucs_model": "test_demucs_model.yaml",
        "input_paths": [str(mock_audio_file)],
        "output_path": str(temp_dir),
        "save_format": ac.WAV,
        "wav_type_set": "PCM_16",
        "mp3_bit_set": "320k",
        "is_normalization": False,
        "is_gpu_conversion": False,
        "device_set": "Default",
        "is_tta": False,
        "is_post_process": False,
        "is_high_end_process": False,
        "post_process_threshold": 0.2,
        "aggression_setting": 5,
        "window_size": 512,
        "batch_size": 4,
        "crop_size": 256,
        "is_primary_stem_only": False,
        "is_secondary_stem_only": False,
    }


@pytest.fixture
def ensemble_settings_dict(temp_dir, mock_audio_file):
    """Create ensemble settings dictionary for testing."""
    return {
        "chosen_process_method": ac.ENSEMBLE_MODE,
        "ensemble_model": "",  # Empty for live ensemble
        "ensemble_selected_models": ["model1.pth", "model2.onnx"],
        "ensemble_main_stem_pair": "Vocals/Instrumental",
        "ensemble_algorithm": "Average/Average",
        "input_paths": [str(mock_audio_file)],
        "output_path": str(temp_dir),
        "save_format": ac.WAV,
        "wav_type_set": "PCM_16",
        "mp3_bit_set": "320k",
        "is_normalization": False,
    }


@pytest.fixture
def mock_model_data():
    """Create a mock ModelData instance."""
    model_data = Mock(spec=ModelData)
    model_data.model_status = True
    model_data.model_name = "test_model"
    model_data.model_basename = "test_model"
    model_data.process_method = ac.VR_ARCH_TYPE
    model_data.primary_stem = ac.VOCAL_STEM
    model_data.secondary_stem = ac.INST_STEM
    model_data.is_ensemble_mode = False
    model_data.is_ensemble_member = False
    model_data.ensemble_models = []
    model_data.save_format = ac.WAV
    model_data.wav_type_set = "PCM_16"
    model_data.mp3_bit_set = "320k"
    model_data.is_normalization = False
    model_data.is_4_stem_ensemble = False
    # Add missing attributes expected by processing worker
    model_data.audio_file = None
    model_data.export_path = None
    model_data.model_path = None
    model_data.secondary_model_4_stem_instances = []
    model_data.secondary_model_4_stem_scales = []
    model_data.ensemble_type = ac.AVERAGE_ENSEMBLE
    return model_data


@pytest.fixture
def mock_separator_logic():
    """Mock separator logic for different architectures."""
    mock_vr_separator = Mock()
    mock_vr_separator.separate.return_value = {
        ac.VOCAL_STEM: np.random.rand(2, 1000).astype(np.float32),
        ac.INST_STEM: np.random.rand(2, 1000).astype(np.float32),
    }

    mock_mdx_separator = Mock()
    mock_mdx_separator.separate.return_value = {
        ac.VOCAL_STEM: np.random.rand(2, 1000).astype(np.float32),
        ac.INST_STEM: np.random.rand(2, 1000).astype(np.float32),
    }

    mock_demucs_separator = Mock()
    mock_demucs_separator.separate.return_value = {
        ac.VOCAL_STEM: np.random.rand(2, 1000).astype(np.float32),
        ac.INST_STEM: np.random.rand(2, 1000).astype(np.float32),
        ac.BASS_STEM: np.random.rand(2, 1000).astype(np.float32),
        ac.DRUM_STEM: np.random.rand(2, 1000).astype(np.float32),
    }

    # Mock the actual separator classes imported from separate_logic module
    with patch(
        "uvr_pyside6_ui.core.processing_worker.SeperateVRLogic",
        return_value=mock_vr_separator,
    ), patch(
        "uvr_pyside6_ui.core.processing_worker.SeperateMDXLogic",
        return_value=mock_mdx_separator,
    ), patch(
        "uvr_pyside6_ui.core.processing_worker.SeperateMDXCLogic",
        return_value=mock_mdx_separator,
    ), patch(
        "uvr_pyside6_ui.core.processing_worker.SeperateDemucsLogic",
        return_value=mock_demucs_separator,
    ), patch(
        "uvr_pyside6_ui.core.processing_worker.prepare_mix_logic"
    ) as mock_prepare_mix, patch(
        "uvr_pyside6_ui.core.processing_worker.write_audio_logic"
    ) as mock_write_audio, patch(
        "uvr_pyside6_ui.core.processing_worker.clear_gpu_cache_logic"
    ) as mock_clear_gpu:

        # Mock audio loading and writing functions
        mock_prepare_mix.return_value = np.random.rand(2, 44100).astype(np.float32)
        mock_write_audio.return_value = True
        mock_clear_gpu.return_value = None

        yield {
            "vr": Mock(return_value=mock_vr_separator),
            "mdx": Mock(return_value=mock_mdx_separator),
            "demucs": Mock(return_value=mock_demucs_separator),
        }


def assert_audio_array_valid(
    audio_array, expected_shape=None, expected_dtype=np.float32
):
    """Assert that an audio array is valid."""
    assert audio_array is not None, "Audio array should not be None"
    assert isinstance(audio_array, np.ndarray), "Audio should be numpy array"
    assert (
        audio_array.dtype == expected_dtype
    ), f"Expected dtype {expected_dtype}, got {audio_array.dtype}"

    if expected_shape:
        assert (
            audio_array.shape == expected_shape
        ), f"Expected shape {expected_shape}, got {audio_array.shape}"

    # Check for reasonable audio values
    assert not np.isnan(audio_array).any(), "Audio array contains NaN values"
    assert not np.isinf(audio_array).any(), "Audio array contains infinite values"


def create_mock_ensemble_models():
    """Create mock ensemble models for testing."""
    model1 = Mock(spec=ModelData)
    model1.model_status = True
    model1.model_name = "ensemble_model_1"
    model1.model_basename = "ensemble_model_1"
    model1.process_method = ac.VR_ARCH_TYPE
    model1.primary_stem = ac.VOCAL_STEM
    model1.secondary_stem = ac.INST_STEM

    model2 = Mock(spec=ModelData)
    model2.model_status = True
    model2.model_name = "ensemble_model_2"
    model2.model_basename = "ensemble_model_2"
    model2.process_method = ac.MDX_ARCH_TYPE
    model2.primary_stem = ac.VOCAL_STEM
    model2.secondary_stem = ac.INST_STEM

    return [model1, model2]


@pytest.fixture
def mock_uvr_core_adapter():
    """Mock UVRCoreAdapter for testing."""
    adapter = Mock(spec=UVRCoreAdapter)
    adapter.get_available_models.return_value = [
        "model1.pth",
        "model2.onnx",
        "model3.yaml",
    ]
    adapter.get_model_info.return_value = {
        "primary_stem": ac.VOCAL_STEM,
        "secondary_stem": ac.INST_STEM,
        "model_type": ac.VR_ARCH_TYPE,
    }
    return adapter


# Test configuration helpers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "ui: UI/GUI tests")
    config.addinivalue_line("markers", "ensemble: Ensemble processing tests")
    config.addinivalue_line("markers", "audio: Audio processing tests")
    config.addinivalue_line("markers", "edge_case: Edge cases and error conditions")
    config.addinivalue_line("markers", "slow: Tests that take more than 5 seconds")
    config.addinivalue_line("markers", "mock_audio: Tests using mocked audio")
    config.addinivalue_line("markers", "model: Model-related tests")
    config.addinivalue_line("markers", "worker: Processing worker tests")
    config.addinivalue_line("markers", "presenter: Presenter layer tests")
