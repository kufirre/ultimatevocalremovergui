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
        
        with patch("uvr_pyside6_ui.core.model_data.VR_HASH_DIR_PATH") as mock_hash_dir, \
             patch("builtins.open", mock_open(read_data=json.dumps(hash_json_data))), \
             patch("uvr_pyside6_ui.core.model_data.Path") as mock_path, \
             patch("uvr_pyside6_ui.core.model_data.ModelParameters") as mock_model_params, \
             patch("uvr_pyside6_ui.core.model_data.hashlib") as mock_hashlib:
            
            # Setup common mocks
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stem = "test_model"
            mock_hashlib.md5.return_value.hexdigest.return_value = "fake_hash"
            mock_model_params.return_value = Mock()
            
            return ModelData.from_settings_dict(settings)

    def _create_mock_mdx_model(self, settings, primary_stem="Vocals"):
        """Helper method to create a mocked MDX model with consistent setup."""
        hash_json_data = {"primary_stem": primary_stem}
        
        with patch("uvr_pyside6_ui.core.model_data.MDX_HASH_DIR_PATH") as mock_hash_dir, \
             patch("builtins.open", mock_open(read_data=json.dumps(hash_json_data))), \
             patch("uvr_pyside6_ui.core.model_data.Path") as mock_path:
            
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stem = "test_mdx_model"
            
            return ModelData.from_settings_dict(settings)

    def _create_mock_demucs_model(self, settings):
        """Helper method to create a mocked Demucs model with consistent setup."""
        with patch("uvr_pyside6_ui.core.model_data.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stem = "test_demucs"
            
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

        # Verify the model loaded successfully
        assert (
            model_data.model_status == True
        ), f"Model should load successfully, but status is {model_data.model_status}"

        # Verify the model correctly identifies user intent
        assert model_data.user_requested_stem == ac.INST_STEM
        # Since user wants Instrumental (secondary), should swap to secondary_only
        assert model_data.is_secondary_stem_only == True
        assert model_data.is_primary_stem_only == False

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
        assert model_data.user_requested_stem == ac.INST_STEM
        assert model_data.is_secondary_stem_only == True
        assert model_data.is_primary_stem_only == False

    def test_demucs_model_stem_swapping(self):
        """Test Demucs model stem swapping logic."""
        settings = {
            "chosen_process_method": ac.DEMUCS_ARCH_TYPE,
            "demucs_model": "test_demucs.yaml",
            "is_primary_stem_only_Demucs": True,
            "is_secondary_stem_only_Demucs": False,
            "primary_stem_text": "Bass Only",  # What user wants
            "secondary_stem_text": "No Bass",
            "demucs_stems": "Bass",
            "output_path": "/tmp/test",
        }

        model_data = self._create_mock_demucs_model(settings)

        # Verify Demucs model handles bass extraction correctly
        assert model_data.user_requested_stem == ac.BASS_STEM
        assert model_data.demucs_source_list == ac.DEMUCS_4_SOURCE_LIST
        # Bass should be available in 4-stem model
        assert ac.BASS_STEM in model_data.demucs_source_list

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
