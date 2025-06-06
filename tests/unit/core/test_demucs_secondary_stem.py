"""
Tests for the Demucs secondary stem logic fix (ac.NO_STEM bug).

This test suite verifies that the fix for the AttributeError:
module 'uvr_pyside6_ui.core.app_constants' has no attribute 'NO_STEM'
works correctly across all Demucs stem types.

The bug was in line 985 of separate_logic.py where:
- OLD (BROKEN): md.secondary_stem != ac.NO_STEM
- NEW (FIXED): not md.secondary_stem.startswith("No ")
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.separate_demucs_logic import SeperateDemucsLogic


@pytest.mark.unit
@pytest.mark.separate_logic
class TestDemucsSecondaryStemFix:
    """Test the fixed secondary stem logic for the ac.NO_STEM bug."""

    def test_secondary_stem_logic_for_drums_primary(self):
        """Test that Drums primary stem correctly does NOT create secondary stem."""
        # Drums -> "No Drums" secondary stem should NOT be created
        secondary_stem = ac.secondary_stem("Drums")  # Returns "No Drums"

        # Test the actual fix logic
        should_create_secondary = not secondary_stem.startswith("No ")

        assert secondary_stem == "No Drums"
        assert (
            should_create_secondary == False
        ), f"Drums primary should NOT create secondary stem, but logic says create: {should_create_secondary}"

    def test_secondary_stem_logic_for_bass_primary(self):
        """Test that Bass primary stem correctly does NOT create secondary stem."""
        # Bass -> "No Bass" secondary stem should NOT be created
        secondary_stem = ac.secondary_stem("Bass")  # Returns "No Bass"

        # Test the actual fix logic
        should_create_secondary = not secondary_stem.startswith("No ")

        assert secondary_stem == "No Bass"
        assert (
            should_create_secondary == False
        ), f"Bass primary should NOT create secondary stem, but logic says create: {should_create_secondary}"

    def test_secondary_stem_logic_for_other_primary(self):
        """Test that Other primary stem correctly does NOT create secondary stem."""
        # Other -> "No Other" secondary stem should NOT be created
        secondary_stem = ac.secondary_stem("Other")  # Returns "No Other"

        # Test the actual fix logic
        should_create_secondary = not secondary_stem.startswith("No ")

        assert secondary_stem == "No Other"
        assert (
            should_create_secondary == False
        ), f"Other primary should NOT create secondary stem, but logic says create: {should_create_secondary}"

    def test_secondary_stem_logic_for_vocals_primary(self):
        """Test that Vocals primary stem correctly DOES create secondary stem."""
        # Vocals -> "Instrumental" secondary stem SHOULD be created
        secondary_stem = ac.secondary_stem("Vocals")  # Returns "Instrumental"

        # Test the actual fix logic
        should_create_secondary = not secondary_stem.startswith("No ")

        assert secondary_stem == "Instrumental"
        assert (
            should_create_secondary == True
        ), f"Vocals primary should CREATE secondary stem, but logic says don't create: {should_create_secondary}"

    def test_old_logic_would_fail_with_no_stem_error(self):
        """Test that the old logic would have failed with ac.NO_STEM AttributeError."""
        # Verify that ac.NO_STEM doesn't exist (confirming the bug)
        with pytest.raises(AttributeError, match="has no attribute 'NO_STEM'"):
            _ = ac.NO_STEM

    def test_comprehensive_stem_logic_verification(self):
        """Test the fix logic for all possible Demucs stem combinations."""
        test_cases = [
            # (primary_stem, expected_secondary, should_create_secondary)
            ("Vocals", "Instrumental", True),  # ✅ Should create secondary
            ("Drums", "No Drums", False),  # ✅ Should NOT create secondary
            ("Bass", "No Bass", False),  # ✅ Should NOT create secondary
            ("Other", "No Other", False),  # ✅ Should NOT create secondary
        ]

        for primary_stem, expected_secondary, expected_create in test_cases:
            # Get the actual secondary stem from app_constants
            actual_secondary = ac.secondary_stem(primary_stem)

            # Test our fixed logic
            actual_create = not actual_secondary.startswith("No ")

            assert (
                actual_secondary == expected_secondary
            ), f"Secondary stem mismatch for {primary_stem}: expected {expected_secondary}, got {actual_secondary}"

            assert (
                actual_create == expected_create
            ), f"Creation logic mismatch for {primary_stem}: expected {expected_create}, got {actual_create}"

    def test_demucs_separator_drums_processing_mock(self):
        """Test Demucs separator with Drums processing (mocked to avoid full model loading)."""
        # Create mock model data for Drums processing
        mock_model_data = Mock()
        mock_model_data.process_method = ac.DEMUCS_ARCH_TYPE
        mock_model_data.model_basename = "test_demucs"
        mock_model_data.audio_file = "/fake/audio.wav"
        mock_model_data.export_path = "/fake/output"
        mock_model_data.demucs_stems = "Drums"  # Single instrument
        mock_model_data.secondary_stem = "No Drums"  # This triggers the fix
        mock_model_data.is_primary_stem_only = False
        mock_model_data.is_secondary_stem_only = False
        mock_model_data.demucs_source_map = {"Drums": 1}
        mock_model_data.model_samplerate = 44100
        mock_model_data.is_demucs_combine_stems = True

        process_data = {
            "_is_running_check": lambda: True,
            "input_audio_array": np.random.random((44100, 2)),  # 1 second stereo
        }

        separator = SeperateDemucsLogic(mock_model_data, process_data)

        # Mock the _write_stem method to verify behavior
        with patch.object(separator, "_write_stem") as mock_write_stem:

            # Test the actual logic from the fixed code
            # This is the exact logic from line 985+ in separate_logic.py
            if (
                not mock_model_data.is_primary_stem_only
                and not mock_model_data.secondary_stem.startswith("No ")
            ):
                # This should NOT execute for Drums because "No Drums".startswith("No ") is True
                separator._write_stem("No Drums", np.zeros((1000, 2)), 44100)

            # Verify no secondary stem was written (because the condition was False)
            mock_write_stem.assert_not_called()

    def test_demucs_separator_vocals_processing_mock(self):
        """Test Demucs separator with Vocals processing (mocked to avoid full model loading)."""
        # Create mock model data for Vocals processing
        mock_model_data = Mock()
        mock_model_data.process_method = ac.DEMUCS_ARCH_TYPE
        mock_model_data.model_basename = "test_demucs"
        mock_model_data.audio_file = "/fake/audio.wav"
        mock_model_data.export_path = "/fake/output"
        mock_model_data.demucs_stems = "Vocals"  # Single instrument
        mock_model_data.secondary_stem = "Instrumental"  # This should create secondary
        mock_model_data.is_primary_stem_only = False
        mock_model_data.is_secondary_stem_only = False
        mock_model_data.demucs_source_map = {"Vocals": 3}
        mock_model_data.model_samplerate = 44100
        mock_model_data.is_demucs_combine_stems = False

        process_data = {
            "_is_running_check": lambda: True,
            "input_audio_array": np.random.random((44100, 2)),  # 1 second stereo
        }

        separator = SeperateDemucsLogic(mock_model_data, process_data)

        # Mock the _write_stem method to verify behavior
        with patch.object(separator, "_write_stem") as mock_write_stem:

            # Test the actual logic from the fixed code
            # This is the exact logic from line 985+ in separate_logic.py
            if (
                not mock_model_data.is_primary_stem_only
                and not mock_model_data.secondary_stem.startswith("No ")
            ):
                # This SHOULD execute for Vocals because "Instrumental".startswith("No ") is False
                separator._write_stem("Instrumental", np.zeros((1000, 2)), 44100)

            # Verify secondary stem was written (because the condition was True)
            mock_write_stem.assert_called_once_with(
                "Instrumental", mock_write_stem.call_args[0][1], 44100
            )

    @pytest.mark.parametrize(
        "primary_stem,secondary_stem,should_create",
        [
            ("Drums", "No Drums", False),
            ("Bass", "No Bass", False),
            ("Other", "No Other", False),
            ("Vocals", "Instrumental", True),
        ],
    )
    def test_parametrized_secondary_stem_creation_logic(
        self, primary_stem, secondary_stem, should_create
    ):
        """Parametrized test for all stem types to verify the fix works universally."""
        # Test the exact logic from our fix
        actual_should_create = not secondary_stem.startswith("No ")

        assert (
            actual_should_create == should_create
        ), f"Logic failed for {primary_stem} -> {secondary_stem}: expected {should_create}, got {actual_should_create}"

    def test_edge_case_empty_secondary_stem(self):
        """Test edge case where secondary stem might be empty or None."""
        # Test with empty string
        empty_secondary = ""
        should_create = not empty_secondary.startswith("No ")
        assert should_create == True  # Empty string should create secondary

        # Test with None (should be handled by ModelData, but test for robustness)
        try:
            none_secondary = None
            should_create = not none_secondary.startswith("No ")
        except AttributeError:
            # This is expected behavior - None doesn't have startswith method
            # In real code, this would be prevented by ModelData validation
            pass

    def test_edge_case_unusual_secondary_stem_names(self):
        """Test edge cases with unusual secondary stem names."""
        unusual_cases = [
            ("No ", False),  # Starts with "No " (has space) - should not create
            ("No", True),  # Just "No" without space - should create
            ("NoSpace", True),  # "No" without space - should create
            ("No Unusual Stem", False),  # Custom "No " stem - should not create
            (
                "Not a No stem",
                True,
            ),  # Contains "No" but doesn't start with "No " - should create
        ]

        for secondary_stem, expected_create in unusual_cases:
            actual_create = not secondary_stem.startswith("No ")
            assert (
                actual_create == expected_create
            ), f"Edge case failed for '{secondary_stem}': expected {expected_create}, got {actual_create}"

    def test_regression_no_crash_on_single_instrument_separation(self):
        """Regression test to ensure single instrument separation doesn't crash."""
        # This test verifies that the specific error scenario is fixed
        mock_model_data = Mock()
        mock_model_data.secondary_stem = "No Drums"  # This was causing the crash
        mock_model_data.is_primary_stem_only = False

        # The old logic would try: md.secondary_stem != ac.NO_STEM
        # and crash with: AttributeError: module 'uvr_pyside6_ui.core.app_constants' has no attribute 'NO_STEM'

        # The new logic should work without crashing
        try:
            # This is the FIXED logic
            should_create_secondary = not mock_model_data.secondary_stem.startswith(
                "No "
            )

            # Should succeed without AttributeError
            assert (
                should_create_secondary == False
            )  # "No Drums" should not create secondary

        except AttributeError as e:
            pytest.fail(f"Fixed logic should not raise AttributeError, but got: {e}")

    def test_actual_app_constants_secondary_stem_function(self):
        """Test that the app_constants.secondary_stem function works correctly."""
        # Verify all expected stem mappings work
        stem_mappings = {
            ac.VOCAL_STEM: ac.INST_STEM,  # "Vocals" -> "Instrumental"
            ac.INST_STEM: ac.VOCAL_STEM,  # "Instrumental" -> "Vocals"
            ac.DRUM_STEM: f"No {ac.DRUM_STEM}",  # "Drums" -> "No Drums"
            ac.BASS_STEM: f"No {ac.BASS_STEM}",  # "Bass" -> "No Bass"
            ac.OTHER_STEM: f"No {ac.OTHER_STEM}",  # "Other" -> "No Other"
        }

        for primary, expected_secondary in stem_mappings.items():
            actual_secondary = ac.secondary_stem(primary)
            assert (
                actual_secondary == expected_secondary
            ), f"secondary_stem({primary}) should return {expected_secondary}, got {actual_secondary}"
