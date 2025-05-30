from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QCheckBox, QHBoxLayout, QLabel, QComboBox, QGridLayout
)
from PySide6.QtCore import Signal, Slot, Qt


class ProcessingSettingsView(QWidget):
    """
    View for common processing settings like GPU usage, output format,
    stem saving options, and sample mode.
    """
    gpu_conversion_changed = Signal(bool)
    normalize_output_changed = Signal(bool)
    output_format_changed = Signal(str)
    primary_stem_only_changed = Signal(bool)
    secondary_stem_only_changed = Signal(bool)
    sample_mode_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        main_container_layout = QVBoxLayout(self)
        main_container_layout.setContentsMargins(0, 0, 0, 0)

        settings_group = QGroupBox("Processing Options")
        grid_layout = QGridLayout(settings_group) # Use QGridLayout directly in GroupBox

        # Row 0: GPU Conversion, Output Format
        self.gpu_checkbox = QCheckBox("GPU Conversion")
        self.gpu_checkbox.setToolTip("Enable GPU acceleration if a compatible GPU is available.")
        self.gpu_checkbox.toggled.connect(self.gpu_conversion_changed)
        grid_layout.addWidget(self.gpu_checkbox, 0, 0)

        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["WAV", "FLAC", "MP3"])
        self.format_combo.setToolTip("Select the desired audio format for output files.")
        self.format_combo.currentTextChanged.connect(self.output_format_changed)
        
        format_layout = QHBoxLayout() # To keep label and combo together
        format_layout.addStretch(1) # Push to right
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        grid_layout.addLayout(format_layout, 0, 1, Qt.AlignRight) # Add QHBoxLayout to grid cell

        # Row 1: Stem Saving Options
        self.primary_stem_checkbox = QCheckBox("Primary Stem Only")
        self.primary_stem_checkbox.setToolTip("Save only the primary target stem (e.g., Vocals).")
        self.primary_stem_checkbox.toggled.connect(self.primary_stem_only_changed)
        grid_layout.addWidget(self.primary_stem_checkbox, 1, 0, 1, 1, Qt.AlignLeft)

        self.secondary_stem_checkbox = QCheckBox("Secondary Stem Only")
        self.secondary_stem_checkbox.setToolTip("Save only the secondary stem (e.g., Instrumental).")
        self.secondary_stem_checkbox.toggled.connect(self.secondary_stem_only_changed)
        grid_layout.addWidget(self.secondary_stem_checkbox, 1, 1, 1, 1, Qt.AlignLeft) # Align to left in its cell

        # Row 2: Other Options
        self.normalize_checkbox = QCheckBox("Normalize Output")
        self.normalize_checkbox.setToolTip("Normalize audio output to prevent clipping.")
        self.normalize_checkbox.toggled.connect(self.normalize_output_changed)
        grid_layout.addWidget(self.normalize_checkbox, 2, 0)

        self.sample_mode_checkbox = QCheckBox("Sample Mode")
        self.sample_mode_checkbox.setToolTip(
            "Process only a short sample of the audio (duration configured in Preferences).")
        self.sample_mode_checkbox.toggled.connect(self.sample_mode_changed)
        grid_layout.addWidget(self.sample_mode_checkbox, 2, 1, Qt.AlignLeft) # Align to left

        # Set column stretch to push second column content to the right if space allows
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setHorizontalSpacing(16)
        grid_layout.setVerticalSpacing(10)

        main_container_layout.addWidget(settings_group)
        self.setLayout(main_container_layout)
        print("ProcessingSettingsView Initialized with QGridLayout.")

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
