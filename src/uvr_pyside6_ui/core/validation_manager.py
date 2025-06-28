"""
Streamlined validation system for UVR PySide6 application.

This module provides focused validation for model outputs and basic file validation,
prioritizing real user value over comprehensive but redundant checks.
"""

import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from PySide6.QtCore import QObject, Signal

from .logger_utils import get_logger

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """Validation result severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Validation categories for organizing checks."""

    AUDIO_INTEGRITY = "audio_integrity"
    FORMAT_COMPATIBILITY = "format_compatibility"
    MODEL_OUTPUT = "model_output"
    PATH_VALIDATION = "path_validation"


@dataclass
class ValidationResult:
    """Detailed validation result with user guidance."""

    is_valid: bool
    severity: ValidationSeverity
    category: ValidationCategory
    message: str
    technical_details: str
    suggestions: List[str]
    help_url: Optional[str] = None
    can_proceed: bool = True  # Whether processing can continue despite issues

    def __post_init__(self):
        """Set can_proceed based on severity."""
        if self.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.can_proceed = False


class BasicFileValidator:
    """Simple file validation - let librosa handle the heavy lifting."""

    @classmethod
    def validate_file_path(cls, file_path: Union[str, Path]) -> ValidationResult:
        """
        Basic file path validation. Librosa will handle format/content validation.

        Args:
            file_path: Path to audio file

        Returns:
            ValidationResult with basic path checks
        """
        file_path = Path(file_path)

        # File existence
        if not file_path.exists():
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.PATH_VALIDATION,
                message=f"Audio file not found: {file_path.name}",
                technical_details=f"File path does not exist: {file_path}",
                suggestions=[
                    "Check the file path is correct",
                    "Ensure the file hasn't been moved or deleted",
                    "Try selecting the file again",
                ],
            )

        # Basic size check (empty files)
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.AUDIO_INTEGRITY,
                    message=f"Audio file is empty: {file_path.name}",
                    technical_details="File size is 0 bytes",
                    suggestions=[
                        "Check if the file downloaded completely",
                        "Try re-exporting the audio file",
                        "Use a different audio file",
                    ],
                )
        except OSError as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.PATH_VALIDATION,
                message=f"Cannot access audio file: {file_path.name}",
                technical_details=f"OS error: {str(e)}",
                suggestions=[
                    "Check file permissions",
                    "Ensure the file is not being used by another application",
                ],
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            category=ValidationCategory.PATH_VALIDATION,
            message=f"File accessible: {file_path.name}",
            technical_details="Basic file validation passed",
            suggestions=["Librosa will handle format validation during loading"],
        )


class ModelOutputValidator:
    """Validation for model processing outputs - this provides real user value."""

    @classmethod
    def validate_model_output(
        cls,
        output_audio: np.ndarray,
        model_name: str,
        stem_name: str,
        expected_duration: Optional[float] = None,
    ) -> ValidationResult:
        """
        Validate model output audio for quality and integrity.

        Args:
            output_audio: Model output audio array
            model_name: Name of the model that produced the output
            stem_name: Name of the stem (e.g., "Vocals", "Instrumental")
            expected_duration: Expected duration in seconds (optional)

        Returns:
            ValidationResult with analysis
        """
        try:
            # Basic array validation
            if output_audio is None:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.MODEL_OUTPUT,
                    message=f"Model produced no output: {model_name} ({stem_name})",
                    technical_details="Output audio is None",
                    suggestions=[
                        "Model may have failed during processing",
                        "Check model file integrity",
                        "Try with a different audio file",
                        "Verify model compatibility",
                    ],
                )

            if output_audio.size == 0:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.MODEL_OUTPUT,
                    message=f"Model produced empty output: {model_name} ({stem_name})",
                    technical_details="Output audio array is empty",
                    suggestions=[
                        "Model processing may have failed",
                        "Input audio may be incompatible",
                        "Check model settings and parameters",
                    ],
                )

            # Shape validation
            if output_audio.ndim not in [1, 2]:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.MODEL_OUTPUT,
                    message=f"Invalid audio dimensions: {model_name} ({stem_name})",
                    technical_details=f"Audio shape: {output_audio.shape}, expected 1D or 2D array",
                    suggestions=[
                        "Model output format is incorrect",
                        "This may indicate a model compatibility issue",
                        "Try a different model or check model files",
                    ],
                )

            # Data integrity checks
            if np.any(np.isnan(output_audio)):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.MODEL_OUTPUT,
                    message=f"Model output contains invalid data: {model_name} ({stem_name})",
                    technical_details="Output contains NaN values",
                    suggestions=[
                        "Model processing encountered numerical errors",
                        "Input audio may be corrupted",
                        "Try different model settings",
                        "Check input audio quality",
                    ],
                )

            if np.any(np.isinf(output_audio)):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.MODEL_OUTPUT,
                    message=f"Model output contains infinite values: {model_name} ({stem_name})",
                    technical_details="Output contains infinite values",
                    suggestions=[
                        "Model processing encountered overflow errors",
                        "Try reducing input volume or gain",
                        "Check model compatibility with input format",
                    ],
                )

            # Audio quality analysis
            max_amplitude = np.max(np.abs(output_audio))
            rms_level = np.sqrt(np.mean(output_audio**2))

            # Check for silent output
            if max_amplitude < 1e-8:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.MODEL_OUTPUT,
                    message=f"Model produced silent output: {model_name} ({stem_name})",
                    technical_details=f"Maximum amplitude: {max_amplitude}, RMS: {rms_level}",
                    suggestions=[
                        "Model may not have detected the target stem",
                        "Input audio may not contain the target stem",
                        "Try adjusting model sensitivity settings",
                        "Consider using a different model",
                    ],
                )

            # Check for clipping
            clipping_threshold = 0.99
            clipped_samples = np.sum(np.abs(output_audio) > clipping_threshold)
            if clipped_samples > 0:
                clipping_percentage = (clipped_samples / output_audio.size) * 100
                severity = (
                    ValidationSeverity.ERROR
                    if clipping_percentage > 1
                    else ValidationSeverity.WARNING
                )

                return ValidationResult(
                    is_valid=clipping_percentage <= 1,  # Allow minor clipping
                    severity=severity,
                    category=ValidationCategory.MODEL_OUTPUT,
                    message=f"Audio clipping detected: {model_name} ({stem_name}) - {clipping_percentage:.2f}%",
                    technical_details=f"Clipped samples: {clipped_samples}/{output_audio.size}",
                    suggestions=[
                        "Output audio has excessive clipping/distortion",
                        "Try reducing input volume before processing",
                        "Enable normalization in output settings",
                        "Consider using a different model",
                    ],
                )

            # Dynamic range analysis
            if rms_level > 0:
                dynamic_range_db = 20 * np.log10(max_amplitude / rms_level)
                if dynamic_range_db < 6:  # Very compressed
                    return ValidationResult(
                        is_valid=True,
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.MODEL_OUTPUT,
                        message=f"Low dynamic range detected: {model_name} ({stem_name}) - {dynamic_range_db:.1f}dB",
                        technical_details=f"Dynamic range: {dynamic_range_db:.1f}dB, Max: {max_amplitude:.6f}, RMS: {rms_level:.6f}",
                        suggestions=[
                            "Output may be heavily compressed or processed",
                            "This is normal for some separation models",
                            "Consider post-processing to restore dynamics if needed",
                        ],
                    )

            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                category=ValidationCategory.MODEL_OUTPUT,
                message=f"Model output validated: {model_name} ({stem_name})",
                technical_details=f"Shape: {output_audio.shape}, Max: {max_amplitude:.6f}, RMS: {rms_level:.6f}",
                suggestions=[
                    "Output quality appears good",
                    f"Maximum amplitude: {max_amplitude:.6f}",
                    f"RMS level: {rms_level:.6f}",
                ],
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.MODEL_OUTPUT,
                message=f"Failed to validate model output: {model_name} ({stem_name})",
                technical_details=f"Validation error: {str(e)}\n{traceback.format_exc()}",
                suggestions=[
                    "Model output validation encountered an error",
                    "This may indicate a serious processing issue",
                    "Try restarting the processing with different settings",
                ],
            )


class ValidationManager(QObject):
    """Streamlined validation manager focused on model output validation."""

    validation_completed = Signal(ValidationResult)
    validation_progress = Signal(str)  # Progress message

    def __init__(self):
        super().__init__()
        self.file_validator = BasicFileValidator()
        self.output_validator = ModelOutputValidator()

    def validate_file_path(self, file_path: Union[str, Path]) -> ValidationResult:
        """Basic file path validation - librosa will handle the rest."""
        self.validation_progress.emit(f"Checking file: {Path(file_path).name}")
        result = self.file_validator.validate_file_path(file_path)
        self.validation_completed.emit(result)
        return result

    def validate_batch_files(
        self, file_paths: List[Union[str, Path]]
    ) -> List[ValidationResult]:
        """Validate file paths for batch processing - early failure detection."""
        results = []
        total_files = len(file_paths)

        for i, file_path in enumerate(file_paths, 1):
            self.validation_progress.emit(
                f"Checking file {i}/{total_files}: {Path(file_path).name}"
            )
            result = self.file_validator.validate_file_path(file_path)
            results.append(result)
            self.validation_completed.emit(result)

        return results

    def validate_model_output(
        self,
        output_audio: np.ndarray,
        model_name: str,
        stem_name: str,
        expected_duration: Optional[float] = None,
    ) -> ValidationResult:
        """Validate model output - this is where the real value is."""
        self.validation_progress.emit(f"Validating output: {model_name} ({stem_name})")
        result = self.output_validator.validate_model_output(
            output_audio, model_name, stem_name, expected_duration
        )
        self.validation_completed.emit(result)
        return result

    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, int]:
        """Get summary statistics from validation results."""
        summary = {
            "total": len(results),
            "valid": sum(1 for r in results if r.is_valid),
            "warnings": sum(
                1 for r in results if r.severity == ValidationSeverity.WARNING
            ),
            "errors": sum(1 for r in results if r.severity == ValidationSeverity.ERROR),
            "critical": sum(
                1 for r in results if r.severity == ValidationSeverity.CRITICAL
            ),
            "can_proceed": sum(1 for r in results if r.can_proceed),
        }
        return summary
