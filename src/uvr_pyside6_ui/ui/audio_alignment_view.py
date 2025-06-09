"""View for the Audio Alignment Tool."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class AudioAlignmentView(QDialog):
    """Dialog for audio alignment and synchronization."""

    # Define signals
    alignment_applied = Signal(dict)
    preview_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio Alignment Tool")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # Description section
        description_label = QLabel(
            "This tool helps align audio tracks for better separation results."
        )
        description_label.setWordWrap(True)
        main_layout.addWidget(description_label)

        # Alignment Method section
        method_group = QGroupBox("Alignment Method")
        method_layout = QVBoxLayout(method_group)

        self.auto_align_checkbox = QCheckBox("Auto-detect Alignment")
        self.auto_align_checkbox.setChecked(True)
        self.auto_align_checkbox.toggled.connect(self._toggle_manual_controls)
        method_layout.addWidget(self.auto_align_checkbox)

        # Manual Alignment Controls
        manual_controls_layout = QFormLayout()
        
        # Time Shift
        self.time_shift_label = QLabel("Time Shift (ms):")
        self.time_shift_spin = QSpinBox()
        self.time_shift_spin.setRange(-5000, 5000)
        self.time_shift_spin.setValue(0)
        self.time_shift_spin.setSingleStep(10)
        self.time_shift_spin.setEnabled(False)
        manual_controls_layout.addRow(self.time_shift_label, self.time_shift_spin)
        
        # Phase Correction
        self.phase_correction_label = QLabel("Phase Correction:")
        self.phase_correction_combo = QComboBox()
        self.phase_correction_combo.addItems(["None", "Normal", "Invert"])
        self.phase_correction_combo.setEnabled(False)
        manual_controls_layout.addRow(self.phase_correction_label, self.phase_correction_combo)
        
        method_layout.addLayout(manual_controls_layout)
        main_layout.addWidget(method_group)

        # Advanced Options section
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QFormLayout(advanced_group)
        
        # Correlation Window
        self.correlation_window_label = QLabel("Correlation Window:")
        self.correlation_window_combo = QComboBox()
        self.correlation_window_combo.addItems(["Short", "Medium", "Long"])
        self.correlation_window_combo.setCurrentText("Medium")
        advanced_layout.addRow(self.correlation_window_label, self.correlation_window_combo)
        
        # Sensitivity
        self.sensitivity_label = QLabel("Detection Sensitivity:")
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_value_label = QLabel("5")
        self.sensitivity_slider.valueChanged.connect(
            lambda v: self.sensitivity_value_label.setText(str(v))
        )
        
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(self.sensitivity_slider)
        sensitivity_layout.addWidget(self.sensitivity_value_label)
        advanced_layout.addRow(self.sensitivity_label, sensitivity_layout)
        
        # Threshold
        self.threshold_label = QLabel("Alignment Threshold:")
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setValue(0.7)
        self.threshold_spin.setSingleStep(0.05)
        advanced_layout.addRow(self.threshold_label, self.threshold_spin)
        
        main_layout.addWidget(advanced_group)

        # Apply to Processing section
        apply_group = QGroupBox("Apply to Processing")
        apply_layout = QVBoxLayout(apply_group)
        
        self.apply_to_all_checkbox = QCheckBox("Apply to all files in batch")
        self.apply_to_all_checkbox.setChecked(True)
        apply_layout.addWidget(self.apply_to_all_checkbox)
        
        self.save_settings_checkbox = QCheckBox("Save as default alignment settings")
        apply_layout.addWidget(self.save_settings_checkbox)
        
        main_layout.addWidget(apply_group)

        # Buttons
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self._on_preview)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply)
        self.apply_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)

    def _toggle_manual_controls(self, auto_enabled):
        """Enable/disable manual controls based on auto-align checkbox."""
        manual_enabled = not auto_enabled
        self.time_shift_spin.setEnabled(manual_enabled)
        self.phase_correction_combo.setEnabled(manual_enabled)

    def _on_preview(self):
        """Handle preview button click."""
        settings = self._get_current_settings()
        self.preview_requested.emit(settings)

    def _on_apply(self):
        """Handle apply button click."""
        settings = self._get_current_settings()
        self.alignment_applied.emit(settings)
        self.accept()

    def _get_current_settings(self):
        """Get current settings as a dictionary."""
        return {
            "auto_align": self.auto_align_checkbox.isChecked(),
            "time_shift_ms": self.time_shift_spin.value(),
            "phase_correction": self.phase_correction_combo.currentText(),
            "correlation_window": self.correlation_window_combo.currentText(),
            "sensitivity": self.sensitivity_slider.value(),
            "threshold": self.threshold_spin.value(),
            "apply_to_all": self.apply_to_all_checkbox.isChecked(),
            "save_settings": self.save_settings_checkbox.isChecked(),
        }

    def set_settings(self, settings):
        """Load settings into the dialog."""
        if "auto_align" in settings:
            self.auto_align_checkbox.setChecked(settings["auto_align"])
            
        if "time_shift_ms" in settings:
            self.time_shift_spin.setValue(settings["time_shift_ms"])
            
        if "phase_correction" in settings:
            index = self.phase_correction_combo.findText(settings["phase_correction"])
            if index >= 0:
                self.phase_correction_combo.setCurrentIndex(index)
                
        if "correlation_window" in settings:
            index = self.correlation_window_combo.findText(settings["correlation_window"])
            if index >= 0:
                self.correlation_window_combo.setCurrentIndex(index)
                
        if "sensitivity" in settings:
            self.sensitivity_slider.setValue(settings["sensitivity"])
            
        if "threshold" in settings:
            self.threshold_spin.setValue(settings["threshold"])
            
        if "apply_to_all" in settings:
            self.apply_to_all_checkbox.setChecked(settings["apply_to_all"])
            
        if "save_settings" in settings:
            self.save_settings_checkbox.setChecked(settings["save_settings"])
