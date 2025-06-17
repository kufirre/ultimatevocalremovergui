"""Advanced Demucs settings dialog."""

import os
import platform
import subprocess
from pathlib import Path

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
    QWidget,
)

from ..core import app_constants as ac
from ..core.logger_utils import get_logger
from ..core.model_data import ModelData
from ..core.uvr_core_adapter import UVRCoreAdapter


logger = get_logger(__name__)


class DemucsAdvancedDialog(QDialog):
    """Advanced Demucs settings dialog matching UVR.py structure."""

    settings_updated = Signal(dict)

    def __init__(self, current_settings=None, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings or {}
        self.setWindowTitle("Advanced Demucs Options")
        self.setMinimumSize(450, 500)

        # Lazy loading flags
        self._models_loaded = False
        self._secondary_tab_widget = None

        self._setup_ui()
        self._load_current_settings()

    def _get_filtered_models_for_stem(self, primary_stem, secondary_stem):
        """Get models that are suitable for the given stem pair.

        This implements the same filtering logic as the original UVR.py model_list function.
        """
        try:
            adapter = UVRCoreAdapter()
            suitable_models = [ac.NO_MODEL]

            # Get all available models from all architectures
            for arch_key in [
                ac.VR_ARCH_MODELS_KEY,
                ac.MDX_NET_MODELS_KEY,
                ac.DEMUCS_MODELS_KEY,
            ]:
                arch_models = adapter.get_available_models(arch_key)

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

                        # Check if model is suitable for this stem pair
                        if self._is_model_suitable_for_stem_pair(
                            model_data, primary_stem, secondary_stem
                        ):
                            suitable_models.append(model_name)

                    except Exception as e:
                        logger.debug(f"Could not check model {model_name}: {e}")
                        continue

            return suitable_models

        except Exception as e:
            logger.error(
                f"Error getting filtered models for {primary_stem}/{secondary_stem}: {e}"
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

        # Connect tab change signal for lazy loading
        tab_widget.currentChanged.connect(self._on_tab_changed)

        # Advanced Settings Tab
        advanced_tab = self._create_advanced_tab()
        tab_widget.addTab(advanced_tab, "Advanced")

        # Secondary Model Tab
        secondary_tab = self._create_secondary_model_tab()
        tab_widget.addTab(secondary_tab, "Secondary")

        # Preprocess Model Tab
        preprocess_tab = self._create_preprocess_model_tab()
        tab_widget.addTab(preprocess_tab, "Preprocess")

        # Vocal Splitter Tab
        vocal_tab = self._create_vocal_splitter_tab()
        tab_widget.addTab(vocal_tab, "Vocal Split")

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

    def _create_advanced_tab(self):
        """Create the advanced settings tab."""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # Main settings form
        form_layout = QFormLayout()

        # Shifts (0-5)
        self.shifts_spin = QSpinBox()
        self.shifts_spin.setRange(0, 5)
        self.shifts_spin.setValue(2)
        form_layout.addRow("Shifts:", self.shifts_spin)

        # Overlap (0.1-0.99)
        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setRange(0.1, 0.99)
        self.overlap_spin.setSingleStep(0.05)
        self.overlap_spin.setValue(0.25)
        self.overlap_spin.setDecimals(2)
        form_layout.addRow("Overlap:", self.overlap_spin)

        # Shift Conversion Pitch - slider with value label beside it
        pitch_layout = QHBoxLayout()
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.setTickInterval(6)

        self.pitch_value_label = QLabel("0")
        self.pitch_value_label.setMinimumWidth(30)
        self.pitch_value_label.setAlignment(Qt.AlignCenter)

        self.pitch_slider.valueChanged.connect(
            lambda v: self.pitch_value_label.setText(str(v))
        )

        pitch_layout.addWidget(self.pitch_slider)
        pitch_layout.addWidget(self.pitch_value_label)
        form_layout.addRow("Shift Conversion Pitch:", pitch_layout)

        # Split Mode checkbox
        self.split_mode_check = QCheckBox("Split Mode")
        self.split_mode_check.setChecked(True)
        form_layout.addRow(self.split_mode_check)

        # Combine Stems checkbox
        self.combine_stems_check = QCheckBox("Combine Stems")
        self.combine_stems_check.setChecked(False)
        form_layout.addRow(self.combine_stems_check)

        # Spectral Inversion checkbox
        self.invert_spec_check = QCheckBox("Spectral Inversion")
        self.invert_spec_check.setChecked(False)
        form_layout.addRow(self.invert_spec_check)

        layout.addLayout(form_layout)

        # Actions Group at the bottom
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)

        # Open Models Folder button
        self.open_models_btn = QPushButton("Open Models Folder")
        self.open_models_btn.clicked.connect(self._open_models_folder)
        actions_layout.addWidget(self.open_models_btn)

        layout.addWidget(actions_group)
        layout.addStretch()

        return widget

    def _create_secondary_model_tab(self):
        """Create the secondary model tab with compact layout to fit without scrolling."""
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

        # Create compact vertical layout for the four sections
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
        """Create a compact secondary model section with horizontal layout."""
        group = QGroupBox(title)
        group_layout = QHBoxLayout(group)  # Use horizontal layout for compactness
        group_layout.setSpacing(8)

        # Model combo box - start with NO_MODEL, will be populated lazily
        model_combo = QComboBox()
        model_combo.addItems([ac.NO_MODEL])  # NO_MODEL is a valid selectable option
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

        # Store references to widgets using the original naming convention
        setattr(self, f"{section_name}_model_combo", model_combo)
        setattr(self, f"{section_name}_scale_slider", scale_slider)
        setattr(self, f"{section_name}_scale_label", scale_label)

        self.secondary_widgets.extend([model_combo, scale_slider])

        return group

    def _create_preprocess_model_tab(self):
        """Create the preprocess model tab."""
        widget = QFrame()
        layout = QFormLayout(widget)

        # Enable Preprocess Model
        self.enable_preprocess_check = QCheckBox("Enable Preprocess Model")
        self.enable_preprocess_check.setChecked(False)
        layout.addRow(self.enable_preprocess_check)

        # Preprocess Model Selection
        self.preprocess_model_combo = QComboBox()
        self.preprocess_model_combo.addItems(
            [
                "No Model",
                "UVR_MDXNET_1_9703.onnx",
                "UVR_MDXNET_2_9682.onnx",
                "UVR_MDXNET_3_9662.onnx",
            ]
        )
        self.preprocess_model_combo.setEnabled(False)
        layout.addRow("Preprocess Model:", self.preprocess_model_combo)

        # Save Instrument Mixture checkbox
        self.save_inst_mix_check = QCheckBox("Save Instrument Mixture")
        self.save_inst_mix_check.setChecked(False)
        self.save_inst_mix_check.setEnabled(False)
        layout.addRow(self.save_inst_mix_check)

        # Connect enable checkbox to toggle widgets
        self.enable_preprocess_check.toggled.connect(
            lambda enabled: [
                self.preprocess_model_combo.setEnabled(enabled),
                self.save_inst_mix_check.setEnabled(enabled),
            ]
        )

        return widget

    def _create_vocal_splitter_tab(self):
        """Create the vocal splitter tab."""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        # Enable Vocal Splitter
        self.enable_vocal_check = QCheckBox("Enable Vocal Splitter")
        self.enable_vocal_check.setChecked(False)
        layout.addWidget(self.enable_vocal_check)

        # Vocal splitter widgets list for enable/disable
        self.vocal_widgets = []

        # Vocal Splitter Model
        vocal_form = QFormLayout()

        self.vocal_splitter_combo = QComboBox()
        self.vocal_splitter_combo.addItems(
            ["No Model", "UVR_MDXNET_KARA_2.onnx", "Kim_Vocal_2.onnx"]
        )
        self.vocal_splitter_combo.setEnabled(False)
        vocal_form.addRow("Vocal Splitter Model:", self.vocal_splitter_combo)
        self.vocal_widgets.append(self.vocal_splitter_combo)

        layout.addLayout(vocal_form)

        # Deverb Section
        deverb_group = QGroupBox("Deverb")
        deverb_layout = QFormLayout(deverb_group)

        # Enable Deverb
        self.enable_deverb_check = QCheckBox("Enable Deverb")
        self.enable_deverb_check.setChecked(False)
        self.enable_deverb_check.setEnabled(False)
        deverb_layout.addRow(self.enable_deverb_check)
        self.vocal_widgets.append(self.enable_deverb_check)

        # Deverb widgets list
        self.deverb_widgets = []

        # Deverb Model
        self.deverb_model_combo = QComboBox()
        self.deverb_model_combo.addItems(["No Model", "Reverb_HQ_By_FoxJoy.onnx"])
        self.deverb_model_combo.setEnabled(False)
        deverb_layout.addRow("Deverb Model:", self.deverb_model_combo)
        self.deverb_widgets.append(self.deverb_model_combo)

        layout.addWidget(deverb_group)

        # Connect signals
        self.enable_vocal_check.toggled.connect(self._toggle_vocal_widgets)
        self.enable_deverb_check.toggled.connect(self._toggle_deverb_widgets)

        layout.addStretch()

        return widget

    def _toggle_secondary_widgets(self, enabled):
        """Toggle secondary model widgets."""
        for widget in self.secondary_widgets:
            widget.setEnabled(enabled)

    def _toggle_vocal_widgets(self, enabled):
        """Toggle vocal splitter widgets."""
        for widget in self.vocal_widgets:
            widget.setEnabled(enabled)

    def _toggle_deverb_widgets(self, enabled):
        """Toggle deverb widgets."""
        for widget in self.deverb_widgets:
            widget.setEnabled(enabled)

    def _load_current_settings(self):
        """Load current settings from the application."""
        # This would load from actual settings in a real implementation
        pass

    def _load_settings(self, settings):
        """Load settings from a dictionary."""
        if not settings:
            return

        # Load advanced settings
        if "shifts" in settings:
            self.shifts_spin.setValue(settings["shifts"])

        if "overlap" in settings:
            self.overlap_spin.setValue(settings["overlap"])

        if "pitch" in settings:
            self.pitch_slider.setValue(settings["pitch"])

        if "split_mode" in settings:
            self.split_mode_check.setChecked(settings["split_mode"])

        if "combine_stems" in settings:
            self.combine_stems_check.setChecked(settings["combine_stems"])

        if "invert_spec" in settings:
            self.invert_spec_check.setChecked(settings["invert_spec"])

        # Load secondary model settings
        if "enable_secondary" in settings:
            self.enable_secondary_check.setChecked(settings["enable_secondary"])

        secondary_models = settings.get("secondary_models", {})
        if "vocals" in secondary_models:
            self.vocals_model_combo.setCurrentText(secondary_models["vocals"])
        if "bass" in secondary_models:
            self.bass_model_combo.setCurrentText(secondary_models["bass"])
        if "drums" in secondary_models:
            self.drums_model_combo.setCurrentText(secondary_models["drums"])
        if "other" in secondary_models:
            self.other_model_combo.setCurrentText(secondary_models["other"])

        # Load secondary scales
        secondary_scales = settings.get("secondary_scales", {})
        if "vocals" in secondary_scales:
            self.vocals_scale_slider.setValue(secondary_scales["vocals"])
        if "bass" in secondary_scales:
            self.bass_scale_slider.setValue(secondary_scales["bass"])
        if "drums" in secondary_scales:
            self.drums_scale_slider.setValue(secondary_scales["drums"])
        if "other" in secondary_scales:
            self.other_scale_slider.setValue(secondary_scales["other"])

        # Load preprocess settings
        if "enable_preprocess" in settings:
            self.enable_preprocess_check.setChecked(settings["enable_preprocess"])
        if "preprocess_model" in settings:
            self.preprocess_model_combo.setCurrentText(settings["preprocess_model"])
        if "save_inst_mix" in settings:
            self.save_inst_mix_check.setChecked(settings["save_inst_mix"])

        # Load vocal splitter settings
        if "enable_vocal" in settings:
            self.enable_vocal_check.setChecked(settings["enable_vocal"])
        if "vocal_splitter_model" in settings:
            self.vocal_splitter_combo.setCurrentText(settings["vocal_splitter_model"])
        if "enable_deverb" in settings:
            self.enable_deverb_check.setChecked(settings["enable_deverb"])
        if "deverb_model" in settings:
            self.deverb_model_combo.setCurrentText(settings["deverb_model"])

    def _apply_settings(self):
        """Apply the current settings."""
        settings = {
            # Advanced settings
            "shifts": self.shifts_spin.value(),
            "overlap": self.overlap_spin.value(),
            "pitch": self.pitch_slider.value(),
            "split_mode": self.split_mode_check.isChecked(),
            "combine_stems": self.combine_stems_check.isChecked(),
            "invert_spec": self.invert_spec_check.isChecked(),
            # Secondary model settings
            "enable_secondary": self.enable_secondary_check.isChecked(),
            "secondary_models": {
                "vocals": self.vocals_model_combo.currentText(),
                "bass": self.bass_model_combo.currentText(),
                "drums": self.drums_model_combo.currentText(),
                "other": self.other_model_combo.currentText(),
            },
            "secondary_scales": {
                "vocals": self.vocals_scale_slider.value(),
                "bass": self.bass_scale_slider.value(),
                "drums": self.drums_scale_slider.value(),
                "other": self.other_scale_slider.value(),
            },
            # Preprocess settings
            "enable_preprocess": self.enable_preprocess_check.isChecked(),
            "preprocess_model": self.preprocess_model_combo.currentText(),
            "save_inst_mix": self.save_inst_mix_check.isChecked(),
            # Vocal splitter settings
            "enable_vocal": self.enable_vocal_check.isChecked(),
            "vocal_splitter_model": self.vocal_splitter_combo.currentText(),
            "enable_deverb": self.enable_deverb_check.isChecked(),
            "deverb_model": self.deverb_model_combo.currentText(),
        }

        self.settings_updated.emit(settings)
        self.accept()

    def _on_tab_changed(self, index):
        """Handle tab change to implement lazy loading."""
        if index == 1 and not self._models_loaded:  # Secondary tab is index 1
            self._load_models_if_needed()

    def _load_models_if_needed(self):
        """Lazy load models only when needed - optimized to load all models once."""
        if self._models_loaded:
            return

        try:
            from ..core import app_constants as ac
            from ..core.model_data import ModelData
            from ..core.uvr_core_adapter import UVRCoreAdapter

            # Load all models once and cache them
            adapter = UVRCoreAdapter()
            all_suitable_models = []

            # Get all available models from all architectures (do this once)
            for arch_key in [
                ac.VR_ARCH_MODELS_KEY,
                ac.MDX_NET_MODELS_KEY,
                ac.DEMUCS_MODELS_KEY,
            ]:
                arch_models = adapter.get_available_models(arch_key)

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

            logger.debug(
                "Demucs models loaded successfully for secondary tab (optimized)"
            )

        except Exception as e:
            logger.error(f"Error loading Demucs models: {e}")
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

        sections = ["vocals", "bass", "drums", "other"]
        for section in sections:
            # Model selection - Demucs uses nested structure
            model_key = f"demucs_{section}_secondary_model"
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


class DemucsAdvancedPresenter(QObject):
    """Presenter for the Demucs advanced dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_settings = {}

    def show_dialog(self, parent_widget=None, current_settings=None):
        """Show the advanced dialog."""
        dialog = DemucsAdvancedDialog(current_settings, parent_widget)
        dialog.settings_updated.connect(self.update_settings)
        return dialog.exec()

    def update_settings(self, settings):
        """Update the current settings."""
        self._current_settings = settings

    def get_settings(self):
        """Get the current settings."""
        return self._current_settings
