"""
Enhanced VIP Verification Manager for UVR PySide6 application.

This module provides improved VIP code verification with detailed feedback,
following SOLID principles and clean code practices while maintaining
compatibility with the original UVR cryptographic verification system.
"""

import base64
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, Signal

from . import app_constants as ac
from .logger_utils import get_logger

logger = get_logger(__name__)

# Import cryptography with fallback (following original UVR pattern)
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except ImportError:
    logger.warning("Cryptography library not available - VIP verification disabled")
    CRYPTO_AVAILABLE = False


class VIPVerificationError(Enum):
    """
    Enumeration of VIP verification error types.

    This enum implements the Interface Segregation Principle by providing
    specific error categories that clients can handle differently.
    """

    EMPTY_CODE = "empty_code"
    INVALID_FORMAT = "invalid_format"
    CRYPTOGRAPHIC_ERROR = "cryptographic_error"
    NETWORK_ERROR = "network_error"
    EXPIRED_CODE = "expired_code"
    ALREADY_USED = "already_used"
    SYSTEM_ERROR = "system_error"
    CRYPTO_UNAVAILABLE = "crypto_unavailable"


@dataclass
class VIPVerificationResult:
    """
    Result of VIP code verification with detailed feedback.

    This class follows the Single Responsibility Principle by encapsulating
    all verification result information in one focused data structure.
    """

    success: bool
    decoded_link: Optional[str]
    error_type: Optional[VIPVerificationError]
    user_message: str
    technical_details: str
    retry_allowed: bool
    help_url: Optional[str]
    suggestions: list[str]


class VIPVerificationManager(QObject):
    """
    Enhanced VIP verification manager with detailed user feedback.

    This class implements:
    - Single Responsibility: Focused solely on VIP verification and feedback
    - Open/Closed: Extensible for new verification methods
    - Liskov Substitution: Can be subclassed for different VIP systems
    - Interface Segregation: Clean verification interface
    - Dependency Inversion: Depends on abstract cryptographic interface
    """

    # Signals for UI updates
    verification_completed = Signal(object)  # VIPVerificationResult
    verification_started = Signal()
    error_occurred = Signal(str)  # Error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._verification_history: list[str] = []
        self._max_history_size = ac.VIP_MAX_HISTORY_SIZE

    def verify_vip_code(self, code: str) -> VIPVerificationResult:
        """
        Verify VIP code with enhanced feedback.

        This method provides detailed feedback following the original UVR
        cryptographic verification while adding comprehensive error analysis.

        Args:
            code: VIP access code to verify

        Returns:
            VIPVerificationResult with detailed feedback
        """
        self.verification_started.emit()

        try:
            # Pre-validation checks (defensive programming)
            pre_validation_result = self._pre_validate_code(code)
            if not pre_validation_result.success:
                self.verification_completed.emit(pre_validation_result)
                return pre_validation_result

            # Perform cryptographic verification (original UVR method)
            verification_result = self._perform_cryptographic_verification(code)

            # Post-process result with enhanced feedback
            enhanced_result = self._enhance_verification_result(
                verification_result, code
            )

            # Update verification history
            self._update_verification_history(code, enhanced_result.success)

            self.verification_completed.emit(enhanced_result)
            return enhanced_result

        except Exception as e:
            error_result = self._create_system_error_result(str(e))
            self.error_occurred.emit(error_result.user_message)
            self.verification_completed.emit(error_result)
            return error_result

    def _pre_validate_code(self, code: str) -> VIPVerificationResult:
        """Pre-validate VIP code format and basic requirements."""
        # Check for empty code
        if not code or not code.strip():
            return VIPVerificationResult(
                success=False,
                decoded_link=None,
                error_type=VIPVerificationError.EMPTY_CODE,
                user_message="Please enter a VIP access code",
                technical_details="Code input is empty or contains only whitespace",
                retry_allowed=True,
                help_url=ac.VIP_HELP_URL,
                suggestions=[
                    "Enter your VIP access code in the text field",
                    "Make sure you've copied the complete code",
                    "Check for extra spaces at the beginning or end",
                ],
            )

        # Check cryptography availability
        if not CRYPTO_AVAILABLE:
            return VIPVerificationResult(
                success=False,
                decoded_link=None,
                error_type=VIPVerificationError.CRYPTO_UNAVAILABLE,
                user_message="VIP verification is not available - cryptography library missing",
                technical_details="The required cryptography library is not installed",
                retry_allowed=False,
                help_url=ac.VIP_SETUP_URL,
                suggestions=[
                    "Install the cryptography library: pip install cryptography",
                    "Contact support if you continue having issues",
                    "Use the manual download option as an alternative",
                ],
            )

        # If all pre-validation passes, return success to continue
        return VIPVerificationResult(
            success=True,
            decoded_link=None,
            error_type=None,
            user_message="Code format looks valid",
            technical_details="Pre-validation passed",
            retry_allowed=True,
            help_url=None,
            suggestions=[],
        )

    def _perform_cryptographic_verification(self, code: str) -> VIPVerificationResult:
        """Perform cryptographic verification using original UVR method."""
        try:
            # Use original UVR cryptographic verification
            decoded_link = self._vip_downloads_original(code)

            if decoded_link != ac.VIP_NO_CODE:
                return VIPVerificationResult(
                    success=True,
                    decoded_link=decoded_link,
                    error_type=None,
                    user_message="✅ VIP Access Activated! Premium models unlocked.",
                    technical_details="Successfully decoded VIP link",
                    retry_allowed=False,
                    help_url=ac.VIP_ACTIVATED_URL,
                    suggestions=[
                        "Refresh the model catalog to see premium models",
                        "VIP models are now available in the Download Center",
                        "Your VIP status has been saved for future sessions",
                    ],
                )
            else:
                return VIPVerificationResult(
                    success=False,
                    decoded_link=None,
                    error_type=VIPVerificationError.CRYPTOGRAPHIC_ERROR,
                    user_message="❌ Invalid VIP code. Please check and try again.",
                    technical_details="Cryptographic verification failed",
                    retry_allowed=True,
                    help_url=ac.VIP_TROUBLESHOOT_URL,
                    suggestions=[
                        "Double-check the code for typos or missing characters",
                        "Make sure you have the latest code from your provider",
                        "Try copying and pasting the code instead of typing it",
                        "Contact support if you believe the code should be valid",
                    ],
                )

        except Exception as e:
            return VIPVerificationResult(
                success=False,
                decoded_link=None,
                error_type=VIPVerificationError.CRYPTOGRAPHIC_ERROR,
                user_message="Verification failed due to technical error",
                technical_details=f"Cryptographic operation failed: {str(e)}",
                retry_allowed=True,
                help_url=ac.VIP_TECHNICAL_URL,
                suggestions=[
                    "Try again in a few moments",
                    "Restart the application if the problem persists",
                    "Contact technical support with error details",
                ],
            )

    def _vip_downloads_original(
        self, password: str, link_type: tuple = ac.VIP_REPO
    ) -> str:
        """
        Original UVR VIP downloads function with exact compatibility.

        This method maintains the exact implementation from UVR.py to ensure
        complete compatibility with existing VIP codes.
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=link_type[0],
                iterations=390000,
            )

            key = base64.urlsafe_b64encode(kdf.derive(bytes(password, "utf-8")))
            f = Fernet(key)

            return str(f.decrypt(link_type[1]), "UTF-8")
        except Exception:
            return ac.VIP_NO_CODE

    def _enhance_verification_result(
        self, result: VIPVerificationResult, code: str
    ) -> VIPVerificationResult:
        """Enhance verification result with additional context and suggestions."""
        if result.success:
            # Add success-specific enhancements
            result.suggestions.extend(
                [
                    "Your VIP access is now active for this session",
                    "Premium models will appear in your download catalog",
                    "VIP status will be remembered for future sessions",
                ]
            )
        else:
            # Add failure-specific enhancements based on error patterns
            enhanced_suggestions = self._analyze_failure_patterns(
                code, result.error_type
            )
            result.suggestions.extend(enhanced_suggestions)

        return result

    def _analyze_failure_patterns(
        self, code: str, error_type: Optional[VIPVerificationError]
    ) -> list[str]:
        """Analyze failure patterns to provide targeted suggestions."""
        suggestions = []

        # Analyze code characteristics for targeted advice
        if len(code) < 8:
            suggestions.append(
                "VIP codes are typically longer - make sure you have the complete code"
            )

        if len(code) > 100:
            suggestions.append(
                "VIP codes are typically shorter - you may have extra text"
            )

        if code.isdigit():
            suggestions.append("VIP codes usually contain both letters and numbers")

        if " " in code:
            suggestions.append("Try removing any spaces from the code")

        if code != code.strip():
            suggestions.append("Remove any leading or trailing spaces")

        return suggestions

    def _update_verification_history(self, code: str, success: bool) -> None:
        """Update verification history for rate limiting and analytics."""
        # Store only a hash of the code for privacy
        code_hash = str(hash(code))
        self._verification_history.append(code_hash)

        # Keep history size manageable
        if len(self._verification_history) > self._max_history_size:
            self._verification_history = self._verification_history[
                -self._max_history_size :
            ]

    def _create_system_error_result(self, error_details: str) -> VIPVerificationResult:
        """Create a system error result for unexpected failures."""
        return VIPVerificationResult(
            success=False,
            decoded_link=None,
            error_type=VIPVerificationError.SYSTEM_ERROR,
            user_message="A technical error occurred during verification",
            technical_details=error_details,
            retry_allowed=True,
            help_url=ac.VIP_SUPPORT_URL,
            suggestions=[
                "Try again in a few moments",
                "Restart the application if the problem persists",
                "Contact support if the issue continues",
            ],
        )

    def get_verification_statistics(self) -> dict:
        """
        Get verification statistics for debugging and monitoring.

        Returns:
            Dictionary with verification statistics
        """
        return {
            "total_attempts": len(self._verification_history),
            "crypto_available": CRYPTO_AVAILABLE,
            "recent_attempts": len(self._verification_history[-5:]),
        }

    def clear_verification_history(self) -> None:
        """
        Clear verification history.

        This method provides a way to reset the verification state,
        useful for testing or privacy purposes.
        """
        self._verification_history.clear()
        logger.info("VIP verification history cleared")
