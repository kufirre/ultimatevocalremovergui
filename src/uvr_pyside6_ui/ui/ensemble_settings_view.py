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
        settings_v_layout = QVBoxLayout(settings_group) # Main vertical layout for the group

        # --- Top Config: Stem Pair and Algorithm (using QHBoxLayout as per current file state) ---
        stem_pair_layout = QHBoxLayout()
        stem_pair_label = QLabel("Main Stem Pair:")
        self.stem_pair_combo = QComboBox()
        self.stem_pair_combo.addItems(ac.ENSEMBLE_MAIN_STEM_OPTIONS)
        self.stem_pair_combo.currentTextChanged.connect(self.main_stem_pair_changed)
        stem_pair_layout.addWidget(stem_pair_label)
        stem_pair_layout.addWidget(self.stem_pair_combo, 1)
        settings_v_layout.addLayout(stem_pair_layout)

        algo_layout = QHBoxLayout()
        algo_label = QLabel("Ensemble Algorithm:")
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.currentTextChanged.connect(self.ensemble_algorithm_changed)
        algo_layout.addWidget(algo_label)
        algo_layout.addWidget(self.algorithm_combo, 1)
        settings_v_layout.addLayout(algo_layout)

        # --- Model Selection Area (Available, Transfer, Selected) ---
        model_selection_h_layout = QHBoxLayout()

        # Available Models
        available_models_group = QGroupBox("Available Models (Local Library)")
        available_models_group_layout = QVBoxLayout(available_models_group)
        self.available_models_list = QListWidget()
        self.available_models_list.setSelectionMode(QListWidget.ExtendedSelection) # Changed from MultiSelection
        available_models_group_layout.addWidget(self.available_models_list)
        model_selection_h_layout.addWidget(available_models_group, 2) # Stretch factor

        # Transfer Buttons
        transfer_buttons_layout = QVBoxLayout()
        transfer_buttons_layout.addStretch()
        self.add_to_ensemble_button = QPushButton(">")
        self.add_to_ensemble_button.setToolTip("Add selected to ensemble list")
        self.remove_from_ensemble_button = QPushButton("<")
        self.remove_from_ensemble_button.setToolTip("Remove selected from ensemble list")
        transfer_buttons_layout.addWidget(self.add_to_ensemble_button)
        transfer_buttons_layout.addWidget(self.remove_from_ensemble_button)
        transfer_buttons_layout.addStretch()
        model_selection_h_layout.addLayout(transfer_buttons_layout)

        # Selected Models for Ensemble
        selected_models_group = QGroupBox("Models for Ensemble")
        selected_models_group_layout = QVBoxLayout(selected_models_group)
        self.selected_models_list = QListWidget() # New list widget
        self.selected_models_list.setSelectionMode(QListWidget.ExtendedSelection)
        selected_models_group_layout.addWidget(self.selected_models_list)
        model_selection_h_layout.addWidget(selected_models_group, 2) # Stretch factor
        
        settings_v_layout.addLayout(model_selection_h_layout, 1) # Give this area vertical stretch

        # --- Ensemble Management Actions (using QHBoxLayout) ---
        # This part remains similar, just added to settings_v_layout
        ensemble_actions_layout = QHBoxLayout()
        self.ensemble_actions_combo = QComboBox()
        self.ensemble_actions_combo.addItem("--- Ensemble Actions ---")
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_LOAD)
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_SAVE_AS)
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_CLEAR_SELECTION)
        self.ensemble_actions_combo.activated[int].connect(self._handle_ensemble_action_by_index)
        ensemble_actions_layout.addWidget(self.ensemble_actions_combo, 1) # Combobox takes available space
        settings_v_layout.addLayout(ensemble_actions_layout)

        layout.addWidget(settings_group)
        self.setLayout(layout)

        # Connect new button signals
        self.add_to_ensemble_button.clicked.connect(self._on_add_to_ensemble)
        self.remove_from_ensemble_button.clicked.connect(self._on_remove_from_ensemble)
        # When items in selected_models_list change (e.g. due to add/remove/clear), notify presenter
        self.selected_models_list.model().rowsInserted.connect(self._emit_ensemble_model_list_changed)
        self.selected_models_list.model().rowsRemoved.connect(self._emit_ensemble_model_list_changed)
        
        print("EnsembleSettingsView Redesigned with two-panel layout.")

    # Method _notify_selected_models is no longer needed as selection changes are handled by _emit_ensemble_model_list_changed
    # def _notify_selected_models(self) -> None:
    #     """Emit a list of currently selected model names."""
    #     selected_items = [item.text() for item in self.available_models_list.selectedItems()]
    #     self.selected_models_changed.emit(selected_items)

    def _emit_ensemble_model_list_changed(self):
        """Helper to emit the current list of models in the ensemble."""
        current_ensemble_models = [self.selected_models_list.item(i).text() for i in range(self.selected_models_list.count())]
        self.selected_models_changed.emit(current_ensemble_models)

    @Slot()
    def _on_add_to_ensemble(self):
        selected_items = self.available_models_list.selectedItems()
        for item in selected_items:
            # Avoid duplicates in the selected_models_list
            if not self.selected_models_list.findItems(item.text(), Qt.MatchExactly):
                self.selected_models_list.addItem(item.text())
        
        # Safer way to remove from available_models_list after adding to selected_models_list
        # This avoids issues if an item is somehow in available_models_list multiple times or if selection changes
        for item_text in [item.text() for item in selected_items]: # Get texts before modifying list
            items_to_remove_from_available = self.available_models_list.findItems(item_text, Qt.MatchExactly)
            for item_to_remove in items_to_remove_from_available:
                 self.available_models_list.takeItem(self.available_models_list.row(item_to_remove))
        
        self.selected_models_list.sortItems() # Sort the destination list
        self._emit_ensemble_model_list_changed()

    @Slot()
    def _on_remove_from_ensemble(self):
        selected_items_to_remove = self.selected_models_list.selectedItems()
        for item in selected_items_to_remove:
            # Add back to available_models_list if not already there (maintains uniqueness)
            if not self.available_models_list.findItems(item.text(), Qt.MatchExactly):
                self.available_models_list.addItem(item.text())
            self.selected_models_list.takeItem(self.selected_models_list.row(item))
        
        self.available_models_list.sortItems() # Sort the source list after adding items back
        self._emit_ensemble_model_list_changed()
        
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
