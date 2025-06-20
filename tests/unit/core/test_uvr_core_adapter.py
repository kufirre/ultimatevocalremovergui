"""
Unit tests for uvr_core_adapter module.

Tests cover the UVRCoreAdapter class including model management,
downloads, processing coordination, and Qt signal handling.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QThread
from PySide6.QtTest import QSignalSpy

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter


@pytest.mark.unit
@pytest.mark.adapter
class TestUVRCoreAdapter:
    """Test cases for UVRCoreAdapter class."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.models_dir = self.temp_dir / "models"
        self.models_dir.mkdir()

    def test_uvr_core_adapter_initialization(self, qapp):
        """Test UVRCoreAdapter initialization."""
        adapter = UVRCoreAdapter()

        # Check signals exist
        assert hasattr(adapter, "progress_updated")
        assert hasattr(adapter, "processing_finished")
        assert hasattr(adapter, "download_progress")
        assert hasattr(adapter, "download_finished")
        assert hasattr(adapter, "model_download_completed")

        # Check initial state
        assert adapter.processing_thread is None
        assert adapter._online_catalog_data_cache is None
        assert adapter.download_manager is not None

    def test_get_project_models_dir_success(self):
        """Test successful models directory detection."""
        adapter = UVRCoreAdapter()

        with patch.object(Path, "resolve") as mock_resolve:
            with patch.object(Path, "is_dir", return_value=True) as mock_is_dir:
                # Mock the file path to simulate proper directory structure
                mock_file_path = Mock()
                mock_file_path.parents = [Mock(), Mock(), Mock(), self.temp_dir]
                mock_resolve.return_value = mock_file_path

                result = adapter._get_project_models_dir()

                assert result == self.temp_dir / "models"

    def test_get_project_models_dir_fallback_cwd(self):
        """Test fallback to current working directory."""
        adapter = UVRCoreAdapter()

        with patch.object(Path, "resolve") as mock_resolve:
            with patch.object(Path, "cwd", return_value=self.temp_dir):
                # Mock the file path to simulate IndexError (empty parents)
                mock_file_path = Mock()
                mock_file_path.parents = []  # Empty to trigger IndexError
                mock_resolve.return_value = mock_file_path

                # Mock is_dir to return True only for the fallback models directory
                temp_dir_str = str(self.temp_dir)  # Capture in local scope

                def mock_is_dir(path_instance):
                    path_str = str(path_instance)
                    return path_str.endswith("models") and path_str.startswith(
                        temp_dir_str
                    )

                with patch.object(Path, "is_dir", mock_is_dir):
                    result = adapter._get_project_models_dir()

                    assert result == self.temp_dir / "models"

    def test_get_project_models_dir_none_when_not_found(self):
        """Test returning None when models directory not found."""
        adapter = UVRCoreAdapter()

        with patch.object(Path, "resolve") as mock_resolve:
            with patch.object(Path, "is_dir", return_value=False):
                with patch.object(Path, "cwd", return_value=self.temp_dir):
                    mock_file_path = Mock()
                    mock_file_path.parents = []
                    mock_resolve.return_value = mock_file_path

                    result = adapter._get_project_models_dir()

                    assert result is None

    @patch("uvr_pyside6_ui.core.uvr_core_adapter.fetch_online_model_catalog")
    def test_get_online_catalog_success(self, mock_fetch):
        """Test successful online catalog retrieval."""
        mock_catalog = {ac.ONLINE_VR_DOWNLOAD_LIST_KEY: {"model1": "url1"}}
        mock_fetch.return_value = mock_catalog

        adapter = UVRCoreAdapter()

        result = adapter.get_online_catalog()

        assert result == mock_catalog
        assert adapter._online_catalog_data_cache == mock_catalog
        mock_fetch.assert_called_once()

    @patch("uvr_pyside6_ui.core.uvr_core_adapter.fetch_online_model_catalog")
    def test_get_online_catalog_cached(self, mock_fetch):
        """Test that cached catalog is returned without fetching."""
        cached_catalog = {"cached": "data"}
        mock_fetch.return_value = {"fresh": "data"}

        adapter = UVRCoreAdapter()
        adapter._online_catalog_data_cache = cached_catalog

        result = adapter.get_online_catalog()

        assert result == cached_catalog
        mock_fetch.assert_not_called()

    @patch("uvr_pyside6_ui.core.uvr_core_adapter.fetch_online_model_catalog")
    def test_get_online_catalog_fallback(self, mock_fetch):
        """Test fallback catalog when fetch returns None."""
        mock_fetch.return_value = None

        adapter = UVRCoreAdapter()

        result = adapter.get_online_catalog()

        assert result == ac.FALLBACK_ONLINE_CATALOG

    def test_construct_full_url_already_full(self):
        """Test URL construction when URL is already complete."""
        adapter = UVRCoreAdapter()

        full_url = "https://example.com/model.pth"
        result = adapter._construct_full_url(full_url, ac.VR_ARCH_MODELS_KEY)

        assert result == full_url

    def test_construct_full_url_relative_path(self):
        """Test URL construction with relative path."""
        adapter = UVRCoreAdapter()

        relative_path = "models/test_model.pth"
        result = adapter._construct_full_url(relative_path, ac.VR_ARCH_MODELS_KEY)

        expected = f"{ac.MODEL_REPO_URL_BASE.rstrip('/')}/{relative_path}"
        assert result == expected

    def test_construct_full_url_demucs_config(self):
        """Test URL construction for Demucs config files."""
        adapter = UVRCoreAdapter()

        config_path = "config.yaml"
        result = adapter._construct_full_url(
            config_path, ac.DEMUCS_MODELS_KEY, is_config=True
        )

        expected = f"{ac.DEMUCS_CONFIG_URL_BASE.rstrip('/')}/{config_path}"
        assert result == expected

    def test_get_primary_filename_from_download_info_string(self):
        """Test filename extraction from string download info."""
        adapter = UVRCoreAdapter()

        download_info = "path/to/model.pth"
        result = adapter._get_primary_filename_from_download_info(download_info)

        assert result == "model.pth"

    def test_get_primary_filename_from_download_info_dict_yaml(self):
        """Test filename extraction from dict with YAML file."""
        adapter = UVRCoreAdapter()

        download_info = {"config.yaml": "url1", "model.pth": "url2"}
        result = adapter._get_primary_filename_from_download_info(download_info)

        assert result == "config.yaml"

    def test_get_primary_filename_from_download_info_dict_extensions(self):
        """Test filename extraction from dict with model extensions."""
        adapter = UVRCoreAdapter()

        download_info = {"readme.txt": "url1", "model.pth": "url2"}
        result = adapter._get_primary_filename_from_download_info(download_info)

        assert result == "model.pth"

    def test_get_primary_filename_from_download_info_empty(self):
        """Test filename extraction when no valid files found."""
        adapter = UVRCoreAdapter()

        download_info = {"invalid": "data"}
        result = adapter._get_primary_filename_from_download_info(download_info)

        assert result == ""

    def test_get_locally_installed_primary_model_filenames_vr(self):
        """Test getting locally installed VR model filenames."""
        adapter = UVRCoreAdapter()

        # Create mock VR models directory
        vr_models_dir = self.models_dir / "VR_Models"
        vr_models_dir.mkdir()
        (vr_models_dir / "model1.pth").touch()
        (vr_models_dir / "model2.pth").touch()
        (vr_models_dir / "excluded.txt").touch()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter._get_locally_installed_primary_model_filenames(
                ac.VR_ARCH_MODELS_KEY
            )

        assert "model1.pth" in result
        assert "model2.pth" in result
        assert "excluded.txt" not in result

    def test_get_locally_installed_primary_model_filenames_mdx(self):
        """Test getting locally installed MDX model filenames."""
        adapter = UVRCoreAdapter()

        # Create mock MDX models directory
        mdx_models_dir = self.models_dir / "MDX_Net_Models"
        mdx_models_dir.mkdir()
        (mdx_models_dir / "model1.onnx").touch()
        (mdx_models_dir / "model2.ckpt").touch()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter._get_locally_installed_primary_model_filenames(
                ac.MDX_NET_MODELS_KEY
            )

        assert "model1.onnx" in result
        assert "model2.ckpt" in result

    def test_get_locally_installed_primary_model_filenames_demucs(self):
        """Test getting locally installed Demucs model filenames."""
        adapter = UVRCoreAdapter()

        # Create mock Demucs models directory structure
        demucs_models_dir = self.models_dir / "Demucs_Models"
        demucs_models_dir.mkdir()
        (demucs_models_dir / "legacy_model.th").touch()

        v3_v4_dir = demucs_models_dir / "v3_v4_repo"
        v3_v4_dir.mkdir()
        (v3_v4_dir / "newer_model.yaml").touch()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter._get_locally_installed_primary_model_filenames(
                ac.DEMUCS_MODELS_KEY
            )

        assert "legacy_model.th" in result
        assert "newer_model.yaml" in result

    def test_get_locally_installed_primary_model_filenames_no_models_dir(self):
        """Test behavior when models directory doesn't exist."""
        adapter = UVRCoreAdapter()

        with patch.object(adapter, "_get_project_models_dir", return_value=None):
            result = adapter._get_locally_installed_primary_model_filenames(
                ac.VR_ARCH_MODELS_KEY
            )

        assert result == set()

    def test_get_downloadable_models_for_type_success(self):
        """Test getting downloadable models for a specific type."""
        adapter = UVRCoreAdapter()

        mock_catalog = {
            ac.ONLINE_VR_DOWNLOAD_LIST_KEY: {
                "Available Model": "model.pth",
                "Installed Model": "installed.pth",
            }
        }

        with patch.object(adapter, "get_online_catalog", return_value=mock_catalog):
            with patch.object(
                adapter,
                "_get_locally_installed_primary_model_filenames",
                return_value={"installed.pth"},
            ):
                with patch.object(
                    adapter, "_get_primary_filename_from_download_info"
                ) as mock_get_filename:
                    # Mock the filename extraction to return the expected filenames
                    mock_get_filename.side_effect = lambda x: (
                        x if isinstance(x, str) else None
                    )

                    result = adapter.get_downloadable_models_for_type(
                        ac.VR_ARCH_MODELS_KEY
                    )

        assert "Available Model" in result
        assert "Installed Model" not in result

    def test_get_downloadable_models_for_type_no_catalog(self):
        """Test behavior when online catalog is empty."""
        adapter = UVRCoreAdapter()

        with patch.object(adapter, "get_online_catalog", return_value={}):
            result = adapter.get_downloadable_models_for_type(ac.VR_ARCH_MODELS_KEY)

        assert result == {}

    def test_on_download_finished_success(self):
        """Test download finished signal handling."""
        adapter = UVRCoreAdapter()

        download_finished_spy = QSignalSpy(adapter.download_finished)
        download_completed_spy = QSignalSpy(adapter.model_download_completed)

        adapter._on_download_finished(
            success=True,
            model_path="/path/VR_Models/test_model.pth",
            config_path="",
            message="Success",
            model_type=ac.VR_ARCH_MODELS_KEY,
        )

        # Check download_finished signal
        assert download_finished_spy.count() == 1
        signal_args = download_finished_spy.at(0)
        assert signal_args[0] == ac.VR_ARCH_MODELS_KEY  # model_type_ui_name
        assert signal_args[1] == "test_model"  # model_display_name
        assert signal_args[2] is True  # success
        assert signal_args[3] == "Success"  # message

        # Check model_download_completed signal
        assert download_completed_spy.count() == 1
        assert download_completed_spy.at(0)[0] == ac.VR_ARCH_MODELS_KEY

    def test_on_download_finished_failure(self):
        """Test download finished signal handling for failure."""
        adapter = UVRCoreAdapter()

        download_finished_spy = QSignalSpy(adapter.download_finished)
        download_completed_spy = QSignalSpy(adapter.model_download_completed)

        adapter._on_download_finished(
            success=False,
            model_path="",
            config_path="",
            message="Download failed",
            model_type=ac.VR_ARCH_MODELS_KEY,
        )

        # Check download_finished signal
        assert download_finished_spy.count() == 1
        signal_args = download_finished_spy.at(0)
        assert signal_args[2] is False  # success

        # Check model_download_completed signal not emitted
        assert download_completed_spy.count() == 0

    def test_get_model_info_vr_model(self):
        """Test getting model info for VR model."""
        adapter = UVRCoreAdapter()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter.get_model_info("test_vr_model", ac.VR_ARCH_MODELS_KEY)

        assert result is not None
        assert result["model_name"] == "test_vr_model"
        assert result["model_type"] == ac.VR_ARCH_MODELS_KEY
        assert result["primary_stem"] == ac.VOCAL_STEM

    def test_get_model_info_mdx_model(self):
        """Test getting model info for MDX model."""
        adapter = UVRCoreAdapter()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter.get_model_info("test_mdx_model", ac.MDX_NET_MODELS_KEY)

        assert result is not None
        assert result["mdx_model_stems"] == [ac.VOCAL_STEM, ac.INST_STEM]
        assert result["mdx_stem_count"] == 2
        assert result["is_4_stem"] is False

    def test_get_model_info_mdx_4stem_model(self):
        """Test getting model info for 4-stem MDX model."""
        adapter = UVRCoreAdapter()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter.get_model_info("test_4stem_model", ac.MDX_NET_MODELS_KEY)

        assert result is not None
        assert result["is_4_stem"] is True
        assert result["mdx_stem_count"] == 4
        assert len(result["mdx_model_stems"]) == 4

    def test_get_model_info_demucs_model(self):
        """Test getting model info for Demucs model."""
        adapter = UVRCoreAdapter()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter.get_model_info("test_demucs_model", ac.DEMUCS_MODELS_KEY)

        assert result is not None
        assert result["demucs_stems"] == [
            ac.VOCAL_STEM,
            ac.DRUM_STEM,
            ac.BASS_STEM,
            ac.OTHER_STEM,
        ]
        assert result["is_4_stem"] is True

    def test_get_model_info_demucs_2stem_model(self):
        """Test getting model info for 2-stem Demucs model."""
        adapter = UVRCoreAdapter()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter.get_model_info(
                "test_2stem_vocal_model", ac.DEMUCS_MODELS_KEY
            )

        assert result is not None
        assert result["demucs_stems"] == [ac.VOCAL_STEM, ac.INST_STEM]
        assert result["is_4_stem"] is False

    def test_get_model_info_no_models_dir(self):
        """Test get_model_info when models directory not found."""
        adapter = UVRCoreAdapter()

        with patch.object(adapter, "_get_project_models_dir", return_value=None):
            result = adapter.get_model_info("test_model", ac.VR_ARCH_MODELS_KEY)

        assert result is None

    def test_get_model_info_exception_handling(self):
        """Test exception handling in get_model_info."""
        adapter = UVRCoreAdapter()

        with patch.object(
            adapter, "_get_project_models_dir", side_effect=Exception("Test error")
        ):
            with patch("uvr_pyside6_ui.core.uvr_core_adapter.logger") as mock_logger:
                result = adapter.get_model_info("test_model", ac.VR_ARCH_MODELS_KEY)

        assert result is None
        mock_logger.error.assert_called_once()

    def test_download_model_string_download_info(self):
        """Test downloading model with string download info."""
        adapter = UVRCoreAdapter()

        # Mock the download manager instead of patching it as a class attribute
        mock_download_manager = Mock()
        adapter.download_manager = mock_download_manager

        progress_spy = QSignalSpy(adapter.download_progress)

        adapter.download_model(ac.VR_ARCH_MODELS_KEY, "Test Model", "model.pth")

        # Check initial progress signal
        assert progress_spy.count() == 1
        assert progress_spy.at(0) == ["Test Model", 0]

        # Check download manager was called
        mock_download_manager.start_download.assert_called_once()

    def test_download_model_dict_download_info(self):
        """Test downloading model with dict download info."""
        adapter = UVRCoreAdapter()

        # Mock the download manager instead of patching it as a class attribute
        mock_download_manager = Mock()
        adapter.download_manager = mock_download_manager

        download_info = {"model_url": "model.pth", "config_url": "config.yaml"}

        adapter.download_model(ac.DEMUCS_MODELS_KEY, "Test Model", download_info)

        mock_download_manager.start_download.assert_called_once()
        call_args = mock_download_manager.start_download.call_args
        assert call_args.kwargs["config_url"] is not None

    def test_download_model_no_url_error(self):
        """Test download model error when no URL can be determined."""
        adapter = UVRCoreAdapter()

        download_finished_spy = QSignalSpy(adapter.download_finished)

        adapter.download_model(ac.VR_ARCH_MODELS_KEY, "Test Model", {})

        # Check error signal
        assert download_finished_spy.count() == 1
        signal_args = download_finished_spy.at(0)
        assert signal_args[2] is False  # success
        assert "Could not determine download URL" in signal_args[3]

    def test_scan_path_for_identifiers_success(self):
        """Test scanning path for model identifiers."""
        adapter = UVRCoreAdapter()

        # Create test directory with models
        test_dir = self.temp_dir / "test_scan"
        test_dir.mkdir()
        (test_dir / "model1.pth").touch()
        (test_dir / "model2.pth").touch()
        (test_dir / "excluded.txt").touch()

        result = adapter._scan_path_for_identifiers(test_dir, [".pth"], recursive=False)

        assert "model1" in result
        assert "model2" in result
        assert len(result) == 2

    def test_scan_path_for_identifiers_mdx_ckpt_special_case(self):
        """Test scanning with MDX CKPT special case."""
        adapter = UVRCoreAdapter()

        test_dir = self.temp_dir / "test_scan"
        test_dir.mkdir()
        (test_dir / "model.ckpt").touch()

        result = adapter._scan_path_for_identifiers(
            test_dir, [".ckpt"], is_mdx_ckpt_special_case=True
        )

        assert "model.ckpt" in result  # Should include extension for CKPT

    def test_scan_path_for_identifiers_recursive(self):
        """Test recursive scanning."""
        adapter = UVRCoreAdapter()

        test_dir = self.temp_dir / "test_scan"
        test_dir.mkdir()
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "deep_model.pth").touch()

        result = adapter._scan_path_for_identifiers(test_dir, [".pth"], recursive=True)

        assert "deep_model" in result

    def test_scan_path_for_identifiers_invalid_path(self):
        """Test scanning invalid path."""
        adapter = UVRCoreAdapter()

        result = adapter._scan_path_for_identifiers(Path("/nonexistent"), [".pth"])

        assert result == []

    def test_load_name_mapper_success(self):
        """Test loading name mapper file successfully."""
        adapter = UVRCoreAdapter()

        test_dir = self.temp_dir / "test_models"
        test_dir.mkdir()
        mapper_dir = test_dir / "model_data"
        mapper_dir.mkdir()
        mapper_file = mapper_dir / "model_name_mapper.json"

        mapper_data = {"model_file.pth": "Display Name"}
        mapper_file.write_text(json.dumps(mapper_data))

        result = adapter._load_name_mapper(test_dir)

        assert result == mapper_data

    def test_load_name_mapper_file_not_found(self):
        """Test loading name mapper when file doesn't exist."""
        adapter = UVRCoreAdapter()

        with patch("uvr_pyside6_ui.core.uvr_core_adapter.logger") as mock_logger:
            result = adapter._load_name_mapper(self.temp_dir)

        assert result == {}
        mock_logger.warning.assert_called_once()

    def test_load_name_mapper_json_error(self):
        """Test loading name mapper with invalid JSON."""
        adapter = UVRCoreAdapter()

        test_dir = self.temp_dir / "test_models"
        test_dir.mkdir()
        mapper_dir = test_dir / "model_data"
        mapper_dir.mkdir()
        mapper_file = mapper_dir / "model_name_mapper.json"

        mapper_file.write_text("invalid json {")

        with patch("uvr_pyside6_ui.core.uvr_core_adapter.logger") as mock_logger:
            result = adapter._load_name_mapper(test_dir)

        assert result == {}
        mock_logger.error.assert_called_once()

    def test_get_display_name_from_mapper_success(self):
        """Test getting display name from mapper successfully."""
        adapter = UVRCoreAdapter()

        name_mapper = {"model_file.pth": "Beautiful Display Name"}

        result = adapter._get_display_name_from_mapper("model_file", name_mapper)

        assert result == ("Beautiful Display Name", True)

    def test_get_display_name_from_mapper_no_match(self):
        """Test getting display name when no mapping found."""
        adapter = UVRCoreAdapter()

        name_mapper = {"other_model.pth": "Other Name"}

        result = adapter._get_display_name_from_mapper("target_model", name_mapper)

        assert result == ("target_model", False)

    def test_get_display_name_from_mapper_empty_mapper(self):
        """Test getting display name with empty mapper."""
        adapter = UVRCoreAdapter()

        result = adapter._get_display_name_from_mapper("model", {})

        assert result == ("model", False)

    def test_get_available_methods(self):
        """Test getting available processing methods."""
        adapter = UVRCoreAdapter()

        result = adapter.get_available_methods()

        expected = [
            ac.VR_ARCH_MODELS_KEY,
            ac.MDX_NET_MODELS_KEY,
            ac.DEMUCS_MODELS_KEY,
            ac.ENSEMBLE_MODELS_KEY,
        ]
        assert result == expected

    def test_get_available_models_vr(self):
        """Test getting available VR models."""
        adapter = UVRCoreAdapter()

        # Mock the scan_models_directory function directly
        with patch(
            "uvr_pyside6_ui.core.model_utils.scan_models_directory"
        ) as mock_scan:
            mock_scan.return_value = ["Beautiful Model 1", "Amazing Model 2"]

            result = adapter.get_available_models(ac.VR_ARCH_MODELS_KEY)

        assert "Beautiful Model 1" in result
        assert "Amazing Model 2" in result

    def test_get_available_models_no_models_dir(self):
        """Test get_available_models when models directory not found."""
        adapter = UVRCoreAdapter()

        # Mock scan_models_directory to return empty list when no models dir
        with patch(
            "uvr_pyside6_ui.core.model_utils.scan_models_directory"
        ) as mock_scan:
            mock_scan.return_value = []
            result = adapter.get_available_models(ac.VR_ARCH_MODELS_KEY)

        assert result == []

    def test_get_available_models_unknown_method(self):
        """Test get_available_models with unknown method."""
        adapter = UVRCoreAdapter()

        with patch.object(
            adapter, "_get_project_models_dir", return_value=self.models_dir
        ):
            result = adapter.get_available_models("UNKNOWN_METHOD")

        assert result == []

    @patch("uvr_pyside6_ui.core.uvr_core_adapter.ProcessingThread")
    def test_start_processing_success(self, mock_processing_thread_class):
        """Test starting processing successfully."""
        mock_thread = Mock(spec=QThread)

        # Add the required signal attributes
        mock_thread.progress_updated = Mock()
        mock_thread.processing_finished = Mock()
        mock_thread.finished = Mock()

        # Add connect method to signals
        mock_thread.progress_updated.connect = Mock()
        mock_thread.processing_finished.connect = Mock()
        mock_thread.finished.connect = Mock()

        mock_processing_thread_class.return_value = mock_thread

        adapter = UVRCoreAdapter()
        settings_dict = {"test": "settings"}

        adapter.start_processing(settings_dict)

        assert adapter.processing_thread == mock_thread
        mock_processing_thread_class.assert_called_once_with(settings_dict)
        mock_thread.start.assert_called_once()

    @patch("uvr_pyside6_ui.core.uvr_core_adapter.ProcessingThread")
    def test_start_processing_already_running(self, mock_processing_thread_class):
        """Test starting processing when already running."""
        mock_thread = Mock(spec=QThread)
        mock_thread.isRunning.return_value = True

        adapter = UVRCoreAdapter()
        adapter.processing_thread = mock_thread

        adapter.start_processing({"test": "settings"})

        # Should not create new thread
        mock_processing_thread_class.assert_not_called()

    def test_stop_processing_running(self):
        """Test stopping running processing."""
        adapter = UVRCoreAdapter()

        mock_thread = Mock(spec=QThread)
        mock_thread.isRunning.return_value = True
        # Add the stop_processing method to the mock
        mock_thread.stop_processing = Mock()
        adapter.processing_thread = mock_thread

        adapter.stop_processing()

        mock_thread.stop_processing.assert_called_once()

    def test_stop_processing_not_running(self):
        """Test stopping when not running."""
        adapter = UVRCoreAdapter()

        # Should not raise error
        adapter.stop_processing()

    def test_on_processing_thread_finished(self):
        """Test processing thread finished cleanup."""
        adapter = UVRCoreAdapter()

        mock_thread = Mock(spec=QThread)
        adapter.processing_thread = mock_thread

        adapter._on_processing_thread_finished()

        assert adapter.processing_thread is None


@pytest.mark.integration
@pytest.mark.adapter
class TestUVRCoreAdapterIntegration:
    """Integration tests for UVRCoreAdapter."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.models_dir = self.temp_dir / "models"
        self.models_dir.mkdir()

    def test_full_model_scanning_workflow(self):
        """Test complete model scanning workflow."""
        adapter = UVRCoreAdapter()

        # Create complete directory structure
        vr_dir = self.models_dir / "VR_Models"
        vr_dir.mkdir()
        (vr_dir / "test_model.pth").touch()

        mapper_dir = vr_dir / "model_data"
        mapper_dir.mkdir()
        mapper_file = mapper_dir / "model_name_mapper.json"
        mapper_data = {"test_model.pth": "Test VR Model"}
        mapper_file.write_text(json.dumps(mapper_data))

        # Mock scan_models_directory to return our test model
        with patch(
            "uvr_pyside6_ui.core.model_utils.scan_models_directory"
        ) as mock_scan:
            mock_scan.return_value = ["Test VR Model"]

            # Get available methods
            methods = adapter.get_available_methods()
            assert ac.VR_ARCH_MODELS_KEY in methods

            # Get available models
            models = adapter.get_available_models(ac.VR_ARCH_MODELS_KEY)
            assert "Test VR Model" in models

            # Get model info (this needs to be mocked too since it depends on real model files)
            with patch.object(adapter, "get_model_info") as mock_get_info:
                mock_get_info.return_value = {"primary_stem": ac.VOCAL_STEM}
                info = adapter.get_model_info("Test VR Model", ac.VR_ARCH_MODELS_KEY)
                assert info is not None
                assert info["primary_stem"] == ac.VOCAL_STEM

    @patch("uvr_pyside6_ui.core.uvr_core_adapter.fetch_online_model_catalog")
    def test_download_workflow_integration(self, mock_fetch):
        """Test complete download workflow integration."""
        mock_catalog = {
            ac.ONLINE_VR_DOWNLOAD_LIST_KEY: {"Test Online Model": "test_model.pth"}
        }
        mock_fetch.return_value = mock_catalog

        adapter = UVRCoreAdapter()

        # Setup empty local models to show downloadable
        with patch.object(
            adapter,
            "_get_locally_installed_primary_model_filenames",
            return_value=set(),
        ):
            # Get online catalog
            catalog = adapter.get_online_catalog()
            assert catalog == mock_catalog

            # Get downloadable models
            downloadable = adapter.get_downloadable_models_for_type(
                ac.VR_ARCH_MODELS_KEY
            )
            assert "Test Online Model" in downloadable

            # Start download (mocked)
            with patch.object(adapter.download_manager, "start_download") as mock_start:
                adapter.download_model(
                    ac.VR_ARCH_MODELS_KEY, "Test Online Model", "test_model.pth"
                )
                mock_start.assert_called_once()

    def test_signal_connections_integration(self):
        """Test that all signal connections work properly."""
        adapter = UVRCoreAdapter()

        # Test download manager signal connections
        progress_spy = QSignalSpy(adapter.download_progress)
        finished_spy = QSignalSpy(adapter.download_finished)

        # Simulate download manager signals
        adapter.download_manager.download_progress.emit("test_model.pth", 50)
        adapter.download_manager.download_finished.emit(
            True, "/path/to/model.pth", "", "Success", ac.VR_ARCH_MODELS_KEY
        )

        # Check signals were forwarded
        assert progress_spy.count() == 1
        assert finished_spy.count() == 1
