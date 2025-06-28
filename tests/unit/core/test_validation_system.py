"""Tests for the streamlined validation system."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

from src.uvr_pyside6_ui.core.validation_manager import (
    BasicFileValidator,
    ModelOutputValidator,
    ValidationCategory,
    ValidationManager,
    ValidationResult,
    ValidationSeverity,
)


@pytest.mark.unit
@pytest.mark.validation
class TestBasicFileValidator:
    """Test cases for BasicFileValidator - simple file checks only."""

    def test_nonexistent_file_validation(self):
        """Test validation of non-existent files."""
        result = BasicFileValidator.validate_file_path("/nonexistent/path/file.wav")

        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.PATH_VALIDATION
        assert "not found" in result.message.lower()
        assert not result.can_proceed

    def test_empty_file_validation(self):
        """Test validation of empty files."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            # File is empty by default

        try:
            result = BasicFileValidator.validate_file_path(temp_path)

            assert not result.is_valid
            assert result.severity == ValidationSeverity.ERROR
            assert result.category == ValidationCategory.AUDIO_INTEGRITY
            assert "empty" in result.message.lower()
            assert not result.can_proceed

        finally:
            temp_path.unlink(missing_ok=True)

    def test_valid_file_validation(self):
        """Test validation of accessible files."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data" + b"\x00" * 1000)

        try:
            result = BasicFileValidator.validate_file_path(temp_path)

            assert result.is_valid
            assert result.severity == ValidationSeverity.INFO
            assert result.category == ValidationCategory.PATH_VALIDATION
            assert "accessible" in result.message.lower()
            assert result.can_proceed
            assert "librosa" in " ".join(result.suggestions).lower()

        finally:
            temp_path.unlink(missing_ok=True)


@pytest.mark.unit
@pytest.mark.validation
class TestModelOutputValidator:
    """Test cases for ModelOutputValidator - the real value provider."""

    def test_none_output_validation(self):
        """Test validation of None model output."""
        result = ModelOutputValidator.validate_model_output(None, "TestModel", "Vocals")

        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "no output" in result.message.lower()
        assert not result.can_proceed

    def test_empty_output_validation(self):
        """Test validation of empty model output."""
        empty_audio = np.array([])

        result = ModelOutputValidator.validate_model_output(
            empty_audio, "TestModel", "Vocals"
        )

        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "empty output" in result.message.lower()
        assert not result.can_proceed

    def test_invalid_dimensions_validation(self):
        """Test validation of invalid audio dimensions."""
        invalid_audio = np.random.random((2, 3, 4, 5))  # 4D array

        result = ModelOutputValidator.validate_model_output(
            invalid_audio, "TestModel", "Vocals"
        )

        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert (
            "invalid" in result.message.lower()
            and "dimensions" in result.message.lower()
        )
        assert not result.can_proceed

    def test_nan_values_validation(self):
        """Test validation of output with NaN values."""
        nan_audio = np.array([1.0, 2.0, np.nan, 4.0])

        result = ModelOutputValidator.validate_model_output(
            nan_audio, "TestModel", "Vocals"
        )

        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "invalid data" in result.message.lower()
        assert not result.can_proceed

    def test_infinite_values_validation(self):
        """Test validation of output with infinite values."""
        inf_audio = np.array([1.0, 2.0, np.inf, 4.0])

        result = ModelOutputValidator.validate_model_output(
            inf_audio, "TestModel", "Vocals"
        )

        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "infinite values" in result.message.lower()
        assert not result.can_proceed

    def test_silent_output_validation(self):
        """Test validation of silent model output."""
        silent_audio = np.zeros(44100) + 1e-10  # Essentially silent

        result = ModelOutputValidator.validate_model_output(
            silent_audio, "TestModel", "Vocals"
        )

        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "silent output" in result.message.lower()
        assert not result.can_proceed

    def test_clipping_validation(self):
        """Test validation of clipped audio output."""
        # Create audio with severe clipping (5% of samples)
        clipped_audio = np.random.random(1000) * 0.8
        clipped_audio[::20] = 1.0  # Every 20th sample is clipped

        result = ModelOutputValidator.validate_model_output(
            clipped_audio, "TestModel", "Vocals"
        )

        assert not result.is_valid  # >1% clipping is invalid
        assert result.severity == ValidationSeverity.ERROR
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "clipping" in result.message.lower()
        assert not result.can_proceed

    def test_minor_clipping_validation(self):
        """Test validation of audio with minor clipping."""
        # Create audio with minor clipping (0.5% of samples)
        clipped_audio = np.random.random(1000) * 0.8
        clipped_audio[::200] = 1.0  # Every 200th sample is clipped (0.5%)

        result = ModelOutputValidator.validate_model_output(
            clipped_audio, "TestModel", "Vocals"
        )

        assert result.is_valid  # <1% clipping is acceptable
        assert result.severity == ValidationSeverity.WARNING
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "clipping" in result.message.lower()
        assert result.can_proceed

    def test_low_dynamic_range_validation(self):
        """Test validation of audio with low dynamic range."""
        # Create heavily compressed audio (low dynamic range)
        compressed_audio = np.random.random(44100) * 0.01 + 0.5  # Very compressed

        result = ModelOutputValidator.validate_model_output(
            compressed_audio, "TestModel", "Vocals"
        )

        assert result.is_valid
        assert result.severity == ValidationSeverity.WARNING
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "dynamic range" in result.message.lower()
        assert result.can_proceed

    def test_valid_output_validation(self):
        """Test validation of good quality model output."""
        # Create good quality audio with proper dynamic range
        # Use a sine wave with varying amplitude to ensure good dynamic range

        time_points = np.linspace(0, 1, 44100)
        base_signal = np.sin(2 * np.pi * 440 * time_points)  # 440 Hz sine wave
        envelope = np.sin(2 * np.pi * 2 * time_points) * 0.5 + 0.5  # 2 Hz envelope
        valid_audio = base_signal * envelope * 0.2  # Scale to reasonable level

        result = ModelOutputValidator.validate_model_output(
            valid_audio, "TestModel", "Vocals"
        )

        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
        assert result.category == ValidationCategory.MODEL_OUTPUT
        assert "validated" in result.message.lower()
        assert result.can_proceed
        assert len(result.suggestions) > 0


@pytest.mark.unit
@pytest.mark.validation
class TestValidationManager:
    """Test cases for the streamlined ValidationManager."""

    def test_validation_manager_initialization(self):
        """Test ValidationManager initialization."""
        manager = ValidationManager()

        assert hasattr(manager, "validation_completed")
        assert hasattr(manager, "validation_progress")
        assert hasattr(manager, "file_validator")
        assert hasattr(manager, "output_validator")

    def test_file_path_validation_signal(self):
        """Test that file path validation emits signals."""
        manager = ValidationManager()

        # Mock the signal
        manager.validation_completed = Mock()
        manager.validation_progress = Mock()

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            result = manager.validate_file_path(temp_path)

            # Check that signals were emitted
            manager.validation_progress.emit.assert_called()
            manager.validation_completed.emit.assert_called()

            # Check result
            assert isinstance(result, ValidationResult)

        finally:
            temp_path.unlink(missing_ok=True)

    def test_batch_files_validation(self):
        """Test validation of multiple file paths."""
        manager = ValidationManager()

        # Create multiple temporary files
        temp_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f"_test_{i}.wav", delete=False
            )
            temp_file.write(b"fake audio data")
            temp_files.append(Path(temp_file.name))
            temp_file.close()

        try:
            results = manager.validate_batch_files(temp_files)

            assert len(results) == 3
            assert all(isinstance(result, ValidationResult) for result in results)
            assert all(result.is_valid for result in results)

        finally:
            for temp_file in temp_files:
                temp_file.unlink(missing_ok=True)

    def test_model_output_validation_signal(self):
        """Test that model output validation emits signals."""
        manager = ValidationManager()

        # Mock the signals
        manager.validation_completed = Mock()
        manager.validation_progress = Mock()

        # Test with valid audio
        valid_audio = np.random.random(1000) * 0.5

        result = manager.validate_model_output(valid_audio, "TestModel", "Vocals")

        # Check that signals were emitted
        manager.validation_progress.emit.assert_called()
        manager.validation_completed.emit.assert_called()

        # Check result
        assert isinstance(result, ValidationResult)

    def test_validation_summary(self):
        """Test validation summary generation."""
        manager = ValidationManager()

        # Create mock results with different severities
        results = [
            ValidationResult(
                True,
                ValidationSeverity.INFO,
                ValidationCategory.MODEL_OUTPUT,
                "Good",
                "Details",
                [],
            ),
            ValidationResult(
                True,
                ValidationSeverity.WARNING,
                ValidationCategory.MODEL_OUTPUT,
                "Warning",
                "Details",
                [],
            ),
            ValidationResult(
                False,
                ValidationSeverity.ERROR,
                ValidationCategory.MODEL_OUTPUT,
                "Error",
                "Details",
                [],
            ),
        ]

        summary = manager.get_validation_summary(results)

        assert summary["total"] == 3
        assert summary["valid"] == 2
        assert summary["warnings"] == 1
        assert summary["errors"] == 1


@pytest.mark.integration
@pytest.mark.validation
class TestValidationIntegration:
    """Integration tests for the streamlined validation system."""

    def test_model_output_validation_workflow(self):
        """Test complete model output validation workflow."""
        manager = ValidationManager()

        # Test with realistic model output
        audio_data = np.random.random(44100) * 0.3  # 1 second of audio

        result = manager.validate_model_output(audio_data, "UVR-MDX", "Vocals")

        # Should pass validation for realistic output
        assert result.is_valid
        assert result.can_proceed
        assert result.severity in [
            ValidationSeverity.INFO,
            ValidationSeverity.WARNING,
        ]

    def test_validation_error_resilience(self):
        """Test that validation system handles errors gracefully."""
        manager = ValidationManager()

        # Test with completely invalid input
        result = manager.validate_file_path("/nonexistent/path/file.wav")

        assert not result.is_valid
        assert not result.can_proceed
        assert len(result.suggestions) > 0
        assert result.technical_details != ""

    def test_validation_performance(self):
        """Test validation performance doesn't significantly impact processing."""
        import time

        manager = ValidationManager()

        # Test model output validation performance
        large_audio = np.random.random(441000) * 0.5  # 10 seconds of audio

        start_time = time.time()
        result = manager.validate_model_output(large_audio, "TestModel", "Vocals")
        validation_time = time.time() - start_time

        # Validation should complete quickly (under 100ms for 10s of audio)
        assert validation_time < 0.1
        assert result.is_valid


@pytest.mark.regression
@pytest.mark.validation
class TestValidationRegression:
    """Regression tests for the streamlined validation system."""

    def test_validation_preserves_audio_processing_flow(self):
        """Ensure validation doesn't break existing audio processing."""
        manager = ValidationManager()

        # Test various audio formats and conditions that should work
        test_cases = [
            (np.random.random(44100) * 0.5, "Normal audio"),
            (np.random.random((2, 44100)) * 0.3, "Stereo audio"),
            (np.random.random(88200) * 0.8, "Longer audio"),
        ]

        for audio_data, description in test_cases:
            result = manager.validate_model_output(audio_data, "TestModel", "Vocals")

            # All these should be valid
            assert result.can_proceed, f"Failed for {description}: {result.message}"

    def test_validation_error_messages_are_helpful(self):
        """Ensure validation error messages provide actionable guidance."""
        manager = ValidationManager()

        # Test various error conditions
        error_cases = [
            (np.array([]), "Empty output"),
            (np.array([np.nan, 1, 2]), "NaN values"),
            (np.array([np.inf, 1, 2]), "Infinite values"),
            (np.zeros(1000), "Silent output"),
        ]

        for audio_data, description in error_cases:
            result = manager.validate_model_output(audio_data, "TestModel", "Vocals")

            assert not result.can_proceed, f"Should fail for {description}"
            assert len(result.suggestions) > 0, f"No suggestions for {description}"
            assert (
                result.technical_details != ""
            ), f"No technical details for {description}"

            # Check that suggestions are actionable (contain verbs)
            action_words = ["try", "check", "use", "consider", "ensure", "verify"]
            suggestions_text = " ".join(result.suggestions).lower()
            assert any(
                word in suggestions_text for word in action_words
            ), f"Suggestions not actionable for {description}: {result.suggestions}"

    def test_streamlined_validation_is_faster(self):
        """Test that streamlined validation is faster than comprehensive validation."""
        import time

        manager = ValidationManager()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data" * 1000)

        try:
            # Time the streamlined file validation
            start_time = time.time()
            result = manager.validate_file_path(temp_path)
            validation_time = time.time() - start_time

            # Should be very fast (basic file checks only)
            assert validation_time < 0.01  # Less than 10ms
            assert result.is_valid

        finally:
            temp_path.unlink(missing_ok=True)
