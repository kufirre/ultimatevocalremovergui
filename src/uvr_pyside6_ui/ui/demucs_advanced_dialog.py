import logging
import os
import platform
import subprocess

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class DemucsAdvancedDialog(QDialog):
    """Advanced Demucs settings dialog matching UVR.py structure."""

    settings_updated = Signal(dict)

    def __init__(self, current_settings=None, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings or {}
        self.setWindowTitle("Advanced Demucs Options")
        self.setMinimumSize(450, 500)

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Create tab widget for organizing settings with modern styling
        tab_widget = QTabWidget()
        tab_widget.setTabPosition(QTabWidget.North)
        tab_widget.setUsesScrollButtons(False)  # Disable scroll buttons for modern look
        tab_widget.setElideMode(Qt.ElideNone)  # Don't elide tab text
        tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #4a637a;
                background-color: #2c3e50;
            }
            QTabBar::tab {
                background-color: #34495e;
                color: #ecf0f1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2c3e50;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover:!selected {
                background-color: #4a637a;
            }
        """
        )
        layout.addWidget(tab_widget)

        # Advanced Settings Tab
        advanced_tab = self._create_advanced_tab()
        tab_widget.addTab(advanced_tab, "Advanced")

        # Secondary Model Tab
        secondary_tab = self._create_secondary_model_tab()
        tab_widget.addTab(secondary_tab, "Secondary Model")

        # Preprocess Model Tab
        preprocess_tab = self._create_preprocess_model_tab()
        tab_widget.addTab(preprocess_tab, "Preprocess Model")

        # Vocal Splitter Tab
        vocal_tab = self._create_vocal_splitter_tab()
        tab_widget.addTab(vocal_tab, "Vocal Splitter")

        # Button box with Apply/Close positioned closer together like OK/Cancel
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right

        # Create individual buttons for better control over spacing
        self.apply_btn = QPushButton("Apply")
        self.close_btn = QPushButton("Close")

        # Set consistent button sizes
        button_width = 80
        self.apply_btn.setFixedWidth(button_width)
        self.close_btn.setFixedWidth(button_width)

        # Connect signals
        self.apply_btn.clicked.connect(self._apply_settings)
        self.close_btn.clicked.connect(self.reject)

        # Add buttons with minimal spacing between them
        button_layout.addWidget(self.apply_btn)
        button_layout.addSpacing(5)  # Small gap between buttons
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _open_models_folder(self):
        """Open the Demucs models folder in the system file manager."""
        logger.info("Open Demucs models folder requested")

        try:
            # Determine the Demucs models directory from project root
            from ..core.model_data import DEMUCS_MODELS_DIR_PATH

            demucs_models_dir = DEMUCS_MODELS_DIR_PATH

            # Create the directory if it doesn't exist
            demucs_models_dir.mkdir(parents=True, exist_ok=True)

            # Open the folder in the system file manager
            system = platform.system()
            if system == "Windows":
                os.startfile(str(demucs_models_dir))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(demucs_models_dir)])
            elif system == "Linux":
                subprocess.run(["xdg-open", str(demucs_models_dir)])
            else:
                logger.warning(f"Unsupported platform for opening folder: {system}")
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self, "Models Folder", f"Demucs models folder: {demucs_models_dir}"
                )

        except Exception as e:
            logger.error(f"Error opening models folder: {e}")
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self, "Open Folder Error", f"Failed to open models folder: {str(e)}"
            )

    def _vocal_splitter_options(self):
        """Open vocal splitter options dialog."""
        logger.info("Vocal splitter options requested")
        # TODO: Implement vocal splitter options dialog
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Vocal Splitter Options",
            "Vocal splitter options dialog will be implemented here.",
        )

    def _clear_autoset_cache(self):
        """Clear the autoset cache."""
        logger.info("Clear autoset cache requested")
        # TODO: Implement cache clearing functionality
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self, "Clear Cache", "AutoSet cache cleared successfully."
        )

    def _create_advanced_tab(self):
        """Create the advanced settings tab."""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # Demucs Settings Group
        demucs_group = QGroupBox("Demucs Settings")
        demucs_layout = QFormLayout(demucs_group)
        demucs_layout.setSpacing(10)

        # Shifts (0-5)
        self.shifts_spin = QSpinBox()
        self.shifts_spin.setRange(0, 5)
        self.shifts_spin.setValue(2)
        demucs_layout.addRow("Shifts:", self.shifts_spin)

        # Overlap (0.1-0.99)
        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setRange(0.1, 0.99)
        self.overlap_spin.setSingleStep(0.05)
        self.overlap_spin.setValue(0.25)
        self.overlap_spin.setDecimals(2)
        demucs_layout.addRow("Overlap:", self.overlap_spin)

        # Shift Conversion Pitch - slider with value label beside it
        pitch_layout = QHBoxLayout()
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.setTickInterval(6)
        self.pitch_slider.setMinimumWidth(180)

        self.pitch_value_label = QLabel("0")
        self.pitch_value_label.setMinimumWidth(30)
        self.pitch_value_label.setAlignment(Qt.AlignCenter)
        self.pitch_value_label.setStyleSheet("font-weight: bold; color: #3498db;")

        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_value_label.setText(str(v))
        )

        pitch_layout.addWidget(self.pitch_slider)
        pitch_layout.addWidget(self.pitch_value_label)
        demucs_layout.addRow("Shift Conversion Pitch:", pitch_layout)

        layout.addWidget(demucs_group)

        # Processing Options Group
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(8)

        # Split Mode checkbox
        self.split_mode_check = QCheckBox("Split Mode")
        self.split_mode_check.setChecked(True)
        options_layout.addWidget(self.split_mode_check)

        # Combine Stems checkbox
        self.combine_stems_check = QCheckBox("Combine Stems")
        self.combine_stems_check.setChecked(False)
        options_layout.addWidget(self.combine_stems_check)

        # Spectral Inversion checkbox
        self.invert_spec_check = QCheckBox("Spectral Inversion")
        self.invert_spec_check.setChecked(False)
        options_layout.addWidget(self.invert_spec_check)

        layout.addWidget(options_group)

        # Actions Group
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(8)

        self.clear_cache_btn = QPushButton("Clear AutoSet Cache")
        self.clear_cache_btn.clicked.connect(self._clear_autoset_cache)
        actions_layout.addWidget(self.clear_cache_btn)

        self.open_models_btn = QPushButton("Open Models Folder")
        self.open_models_btn.clicked.connect(self._open_models_folder)
        actions_layout.addWidget(self.open_models_btn)

        layout.addWidget(actions_group)
        layout.addStretch()  # Push everything to the top

        return widget

    def _create_secondary_model_tab(self):
        """Create the secondary model tab with vertical layout to fit without scrolling."""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)

        # Enable Secondary Model
        self.enable_secondary_check = QCheckBox("Enable Secondary Model")
        self.enable_secondary_check.setChecked(False)
        layout.addWidget(self.enable_secondary_check)

        # Store secondary model widgets for enable/disable
        self.secondary_widgets = []

        # Create vertical layout for the four sections
        # 1. Vocals/Instruments Section
        vocals_group = self._create_secondary_section("Vocals/Instruments", "vocals")
        layout.addWidget(vocals_group)

        # 2. Bass/No Bass Section
        bass_group = self._create_secondary_section("Bass/No Bass", "bass")
        layout.addWidget(bass_group)

        # 3. Drums/No Drums Section
        drums_group = self._create_secondary_section("Drums/No Drums", "drums")
        layout.addWidget(drums_group)

        # 4. Other/No Other Section
        other_group = self._create_secondary_section("Other/No Other", "other")
        layout.addWidget(other_group)

        layout.addStretch()

        # Connect enable checkbox
        self.enable_secondary_check.toggled.connect(self._toggle_secondary_widgets)

        return widget

    def _create_secondary_section(self, title, section_name):
        """Create a compact secondary model section."""
        group = QGroupBox(title)
        group_layout = QHBoxLayout(group)  # Use horizontal layout for compactness
        group_layout.setSpacing(8)

        # Model combo box
        model_combo = QComboBox()
        model_combo.addItems(
            [
                "No Model",
                "UVR-MDX-NET-1_9.onnx",
                "UVR-MDX-NET-2_9.onnx",
                "UVR-MDX-NET-3_9.onnx",
                "Kim_Vocal_1.onnx",
            ]
        )
        model_combo.setEnabled(False)
        model_combo.setMinimumWidth(180)

        # Scale slider with compact layout
        scale_slider = QSlider(Qt.Horizontal)
        scale_slider.setRange(10, 100)
        scale_slider.setValue(100)
        scale_slider.setEnabled(False)
        scale_slider.setMinimumWidth(100)
        scale_slider.setMaximumWidth(120)

        scale_label = QLabel("100%")
        scale_label.setMinimumWidth(40)
        scale_label.setAlignment(Qt.AlignCenter)
        scale_label.setStyleSheet("font-weight: bold; color: #2196F3;")

        scale_slider.valueChanged.connect(
            lambda v, lbl=scale_label: lbl.setText(f"{v}%")
        )

        # Add widgets to horizontal layout
        group_layout.addWidget(QLabel("Model:"))
        group_layout.addWidget(model_combo)
        group_layout.addWidget(QLabel("Scale:"))
        group_layout.addWidget(scale_slider)
        group_layout.addWidget(scale_label)
        group_layout.addStretch()

        # Store references to widgets
        setattr(self, f"{section_name}_model_combo", model_combo)
        setattr(self, f"{section_name}_scale_slider", scale_slider)
        setattr(self, f"{section_name}_scale_label", scale_label)

        self.secondary_widgets.extend([model_combo, scale_slider])

        return group

    def _create_preprocess_model_tab(self):
        """Create the preprocess model tab."""
        widget = QFrame()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Enable Preprocess Model
        self.enable_preprocess_check = QCheckBox("Enable Preprocess Model")
        self.enable_preprocess_check.setChecked(False)
        layout.addRow(self.enable_preprocess_check)

        # Model selection
        self.preprocess_model_combo = QComboBox()
        self.preprocess_model_combo.addItems(
            [
                "No Model",
                "UVR_Demucs_Model_1",
                "UVR_Demucs_Model_2",
                "UVR_Demucs_Model_3",
                "UVR_Demucs_Model_4",
            ]
        )
        self.preprocess_model_combo.setEnabled(False)
        layout.addRow("Model:", self.preprocess_model_combo)

        # Save Instrument Mix
        self.save_inst_mix_check = QCheckBox("Save Instrument Mix")
        self.save_inst_mix_check.setChecked(False)
        self.save_inst_mix_check.setEnabled(False)
        layout.addRow(self.save_inst_mix_check)

        # Connect enable checkbox
        self.enable_preprocess_check.toggled.connect(self._toggle_preprocess_widgets)

        return widget

    def _toggle_preprocess_widgets(self, enabled):
        """Toggle preprocess widgets."""
        self.preprocess_model_combo.setEnabled(enabled)
        self.save_inst_mix_check.setEnabled(enabled)

    def _create_vocal_splitter_tab(self):
        """Create the vocal splitter tab."""
        widget = QFrame()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Enable Vocal Split
        self.enable_vocal_split_check = QCheckBox("Enable Vocal Split Mode")
        self.enable_vocal_split_check.setChecked(False)
        layout.addRow(self.enable_vocal_split_check)

        # Vocal Model Selection
        self.vocal_model_combo = QComboBox()
        self.vocal_model_combo.addItems(
            [
                "No Model",
                "2_HP-UVR.pth",
                "3_HP-Vocal-UVR.pth",
                "4_HP-Vocal-UVR.pth",
                "5_HP-Karaoke-UVR.pth",
            ]
        )
        self.vocal_model_combo.setEnabled(False)
        layout.addRow("Model:", self.vocal_model_combo)

        # Save Instrumentals checkbox
        self.save_inst_check = QCheckBox("Save Split Vocal Instrumentals")
        self.save_inst_check.setChecked(False)
        self.save_inst_check.setEnabled(False)
        layout.addRow(self.save_inst_check)

        # Deverb section
        self.enable_deverb_check = QCheckBox("Deverb Vocals")
        self.enable_deverb_check.setChecked(False)
        layout.addRow(self.enable_deverb_check)

        # Deverb Type - using correct UVR.py options
        self.deverb_type_combo = QComboBox()
        self.deverb_type_combo.addItems(
            [
                "Main Vocals Only",
                "Lead Vocals Only",
                "Backing Vocals Only",
                "All Vocal Types",
            ]
        )
        self.deverb_type_combo.setEnabled(False)
        layout.addRow("Vocal Type:", self.deverb_type_combo)

        # Connect enable checkboxes
        self.enable_vocal_split_check.toggled.connect(self._toggle_vocal_widgets)
        self.enable_deverb_check.toggled.connect(self._toggle_deverb_widgets)

        return widget

    def _toggle_secondary_widgets(self, enabled):
        """Toggle secondary model widgets."""
        for widget in self.secondary_widgets:
            widget.setEnabled(enabled)

    def _toggle_vocal_widgets(self, enabled):
        """Toggle vocal splitter widgets."""
        self.vocal_model_combo.setEnabled(enabled)
        self.save_inst_check.setEnabled(enabled)

    def _toggle_deverb_widgets(self, enabled):
        """Toggle deverb widgets."""
        self.deverb_type_combo.setEnabled(enabled)

    def _load_current_settings(self):
        """Load current settings into the dialog."""
        if not self.current_settings:
            return

        # Advanced settings
        if "shifts" in self.current_settings:
            self.shifts_spin.setValue(self.current_settings["shifts"])
        if "overlap" in self.current_settings:
            self.overlap_spin.setValue(self.current_settings["overlap"])
        if "semitone_shift" in self.current_settings:
            value = self.current_settings["semitone_shift"]
            self.pitch_slider.setValue(value)
            self.pitch_value_label.setText(str(value))
        if "is_split_mode" in self.current_settings:
            self.split_mode_check.setChecked(self.current_settings["is_split_mode"])
        if "is_demucs_combine_stems" in self.current_settings:
            self.combine_stems_check.setChecked(
                self.current_settings["is_demucs_combine_stems"]
            )
        if "is_invert_spec" in self.current_settings:
            self.invert_spec_check.setChecked(self.current_settings["is_invert_spec"])

        # Secondary model settings
        if "is_secondary_model" in self.current_settings:
            self.enable_secondary_check.setChecked(
                self.current_settings["is_secondary_model"]
            )

        # Load settings for all four secondary model sections
        if "vocals_secondary_model" in self.current_settings:
            model = self.current_settings["vocals_secondary_model"]
            index = self.vocals_model_combo.findText(model)
            if index >= 0:
                self.vocals_model_combo.setCurrentIndex(index)
        if "vocals_secondary_scale" in self.current_settings:
            scale = int(self.current_settings["vocals_secondary_scale"] * 100)
            self.vocals_scale_slider.setValue(scale)
            self.vocals_scale_label.setText(f"{scale}%")

        if "bass_secondary_model" in self.current_settings:
            model = self.current_settings["bass_secondary_model"]
            index = self.bass_model_combo.findText(model)
            if index >= 0:
                self.bass_model_combo.setCurrentIndex(index)
        if "bass_secondary_scale" in self.current_settings:
            scale = int(self.current_settings["bass_secondary_scale"] * 100)
            self.bass_scale_slider.setValue(scale)
            self.bass_scale_label.setText(f"{scale}%")

        if "drums_secondary_model" in self.current_settings:
            model = self.current_settings["drums_secondary_model"]
            index = self.drums_model_combo.findText(model)
            if index >= 0:
                self.drums_model_combo.setCurrentIndex(index)
        if "drums_secondary_scale" in self.current_settings:
            scale = int(self.current_settings["drums_secondary_scale"] * 100)
            self.drums_scale_slider.setValue(scale)
            self.drums_scale_label.setText(f"{scale}%")

        if "other_secondary_model" in self.current_settings:
            model = self.current_settings["other_secondary_model"]
            index = self.other_model_combo.findText(model)
            if index >= 0:
                self.other_model_combo.setCurrentIndex(index)
        if "other_secondary_scale" in self.current_settings:
            scale = int(self.current_settings["other_secondary_scale"] * 100)
            self.other_scale_slider.setValue(scale)
            self.other_scale_label.setText(f"{scale}%")

        # Preprocess model settings
        if "is_pre_proc_model" in self.current_settings:
            self.enable_preprocess_check.setChecked(
                self.current_settings["is_pre_proc_model"]
            )
        if "pre_proc_model" in self.current_settings:
            model = self.current_settings["pre_proc_model"]
            index = self.preprocess_model_combo.findText(model)
            if index >= 0:
                self.preprocess_model_combo.setCurrentIndex(index)
        if "is_demucs_pre_proc_model_inst_mix" in self.current_settings:
            self.save_inst_mix_check.setChecked(
                self.current_settings["is_demucs_pre_proc_model_inst_mix"]
            )

        # Vocal splitter settings
        if "is_set_vocal_splitter" in self.current_settings:
            self.enable_vocal_split_check.setChecked(
                self.current_settings["is_set_vocal_splitter"]
            )
        if "set_vocal_splitter" in self.current_settings:
            model = self.current_settings["set_vocal_splitter"]
            index = self.vocal_model_combo.findText(model)
            if index >= 0:
                self.vocal_model_combo.setCurrentIndex(index)
        if "is_save_inst_set_vocal_splitter" in self.current_settings:
            self.save_inst_check.setChecked(
                self.current_settings["is_save_inst_set_vocal_splitter"]
            )
        if "is_deverb_vocals" in self.current_settings:
            self.enable_deverb_check.setChecked(
                self.current_settings["is_deverb_vocals"]
            )
        if "deverb_vocal_opt" in self.current_settings:
            option = self.current_settings["deverb_vocal_opt"]
            index = self.deverb_type_combo.findText(option)
            if index >= 0:
                self.deverb_type_combo.setCurrentIndex(index)

    def _apply_settings(self):
        """Apply the settings and emit the updated signal."""
        settings = {}

        # Advanced settings
        settings["shifts"] = self.shifts_spin.value()
        settings["overlap"] = self.overlap_spin.value()
        settings["semitone_shift"] = self.pitch_slider.value()
        settings["is_split_mode"] = self.split_mode_check.isChecked()
        settings["is_demucs_combine_stems"] = self.combine_stems_check.isChecked()
        settings["is_invert_spec"] = self.invert_spec_check.isChecked()

        # Secondary model settings
        settings["is_secondary_model"] = self.enable_secondary_check.isChecked()

        # Save settings for all four secondary model sections
        settings["vocals_secondary_model"] = self.vocals_model_combo.currentText()
        settings["vocals_secondary_scale"] = self.vocals_scale_slider.value() / 100.0
        settings["bass_secondary_model"] = self.bass_model_combo.currentText()
        settings["bass_secondary_scale"] = self.bass_scale_slider.value() / 100.0
        settings["drums_secondary_model"] = self.drums_model_combo.currentText()
        settings["drums_secondary_scale"] = self.drums_scale_slider.value() / 100.0
        settings["other_secondary_model"] = self.other_model_combo.currentText()
        settings["other_secondary_scale"] = self.other_scale_slider.value() / 100.0

        # Preprocess model settings
        settings["is_pre_proc_model"] = self.enable_preprocess_check.isChecked()
        settings["pre_proc_model"] = self.preprocess_model_combo.currentText()
        settings["is_demucs_pre_proc_model_inst_mix"] = (
            self.save_inst_mix_check.isChecked()
        )

        # Vocal splitter settings
        settings["is_set_vocal_splitter"] = self.enable_vocal_split_check.isChecked()
        settings["set_vocal_splitter"] = self.vocal_model_combo.currentText()
        settings["is_save_inst_set_vocal_splitter"] = self.save_inst_check.isChecked()
        settings["is_deverb_vocals"] = self.enable_deverb_check.isChecked()
        settings["deverb_vocal_opt"] = self.deverb_type_combo.currentText()

        logger.info(f"Demucs advanced settings updated: {settings}")

        self.settings_updated.emit(settings)
        self.accept()


class DemucsAdvancedPresenter(QObject):
    """Presenter for Demucs advanced settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialog = None

    def show_dialog(self, parent_widget=None, current_settings=None):
        """Show the advanced settings dialog."""
        self.dialog = DemucsAdvancedDialog(current_settings, parent_widget)
        return self.dialog.exec()

    def update_settings(self, settings):
        """Update current settings."""
        if self.dialog:
            self.dialog.current_settings.update(settings)

    def get_settings(self):
        """Get current settings from dialog."""
        if self.dialog:
            return self.dialog.current_settings
        return {}
