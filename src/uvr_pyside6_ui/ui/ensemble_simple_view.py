"""Simplified Ensemble View for the main window."""

from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import app_constants as ac
from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class EnsembleSimpleView(QWidget):
    """Simplified widget for ensemble configuration in main window."""

    main_stem_pair_changed = Signal(str)
    ensemble_algorithm_changed = Signal(str)
    advanced_settings_requested = Signal()
    save_all_outputs_changed = Signal(bool)
    append_ensemble_name_changed = Signal(bool)
    use_waveform_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        # Main ensemble group
        ensemble_group = QGroupBox("Ensemble Settings")
        ensemble_layout = QVBoxLayout(ensemble_group)

        # Row 1: Stem Pair and Algorithm
        config_row = QHBoxLayout()
        
        # Stem Pair
        stem_pair_label = QLabel("Main Stem Pair:")
        stem_pair_label.setMinimumWidth(100)
        self.stem_pair_combo = QComboBox()
        self.stem_pair_combo.addItems(ac.ENSEMBLE_MAIN_STEM_OPTIONS)
        
        config_row.addWidget(stem_pair_label)
        config_row.addWidget(self.stem_pair_combo, 1)
        config_row.addSpacing(20)
        
        # Algorithm
        algorithm_label = QLabel("Algorithm:")
        algorithm_label.setMinimumWidth(80)
        self.algorithm_combo = QComboBox()
        
        config_row.addWidget(algorithm_label)
        config_row.addWidget(self.algorithm_combo, 1)
        
        ensemble_layout.addLayout(config_row)

        # Row 2: Ensemble Options Checkboxes
        options_row = QHBoxLayout()
        
        # Save all outputs checkbox
        self.save_all_outputs_checkbox = QCheckBox(ac.SAVE_ALL_OUTPUTS_TEXT)
        self.save_all_outputs_checkbox.setChecked(True)  # Default to True
        self.save_all_outputs_checkbox.setToolTip("Save all individual ensemble outputs")
        
        # Append ensemble name checkbox
        self.append_ensemble_name_checkbox = QCheckBox(ac.APPEND_ENSEMBLE_NAME_TEXT)
        self.append_ensemble_name_checkbox.setChecked(False)  # Default to False
        self.append_ensemble_name_checkbox.setToolTip("Add ensemble name to output filename")
        
        # Use waveform checkbox
        self.use_waveform_checkbox = QCheckBox(ac.WAVEFORM_ENSEMBLE_TEXT)
        self.use_waveform_checkbox.setChecked(False)  # Default to False
        self.use_waveform_checkbox.setToolTip("Use waveform ensemble instead of spectrogram")
        
        options_row.addWidget(self.save_all_outputs_checkbox)
        options_row.addWidget(self.append_ensemble_name_checkbox)
        options_row.addWidget(self.use_waveform_checkbox)
        options_row.addStretch()
        
        ensemble_layout.addLayout(options_row)

        # Row 3: Current Selection and Advanced Button
        status_row = QHBoxLayout()
        
        # Current selection status
        self.selection_status_label = QLabel("No models selected")
        self.selection_status_label.setStyleSheet("color: #666666; font-style: italic;")
        
        # Advanced settings button
        self.advanced_button = QPushButton("Advanced Configuration...")
        self.advanced_button.setMinimumWidth(180)
        self.advanced_button.setToolTip("Open advanced ensemble settings dialog")
        
        status_row.addWidget(self.selection_status_label, 1)
        status_row.addWidget(self.advanced_button)
        
        ensemble_layout.addLayout(status_row)

        layout.addWidget(ensemble_group)

    def _setup_connections(self):
        """Set up signal connections."""
        self.stem_pair_combo.currentTextChanged.connect(self.main_stem_pair_changed)
        self.algorithm_combo.currentTextChanged.connect(self.ensemble_algorithm_changed)
        self.advanced_button.clicked.connect(self.advanced_settings_requested)
        
        # Checkbox connections
        self.save_all_outputs_checkbox.toggled.connect(self.save_all_outputs_changed)
        self.append_ensemble_name_checkbox.toggled.connect(self.append_ensemble_name_changed)
        self.use_waveform_checkbox.toggled.connect(self.use_waveform_changed)

    def set_current_stem_pair(self, stem_pair: str):
        """Set the current stem pair selection."""
        if stem_pair in [self.stem_pair_combo.itemText(i) for i in range(self.stem_pair_combo.count())]:
            self.stem_pair_combo.setCurrentText(stem_pair)

    def set_current_algorithm(self, algorithm: str):
        """Set the current algorithm selection."""
        if algorithm in [self.algorithm_combo.itemText(i) for i in range(self.algorithm_combo.count())]:
            self.algorithm_combo.setCurrentText(algorithm)

    def update_algorithm_options(self, algorithms: List[str]):
        """Update available algorithm options."""
        current_algorithm = self.algorithm_combo.currentText()
        self.algorithm_combo.clear()
        self.algorithm_combo.addItems(algorithms)
        
        # Restore selection if possible
        if current_algorithm in algorithms:
            self.algorithm_combo.setCurrentText(current_algorithm)

    def update_selection_status(self, selected_models: List[str]):
        """Update the selection status label."""
        count = len(selected_models)
        if count == 0:
            self.selection_status_label.setText("No models selected")
            self.selection_status_label.setStyleSheet("color: #cc6666; font-style: italic;")
        elif count == 1:
            self.selection_status_label.setText(f"1 model selected: {selected_models[0][:30]}...")
            self.selection_status_label.setStyleSheet("color: #66cc66; font-style: normal;")
        else:
            self.selection_status_label.setText(f"{count} models selected for ensemble")
            self.selection_status_label.setStyleSheet("color: #66cc66; font-style: normal;")

    def get_current_stem_pair(self) -> str:
        """Get current stem pair selection."""
        return self.stem_pair_combo.currentText()

    def get_current_algorithm(self) -> str:
        """Get current algorithm selection."""
        return self.algorithm_combo.currentText()

    def get_save_all_outputs(self) -> bool:
        """Get save all outputs checkbox state."""
        return self.save_all_outputs_checkbox.isChecked()

    def set_save_all_outputs(self, value: bool):
        """Set save all outputs checkbox state."""
        self.save_all_outputs_checkbox.setChecked(value)

    def get_append_ensemble_name(self) -> bool:
        """Get append ensemble name checkbox state."""
        return self.append_ensemble_name_checkbox.isChecked()

    def set_append_ensemble_name(self, value: bool):
        """Set append ensemble name checkbox state."""
        self.append_ensemble_name_checkbox.setChecked(value)

    def get_use_waveform(self) -> bool:
        """Get use waveform checkbox state."""
        return self.use_waveform_checkbox.isChecked()

    def set_use_waveform(self, value: bool):
        """Set use waveform checkbox state."""
        self.use_waveform_checkbox.setChecked(value) 