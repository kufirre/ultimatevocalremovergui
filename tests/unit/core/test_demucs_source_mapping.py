"""
Comprehensive unit tests for Demucs source mapping optimization.

This module tests the core functions that handle Demucs model output transformation
and source mapping to ensure the bass/drums swapping fix never regresses.
"""

import numpy as np
import pytest

from uvr_pyside6_ui.core import app_constants as ac


@pytest.mark.critical
@pytest.mark.regression
class TestDemucsSourceMapping:
    """Test the core Demucs source mapping functions."""

    def test_get_demucs_source_mapping_2_stem(self):
        """Test 2-stem Demucs source mapping (UVR models)."""
        source_list, source_map = ac.get_demucs_source_mapping(2)

        # Verify 2-stem structure
        assert len(source_list) == 2, "2-stem should return 2 sources"
        assert len(source_map) == 2, "2-stem should return 2 mappings"

        # Verify expected sources
        expected_sources = [ac.INST_STEM, ac.VOCAL_STEM]
        assert (
            source_list == expected_sources
        ), f"2-stem sources should be {expected_sources}, got {source_list}"

        # Verify mappings
        expected_mapping = {ac.INST_STEM: 0, ac.VOCAL_STEM: 1}
        assert (
            source_map == expected_mapping
        ), f"2-stem mapping should be {expected_mapping}, got {source_map}"

    def test_get_demucs_source_mapping_4_stem(self):
        """Test 4-stem Demucs source mapping (standard models)."""
        source_list, source_map = ac.get_demucs_source_mapping(4)

        # Verify 4-stem structure
        assert len(source_list) == 4, "4-stem should return 4 sources"
        assert len(source_map) == 4, "4-stem should return 4 mappings"

        # Verify expected UVR interface order: [Bass, Drums, Other, Vocals]
        expected_sources = [ac.BASS_STEM, ac.DRUM_STEM, ac.OTHER_STEM, ac.VOCAL_STEM]
        assert (
            source_list == expected_sources
        ), f"4-stem sources should be {expected_sources}, got {source_list}"

        # Verify UVR interface mappings
        expected_mapping = {
            ac.BASS_STEM: 0,  # Bass at index 0 (UVR interface)
            ac.DRUM_STEM: 1,  # Drums at index 1 (UVR interface)
            ac.OTHER_STEM: 2,  # Other at index 2
            ac.VOCAL_STEM: 3,  # Vocals at index 3
        }
        assert (
            source_map == expected_mapping
        ), f"4-stem mapping should be {expected_mapping}, got {source_map}"

    def test_get_demucs_source_mapping_6_stem(self):
        """Test 6-stem Demucs source mapping (extended models)."""
        source_list, source_map = ac.get_demucs_source_mapping(6)

        # Verify 6-stem structure
        assert len(source_list) == 6, "6-stem should return 6 sources"
        assert len(source_map) == 6, "6-stem should return 6 mappings"

        # Verify expected sources
        expected_sources = [
            ac.BASS_STEM,
            ac.DRUM_STEM,
            ac.OTHER_STEM,
            ac.VOCAL_STEM,
            ac.GUITAR_STEM,
            ac.PIANO_STEM,
        ]
        assert (
            source_list == expected_sources
        ), f"6-stem sources should be {expected_sources}, got {source_list}"

        # Verify mappings
        expected_mapping = {
            ac.BASS_STEM: 0,
            ac.DRUM_STEM: 1,
            ac.OTHER_STEM: 2,
            ac.VOCAL_STEM: 3,
            ac.GUITAR_STEM: 4,
            ac.PIANO_STEM: 5,
        }
        assert (
            source_map == expected_mapping
        ), f"6-stem mapping should be {expected_mapping}, got {source_map}"

    def test_get_demucs_source_mapping_default_fallback(self):
        """Test that invalid stem counts default to 4-stem."""
        # Test various invalid inputs should all return 4-stem
        invalid_inputs = [0, 1, 3, 5, 7, 10, -1]

        for invalid_count in invalid_inputs:
            source_list, source_map = ac.get_demucs_source_mapping(invalid_count)

            # Should default to 4-stem
            assert (
                len(source_list) == 4
            ), f"Invalid count {invalid_count} should default to 4-stem, got {len(source_list)}"
            assert (
                len(source_map) == 4
            ), f"Invalid count {invalid_count} should default to 4-stem mapping, got {len(source_map)}"

            # Verify it's actually the 4-stem mapping
            expected_sources = [
                ac.BASS_STEM,
                ac.DRUM_STEM,
                ac.OTHER_STEM,
                ac.VOCAL_STEM,
            ]
            assert source_list == expected_sources


@pytest.mark.critical
@pytest.mark.regression
class TestDemucsTransformation:
    """Test the Demucs output transformation function."""

    def test_transform_demucs_output_to_uvr_order_4_stem(self):
        """Test 4-stem transformation from model output to UVR order."""
        # Create mock model output: [drums, bass, other, vocals] (model's natural order)
        # Shape: (n_stems, channels, time)
        model_output = np.array(
            [
                [[1.0, 1.1, 1.2], [1.0, 1.1, 1.2]],  # drums (model index 0)
                [[2.0, 2.1, 2.2], [2.0, 2.1, 2.2]],  # bass (model index 1)
                [[3.0, 3.1, 3.2], [3.0, 3.1, 3.2]],  # other (model index 2)
                [[4.0, 4.1, 4.2], [4.0, 4.1, 4.2]],  # vocals (model index 3)
            ]
        )

        # Apply transformation
        transformed = ac.transform_demucs_output_to_uvr_order(model_output, 4)

        # Verify shape is preserved
        assert (
            transformed.shape == model_output.shape
        ), "Transformation should preserve array shape"

        # Verify the swap: UVR expects [bass, drums, other, vocals]
        # Index 0 should now be bass (was drums)
        np.testing.assert_array_equal(
            transformed[0],
            model_output[1],
            "Index 0 should be bass after transformation",
        )

        # Index 1 should now be drums (was bass)
        np.testing.assert_array_equal(
            transformed[1],
            model_output[0],
            "Index 1 should be drums after transformation",
        )

        # Index 2 should still be other (unchanged)
        np.testing.assert_array_equal(
            transformed[2], model_output[2], "Index 2 should remain other"
        )

        # Index 3 should still be vocals (unchanged)
        np.testing.assert_array_equal(
            transformed[3], model_output[3], "Index 3 should remain vocals"
        )

    def test_transform_demucs_output_to_uvr_order_6_stem(self):
        """Test 6-stem transformation (should also swap drums/bass)."""
        # Create mock 6-stem model output
        model_output = np.zeros((6, 2, 100))  # 6 stems, 2 channels, 100 samples

        # Set unique values for each stem to track the swap
        for i in range(6):
            model_output[i] = i + 1

        # Apply transformation
        transformed = ac.transform_demucs_output_to_uvr_order(model_output, 6)

        # Verify the drums/bass swap for 6-stem too
        np.testing.assert_array_equal(
            transformed[0], model_output[1], "6-stem: Index 0 should be bass"
        )
        np.testing.assert_array_equal(
            transformed[1], model_output[0], "6-stem: Index 1 should be drums"
        )

        # Other stems should remain unchanged
        for i in range(2, 6):
            np.testing.assert_array_equal(
                transformed[i],
                model_output[i],
                f"6-stem: Index {i} should remain unchanged",
            )

    def test_transform_demucs_output_to_uvr_order_2_stem(self):
        """Test 2-stem transformation (should be unchanged)."""
        # Create mock 2-stem model output
        model_output = np.array(
            [
                [[1.0, 1.1], [1.0, 1.1]],  # instrumental
                [[2.0, 2.1], [2.0, 2.1]],  # vocals
            ]
        )

        # Apply transformation
        transformed = ac.transform_demucs_output_to_uvr_order(model_output, 2)

        # 2-stem should be unchanged (no drums/bass to swap)
        np.testing.assert_array_equal(
            transformed, model_output, "2-stem transformation should be unchanged"
        )

    def test_transform_demucs_output_edge_cases(self):
        """Test transformation edge cases."""
        # Test with insufficient stems (less than 2)
        single_stem = np.array([[[1.0, 1.1], [1.0, 1.1]]])
        transformed = ac.transform_demucs_output_to_uvr_order(single_stem, 4)
        np.testing.assert_array_equal(
            transformed, single_stem, "Single stem should be unchanged"
        )

        # Test with empty array
        empty_array = np.array([]).reshape((0, 2, 100))
        transformed = ac.transform_demucs_output_to_uvr_order(empty_array, 4)
        np.testing.assert_array_equal(
            transformed, empty_array, "Empty array should be unchanged"
        )

    def test_transform_demucs_output_preserves_data_integrity(self):
        """Test that transformation preserves all data (no data loss)."""
        # Create model output with unique values to verify no data loss
        model_output = np.random.rand(4, 2, 1000)
        original_sum = np.sum(model_output)

        # Apply transformation
        transformed = ac.transform_demucs_output_to_uvr_order(model_output, 4)
        transformed_sum = np.sum(transformed)

        # Verify no data loss (sums should be equal)
        assert (
            abs(original_sum - transformed_sum) < 1e-10
        ), "Transformation should not lose any data"

        # Verify it's a copy, not a view
        assert not np.shares_memory(
            model_output, transformed
        ), "Transformation should return a copy"


@pytest.mark.critical
@pytest.mark.regression
class TestCaseInsensitiveLookup:
    """Test the case-insensitive stem lookup function."""

    def test_get_stem_index_safe_exact_match(self):
        """Test exact case-sensitive matches work."""
        source_map = {
            ac.BASS_STEM: 0,
            ac.DRUM_STEM: 1,
            ac.OTHER_STEM: 2,
            ac.VOCAL_STEM: 3,
        }

        # Test exact matches
        assert ac.get_stem_index_safe(source_map, ac.BASS_STEM) == 0
        assert ac.get_stem_index_safe(source_map, ac.DRUM_STEM) == 1
        assert ac.get_stem_index_safe(source_map, ac.OTHER_STEM) == 2
        assert ac.get_stem_index_safe(source_map, ac.VOCAL_STEM) == 3

    def test_get_stem_index_safe_case_insensitive(self):
        """Test case-insensitive matches work."""
        # Create source map with lowercase keys (like what original UVR creates)
        source_map = {"bass": 0, "drums": 1, "other": 2, "vocals": 3}

        # Test our title-case constants can find lowercase keys
        assert ac.get_stem_index_safe(source_map, "Bass") == 0
        assert ac.get_stem_index_safe(source_map, "Drums") == 1
        assert ac.get_stem_index_safe(source_map, "Other") == 2
        assert ac.get_stem_index_safe(source_map, "Vocals") == 3

    def test_get_stem_index_safe_mixed_cases(self):
        """Test various case combinations."""
        source_map = {"BASS": 0, "drums": 1, "Other": 2, "vOcAlS": 3}

        # Test all combinations work
        assert ac.get_stem_index_safe(source_map, "bass") == 0
        assert ac.get_stem_index_safe(source_map, "Bass") == 0
        assert ac.get_stem_index_safe(source_map, "BASS") == 0

        assert ac.get_stem_index_safe(source_map, "DRUMS") == 1
        assert ac.get_stem_index_safe(source_map, "Drums") == 1

        assert ac.get_stem_index_safe(source_map, "other") == 2
        assert ac.get_stem_index_safe(source_map, "OTHER") == 2

        assert ac.get_stem_index_safe(source_map, "vocals") == 3
        assert ac.get_stem_index_safe(source_map, "VOCALS") == 3

    def test_get_stem_index_safe_not_found(self):
        """Test returns None when stem not found."""
        source_map = {ac.BASS_STEM: 0, ac.DRUM_STEM: 1}

        # Test stems not in map
        assert ac.get_stem_index_safe(source_map, ac.VOCAL_STEM) is None
        assert ac.get_stem_index_safe(source_map, "NotAStem") is None
        assert ac.get_stem_index_safe(source_map, "") is None

    def test_get_stem_index_safe_empty_map(self):
        """Test behavior with empty source map."""
        empty_map = {}

        assert ac.get_stem_index_safe(empty_map, ac.VOCAL_STEM) is None
        assert ac.get_stem_index_safe(empty_map, "anything") is None

    def test_get_stem_index_safe_performance_exact_match_first(self):
        """Test that exact matches are found first (performance optimization)."""
        # This test ensures exact matches don't go through case-insensitive loop
        source_map = {ac.VOCAL_STEM: 0, "vocals": 1}  # Both exist

        # Exact match should return first occurrence (index 0)
        result = ac.get_stem_index_safe(source_map, ac.VOCAL_STEM)
        assert result == 0, "Exact match should be found first"


@pytest.mark.integration
@pytest.mark.regression
class TestDemucsSourceMappingIntegration:
    """Integration tests combining all Demucs mapping functions."""

    def test_complete_demucs_processing_pipeline(self):
        """Test the complete pipeline from source mapping to transformation."""
        # Test 4-stem pipeline
        stem_count = 4

        # Step 1: Get source mapping
        source_list, source_map = ac.get_demucs_source_mapping(stem_count)

        # Step 2: Create mock model output in model's natural order
        model_output = np.array(
            [
                [[1.0, 1.1], [1.0, 1.1]],  # drums (model index 0)
                [[2.0, 2.1], [2.0, 2.1]],  # bass (model index 1)
                [[3.0, 3.1], [3.0, 3.1]],  # other (model index 2)
                [[4.0, 4.1], [4.0, 4.1]],  # vocals (model index 3)
            ]
        )

        # Step 3: Transform to UVR order
        uvr_ordered_output = ac.transform_demucs_output_to_uvr_order(
            model_output, stem_count
        )

        # Step 4: Verify we can lookup stems correctly
        bass_idx = ac.get_stem_index_safe(source_map, ac.BASS_STEM)
        drums_idx = ac.get_stem_index_safe(source_map, ac.DRUM_STEM)
        other_idx = ac.get_stem_index_safe(source_map, ac.OTHER_STEM)
        vocals_idx = ac.get_stem_index_safe(source_map, ac.VOCAL_STEM)

        # Verify indices are found
        assert bass_idx == 0, "Bass should be at index 0 in UVR order"
        assert drums_idx == 1, "Drums should be at index 1 in UVR order"
        assert other_idx == 2, "Other should be at index 2 in UVR order"
        assert vocals_idx == 3, "Vocals should be at index 3 in UVR order"

        # Verify the actual data is correctly positioned
        # UVR order: [bass, drums, other, vocals]
        # Bass data (originally at model index 1) should now be at UVR index 0
        np.testing.assert_array_equal(uvr_ordered_output[bass_idx], model_output[1])

        # Drums data (originally at model index 0) should now be at UVR index 1
        np.testing.assert_array_equal(uvr_ordered_output[drums_idx], model_output[0])

    def test_bass_drums_swap_consistency(self):
        """Critical test: Verify bass/drums are consistently swapped."""
        # This is the core regression test for the bass/drums issue

        # Model natural output order
        model_order = (
            ac.DEMUCS_MODEL_OUTPUT_ORDER_4
        )  # ["drums", "bass", "other", "vocals"]

        # UVR interface expected order
        _, uvr_source_map = ac.get_demucs_source_mapping(4)

        # Create test data that clearly identifies each stem
        model_output = np.zeros((4, 2, 10))
        model_output[0] = 100  # drums at model index 0
        model_output[1] = 200  # bass at model index 1
        model_output[2] = 300  # other at model index 2
        model_output[3] = 400  # vocals at model index 3

        # Transform to UVR order
        uvr_output = ac.transform_demucs_output_to_uvr_order(model_output, 4)

        # Verify bass ends up at UVR index 0 (originally at model index 1)
        bass_uvr_idx = uvr_source_map[ac.BASS_STEM]  # Should be 0
        assert np.all(
            uvr_output[bass_uvr_idx] == 200
        ), "Bass data should be at UVR bass index"

        # Verify drums ends up at UVR index 1 (originally at model index 0)
        drums_uvr_idx = uvr_source_map[ac.DRUM_STEM]  # Should be 1
        assert np.all(
            uvr_output[drums_uvr_idx] == 100
        ), "Drums data should be at UVR drums index"

    def test_case_insensitive_lookup_with_real_demucs_scenario(self):
        """Test case-insensitive lookup handles real Demucs scenarios."""
        # Simulate what might happen in real Demucs processing

        # Original UVR creates lowercase source maps from model.sources
        lowercase_source_map = {"drums": 0, "bass": 1, "other": 2, "vocals": 3}

        # Our constants are title-case
        title_case_stems = [ac.DRUM_STEM, ac.BASS_STEM, ac.OTHER_STEM, ac.VOCAL_STEM]

        # Verify all lookups work
        for i, stem in enumerate(title_case_stems):
            found_idx = ac.get_stem_index_safe(lowercase_source_map, stem)
            assert found_idx is not None, f"Should find index for {stem}"
            # Note: We don't assert the exact index because this is testing the model's
            # natural order, not the UVR interface order

    def test_edge_case_empty_or_malformed_inputs(self):
        """Test robustness with edge cases."""
        # Test with None inputs
        assert ac.get_stem_index_safe({}, None) is None

        # Test with various malformed arrays
        malformed_arrays = [np.array([]), np.array([[[]]]), np.zeros((0, 2, 100))]

        for malformed in malformed_arrays:
            # Transformation should not crash and should return a copy
            result = ac.transform_demucs_output_to_uvr_order(malformed, 4)
            assert (
                result is not None
            ), "Transformation should handle malformed arrays gracefully"


@pytest.mark.regression
@pytest.mark.performance
class TestDemucsSourceMappingPerformance:
    """Performance regression tests for Demucs mapping functions."""

    def test_transformation_performance_large_arrays(self):
        """Test transformation performance with large audio arrays."""
        # Create large array similar to real audio processing
        large_array = np.random.rand(
            4, 2, 44100 * 60
        )  # 4 stems, stereo, 1 minute at 44.1kHz

        import time

        start_time = time.time()

        # Transform large array
        result = ac.transform_demucs_output_to_uvr_order(large_array, 4)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should be very fast (less than 1 second for 1 minute of audio)
        assert (
            processing_time < 1.0
        ), f"Transformation took too long: {processing_time:.3f}s"

        # Verify it's actually a copy
        assert not np.shares_memory(
            large_array, result
        ), "Should return a copy for safety"

    def test_lookup_performance_large_maps(self):
        """Test lookup performance doesn't degrade with large source maps."""
        # Create large source map
        large_map = {f"stem_{i}": i for i in range(1000)}
        large_map[ac.VOCAL_STEM] = 999  # Add our target at the end

        import time

        start_time = time.time()

        # Perform many lookups
        for _ in range(1000):
            result = ac.get_stem_index_safe(large_map, ac.VOCAL_STEM)
            assert result == 999

        end_time = time.time()
        processing_time = end_time - start_time

        # Should still be very fast
        assert processing_time < 0.1, f"Lookups took too long: {processing_time:.3f}s"
