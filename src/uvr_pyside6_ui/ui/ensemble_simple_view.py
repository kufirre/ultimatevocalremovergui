"""Simplified Ensemble View for the main window."""

from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
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

        # Row 2: Current Selection and Advanced Button
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

    def set_current_stem_pair(self, stem_pair: str):
        """Set the current stem pair selection."""
        if stem_pair in [
            self.stem_pair_combo.itemText(i)
            for i in range(self.stem_pair_combo.count())
        ]:
            self.stem_pair_combo.setCurrentText(stem_pair)

    def set_current_algorithm(self, algorithm: str):
        """Set the current algorithm selection."""
        if algorithm in [
            self.algorithm_combo.itemText(i)
            for i in range(self.algorithm_combo.count())
        ]:
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
            self.selection_status_label.setStyleSheet(
                "color: #cc6666; font-style: italic;"
            )
        elif count == 1:
            self.selection_status_label.setText(
                f"1 model selected: {selected_models[0][:30]}..."
            )
            self.selection_status_label.setStyleSheet(
                "color: #66cc66; font-style: normal;"
            )
        else:
            self.selection_status_label.setText(f"{count} models selected for ensemble")
            self.selection_status_label.setStyleSheet(
                "color: #66cc66; font-style: normal;"
            )

    def get_current_stem_pair(self) -> str:
        """Get current stem pair selection."""
        return self.stem_pair_combo.currentText()

    def get_current_algorithm(self) -> str:
        """Get current algorithm selection."""
        return self.algorithm_combo.currentText()
