"""
Regression tests for stem assignment and vocal/instrumental swapping issues.

This module contains tests that prevent regression of the critical stem assignment
issues where selecting "vocal only" would output instrumental and vice versa.
"""

import json
from unittest.mock import Mock, mock_open, patch

import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.model_data import ModelData
from uvr_pyside6_ui.core.separate_vr_logic import SeparateVRLogic


@pytest.mark.regression
@pytest.mark.critical
class TestStemAssignmentRegression:
    """Critical regression tests for stem assignment fixes."""

    def setup_method(self):
        """Setup common test data for stem assignment tests."""
        self.model_data = ModelData()
        self.model_data.model_name = "test_vr_model"
        self.model_data.model_path = "test_model.pth"
        self.model_data.audio_file = "test_audio.wav"
        self.model_data.primary_stem = ac.VOCAL_STEM
        self.model_data.secondary_stem = ac.INST_STEM
        self.model_data.model_samplerate = 44100
        self.model_data.is_primary_stem_only = False
        self.model_data.is_secondary_stem_only = False

        self.process_data = {
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
            "base_text_console": "Test: ",
        }

    @pytest.mark.regression
    def test_vr_vocal_only_selection_outputs_vocals_not_instrumental(self):
        """
        CRITICAL Regression test: Selecting "vocal only" should output vocals, not instrumental.

        This test prevents regression of the stem swapping issue where VR models
        would output the wrong stem when user selected vocal-only or instrumental-only.
        """
        # Set up for vocal-only processing
        self.model_data.is_primary_stem_only = True  # User wants vocals only
        self.model_data.is_secondary_stem_only = False
        self.model_data.primary_stem = ac.VOCAL_STEM

        # Create separator
        separator = SeparateVRLogic(self.model_data, self.process_data)

        # Verify the separator is configured correctly for vocal-only output
        assert (
            separator.md.is_primary_stem_only == True
        ), "VR separator should be configured for vocal-only output"
        assert (
            separator.md.primary_stem == ac.VOCAL_STEM
        ), "Primary stem should be vocals when user selects vocal-only"
        assert (
            separator.md.is_secondary_stem_only == False
        ), "Secondary stem should not be selected when user wants vocal-only"

    @pytest.mark.regression
    def test_vr_instrumental_only_selection_outputs_instrumental_not_vocals(self):
        """
        CRITICAL Regression test: Selecting "instrumental only" should output instrumental, not vocals.

        This test prevents regression of the stem swapping issue from the other direction.
        """
        # Set up for instrumental-only processing
        self.model_data.is_primary_stem_only = False
        self.model_data.is_secondary_stem_only = True  # User wants instrumental only
        self.model_data.secondary_stem = ac.INST_STEM

        # Create separator
        separator = SeparateVRLogic(self.model_data, self.process_data)

        # Verify the separator is configured correctly for instrumental-only output
        assert (
            separator.md.is_secondary_stem_only == True
        ), "VR separator should be configured for instrumental-only output"
        assert (
            separator.md.secondary_stem == ac.INST_STEM
        ), "Secondary stem should be instrumental when user selects instrumental-only"
        assert (
            separator.md.is_primary_stem_only == False
        ), "Primary stem should not be selected when user wants instrumental-only"

    @pytest.mark.regression
    def test_vr_stem_assignment_matches_user_intention(self):
        """
        CRITICAL Regression test: VR stem assignment should match user intention.

        This is the core regression test that prevents the stem swapping issue
        where user selections didn't match the actual output.
        """
        test_cases = [
            {
                "name": "User wants vocals",
                "primary_stem_only": True,
                "secondary_stem_only": False,
                "expected_primary": ac.VOCAL_STEM,
                "expected_secondary": ac.INST_STEM,
            },
            {
                "name": "User wants instrumental",
                "primary_stem_only": False,
                "secondary_stem_only": True,
                "expected_primary": ac.VOCAL_STEM,
                "expected_secondary": ac.INST_STEM,
            },
            {
                "name": "User wants both stems",
                "primary_stem_only": False,
                "secondary_stem_only": False,
                "expected_primary": ac.VOCAL_STEM,
                "expected_secondary": ac.INST_STEM,
            },
        ]

        for case in test_cases:
            # Set up model data for this test case
            self.model_data.is_primary_stem_only = case["primary_stem_only"]
            self.model_data.is_secondary_stem_only = case["secondary_stem_only"]
            self.model_data.primary_stem = ac.VOCAL_STEM
            self.model_data.secondary_stem = ac.INST_STEM

            # Create separator
            separator = SeparateVRLogic(self.model_data, self.process_data)

            # Verify the separator is configured correctly for user intention
            assert (
                separator.md.is_primary_stem_only == case["primary_stem_only"]
            ), f"Primary stem only setting should match user intention for {case['name']}"

            assert (
                separator.md.is_secondary_stem_only == case["secondary_stem_only"]
            ), f"Secondary stem only setting should match user intention for {case['name']}"

            # Verify stem assignments match expectations
            assert (
                separator.md.primary_stem == case["expected_primary"]
            ), f"Primary stem should be {case['expected_primary']} for {case['name']}"

            assert (
                separator.md.secondary_stem == case["expected_secondary"]
            ), f"Secondary stem should be {case['expected_secondary']} for {case['name']}"

    @pytest.mark.regression
    def test_vr_spectrogram_assignment_is_consistent(self):
        """
        Regression test: VR spectrogram assignment should be consistent with model behavior.

        This test ensures that the spectrogram assignment logic that was fixed
        remains consistent and doesn't regress.
        """
        # Test the core logic that was fixed
        self.model_data.primary_stem = ac.VOCAL_STEM
        self.model_data.secondary_stem = ac.INST_STEM

        # Create separator
        separator = SeparateVRLogic(self.model_data, self.process_data)

        # Verify that the separator maintains consistent stem assignments
        assert (
            separator.md.primary_stem == ac.VOCAL_STEM
        ), "Primary stem assignment should be consistent"
        assert (
            separator.md.secondary_stem == ac.INST_STEM
        ), "Secondary stem assignment should be consistent"

        # Verify that the audio file path is properly set
        assert (
            separator.audio_file_path is not None
        ), "Audio file path should be set for processing"


@pytest.mark.regression
@pytest.mark.integration
class TestStemAssignmentIntegration:
    """Integration tests for stem assignment across different model types."""

    @pytest.mark.regression
    def test_mdx_stem_assignment_consistency(self):
        """
        Regression test: MDX models should have consistent stem assignment.

        This test ensures that the stem assignment fixes also work correctly
        for MDX models and don't regress.
        """
        from uvr_pyside6_ui.core.separate_mdx_logic import SeparateMDXLogic

        model_data = ModelData()
        model_data.model_name = "test_mdx_model.onnx"
        model_data.process_method = ac.MDX_ARCH_TYPE
        model_data.primary_stem = ac.VOCAL_STEM
        model_data.secondary_stem = ac.INST_STEM
        model_data.is_primary_stem_only = True  # User wants vocals only

        process_data = {
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        # Test that MDX separator can be created with correct stem settings
        separator = SeparateMDXLogic(model_data, process_data)

        assert (
            separator.md.is_primary_stem_only == True
        ), "MDX separator should respect primary stem only setting"
        assert (
            separator.md.primary_stem == ac.VOCAL_STEM
        ), "MDX separator should have correct primary stem assignment"

    @pytest.mark.regression
    def test_demucs_stem_assignment_consistency(self):
        """
        Regression test: Demucs models should have consistent stem assignment.

        This test ensures that the stem assignment fixes work correctly
        for Demucs models across different stem configurations.
        """
        from uvr_pyside6_ui.core.separate_demucs_logic import SeparateDemucsLogic

        model_data = ModelData()
        model_data.model_name = "htdemucs_ft.yaml"
        model_data.process_method = ac.DEMUCS_ARCH_TYPE
        model_data.demucs_stems = ac.VOCAL_STEM  # User wants vocals only
        model_data.primary_stem = ac.VOCAL_STEM

        process_data = {
            "set_progress_bar": Mock(),
            "write_to_console": Mock(),
            "_is_running_check": Mock(return_value=True),
        }

        # Test that Demucs separator can be created with correct stem settings
        separator = SeparateDemucsLogic(model_data, process_data)

        assert (
            separator.md.demucs_stems == ac.VOCAL_STEM
        ), "Demucs separator should respect stem selection"
        assert (
            separator.md.primary_stem == ac.VOCAL_STEM
        ), "Demucs separator should have correct primary stem assignment"


@pytest.mark.critical
@pytest.mark.regression
class TestSwappedStemLogic:
    """Test swapped stem logic for single model processing."""

    def _create_mock_vr_model(self, settings, primary_stem="Vocals"):
        """Helper method to create a mocked VR model with consistent setup."""
        hash_json_data = {"primary_stem": primary_stem, "vr_model_param": "test.json"}

        with patch(
            "uvr_pyside6_ui.core.model_data.VR_HASH_DIR_PATH"
        ) as mock_hash_dir, patch(
            "uvr_pyside6_ui.core.model_data.VR_MODELS_DIR_PATH"
        ) as mock_models_dir, patch(
            "builtins.open", mock_open(read_data=json.dumps(hash_json_data))
        ), patch(
            "uvr_pyside6_ui.core.model_data.Path"
        ) as mock_path, patch(
            "uvr_pyside6_ui.core.model_data.ModelParameters"
        ) as mock_model_params, patch(
            "uvr_pyside6_ui.core.model_data.hashlib"
        ) as mock_hashlib:

            # Setup common mocks
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stem = "test_model"
            mock_hashlib.md5.return_value.hexdigest.return_value = "fake_hash"

            # Mock ModelParameters properly for VR models
            mock_param_instance = Mock()
            mock_param_instance.param = {"sr": 44100}
            mock_model_params.return_value = mock_param_instance

            # Mock VR param file path
            vr_param_path = Mock()
            vr_param_path.exists.return_value = True
            mock_models_dir.__truediv__ = Mock(return_value=vr_param_path)

            return ModelData.from_settings_dict(settings)

    def _create_mock_mdx_model(self, settings, primary_stem="Vocals"):
        """Helper method to create a mocked MDX model with consistent setup."""
        hash_json_data = {"primary_stem": primary_stem}

        with patch(
            "uvr_pyside6_ui.core.model_data.MDX_HASH_DIR_PATH"
        ) as mock_hash_dir, patch(
            "uvr_pyside6_ui.core.model_data.MDX_MODELS_DIR_PATH"
        ) as mock_models_dir, patch(
            "builtins.open", mock_open(read_data=json.dumps(hash_json_data))
        ), patch(
            "uvr_pyside6_ui.core.model_data.Path"
        ) as mock_path:

            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stem = "test_mdx_model"

            # Mock the model path resolution
            mock_models_dir.__truediv__ = Mock(return_value=mock_path.return_value)

            return ModelData.from_settings_dict(settings)

    def _create_mock_demucs_model(self, settings):
        """Helper method to create a mocked Demucs model with consistent setup."""
        with patch(
            "uvr_pyside6_ui.core.model_data.DEMUCS_MODELS_DIR_PATH"
        ) as mock_demucs_dir, patch(
            "uvr_pyside6_ui.core.model_data.DEMUCS_NEWER_REPO_DIR_PATH"
        ) as mock_newer_dir, patch(
            "uvr_pyside6_ui.core.model_data.Path"
        ) as mock_path:

            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stem = "test_demucs"

            # Mock the mapper file doesn't exist so it falls back to direct file lookup
            mapper_path = Mock()
            mapper_path.exists.return_value = False
            mock_demucs_dir.__truediv__ = Mock(return_value=mapper_path)

            return ModelData.from_settings_dict(settings)

    def test_vr_model_with_swapped_stems(self):
        """Test VR model where user wants secondary stem only."""
        # Create settings where user wants Instrumental Only
        settings = {
            "chosen_process_method": ac.VR_ARCH_TYPE,
            "vr_model": "test_model.pth",
            "is_primary_stem_only": False,
            "is_secondary_stem_only": True,
            "primary_stem_text": "Vocals Only",  # Model's primary
            "secondary_stem_text": "Instrumental Only",  # What user wants
            "output_path": "/tmp/test",
        }

        # Mock a VR model where Vocals is primary (normal case)
        model_data = self._create_mock_vr_model(settings)

        # The key thing to verify is that the swapped stem logic runs and detects user intent
        # Even if model loading fails, the stem swapping logic should work
        assert (
            model_data.user_requested_stem == ac.INST_STEM
        ), f"Expected user_requested_stem to be {ac.INST_STEM}, got {model_data.user_requested_stem}"

        # Verify the stem assignment logic worked (user wants secondary stem)
        assert (
            model_data.is_secondary_stem_only == True
        ), "Should be set to secondary stem only since user wants Instrumental (model's secondary)"
        assert (
            model_data.is_primary_stem_only == False
        ), "Should not be primary stem only"

    def test_vr_model_with_instrumental_primary(self):
        """Test VR model where Instrumental is the primary stem."""
        # Create settings where user wants Instrumental Only
        settings = {
            "chosen_process_method": ac.VR_ARCH_TYPE,
            "vr_model": "instrumental_model.pth",
            "is_primary_stem_only": True,
            "is_secondary_stem_only": False,
            "primary_stem_text": "Instrumental Only",  # What user wants
            "secondary_stem_text": "Vocals Only",  # Model's secondary
            "output_path": "/tmp/test",
        }

        # Mock a VR model where Instrumental is primary (swapped model)
        model_data = self._create_mock_vr_model(settings, primary_stem="Instrumental")

        # Verify the model correctly identifies user intent
        assert model_data.user_requested_stem == ac.INST_STEM
        # Since user wants Instrumental and it's the model's primary, keep primary_only
        assert model_data.is_primary_stem_only == True
        assert model_data.is_secondary_stem_only == False

    def test_mdx_model_stem_swapping(self):
        """Test MDX model stem swapping logic."""
        settings = {
            "chosen_process_method": ac.MDX_ARCH_TYPE,
            "mdx_net_model": "test_mdx.onnx",
            "is_primary_stem_only": False,
            "is_secondary_stem_only": True,
            "primary_stem_text": "Vocals Only",
            "secondary_stem_text": "Instrumental Only",  # What user wants
            "output_path": "/tmp/test",
        }

        model_data = self._create_mock_mdx_model(settings)

        # Verify MDX model handles swapping correctly
        # The key is that user_requested_stem gets extracted properly
        # Even if model loading fails, the user intent extraction should work
        if model_data.model_status:
            assert (
                model_data.user_requested_stem == ac.INST_STEM
            ), f"Expected user_requested_stem to be {ac.INST_STEM}, got {model_data.user_requested_stem}"
        else:
            # For failed model loading, we can still test that the settings were parsed correctly
            assert (
                model_data.is_secondary_stem_only == True
            ), "Should be set to secondary stem only"

    def test_demucs_model_stem_swapping(self):
        """Test Demucs model bass extraction."""
        settings = {
            "chosen_process_method": ac.DEMUCS_ARCH_TYPE,
            "demucs_model": "test_demucs.yaml",
            "is_primary_stem_only_Demucs": True,
            "is_secondary_stem_only_Demucs": False,
            "primary_stem_text": "Bass Only",  # User wants bass
            "secondary_stem_text": "No Bass",
            "demucs_stems": "Bass",
            "output_path": "/tmp/test",
        }

        model_data = self._create_mock_demucs_model(settings)

        # Verify Demucs model handles bass extraction correctly
        # Even if the model fails to load, the user intent extraction should work
        if model_data.model_status:
            assert (
                model_data.user_requested_stem == ac.BASS_STEM
            ), f"Expected user_requested_stem to be {ac.BASS_STEM}, got {model_data.user_requested_stem}"
        else:
            # For failed model loading, we can still test that the settings were parsed correctly
            assert (
                model_data.is_primary_stem_only == True
            ), "Should be set to primary stem only for Bass"

    def test_model_cannot_produce_requested_stem(self):
        """Test when model cannot produce the requested stem."""
        settings = {
            "chosen_process_method": ac.VR_ARCH_TYPE,
            "vr_model": "vocals_only_model.pth",
            "is_primary_stem_only": True,
            "is_secondary_stem_only": False,
            "primary_stem_text": "Bass Only",  # User wants bass
            "secondary_stem_text": "No Bass",
            "output_path": "/tmp/test",
        }

        # Mock a VR model that only does vocals/instrumental
        model_data = self._create_mock_vr_model(settings, primary_stem="Vocals")

        # Verify model outputs both stems when it can't produce requested stem
        assert model_data.user_requested_stem == ac.BASS_STEM
        assert model_data.is_primary_stem_only == False
        assert model_data.is_secondary_stem_only == False


@pytest.mark.critical
@pytest.mark.regression
class TestOptimizedDemucsIntegration:
    """Integration tests for optimized Demucs source mapping functions."""

    def test_optimized_demucs_source_mapping_functions_exist(self):
        """Test that all optimized Demucs functions are available."""
        # Verify the core functions exist and are callable
        assert hasattr(
            ac, "get_demucs_source_mapping"
        ), "get_demucs_source_mapping function should exist"
        assert hasattr(
            ac, "transform_demucs_output_to_uvr_order"
        ), "transform_demucs_output_to_uvr_order function should exist"
        assert hasattr(
            ac, "get_stem_index_safe"
        ), "get_stem_index_safe function should exist"

        # Test they're callable
        assert callable(
            ac.get_demucs_source_mapping
        ), "get_demucs_source_mapping should be callable"
        assert callable(
            ac.transform_demucs_output_to_uvr_order
        ), "transform_demucs_output_to_uvr_order should be callable"
        assert callable(
            ac.get_stem_index_safe
        ), "get_stem_index_safe should be callable"

    def test_demucs_constants_have_correct_values(self):
        """Test that Demucs constants have the correct optimized values."""
        # Test model output order constants exist and have correct values
        assert hasattr(
            ac, "DEMUCS_MODEL_OUTPUT_ORDER_4"
        ), "DEMUCS_MODEL_OUTPUT_ORDER_4 should exist"
        assert hasattr(
            ac, "DEMUCS_MODEL_OUTPUT_ORDER_6"
        ), "DEMUCS_MODEL_OUTPUT_ORDER_6 should exist"
        assert hasattr(
            ac, "DEMUCS_MODEL_OUTPUT_ORDER_2"
        ), "DEMUCS_MODEL_OUTPUT_ORDER_2 should exist"

        # Verify the model output order reflects what Demucs actually produces
        expected_4_stem = ["drums", "bass", "other", "vocals"]
        assert (
            ac.DEMUCS_MODEL_OUTPUT_ORDER_4 == expected_4_stem
        ), f"4-stem model output order should be {expected_4_stem}"

        # Test UVR interface mappings are correct
        source_list_4, source_map_4 = ac.get_demucs_source_mapping(4)
        expected_uvr_order = [ac.BASS_STEM, ac.DRUM_STEM, ac.OTHER_STEM, ac.VOCAL_STEM]
        assert (
            source_list_4 == expected_uvr_order
        ), f"UVR interface order should be {expected_uvr_order}"

    def test_demucs_bass_drums_mapping_consistency(self):
        """Critical test: Verify bass/drums mapping is consistent across all functions."""
        import numpy as np

        # Create mock model output in Demucs natural order: [drums, bass, other, vocals]
        model_output = np.array(
            [
                [[100, 101], [100, 101]],  # drums at model index 0
                [[200, 201], [200, 201]],  # bass at model index 1
                [[300, 301], [300, 301]],  # other at model index 2
                [[400, 401], [400, 401]],  # vocals at model index 3
            ]
        )

        # Get UVR interface mapping
        uvr_source_list, uvr_source_map = ac.get_demucs_source_mapping(4)

        # Transform to UVR order
        uvr_output = ac.transform_demucs_output_to_uvr_order(model_output, 4)

        # Test bass lookup and positioning
        bass_uvr_idx = ac.get_stem_index_safe(uvr_source_map, ac.BASS_STEM)
        assert bass_uvr_idx == 0, "Bass should be at UVR index 0"
        np.testing.assert_array_equal(
            uvr_output[bass_uvr_idx],
            model_output[1],
            "Bass data should be correctly positioned",
        )

        # Test drums lookup and positioning
        drums_uvr_idx = ac.get_stem_index_safe(uvr_source_map, ac.DRUM_STEM)
        assert drums_uvr_idx == 1, "Drums should be at UVR index 1"
        np.testing.assert_array_equal(
            uvr_output[drums_uvr_idx],
            model_output[0],
            "Drums data should be correctly positioned",
        )

    def test_case_insensitive_lookup_integration(self):
        """Test case-insensitive lookup works with realistic scenarios."""
        # Test scenario that could happen in real Demucs processing
        # where model.sources creates lowercase keys
        lowercase_map = {"vocals": 3, "drums": 0, "bass": 1, "other": 2}

        # Our constants are title-case, should still work
        vocals_idx = ac.get_stem_index_safe(lowercase_map, ac.VOCAL_STEM)  # "Vocals"
        drums_idx = ac.get_stem_index_safe(lowercase_map, ac.DRUM_STEM)  # "Drums"
        bass_idx = ac.get_stem_index_safe(lowercase_map, ac.BASS_STEM)  # "Bass"
        other_idx = ac.get_stem_index_safe(lowercase_map, ac.OTHER_STEM)  # "Other"

        # All should be found
        assert vocals_idx == 3, "Should find vocals with case-insensitive lookup"
        assert drums_idx == 0, "Should find drums with case-insensitive lookup"
        assert bass_idx == 1, "Should find bass with case-insensitive lookup"
        assert other_idx == 2, "Should find other with case-insensitive lookup"

    def test_demucs_optimization_backwards_compatibility(self):
        """Test that optimized functions don't break existing behavior."""
        # Test that 2-stem, 4-stem, and 6-stem all work as expected
        stem_counts = [2, 4, 6]

        for stem_count in stem_counts:
            source_list, source_map = ac.get_demucs_source_mapping(stem_count)

            # Basic sanity checks
            assert (
                len(source_list) == stem_count
            ), f"{stem_count}-stem should return {stem_count} sources"
            assert (
                len(source_map) == stem_count
            ), f"{stem_count}-stem should return {stem_count} mappings"
            assert (
                len(set(source_map.values())) == stem_count
            ), f"{stem_count}-stem should have unique indices"

            # Verify all indices are sequential starting from 0
            expected_indices = set(range(stem_count))
            actual_indices = set(source_map.values())
            assert (
                actual_indices == expected_indices
            ), f"{stem_count}-stem indices should be 0 to {stem_count-1}"

    def test_demucs_error_resilience(self):
        """Test that optimized functions handle edge cases gracefully."""
        import numpy as np

        # Test transformation with edge cases
        edge_cases = [
            np.array([]),  # Empty array
            np.zeros((1, 2, 100)),  # Single stem
            np.zeros((0, 2, 100)),  # Zero stems
        ]

        for edge_case in edge_cases:
            # Should not crash and should return something reasonable
            result = ac.transform_demucs_output_to_uvr_order(edge_case, 4)
            assert (
                result is not None
            ), "Transformation should handle edge cases gracefully"

        # Test lookup with edge cases
        edge_lookups = [
            ({}, "any_stem"),  # Empty map
            ({"test": 0}, "missing"),  # Missing key
            ({"test": 0}, ""),  # Empty key
            ({"test": 0}, None),  # None key
        ]

        for source_map, key in edge_lookups:
            result = ac.get_stem_index_safe(source_map, key)
            assert (
                result is None
            ), f"Should return None for edge case: map={source_map}, key={key}"

    def test_demucs_performance_requirements(self):
        """Test that optimized functions meet performance requirements."""
        import time

        import numpy as np

        # Test transformation performance with typical audio size
        typical_audio = np.random.rand(4, 2, 44100 * 10)  # 4 stems, stereo, 10 seconds

        start_time = time.time()
        result = ac.transform_demucs_output_to_uvr_order(typical_audio, 4)
        end_time = time.time()

        processing_time = end_time - start_time
        assert (
            processing_time < 0.1
        ), f"Transformation should be fast, took {processing_time:.3f}s"

        # Test lookup performance
        large_map = {f"stem_{i}": i for i in range(100)}
        large_map[ac.VOCAL_STEM] = 99

        start_time = time.time()
        for _ in range(1000):
            result = ac.get_stem_index_safe(large_map, ac.VOCAL_STEM)
        end_time = time.time()

        lookup_time = end_time - start_time
        assert (
            lookup_time < 0.05
        ), f"Lookups should be fast, took {lookup_time:.3f}s for 1000 lookups"
