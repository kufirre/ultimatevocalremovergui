from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QSpinBox,
    QLabel, QHBoxLayout, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Signal, Slot


class MDXNetSettingsView(QWidget):
    """View for MDX-Net specific settings."""
    segment_size_changed = Signal(int)
    overlap_changed = Signal(float)
    match_method_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        settings_group = QGroupBox("MDX-Net Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Segment Size
        seg_layout = QHBoxLayout()
        seg_label = QLabel("Segment Size:")
        self.seg_spin = QSpinBox()
        self.seg_spin.setMinimum(64)
        self.seg_spin.setMaximum(1024)
        self.seg_spin.setSingleStep(64)
        self.seg_spin.setValue(256)
        self.seg_spin.valueChanged.connect(self.segment_size_changed)
        seg_layout.addWidget(seg_label)
        seg_layout.addWidget(self.seg_spin)
        seg_layout.addStretch(1)
        settings_layout.addLayout(seg_layout)

        # Overlap
        overlap_layout = QHBoxLayout()
        overlap_label = QLabel("Overlap:")
        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setMinimum(0.0)
        self.overlap_spin.setMaximum(0.99)
        self.overlap_spin.setSingleStep(0.05)
        self.overlap_spin.setValue(0.25)
        self.overlap_spin.valueChanged.connect(self.overlap_changed)
        overlap_layout.addWidget(overlap_label)
        overlap_layout.addWidget(self.overlap_spin)
        overlap_layout.addStretch(1)
        settings_layout.addLayout(overlap_layout)

        # Match Method
        match_layout = QHBoxLayout()
        match_label = QLabel("Match Method:")
        self.match_combo = QComboBox()
        self.match_combo.addItems(["Default", "Average", "Min/Max"])
        self.match_combo.currentTextChanged.connect(self.match_method_changed)
        match_layout.addWidget(match_label)
        match_layout.addWidget(self.match_combo)
        match_layout.addStretch(1)
        settings_layout.addLayout(match_layout)

        layout.addWidget(settings_group)
        self.setLayout(layout)
        # print("MDXNetSettingsView Initialized.") # Removed unprofessional comment
