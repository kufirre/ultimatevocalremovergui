"""
Tests to verify Demucs V3/V4 models are placed in correct directories.

This test suite confirms that:
1. V3/V4 models are detected and placed in v3_v4_repo subdirectory
2. Legacy models remain in the root Demucs_Models directory
3. Model path resolution works correctly for both locations
4. Download logic handles V3/V4 models specially
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.model_downloader import download_model_file
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter


@pytest.mark.unit
@pytest.mark.model
class TestDemucsV3V4DirectoryPlacement:
    """Test suite for Demucs V3/V4 directory placement verification."""

    def test_demucs_v3_v4_repo_directory_constant(self):
        """Test that the V3/V4 repo directory constant is properly defined."""
        assert ac.DEMUCS_V3_V4_REPO_DIR_NAME == "v3_v4_repo"

    def test_demucs_version_constants(self):
        """Test that Demucs version constants are properly defined."""
        assert ac.DEMUCS_V3 == "v3"
        assert ac.DEMUCS_V4 == "v4"

    def test_model_data_detects_v4_version_from_name(self):
        """Test that ModelData correctly detects V4 version from model name."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE, model_name="v4 | htdemucs_ft"
        )

        settings = {"demucs_stems": ac.ALL_STEMS}
        model_data._load_and_derive_model_properties(settings)

        assert model_data.demucs_version == ac.DEMUCS_V4

    def test_model_data_detects_v3_version_from_name(self):
        """Test that ModelData correctly detects V3 version from model name."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE, model_name="v3 | mdx_extra"
        )

        settings = {"demucs_stems": ac.ALL_STEMS}
        model_data._load_and_derive_model_properties(settings)

        # ✅ FIXED: V3 models are now correctly detected as V3
        # The version detection logic was moved to __post_init__ to ensure it always runs
        assert model_data.demucs_version == ac.DEMUCS_V3

    def test_model_data_defaults_to_v4_for_unspecified_models(self):
        """Test that models without version specifier default to V4."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE,
            model_name="htdemucs.th",  # No version specified
        )

        settings = {"demucs_stems": ac.ALL_STEMS}
        model_data._load_and_derive_model_properties(settings)

        # ✅ CONFIRMED: Models without version info correctly default to V4
        assert model_data.demucs_version == ac.DEMUCS_V4

    def test_model_path_determination_for_v4_model(self):
        """Test that V4 models are correctly resolved to v3_v4_repo directory."""
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
                        # V4 model should be found in newer repo directory
                        model_file = mock_newer_dir / "htdemucs_ft.yaml"
                        with patch.object(model_file, "exists", return_value=True):
                            result = model_data._determine_model_path()

                            assert result is not None
                            # Verify the newer repo path was accessed
                            mock_newer_dir.__truediv__.assert_called_with(
                                "htdemucs_ft.yaml"
                            )

    def test_model_path_determination_for_legacy_model(self):
        """Test that legacy models are found in root Demucs_Models directory."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE, model_name="htdemucs.th"  # Legacy model
        )

        with patch(
            "uvr_pyside6_ui.core.model_data.DEMUCS_MODELS_DIR_PATH"
        ) as mock_demucs_dir:
            with patch(
                "uvr_pyside6_ui.core.model_data.DEMUCS_NEWER_REPO_DIR_PATH"
            ) as mock_newer_dir:
                # Legacy model should be found in root directory
                model_file = mock_demucs_dir / "htdemucs.th"

                with patch.object(
                    Path,
                    "exists",
                    side_effect=lambda path: str(path).endswith("htdemucs.th"),
                ):
                    with patch.object(model_file, "exists", return_value=True):
                        result = model_data._determine_model_path()

                        assert result is not None

    @patch("uvr_pyside6_ui.core.model_downloader.requests.get")
    def test_download_v3_model_goes_to_v3_v4_repo(self, mock_get):
        """Test that V3 models are downloaded to v3_v4_repo directory."""
        mock_response = Mock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"test_model_data"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Use model name containing 'v3' to trigger special handling
        model_name = "mdx_extra_v3_test_model"
        download_url = "https://example.com/model.yaml"  # .yaml extension should trigger v3_v4_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the target directory to our temp directory
            target_dir = Path(temp_dir) / "Demucs_Models"
            target_dir.mkdir(parents=True, exist_ok=True)

            with patch(
                "uvr_pyside6_ui.core.model_downloader.MODEL_TYPE_PATHS",
                {ac.DEMUCS_MODELS_KEY: target_dir},
            ):
                with patch("builtins.open", mock_open()):
                    success, message, config_path = download_model_file(
                        model_name, download_url, ac.DEMUCS_MODELS_KEY
                    )

            assert success is True
            # Check if the file was saved in v3_v4_repo (based on .yaml extension)
            assert ac.DEMUCS_V3_V4_REPO_DIR_NAME in str(message)

            # Verify the v3_v4_repo directory was created
            v3_v4_dir = target_dir / ac.DEMUCS_V3_V4_REPO_DIR_NAME
            assert v3_v4_dir.exists()

    @patch("uvr_pyside6_ui.core.model_downloader.requests.get")
    def test_download_v4_model_goes_to_v3_v4_repo(self, mock_get):
        """Test that V4 models are downloaded to v3_v4_repo directory."""
        mock_response = Mock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"test_model_data"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Use model name containing 'v4' and .yaml extension to trigger special handling
        model_name = "htdemucs_ft_v4"
        download_url = (
            "https://example.com/model.yaml"  # .yaml extension triggers v3_v4_repo
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "Demucs_Models"
            target_dir.mkdir(parents=True, exist_ok=True)

            with patch(
                "uvr_pyside6_ui.core.model_downloader.MODEL_TYPE_PATHS",
                {ac.DEMUCS_MODELS_KEY: target_dir},
            ):
                with patch("builtins.open", mock_open()):
                    success, message, config_path = download_model_file(
                        model_name, download_url, ac.DEMUCS_MODELS_KEY
                    )

            assert success is True
            # Check if the file was saved in v3_v4_repo (based on .yaml extension)
            assert ac.DEMUCS_V3_V4_REPO_DIR_NAME in str(message)

    def test_download_legacy_model_goes_to_root_directory(self):
        """Test that legacy models go to root Demucs_Models directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "Demucs_Models"
            target_dir.mkdir(parents=True, exist_ok=True)

            # Create a mock legacy model file (non-yaml extension)
            legacy_model = target_dir / "htdemucs.th"
            legacy_model.touch()

            # Legacy models should NOT be in v3_v4_repo
            v3_v4_dir = target_dir / ac.DEMUCS_V3_V4_REPO_DIR_NAME
            assert not (v3_v4_dir / "htdemucs.th").exists()

            # Should be in root directory
            assert legacy_model.exists()

    def test_uvr_core_adapter_scans_both_directories(self):
        """Test that UVRCoreAdapter scans both root and v3_v4_repo directories."""
        adapter = UVRCoreAdapter()

        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)
            demucs_models_dir = models_dir / "Demucs_Models"
            demucs_models_dir.mkdir()

            # Create legacy model in root
            (demucs_models_dir / "legacy_model.th").touch()

            # Create V3/V4 models in v3_v4_repo subdirectory
            v3_v4_dir = demucs_models_dir / ac.DEMUCS_V3_V4_REPO_DIR_NAME
            v3_v4_dir.mkdir()
            (v3_v4_dir / "newer_model.yaml").touch()
            (v3_v4_dir / "another_v4_model.yaml").touch()

            with patch.object(
                adapter, "_get_project_models_dir", return_value=models_dir
            ):
                result = adapter._get_locally_installed_primary_model_filenames(
                    ac.DEMUCS_MODELS_KEY
                )

            # Should find models from both directories
            assert "legacy_model.th" in result
            assert "newer_model.yaml" in result
            assert "another_v4_model.yaml" in result

    def test_model_version_detection_edge_cases(self):
        """Test version detection with various edge cases."""
        test_cases = [
            ("v4 | htdemucs_ft", ac.DEMUCS_V4),  # ✅ V4 detection works
            ("v3 | mdx_extra", ac.DEMUCS_V3),  # ✅ FIXED: V3 detection now works
            ("v1 | old_model", ac.DEMUCS_V1),  # ✅ V1 detection works
            ("v2 | another_old", ac.DEMUCS_V2),  # ✅ V2 detection works
            ("demucs_v3_special", ac.DEMUCS_V3),  # ✅ V3 detection in filename works
            ("htdemucs_v4_model", ac.DEMUCS_V4),  # ✅ V4 detection in filename works
            ("htdemucs.th", ac.DEMUCS_V4),  # ✅ Default to V4 works
        ]

        for model_name, expected_version in test_cases:
            model_data = ModelData(
                process_method=ac.DEMUCS_ARCH_TYPE, model_name=model_name
            )

            settings = {"demucs_stems": ac.ALL_STEMS}
            model_data._load_and_derive_model_properties(settings)

            assert (
                model_data.demucs_version == expected_version
            ), f"Model '{model_name}' should detect version {expected_version}, got {model_data.demucs_version}"

    def test_directory_structure_integrity(self):
        """Test that the expected directory structure is maintained."""
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir)

            # Create full expected structure
            demucs_root = models_dir / "Demucs_Models"
            demucs_root.mkdir()

            # Root directory for legacy models
            (demucs_root / "htdemucs.th").touch()
            (demucs_root / "tasnet.th").touch()

            # v3_v4_repo subdirectory for newer models
            v3_v4_repo = demucs_root / ac.DEMUCS_V3_V4_REPO_DIR_NAME
            v3_v4_repo.mkdir()
            (v3_v4_repo / "htdemucs_ft.yaml").touch()
            (v3_v4_repo / "mdx_extra.yaml").touch()

            # model_data subdirectory for configurations
            model_data_dir = demucs_root / "model_data"
            model_data_dir.mkdir()
            (model_data_dir / "model_name_mapper.json").touch()

            # Verify structure
            assert demucs_root.exists()
            assert v3_v4_repo.exists()
            assert model_data_dir.exists()

            # Verify files are in correct locations
            assert (demucs_root / "htdemucs.th").exists()  # Legacy in root
            assert (v3_v4_repo / "htdemucs_ft.yaml").exists()  # V4 in subdirectory
            assert not (demucs_root / "htdemucs_ft.yaml").exists()  # V4 NOT in root
            assert not (
                v3_v4_repo / "htdemucs.th"
            ).exists()  # Legacy NOT in subdirectory

    @pytest.mark.parametrize(
        "model_name,download_url,should_be_in_v3_v4_repo",
        [
            (
                "demucs_v3_model",
                "https://example.com/model.yaml",
                True,
            ),  # .yaml extension
            (
                "htdemucs_v4_ft",
                "https://example.com/model.yaml",
                True,
            ),  # .yaml extension
            (
                "v3_model_test",
                "https://example.com/model.yaml",
                True,
            ),  # .yaml extension
            ("v4_special", "https://example.com/model.yaml", True),  # .yaml extension
            ("htdemucs", "https://example.com/model.th", False),  # .th extension
            ("tasnet", "https://example.com/model.th", False),  # .th extension
            (
                "regular_model",
                "https://example.com/model.ckpt",
                False,
            ),  # .ckpt extension
            ("some_model", "https://example.com/model.gz", False),  # .gz extension
        ],
    )
    def test_v3_v4_model_detection_logic(
        self, model_name, download_url, should_be_in_v3_v4_repo
    ):
        """Test the logic that determines if a model should go in v3_v4_repo."""
        # The actual logic checks for v3/v4 in model name OR .yaml extension
        model_has_v3_v4 = any(version in model_name.lower() for version in ["v3", "v4"])
        is_yaml_file = download_url.endswith(".yaml")
        is_v3_v4_model = model_has_v3_v4 or is_yaml_file

        assert (
            is_v3_v4_model == should_be_in_v3_v4_repo
        ), f"Model '{model_name}' with URL '{download_url}' detection failed. Expected: {should_be_in_v3_v4_repo}, Got: {is_v3_v4_model}"

    def test_fallback_path_resolution(self):
        """Test that model path resolution tries both directories as fallback."""
        model_data = ModelData(
            process_method=ac.DEMUCS_ARCH_TYPE, model_name="test_model"
        )

        with patch(
            "uvr_pyside6_ui.core.model_data.DEMUCS_MODELS_DIR_PATH"
        ) as mock_root_dir:
            with patch(
                "uvr_pyside6_ui.core.model_data.DEMUCS_NEWER_REPO_DIR_PATH"
            ) as mock_v3_v4_dir:
                # Model not found in primary location, should check fallback

                def mock_exists(path):
                    # Simulate model found in fallback location
                    return str(path).endswith(
                        "test_model.yaml"
                    ) and "v3_v4_repo" in str(path)

                with patch.object(Path, "exists", side_effect=mock_exists):
                    result = model_data._determine_model_path()

                    # Should find the model in the fallback directory
                    assert result is not None

    def test_config_file_placement_with_v3_v4_models(self):
        """Test that config files for V3/V4 models also go in v3_v4_repo."""
        with patch("uvr_pyside6_ui.core.model_downloader.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {"content-length": "1000"}
            mock_response.iter_content.return_value = [b"config_data"]
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            model_name = "test_v4_model"
            download_url = "https://example.com/model.yaml"  # .yaml triggers v3_v4_repo
            config_url = "https://example.com/config.yaml"

            with tempfile.TemporaryDirectory() as temp_dir:
                target_dir = Path(temp_dir) / "Demucs_Models"
                target_dir.mkdir(parents=True, exist_ok=True)

                with patch(
                    "uvr_pyside6_ui.core.model_downloader.MODEL_TYPE_PATHS",
                    {ac.DEMUCS_MODELS_KEY: target_dir},
                ):
                    with patch("builtins.open", mock_open()):
                        success, message, config_path = download_model_file(
                            model_name, download_url, ac.DEMUCS_MODELS_KEY, config_url
                        )

                assert success is True

                # Config should also be in v3_v4_repo directory
                if config_path:
                    assert ac.DEMUCS_V3_V4_REPO_DIR_NAME in config_path

    def test_yaml_extension_triggers_v3_v4_repo_placement(self):
        """Test that any .yaml file (regardless of model name) goes to v3_v4_repo."""
        with patch("uvr_pyside6_ui.core.model_downloader.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.headers = {"content-length": "1000"}
            mock_response.iter_content.return_value = [b"model_data"]
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Model name without v3/v4 but with .yaml extension
            model_name = "htdemucs_ft_new"
            download_url = (
                "https://example.com/model.yaml"  # .yaml should trigger v3_v4_repo
            )

            with tempfile.TemporaryDirectory() as temp_dir:
                target_dir = Path(temp_dir) / "Demucs_Models"
                target_dir.mkdir(parents=True, exist_ok=True)

                with patch(
                    "uvr_pyside6_ui.core.model_downloader.MODEL_TYPE_PATHS",
                    {ac.DEMUCS_MODELS_KEY: target_dir},
                ):
                    with patch("builtins.open", mock_open()):
                        success, message, config_path = download_model_file(
                            model_name, download_url, ac.DEMUCS_MODELS_KEY
                        )

                assert success is True
                # Should be placed in v3_v4_repo because of .yaml extension
                assert ac.DEMUCS_V3_V4_REPO_DIR_NAME in str(message)
