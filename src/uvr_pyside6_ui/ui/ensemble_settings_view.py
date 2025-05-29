"""View components for configuring ensemble processing in the UI."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QPushButton,
    QHBoxLayout,
    QComboBox,
    QListWidgetItem,
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import List
from ..core import app_constants as ac  # For options
import natsort


class EnsembleSettingsView(QWidget):
    """Widget for configuring ensemble processing options."""
    main_stem_pair_changed = Signal(str)
    ensemble_algorithm_changed = Signal(str)
    selected_models_changed = Signal(list)  # List of selected model display names
    # Renamed: This will emit the action string after getting it from index
    ensemble_action_requested = Signal(str) # Covers Load, Save As, Clear

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        settings_group = QGroupBox("Ensemble Configuration")
        settings_layout = QVBoxLayout(settings_group)

        # --- Main Stem Pair ---
        stem_pair_layout = QHBoxLayout()
        stem_pair_label = QLabel("Main Stem Pair:")
        self.stem_pair_combo = QComboBox()
        self.stem_pair_combo.addItems(ac.ENSEMBLE_MAIN_STEM_OPTIONS)
        self.stem_pair_combo.currentTextChanged.connect(self.main_stem_pair_changed)
        stem_pair_layout.addWidget(stem_pair_label)
        stem_pair_layout.addWidget(self.stem_pair_combo, 1)
        settings_layout.addLayout(stem_pair_layout)

        # --- Ensemble Algorithm ---
        algo_layout = QHBoxLayout()
        algo_label = QLabel("Ensemble Algorithm:")
        self.algorithm_combo = QComboBox()
        # This will be populated by presenter based on stem_pair_combo
        self.algorithm_combo.currentTextChanged.connect(self.ensemble_algorithm_changed)
        algo_layout.addWidget(algo_label)
        algo_layout.addWidget(self.algorithm_combo, 1)
        settings_layout.addLayout(algo_layout)

        # --- Available Models List ---
        avail_models_label = QLabel("Select Models for Ensemble (from local library):")
        settings_layout.addWidget(avail_models_label)
        self.available_models_list = QListWidget()
        self.available_models_list.setSelectionMode(QListWidget.MultiSelection)
        self.available_models_list.itemSelectionChanged.connect(
            self._notify_selected_models
        )
        settings_layout.addWidget(self.available_models_list, 1)

        # --- Ensemble Management Buttons/Combo ---
        ensemble_manage_layout = QHBoxLayout()
        self.ensemble_actions_combo = QComboBox()
        self.ensemble_actions_combo.addItem("--- Ensemble Actions ---")  # Placeholder/Instruction
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_LOAD) # "Load Saved Ensemble..."
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_SAVE_AS) # "Save Current Ensemble As..."
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_CLEAR_SELECTION) # "Clear Model Selection"
        # CORRECTED SIGNAL CONNECTION:
        self.ensemble_actions_combo.activated[int].connect(self._handle_ensemble_action_by_index)

        ensemble_manage_layout.addWidget(self.ensemble_actions_combo, 1)
        settings_layout.addLayout(ensemble_manage_layout)

        layout.addWidget(settings_group)
        self.setLayout(layout)
        print("EnsembleSettingsView Redesigned.")

    def _notify_selected_models(self) -> None:
        """Emit a list of currently selected model names."""
        selected_items = [item.text() for item in self.available_models_list.selectedItems()]
        self.selected_models_changed.emit(selected_items)

    # NEW SLOT to handle activated[int] from load_ensemble_combo
    @Slot(int)
    def _handle_ensemble_action_by_index(self, index: int):
        """Handles user activation of an item in the ensemble action combobox."""
        if index >= 0:
            action_text = self.ensemble_actions_combo.itemText(index)
            if action_text != "--- Ensemble Actions ---":
                # Let presenter handle all actions, including UI updates for "Clear"
                self.ensemble_action_requested.emit(action_text)
            self.ensemble_actions_combo.setCurrentIndex(0)

    # --- Slots to be called by Presenter ---
    @Slot(list)
    def populate_available_models(self, model_names: List[str]):
        """Populates the list of models available for selection."""
        self.available_models_list.clear()
        self.available_models_list.addItems(natsort.natsorted(model_names))
        # self.available_models_list.sortItems() # Use natsort if available and needed

    @Slot(list)
    def set_selected_models_in_list(self, model_names_to_select: List[str]):
        """Populates the list of models currently in the ensemble."""
        self.selected_models_list.clear()
        self.selected_models_list.addItems(natsort.natsorted(model_names_to_select))
        # self.selected_models_list.sortItems() # Use natsort if available and needed
        # This method implicitly changes the ensemble content, so we should notify.
        self._emit_ensemble_model_list_changed()

    @Slot(str)
    def set_current_stem_pair(self, stem_pair: str):
        self.stem_pair_combo.blockSignals(True)
        self.stem_pair_combo.setCurrentText(stem_pair)
        self.stem_pair_combo.blockSignals(False)

    @Slot(list)
    def set_ensemble_algorithms(self, algorithms: List[str]):
        self.algorithm_combo.blockSignals(True)
        self.algorithm_combo.clear()
        self.algorithm_combo.addItems(algorithms)
        if algorithms and self.algorithm_combo.count() > 0:
            self.algorithm_combo.setCurrentIndex(0)
        self.algorithm_combo.blockSignals(False)

    @Slot(str)
    def set_current_algorithm(self, algorithm: str):
        self.algorithm_combo.blockSignals(True)
        self.algorithm_combo.setCurrentText(algorithm)
        self.algorithm_combo.blockSignals(False)
