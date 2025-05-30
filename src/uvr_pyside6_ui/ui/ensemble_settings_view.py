"""View components for configuring ensemble processing in the UI."""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel, QListWidget, QPushButton, QHBoxLayout,
    QComboBox, QListWidgetItem, QGridLayout)
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import QSizePolicy, QScrollArea
from typing import List
from ..core import app_constants as ac  # For options
import natsort


class EnsembleSettingsView(QWidget):
    """Widget for configuring ensemble processing options."""
    main_stem_pair_changed = Signal(str)
    ensemble_algorithm_changed = Signal(str)
    selected_models_changed = Signal(list)  # List of selected model display names
    # This will emit the action string after getting it from index
    ensemble_action_requested = Signal(str) # Covers Load, Save As, Clear

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        # Create the main group
        settings_group = QGroupBox("Ensemble Configuration")
        # Don't force a large minimum, let scroll handle overflow
        settings_group.setSizePolicy(settings_group.sizePolicy().horizontalPolicy(), QSizePolicy.Expanding)

        # Main content layout inside group
        settings_grid = QGridLayout()
        settings_grid.setContentsMargins(8, 8, 8, 8)
        settings_grid.setSpacing(6)

        # --- Algorithm/Selector Row ---
        stem_pair_label = QLabel("Main Stem Pair:")
        self.stem_pair_combo = QComboBox()
        self.stem_pair_combo.addItems(ac.ENSEMBLE_MAIN_STEM_OPTIONS)
        self.stem_pair_combo.currentTextChanged.connect(self.main_stem_pair_changed)

        algo_label = QLabel("Ensemble Algorithm:")
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.currentTextChanged.connect(self.ensemble_algorithm_changed)

        settings_grid.addWidget(stem_pair_label, 0, 0)
        settings_grid.addWidget(self.stem_pair_combo, 0, 1)
        settings_grid.addWidget(algo_label, 0, 2)
        settings_grid.addWidget(self.algorithm_combo, 0, 3)

        # --- Model Selection Section ---
        available_models_group = QGroupBox("Available Models (Local Library)")
        available_models_layout = QVBoxLayout(available_models_group)
        self.available_models_list = QListWidget()
        self.available_models_list.setSelectionMode(QListWidget.ExtendedSelection)
        # Remove minimum height, let scroll area manage height
        self.available_models_list.setSizePolicy(self.available_models_list.sizePolicy().horizontalPolicy(), QSizePolicy.Expanding)
        available_models_layout.addWidget(self.available_models_list)

        transfer_buttons_widget = QWidget()
        transfer_buttons_layout = QVBoxLayout(transfer_buttons_widget)
        transfer_buttons_layout.addStretch()
        self.add_to_ensemble_button = QPushButton(">")
        self.add_to_ensemble_button.setToolTip("Add selected to ensemble list")
        self.remove_from_ensemble_button = QPushButton("<")
        self.remove_from_ensemble_button.setToolTip("Remove selected from ensemble list")
        self.add_to_ensemble_button.setMaximumWidth(36)
        self.remove_from_ensemble_button.setMaximumWidth(36)
        transfer_buttons_layout.addWidget(self.add_to_ensemble_button)
        transfer_buttons_layout.addWidget(self.remove_from_ensemble_button)
        transfer_buttons_layout.addStretch()

        selected_models_group = QGroupBox("Models for Ensemble")
        selected_models_layout = QVBoxLayout(selected_models_group)
        self.selected_models_list = QListWidget()
        self.selected_models_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.selected_models_list.setSizePolicy(self.selected_models_list.sizePolicy().horizontalPolicy(), QSizePolicy.Expanding)
        selected_models_layout.addWidget(self.selected_models_list)

        # Set relative sizing using stretch on grid columns/rows
        settings_grid.addWidget(available_models_group, 1, 0, 1, 2)
        settings_grid.addWidget(transfer_buttons_widget, 1, 2)
        settings_grid.addWidget(selected_models_group, 1, 3, 1, 1)
        settings_grid.setColumnStretch(0, 2)
        settings_grid.setColumnStretch(1, 2)
        settings_grid.setColumnStretch(2, 0)
        settings_grid.setColumnStretch(3, 2)
        settings_grid.setRowStretch(1, 1)

        # Place the grid into a widget (for scroll area compatibility)
        grid_widget = QWidget()
        grid_widget.setLayout(settings_grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_widget)

        # Place scroll area inside group
        group_layout = QVBoxLayout(settings_group)
        group_layout.addWidget(scroll)

        # --- Ensemble Management Actions ---
        ensemble_actions_layout = QHBoxLayout()
        self.ensemble_actions_combo = QComboBox()
        self.ensemble_actions_combo.addItem("--- Ensemble Actions ---")
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_LOAD)
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_SAVE_AS)
        self.ensemble_actions_combo.addItem(ac.ENSEMBLE_ACTION_CLEAR_SELECTION)
        self.ensemble_actions_combo.activated[int].connect(self._handle_ensemble_action_by_index)
        ensemble_actions_layout.addWidget(self.ensemble_actions_combo, 1)
        settings_grid.addLayout(ensemble_actions_layout, 2, 0, 1, 4)

        layout.addWidget(settings_group)
        self.setLayout(layout)
        
        # --- Connect Signals ---
        # Double-click available model to add to ensemble
        self.available_models_list.itemDoubleClicked.connect(self._on_add_to_ensemble_double_click)
        # Transfer buttons
        self.add_to_ensemble_button.clicked.connect(self._on_add_to_ensemble)
        self.remove_from_ensemble_button.clicked.connect(self._on_remove_from_ensemble)
        # When items in selected_models_list change (e.g. due to add/remove/clear), notify presenter
        self.selected_models_list.model().rowsInserted.connect(self._emit_ensemble_model_list_changed)
        self.selected_models_list.model().rowsRemoved.connect(self._emit_ensemble_model_list_changed)
        
        print("EnsembleSettingsView Initialized with two-panel layout.")

    def _on_add_to_ensemble_double_click(self, item: QListWidgetItem):
        """Handles double-clicking an item in the available_models_list."""
        item_text = item.text()
        
        # Add to selected_models_list if not already there
        if not self.selected_models_list.findItems(item_text, Qt.MatchExactly):
            self.selected_models_list.addItem(item_text)
            self.selected_models_list.sortItems()

        # Remove from available_models_list
        row = self.available_models_list.row(item)
        self.available_models_list.takeItem(row)
        
        self._emit_ensemble_model_list_changed()

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
        selected_item_texts = [item.text() for item in self.selected_models_list.selectedItems()]
        
        for item_text in selected_item_texts:
            # Add back to available_models_list if not already there
            if not self.available_models_list.findItems(item_text, Qt.MatchExactly):
                self.available_models_list.addItem(item_text)
            
            # Remove from selected_models_list
            items_in_selected = self.selected_models_list.findItems(item_text, Qt.MatchExactly)
            if items_in_selected: # Should always find at least one
                self.selected_models_list.takeItem(self.selected_models_list.row(items_in_selected[0]))
        
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
