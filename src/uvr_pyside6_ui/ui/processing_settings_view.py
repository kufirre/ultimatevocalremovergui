from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QCheckBox, QHBoxLayout, QLabel, QComboBox
)
from PySide6.QtCore import Signal, Slot


class ProcessingSettingsView(QWidget):
    """
    View for common processing settings like GPU usage, output format,
    stem saving options, and sample mode.
    """
    gpu_conversion_changed = Signal(bool)
    normalize_output_changed = Signal(bool)
    output_format_changed = Signal(str)
    # NEW Signals
    primary_stem_only_changed = Signal(bool)
    secondary_stem_only_changed = Signal(bool)
    sample_mode_changed = Signal(bool)

    # sample_duration_changed = Signal(int) # For later, with a QSpinBox

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # GroupBox will provide margins

        settings_group = QGroupBox("Processing Options")  # Renamed for clarity
        settings_layout = QVBoxLayout(settings_group)

        # --- Top Row: GPU and Output Format ---
        gpu_format_layout = QHBoxLayout()
        self.gpu_checkbox = QCheckBox("GPU Conversion")
        self.gpu_checkbox.setToolTip("Enable GPU acceleration if a compatible GPU is available.")
        self.gpu_checkbox.toggled.connect(self.gpu_conversion_changed)
        gpu_format_layout.addWidget(self.gpu_checkbox)

        gpu_format_layout.addStretch(1)

        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["WAV", "FLAC", "MP3"])
        self.format_combo.setToolTip("Select the desired audio format for output files.")
        self.format_combo.currentTextChanged.connect(self.output_format_changed)
        gpu_format_layout.addWidget(format_label)
        gpu_format_layout.addWidget(self.format_combo)
        settings_layout.addLayout(gpu_format_layout)

        # --- Middle Row: Stem Saving Options ---
        stem_save_layout = QHBoxLayout()
        self.primary_stem_checkbox = QCheckBox("Primary Stem Only")
        self.primary_stem_checkbox.setToolTip("Save only the primary target stem (e.g., Vocals).")
        self.primary_stem_checkbox.toggled.connect(self.primary_stem_only_changed)

        self.secondary_stem_checkbox = QCheckBox("Secondary Stem Only")
        self.secondary_stem_checkbox.setToolTip("Save only the secondary stem (e.g., Instrumental).")
        self.secondary_stem_checkbox.toggled.connect(self.secondary_stem_only_changed)

        stem_save_layout.addWidget(self.primary_stem_checkbox)
        stem_save_layout.addWidget(self.secondary_stem_checkbox)
        stem_save_layout.addStretch(1)
        settings_layout.addLayout(stem_save_layout)

        # --- Bottom Row: Other Options ---
        other_opts_layout = QHBoxLayout()
        self.normalize_checkbox = QCheckBox("Normalize Output")
        self.normalize_checkbox.setToolTip("Normalize audio output to prevent clipping.")
        self.normalize_checkbox.toggled.connect(self.normalize_output_changed)

        self.sample_mode_checkbox = QCheckBox("Sample Mode")
        self.sample_mode_checkbox.setToolTip(
            "Process only a short sample of the audio (duration configured in Preferences).")
        self.sample_mode_checkbox.toggled.connect(self.sample_mode_changed)

        other_opts_layout.addWidget(self.normalize_checkbox)
        other_opts_layout.addWidget(self.sample_mode_checkbox)
        other_opts_layout.addStretch(1)
        settings_layout.addLayout(other_opts_layout)

        layout.addWidget(settings_group)
        self.setLayout(layout)
        print("ProcessingSettingsView Initialized with new checkboxes.")

    # --- Slots (Called by Presenter) ---
    @Slot(bool)
    def set_gpu_conversion_enabled(self, is_enabled: bool):
        self.gpu_checkbox.setEnabled(is_enabled)
        if not is_enabled: self.gpu_checkbox.setChecked(False)

    @Slot(bool)
    def set_gpu_conversion_checked(self, is_checked: bool):
        self.gpu_checkbox.blockSignals(True);
        self.gpu_checkbox.setChecked(is_checked);
        self.gpu_checkbox.blockSignals(False)

    @Slot(bool)
    def set_normalize_checked(self, is_checked: bool):
        self.normalize_checkbox.blockSignals(True);
        self.normalize_checkbox.setChecked(is_checked);
        self.normalize_checkbox.blockSignals(False)

    @Slot(str)
    def set_output_format(self, format_str: str):
        self.format_combo.blockSignals(True);
        self.format_combo.setCurrentText(format_str.upper());
        self.format_combo.blockSignals(False)

    @Slot(bool)
    def set_primary_stem_only_checked(self, is_checked: bool):
        self.primary_stem_checkbox.blockSignals(True)
        self.primary_stem_checkbox.setChecked(is_checked)
        self.primary_stem_checkbox.blockSignals(False)

    @Slot(bool)
    def set_secondary_stem_only_checked(self, is_checked: bool):
        self.secondary_stem_checkbox.blockSignals(True)
        self.secondary_stem_checkbox.setChecked(is_checked)
        self.secondary_stem_checkbox.blockSignals(False)

    @Slot(bool)
    def set_sample_mode_checked(self, is_checked: bool):
        self.sample_mode_checkbox.blockSignals(True)
        self.sample_mode_checkbox.setChecked(is_checked)
        self.sample_mode_checkbox.blockSignals(False)
