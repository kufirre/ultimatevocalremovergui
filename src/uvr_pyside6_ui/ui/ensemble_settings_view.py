from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QListWidget,
    QPushButton, QHBoxLayout, QComboBox, QListWidgetItem
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import List
from ..core import app_constants as ac  # For options
import natsort


class EnsembleSettingsView(QWidget):
    """
    View for configuring Ensemble Mode.
    Allows selecting main stem pair, ensemble algorithm, and multiple models.
    """
    main_stem_pair_changed = Signal(str)
    ensemble_algorithm_changed = Signal(str)
    selected_models_changed = Signal(list)  # List of selected model display names
    save_ensemble_clicked = Signal()
    # Renamed: This will emit the action string after getting it from index
    ensemble_action_requested = Signal(str)
    clear_model_selection_clicked = Signal()

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
        self.available_models_list.itemSelectionChanged.connect(self._emit_selected_models)
        settings_layout.addWidget(self.available_models_list, 1)

        # --- Ensemble Management Buttons/Combo ---
        ensemble_manage_layout = QHBoxLayout()
        self.load_ensemble_combo = QComboBox()
        self.load_ensemble_combo.addItem("--- Ensemble Actions ---")  # Placeholder/Instruction
        self.load_ensemble_combo.addItem("Load Saved Ensemble")
        self.load_ensemble_combo.addItem("Save Current Ensemble As...")
        self.load_ensemble_combo.addItem("Clear Model Selection")
        # CORRECTED SIGNAL CONNECTION:
        self.load_ensemble_combo.activated[int].connect(self._handle_ensemble_action_by_index)

        ensemble_manage_layout.addWidget(self.load_ensemble_combo, 1)
        settings_layout.addLayout(ensemble_manage_layout)

        layout.addWidget(settings_group)
        self.setLayout(layout)
        print("EnsembleSettingsView Redesigned.")

    def _emit_selected_models(self):
        selected_items = [item.text() for item in self.available_models_list.selectedItems()]
        self.selected_models_changed.emit(selected_items)

    # NEW SLOT to handle activated[int] from load_ensemble_combo
    @Slot(int)
    def _handle_ensemble_action_by_index(self, index: int):
        """Handles user activation of an item in the ensemble action combobox."""
        if index >= 0:  # Ensure a valid index is received
            action_text = self.load_ensemble_combo.itemText(index)
            print(f"EnsembleSettingsView: User activated ensemble action: '{action_text}'")
            if action_text != "--- Ensemble Actions ---":  # Don't emit for the placeholder
                self.ensemble_action_requested.emit(action_text)
            # Reset to placeholder after action to allow re-selection of same action
            self.load_ensemble_combo.setCurrentIndex(0)

    # --- Slots to be called by Presenter ---
    @Slot(list)
    def populate_available_models(self, model_names: List[str]):
        self.available_models_list.clear()
        self.available_models_list.addItems(model_names)

    @Slot(list)
    def populate_saved_ensembles_list(self, ensemble_names: List[str]):  # Renamed for clarity
        """Populates the 'Load Saved Ensemble' part of the action combo, or a dedicated combo."""
        # This method might need more complex logic if 'Load Saved Ensemble'
        # is meant to dynamically populate another list/combo.
        # For now, assuming the action combo's items are relatively static beyond the placeholder.
        # If you want a dynamic list of saved ensembles to pick from before clicking "Load",
        # this would need a separate QComboBox for saved_ensembles.
        # For simplicity, we'll assume the presenter handles the "Load" action when user clicks "Load Saved Ensemble"
        # and then perhaps shows another dialog to pick which one.
        # The current self.load_ensemble_combo is an ACTION combo.

        # If you intend for the load_ensemble_combo to *also* list saved ensembles:
        self.load_ensemble_combo.blockSignals(True)
        # Keep placeholder and static actions
        static_actions = [self.load_ensemble_combo.itemText(i) for i in
                          range(self.load_ensemble_combo.count())]  # Keep existing static actions
        self.load_ensemble_combo.clear()
        self.load_ensemble_combo.addItem("--- Ensemble Actions ---")  # Placeholder
        if ensemble_names:
            self.load_ensemble_combo.addItems(natsort.natsorted(ensemble_names))  # Add sorted saved names
            self.load_ensemble_combo.insertSeparator(1 + len(ensemble_names))  # Separator after loaded names

        # Re-add static actions if they were not part of ensemble_names
        for action in static_actions:
            if action not in ensemble_names and action != "--- Ensemble Actions ---" and self.load_ensemble_combo.findText(
                    action) == -1:
                self.load_ensemble_combo.addItem(action)

        self.load_ensemble_combo.setCurrentIndex(0)  # Default to placeholder
        self.load_ensemble_combo.blockSignals(False)
        print(f"EnsembleSettingsView: Saved ensembles list updated in action combo.")

    @Slot(list)
    def set_selected_models_in_list(self, model_names_to_select: List[str]):
        self.available_models_list.clearSelection()
        for i in range(self.available_models_list.count()):
            item = self.available_models_list.item(i)
            if item.text() in model_names_to_select:
                item.setSelected(True)

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
