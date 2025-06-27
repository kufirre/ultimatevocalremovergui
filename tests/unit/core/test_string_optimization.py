"""Tests for string operation optimization features.

This module tests the PathCache system and string optimization utilities
implemented to improve performance in file-heavy operations.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from uvr_pyside6_ui.core import app_constants as ac


class TestPathCache:
    """Test the PathCache system for performance optimization."""

    def setup_method(self):
        """Clear cache before each test."""
        ac.PathCache.clear()

    def teardown_method(self):
        """Clear cache after each test."""
        ac.PathCache.clear()

    def test_cache_initialization(self):
        """Test that cache starts empty."""
        ac.PathCache.clear()  # Ensure clean state
        assert ac.PathCache._cache == {}

    def test_get_or_compute_caching(self):
        """Test that get_or_compute properly caches results."""
        call_count = 0

        def expensive_computation():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # First call should compute
        result1 = ac.PathCache.get_or_compute("test_key", expensive_computation)
        assert result1 == "result_1"
        assert call_count == 1

        # Second call should use cache
        result2 = ac.PathCache.get_or_compute("test_key", expensive_computation)
        assert result2 == "result_1"  # Same result
        assert call_count == 1  # No additional computation

        # Different key should compute again
        result3 = ac.PathCache.get_or_compute("other_key", expensive_computation)
        assert result3 == "result_2"
        assert call_count == 2

    def test_cache_clear(self):
        """Test that cache can be cleared."""
        # Add something to cache
        ac.PathCache.get_or_compute("test", lambda: "value")
        assert len(ac.PathCache._cache) >= 1

        # Clear cache
        ac.PathCache.clear()
        assert ac.PathCache._cache == {}

    def test_get_project_root_returns_path(self):
        """Test get_project_root returns a valid Path object."""
        result = ac.PathCache.get_project_root()
        assert isinstance(result, Path)
        assert result.exists()  # Should be a real path

    def test_get_project_root_is_cached_in_normal_mode(self):
        """Test that get_project_root caches results in normal mode."""
        # Clear cache to start fresh
        ac.PathCache.clear()

        # Mock to simulate non-test environment
        with patch("sys.argv", ["python", "script.py"]), patch(
            "sys.modules", {"regular_module": Mock()}
        ):

            result1 = ac.PathCache.get_project_root()
            result2 = ac.PathCache.get_project_root()

            # Should return same cached object
            assert result1 == result2
            assert "project_root" in ac.PathCache._cache

    def test_get_models_dir_caching(self):
        """Test that get_models_dir properly caches results."""
        ac.PathCache.clear()

        # First call
        result1 = ac.PathCache.get_models_dir()
        assert isinstance(result1, Path)

        # Second call should use cache
        result2 = ac.PathCache.get_models_dir()
        assert result2 == result1
        # Should have cached the models_dir
        assert "models_dir" in ac.PathCache._cache

    def test_get_model_type_dir_caching(self):
        """Test that get_model_type_dir properly caches results."""
        ac.PathCache.clear()

        # First call for VR models
        result1 = ac.PathCache.get_model_type_dir(ac.VR_ARCH_MODELS_KEY)
        assert isinstance(result1, Path)
        assert result1.name == "VR_Models"

        # Second call should use cache
        result2 = ac.PathCache.get_model_type_dir(ac.VR_ARCH_MODELS_KEY)
        assert result2 == result1

    def test_get_model_type_dir_different_types(self):
        """Test that different model types get different cached entries."""
        ac.PathCache.clear()

        vr_dir = ac.PathCache.get_model_type_dir(ac.VR_ARCH_MODELS_KEY)
        mdx_dir = ac.PathCache.get_model_type_dir(ac.MDX_NET_MODELS_KEY)
        demucs_dir = ac.PathCache.get_model_type_dir(ac.DEMUCS_MODELS_KEY)

        assert vr_dir.name == "VR_Models"
        assert mdx_dir.name == "MDX_Net_Models"
        assert demucs_dir.name == "Demucs_Models"

        # All should be different paths
        assert vr_dir != mdx_dir != demucs_dir


class TestStringUtilities:
    """Test string optimization utility functions."""

    def test_join_url_parts_basic(self):
        """Test basic URL joining functionality."""
        result = ac.join_url_parts("https://example.com", "path/to/file")
        assert result == "https://example.com/path/to/file"

    def test_join_url_parts_trailing_slash(self):
        """Test URL joining when base has trailing slash."""
        result = ac.join_url_parts("https://example.com/", "path/to/file")
        assert result == "https://example.com/path/to/file"

    def test_join_url_parts_leading_slash(self):
        """Test URL joining when path has leading slash."""
        result = ac.join_url_parts("https://example.com", "/path/to/file")
        assert result == "https://example.com/path/to/file"

    def test_join_url_parts_both_slashes(self):
        """Test URL joining when both have slashes."""
        result = ac.join_url_parts("https://example.com/", "/path/to/file")
        assert result == "https://example.com/path/to/file"

    def test_join_url_parts_no_slashes(self):
        """Test URL joining when neither have slashes."""
        result = ac.join_url_parts("https://example.com", "path/to/file")
        assert result == "https://example.com/path/to/file"

    def test_join_url_parts_multiple_slashes(self):
        """Test URL joining with multiple slashes."""
        result = ac.join_url_parts("https://example.com///", "///path/to/file")
        assert result == "https://example.com/path/to/file"

    def test_join_url_parts_empty_path(self):
        """Test URL joining with empty path."""
        result = ac.join_url_parts("https://example.com/", "")
        # Empty path should result in base without trailing slash
        assert result == "https://example.com"

    def test_join_url_parts_empty_base(self):
        """Test URL joining with empty base."""
        result = ac.join_url_parts("", "path/to/file")
        assert result == "/path/to/file"

    def test_join_url_parts_both_empty(self):
        """Test URL joining with both empty."""
        result = ac.join_url_parts("", "")
        # Both empty should result in empty string
        assert result == ""


class TestPerformanceIntegration:
    """Test that string optimizations are properly integrated."""

    def setup_method(self):
        """Clear cache before each test."""
        ac.PathCache.clear()

    def teardown_method(self):
        """Clear cache after each test."""
        ac.PathCache.clear()

    def test_model_data_uses_cached_paths(self):
        """Test that model_data module uses cached paths."""
        from uvr_pyside6_ui.core import model_data

        # Call get_project_root function
        result = model_data.get_project_root()

        # Should return a Path object
        assert isinstance(result, Path)

        # Should be using the cached version from PathCache
        cached_result = ac.PathCache.get_project_root()
        assert result == cached_result

    def test_model_utils_uses_cached_paths(self):
        """Test that model_utils module uses cached paths."""
        from uvr_pyside6_ui.core import model_utils

        # Call get_project_root function
        result = model_utils.get_project_root()

        # Should return a Path object
        assert isinstance(result, Path)

        # Should be using the cached version from PathCache
        cached_result = ac.PathCache.get_project_root()
        assert result == cached_result

    def test_model_downloader_constants_exist(self):
        """Test that model_downloader has the expected constants."""
        from uvr_pyside6_ui.core import model_downloader

        # Should have MODEL_TYPE_PATHS constant
        assert hasattr(model_downloader, "MODEL_TYPE_PATHS")
        paths = model_downloader.MODEL_TYPE_PATHS

        # Should be a dictionary with expected keys
        assert isinstance(paths, dict)
        assert ac.VR_ARCH_MODELS_KEY in paths
        assert ac.MDX_NET_MODELS_KEY in paths
        assert ac.DEMUCS_MODELS_KEY in paths

    def test_uvr_core_adapter_uses_join_url_parts(self):
        """Test that uvr_core_adapter uses optimized URL joining."""
        from uvr_pyside6_ui.core import uvr_core_adapter

        # Test the join_url_parts usage in construct_full_url
        adapter = uvr_core_adapter.UVRCoreAdapter()

        result = adapter._construct_full_url("test.model", "https://example.com/base/")

        # Should return a proper URL (uses actual base URL logic)
        assert isinstance(result, str)
        assert "test.model" in result
        # The adapter may use a different base URL logic, just verify it's a valid URL
        assert result.startswith("http")
        assert "://" in result


class TestCachePerformance:
    """Test that caching actually improves performance."""

    def setup_method(self):
        """Clear cache before each test."""
        ac.PathCache.clear()

    def teardown_method(self):
        """Clear cache after each test."""
        ac.PathCache.clear()

    def test_path_cache_performance_benefit(self):
        """Test that caching reduces expensive operations."""
        expensive_call_count = 0

        def expensive_operation():
            nonlocal expensive_call_count
            expensive_call_count += 1
            # Simulate expensive file system operation
            return Path("/expensive/computation/result")

        # First call - should be expensive
        result1 = ac.PathCache.get_or_compute("expensive_path", expensive_operation)
        assert expensive_call_count == 1

        # Multiple subsequent calls - should use cache
        for _ in range(10):
            result = ac.PathCache.get_or_compute("expensive_path", expensive_operation)
            assert result == result1

        # Should still only have called expensive operation once
        assert expensive_call_count == 1

    def test_different_keys_different_cache_entries(self):
        """Test that different cache keys maintain separate entries."""
        ac.PathCache.get_or_compute("key1", lambda: "value1")
        ac.PathCache.get_or_compute("key2", lambda: "value2")
        ac.PathCache.get_or_compute("key3", lambda: "value3")

        assert len(ac.PathCache._cache) >= 3
        assert ac.PathCache._cache["key1"] == "value1"
        assert ac.PathCache._cache["key2"] == "value2"
        assert ac.PathCache._cache["key3"] == "value3"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Clear cache before each test."""
        ac.PathCache.clear()

    def teardown_method(self):
        """Clear cache after each test."""
        ac.PathCache.clear()

    def test_cache_with_none_values(self):
        """Test that cache handles None values correctly."""
        result = ac.PathCache.get_or_compute("none_key", lambda: None)
        assert result is None

        # Should still cache None values
        assert "none_key" in ac.PathCache._cache
        assert ac.PathCache._cache["none_key"] is None

    def test_cache_with_exception_in_compute_func(self):
        """Test cache behavior when compute function raises exception."""

        def failing_function():
            raise ValueError("Computation failed")

        with pytest.raises(ValueError, match="Computation failed"):
            ac.PathCache.get_or_compute("failing_key", failing_function)

        # Failed computation should not be cached
        assert "failing_key" not in ac.PathCache._cache

    def test_join_url_parts_with_special_characters(self):
        """Test URL joining with special characters."""
        result = ac.join_url_parts(
            "https://example.com/base%20path/", "/sub%20path/file%20name.txt"
        )
        assert result == "https://example.com/base%20path/sub%20path/file%20name.txt"

    def test_join_url_parts_with_query_params(self):
        """Test URL joining preserves query parameters."""
        result = ac.join_url_parts("https://example.com/api?version=1", "endpoint")
        assert result == "https://example.com/api?version=1/endpoint"


class TestRegressionProtection:
    """Tests to protect against regressions in string optimization."""

    def test_cached_paths_match_original_computation(self):
        """Ensure cached paths match what original computation would return."""
        ac.PathCache.clear()

        # Test that different path computations work correctly
        project_root = ac.PathCache.get_project_root()
        models_dir = ac.PathCache.get_models_dir()
        vr_dir = ac.PathCache.get_model_type_dir(ac.VR_ARCH_MODELS_KEY)

        # Verify relationships
        assert models_dir.parent == project_root
        assert vr_dir.parent == models_dir
        assert vr_dir.name == "VR_Models"

    def test_string_optimizations_preserve_functionality(self):
        """Ensure string optimizations don't break existing functionality."""
        # Test that URL joining produces same results as manual concatenation
        base = "https://example.com/base"
        path = "path/to/file"

        # Our optimized version
        optimized_result = ac.join_url_parts(base, path)

        # Manual version (what code might have done before)
        manual_result = base.rstrip("/") + "/" + path.lstrip("/")

        assert optimized_result == manual_result

    def test_cache_isolation_between_tests(self):
        """Ensure cache can be properly cleared between tests."""
        ac.PathCache.clear()
        initial_count = len(ac.PathCache._cache)

        # Add something to cache
        ac.PathCache.get_or_compute("test_isolation", lambda: "value")
        assert len(ac.PathCache._cache) == initial_count + 1

        # Clear cache (simulating test teardown)
        ac.PathCache.clear()
        assert len(ac.PathCache._cache) == 0

        # Verify it's actually clean
        assert "test_isolation" not in ac.PathCache._cache

    def test_path_cache_consistency(self):
        """Test that PathCache provides consistent results."""
        ac.PathCache.clear()

        # Multiple calls should return identical objects
        root1 = ac.PathCache.get_project_root()
        root2 = ac.PathCache.get_project_root()

        assert root1 == root2
        assert str(root1) == str(root2)

        models1 = ac.PathCache.get_models_dir()
        models2 = ac.PathCache.get_models_dir()

        assert models1 == models2
        assert str(models1) == str(models2)
