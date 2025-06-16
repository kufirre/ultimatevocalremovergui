from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class DemucsSettingsView(QWidget):
    """View for Demucs simple settings (on main separation page) - stems and segments."""

    segments_changed = Signal(int)
    stems_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        settings_group = QGroupBox("Demucs Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Stems selection
        stems_layout = QHBoxLayout()
        stems_label = QLabel("Extract:")
        self.stems_combo = QComboBox()
        self.stems_combo.addItems(
            ["All Stems", "Vocals", "Bass", "Drums", "Other", "Instrumental"]
        )
        stems_layout.addWidget(stems_label)
        stems_layout.addWidget(self.stems_combo)
        stems_layout.addStretch()

        # Segments selection
        segments_layout = QHBoxLayout()
        segments_label = QLabel("Segments:")
        self.segments_combo = QComboBox()
        self.segments_combo.addItems(
            [
                "Default",
                "1",
                "5",
                "10",
                "15",
                "20",
                "25",
                "30",
                "35",
                "40",
                "45",
                "50",
                "55",
                "60",
                "65",
                "70",
                "75",
                "80",
                "85",
                "90",
                "95",
                "100",
            ]
        )
        segments_layout.addWidget(segments_label)
        segments_layout.addWidget(self.segments_combo)
        segments_layout.addStretch()

        settings_layout.addLayout(stems_layout)
        settings_layout.addLayout(segments_layout)

        layout.addWidget(settings_group)
        layout.addStretch()

        # Connect signals
        self.stems_combo.currentTextChanged.connect(self.stems_changed.emit)
        self.segments_combo.currentTextChanged.connect(self._on_segments_changed)

    def _on_segments_changed(self, text):
        """Convert segments text to integer and emit signal."""
        if text == "Default":
            self.segments_changed.emit(40)  # Default value
        else:
            self.segments_changed.emit(int(text))

    def get_stems(self):
        return self.stems_combo.currentText()

    def set_stems(self, stems):
        index = self.stems_combo.findText(stems)
        if index >= 0:
            self.stems_combo.setCurrentIndex(index)

    def get_segments(self):
        text = self.segments_combo.currentText()
        return 40 if text == "Default" else int(text)

    def set_segments(self, segments):
        if segments == 40:
            self.segments_combo.setCurrentText("Default")
        else:
            self.segments_combo.setCurrentText(str(segments))


class AdvancedDemucsSettingsView(QDialog):
    """Advanced settings dialog for Demucs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Demucs Options")
        self.setModal(True)
        self.setMinimumSize(500, 600)  # Increased size for better spacing

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Add proper spacing
        layout.setContentsMargins(20, 20, 20, 20)  # Add margins

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Primary Models Tab
        primary_tab = QWidget()
        primary_layout = QVBoxLayout(primary_tab)
        primary_layout.setSpacing(10)
        primary_layout.setContentsMargins(15, 15, 15, 15)

        # Stem Selection
        stem_group = QGroupBox("Stem Selection")
        stem_layout = QFormLayout(stem_group)
        stem_layout.setSpacing(8)

        self.primary_stem_combo = QComboBox()
        self.primary_stem_combo.addItems(
            ["All Stems", "Vocals", "Other", "Bass", "Drums"]
        )
        self.primary_stem_combo.setMinimumWidth(150)
        stem_layout.addRow("Primary Stem:", self.primary_stem_combo)

        self.secondary_stem_combo = QComboBox()
        self.secondary_stem_combo.addItems(["None", "Vocals", "Other", "Bass", "Drums"])
        self.secondary_stem_combo.setMinimumWidth(150)
        stem_layout.addRow("Secondary Stem:", self.secondary_stem_combo)

        primary_layout.addWidget(stem_group)

        # Processing Options
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(8)

        self.split_mode_check = QCheckBox("Split Mode")
        options_layout.addWidget(self.split_mode_check)

        self.combine_stems_check = QCheckBox("Combine Stems to Mixture")
        options_layout.addWidget(self.combine_stems_check)

        primary_layout.addWidget(options_group)

        # Segments and Overlap
        segments_group = QGroupBox("Segments and Overlap")
        segments_layout = QFormLayout(segments_group)
        segments_layout.setSpacing(10)

        # Segments
        self.segments_label = QLabel("Segments:")
        self.segments_value_label = QLabel("Default")
        self.segments_value_label.setAlignment(Qt.AlignCenter)
        self.segments_value_label.setMinimumWidth(60)
        self.segments_slider = QSlider(Qt.Horizontal)
        self.segments_slider.setMinimum(1)
        self.segments_slider.setMaximum(100)
        self.segments_slider.setValue(0)  # 0 = Default
        self.segments_slider.setMinimumWidth(200)
        self.segments_slider.valueChanged.connect(self._update_segments_label)

        segments_widget = QHBoxLayout()
        segments_widget.setSpacing(10)
        segments_widget.addWidget(self.segments_slider)
        segments_widget.addWidget(self.segments_value_label)
        segments_layout.addRow(self.segments_label, segments_widget)

        # Overlap
        self.overlap_label = QLabel("Overlap:")
        self.overlap_value_label = QLabel("0.25")
        self.overlap_value_label.setAlignment(Qt.AlignCenter)
        self.overlap_value_label.setMinimumWidth(60)
        self.overlap_slider = QSlider(Qt.Horizontal)
        self.overlap_slider.setMinimum(1)
        self.overlap_slider.setMaximum(99)
        self.overlap_slider.setValue(25)
        self.overlap_slider.setMinimumWidth(200)
        self.overlap_slider.valueChanged.connect(self._update_overlap_label)

        overlap_widget = QHBoxLayout()
        overlap_widget.setSpacing(10)
        overlap_widget.addWidget(self.overlap_slider)
        overlap_widget.addWidget(self.overlap_value_label)
        segments_layout.addRow(self.overlap_label, overlap_widget)

        primary_layout.addWidget(segments_group)

        # Shifts
        shifts_group = QGroupBox("Shifts")
        shifts_layout = QFormLayout(shifts_group)
        shifts_layout.setSpacing(10)

        self.shifts_label = QLabel("Number of Shifts:")
        self.shifts_value_label = QLabel("2")
        self.shifts_value_label.setAlignment(Qt.AlignCenter)
        self.shifts_value_label.setMinimumWidth(60)
        self.shifts_slider = QSlider(Qt.Horizontal)
        self.shifts_slider.setMinimum(0)
        self.shifts_slider.setMaximum(20)
        self.shifts_slider.setValue(2)
        self.shifts_slider.setMinimumWidth(200)
        self.shifts_slider.valueChanged.connect(
            lambda v: self.shifts_value_label.setText(str(v))
        )

        shifts_widget = QHBoxLayout()
        shifts_widget.setSpacing(10)
        shifts_widget.addWidget(self.shifts_slider)
        shifts_widget.addWidget(self.shifts_value_label)
        shifts_layout.addRow(self.shifts_label, shifts_widget)

        primary_layout.addWidget(shifts_group)
        primary_layout.addStretch()

        self.tab_widget.addTab(primary_tab, "Primary Models")

        # Secondary Models Tab
        secondary_tab = QWidget()
        secondary_layout = QVBoxLayout(secondary_tab)
        secondary_layout.setSpacing(10)
        secondary_layout.setContentsMargins(15, 15, 15, 15)

        # Model Selection
        model_group = QGroupBox("Model Selection")
        model_layout = QFormLayout(model_group)
        model_layout.setSpacing(8)

        self.secondary_model_combo = QComboBox()
        self.secondary_model_combo.addItems(
            ["None", "htdemucs", "htdemucs_ft", "htdemucs_6s"]
        )
        self.secondary_model_combo.setMinimumWidth(150)
        model_layout.addRow("Secondary Model:", self.secondary_model_combo)

        secondary_layout.addWidget(model_group)
        secondary_layout.addStretch()

        self.tab_widget.addTab(secondary_tab, "Secondary Models")

        layout.addWidget(self.tab_widget)

        # Dialog buttons - Apply/Close at the right
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.accept
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Close).clicked.connect(
            self.reject
        )

        layout.addWidget(self.button_box)

    def _update_segments_label(self):
        """Update the segments label based on the slider value."""
        self.segments_value_label.setText(str(self.segments_slider.value()))

    def _update_overlap_label(self):
        """Update the overlap label based on the slider value."""
        self.overlap_value_label.setText(str(self.overlap_slider.value() / 100))
