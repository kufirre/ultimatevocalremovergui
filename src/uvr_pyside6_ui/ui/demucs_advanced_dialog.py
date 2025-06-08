from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QComboBox, QCheckBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QDialogButtonBox, QSlider, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
import logging
import os
import platform
import subprocess
from pathlib import Path

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
        tab_widget.setStyleSheet("""
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
        """)
        layout.addWidget(tab_widget)
        
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
                    self,
                    "Models Folder",
                    f"Demucs models folder: {demucs_models_dir}"
                )
                    
        except Exception as e:
            logger.error(f"Error opening models folder: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Open Folder Error",
                f"Failed to open models folder: {str(e)}"
            )
        
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
        
        self.open_models_btn = QPushButton("Open Models Folder")
        self.open_models_btn.clicked.connect(self._open_models_folder)
        actions_layout.addWidget(self.open_models_btn)
        
        layout.addWidget(actions_group)
        layout.addStretch()  # Push everything to the top
        
        return widget
        
    def _create_secondary_model_tab(self):
        """Create the secondary model tab with four separate sections."""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        # Enable Secondary Model
        self.enable_secondary_check = QCheckBox("Enable Secondary Model")
        self.enable_secondary_check.setChecked(False)
        layout.addWidget(self.enable_secondary_check)
        
        # Create scroll area for the four sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QFrame()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Store secondary model widgets for enable/disable
        self.secondary_widgets = []
        
        # 1. Vocals/Instruments Section
        vocals_group = QGroupBox("Vocals/Instruments")
        vocals_layout = QFormLayout(vocals_group)
        
        self.vocals_model_combo = QComboBox()
        self.vocals_model_combo.addItems([
            "No Model", "UVR-MDX-NET-1_9.onnx", "UVR-MDX-NET-2_9.onnx", 
            "UVR-MDX-NET-3_9.onnx", "Kim_Vocal_1.onnx"
        ])
        self.vocals_model_combo.setEnabled(False)
        vocals_layout.addRow("Model:", self.vocals_model_combo)
        
        # Vocals Scale with better UI
        vocals_scale_layout = QHBoxLayout()
        self.vocals_scale_slider = QSlider(Qt.Horizontal)
        self.vocals_scale_slider.setRange(10, 100)
        self.vocals_scale_slider.setValue(100)
        self.vocals_scale_slider.setEnabled(False)
        self.vocals_scale_slider.setMinimumWidth(200)
        
        self.vocals_scale_label = QLabel("100%")
        self.vocals_scale_label.setMinimumWidth(50)
        self.vocals_scale_label.setAlignment(Qt.AlignCenter)
        self.vocals_scale_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        
        self.vocals_scale_slider.valueChanged.connect(
            lambda v: self.vocals_scale_label.setText(f"{v}%")
        )
        
        vocals_scale_layout.addWidget(self.vocals_scale_slider)
        vocals_scale_layout.addWidget(self.vocals_scale_label)
        vocals_layout.addRow("Scale:", vocals_scale_layout)
        
        scroll_layout.addWidget(vocals_group)
        self.secondary_widgets.extend([self.vocals_model_combo, self.vocals_scale_slider])
        
        # 2. Bass/No Bass Section  
        bass_group = QGroupBox("Bass/No Bass")
        bass_layout = QFormLayout(bass_group)
        
        self.bass_model_combo = QComboBox()
        self.bass_model_combo.addItems([
            "No Model", "UVR-MDX-NET-1_9.onnx", "UVR-MDX-NET-2_9.onnx",
            "UVR-MDX-NET-3_9.onnx", "Kim_Vocal_1.onnx"
        ])
        self.bass_model_combo.setEnabled(False)
        bass_layout.addRow("Model:", self.bass_model_combo)
        
        # Bass Scale
        bass_scale_layout = QHBoxLayout()
        self.bass_scale_slider = QSlider(Qt.Horizontal)
        self.bass_scale_slider.setRange(10, 100)
        self.bass_scale_slider.setValue(100)
        self.bass_scale_slider.setEnabled(False)
        self.bass_scale_slider.setMinimumWidth(200)
        
        self.bass_scale_label = QLabel("100%")
        self.bass_scale_label.setMinimumWidth(50)
        self.bass_scale_label.setAlignment(Qt.AlignCenter)
        self.bass_scale_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        
        self.bass_scale_slider.valueChanged.connect(
            lambda v: self.bass_scale_label.setText(f"{v}%")
        )
        
        bass_scale_layout.addWidget(self.bass_scale_slider)
        bass_scale_layout.addWidget(self.bass_scale_label)
        bass_layout.addRow("Scale:", bass_scale_layout)
        
        scroll_layout.addWidget(bass_group)
        self.secondary_widgets.extend([self.bass_model_combo, self.bass_scale_slider])
        
        # 3. Drums/No Drums Section
        drums_group = QGroupBox("Drums/No Drums")
        drums_layout = QFormLayout(drums_group)
        
        self.drums_model_combo = QComboBox()
        self.drums_model_combo.addItems([
            "No Model", "UVR-MDX-NET-1_9.onnx", "UVR-MDX-NET-2_9.onnx",
            "UVR-MDX-NET-3_9.onnx", "Kim_Vocal_1.onnx"
        ])
        self.drums_model_combo.setEnabled(False)
        drums_layout.addRow("Model:", self.drums_model_combo)
        
        # Drums Scale
        drums_scale_layout = QHBoxLayout()
        self.drums_scale_slider = QSlider(Qt.Horizontal)
        self.drums_scale_slider.setRange(10, 100)
        self.drums_scale_slider.setValue(100)
        self.drums_scale_slider.setEnabled(False)
        self.drums_scale_slider.setMinimumWidth(200)
        
        self.drums_scale_label = QLabel("100%")
        self.drums_scale_label.setMinimumWidth(50)
        self.drums_scale_label.setAlignment(Qt.AlignCenter)
        self.drums_scale_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        
        self.drums_scale_slider.valueChanged.connect(
            lambda v: self.drums_scale_label.setText(f"{v}%")
        )
        
        drums_scale_layout.addWidget(self.drums_scale_slider)
        drums_scale_layout.addWidget(self.drums_scale_label)
        drums_layout.addRow("Scale:", drums_scale_layout)
        
        scroll_layout.addWidget(drums_group)
        self.secondary_widgets.extend([self.drums_model_combo, self.drums_scale_slider])
        
        # 4. Other/No Other Section
        other_group = QGroupBox("Other/No Other")
        other_layout = QFormLayout(other_group)
        
        self.other_model_combo = QComboBox()
        self.other_model_combo.addItems([
            "No Model", "UVR-MDX-NET-1_9.onnx", "UVR-MDX-NET-2_9.onnx",
            "UVR-MDX-NET-3_9.onnx", "Kim_Vocal_1.onnx"
        ])
        self.other_model_combo.setEnabled(False)
        other_layout.addRow("Model:", self.other_model_combo)
        
        # Other Scale
        other_scale_layout = QHBoxLayout()
        self.other_scale_slider = QSlider(Qt.Horizontal)
        self.other_scale_slider.setRange(10, 100)
        self.other_scale_slider.setValue(100)
        self.other_scale_slider.setEnabled(False)
        self.other_scale_slider.setMinimumWidth(200)
        
        self.other_scale_label = QLabel("100%")
        self.other_scale_label.setMinimumWidth(50)
        self.other_scale_label.setAlignment(Qt.AlignCenter)
        self.other_scale_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        
        self.other_scale_slider.valueChanged.connect(
            lambda v: self.other_scale_label.setText(f"{v}%")
        )
        
        other_scale_layout.addWidget(self.other_scale_slider)
        other_scale_layout.addWidget(self.other_scale_label)
        other_layout.addRow("Scale:", other_scale_layout)
        
        scroll_layout.addWidget(other_group)
        self.secondary_widgets.extend([self.other_model_combo, self.other_scale_slider])
        
        # Add stretch to push content to top
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Connect enable checkbox
        self.enable_secondary_check.toggled.connect(self._toggle_secondary_widgets)
        
        return widget
        
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
        self.preprocess_model_combo.addItems([
            "No Model", "UVR_MDXNET_1_9703.onnx", "UVR_MDXNET_2_9682.onnx",
            "UVR_MDXNET_3_9662.onnx"
        ])
        self.preprocess_model_combo.setEnabled(False)
        layout.addRow("Preprocess Model:", self.preprocess_model_combo)
        
        # Save Instrument Mixture checkbox
        self.save_inst_mix_check = QCheckBox("Save Instrument Mixture")
        self.save_inst_mix_check.setChecked(False)
        self.save_inst_mix_check.setEnabled(False)
        layout.addRow(self.save_inst_mix_check)
        
        # Connect enable checkbox
        self.enable_preprocess_check.toggled.connect(
            lambda enabled: (
                self.preprocess_model_combo.setEnabled(enabled),
                self.save_inst_mix_check.setEnabled(enabled)
            )
        )
        
        return widget
        
    def _create_vocal_splitter_tab(self):
        """Create the vocal splitter tab."""
        widget = QFrame()
        layout = QFormLayout(widget)
        
        # Enable Vocal Split
        self.enable_vocal_split_check = QCheckBox("Enable Vocal Split Mode")
        self.enable_vocal_split_check.setChecked(False)
        layout.addRow(self.enable_vocal_split_check)
        
        # Vocal Model Selection
        self.vocal_model_combo = QComboBox()
        self.vocal_model_combo.addItems([
            "No Model", "2_HP-UVR.pth", "3_HP-Vocal-UVR.pth", 
            "4_HP-Vocal-UVR.pth", "5_HP-Karaoke-UVR.pth"
        ])
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
        self.deverb_type_combo.addItems([
            "Main Vocals Only", "Lead Vocals Only", 
            "Backing Vocals Only", "All Vocal Types"
        ])
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
        if 'shifts' in self.current_settings:
            self.shifts_spin.setValue(self.current_settings['shifts'])
        if 'overlap' in self.current_settings:
            self.overlap_spin.setValue(self.current_settings['overlap'])
        if 'semitone_shift' in self.current_settings:
            value = self.current_settings['semitone_shift']
            self.pitch_slider.setValue(value)
            self.pitch_value_label.setText(str(value))
        if 'is_split_mode' in self.current_settings:
            self.split_mode_check.setChecked(self.current_settings['is_split_mode'])
        if 'is_demucs_combine_stems' in self.current_settings:
            self.combine_stems_check.setChecked(self.current_settings['is_demucs_combine_stems'])
        if 'is_invert_spec' in self.current_settings:
            self.invert_spec_check.setChecked(self.current_settings['is_invert_spec'])
            
        # Secondary model settings
        if 'is_secondary_model' in self.current_settings:
            self.enable_secondary_check.setChecked(self.current_settings['is_secondary_model'])
            
        # Load settings for all four secondary model sections
        if 'vocals_secondary_model' in self.current_settings:
            model = self.current_settings['vocals_secondary_model']
            index = self.vocals_model_combo.findText(model)
            if index >= 0:
                self.vocals_model_combo.setCurrentIndex(index)
        if 'vocals_secondary_scale' in self.current_settings:
            scale = int(self.current_settings['vocals_secondary_scale'] * 100)
            self.vocals_scale_slider.setValue(scale)
            self.vocals_scale_label.setText(f"{scale}%")
            
        if 'bass_secondary_model' in self.current_settings:
            model = self.current_settings['bass_secondary_model']
            index = self.bass_model_combo.findText(model)
            if index >= 0:
                self.bass_model_combo.setCurrentIndex(index)
        if 'bass_secondary_scale' in self.current_settings:
            scale = int(self.current_settings['bass_secondary_scale'] * 100)
            self.bass_scale_slider.setValue(scale)
            self.bass_scale_label.setText(f"{scale}%")
            
        if 'drums_secondary_model' in self.current_settings:
            model = self.current_settings['drums_secondary_model']
            index = self.drums_model_combo.findText(model)
            if index >= 0:
                self.drums_model_combo.setCurrentIndex(index)
        if 'drums_secondary_scale' in self.current_settings:
            scale = int(self.current_settings['drums_secondary_scale'] * 100)
            self.drums_scale_slider.setValue(scale)
            self.drums_scale_label.setText(f"{scale}%")
            
        if 'other_secondary_model' in self.current_settings:
            model = self.current_settings['other_secondary_model']
            index = self.other_model_combo.findText(model)
            if index >= 0:
                self.other_model_combo.setCurrentIndex(index)
        if 'other_secondary_scale' in self.current_settings:
            scale = int(self.current_settings['other_secondary_scale'] * 100)
            self.other_scale_slider.setValue(scale)
            self.other_scale_label.setText(f"{scale}%")
            
        # Preprocess model settings
        if 'is_pre_proc_model' in self.current_settings:
            self.enable_preprocess_check.setChecked(self.current_settings['is_pre_proc_model'])
        if 'pre_proc_model' in self.current_settings:
            model = self.current_settings['pre_proc_model']
            index = self.preprocess_model_combo.findText(model)
            if index >= 0:
                self.preprocess_model_combo.setCurrentIndex(index)
        if 'is_demucs_pre_proc_model_inst_mix' in self.current_settings:
            self.save_inst_mix_check.setChecked(self.current_settings['is_demucs_pre_proc_model_inst_mix'])
            
        # Vocal splitter settings
        if 'is_set_vocal_splitter' in self.current_settings:
            self.enable_vocal_split_check.setChecked(self.current_settings['is_set_vocal_splitter'])
        if 'set_vocal_splitter' in self.current_settings:
            model = self.current_settings['set_vocal_splitter']
            index = self.vocal_model_combo.findText(model)
            if index >= 0:
                self.vocal_model_combo.setCurrentIndex(index)
        if 'is_save_inst_set_vocal_splitter' in self.current_settings:
            self.save_inst_check.setChecked(self.current_settings['is_save_inst_set_vocal_splitter'])
        if 'is_deverb_vocals' in self.current_settings:
            self.enable_deverb_check.setChecked(self.current_settings['is_deverb_vocals'])
        if 'deverb_vocal_opt' in self.current_settings:
            option = self.current_settings['deverb_vocal_opt']
            index = self.deverb_type_combo.findText(option)
            if index >= 0:
                self.deverb_type_combo.setCurrentIndex(index)
        
    def _apply_settings(self):
        """Apply the settings and emit the updated signal."""
        settings = {}
        
        # Advanced settings
        settings['shifts'] = self.shifts_spin.value()
        settings['overlap'] = self.overlap_spin.value()
        settings['semitone_shift'] = self.pitch_slider.value()
        settings['is_split_mode'] = self.split_mode_check.isChecked()
        settings['is_demucs_combine_stems'] = self.combine_stems_check.isChecked()
        settings['is_invert_spec'] = self.invert_spec_check.isChecked()
        
        # Secondary model settings
        settings['is_secondary_model'] = self.enable_secondary_check.isChecked()
        
        # Save settings for all four secondary model sections
        settings['vocals_secondary_model'] = self.vocals_model_combo.currentText()
        settings['vocals_secondary_scale'] = self.vocals_scale_slider.value() / 100.0
        settings['bass_secondary_model'] = self.bass_model_combo.currentText()
        settings['bass_secondary_scale'] = self.bass_scale_slider.value() / 100.0
        settings['drums_secondary_model'] = self.drums_model_combo.currentText()
        settings['drums_secondary_scale'] = self.drums_scale_slider.value() / 100.0
        settings['other_secondary_model'] = self.other_model_combo.currentText()
        settings['other_secondary_scale'] = self.other_scale_slider.value() / 100.0
        
        # Preprocess model settings
        settings['is_pre_proc_model'] = self.enable_preprocess_check.isChecked()
        settings['pre_proc_model'] = self.preprocess_model_combo.currentText()
        settings['is_demucs_pre_proc_model_inst_mix'] = self.save_inst_mix_check.isChecked()
        
        # Vocal splitter settings
        settings['is_set_vocal_splitter'] = self.enable_vocal_split_check.isChecked()
        settings['set_vocal_splitter'] = self.vocal_model_combo.currentText()
        settings['is_save_inst_set_vocal_splitter'] = self.save_inst_check.isChecked()
        settings['is_deverb_vocals'] = self.enable_deverb_check.isChecked()
        settings['deverb_vocal_opt'] = self.deverb_type_combo.currentText()
        
        logger.info(f"Demucs advanced settings updated: {settings}")
        
        self.settings_updated.emit(settings)
        self.accept()


class DemucsAdvancedPresenter(QObject):
    """Presenter for Demucs advanced settings dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_settings = {}
        
    def show_dialog(self, parent_widget=None, current_settings=None):
        """Show the advanced settings dialog."""
        if current_settings:
            self.current_settings = current_settings
            
        dialog = DemucsAdvancedDialog(self.current_settings, parent_widget)
        dialog.settings_updated.connect(self.update_settings)
        dialog.exec()
        
    def update_settings(self, settings):
        """Update the current settings."""
        self.current_settings.update(settings)
        logger.info(f"Demucs advanced settings presenter updated: {self.current_settings}")
        
    def get_settings(self):
        """Get the current advanced settings."""
        return self.current_settings.copy() 