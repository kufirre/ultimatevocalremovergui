from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox,
    QLabel, QHBoxLayout, QStackedWidget  # QCheckBox removed if it was only for ensemble
)
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from typing import List, Dict
from ..core import app_constants as ac


class ModelSelectionView(QWidget):
    process_method_changed = Signal(str)
    model_selected_by_user = Signal(str)

    # ensemble_mode_changed = Signal(bool) # Removed, as checkbox is removed

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

        # self.ensemble_checkbox was here - REMOVED

        self.settings_stack = QStackedWidget()
        # Removed setMinimumHeight to allow dynamic sizing based on content
        model_layout.addWidget(self.settings_stack)

        self.widget_map: Dict[str, QWidget] = {}

        layout.addWidget(model_group)
        self.setLayout(layout)
        # print("ModelSelectionView Initialized (Ensemble checkbox removed).") # Removed unprofessional comment

    # ... _handle_model_combo_activated_by_user, set_process_methods, set_models,
    # ... set_current_method_text, set_current_model_text,
    # ... add_settings_panel, show_settings_panel
    # ... (These methods remain as in response #35/36, ensure set_ensemble_checked is removed)
    @Slot(int)
    def _handle_model_combo_activated_by_user(self, index: int):
        if index >= 0 and index < self.model_combo_model.rowCount():
            selected_text = self.model_combo_model.item(index).text()
            self.model_selected_by_user.emit(selected_text)

    @Slot(list)
    def set_process_methods(self, methods: List[str]):
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        if methods:
            self.method_combo.addItems(methods)
            if self.method_combo.count() > 0: self.method_combo.setCurrentIndex(0)
        self.method_combo.blockSignals(False)

    @Slot(list)
    def set_models(self, models: List[str], current_method: str) -> str:
        self.model_combo.blockSignals(True)
        self.model_combo_model.clear()
        programmatic_selection_text = ""
        if current_method == ac.ENSEMBLE_MODELS_KEY:
            info_item = QStandardItem(ac.ENSEMBLE_MODEL_INFO_TEXT);
            info_item.setEnabled(False)
            self.model_combo_model.appendRow(info_item)
            self.model_combo.setCurrentIndex(0)
            programmatic_selection_text = ac.ENSEMBLE_MODEL_INFO_TEXT
            self.model_combo.setEnabled(False)
        else:
            has_actual_models = bool(models)
            if has_actual_models:
                for model_name in models: self.model_combo_model.appendRow(QStandardItem(model_name))
            self.model_combo_model.appendRow(QStandardItem(ac.DOWNLOAD_MORE_MODELS_TEXT))
            if has_actual_models:
                self.model_combo.setCurrentIndex(0)
                programmatic_selection_text = self.model_combo_model.item(0).text()
            else:
                self.model_combo.setCurrentIndex(0)
                programmatic_selection_text = ac.DOWNLOAD_MORE_MODELS_TEXT
            self.model_combo.setEnabled(True)
        self.model_combo.blockSignals(False)
        return programmatic_selection_text

    @Slot(str)
    def set_current_method_text(self, method: str):
        self.method_combo.blockSignals(True)
        self.method_combo.setCurrentText(method)
        self.method_combo.blockSignals(False)

    @Slot(str)
    def set_current_model_text(self, model_text_to_select: str):
        self.model_combo.blockSignals(True)
        idx = -1
        for i in range(self.model_combo_model.rowCount()):
            if self.model_combo_model.item(i).text() == model_text_to_select: idx = i; break
        if idx != -1:
            self.model_combo.setCurrentIndex(idx)
        elif self.model_combo.currentText() == ac.ENSEMBLE_MODEL_INFO_TEXT:
            pass
        elif self.model_combo_model.rowCount() > 0:
            first_item = self.model_combo_model.item(0)
            if first_item and first_item.text() != ac.DOWNLOAD_MORE_MODELS_TEXT:
                self.model_combo.setCurrentIndex(0)
            elif self.model_combo_model.rowCount() == 1 and first_item and first_item.text() == ac.DOWNLOAD_MORE_MODELS_TEXT:
                self.model_combo.setCurrentIndex(0)
        self.model_combo.blockSignals(False)

    def add_settings_panel(self, name: str, widget: QWidget):
        if name not in self.widget_map:
            index = self.settings_stack.addWidget(widget)
            self.widget_map[name] = widget

    @Slot(str)
    def show_settings_panel(self, name: str):
        widget_to_show = self.widget_map.get(name)
        if widget_to_show:
            self.settings_stack.setCurrentWidget(widget_to_show)
        elif self.settings_stack.count() > 0:
            self.settings_stack.setCurrentIndex(0)
