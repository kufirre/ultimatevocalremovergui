from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox,
    QLabel, QHBoxLayout, QCheckBox, QStackedWidget
)
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from typing import List, Dict

from ..core import app_constants as ac


class ModelSelectionView(QWidget):
    # ... (signals as before) ...
    process_method_changed = Signal(str)
    model_selected_by_user = Signal(str)
    ensemble_mode_changed = Signal(bool)  # Though Ensemble mode itself is a Process Method now

    # ... (__init__ mostly as before, just connection for model_combo) ...
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
        self.method_combo.currentTextChanged.connect(self.process_method_changed)
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

        # Ensemble Mode checkbox might be redundant if "Ensemble" is a process method
        # UVR.py has it, seems to affect how ensemble sub-stems are chosen. Keep for now.
        self.ensemble_checkbox = QCheckBox("Advanced Ensemble Options (e.g., per-stem)")
        self.ensemble_checkbox.toggled.connect(self.ensemble_mode_changed)
        model_layout.addWidget(self.ensemble_checkbox)

        self.settings_stack = QStackedWidget()
        model_layout.addWidget(self.settings_stack)
        self.widget_map: Dict[str, QWidget] = {}
        layout.addWidget(model_group)
        self.setLayout(layout)
        print("ModelSelectionView Initialized.")

    # ... (_handle_model_combo_activated_by_user, set_process_methods as before) ...
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
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        first_method_text = ""
        if methods:
            self.method_combo.addItems(methods)
            if self.method_combo.count() > 0:
                self.method_combo.setCurrentIndex(0)
                first_method_text = self.method_combo.itemText(0)
        self.method_combo.blockSignals(False)
        if first_method_text or not methods:
            # print(f"ModelSelectionView: set_process_methods emitting initial method: {first_method_text}")
            # Let MainWindowView trigger the first full handle_method_change
            pass  # self.process_method_changed.emit(first_method_text)

    @Slot(list)  # This is for individual model lists (VR, MDX, Demucs)
    def set_models(self, models: List[str], current_method: str) -> str:
        self.model_combo.blockSignals(True)
        self.model_combo_model.clear()
        programmatic_selection_text = ""

        if current_method == ac.ENSEMBLE_MODELS_KEY:
            # For Ensemble mode, the model combo is not used for primary model selection.
            # It might show "N/A" or be hidden. For now, let's add a placeholder.
            info_item = QStandardItem(ac.ENSEMBLE_MODEL_INFO_TEXT)
            info_item.setEnabled(False)
            self.model_combo_model.appendRow(info_item)
            self.model_combo.setCurrentIndex(0)
            programmatic_selection_text = ac.ENSEMBLE_MODEL_INFO_TEXT
            self.model_combo.setEnabled(False)  # Disable model choice for Ensemble method
        else:
            has_actual_models = bool(models)
            if has_actual_models:
                for model_name in models:
                    item = QStandardItem(model_name)
                    self.model_combo_model.appendRow(item)

            download_item = QStandardItem(ac.DOWNLOAD_MORE_MODELS_TEXT)
            self.model_combo_model.appendRow(download_item)

            if has_actual_models:
                self.model_combo.setCurrentIndex(0)
                programmatic_selection_text = self.model_combo_model.item(0).text()
            else:
                self.model_combo.setCurrentIndex(0)  # Selects "Download More..."
                programmatic_selection_text = ac.DOWNLOAD_MORE_MODELS_TEXT
            self.model_combo.setEnabled(True)

        self.model_combo.blockSignals(False)
        print(
            f"ModelSelectionView: set_models for '{current_method}', programmatically selected "
            f"'{programmatic_selection_text}'")
        return programmatic_selection_text

    @Slot(str)  # Called by Presenter to set method text during init
    def set_current_method_text(self, method: str):
        # ... (as before) ...
        self.method_combo.blockSignals(True)
        self.method_combo.setCurrentText(method)
        self.method_combo.blockSignals(False)
        print(f"ModelSelectionView: Method text programmatically set to '{method}'")

    @Slot(str)  # Called by Presenter to reset model combo after "Download..."
    def set_current_model_text(self, model_text_to_select: str):
        # ... (as before, but ensure it handles ENSEMBLE_MODEL_INFO_TEXT correctly if needed) ...
        self.model_combo.blockSignals(True)
        idx = -1
        for i in range(self.model_combo_model.rowCount()):
            if self.model_combo_model.item(i).text() == model_text_to_select:
                idx = i
                break

        if idx != -1:
            self.model_combo.setCurrentIndex(idx)
        elif self.model_combo.currentText() == ac.ENSEMBLE_MODEL_INFO_TEXT:  # If ensemble, keep it on info
            pass
        elif self.model_combo_model.rowCount() > 0:
            first_item = self.model_combo_model.item(0)
            if first_item and first_item.text() != ac.DOWNLOAD_MORE_MODELS_TEXT:
                self.model_combo.setCurrentIndex(0)
            elif (self.model_combo_model.rowCount() == 1 and
                  first_item and first_item.text() == ac.DOWNLOAD_MORE_MODELS_TEXT):
                self.model_combo.setCurrentIndex(0)
        current_text_after_set = self.model_combo.currentText()
        print(
            f"ModelSelectionView: set_current_model_text for '{model_text_to_select}', "
            f"combo is now '{current_text_after_set}'")
        self.model_combo.blockSignals(False)

    # ... (add_settings_panel, show_settings_panel, set_ensemble_checked as before) ...
    def add_settings_panel(self, name: str, widget: QWidget):
        if name not in self.widget_map:
            index = self.settings_stack.addWidget(widget)
            self.widget_map[name] = widget
            print(f"ModelSelectionView: Added '{name}' panel at index {index}.")
        else:
            print(f"ModelSelectionView: Warning: Panel '{name}' already exists.")

    @Slot(str)
    def show_settings_panel(self, name: str):
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
    def set_ensemble_checked(self, is_checked: bool):
        self.ensemble_checkbox.blockSignals(True)
        self.ensemble_checkbox.setChecked(is_checked)
        self.ensemble_checkbox.blockSignals(False)