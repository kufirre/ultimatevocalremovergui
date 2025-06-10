from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)


class MDXNetSettingsView(QWidget):
    """View for MDX-Net specific settings."""

    segment_size_changed = Signal(int)
    overlap_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        settings_group = QGroupBox("MDX-Net Settings")
        settings_layout = QHBoxLayout(settings_group)  # Changed to horizontal to save height
        
        # Segment Size
        seg_label = QLabel("Segment Size:")
        self.seg_spin = QSpinBox()
        self.seg_spin.setMinimum(64)
        self.seg_spin.setMaximum(1024)
        self.seg_spin.setSingleStep(64)
        self.seg_spin.setValue(256)
        self.seg_spin.valueChanged.connect(self.segment_size_changed)
        
        # Overlap
        overlap_label = QLabel("Overlap:")
        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setMinimum(0.0)
        self.overlap_spin.setMaximum(0.99)
        self.overlap_spin.setSingleStep(0.05)
        self.overlap_spin.setValue(0.25)
        self.overlap_spin.setDecimals(2)
        self.overlap_spin.valueChanged.connect(self.overlap_changed)
        
        # Add all elements in a single row to save vertical space
        settings_layout.addWidget(seg_label)
        settings_layout.addWidget(self.seg_spin)
        settings_layout.addSpacing(20)  # Add some spacing between controls
        settings_layout.addWidget(overlap_label)
        settings_layout.addWidget(self.overlap_spin)
        settings_layout.addStretch(1)

        layout.addWidget(settings_group)
        self.setLayout(layout)

    def get_settings(self):
        """Get current settings values."""
        return {
            'mdx_segment_size': self.seg_spin.value(),
            'overlap': self.overlap_spin.value()
        }

    def set_settings(self, settings):
        """Set settings values."""
        if 'mdx_segment_size' in settings:
            self.seg_spin.setValue(settings['mdx_segment_size'])
        if 'overlap' in settings:
            self.overlap_spin.setValue(settings['overlap'])
