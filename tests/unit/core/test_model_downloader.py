"""
Unit tests for model_downloader module.

Tests cover online catalog fetching, model file downloads,
caching mechanisms, and error handling scenarios.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core import model_downloader


@pytest.mark.unit
@pytest.mark.download
class TestModelDownloader:
    """Test cases for model downloader functionality."""

    def setup_method(self):
        """Setup test environment."""
        # Patch the global variables to use temp directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.models_dir = self.temp_dir / "models"
        self.cache_dir = self.temp_dir / "cache"

        patcher1 = patch.object(model_downloader, "MODELS_DIR", self.models_dir)
        patcher2 = patch.object(model_downloader, "CACHE_DIR", self.cache_dir)
        patcher3 = patch.object(
            model_downloader,
            "ONLINE_CATALOG_CACHE_FILE",
            self.cache_dir / ac.ONLINE_CATALOG_CACHE_FILENAME,
        )

        self.models_dir_patcher = patcher1.start()
        self.cache_dir_patcher = patcher2.start()
        self.cache_file_patcher = patcher3.start()

        # Update MODEL_TYPE_PATHS
        model_downloader.MODEL_TYPE_PATHS = {
            ac.VR_ARCH_MODELS_KEY: self.models_dir / "VR_Models",
            ac.MDX_NET_MODELS_KEY: self.models_dir / "MDX_Net_Models",
            ac.DEMUCS_MODELS_KEY: self.models_dir / "Demucs_Models",
        }

    def teardown_method(self):
        """Clean up test environment."""
        patch.stopall()

    def test_fetch_online_model_catalog_success(self):
        """Test successful fetching of online model catalog."""
        mock_catalog = {
            ac.ONLINE_VR_DOWNLOAD_LIST_KEY: {"model1": "url1"},
            ac.ONLINE_MDX_DOWNLOAD_LIST_KEY: {"model2": "url2"},
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_catalog
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.dump") as mock_json_dump:
                    catalog = model_downloader.fetch_online_model_catalog()

                    assert catalog == mock_catalog
                    mock_json_dump.assert_called_once()

    def test_fetch_online_model_catalog_uses_cache(self):
        """Test that cached catalog is used when available."""
        cached_catalog = {"cached": "data"}
        cache_file = self.cache_dir / ac.ONLINE_CATALOG_CACHE_FILENAME

        # Create cache directory and file
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cached_catalog))

        with patch("builtins.print") as mock_print:
            catalog = model_downloader.fetch_online_model_catalog()

            assert catalog == cached_catalog
            mock_print.assert_called_with("Using cached online model catalog.")

    def test_fetch_online_model_catalog_cache_error_fallback(self):
        """Test fallback when cache file is corrupted."""
        cache_file = self.cache_dir / ac.ONLINE_CATALOG_CACHE_FILENAME

        # Create corrupted cache file
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("invalid json {")

        mock_catalog = {"fresh": "data"}
        mock_response = Mock()
        mock_response.json.return_value = mock_catalog
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.dump"):
                    catalog = model_downloader.fetch_online_model_catalog()

                    assert catalog == mock_catalog

    def test_fetch_online_model_catalog_network_error_uses_fallback(self):
        """Test fallback catalog when network request fails."""
        with patch(
            "requests.get", side_effect=requests.RequestException("Network error")
        ):
            catalog = model_downloader.fetch_online_model_catalog()

            assert catalog == ac.FALLBACK_ONLINE_CATALOG

    def test_fetch_online_model_catalog_json_decode_error_uses_fallback(self):
        """Test fallback when response JSON is invalid."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            catalog = model_downloader.fetch_online_model_catalog()

            assert catalog == ac.FALLBACK_ONLINE_CATALOG

    def test_download_model_file_success(self):
        """Test successful model file download."""
        model_name = "test_model"
        download_url = "https://example.com/model.pth"
        model_type = ac.VR_ARCH_MODELS_KEY

        # Create target directory
        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)

        mock_response = Mock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_response.raise_for_status.return_value = None

        progress_calls = []

        def mock_progress(filename, percent):
            progress_calls.append((filename, percent))

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()) as mock_file:
                success, message, config_path = model_downloader.download_model_file(
                    model_name,
                    download_url,
                    model_type,
                    progress_callback=mock_progress,
                )

                assert success is True
                assert str(target_dir / "model.pth") in message
                assert config_path is None
                assert len(progress_calls) > 0

    def test_download_model_file_with_config(self):
        """Test downloading model file with config file."""
        model_name = "test_demucs"
        download_url = "https://example.com/model.th"
        config_url = "https://example.com/model.yaml"
        model_type = ac.DEMUCS_MODELS_KEY

        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)

        mock_response = Mock()
        mock_response.headers = {"content-length": "500"}
        mock_response.iter_content.return_value = [b"data"]
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()):
                success, message, config_path = model_downloader.download_model_file(
                    model_name, download_url, model_type, config_url=config_url
                )

                assert success is True
                assert config_path is not None
                assert "model.yaml" in config_path

    @patch("uvr_pyside6_ui.core.model_downloader.requests.get")
    def test_download_model_file_demucs_v3_v4_special_handling(self, mock_get):
        """Test special handling for Demucs v3/v4 models."""
        mock_response = Mock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"test_data"]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Use a model name that contains v3 to trigger the special handling
        model_name = "demucs_v3_test_model"  # This should trigger v3_v4_repo logic
        download_url = "https://example.com/model.yaml"

        # Create the target directory structure before the test
        target_dir = model_downloader.MODEL_TYPE_PATHS[ac.DEMUCS_MODELS_KEY]
        target_dir.mkdir(parents=True, exist_ok=True)

        with patch("builtins.open", mock_open()):
            success, message, config_path = model_downloader.download_model_file(
                model_name,
                download_url,
                ac.DEMUCS_MODELS_KEY,
                "https://example.com/config.yaml",
            )

        assert success is True
        # The model should be saved in the v3_v4_repo subdirectory
        assert ac.DEMUCS_V3_V4_REPO_DIR_NAME in message

    def test_download_model_file_unknown_model_type(self):
        """Test error handling for unknown model type."""
        success, message, config_path = model_downloader.download_model_file(
            "test", "url", "UNKNOWN_TYPE"
        )

        assert success is False
        assert "Unknown model type" in message
        assert config_path is None

    def test_download_model_file_network_error(self):
        """Test error handling for network errors during download."""
        model_name = "test_model"
        download_url = "https://example.com/model.pth"
        model_type = ac.VR_ARCH_MODELS_KEY

        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)

        with patch(
            "requests.get", side_effect=requests.RequestException("Network error")
        ):
            success, message, config_path = model_downloader.download_model_file(
                model_name, download_url, model_type
            )

            assert success is False
            assert "Error downloading" in message
            assert config_path is None

    def test_download_model_file_progress_callback_no_content_length(self):
        """Test progress callback when content-length header is missing."""
        model_name = "test_model"
        download_url = "https://example.com/model.pth"
        model_type = ac.VR_ARCH_MODELS_KEY

        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)

        mock_response = Mock()
        mock_response.headers = {}  # No content-length
        mock_response.iter_content.return_value = [b"chunk"] * 10
        mock_response.raise_for_status.return_value = None

        progress_calls = []

        def mock_progress(filename, percent):
            progress_calls.append((filename, percent))

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()):
                success, message, config_path = model_downloader.download_model_file(
                    model_name,
                    download_url,
                    model_type,
                    progress_callback=mock_progress,
                )

                assert success is True
                assert len(progress_calls) > 0

    def test_download_model_file_cleanup_on_error(self):
        """Test that partial downloads are cleaned up on error."""
        model_name = "test_model"
        download_url = "https://example.com/model.pth"
        model_type = ac.VR_ARCH_MODELS_KEY

        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "model.pth"

        # Create a partial file
        target_file.write_text("partial data")
        assert target_file.exists()

        with patch("requests.get", side_effect=requests.RequestException("Error")):
            success, message, config_path = model_downloader.download_model_file(
                model_name, download_url, model_type
            )

            assert success is False
            # File should be cleaned up
            assert not target_file.exists()

    @pytest.mark.edge_case
    def test_download_model_file_unexpected_error(self):
        """Test handling of unexpected errors during download."""
        model_name = "test_model"
        download_url = "https://example.com/model.pth"
        model_type = ac.VR_ARCH_MODELS_KEY

        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)

        with patch("requests.get", side_effect=Exception("Unexpected error")):
            success, message, config_path = model_downloader.download_model_file(
                model_name, download_url, model_type
            )

            assert success is False
            assert "An unexpected error occurred" in message
            assert config_path is None

    def test_model_type_paths_initialization(self):
        """Test that model type paths are properly initialized."""
        expected_paths = {
            ac.VR_ARCH_MODELS_KEY: model_downloader.MODELS_DIR / "VR_Models",
            ac.MDX_NET_MODELS_KEY: model_downloader.MODELS_DIR / "MDX_Net_Models",
            ac.DEMUCS_MODELS_KEY: model_downloader.MODELS_DIR / "Demucs_Models",
        }

        for model_type, expected_path in expected_paths.items():
            assert model_type in model_downloader.MODEL_TYPE_PATHS
            # Path should be equivalent (may be different objects but same path)
            assert str(model_downloader.MODEL_TYPE_PATHS[model_type]) == str(
                expected_path
            )

    def test_cache_directory_creation(self):
        """Test that cache directory is created properly."""
        # This is handled in module initialization
        assert model_downloader.CACHE_DIR is not None
        assert model_downloader.ONLINE_CATALOG_CACHE_FILE is not None

    @pytest.mark.parametrize(
        "model_type",
        [ac.VR_ARCH_MODELS_KEY, ac.MDX_NET_MODELS_KEY, ac.DEMUCS_MODELS_KEY],
    )
    def test_download_model_file_different_model_types(self, model_type):
        """Test downloading models for different model types."""
        model_name = f"test_{model_type.lower().replace(' ', '_')}"
        download_url = "https://example.com/model.file"

        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)

        mock_response = Mock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content.return_value = [b"data"]
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()):
                success, message, config_path = model_downloader.download_model_file(
                    model_name, download_url, model_type
                )

                assert success is True
                assert str(target_dir) in message

    def test_progress_callback_called_correctly(self):
        """Test that progress callback is called with correct parameters."""
        model_name = "test_model"
        download_url = "https://example.com/model.pth"
        model_type = ac.VR_ARCH_MODELS_KEY

        target_dir = model_downloader.MODEL_TYPE_PATHS[model_type]
        target_dir.mkdir(parents=True, exist_ok=True)

        mock_response = Mock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content.return_value = [b"x" * 50, b"y" * 50]
        mock_response.raise_for_status.return_value = None

        progress_calls = []

        def mock_progress(filename, percent):
            progress_calls.append((filename, percent))

        with patch("requests.get", return_value=mock_response):
            with patch("builtins.open", mock_open()):
                model_downloader.download_model_file(
                    model_name,
                    download_url,
                    model_type,
                    progress_callback=mock_progress,
                )

                # Should have start (0), progress updates, and end (100)
                assert (Path(download_url).name, 0) in progress_calls
                assert (Path(download_url).name, 100) in progress_calls

                # All calls should have the correct filename
                for filename, percent in progress_calls:
                    assert filename == Path(download_url).name
                    assert 0 <= percent <= 100


@pytest.mark.integration
@pytest.mark.download
class TestModelDownloaderIntegration:
    """Integration tests for model downloader."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_full_download_workflow(self):
        """Test complete download workflow from catalog to file."""
        # Mock catalog data
        mock_catalog = {
            ac.ONLINE_VR_DOWNLOAD_LIST_KEY: {
                "Test VR Model": "https://example.com/test_vr.pth"
            }
        }

        mock_response_catalog = Mock()
        mock_response_catalog.json.return_value = mock_catalog
        mock_response_catalog.raise_for_status.return_value = None

        mock_response_download = Mock()
        mock_response_download.headers = {"content-length": "1000"}
        mock_response_download.iter_content.return_value = [b"model_data"]
        mock_response_download.raise_for_status.return_value = None

        with patch(
            "requests.get", side_effect=[mock_response_catalog, mock_response_download]
        ):
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.dump"):
                    # First fetch catalog
                    catalog = model_downloader.fetch_online_model_catalog()
                    assert "Test VR Model" in catalog[ac.ONLINE_VR_DOWNLOAD_LIST_KEY]

                    # Then download model
                    success, message, config_path = (
                        model_downloader.download_model_file(
                            "Test VR Model",
                            "https://example.com/test_vr.pth",
                            ac.VR_ARCH_MODELS_KEY,
                        )
                    )

                    assert success is True

    def test_cache_persistence(self):
        """Test that cache persists between calls."""
        mock_catalog = {"cached": "data"}

        with patch.object(
            model_downloader,
            "ONLINE_CATALOG_CACHE_FILE",
            self.temp_dir / "test_cache.json",
        ):
            # First call should cache
            mock_response = Mock()
            mock_response.json.return_value = mock_catalog
            mock_response.raise_for_status.return_value = None

            with patch("requests.get", return_value=mock_response):
                catalog1 = model_downloader.fetch_online_model_catalog()

            # Second call should use cache (no network call)
            with patch("requests.get") as mock_get:
                catalog2 = model_downloader.fetch_online_model_catalog()
                mock_get.assert_not_called()

            assert catalog1 == catalog2 == mock_catalog
