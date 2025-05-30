from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QCheckBox
)
from PySide6.QtCore import Signal, Slot


class DemucsSettingsView(QWidget):
    """View for Demucs specific settings."""
    segments_changed = Signal(int)
    shifts_changed = Signal(int)
    split_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        settings_group = QGroupBox("Demucs Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Segments
        seg_layout = QHBoxLayout()
        seg_label = QLabel("Segments:")
        self.seg_spin = QSpinBox()
        self.seg_spin.setMinimum(1)
        self.seg_spin.setMaximum(50)
        self.seg_spin.setValue(10)
        self.seg_spin.valueChanged.connect(self.segments_changed)
        seg_layout.addWidget(seg_label)
        seg_layout.addWidget(self.seg_spin)
        seg_layout.addStretch(1)
        settings_layout.addLayout(seg_layout)

        # Shifts
        shift_layout = QHBoxLayout()
        shift_label = QLabel("Shifts:")
        self.shift_spin = QSpinBox()
        self.shift_spin.setMinimum(0)
        self.shift_spin.setMaximum(10)
        self.shift_spin.setValue(2)
        self.shift_spin.valueChanged.connect(self.shifts_changed)
        shift_layout.addWidget(shift_label)
        shift_layout.addWidget(self.shift_spin)
        shift_layout.addStretch(1)
        settings_layout.addLayout(shift_layout)

        # Split
        self.split_checkbox = QCheckBox("Split Audio")
        self.split_checkbox.setChecked(True)
        self.split_checkbox.toggled.connect(self.split_changed)
        settings_layout.addWidget(self.split_checkbox)

        layout.addWidget(settings_group)
        self.setLayout(layout)
        # Debug print removed
