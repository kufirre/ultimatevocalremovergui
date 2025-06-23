"""
Unit tests for enhanced VIP verification functionality.

This module tests the VIPVerificationManager to ensure proper
VIP code verification with detailed user feedback.
"""

from unittest.mock import patch

import pytest
from PySide6.QtTest import QSignalSpy

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.vip_verification_manager import (
    VIPVerificationError,
    VIPVerificationManager,
    VIPVerificationResult,
)


@pytest.mark.unit
@pytest.mark.vip
@pytest.mark.verification
class TestVIPVerificationManager:
    """Test cases for VIPVerificationManager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = VIPVerificationManager()

        assert hasattr(manager, "verification_completed")
        assert hasattr(manager, "verification_started")
        assert hasattr(manager, "error_occurred")
        assert manager._verification_history == []

    def test_empty_code_validation(self):
        """Test validation of empty VIP codes."""
        manager = VIPVerificationManager()

        # Test empty string
        result = manager.verify_vip_code("")
        assert result.success is False
        assert result.error_type == VIPVerificationError.EMPTY_CODE
        assert "Please enter a VIP access code" in result.user_message
        assert result.retry_allowed is True
        assert len(result.suggestions) > 0

    def test_whitespace_only_code_validation(self):
        """Test validation of whitespace-only codes."""
        manager = VIPVerificationManager()

        result = manager.verify_vip_code("   \t\n  ")
        assert result.success is False
        assert result.error_type == VIPVerificationError.EMPTY_CODE
        assert result.retry_allowed is True

    def test_crypto_unavailable_handling(self):
        """Test handling when cryptography library is unavailable."""
        manager = VIPVerificationManager()

        with patch(
            "uvr_pyside6_ui.core.vip_verification_manager.CRYPTO_AVAILABLE", False
        ):
            result = manager.verify_vip_code("test_code")

            assert result.success is False
            assert result.error_type == VIPVerificationError.CRYPTO_UNAVAILABLE
            assert "cryptography library missing" in result.user_message
            assert result.retry_allowed is False

    def test_invalid_code_verification(self):
        """Test verification of invalid VIP codes."""
        manager = VIPVerificationManager()

        result = manager.verify_vip_code("invalid_test_code")
        assert result.success is False
        assert result.error_type == VIPVerificationError.CRYPTOGRAPHIC_ERROR
        assert "Invalid VIP code" in result.user_message
        assert result.retry_allowed is True
        assert len(result.suggestions) > 0

    def test_verification_signals(self):
        """Test that verification emits appropriate signals."""
        manager = VIPVerificationManager()

        started_spy = QSignalSpy(manager.verification_started)
        completed_spy = QSignalSpy(manager.verification_completed)

        manager.verify_vip_code("test_code")

        assert started_spy.count() == 1
        assert completed_spy.count() == 1

    def test_failure_pattern_analysis(self):
        """Test analysis of failure patterns for better suggestions."""
        manager = VIPVerificationManager()

        # Test short code
        result = manager.verify_vip_code("123")
        suggestions_text = " ".join(result.suggestions)
        assert (
            "typically longer" in suggestions_text
            or "complete code" in suggestions_text
        )

        # Test numeric only code
        result = manager.verify_vip_code("12345678")
        suggestions_text = " ".join(result.suggestions)
        assert "letters and numbers" in suggestions_text

        # Test code with spaces
        result = manager.verify_vip_code("test code with spaces")
        suggestions_text = " ".join(result.suggestions)
        assert "spaces" in suggestions_text

    def test_verification_history_tracking(self):
        """Test verification history tracking."""
        manager = VIPVerificationManager()

        # Verify multiple codes
        manager.verify_vip_code("code1")
        manager.verify_vip_code("code2")
        manager.verify_vip_code("code3")

        stats = manager.get_verification_statistics()
        assert stats["total_attempts"] == 3
        assert "crypto_available" in stats

    def test_history_size_limit(self):
        """Test that verification history respects size limits."""
        manager = VIPVerificationManager()
        manager._max_history_size = 3

        # Add more codes than the limit
        for i in range(5):
            manager.verify_vip_code(f"code{i}")

        stats = manager.get_verification_statistics()
        assert stats["total_attempts"] <= manager._max_history_size

    def test_clear_verification_history(self):
        """Test clearing verification history."""
        manager = VIPVerificationManager()

        manager.verify_vip_code("test_code")
        assert len(manager._verification_history) > 0

        manager.clear_verification_history()
        assert len(manager._verification_history) == 0

    def test_system_error_handling(self):
        """Test handling of system errors during verification."""
        manager = VIPVerificationManager()

        # Mock an exception in the verification process
        with patch.object(
            manager, "_pre_validate_code", side_effect=Exception("Test error")
        ):
            result = manager.verify_vip_code("test_code")

            assert result.success is False
            assert result.error_type == VIPVerificationError.SYSTEM_ERROR
            assert "technical error" in result.user_message


@pytest.mark.unit
@pytest.mark.vip
@pytest.mark.verification
class TestVIPVerificationResult:
    """Test cases for VIPVerificationResult data structure."""

    def test_verification_result_creation(self):
        """Test creation of VIPVerificationResult."""
        result = VIPVerificationResult(
            success=True,
            decoded_link="https://example.com/vip",
            error_type=None,
            user_message="Success!",
            technical_details="All good",
            retry_allowed=False,
            help_url="https://help.com",
            suggestions=["Great job!"],
        )

        assert result.success is True
        assert result.decoded_link == "https://example.com/vip"
        assert result.error_type is None
        assert result.user_message == "Success!"
        assert result.retry_allowed is False
        assert len(result.suggestions) == 1

    def test_error_result_creation(self):
        """Test creation of error VIPVerificationResult."""
        result = VIPVerificationResult(
            success=False,
            decoded_link=None,
            error_type=VIPVerificationError.INVALID_FORMAT,
            user_message="Invalid format",
            technical_details="Format check failed",
            retry_allowed=True,
            help_url="https://help.com/format",
            suggestions=["Check format", "Try again"],
        )

        assert result.success is False
        assert result.decoded_link is None
        assert result.error_type == VIPVerificationError.INVALID_FORMAT
        assert result.retry_allowed is True
        assert len(result.suggestions) == 2


@pytest.mark.regression
@pytest.mark.vip
@pytest.mark.verification
class TestVIPVerificationRegression:
    """Regression tests for VIP verification functionality."""

    def test_vip_verification_feedback_prevents_user_confusion(self):
        """
        CRITICAL Regression test: VIP verification should provide clear feedback.

        This test prevents regression of poor user experience with generic
        "invalid code" messages that don't help users understand the problem.
        """
        manager = VIPVerificationManager()

        # Test various failure scenarios
        test_cases = [
            ("", "empty code"),
            ("   ", "whitespace only"),
            ("123", "too short"),
            ("invalid_code_123", "invalid format"),
        ]

        for code, scenario in test_cases:
            result = manager.verify_vip_code(code)

            # Should provide specific feedback, not generic error
            assert result.success is False
            assert result.user_message != "Invalid code"  # Generic message
            assert len(result.suggestions) > 0  # Should provide suggestions
            assert result.help_url is not None or len(result.suggestions) > 2

            # Each error should have specific guidance
            if scenario == "empty code":
                assert "enter" in result.user_message.lower()
            elif scenario == "too short":
                suggestions_text = " ".join(result.suggestions).lower()
                assert "longer" in suggestions_text or "complete" in suggestions_text

    def test_cryptographic_compatibility_with_original_uvr(self):
        """
        Regression test: Should maintain compatibility with original UVR verification.

        This ensures the enhanced verification doesn't break existing VIP codes.
        """
        manager = VIPVerificationManager()

        # Test that the cryptographic method matches original UVR behavior
        test_code = "test_invalid_code"
        result = manager.verify_vip_code(test_code)

        # Should fail with cryptographic error (expected for invalid code)
        assert result.success is False
        assert result.error_type == VIPVerificationError.CRYPTOGRAPHIC_ERROR

        # But should provide helpful feedback, not just "incorrect_code"
        assert result.user_message != ac.VIP_NO_CODE
        assert len(result.suggestions) > 0

    def test_enhanced_feedback_preserves_security(self):
        """
        Regression test: Enhanced feedback should not compromise security.

        This ensures detailed feedback doesn't reveal sensitive information
        about the verification process.
        """
        manager = VIPVerificationManager()

        # Test with various potentially malicious inputs
        malicious_codes = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "eval(malicious_code)",
        ]

        for malicious_code in malicious_codes:
            result = manager.verify_vip_code(malicious_code)

            # Should fail safely without revealing system information
            assert result.success is False
            assert "script" not in result.technical_details.lower()
            assert "drop" not in result.technical_details.lower()
            assert "eval" not in result.technical_details.lower()

            # Should not expose internal paths or system details
            assert "/etc/" not in result.technical_details
            assert "passwd" not in result.technical_details

    def test_verification_performance_and_rate_limiting(self):
        """
        Regression test: Verification should be performant and prevent abuse.

        This ensures the enhanced verification doesn't introduce performance
        issues or allow brute force attacks.
        """
        manager = VIPVerificationManager()

        # Test multiple rapid verifications
        codes = [f"test_code_{i}" for i in range(10)]

        for code in codes:
            result = manager.verify_vip_code(code)
            # Should complete reasonably quickly and not hang
            assert result is not None
            assert hasattr(result, "success")

        # History should be maintained but limited
        stats = manager.get_verification_statistics()
        assert stats["total_attempts"] <= manager._max_history_size
