from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QCheckBox, QHBoxLayout, QLabel, QComboBox
)
from PySide6.QtCore import Signal, Slot


class ProcessingSettingsView(QWidget):
    """
    View for common processing settings like GPU usage, output format, etc.
    """
    # Signals for the Presenter
    gpu_conversion_changed = Signal(bool)
    normalize_output_changed = Signal(bool)
    output_format_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        settings_group = QGroupBox("Processing Settings")
        settings_layout = QVBoxLayout(settings_group)

        # --- Checkboxes ---
        checkbox_layout = QVBoxLayout()
        self.gpu_checkbox = QCheckBox("GPU Conversion")
        self.gpu_checkbox.toggled.connect(self.gpu_conversion_changed)
        self.normalize_checkbox = QCheckBox("Normalize Output")
        self.normalize_checkbox.toggled.connect(self.normalize_output_changed)

        checkbox_layout.addWidget(self.gpu_checkbox)
        checkbox_layout.addWidget(self.normalize_checkbox)

        settings_layout.addLayout(checkbox_layout)

        # --- Output Format ---
        format_layout = QHBoxLayout()
        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["WAV", "FLAC", "MP3"])  # Example formats
        self.format_combo.currentTextChanged.connect(self.output_format_changed)

        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch(1)  # Pushes combo box left

        settings_layout.addLayout(format_layout)

        layout.addWidget(settings_group)
        self.setLayout(layout)

        print("ProcessingSettingsView Initialized.")

    # --- Slots (Called by the Presenter to update View state) ---

    @Slot(bool)
    def set_gpu_conversion_enabled(self, is_enabled):
        """Sets the enabled state of the GPU checkbox."""
        self.gpu_checkbox.setEnabled(is_enabled)
        if not is_enabled:
            self.gpu_checkbox.setChecked(False)

    @Slot(bool)
    def set_gpu_conversion_checked(self, is_checked):
        """Sets the checked state of the GPU checkbox."""
        self.gpu_checkbox.blockSignals(True)
        self.gpu_checkbox.setChecked(is_checked)
        self.gpu_checkbox.blockSignals(False)

    @Slot(bool)
    def set_normalize_checked(self, is_checked):
        """Sets the checked state of the Normalize checkbox."""
        self.normalize_checkbox.blockSignals(True)
        self.normalize_checkbox.setChecked(is_checked)
        self.normalize_checkbox.blockSignals(False)

    @Slot(str)
    def set_output_format(self, format_str):
        """Sets the current value in the Output Format combobox."""
        self.format_combo.blockSignals(True)
        self.format_combo.setCurrentText(format_str.upper())
        self.format_combo.blockSignals(False)
