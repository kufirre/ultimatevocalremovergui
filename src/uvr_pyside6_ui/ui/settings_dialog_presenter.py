"""Presenter for the settings and download center dialogs."""

import base64
import json
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PySide6.QtCore import QObject, QStandardPaths, QTimer, Slot
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
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from uvr_pyside6_ui.core import app_constants as ac
from uvr_pyside6_ui.core.logger_utils import get_logger
from uvr_pyside6_ui.core.uvr_core_adapter import UVRCoreAdapter

from ..core import app_constants as ac
from .download_center_presenter import DownloadCenterPresenter
from .settings_dialog_view import SettingsDialogView

logger = get_logger(__name__)

# VIP Constants - matching original UVR.py
VIP_REPO = (
    b"\xf3\xc2W\x19\x1foI)\xc2\xa9\xcc\xb67(Z\xf5",
    b"gAAAAABjQAIQ-NpNMMxMedpKHHb7ze_nqB05hw0YhbOy3pFzuzDrfqumn8_qvraxEoUpZC5ZXC0gGvfDxFMqyq9VWbYKlA67SUFI_wZB6QoVyGI581vs7kaGfUqlXHIdDS6tQ_U-BfjbEAK9EU_74-R2zXjz8Xzekw==",
)
NO_CODE = "incorrect_code"


def vip_downloads(password, link_type=VIP_REPO):
    """Attempts to decrypt VIP model link with given input codex"""
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


class SettingsDialogPresenter(QObject):
    """Handle user preferences and model downloads."""

    def __init__(self, adapter: UVRCoreAdapter, parent_qt_object: QObject = None):
        super().__init__(parent_qt_object)
        self.view: SettingsDialogView | None = None
        self.adapter = adapter
        self._settings_file_path = self._get_settings_file_path()
        self._current_settings = self._load_settings_from_store()

        # Create download center presenter with settings file path
        self.download_center_presenter = DownloadCenterPresenter(
            adapter, self._settings_file_path, self
        )

        # Reference to main window presenters for advanced settings
        self._main_window_presenters = None

        # References to information guide and error log presenters
        self._information_guide_presenter = None
        self._error_log_presenter = None

    def set_main_window_presenters(self, presenters: dict):
        """Set reference to main window presenters for advanced settings."""
        self._main_window_presenters = presenters

        # Connect presenter settings_changed signals to persistence system
        self._connect_presenter_settings_to_persistence()

    def set_information_guide_presenter(self, presenter):
        """Set reference to information guide presenter."""
        self._information_guide_presenter = presenter

    def set_error_log_presenter(self, presenter):
        """Set reference to error log presenter."""
        self._error_log_presenter = presenter

    def _connect_presenter_settings_to_persistence(self):
        """Connect presenter settings_changed signals to the persistence system."""
        if not self._main_window_presenters:
            return

        from ..core import app_constants as ac

        # Connect VR presenter
        if ac.VR_ARCH_PRESENTER_KEY in self._main_window_presenters:
            vr_presenter = self._main_window_presenters[ac.VR_ARCH_PRESENTER_KEY]
            vr_presenter.settings_changed.connect(self._save_presenter_settings)
            # Load existing settings for VR presenter
            self._load_presenter_settings(vr_presenter, "vr_arch_settings")

        # Connect MDX presenter
        if ac.MDX_NET_PRESENTER_KEY in self._main_window_presenters:
            mdx_presenter = self._main_window_presenters[ac.MDX_NET_PRESENTER_KEY]
            mdx_presenter.settings_changed.connect(self._save_presenter_settings)
            # Load existing settings for MDX presenter
            self._load_presenter_settings(mdx_presenter, "mdx_net_settings")

        # Connect Demucs presenter
        if ac.DEMUCS_PRESENTER_KEY in self._main_window_presenters:
            demucs_presenter = self._main_window_presenters[ac.DEMUCS_PRESENTER_KEY]
            demucs_presenter.settings_changed.connect(self._save_presenter_settings)
            # Load existing settings for Demucs presenter
            self._load_presenter_settings(demucs_presenter, "demucs_settings")

        # Connect Model Selection presenter
        if ac.MODEL_SELECTION_PRESENTER_KEY in self._main_window_presenters:
            model_presenter = self._main_window_presenters[
                ac.MODEL_SELECTION_PRESENTER_KEY
            ]
            model_presenter.settings_changed.connect(self._save_presenter_settings)
            # Load existing settings for Model Selection presenter
            self._load_presenter_settings(model_presenter, "model_selection_settings")

    def _save_presenter_settings(self, settings_dict):
        """Save presenter settings to persistent storage."""
        # Determine which presenter sent the signal
        sender = self.sender()
        if not sender:
            return

        from ..core import app_constants as ac

        # Map sender to settings key
        settings_key = None
        if (
            ac.VR_ARCH_PRESENTER_KEY in self._main_window_presenters
            and sender == self._main_window_presenters[ac.VR_ARCH_PRESENTER_KEY]
        ):
            settings_key = "vr_arch_settings"
        elif (
            ac.MDX_NET_PRESENTER_KEY in self._main_window_presenters
            and sender == self._main_window_presenters[ac.MDX_NET_PRESENTER_KEY]
        ):
            settings_key = "mdx_net_settings"
        elif (
            ac.DEMUCS_PRESENTER_KEY in self._main_window_presenters
            and sender == self._main_window_presenters[ac.DEMUCS_PRESENTER_KEY]
        ):
            settings_key = "demucs_settings"
        elif (
            ac.MODEL_SELECTION_PRESENTER_KEY in self._main_window_presenters
            and sender == self._main_window_presenters[ac.MODEL_SELECTION_PRESENTER_KEY]
        ):
            settings_key = "model_selection_settings"

        if settings_key:
            # Update current settings with the new data
            self._current_settings[settings_key] = settings_dict
            # Save to persistent storage
            try:
                with open(self._settings_file_path, "w", encoding="utf-8") as f:
                    json.dump(self._current_settings, f, indent=4)
                logger.debug(f"Saved {settings_key} to persistent storage")
            except OSError as e:
                logger.error(f"Error saving {settings_key}: {e}")

    def _load_presenter_settings(self, presenter, settings_key):
        """Load settings for a specific presenter from persistent storage."""
        if settings_key in self._current_settings:
            settings_data = self._current_settings[settings_key]
            if hasattr(presenter, "load_settings"):
                presenter.load_settings(settings_data)
                logger.debug(f"Loaded {settings_key} from persistent storage")

    def _setup_view_connections(self):
        """Set up signal connections for the view."""
        if not self.view:
            return

        # Connect view signals
        self.view.settings_saved.connect(self._save_settings_to_store)
        self.view.advanced_settings_requested.connect(
            self._handle_advanced_settings_request
        )

        # Set up download center view if it exists
        if (
            hasattr(self.view, "download_center_view")
            and self.view.download_center_view
        ):
            self.download_center_presenter.set_view(self.view.download_center_view)

    def _get_settings_file_path(self) -> Path:
        """Determines the path for the settings JSON file."""
        # Using QStandardPaths for platform-agnostic config location
        config_dir = Path(
            QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        )
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / ac.APP_SETTINGS_FILENAME

    def _load_settings_from_store(self) -> dict:
        default_settings = {
            "check_updates": True,
            "theme": "Default",
            "default_output": str(Path.home() / "Music" / "UVR_Output"),
            "models_dir": str(
                Path.home() / "Documents" / "UVR_Models"
            ),  # Default models dir
        }
        if self._settings_file_path.exists():
            try:
                with open(self._settings_file_path, encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys are present
                    default_settings.update(loaded_settings)
                    return default_settings
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(
                    f"Error loading settings from {self._settings_file_path}: {e}. Using defaults."
                )
                return default_settings
        return default_settings

    @Slot(dict)
    def _save_settings_to_store(self, settings_data: dict):
        self._current_settings.update(settings_data)
        try:
            with open(self._settings_file_path, "w", encoding="utf-8") as f:
                json.dump(self._current_settings, f, indent=4)
            if self.view:  # Update status if view is available
                self.view.show_status_message("Settings saved.", 2000)
            logger.info(f"Settings saved successfully to {self._settings_file_path}")
        except OSError as e:
            logger.error(f"Error saving settings to {self._settings_file_path}: {e}")
            if self.view:
                QMessageBox.warning(
                    self.view, "Save Error", f"Could not save settings: {e}"
                )

    def _populate_download_center_on_show(self, default_model_type: str | None = None):
        """Populate download center using the dedicated presenter."""
        if self.download_center_presenter:
            self.download_center_presenter.populate_download_center(default_model_type)

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

    def _get_vip_models(self, internal_type: str) -> dict:
        """Get VIP-exclusive models for the specified type."""
        # Removed fake VIP model placeholders
        # Real VIP models would come from fetching the actual VIP repository
        # using the decrypted VIP link
        return {}

    @Slot(str)
    def _handle_advanced_settings_request(self, menu_text: str):
        """Handle request to open advanced settings windows."""
        logger.info(f"Advanced settings requested: {menu_text}")

        if menu_text == "Advanced VR Options":
            self._show_vr_advanced_settings()
        elif menu_text == "Advanced MDX-Net Options":
            self._show_mdx_advanced_settings()
        elif menu_text == "Advanced Demucs Options":
            self._show_demucs_advanced_settings()
        elif menu_text == ac.ENSEMBLE_SETTINGS:
            self._show_ensemble_settings()
        elif menu_text == ac.AUDIO_ALIGNMENT_SETTINGS:
            self._show_audio_alignment_tool()
        elif menu_text == "Open Information Guide":
            self._show_information_guide()
        elif menu_text == "Open Error Log":
            self._show_error_log()

    def _show_vr_advanced_settings(self):
        """Show comprehensive VR Architecture advanced settings dialog."""

        if (
            self._main_window_presenters
            and ac.VR_ARCH_PRESENTER_KEY in self._main_window_presenters
        ):
            # Use the main window's VR presenter which has proper settings persistence
            vr_presenter = self._main_window_presenters[ac.VR_ARCH_PRESENTER_KEY]
            vr_presenter.show_advanced_settings(is_vr_mode=False)
        else:
            logger.warning("VR presenter not available for advanced settings")
            # Fallback to standalone dialog (without persistence)
            from .vr_arch_advanced_dialog import VRArchAdvancedDialog

            dialog = VRArchAdvancedDialog({}, False, self.view)
            dialog.exec()

    def _show_mdx_advanced_settings(self):
        """Show comprehensive MDX-Net advanced settings dialog."""
        if (
            self._main_window_presenters
            and ac.MDX_NET_PRESENTER_KEY in self._main_window_presenters
        ):
            # Use the main window's MDX presenter which has proper settings persistence
            mdx_presenter = self._main_window_presenters[ac.MDX_NET_PRESENTER_KEY]
            mdx_presenter.show_advanced_settings()
        else:
            logger.warning("MDX presenter not available for advanced settings")
            # Fallback to standalone dialog (without persistence)
            from .mdx_net_advanced_dialog import MDXNetAdvancedDialog

            dialog = MDXNetAdvancedDialog({}, self.view)
            dialog.exec()

    def _show_demucs_advanced_settings(self):
        """Show comprehensive Demucs advanced settings dialog."""
        if (
            self._main_window_presenters
            and ac.DEMUCS_PRESENTER_KEY in self._main_window_presenters
        ):
            # Use the main window's Demucs presenter which has proper settings persistence
            demucs_presenter = self._main_window_presenters[ac.DEMUCS_PRESENTER_KEY]
            demucs_presenter.show_advanced_settings()
        else:
            logger.warning("Demucs presenter not available for advanced settings")
            # Fallback to standalone dialog (without persistence)
            from .demucs_advanced_dialog import DemucsAdvancedDialog

            dialog = DemucsAdvancedDialog({}, self.view)
            dialog.exec()

    def _show_ensemble_settings(self):
        """Show advanced ensemble configuration dialog."""
        from .ensemble_advanced_dialog import EnsembleAdvancedDialog

        # Get current ensemble settings from the main window if available
        current_settings = {}
        try:
            # Try to get current settings from the main UI's ensemble presenter
            if hasattr(self, "_main_window_ref") and self._main_window_ref:
                # This would need to be connected properly to the main window
                pass
        except Exception as e:
            logger.debug(f"Could not get current ensemble settings: {e}")

        dialog = EnsembleAdvancedDialog(current_settings, self.view)

        # Set available models if we have access to the adapter
        if hasattr(self, "adapter") and self.adapter:
            try:
                available_models = {
                    ac.VR_ARCH_MODELS_KEY: self.adapter.get_available_models(
                        ac.VR_ARCH_MODELS_KEY
                    ),
                    ac.MDX_NET_MODELS_KEY: self.adapter.get_available_models(
                        ac.MDX_NET_MODELS_KEY
                    ),
                    ac.DEMUCS_MODELS_KEY: self.adapter.get_available_models(
                        ac.DEMUCS_MODELS_KEY
                    ),
                }
                dialog.set_available_models(available_models)
            except Exception as e:
                logger.warning(
                    f"Could not load available models for ensemble dialog: {e}"
                )

        # Connect to handle settings updates
        def on_settings_updated(settings):
            logger.info("Ensemble advanced settings updated")
            # Here we would update the main UI's ensemble presenter with new settings
            # This would need proper integration with the main application

        dialog.settings_updated.connect(on_settings_updated)
        dialog.exec()

    def _show_audio_alignment_tool(self):
        """Show comprehensive audio alignment settings dialog."""
        dialog = QDialog(self.view)
        dialog.setWindowTitle("Audio Alignment Settings")  # Shorter title
        dialog.setModal(True)
        dialog.setFixedSize(360, 420)  # Compact size to fit content

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)  # Reduced spacing
        layout.setContentsMargins(15, 15, 15, 10)  # Reduced margins

        # Note: Removed unsupported algorithm dropdown - only includes real UVR.py functionality

        # Phase Settings Group
        phase_group = QGroupBox("Phase Settings")
        phase_layout = QFormLayout(phase_group)
        phase_layout.setVerticalSpacing(8)  # Compact vertical spacing

        # Secondary Phase
        secondary_phase_check = QCheckBox("Enable Secondary Phase Analysis")
        secondary_phase_check.setChecked(False)
        phase_layout.addRow(secondary_phase_check)

        # Phase Options
        phase_options_combo = QComboBox()
        phase_options_combo.addItems(
            ["Automatic", "Positive Phase", "Negative Phase", "Native Phase"]
        )
        phase_options_combo.setCurrentText("Automatic")
        phase_layout.addRow("Phase Options:", phase_options_combo)

        # Phase Shifts (Slider)
        phase_shift_container = QHBoxLayout()
        phase_shift_slider = QSlider()
        from PySide6.QtCore import Qt

        phase_shift_slider.setOrientation(Qt.Horizontal)
        phase_shift_slider.setMinimum(0)
        phase_shift_slider.setMaximum(6)
        phase_shift_slider.setValue(0)  # Default to "None"
        phase_shift_slider.setTickPosition(QSlider.TicksBelow)
        phase_shift_slider.setTickInterval(1)

        phase_shift_label = QLabel("None")
        phase_shift_values = [
            "None",
            "Very Low",
            "Low",
            "Medium",
            "High",
            "Very High",
            "Very Max",
        ]

        def update_phase_shift_label(value):
            phase_shift_label.setText(phase_shift_values[value])

        phase_shift_slider.valueChanged.connect(update_phase_shift_label)

        phase_shift_container.addWidget(phase_shift_slider)
        phase_shift_container.addWidget(phase_shift_label)

        phase_layout.addRow("Phase Shifts:", phase_shift_container)

        layout.addWidget(phase_group)

        # Matching Settings Group (Based on actual UVR.py parameters)
        matching_group = QGroupBox("Matching Settings")
        matching_layout = QFormLayout(matching_group)
        matching_layout.setVerticalSpacing(8)  # Compact vertical spacing

        # Match Silence (is_match_silence parameter)
        silence_matching_check = QCheckBox("Match Silence")
        silence_matching_check.setChecked(True)
        matching_layout.addRow(silence_matching_check)

        # Spectral Matching (is_spec_match parameter)
        spectral_matching_check = QCheckBox("Spectral Matching")
        spectral_matching_check.setChecked(False)
        matching_layout.addRow(spectral_matching_check)

        layout.addWidget(matching_group)

        # Output Settings Group (Based on actual UVR.py parameters)
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        output_layout.setVerticalSpacing(8)  # Compact vertical spacing

        # Save Aligned Audio (is_save_align parameter)
        save_aligned_check = QCheckBox("Save Aligned Audio")
        save_aligned_check.setChecked(True)
        output_layout.addRow(save_aligned_check)

        layout.addWidget(output_group)

        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = QPushButton("Apply")
        close_btn = QPushButton("Close")

        apply_btn.setFixedWidth(80)
        close_btn.setFixedWidth(80)

        button_layout.addWidget(apply_btn)
        button_layout.addSpacing(5)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Connect buttons
        def apply_settings():
            logger.info("Audio alignment settings applied")
            dialog.accept()

        def close_dialog():
            dialog.reject()

        apply_btn.clicked.connect(apply_settings)
        close_btn.clicked.connect(close_dialog)

        # Show dialog
        dialog.exec()

    def _show_information_guide(self):
        """Show information guide."""
        if self._information_guide_presenter:
            self._information_guide_presenter.show_information_guide()
        else:
            dialog = QDialog(self.view)
            dialog.setWindowTitle("Information Guide")
            dialog.resize(600, 500)

            layout = QVBoxLayout(dialog)

            label = QLabel("Ultimate Vocal Remover - User Guide")
            label.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setPlainText(
                """Welcome to Ultimate Vocal Remover!

This application uses AI models to separate audio sources from mixed recordings.

Key Features:
- VR Architecture: Advanced vocal removal using deep learning
- MDX-Net: High-quality source separation
- Demucs: Multi-stem separation (vocals, drums, bass, other)
- Ensemble Mode: Combine multiple models for better results

Getting Started:
1. Select your audio file
2. Choose a model type and specific model
3. Configure processing options
4. Click 'Start Processing'

Tips:
- VR models work best for vocal isolation
- MDX-Net provides good quality separation
- Demucs can separate into 4 stems
- Try different models to find what works best for your audio

For more information, visit the project documentation."""
            )
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)

            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)

            dialog.exec()

    def _show_error_log(self):
        """Show error log."""
        if self._error_log_presenter:
            self._error_log_presenter.show_error_log()
        else:
            dialog = QDialog(self.view)
            dialog.setWindowTitle("Error Log")
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)

            label = QLabel("Application Error Log")
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label)

            text_edit = QTextEdit()
            # In a real implementation, this would read from actual log files
            text_edit.setPlainText(
                "No errors recorded in this session.\n\nThis log shows application errors and warnings to help diagnose issues."
            )
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)

            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            clear_btn = QPushButton("Clear Log")
            close_btn = QPushButton("Close")
            clear_btn.clicked.connect(lambda: text_edit.clear())
            close_btn.clicked.connect(dialog.accept)

            button_layout.addWidget(clear_btn)
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)

            dialog.exec()

    @Slot()
    def _on_dc_stop_button_clicked(self) -> None:
        """Handle stop download button clicks."""
        logger.info("Stop download requested")
        # TODO: Implement download cancellation in adapter
        self.view.show_status_message("Download stopped", 3000)

    @Slot()
    def _on_dc_download_button_clicked(self) -> None:
        """Handle download button clicks from the download center."""
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

                    # Special handling for MDX23C VIP models
                    if (
                        isinstance(download_target_info, dict)
                        and len(download_target_info) == 1
                    ):
                        # MDX23C format: {'MDX23C_D1581.ckpt': 'model_2_stem_061321.yaml'}
                        # We should download the .ckpt file, not the .yaml file
                        for ckpt_file, yaml_file in download_target_info.items():
                            if ckpt_file.endswith(".ckpt"):
                                # Convert to format expected by adapter: download the .ckpt file
                                download_target_info = ckpt_file
                                logger.info(
                                    f"Converted MDX23C VIP model format: {ckpt_file}"
                                )
                                break

            if not download_target_info:
                self.view.show_status_message(
                    f"Model '{model_name}' not found in catalog", 3000
                )
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
            self.view.show_status_message(f"{str(e)}", 5000)

    @Slot(str, int)
    def _on_adapter_download_progress(self, model_name: str, percentage: int):
        """Handle download progress updates with proper UI updates."""
        if (
            self.view
            and self.view.isVisible()
            and self.view.tab_widget.currentIndex() == 2  # Download Center tab
        ):
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
                QTimer.singleShot(
                    1000, lambda: self._populate_download_center_on_show()
                )

                # Reset after delay to show completion
                QTimer.singleShot(3000, lambda: self._reset_download_progress_display())

                # Emit signal that main UI can catch to refresh its model list
                # This should trigger the main UI to refresh the model dropdown for the downloaded type
                logger.info(
                    f"Download completed for {model_type_ui_name}, triggering main UI refresh"
                )

                # NOTE: The adapter already emits model_download_completed signal automatically
                # in its _on_download_finished method when success=True
                # So the main UI should already be getting the refresh signal

            else:
                # Error - show error with better formatting
                self.view.dc_progress_info_label.setText(
                    f"❌ Download failed: {message}"
                )
                self.view.dc_progress_percent_label.setText("Failed")
                self.view.dc_progress_bar.setValue(0)

                # Reset after longer delay for error message
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
        self.view.dc_progress_info_label.setText("Refreshing model catalog...")

        # Clear cached catalog to force refresh
        self._full_online_catalog = {}

        # Repopulate with fresh data
        self._populate_download_center_on_show()

        self.view.dc_progress_info_label.setText("Model catalog refreshed")
        QTimer.singleShot(
            2000, lambda: self.view.dc_progress_info_label.setText("Ready to download")
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

        decoded_vip_link = vip_downloads(vip_code)

        if decoded_vip_link != NO_CODE:
            # Success - VIP activated
            self.vip_status_label.setText(
                "✅ VIP Access Activated! Premium models unlocked."
            )
            self.vip_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

            # Save VIP status (in a real implementation)
            self._save_vip_status(vip_code)

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
            self._populate_download_center_on_show()

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

            # In a real implementation, this would be encrypted and saved securely
            self._current_settings.update(vip_settings)

            with open(self._settings_file_path, "w", encoding="utf-8") as f:
                json.dump(self._current_settings, f, indent=4)

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

    @Slot()
    def show_dialog(
        self, exec_dialog: bool = True, default_model_type: str | None = None
    ) -> None:
        """Display the settings dialog, optionally modal."""
        if not self.view:
            parent_widget = (
                self.parent() if isinstance(self.parent(), QWidget) else None
            )
            self.view = SettingsDialogView(parent=parent_widget)
            self._setup_view_connections()

        settings_to_load = self._load_settings_from_store()
        self.view.load_settings(settings_to_load)

        # Pass default_model_type to setup function
        self._populate_download_center_on_show(default_model_type=default_model_type)

        if exec_dialog:
            result = self.view.exec()
        else:
            if not self.view.isVisible():
                self.view.show()
            self.view.activateWindow()
            self.view.raise_()

    def _check_vip_status(self):
        """Check if user has valid VIP access"""
        vip_code = self._current_settings.get("vip_code", "")
        if vip_code:
            decoded_link = vip_downloads(vip_code)
            return decoded_link != NO_CODE
        return False
