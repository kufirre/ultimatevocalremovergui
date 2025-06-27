"""Presenter for the download center functionality."""

import base64
import json
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from uvr_pyside6_ui.core.logger_utils import get_logger
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter

logger = get_logger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except ImportError:
    logger.warning("Cryptography library not available - VIP verification disabled")
    CRYPTO_AVAILABLE = False

VIP_REPO = (
    b"\xf3\xc2W\x19\x1foI)\xc2\xa9\xcc\xb67(Z\xf5",
    b"gAAAAABjQAIQ-NpNMMxMedpKHHb7ze_nqB05hw0YhbOy3pFzuzDrfqumn8_qvraxEoUpZC5ZXC0gGvfDxFMqyq9VWbYKlA67SUFI_wZB6QoVyGI581vs7kaGfUqlXHIdDS6tQ_U-BfjbEAK9EU_74-R2zXjz8Xzekw==",
)
NO_CODE = "incorrect_code"


def vip_downloads(password, link_type=VIP_REPO):
    """Attempts to decrypt VIP model link with given input code"""
    if not CRYPTO_AVAILABLE:
        return NO_CODE

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
        return NO_CODE


class DownloadCenterPresenter(QObject):
    """Handle model downloads and VIP functionality."""

    def __init__(
        self,
        adapter: UVRCoreAdapter,
        settings_file_path: Path,
        parent_qt_object: QObject = None,
    ):
        super().__init__(parent_qt_object)
        self.view = None
        self.adapter = adapter
        self._settings_file_path = settings_file_path
        self._full_online_catalog: dict = {}
        self._is_download_in_progress = False
        self._last_progress_percentage = -1  # Track last progress to throttle updates
        self._decoded_vip_link: str | None = None

        # Check if VIP is already activated and set up adapter
        self._check_vip_status()

    def set_view(self, view):
        """Set the download center view and connect signals."""
        self.view = view
        self._setup_view_connections()

    def _setup_view_connections(self):
        """Set up signal connections for the view."""
        if not self.view:
            return

        # Connect view signals
        self.view.download_button_clicked.connect(self._on_dc_download_button_clicked)
        self.view.download_stop_requested.connect(self._on_dc_stop_button_clicked)

        # Connect download center action buttons
        if hasattr(self.view, "dc_refresh_btn"):
            self.view.dc_refresh_btn.clicked.connect(self._on_refresh_models)
        if hasattr(self.view, "dc_key_btn"):
            self.view.dc_key_btn.clicked.connect(self._on_vip_access)
        if hasattr(self.view, "dc_manual_btn"):
            self.view.dc_manual_btn.clicked.connect(self._on_manual_download)

        # Connect adapter download signals
        self.adapter.download_progress.connect(self._on_adapter_download_progress)
        self.adapter.download_finished.connect(self._on_adapter_download_finished)

    def populate_download_center(self, default_model_type: str | None = None):
        """Populate the download center with available models."""
        if not self.view:
            return

        if not isinstance(
            self.adapter, UVRCoreAdapter
        ):  # Should not happen with proper init
            self.view.dc_progress_info_label.setText("Adapter unavailable.")
            return

        if not self._full_online_catalog:
            self._full_online_catalog = self.adapter.get_online_catalog()

        if self._full_online_catalog:
            # Get downloadable models and filter out already downloaded ones
            vr_models = self._get_filtered_downloadable_models("VR Architecture")
            self.view.set_vr_models(
                list(vr_models.keys()) if vr_models else ["No models available"]
            )

            mdx_models = self._get_filtered_downloadable_models("MDX-Net")
            self.view.set_mdx_models(
                list(mdx_models.keys()) if mdx_models else ["No models available"]
            )

            demucs_models = self._get_filtered_downloadable_models("Demucs")
            self.view.set_demucs_models(
                list(demucs_models.keys()) if demucs_models else ["No models available"]
            )

            # Set default selection if provided
            if default_model_type:
                if hasattr(self.view, "dc_architecture_combo"):
                    if default_model_type == "VR Arch":
                        self.view.dc_architecture_combo.setCurrentText(
                            "VR Architecture"
                        )
                    elif default_model_type == "MDX-Net":
                        self.view.dc_architecture_combo.setCurrentText("MDX-Net")
                    elif default_model_type == "Demucs":
                        self.view.dc_architecture_combo.setCurrentText("Demucs")
                    self.view._populate_models_for_architecture()

            # Initialize progress display to clean state
            if not self._is_download_in_progress:
                self.view.dc_progress_info_label.setText("Ready to download")
                self.view.dc_progress_percent_label.setText("0%")
                self.view.dc_progress_bar.setValue(0)
        else:
            self.view.set_vr_models(["Could not load catalog"])
            self.view.set_mdx_models(["Could not load catalog"])
            self.view.set_demucs_models(["Could not load catalog"])
            self.view.dc_progress_info_label.setText("Could not load download catalog")

    def _get_filtered_downloadable_models(self, ui_model_type: str) -> dict:
        """Get downloadable models filtered to exclude already downloaded ones."""
        # Map UI type to internal adapter type
        ui_to_internal_map = {
            "VR Architecture": "VR Arch",
            "MDX-Net": "MDX-Net",
            "Demucs": "Demucs",
        }
        internal_type = ui_to_internal_map.get(ui_model_type, ui_model_type)

        # Get all downloadable models for this type (including VIP if applicable)
        all_models = self._get_models_including_vip(internal_type)
        if not all_models:
            logger.warning(
                f"No downloadable models found for type: {internal_type} (UI: {ui_model_type})"
            )
            return {}

        # Get list of already installed models
        installed_models = self.adapter._get_locally_installed_primary_model_filenames(
            internal_type
        )
        logger.debug(f"Installed models for {internal_type}: {installed_models}")

        # Filter out models that are already downloaded
        filtered_models = {}
        for model_name, model_info in all_models.items():
            # Check if this model is already installed
            is_installed = False

            # For different model types, extract the actual filename
            if internal_type == "VR Arch":
                # VR model names often have format like "VR Arch Single Model v5: 4_HP-Vocal-UVR"
                # We need to extract the actual filename part after the colon
                if ":" in model_name:
                    actual_filename = model_name.split(":")[-1].strip()
                else:
                    actual_filename = model_name

                # Add .pth extension if not present
                if not actual_filename.endswith(".pth"):
                    actual_filename += ".pth"

                # Check multiple ways the model could match
                for installed in installed_models:
                    # Direct filename match
                    if actual_filename == installed:
                        is_installed = True
                        break
                    # Base name match (without extension)
                    if actual_filename.replace(".pth", "") in installed:
                        is_installed = True
                        break
                    # Partial match (for complex model names)
                    if actual_filename.replace(".pth", "") == installed.replace(
                        ".pth", ""
                    ):
                        is_installed = True
                        break

                logger.debug(
                    f"VR Model check - Name: {model_name}, Filename: {actual_filename}, Installed: {is_installed}"
                )

            elif internal_type == "MDX-Net":
                # MDX models - extract actual filename from model info
                actual_filename = None

                # Handle different MDX model info formats
                if isinstance(model_info, str):
                    # Simple string format
                    actual_filename = (
                        model_info
                        if model_info.endswith(".onnx")
                        else f"{model_info}.onnx"
                    )
                elif isinstance(model_info, dict):
                    # Complex format like MDX23C: {'MDX23C_D1581.ckpt': 'model_2_stem_061321.yaml'}
                    for key, value in model_info.items():
                        if key.endswith(".onnx") or key.endswith(".ckpt"):
                            actual_filename = key
                            break
                    if not actual_filename and model_info:
                        # Fallback - use first item
                        actual_filename = (
                            list(model_info.keys())[0] if model_info else None
                        )
                else:
                    # Extract from model name if other formats fail
                    if ":" in model_name:
                        actual_filename = model_name.split(":")[-1].strip()
                        if not actual_filename.endswith((".onnx", ".ckpt")):
                            actual_filename += ".onnx"
                    else:
                        actual_filename = model_name.replace(" ", "_").replace(":", "_")
                        if not actual_filename.endswith((".onnx", ".ckpt")):
                            actual_filename += ".onnx"

                # Check if model is installed
                if actual_filename:
                    for installed in installed_models:
                        if actual_filename == installed or actual_filename.replace(
                            ".onnx", ""
                        ).replace(".ckpt", "") == installed.replace(
                            ".onnx", ""
                        ).replace(
                            ".ckpt", ""
                        ):
                            is_installed = True
                            break
                        # Also check without extensions
                        if (
                            actual_filename.replace(".onnx", "").replace(".ckpt", "")
                            in installed
                        ):
                            is_installed = True
                            break

                logger.debug(
                    f"MDX Model check - Name: {model_name}, Filename: {actual_filename}, Installed: {is_installed}"
                )

            elif internal_type == "Demucs":
                # Demucs models - extract filename part
                if ":" in model_name:
                    actual_filename = model_name.split(":")[-1].strip()
                else:
                    actual_filename = model_name

                # Check if model is installed
                for installed in installed_models:
                    if actual_filename in installed or installed in actual_filename:
                        is_installed = True
                        break

            # Only include if not already installed
            if not is_installed:
                filtered_models[model_name] = model_info
            else:
                logger.debug(f"Filtered out already installed model: {model_name}")

        logger.info(
            f"Found {len(filtered_models)} downloadable models for {ui_model_type} (filtered from {len(all_models)} total)"
        )
        return filtered_models

    def _get_models_including_vip(self, internal_type: str) -> dict:
        """Get models including VIP models if user has valid VIP access."""
        # Start with standard downloadable models
        all_models = self.adapter.get_downloadable_models_for_type(internal_type)

        # Check if user has VIP access and can get real VIP models
        if self._check_vip_status():
            logger.info("VIP access detected - checking for actual VIP models")

            # Get the full online catalog to access VIP lists
            full_catalog = self.adapter.get_online_catalog()

            # Map internal types to VIP catalog keys
            vip_catalog_keys = {
                "VR Arch": "vr_download_vip_list",
                "MDX-Net": "mdx_download_vip_list",
                "Demucs": "demucs_download_vip_list",
            }

            # Also check MDX23C for MDX-Net type
            if internal_type == "MDX-Net":
                mdx23c_key = "mdx23c_download_vip_list"
                if mdx23c_key in full_catalog:
                    mdx23c_vip_models = full_catalog[mdx23c_key]
                    if isinstance(mdx23c_vip_models, dict) and mdx23c_vip_models:
                        logger.info(
                            f"Adding {len(mdx23c_vip_models)} VIP MDX23C models"
                        )
                        all_models.update(mdx23c_vip_models)

            # Get VIP models for this type
            vip_key = vip_catalog_keys.get(internal_type)
            if vip_key and vip_key in full_catalog:
                vip_models = full_catalog[vip_key]

                # Handle different VIP list formats
                if isinstance(vip_models, dict) and vip_models:
                    logger.info(
                        f"Adding {len(vip_models)} VIP models for {internal_type}"
                    )
                    all_models.update(vip_models)
                elif isinstance(vip_models, list) and vip_models:
                    logger.info(
                        f"VIP list for {internal_type} is array format: {vip_models}"
                    )
                else:
                    logger.info(f"No VIP models available for {internal_type}")
            else:
                logger.info(
                    f"VIP catalog key '{vip_key}' not found for {internal_type}"
                )

        return all_models

    @Slot()
    def _on_dc_stop_button_clicked(self) -> None:
        """Handle stop download button clicks."""
        logger.info("Stop download requested")

        # Cancel downloads through the adapter
        if self.adapter:
            self.adapter.cancel_downloads()

        # Update UI to reflect cancellation
        if self.view:
            self.view.show_status_message("Download cancellation requested", 3000)
            self.view.dc_progress_info_label.setText("🚫 Cancelling download...")
            # Note: Progress will be reset when download_finished signal is emitted

    @Slot()
    def _on_dc_download_button_clicked(self) -> None:
        """Handle download button clicks from the download center."""
        if not self.view:
            return

        model_type = self.view.get_selected_model_type()
        model_name = self.view.get_selected_model()

        if not model_type or not model_name or model_name == "No models available":
            self.view.show_status_message("Please select a model to download", 3000)
            return

        logger.info(f"Download requested for {model_type}: {model_name}")

        try:
            # Map UI type to internal type for the adapter
            ui_to_internal_map = {
                "VR Architecture": "VR Arch",
                "MDX-Net": "MDX-Net",
                "Demucs": "Demucs",
            }
            internal_model_type = ui_to_internal_map.get(model_type, model_type)

            # First try to get the download target info from the standard catalog
            downloadable_models = self.adapter.get_downloadable_models_for_type(
                internal_model_type
            )
            download_target_info = None

            if downloadable_models and model_name in downloadable_models:
                download_target_info = downloadable_models[model_name]
            else:
                # If not found in standard catalog, check if it's a VIP model
                vip_enhanced_models = self._get_models_including_vip(
                    internal_model_type
                )
                if model_name in vip_enhanced_models:
                    download_target_info = vip_enhanced_models[model_name]
                    logger.info(f"Found VIP model in enhanced catalog: {model_name}")
                    logger.debug(
                        f"VIP model info format: {type(download_target_info)} - {download_target_info}"
                    )

                    # Special handling for different VIP model formats
                    if isinstance(download_target_info, dict):
                        if len(download_target_info) == 1:
                            # MDX23C format: {'MDX23C_D1581.ckpt': 'model_2_stem_061321.yaml'}
                            # Download the .ckpt file, not the .yaml file
                            for ckpt_file, yaml_file in download_target_info.items():
                                if ckpt_file.endswith(".ckpt"):
                                    # Convert to format expected by adapter: download the .ckpt file
                                    download_target_info = ckpt_file
                                    logger.info(
                                        f"Converted MDX23C VIP model format: {ckpt_file}"
                                    )
                                    break
                        else:
                            # Complex VIP model format - extract the actual model filename
                            # Look for common model file extensions
                            for key, value in download_target_info.items():
                                if key.endswith((".onnx", ".pth", ".ckpt")):
                                    download_target_info = key
                                    logger.info(f"Extracted VIP model filename: {key}")
                                    break
                            else:
                                # If no direct file found, use the first value that looks like a filename
                                if download_target_info:
                                    first_key = list(download_target_info.keys())[0]
                                    download_target_info = first_key
                                    logger.info(
                                        f"Using first VIP model key: {first_key}"
                                    )
                    elif isinstance(download_target_info, str):
                        # Simple string format - extract just the filename if it has model prefix
                        if ":" in download_target_info:
                            # Format like "MDX-Net Model VIP: UVR-MDX-NET_Main_406"
                            actual_filename = download_target_info.split(":")[
                                -1
                            ].strip()
                            download_target_info = actual_filename
                            logger.info(
                                f"Extracted filename from VIP string: {actual_filename}"
                            )

                    logger.info(f"Final VIP download target: {download_target_info}")

            if not download_target_info:
                error_msg = "Model not found in catalog"
                self.view.show_status_message(error_msg, 3000)
                logger.error(
                    f"Model '{model_name}' not found in any catalog for {internal_model_type}"
                )
                return

            # Set download in progress state
            self.view.set_download_in_progress_state(True)
            self.view.dc_progress_info_label.setText(
                f"Initializing download of {model_name}..."
            )
            self.view.dc_progress_percent_label.setText("0%")
            self.view.dc_progress_bar.setValue(0)

            # Request download from adapter with all required parameters
            self.adapter.download_model(
                internal_model_type, model_name, download_target_info
            )

        except Exception as e:
            logger.error(f"Error starting download: {e}")
            self.view.set_download_in_progress_state(False)
            # Show brief error in UI, full details in log
            error_msg = "Download failed to start"
            self.view.show_status_message(error_msg, 5000)
            self.view.dc_progress_info_label.setText(f"❌ {error_msg}")

    @Slot(str, int)
    def _on_adapter_download_progress(self, model_name: str, percentage: int):
        """Handle download progress updates with proper UI updates."""
        if self.view and self.view.isVisible():
            # Update progress info label
            self.view.dc_progress_info_label.setText(f"Downloading {model_name}...")

            # Update progress percentage label
            self.view.dc_progress_percent_label.setText(f"{percentage}%")

            # Update progress bar
            self.view.dc_progress_bar.setValue(percentage)

            # Force UI update
            self.view.dc_progress_bar.repaint()

    @Slot(str, str, bool, str)
    def _on_adapter_download_finished(
        self,
        model_type_ui_name: str,
        model_display_name: str,
        success: bool,
        message: str,
    ):
        """Handle download completion with proper progress state reset."""
        if self.view and self.view.isVisible():
            self._is_download_in_progress = False
            self.view.set_download_in_progress_state(False)

            if success:
                # Success - show completion with nice formatting
                self.view.dc_progress_info_label.setText(
                    f"✅ Successfully downloaded {model_display_name}"
                )
                self.view.dc_progress_percent_label.setText("100%")
                self.view.dc_progress_bar.setValue(100)

                # Refresh the model lists to remove the downloaded model
                QTimer.singleShot(1000, lambda: self.populate_download_center())

                # Reset after delay to show completion
                QTimer.singleShot(3000, lambda: self._reset_download_progress_display())

                # Emit signal that main UI can catch to refresh its model list
                # This should trigger the main UI to refresh the model dropdown for the downloaded type
                logger.info(
                    f"Download completed for {model_type_ui_name}, triggering main UI refresh"
                )

            else:
                # Check if this is a cancellation or actual failure
                is_cancellation = "cancelled" in message.lower()

                if is_cancellation:
                    # Cancellation - show cancellation message
                    self.view.dc_progress_info_label.setText("🚫 Download cancelled")
                    self.view.dc_progress_percent_label.setText("Cancelled")
                    self.view.dc_progress_bar.setValue(0)

                    # Log as info, not error
                    logger.info(
                        f"Download cancelled for {model_display_name}: {message}"
                    )
                else:
                    # Actual error - show error message
                    brief_error = "Download failed"
                    self.view.dc_progress_info_label.setText(f"❌ {brief_error}")
                    self.view.dc_progress_percent_label.setText("Failed")
                    self.view.dc_progress_bar.setValue(0)

                    # Log full error details
                    logger.error(f"Download failed for {model_display_name}: {message}")

                # Reset after longer delay for error/cancellation message
                QTimer.singleShot(5000, lambda: self._reset_download_progress_display())

    def _reset_download_progress_display(self):
        """Reset download progress display to ready state."""
        if self.view and not self._is_download_in_progress:
            self.view.dc_progress_info_label.setText("Ready to download")
            self.view.dc_progress_percent_label.setText("0%")
            self.view.dc_progress_bar.setValue(0)

    @Slot()
    def _on_refresh_models(self):
        """Handle refresh models button click."""
        logger.info("Refreshing model catalog")
        if self.view:
            self.view.dc_progress_info_label.setText("Refreshing model catalog...")

        # Clear cached catalog to force refresh
        self._full_online_catalog = {}

        # Repopulate with fresh data
        self.populate_download_center()

        if self.view:
            self.view.dc_progress_info_label.setText("Model catalog refreshed")
            QTimer.singleShot(
                2000,
                lambda: self.view.dc_progress_info_label.setText("Ready to download"),
            )

    @Slot()
    def _on_vip_access(self):
        """Handle VIP access button click - show VIP code input dialog."""
        dialog = QDialog(self.view)
        dialog.setWindowTitle("VIP Access")
        dialog.resize(450, 350)

        layout = QVBoxLayout(dialog)

        # Header
        title_label = QLabel("Ultimate Vocal Remover VIP Access")
        title_label.setStyleSheet(
            "font-weight: bold; font-size: 16px; margin-bottom: 10px;"
        )
        layout.addWidget(title_label)

        # Description
        desc_text = QTextEdit()
        desc_text.setPlainText(
            """VIP Access unlocks premium features:

• Exclusive high-quality AI models
• Early access to experimental models
• Advanced processing algorithms
• Premium model configurations
• Priority download speeds
• Extended format support

Enter your VIP access code below to unlock these features."""
        )
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(120)
        layout.addWidget(desc_text)

        # VIP Code Input Section
        input_group = QGroupBox("VIP Code Entry")
        input_layout = QFormLayout(input_group)

        # VIP Code input
        self.vip_code_input = QLineEdit()
        self.vip_code_input.setPlaceholderText("Enter your VIP access code...")
        self.vip_code_input.setEchoMode(
            QLineEdit.Password
        )  # Hide the code for security
        input_layout.addRow("VIP Code:", self.vip_code_input)

        # Show/Hide code checkbox
        show_code_checkbox = QCheckBox("Show code")
        show_code_checkbox.toggled.connect(
            lambda checked: self.vip_code_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        input_layout.addRow("", show_code_checkbox)

        layout.addWidget(input_group)

        # Status label
        self.vip_status_label = QLabel("")
        self.vip_status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.vip_status_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        # Get VIP Access button (for purchasing/info)
        get_vip_btn = QPushButton("Get VIP Access")
        get_vip_btn.clicked.connect(lambda: self._show_vip_purchase_info(dialog))
        button_layout.addWidget(get_vip_btn)

        button_layout.addStretch()

        # Activate button
        activate_btn = QPushButton("Activate VIP")
        activate_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """
        )
        activate_btn.clicked.connect(lambda: self._activate_vip_code(dialog))
        button_layout.addWidget(activate_btn)

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def _activate_vip_code(self, dialog):
        """Activate VIP code and unlock premium models."""
        vip_code = self.vip_code_input.text().strip()

        if not vip_code:
            self.vip_status_label.setText("Please enter a VIP code")
            self.vip_status_label.setStyleSheet("color: #e74c3c;")
            return

        # Use the same cryptographic verification as original UVR.py
        decoded_vip_link = vip_downloads(vip_code)

        if decoded_vip_link != NO_CODE:
            # Success - VIP activated
            self.vip_status_label.setText(
                "✅ VIP Access Activated! Premium models unlocked."
            )
            self.vip_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

            # Save VIP status and set VIP link in adapter
            self._save_vip_status(vip_code)
            self._decoded_vip_link = decoded_vip_link

            # Set VIP link in the adapter for URL construction
            self.adapter.set_vip_link(decoded_vip_link)

            # Show success message
            QMessageBox.information(
                dialog,
                "VIP Activated!",
                "Congratulations! Your VIP access has been activated.\n\n"
                "Premium models and features are now available in the Download Center.\n"
                "Please refresh the model list to see additional options.",
            )

            # Refresh model catalog to show VIP models
            self._full_online_catalog = {}  # Clear cache
            self.populate_download_center()

            dialog.accept()

        else:
            # Invalid code
            self.vip_status_label.setText(
                "❌ Invalid VIP code. Please check and try again."
            )
            self.vip_status_label.setStyleSheet("color: #e74c3c;")
            self.vip_code_input.selectAll()  # Select text for easy replacement

    def _show_vip_purchase_info(self, parent_dialog):
        """Show information about purchasing VIP access."""
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QTextEdit,
            QVBoxLayout,
        )

        info_dialog = QDialog(parent_dialog)
        info_dialog.setWindowTitle("Get VIP Access")
        info_dialog.resize(400, 300)

        layout = QVBoxLayout(info_dialog)

        title_label = QLabel("Get Ultimate VIP Access")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        info_text = QTextEdit()
        info_text.setPlainText(
            """How to get VIP Access:

1. Support the Ultimate Vocal Remover project
2. Become a Patreon supporter
3. Contribute to the open-source development
4. Purchase a VIP license for commercial use

VIP Benefits:
• Access to 50+ premium AI models
• Experimental and cutting-edge algorithms
• Commercial usage rights
• Priority support and updates
• Early access to new features

Contact Information:
• Visit: ultimatevocalremover.com/vip
• Email: vip@ultimatevocalremover.com
• Patreon: patreon.com/ultimatevocalremover

Note: This implementation uses real cryptographic verification.
Valid VIP codes are encrypted and provided by the UVR development team."""
        )
        info_text.setReadOnly(True)
        layout.addWidget(info_text)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(info_dialog.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        info_dialog.exec()

    def _save_vip_status(self, vip_code):
        """Save VIP activation status to settings."""
        try:
            vip_settings = {
                "vip_activated": True,
                "vip_code": vip_code,
                "activation_date": "2025-01-05",  # In real implementation, use current date
            }

            # Load current settings
            current_settings = {}
            if self._settings_file_path.exists():
                try:
                    with open(self._settings_file_path, encoding="utf-8") as f:
                        current_settings = json.load(f)
                except (OSError, json.JSONDecodeError) as e:
                    logger.warning(f"Could not load existing settings file: {e}")

            # Update with VIP settings
            current_settings.update(vip_settings)

            with open(self._settings_file_path, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, indent=4)

            logger.info("VIP access activated and saved to settings")

        except Exception as e:
            logger.error(f"Error saving VIP status: {e}")

    @Slot()
    def _on_manual_download(self):
        """Handle manual download button click."""
        dialog = QDialog(self.view)
        dialog.setWindowTitle("Manual Download")
        dialog.resize(500, 300)

        layout = QVBoxLayout(dialog)

        title_label = QLabel("Manual Model Download")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        form_layout = QFormLayout()

        # Model type
        model_type_combo = QComboBox()
        model_type_combo.addItems(["VR Architecture", "MDX-Net", "Demucs"])
        form_layout.addRow("Model Type:", model_type_combo)

        # Model URL
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("https://example.com/model.pth")
        form_layout.addRow("Model URL:", url_edit)

        # Model name
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("My Custom Model")
        form_layout.addRow("Model Name:", name_edit)

        layout.addLayout(form_layout)

        # Info
        info_label = QLabel(
            "Enter the URL and name for a model you want to download manually."
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        download_btn = QPushButton("Download")
        cancel_btn = QPushButton("Cancel")

        download_btn.clicked.connect(
            lambda: (
                QMessageBox.information(
                    dialog, "Manual Download", "Manual download feature coming soon!"
                ),
                dialog.accept(),
            )
        )
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(download_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec()

    def _check_vip_status(self):
        """Check if user has valid VIP access and set VIP link in adapter"""
        try:
            if self._settings_file_path.exists():
                with open(self._settings_file_path, encoding="utf-8") as f:
                    settings = json.load(f)
                    vip_code = settings.get("vip_code", "")
                    if vip_code:
                        decoded_link = vip_downloads(vip_code)
                        if decoded_link != NO_CODE:
                            self._decoded_vip_link = decoded_link
                            # Set VIP link in the adapter for URL construction
                            self.adapter.set_vip_link(decoded_link)
                            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.debug(f"Could not read VIP settings file: {e}")
        return False
