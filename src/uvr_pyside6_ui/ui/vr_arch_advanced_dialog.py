import logging
import os
import platform
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QIcon

from ..core import app_constants as ac
from ..core.model_data import VR_MODELS_DIR_PATH, ModelData
from ..core.uvr_core_adapter import UVRCoreAdapter

logger = logging.getLogger(__name__)


class VRArchAdvancedDialog(QDialog):
    """Advanced VR Architecture settings dialog matching UVR.py structure."""

    settings_updated = Signal(dict)

    def __init__(self, current_settings=None, is_vr_mode=False, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings or {}
        self.is_vr_mode = is_vr_mode

        self.setWindowTitle("Advanced VR Options")
        self.setWindowIcon(QIcon(ac.QRC_ICON_PATH))
        self.setModal(True)
        self.setMinimumSize(450, 500)  # Consistent with other dialogs

        # Lazy loading flags
        self._models_loaded = False

        self.adapter = UVRCoreAdapter()

        self._setup_ui()
        self._load_settings()

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

        # Connect tab change signal for lazy loading
        tab_widget.currentChanged.connect(self._on_tab_changed)

        # Create tabs
        self._create_advanced_tab(tab_widget)
        self._create_secondary_model_tab(tab_widget)
        self._create_vocal_splitter_tab(tab_widget)

        layout.addWidget(tab_widget)

        # Button layout - Apply and Close closer together
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right

        # Apply and Close buttons with minimal spacing
        self.apply_button = QPushButton("Apply")
        self.close_button = QPushButton("Close")

        # Set consistent button sizes
        button_width = 80
        self.apply_button.setFixedWidth(button_width)
        self.close_button.setFixedWidth(button_width)

        # Connect signals
        self.apply_button.clicked.connect(self._apply_settings)
        self.close_button.clicked.connect(self.reject)

        # Add buttons with minimal spacing between them
        button_layout.addWidget(self.apply_button)
        button_layout.addSpacing(5)  # Small gap between buttons
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _create_advanced_tab(self, tab_widget):
        """Create the advanced settings tab."""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)

        # VR Settings Group
        vr_group = QGroupBox("VR Architecture Settings")
        vr_layout = QFormLayout(vr_group)
        vr_layout.setSpacing(10)

        # Window Size (only if not in VR_ARCH_PM mode)
        if not self.is_vr_mode:
            self.window_size_combo = QComboBox()
            self.window_size_combo.addItems(["320", "512", "1024"])
            self.window_size_combo.setCurrentText("512")
            vr_layout.addRow("Window Size:", self.window_size_combo)

            # Aggression Setting - slider with value label beside it
            aggression_layout = QHBoxLayout()
            self.aggression_slider = QSlider(Qt.Horizontal)
            self.aggression_slider.setMinimum(1)
            self.aggression_slider.setMaximum(50)
            self.aggression_slider.setValue(5)
            self.aggression_slider.setMinimumWidth(180)

            self.aggression_value_label = QLabel("5")
            self.aggression_value_label.setAlignment(Qt.AlignCenter)
            self.aggression_value_label.setMinimumWidth(30)
            self.aggression_value_label.setStyleSheet(
                "font-weight: bold; color: #3498db;"
            )

            self.aggression_slider.valueChanged.connect(
                lambda v: self.aggression_value_label.setText(str(v))
            )

            aggression_layout.addWidget(self.aggression_slider)
            aggression_layout.addWidget(self.aggression_value_label)
            vr_layout.addRow("Aggression Setting:", aggression_layout)

        # Batch Size - slider with value label beside it
        batch_layout = QHBoxLayout()
        self.batch_size_slider = QSlider(Qt.Horizontal)
        self.batch_size_slider.setMinimum(1)
        self.batch_size_slider.setMaximum(16)
        self.batch_size_slider.setValue(4)
        self.batch_size_slider.setMinimumWidth(180)

        self.batch_size_value_label = QLabel("4")
        self.batch_size_value_label.setAlignment(Qt.AlignCenter)
        self.batch_size_value_label.setMinimumWidth(30)
        self.batch_size_value_label.setStyleSheet("font-weight: bold; color: #3498db;")

        self.batch_size_slider.valueChanged.connect(
            lambda v: self.batch_size_value_label.setText(str(v))
        )

        batch_layout.addWidget(self.batch_size_slider)
        batch_layout.addWidget(self.batch_size_value_label)
        vr_layout.addRow("Batch Size:", batch_layout)

        # Post Process Threshold - slider with value label beside it
        threshold_layout = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(1)  # 0.1 * 10
        self.threshold_slider.setMaximum(30)  # 3.0 * 10
        self.threshold_slider.setValue(2)  # 0.2 * 10
        self.threshold_slider.setMinimumWidth(180)
        self.threshold_slider.setEnabled(False)  # Disabled by default

        self.threshold_value_label = QLabel("0.2")
        self.threshold_value_label.setAlignment(Qt.AlignCenter)
        self.threshold_value_label.setMinimumWidth(30)
        self.threshold_value_label.setStyleSheet("font-weight: bold; color: #3498db;")

        self.threshold_slider.valueChanged.connect(self._update_threshold_label)

        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value_label)
        vr_layout.addRow("Post Process Threshold:", threshold_layout)

        layout.addWidget(vr_group)

        # Processing Options Group
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(8)

        # TTA
        self.tta_checkbox = QCheckBox("Enable TTA")
        options_layout.addWidget(self.tta_checkbox)

        # Post Process
        self.post_process_checkbox = QCheckBox("Post Process")
        self.post_process_checkbox.toggled.connect(self._toggle_threshold)
        options_layout.addWidget(self.post_process_checkbox)

        # High End Process
        self.high_end_process_checkbox = QCheckBox("High End Process")
        options_layout.addWidget(self.high_end_process_checkbox)

        layout.addWidget(options_group)

        # Actions section
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

        tab_widget.addTab(widget, "Advanced")
        return widget

    def _vocal_splitter_options(self):
        """Open vocal splitter options dialog."""
        logger.info("Vocal splitter options requested")

        # Create vocal splitter dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Vocal Split Options")
        dialog.setModal(True)
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        # Vocal Split Mode Options
        vocal_split_group = QGroupBox("Vocal Split Mode Options")
        vocal_split_layout = QFormLayout(vocal_split_group)

        # Enable Vocal Split Mode
        enable_vocal_split = QCheckBox("Enable Vocal Split Mode")
        vocal_split_layout.addRow(enable_vocal_split)

        # Select Model
        model_label = QLabel("Select Model:")
        model_combo = QComboBox()

        # Get karaoke models
        try:
            # Get karaoke models using our helper method
            karaoke_models = self._get_karaokee_models()
            model_combo.addItems(karaoke_models)
        except Exception as e:
            logger.error(f"Error loading karaoke models: {e}")
            model_combo.addItems([ac.NO_MODEL])

        vocal_split_layout.addRow(model_label, model_combo)

        # Save Split Vocal Instrumentals
        save_inst_check = QCheckBox("Save Split Vocal Instrumentals")
        save_inst_check.setEnabled(False)
        vocal_split_layout.addRow(save_inst_check)

        layout.addWidget(vocal_split_group)

        # Vocal Deverb Options
        deverb_group = QGroupBox("Vocal Deverb Options")
        deverb_layout = QFormLayout(deverb_group)

        # Select Vocal Type to Deverb
        deverb_label = QLabel("Select Vocal Type to Deverb:")
        deverb_combo = QComboBox()
        deverb_options = [
            "Main Vocals Only",
            "Lead Vocals Only",
            "Backing Vocals Only",
            "All Vocal Types",
        ]
        deverb_combo.addItems(deverb_options)
        deverb_combo.setEnabled(False)
        deverb_layout.addRow(deverb_label, deverb_combo)

        # Deverb Vocals
        deverb_check = QCheckBox("Deverb Vocals")
        deverb_check.setEnabled(False)
        deverb_layout.addRow(deverb_check)

        # Check if deverb model exists
        try:
            deverb_model_path = Path(ac.VR_MODELS_DIR_PATH) / "UVR-DeEcho-DeReverb.pth"
            if not deverb_model_path.exists():
                deverb_check.setEnabled(False)
                deverb_combo.setEnabled(False)
        except Exception:
            deverb_check.setEnabled(False)
            deverb_combo.setEnabled(False)

        layout.addWidget(deverb_group)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Connect enable checkbox logic
        def toggle_vocal_widgets(enabled):
            model_combo.setEnabled(enabled)
            save_inst_check.setEnabled(enabled)

        def toggle_deverb_widgets(enabled):
            deverb_combo.setEnabled(enabled)

        enable_vocal_split.toggled.connect(toggle_vocal_widgets)
        deverb_check.toggled.connect(toggle_deverb_widgets)

        # Show dialog
        dialog.exec()

    def _clear_autoset_cache(self):
        """Clear the autoset cache."""
        logger.info("Clear autoset cache requested")

        try:
            # Clear VR cache directory
            vr_hash_dir = VR_MODELS_DIR_PATH.parent / "vr_hash_dirs"

            if vr_hash_dir.exists():
                for filename in os.listdir(vr_hash_dir):
                    filepath = os.path.join(vr_hash_dir, filename)
                    if filename not in [
                        "model_data.json",
                        "model_name_mapper.json",
                    ] and not os.path.isdir(filepath):
                        try:
                            os.remove(filepath)
                        except (OSError, PermissionError) as e:
                            logger.warning(
                                f"Could not remove cache file {filepath}: {e}"
                            )

            QMessageBox.information(
                self, "Clear Cache", "VR AutoSet cache cleared successfully."
            )
            logger.info("VR cache cleared successfully")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            QMessageBox.warning(
                self, "Clear Cache Error", f"Failed to clear cache: {str(e)}"
            )

    def _create_secondary_model_tab(self, tab_widget):
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

        # Create vertical layout for the four ac.SECTIONS
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
        self.enable_secondary_check.toggled.connect(self._toggle_secondary_controls)

        tab_widget.addTab(widget, "Secondary Model")
        return widget

    def _create_secondary_section(self, title, section_name):
        """Create a compact secondary model section."""
        group = QGroupBox(title)
        group_layout = QHBoxLayout(group)  # Use horizontal layout for compactness
        group_layout.setSpacing(8)

        # Model combo box - start with NO_MODEL, will be populated lazily
        model_combo = QComboBox()
        # Start with NO_MODEL only, will be populated when tab is accessed
        model_combo.addItems([ac.NO_MODEL])
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

    def _update_threshold_label(self, value):
        """Update the threshold label with the scaled value."""
        scaled_value = value / 10.0
        self.threshold_value_label.setText(f"{scaled_value:.1f}")

    def _toggle_threshold(self, state):
        """Toggle the threshold slider enabled state."""
        self.threshold_slider.setEnabled(state == 2)  # Qt.Checked = 2

    def _toggle_secondary_controls(self, enabled):
        """Toggle all secondary model controls."""
        if hasattr(self, "secondary_widgets"):
            for control in self.secondary_widgets:
                control.setEnabled(enabled)

    def _load_settings(self):
        """Load settings into the dialog controls."""
        if not self.current_settings:
            return

        # Advanced settings
        if not self.is_vr_mode:
            if "window_size" in self.current_settings:
                window_size = str(self.current_settings["window_size"])
                index = self.window_size_combo.findText(window_size)
                if index >= 0:
                    self.window_size_combo.setCurrentIndex(index)

            if "aggression_setting" in self.current_settings:
                # Convert float aggression (0.01-0.50) to int (1-50)
                aggression = self.current_settings["aggression_setting"]
                if isinstance(aggression, float):
                    aggression_int = int(aggression * 100)
                else:
                    aggression_int = int(aggression)
                self.aggression_slider.setValue(aggression_int)
                self.aggression_value_label.setText(str(aggression_int))

        if "batch_size" in self.current_settings:
            self.batch_size_slider.setValue(self.current_settings["batch_size"])
            self.batch_size_value_label.setText(
                str(self.current_settings["batch_size"])
            )

        if "post_process_threshold" in self.current_settings:
            threshold = int(self.current_settings["post_process_threshold"] * 10)
            self.threshold_slider.setValue(threshold)
            self._update_threshold_label(threshold)

        # Processing options
        self.tta_checkbox.setChecked(self.current_settings.get("is_tta", False))
        self.post_process_checkbox.setChecked(
            self.current_settings.get("is_post_process", False)
        )
        self.high_end_process_checkbox.setChecked(
            self.current_settings.get("is_high_end_process", False)
        )

        # Secondary model settings
        self.enable_secondary_check.setChecked(
            self.current_settings.get("vr_is_secondary_model_activate", False)
        )

        # Load secondary model settings for each section
        for section in ac.SECTIONS:
            # Model selection
            model_key = f"vr_{section}_secondary_model"
            if model_key in self.current_settings:
                combo = getattr(self, f"{section}_model_combo")
                model = self.current_settings[model_key]
                index = combo.findText(model)
                if index >= 0:
                    combo.setCurrentIndex(index)

            # Scale/percentage
            scale_key = f"vr_{section}_secondary_model_scale"
            if scale_key in self.current_settings:
                slider = getattr(self, f"{section}_scale_slider")
                label = getattr(self, f"{section}_scale_label")
                # Convert from 0.01-0.99 scale to 1-99 percentage
                scale_value = self.current_settings[scale_key]
                if isinstance(scale_value, str):
                    # Handle percentage string format
                    scale_value = float(scale_value.replace("%", "")) / 100.0
                percentage = int(scale_value * 100)
                slider.setValue(percentage)
                label.setText(f"{percentage}%")

        # Vocal splitter settings
        self.enable_vocal_split_check.setChecked(
            self.current_settings.get("vr_is_vocal_split_mode", False)
        )

        # Load vocal model if exists
        vocal_model = self.current_settings.get("vr_vocal_model", "No Model")
        vocal_index = self.vocal_model_combo.findText(vocal_model)
        if vocal_index >= 0:
            self.vocal_model_combo.setCurrentIndex(vocal_index)

        # Load deverb option
        deverb_option = self.current_settings.get(
            "vr_deverb_option", "Main Vocals Only"
        )
        deverb_index = self.deverb_combo.findText(deverb_option)
        if deverb_index >= 0:
            self.deverb_combo.setCurrentIndex(deverb_index)

        self.save_vocal_only_check.setChecked(
            self.current_settings.get("vr_save_vocal_only", False)
        )
        self.save_inst_only_check.setChecked(
            self.current_settings.get("vr_save_inst_only", False)
        )

    def _apply_settings(self):
        """Apply the current settings and emit the signal."""
        settings = {}

        # Advanced settings
        if not self.is_vr_mode:
            settings["window_size"] = int(self.window_size_combo.currentText())
            # Convert int aggression (1-50) to float (0.01-0.50)
            settings["aggression_setting"] = self.aggression_slider.value() / 100.0

        settings["batch_size"] = self.batch_size_slider.value()
        settings["post_process_threshold"] = self.threshold_slider.value() / 10.0

        # Processing options
        settings["is_tta"] = self.tta_checkbox.isChecked()
        settings["is_post_process"] = self.post_process_checkbox.isChecked()
        settings["is_high_end_process"] = self.high_end_process_checkbox.isChecked()

        # Secondary model settings
        settings["vr_is_secondary_model_activate"] = (
            self.enable_secondary_check.isChecked()
        )

        # Secondary model settings for each section
        for section in ac.SECTIONS:
            # Model selection
            combo = getattr(self, f"{section}_model_combo")
            settings[f"vr_{section}_secondary_model"] = combo.currentText()

            # Scale/percentage
            slider = getattr(self, f"{section}_scale_slider")
            # Convert from 1-99 percentage to 0.01-0.99
            percentage = slider.value()
            scale_value = percentage / 100.0
            settings[f"vr_{section}_secondary_model_scale"] = scale_value

        # Vocal splitter settings
        settings["vr_is_vocal_split_mode"] = self.enable_vocal_split_check.isChecked()
        settings["vr_vocal_model"] = self.vocal_model_combo.currentText()
        settings["vr_deverb_option"] = self.deverb_combo.currentText()
        settings["vr_save_vocal_only"] = self.save_vocal_only_check.isChecked()
        settings["vr_save_inst_only"] = self.save_inst_only_check.isChecked()

        logger.info(f"VR advanced settings applied: {settings}")
        self.settings_updated.emit(settings)
        self.accept()

    def _open_models_folder(self):
        """Open the VR models folder in the system file manager."""
        try:
            # Get the VR models directory path
            models_path = Path(VR_MODELS_DIR_PATH)

            # Create directory if it doesn't exist
            models_path.mkdir(parents=True, exist_ok=True)

            # Open in system file manager
            if platform.system() == "Windows":
                os.startfile(str(models_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(models_path)])
            else:  # Linux and others
                subprocess.run(["xdg-open", str(models_path)])

            logger.info(f"Open VR models folder requested: {models_path}")

        except Exception as e:
            logger.error(f"Failed to open VR models folder: {e}")
            # TODO: Show error dialog to user

    def _create_vocal_splitter_tab(self, tab_widget):
        """Create the vocal splitter tab."""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Vocal Splitter Settings Group
        vocal_group = QGroupBox("Vocal Splitter Settings")
        vocal_layout = QFormLayout(vocal_group)
        vocal_layout.setSpacing(10)

        # Enable Vocal Split
        self.enable_vocal_split_check = QCheckBox("Enable Vocal Split Mode")
        self.enable_vocal_split_check.setChecked(False)
        vocal_layout.addRow(self.enable_vocal_split_check)

        # Vocal Model Selection
        self.vocal_model_combo = QComboBox()
        # Load karaoke models dynamically
        try:
            # Get karaoke models using our helper method
            karaoke_models = self._get_karaokee_models()

            self.vocal_model_combo.addItems(karaoke_models)
        except Exception as e:
            logger.error(f"Error loading karaoke models for vocal combo: {e}")
            self.vocal_model_combo.addItems([ac.NO_MODEL])

        self.vocal_model_combo.setEnabled(False)
        vocal_layout.addRow("Model:", self.vocal_model_combo)

        # Vocal Split Mode - DeVerberate Options
        self.deverb_combo = QComboBox()
        self.deverb_combo.addItems(
            [
                "Main Vocals Only",
                "Lead Vocals Only",
                "Backing Vocals Only",
                "All Vocal Types",
            ]
        )
        self.deverb_combo.setEnabled(False)
        vocal_layout.addRow("DeVerberate Option:", self.deverb_combo)

        layout.addWidget(vocal_group)

        # Processing Options
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(8)

        self.save_vocal_only_check = QCheckBox("Save Vocals Only")
        self.save_vocal_only_check.setEnabled(False)
        options_layout.addWidget(self.save_vocal_only_check)

        self.save_inst_only_check = QCheckBox("Save Instrumental Only")
        self.save_inst_only_check.setEnabled(False)
        options_layout.addWidget(self.save_inst_only_check)

        layout.addWidget(options_group)
        layout.addStretch()

        # Connect enable checkbox
        self.enable_vocal_split_check.toggled.connect(self._toggle_vocal_widgets)

        tab_widget.addTab(widget, "Vocal Splitter")
        return widget

    def _toggle_vocal_widgets(self, enabled):
        """Toggle vocal splitter widgets."""
        self.vocal_model_combo.setEnabled(enabled)
        self.deverb_combo.setEnabled(enabled)
        self.save_vocal_only_check.setEnabled(enabled)
        self.save_inst_only_check.setEnabled(enabled)

    def _get_filtered_models_for_stem(self, primary_stem, secondary_stem):
        """Get models that are suitable for the given stem pair.

        This implements the same filtering logic as the original UVR.py model_list function.
        """
        try:
            suitable_models = [ac.NO_MODEL]

            # Get VR models specifically
            vr_models = self.adapter.get_available_models(ac.VR_ARCH_MODELS_KEY)

            for model_name in vr_models:
                try:
                    # Create minimal settings dict for ModelData creation
                    temp_settings = {
                        "chosen_process_method": ac.VR_ARCH_TYPE,
                        "is_gpu_conversion": False,
                        "is_normalization": False,
                    }

                    model_data = ModelData.from_settings_dict(
                        temp_settings,
                        _model_name_override=model_name,
                        _process_method_override=ac.VR_ARCH_TYPE,
                        _is_secondary_model_instance=True,
                    )

                    # Check if model is suitable for this stem pair
                    if self._is_model_suitable_for_stem_pair(
                        model_data, primary_stem, secondary_stem
                    ):
                        suitable_models.append(model_name)

                except Exception as e:
                    logger.debug(f"Could not check VR model {model_name}: {e}")
                    continue

            return suitable_models

        except Exception as e:
            logger.error(
                f"Error getting filtered VR models for {primary_stem}/{secondary_stem}: {e}"
            )
            # If all else fails, return just NO_MODEL - no hardcoded fallback
            return [ac.NO_MODEL]

    def _get_process_method_for_arch(self, arch_key):
        """Get the process method string for the given architecture key."""
        arch_map = {
            ac.VR_ARCH_MODELS_KEY: ac.VR_ARCH_TYPE,
            ac.MDX_NET_MODELS_KEY: ac.MDX_ARCH_TYPE,
            ac.DEMUCS_MODELS_KEY: ac.DEMUCS_ARCH_TYPE,
        }
        return arch_map.get(arch_key, ac.VR_ARCH_TYPE)

    def _is_model_suitable_for_stem_pair(
        self, model_data, primary_stem, secondary_stem
    ):
        """Check if a model is suitable for the given stem pair.

        This implements the exact logic as the original UVR.py matches_stem function.
        """
        try:
            # PRIMARY MATCH: Check if model's primary stem matches either primary or secondary stem
            primary_match = False
            if hasattr(model_data, "primary_stem") and model_data.primary_stem:
                primary_match = model_data.primary_stem in {
                    primary_stem,
                    secondary_stem,
                }

            # MDX STEM MATCH: Check MDX stem compatibility (for 2-stem models only)
            mdx_stem_match = False
            if hasattr(model_data, "mdx_model_stems") and model_data.mdx_model_stems:
                if (
                    hasattr(model_data, "mdx_stem_count")
                    and model_data.mdx_stem_count <= 2
                ):
                    mdx_stem_match = primary_stem in model_data.mdx_model_stems

            # DEMUCS SOURCE MATCH: Check Demucs source compatibility
            demucs_source_match = False
            if (
                hasattr(model_data, "demucs_source_list")
                and model_data.demucs_source_list
            ):
                demucs_source_match = primary_stem.lower() in [
                    s.lower() for s in model_data.demucs_source_list
                ]

            # Apply the exact UVR.py matches_stem logic:
            # return primary_match or mdx_stem_match if is_no_demucs else primary_match or primary_stem in model.mdx_model_stems
            # Since we're checking secondary models (not main models), we apply the full logic
            return primary_match or mdx_stem_match or demucs_source_match

        except Exception as e:
            logger.debug(f"Error checking model suitability: {e}")
            return False

    def _load_models_if_needed(self):
        """Lazy load models only when needed - optimized to load all models once."""
        if self._models_loaded:
            return

        try:
            # Load all models once and cache them
            all_suitable_models = []

            # Get all available models from all architectures (do this once)
            for arch_key in [
                ac.VR_ARCH_MODELS_KEY,
                ac.MDX_NET_MODELS_KEY,
                ac.DEMUCS_MODELS_KEY,
            ]:
                arch_models = self.adapter.get_available_models(arch_key)

                for model_name in arch_models:
                    try:
                        # Create minimal settings dict for ModelData creation
                        temp_settings = {
                            "chosen_process_method": self._get_process_method_for_arch(
                                arch_key
                            ),
                            "is_gpu_conversion": False,
                            "is_normalization": False,
                        }

                        model_data = ModelData.from_settings_dict(
                            temp_settings,
                            _model_name_override=model_name,
                            _process_method_override=self._get_process_method_for_arch(
                                arch_key
                            ),
                            _is_secondary_model_instance=True,
                        )

                        # Store model with its data for filtering
                        all_suitable_models.append((model_name, model_data))

                    except Exception as e:
                        logger.debug(f"Could not check model {model_name}: {e}")
                        continue

            # Now filter for each stem pair efficiently
            stem_pairs = [
                (ac.VOCAL_STEM, ac.INST_STEM),
                (ac.BASS_STEM, ac.secondary_stem(ac.BASS_STEM)),
                (ac.DRUM_STEM, ac.secondary_stem(ac.DRUM_STEM)),
                (ac.OTHER_STEM, ac.secondary_stem(ac.OTHER_STEM)),
            ]

            combo_boxes = [
                self.vocals_model_combo,
                self.bass_model_combo,
                self.drums_model_combo,
                self.other_model_combo,
            ]

            # Filter models for each stem pair
            for i, (primary_stem, secondary_stem) in enumerate(stem_pairs):
                suitable_models = [ac.NO_MODEL]

                for model_name, model_data in all_suitable_models:
                    if self._is_model_suitable_for_stem_pair(
                        model_data, primary_stem, secondary_stem
                    ):
                        suitable_models.append(model_name)

                # Update combo box
                combo_boxes[i].clear()
                combo_boxes[i].addItems(suitable_models)

            self._models_loaded = True

            # After loading models, restore saved selections
            self._load_saved_secondary_model_selections()

            logger.debug("VR models loaded successfully for secondary tab (optimized)")

        except Exception as e:
            logger.error(f"Error loading VR models: {e}")
            # Fallback: populate with just NO_MODEL
            for combo in [
                self.vocals_model_combo,
                self.bass_model_combo,
                self.drums_model_combo,
                self.other_model_combo,
            ]:
                combo.clear()
                combo.addItems([ac.NO_MODEL])

    def _load_saved_secondary_model_selections(self):
        """Load saved secondary model selections after models are loaded."""
        if not self.current_settings:
            return

        for section in ac.SECTIONS:
            # Model selection
            model_key = f"vr_{section}_secondary_model"
            if model_key in self.current_settings:
                combo = getattr(self, f"{section}_model_combo")
                model = self.current_settings[model_key]
                index = combo.findText(model)
                if index >= 0:
                    combo.setCurrentIndex(index)
                else:
                    # If model not found, default to NO_MODEL
                    no_model_index = combo.findText(ac.NO_MODEL)
                    if no_model_index >= 0:
                        combo.setCurrentIndex(no_model_index)

    def _on_tab_changed(self, index):
        """Handle tab change to implement lazy loading."""
        if index == 1 and not self._models_loaded:  # Secondary tab is index 1
            self._load_models_if_needed()

    def _get_karaokee_models(self):
        """Get models that are suitable for vocal splitting using shared utility function."""
        from ..core.model_utils import get_karaoke_models
        return get_karaoke_models()
