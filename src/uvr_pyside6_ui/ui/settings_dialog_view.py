"""Settings Dialog View for UVR PySide6 application."""

from PySide6.QtCore import QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class SettingsDialogView(QDialog):
    settings_saved = Signal(dict)
    advanced_settings_requested = Signal(str)  # New signal for advanced settings
    download_button_clicked = Signal()
    download_stop_requested = Signal()

    # download_model_requested = Signal(str, str) # This was an example, presenter connects to button directly

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(600, 500)
        self._is_download_in_progress = False  # Internal state flag

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create the 3 correct tabs matching original UVR
        self._create_settings_guide_tab()
        self._create_additional_settings_tab()
        self._create_download_center_tab()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

    def _create_settings_guide_tab(self):
        """Create the Settings Guide tab (Tab 1) matching original UVR."""
        guide_tab = QWidget()
        main_layout = QVBoxLayout(guide_tab)
        main_layout.setSpacing(20)

        # General Menu section
        general_group = QGroupBox("General Menu")
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(15)

        # Additional Menus selection label
        menu_label = QLabel("Additional Menus Information")
        menu_label.setStyleSheet("font-weight: bold;")
        general_layout.addWidget(menu_label)

        # Main menu dropdown - matches original UVR options exactly
        self.main_menu_combo = QComboBox()
        self.main_menu_combo.addItems(
            [
                "Choose Advanced Menu",  # Default option
                "Advanced VR Options",
                "Advanced MDX-Net Options",
                "Advanced Demucs Options",
                "Ensemble Customization Options",
                "Audio Alignment Tool",
                "Open Information Guide",
                "Open Error Log",
            ]
        )
        self.main_menu_combo.currentTextChanged.connect(self._on_advanced_menu_selected)
        general_layout.addWidget(self.main_menu_combo)

        # Help hints checkbox
        self.help_hints_checkbox = QCheckBox("Enable Help Hints")
        general_layout.addWidget(self.help_hints_checkbox)

        # Application directory button
        self.open_app_dir_btn = QPushButton("Open Application Directory")
        general_layout.addWidget(self.open_app_dir_btn)

        # Reset settings button
        self.reset_settings_btn = QPushButton("Reset All Settings to Default")
        general_layout.addWidget(self.reset_settings_btn)

        main_layout.addWidget(general_group)

        # Delete User Saved Settings section
        delete_group = QGroupBox("Delete User Saved Setting")
        delete_layout = QVBoxLayout(delete_group)

        self.delete_settings_combo = QComboBox()
        self.delete_settings_combo.addItems(["Select Saved Setting"])
        delete_layout.addWidget(self.delete_settings_combo)

        main_layout.addWidget(delete_group)

        # Application Updates section
        update_group = QGroupBox("Application Updates")
        update_layout = QVBoxLayout(update_group)

        self.update_button = QPushButton("Check for Updates")
        update_layout.addWidget(self.update_button)

        self.update_status_label = QLabel("Ready")
        self.update_status_label.setStyleSheet(
            "border: 1px solid #13849f; padding: 8px; background: #1a1a1a; "
            "color: #13849f; border-radius: 3px;"
        )
        self.update_status_label.setAlignment(Qt.AlignCenter)
        update_layout.addWidget(self.update_status_label)

        main_layout.addWidget(update_group)

        main_layout.addStretch()

        self.tab_widget.addTab(guide_tab, "Settings Guide")

        # Try to add an appropriate icon for Settings Guide
        try:
            guide_icon = QIcon(":/uvr/img/help.png")  # or info.png
            if guide_icon.isNull():
                guide_icon = QIcon(":/uvr/img/info.png")
            if not guide_icon.isNull():
                self.tab_widget.setTabIcon(0, guide_icon)
        except Exception as e:
            logger.error(f"Could not load guide icon: {e}")

    def _on_advanced_menu_selected(self, menu_text: str):
        """Handle advanced menu selection - emit signal to open appropriate window."""
        if menu_text != "Choose Advanced Menu":
            self.advanced_settings_requested.emit(menu_text)
            # Reset to default after a short delay to show that the selection was processed
            QTimer.singleShot(
                500, lambda: self.main_menu_combo.setCurrentText("Choose Advanced Menu")
            )

    def _create_additional_settings_tab(self):
        """Create the Additional Settings tab (Tab 2) matching original UVR."""
        settings_tab = QWidget()
        main_layout = QVBoxLayout(settings_tab)
        main_layout.setSpacing(15)

        # Audio Format Settings Group
        audio_group = QGroupBox("Audio Format Settings")
        audio_layout = QFormLayout(audio_group)

        # WAV Type
        self.wav_type_combo = QComboBox()
        self.wav_type_combo.addItems(["PCM_16", "PCM_24", "PCM_32", "FLOAT", "DOUBLE"])
        self.wav_type_combo.setCurrentText("PCM_16")
        audio_layout.addRow("WAV Type:", self.wav_type_combo)

        # MP3 Bitrate
        self.mp3_bitrate_combo = QComboBox()
        self.mp3_bitrate_combo.addItems(
            ["96", "128", "160", "192", "224", "256", "320"]
        )
        self.mp3_bitrate_combo.setCurrentText("320")
        audio_layout.addRow("MP3 Bitrate:", self.mp3_bitrate_combo)

        main_layout.addWidget(audio_group)

        # General Process Settings Group
        process_group = QGroupBox("General Process Settings")
        process_layout = QVBoxLayout(process_group)
        process_layout.setSpacing(8)

        self.test_mode_checkbox = QCheckBox(
            "Settings Test Mode (Processes only the first 30 seconds)"
        )
        process_layout.addWidget(self.test_mode_checkbox)

        self.model_test_mode_checkbox = QCheckBox(
            "Model Test Mode (Adds model name to output)"
        )
        process_layout.addWidget(self.model_test_mode_checkbox)

        self.create_model_folder_checkbox = QCheckBox("Generate Model Folder")
        process_layout.addWidget(self.create_model_folder_checkbox)

        self.accept_any_input_checkbox = QCheckBox("Accept Any Input")
        process_layout.addWidget(self.accept_any_input_checkbox)

        self.notification_chimes_checkbox = QCheckBox("Notification Chimes")
        process_layout.addWidget(self.notification_chimes_checkbox)

        self.normalize_output_checkbox = QCheckBox("Normalize Output")
        process_layout.addWidget(self.normalize_output_checkbox)

        main_layout.addWidget(process_group)

        # Additional Buttons
        self.change_model_defaults_btn = QPushButton("Change Model Defaults")
        main_layout.addWidget(self.change_model_defaults_btn)

        self.vocal_splitter_btn = QPushButton("Vocal Splitter")
        main_layout.addWidget(self.vocal_splitter_btn)

        # GPU Device Selection (if applicable)
        gpu_group = QGroupBox("CUDA Device")
        gpu_layout = QFormLayout(gpu_group)

        self.gpu_device_combo = QComboBox()
        self.gpu_device_combo.addItems(["CPU", "0", "1", "2", "3"])
        gpu_layout.addRow("Device:", self.gpu_device_combo)

        main_layout.addWidget(gpu_group)

        # Sample Mode Settings
        sample_group = QGroupBox("Sample Mode Settings")
        sample_layout = QVBoxLayout(sample_group)

        sample_label = QLabel("Sample Clip Duration")
        sample_layout.addWidget(sample_label)

        self.sample_duration_label = QLabel("30 seconds")
        sample_layout.addWidget(self.sample_duration_label)

        self.sample_duration_slider = QSlider(Qt.Horizontal)
        self.sample_duration_slider.setMinimum(5)
        self.sample_duration_slider.setMaximum(120)
        self.sample_duration_slider.setValue(30)
        self.sample_duration_slider.valueChanged.connect(
            lambda v: self.sample_duration_label.setText(f"{v} seconds")
        )
        sample_layout.addWidget(self.sample_duration_slider)

        main_layout.addWidget(sample_group)

        main_layout.addStretch()

        try:
            settings_icon = QIcon(":/uvr/img/settings.png")
            if settings_icon.isNull():
                settings_icon = QIcon(":/uvr/img/gear.png")  # Alternative
            if not settings_icon.isNull():
                self.tab_widget.addTab(
                    settings_tab, settings_icon, "Additional Settings"
                )
            else:
                self.tab_widget.addTab(settings_tab, "Additional Settings")
        except Exception as e:
            logger.error(f"Error loading settings icon: {e}")
            self.tab_widget.addTab(settings_tab, "Additional Settings")

    def _create_download_center_tab(self):
        """Create the Download Center tab (Tab 3) with clean, simple design matching settings guide."""
        self.download_center_tab = QWidget()
        dc_main_layout = QVBoxLayout(self.download_center_tab)
        dc_main_layout.setSpacing(20)
        dc_main_layout.setContentsMargins(20, 20, 20, 20)

        # Model Selection section - matching settings guide style
        selection_group = QGroupBox("Model Selection")
        selection_layout = QFormLayout(selection_group)
        selection_layout.setSpacing(15)

        # Architecture dropdown
        self.dc_architecture_combo = QComboBox()
        self.dc_architecture_combo.addItems(["VR Architecture", "MDX-Net", "Demucs"])
        self.dc_architecture_combo.setCurrentText("VR Architecture")
        self.dc_architecture_combo.currentTextChanged.connect(
            self._on_architecture_changed
        )
        selection_layout.addRow("Architecture:", self.dc_architecture_combo)

        # Model dropdown
        self.dc_model_combo = QComboBox()
        self.dc_model_combo.currentTextChanged.connect(
            self._on_dc_list_selection_changed
        )
        selection_layout.addRow("Model:", self.dc_model_combo)

        dc_main_layout.addWidget(selection_group)

        # Download section - matching settings guide style
        download_group = QGroupBox("Download")
        download_layout = QVBoxLayout(download_group)
        download_layout.setSpacing(15)

        # Download button
        self.dc_download_btn = QPushButton("Download Selected Model")
        try:
            download_icon = QIcon(":/uvr/img/download.png")
            if not download_icon.isNull():
                self.dc_download_btn.setIcon(download_icon)
                self.dc_download_btn.setIconSize(QSize(20, 20))
        except Exception:
            pass

        self.dc_download_btn.clicked.connect(self.download_button_clicked.emit)
        download_layout.addWidget(self.dc_download_btn)

        dc_main_layout.addWidget(download_group)

        # Progress section - matching settings guide style
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(10)

        # Progress info label
        self.dc_progress_info_label = QLabel("Ready to download")
        progress_layout.addWidget(self.dc_progress_info_label)

        # Progress percentage and bar container
        progress_container = QHBoxLayout()

        # Progress bar with simple styling
        self.dc_progress_bar = QProgressBar()
        self.dc_progress_bar.setMinimum(0)
        self.dc_progress_bar.setMaximum(100)
        self.dc_progress_bar.setValue(0)
        progress_container.addWidget(self.dc_progress_bar, 1)

        # Progress percentage label
        self.dc_progress_percent_label = QLabel("0%")
        self.dc_progress_percent_label.setMinimumWidth(40)
        progress_container.addWidget(self.dc_progress_percent_label)

        progress_layout.addLayout(progress_container)

        dc_main_layout.addWidget(progress_group)

        # Control buttons section - matching settings guide style
        controls_group = QGroupBox("Actions")
        controls_layout = QGridLayout(controls_group)
        controls_layout.setSpacing(10)

        # Stop download button
        self.dc_stop_btn = QPushButton("Stop Download")
        self.dc_stop_btn.setEnabled(False)
        self.dc_stop_btn.clicked.connect(self.download_stop_requested.emit)
        controls_layout.addWidget(self.dc_stop_btn, 0, 0)

        # Refresh list button
        self.dc_refresh_btn = QPushButton("Refresh List")
        controls_layout.addWidget(self.dc_refresh_btn, 0, 1)

        # Download key button
        self.dc_key_btn = QPushButton("VIP Access")
        try:
            key_icon = QIcon(":/uvr/img/key.png")
            if not key_icon.isNull():
                self.dc_key_btn.setIcon(key_icon)
                self.dc_key_btn.setIconSize(QSize(16, 16))
        except Exception:
            pass
        controls_layout.addWidget(self.dc_key_btn, 1, 0)

        # Manual download button
        self.dc_manual_btn = QPushButton("Manual Download")
        controls_layout.addWidget(self.dc_manual_btn, 1, 1)

        dc_main_layout.addWidget(controls_group)

        dc_main_layout.addStretch()

        self.tab_widget.addTab(self.download_center_tab, "Download Center")

        # Try to add download icon for Download Center tab
        try:
            download_tab_icon = QIcon(":/uvr/img/download.png")
            if not download_tab_icon.isNull():
                self.tab_widget.setTabIcon(
                    2, download_tab_icon
                )  # Download Center is tab index 2
        except Exception as e:
            logger.error(f"Could not load download tab icon: {e}")

    def _on_architecture_changed(self):
        """Handle architecture dropdown changes and update model list."""
        self._populate_models_for_architecture()
        self._on_dc_list_selection_changed()

    def _populate_models_for_architecture(self):
        """Populate the model dropdown based on selected architecture."""
        if not hasattr(self, "dc_architecture_combo") or not hasattr(
            self, "dc_model_combo"
        ):
            return

        architecture = self.dc_architecture_combo.currentText()

        # Get models for the selected architecture
        if architecture == "VR Architecture":
            models = getattr(self, "_vr_models", [])
        elif architecture == "MDX-Net":
            models = getattr(self, "_mdx_models", [])
        elif architecture == "Demucs":
            models = getattr(self, "_demucs_models", [])
        else:
            models = []

        # Update model dropdown
        self.dc_model_combo.clear()
        if models:
            self.dc_model_combo.addItems(models)
        else:
            self.dc_model_combo.addItems(["No models available"])

    def _on_model_type_changed(self):
        """Handle model type changes - legacy method for compatibility."""
        self._on_dc_list_selection_changed()

    def _on_dc_list_selection_changed(self):
        """Handle model selection changes."""
        architecture = self.get_selected_model_type()
        model = self.get_selected_model()
        self.dc_download_btn.setEnabled(
            bool(architecture and model and model != "No models available")
        )

    def get_selected_model_type(self):
        """Get the currently selected architecture."""
        if hasattr(self, "dc_architecture_combo"):
            return self.dc_architecture_combo.currentText()
        return None

    def get_selected_model(self):
        """Get the currently selected model."""
        if hasattr(self, "dc_model_combo"):
            model = self.dc_model_combo.currentText()
            return model if model != "No models available" else None
        return None

    def set_vr_models(self, models):
        """Set VR models and update dropdown if VR is selected."""
        self._vr_models = models
        if (
            hasattr(self, "dc_architecture_combo")
            and self.dc_architecture_combo.currentText() == "VR Architecture"
        ):
            self._populate_models_for_architecture()

    def set_mdx_models(self, models):
        """Set MDX models and update dropdown if MDX is selected."""
        self._mdx_models = models
        if (
            hasattr(self, "dc_architecture_combo")
            and self.dc_architecture_combo.currentText() == "MDX-Net"
        ):
            self._populate_models_for_architecture()

    def set_demucs_models(self, models):
        """Set Demucs models and update dropdown if Demucs is selected."""
        self._demucs_models = models
        if (
            hasattr(self, "dc_architecture_combo")
            and self.dc_architecture_combo.currentText() == "Demucs"
        ):
            self._populate_models_for_architecture()

    def set_download_in_progress_state(self, in_progress: bool):
        """Enable/disable controls based on download state."""
        self._is_download_in_progress = in_progress
        self.dc_download_btn.setEnabled(not in_progress)
        self.dc_stop_btn.setEnabled(in_progress)

        # For new dropdown interface
        if hasattr(self, "dc_architecture_combo"):
            self.dc_architecture_combo.setEnabled(not in_progress)
        if hasattr(self, "dc_model_combo"):
            self.dc_model_combo.setEnabled(not in_progress)

    # Legacy compatibility methods (keeping for presenter)
    def set_download_center_model_types(self, types):
        """Legacy method for compatibility."""
        # Update architecture dropdown if it exists
        if hasattr(self, "dc_architecture_combo"):
            current = self.dc_architecture_combo.currentText()
            self.dc_architecture_combo.clear()
            self.dc_architecture_combo.addItems(types)
            # Restore selection if possible
            index = self.dc_architecture_combo.findText(current)
            if index >= 0:
                self.dc_architecture_combo.setCurrentIndex(index)

    def set_downloadable_models_list(self, models):
        """Legacy method for compatibility."""
        # Update model dropdown if it exists
        if hasattr(self, "dc_model_combo"):
            current = self.dc_model_combo.currentText()
            self.dc_model_combo.clear()
            if models:
                self.dc_model_combo.addItems(models)
            else:
                self.dc_model_combo.addItems(["No models available"])
            # Restore selection if possible
            index = self.dc_model_combo.findText(current)
            if index >= 0:
                self.dc_model_combo.setCurrentIndex(index)

    def closeEvent(self, event: QCloseEvent):
        """Saves settings before closing if not cancelled explicitly."""
        if not hasattr(self, "_rejected"):
            self.settings_saved.emit(self.get_settings())
        super().closeEvent(event)

    def accept(self):
        """Accepts dialog and saves settings."""
        self.settings_saved.emit(self.get_settings())
        super().accept()

    def reject(self):
        """Rejects dialog without saving."""
        self._rejected = True
        super().reject()

    def get_settings(self) -> dict:
        """Get current settings from all tabs."""
        return {
            # Settings Guide tab
            "main_menu": self.main_menu_combo.currentText(),
            "help_hints": self.help_hints_checkbox.isChecked(),
            # Additional Settings tab
            "wav_type": self.wav_type_combo.currentText(),
            "mp3_bitrate": self.mp3_bitrate_combo.currentText(),
            "test_mode": self.test_mode_checkbox.isChecked(),
            "model_test_mode": self.model_test_mode_checkbox.isChecked(),
            "create_model_folder": self.create_model_folder_checkbox.isChecked(),
            "accept_any_input": self.accept_any_input_checkbox.isChecked(),
            "notification_chimes": self.notification_chimes_checkbox.isChecked(),
            "normalize_output": self.normalize_output_checkbox.isChecked(),
            "gpu_device": self.gpu_device_combo.currentText(),
            "sample_duration": self.sample_duration_slider.value(),
        }

    @Slot(dict)
    def load_settings(self, settings_data: dict):
        """Load settings into the dialog."""
        # Settings Guide tab
        if "main_menu" in settings_data:
            index = self.main_menu_combo.findText(settings_data["main_menu"])
            if index >= 0:
                self.main_menu_combo.setCurrentIndex(index)

        if "help_hints" in settings_data:
            self.help_hints_checkbox.setChecked(settings_data["help_hints"])

        # Additional Settings tab
        if "wav_type" in settings_data:
            index = self.wav_type_combo.findText(settings_data["wav_type"])
            if index >= 0:
                self.wav_type_combo.setCurrentIndex(index)

        if "mp3_bitrate" in settings_data:
            index = self.mp3_bitrate_combo.findText(settings_data["mp3_bitrate"])
            if index >= 0:
                self.mp3_bitrate_combo.setCurrentIndex(index)

        if "test_mode" in settings_data:
            self.test_mode_checkbox.setChecked(settings_data["test_mode"])

        if "model_test_mode" in settings_data:
            self.model_test_mode_checkbox.setChecked(settings_data["model_test_mode"])

        if "create_model_folder" in settings_data:
            self.create_model_folder_checkbox.setChecked(
                settings_data["create_model_folder"]
            )

        if "accept_any_input" in settings_data:
            self.accept_any_input_checkbox.setChecked(settings_data["accept_any_input"])

        if "notification_chimes" in settings_data:
            self.notification_chimes_checkbox.setChecked(
                settings_data["notification_chimes"]
            )

        if "normalize_output" in settings_data:
            self.normalize_output_checkbox.setChecked(settings_data["normalize_output"])

        if "gpu_device" in settings_data:
            index = self.gpu_device_combo.findText(settings_data["gpu_device"])
            if index >= 0:
                self.gpu_device_combo.setCurrentIndex(index)

        if "sample_duration" in settings_data:
            self.sample_duration_slider.setValue(settings_data["sample_duration"])

    def show_status_message(self, message: str, timeout: int = 0):
        """Show a status message in the download center progress area."""
        if hasattr(self, "dc_progress_info_label"):
            self.dc_progress_info_label.setText(message)
            if timeout > 0:
                QTimer.singleShot(
                    timeout, lambda: self.dc_progress_info_label.setText("")
                )
