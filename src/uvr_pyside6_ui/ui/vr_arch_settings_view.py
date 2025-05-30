from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox,
    QLabel, QHBoxLayout, QCheckBox, QSlider
)
from PySide6.QtCore import Signal, Slot, Qt


class VRArchSettingsView(QWidget):
    """View for VR Architecture specific settings."""
    # Define signals for changes
    window_size_changed = Signal(str)
    aggression_changed = Signal(int)
    high_end_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)  # Add some top/bottom margin

        settings_group = QGroupBox("VR Architecture Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Window Size
        win_layout = QHBoxLayout()
        win_label = QLabel("Window Size:")
        self.win_combo = QComboBox()
        self.win_combo.addItems(["320", "512", "1024"])  # Example values
        self.win_combo.currentTextChanged.connect(self.window_size_changed)
        win_layout.addWidget(win_label)
        win_layout.addWidget(self.win_combo)
        win_layout.addStretch(1)
        settings_layout.addLayout(win_layout)

        # Aggression
        agg_layout = QHBoxLayout()
        agg_label = QLabel("Aggression (1-100):")
        self.agg_slider = QSlider(Qt.Horizontal)
        self.agg_slider.setMinimum(1)
        self.agg_slider.setMaximum(100)
        self.agg_slider.setValue(5)  # Default
        self.agg_value_label = QLabel(f"{self.agg_slider.value():3d}")
        self.agg_slider.valueChanged.connect(
            lambda value: self.agg_value_label.setText(f"{value:3d}")
        )
        self.agg_slider.valueChanged.connect(self.aggression_changed)
        agg_layout.addWidget(agg_label)
        agg_layout.addWidget(self.agg_slider, 1)
        agg_layout.addWidget(self.agg_value_label)
        settings_layout.addLayout(agg_layout)

        # High End Process
        self.high_end_checkbox = QCheckBox("High End Process")
        self.high_end_checkbox.toggled.connect(self.high_end_changed)
        settings_layout.addWidget(self.high_end_checkbox)
        
        settings_layout.addStretch(1) # Push elements to the top

        layout.addWidget(settings_group)
        self.setLayout(layout)
        # Debug print removed

    # Add Slots here later if Presenter needs to set values.
