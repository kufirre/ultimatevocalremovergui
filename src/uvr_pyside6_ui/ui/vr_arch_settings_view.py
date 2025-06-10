from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.logger_utils import get_logger

logger = get_logger("vr_settings_view")


class VRArchSettingsView(QWidget):
    """View for VR Architecture specific settings."""

    # Define signals for changes
    window_size_changed = Signal(str)
    aggression_changed = Signal(int)
    high_end_changed = Signal(bool)
    tta_changed = Signal(bool)
    post_process_changed = Signal(bool)
    post_process_threshold_changed = Signal(float)
    batch_size_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        main_container_layout = QVBoxLayout(self)
        main_container_layout.setContentsMargins(0, 0, 0, 0)

        settings_group = QGroupBox("VR Architecture Settings")
        grid_layout = QGridLayout(settings_group)
        grid_layout.setContentsMargins(8, 8, 8, 8)
        grid_layout.setSpacing(8)

        # Row 0: Window Size and Batch Size
        win_label = QLabel("Window Size:")
        self.win_combo = QComboBox()
        self.win_combo.addItems(["320", "512", "1024"])
        self.win_combo.setCurrentText("512")
        self.win_combo.setToolTip(
            "Size of the processing window. Larger values may improve quality but use more memory."
        )
        self.win_combo.currentTextChanged.connect(self.window_size_changed)

        batch_label = QLabel("Batch Size:")
        self.batch_spin = QSpinBox()
        self.batch_spin.setMinimum(1)
        self.batch_spin.setMaximum(16)
        self.batch_spin.setValue(4)
        self.batch_spin.setToolTip(
            "Number of samples processed simultaneously. Higher values use more memory."
        )
        self.batch_spin.valueChanged.connect(self.batch_size_changed)

        grid_layout.addWidget(win_label, 0, 0)
        grid_layout.addWidget(self.win_combo, 0, 1)
        grid_layout.addWidget(batch_label, 0, 2)
        grid_layout.addWidget(self.batch_spin, 0, 3)

        # Row 1: Aggression Slider (spanning all columns)
        agg_label = QLabel("Aggression:")
        self.agg_slider = QSlider(Qt.Horizontal)
        self.agg_slider.setMinimum(1)
        self.agg_slider.setMaximum(100)
        self.agg_slider.setValue(5)
        self.agg_slider.setToolTip(
            "Separation aggressiveness. Higher values may improve separation but can introduce artifacts."
        )
        self.agg_value_label = QLabel(f"{self.agg_slider.value():3d}")
        self.agg_value_label.setMinimumWidth(30)

        def update_aggression_label(value):
            self.agg_value_label.setText(f"{value:3d}")

        self.agg_slider.valueChanged.connect(update_aggression_label)
        self.agg_slider.valueChanged.connect(self.aggression_changed)

        grid_layout.addWidget(agg_label, 1, 0)
        grid_layout.addWidget(self.agg_slider, 1, 1, 1, 2)  # Span 2 columns
        grid_layout.addWidget(self.agg_value_label, 1, 3)

        # Row 2: Post Process Threshold (when post process is enabled)
        pp_threshold_label = QLabel("Post Process Threshold:")
        self.pp_threshold_slider = QSlider(Qt.Horizontal)
        self.pp_threshold_slider.setMinimum(1)
        self.pp_threshold_slider.setMaximum(50)
        self.pp_threshold_slider.setValue(20)
        self.pp_threshold_slider.setEnabled(False)  # Disabled by default
        self.pp_threshold_slider.setToolTip(
            "Threshold for post-processing artifact removal."
        )
        self.pp_threshold_value_label = QLabel(
            f"{self.pp_threshold_slider.value()/100:.2f}"
        )
        self.pp_threshold_value_label.setMinimumWidth(40)

        def update_pp_threshold_label(value):
            threshold_val = value / 100.0
            self.pp_threshold_value_label.setText(f"{threshold_val:.2f}")
            self.post_process_threshold_changed.emit(threshold_val)

        self.pp_threshold_slider.valueChanged.connect(update_pp_threshold_label)

        grid_layout.addWidget(pp_threshold_label, 2, 0)
        grid_layout.addWidget(self.pp_threshold_slider, 2, 1, 1, 2)  # Span 2 columns
        grid_layout.addWidget(self.pp_threshold_value_label, 2, 3)

        # Row 3: Advanced Options Checkboxes (all in one row to save height)
        self.high_end_checkbox = QCheckBox("High End Process")
        self.high_end_checkbox.setToolTip(
            "Enable high-end frequency processing for better quality."
        )
        self.high_end_checkbox.toggled.connect(self.high_end_changed)

        self.post_process_checkbox = QCheckBox("Post Process")
        self.post_process_checkbox.setToolTip(
            "Enable post-processing to reduce artifacts."
        )

        def toggle_post_process(enabled):
            self.pp_threshold_slider.setEnabled(enabled)
            self.pp_threshold_value_label.setEnabled(enabled)
            pp_threshold_label.setEnabled(enabled)
            self.post_process_changed.emit(enabled)

        self.post_process_checkbox.toggled.connect(toggle_post_process)

        self.tta_checkbox = QCheckBox("TTA")
        self.tta_checkbox.setToolTip(
            "Enable test-time augmentation for potentially better results (slower processing)."
        )
        self.tta_checkbox.toggled.connect(self.tta_changed)

        # Put all three checkboxes in row 3 to save vertical space
        grid_layout.addWidget(self.high_end_checkbox, 3, 0)
        grid_layout.addWidget(self.post_process_checkbox, 3, 1)
        grid_layout.addWidget(self.tta_checkbox, 3, 2, 1, 2)  # TTA spans last 2 columns

        # Set column stretch ratios for better space utilization
        grid_layout.setColumnStretch(0, 0)  # Labels take minimum space
        grid_layout.setColumnStretch(1, 1)  # Controls take available space
        grid_layout.setColumnStretch(2, 0)  # Second set of labels take minimum space
        grid_layout.setColumnStretch(
            3, 1
        )  # Second set of controls take available space

        main_container_layout.addWidget(settings_group)
        self.setLayout(main_container_layout)

        logger.debug("VRArchSettingsView initialized")

    # --- Slots (Called by Presenter) ---
    @Slot(str)
    def set_window_size(self, value: str):
        self.win_combo.blockSignals(True)
        self.win_combo.setCurrentText(value)
        self.win_combo.blockSignals(False)

    @Slot(int)
    def set_aggression(self, value: int):
        self.agg_slider.blockSignals(True)
        self.agg_slider.setValue(value)
        self.agg_value_label.setText(f"{value:3d}")
        self.agg_slider.blockSignals(False)

    @Slot(bool)
    def set_high_end(self, enabled: bool):
        self.high_end_checkbox.blockSignals(True)
        self.high_end_checkbox.setChecked(enabled)
        self.high_end_checkbox.blockSignals(False)

    @Slot(bool)
    def set_tta(self, enabled: bool):
        self.tta_checkbox.blockSignals(True)
        self.tta_checkbox.setChecked(enabled)
        self.tta_checkbox.blockSignals(False)

    @Slot(bool)
    def set_post_process(self, enabled: bool):
        self.post_process_checkbox.blockSignals(True)
        self.post_process_checkbox.setChecked(enabled)
        self.post_process_checkbox.blockSignals(False)

    @Slot(float)
    def set_post_process_threshold(self, value: float):
        self.pp_threshold_slider.blockSignals(True)
        slider_value = int(value * 100)
        self.pp_threshold_slider.setValue(slider_value)
        self.pp_threshold_value_label.setText(f"{value:.2f}")
        self.pp_threshold_slider.blockSignals(False)

    @Slot(int)
    def set_batch_size(self, value: int):
        self.batch_spin.blockSignals(True)
        self.batch_spin.setValue(value)
        self.batch_spin.blockSignals(False)
