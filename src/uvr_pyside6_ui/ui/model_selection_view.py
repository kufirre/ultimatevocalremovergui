from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox,
    QLabel, QHBoxLayout, QCheckBox, QStackedWidget
)
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from typing import List, Dict

DOWNLOAD_MORE_MODELS_TEXT = "--- Download More Models ---"


class ModelSelectionView(QWidget):
    """
    View for selecting the main processing method, the specific model,
    and displaying the relevant settings panel.
    It handles user interactions and updates its display based on presenter commands.
    """
    process_method_changed = Signal(str)  # Emitted by user changing method_combo
    model_selected_by_user = Signal(str)  # Emitted by user activating model_combo item
    ensemble_mode_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_combo_model = QStandardItemModel(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        model_group = QGroupBox("Model & Method Selection")
        model_layout = QVBoxLayout(model_group)

        method_layout = QHBoxLayout()
        method_label = QLabel("Process Method:")
        self.method_combo = QComboBox()
        self.method_combo.currentTextChanged.connect(self.process_method_changed)  # User changes emit this
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo, 1)
        model_layout.addLayout(method_layout)

        model_select_layout = QHBoxLayout()
        model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        self.model_combo.setModel(self.model_combo_model)
        self.model_combo.activated[int].connect(self._handle_model_combo_activated_by_user)
        model_select_layout.addWidget(model_label)
        model_select_layout.addWidget(self.model_combo, 1)
        model_layout.addLayout(model_select_layout)

        self.ensemble_checkbox = QCheckBox("Ensemble Mode")
        self.ensemble_checkbox.toggled.connect(self.ensemble_mode_changed)
        model_layout.addWidget(self.ensemble_checkbox)

        self.settings_stack = QStackedWidget()
        model_layout.addWidget(self.settings_stack)
        self.widget_map: Dict[str, QWidget] = {}
        layout.addWidget(model_group)
        self.setLayout(layout)
        print("ModelSelectionView Initialized.")

    @Slot(int)
    def _handle_model_combo_activated_by_user(self, index: int):
        if index >= 0 and index < self.model_combo_model.rowCount():
            selected_text = self.model_combo_model.item(index).text()
            print(f"ModelSelectionView: User activated item at index {index}, text: '{selected_text}'")
            self.model_selected_by_user.emit(selected_text)
        else:
            print(f"ModelSelectionView: Invalid index {index} from activated signal.")

    @Slot(list)
    def set_process_methods(self, methods: List[str]):
        """Populates the Process Method combobox."""
        self.method_combo.blockSignals(True)  # Prevent emission during setup
        self.method_combo.clear()
        if methods:
            self.method_combo.addItems(methods)
            if self.method_combo.count() > 0:
                self.method_combo.setCurrentIndex(0)
        self.method_combo.blockSignals(False)
        # The initial actual process_method_changed signal that triggers
        # presenter logic will come from MainWindowView after full setup.
        print(
            f"ModelSelectionView: Process methods set. Current method_combo text: '{self.method_combo.currentText()}'")

    @Slot(list)
    def set_models(self, models: List[str]) -> str:
        # ... (This method remains unchanged from response #29) ...
        self.model_combo.blockSignals(True)
        self.model_combo_model.clear()
        programmatic_selection_text = ""
        has_actual_models = bool(models)
        if has_actual_models:
            for model_name in models:
                item = QStandardItem(model_name)
                self.model_combo_model.appendRow(item)
        download_item = QStandardItem(DOWNLOAD_MORE_MODELS_TEXT)
        self.model_combo_model.appendRow(download_item)
        if has_actual_models:
            self.model_combo.setCurrentIndex(0)
            programmatic_selection_text = self.model_combo_model.item(0).text()
        else:
            self.model_combo.setCurrentIndex(0)
            programmatic_selection_text = DOWNLOAD_MORE_MODELS_TEXT
        self.model_combo.setEnabled(True)
        self.model_combo.blockSignals(False)
        print(f"ModelSelectionView: set_models programmatically selected '{programmatic_selection_text}'")
        return programmatic_selection_text

    @Slot(str)
    def set_current_method_text(self, method: str):  # Programmatic set by presenter
        self.method_combo.blockSignals(True)
        self.method_combo.setCurrentText(method)
        self.method_combo.blockSignals(False)
        print(f"ModelSelectionView: Method text programmatically set to '{method}'")

    @Slot(str)
    def set_current_model_text(self, model_text_to_select: str):  # Programmatic set by presenter
        # ... (This method remains unchanged from response #29) ...
        self.model_combo.blockSignals(True)
        idx = -1
        for i in range(self.model_combo_model.rowCount()):
            if self.model_combo_model.item(i).text() == model_text_to_select:
                idx = i
                break
        if idx != -1:
            self.model_combo.setCurrentIndex(idx)
        elif self.model_combo_model.rowCount() > 0:
            first_item = self.model_combo_model.item(0)
            if first_item and first_item.text() != DOWNLOAD_MORE_MODELS_TEXT:
                self.model_combo.setCurrentIndex(0)
            elif self.model_combo_model.rowCount() == 1 and first_item and first_item.text() == DOWNLOAD_MORE_MODELS_TEXT:
                self.model_combo.setCurrentIndex(0)
        current_text_after_set = self.model_combo.currentText()
        print(
            f"ModelSelectionView: set_current_model_text for '{model_text_to_select}', combo is now '{current_text_after_set}'")
        self.model_combo.blockSignals(False)

    def add_settings_panel(self, name: str, widget: QWidget):  # Unchanged
        if name not in self.widget_map:
            index = self.settings_stack.addWidget(widget)
            self.widget_map[name] = widget
            print(f"ModelSelectionView: Added '{name}' panel at index {index}.")
        else:
            print(f"ModelSelectionView: Warning: Panel '{name}' already exists.")

    @Slot(str)
    def show_settings_panel(self, name: str):  # Unchanged
        print(f"ModelSelectionView: Attempting to show panel '{name}'. Available: {list(self.widget_map.keys())}")
        widget_to_show = self.widget_map.get(name)
        if widget_to_show:
            self.settings_stack.setCurrentWidget(widget_to_show)
            print(f"ModelSelectionView: Showing panel: '{name}'")
        else:
            print(
                f"ModelSelectionView: Panel '{name}' not found for stack. Current stack count: {self.settings_stack.count()}")
            if self.settings_stack.count() > 0:
                self.settings_stack.setCurrentIndex(0)
                current_panel_widget = self.settings_stack.widget(0)
                panel_name = next((k for k, v in self.widget_map.items() if v == current_panel_widget), "Unknown Panel")
                print(f"ModelSelectionView: Defaulted to panel at index 0: {panel_name}")
            else:
                print("ModelSelectionView: Settings stack is empty.")

    @Slot(bool)
    def set_ensemble_checked(self, is_checked: bool):  # Unchanged
        self.ensemble_checkbox.blockSignals(True)
        self.ensemble_checkbox.setChecked(is_checked)
        self.ensemble_checkbox.blockSignals(False)
