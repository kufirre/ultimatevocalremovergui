from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QComboBox,
    QLabel, QHBoxLayout, QCheckBox, QStackedWidget  # Added QStackedWidget
)
from PySide6.QtCore import Signal, Slot
from typing import List, Dict


class ModelSelectionView(QWidget):
    """
    View for selecting the main processing method, the specific model,
    and displaying the relevant settings panel.
    """
    process_method_changed = Signal(str)
    model_changed = Signal(str)
    ensemble_mode_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        model_group = QGroupBox("Model & Method Selection")
        model_layout = QVBoxLayout(model_group)

        # --- Process Method ---
        method_layout = QHBoxLayout()
        method_label = QLabel("Process Method:")
        self.method_combo = QComboBox()
        self.method_combo.currentTextChanged.connect(self.process_method_changed)
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo, 1)
        model_layout.addLayout(method_layout)

        # --- Model Selection ---
        model_select_layout = QHBoxLayout()
        model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self.model_changed)
        model_select_layout.addWidget(model_label)
        model_select_layout.addWidget(self.model_combo, 1)
        model_layout.addLayout(model_select_layout)

        # --- Ensemble Mode ---
        self.ensemble_checkbox = QCheckBox("Ensemble Mode")
        self.ensemble_checkbox.toggled.connect(self.ensemble_mode_changed)
        model_layout.addWidget(self.ensemble_checkbox)

        # --- Settings Panel Stack (NEW) ---
        self.settings_stack = QStackedWidget()
        model_layout.addWidget(self.settings_stack)

        # Keep track of widgets added
        self.widget_map: Dict[str, QWidget] = {}

        layout.addWidget(model_group)
        self.setLayout(layout)
        print("ModelSelectionView Initialized.")

    def add_settings_panel(self, name: str, widget: QWidget):
        """Adds a settings panel QWidget to the stack."""
        if name not in self.widget_map:
            index = self.settings_stack.addWidget(widget)
            self.widget_map[name] = widget
            print(f"Added '{name}' panel at index {index}")
        else:
            print(f"Warning: Panel '{name}' already exists.")

    @Slot(str)
    def show_settings_panel(self, name: str):
        """Shows the settings panel with the given name."""
        widget_to_show = self.widget_map.get(name)
        if widget_to_show:
            self.settings_stack.setCurrentWidget(widget_to_show)
            print(f"Showing panel: '{name}'")
        else:
            # Maybe show a default/empty panel or hide the stack?
            # For now, just print a warning.
            print(f"Warning: Panel '{name}' not found. Cannot show.")
            # Optionally show a placeholder or the first panel
            if self.settings_stack.count() > 0:
                self.settings_stack.setCurrentIndex(0)

    # ... (Keep existing Slot methods: set_process_methods, set_models, etc.) ...
    @Slot(list)
    def set_process_methods(self, methods: List[str]):
        """Populates the Process Method combobox."""
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        self.method_combo.addItems(methods)
        self.method_combo.blockSignals(False)

    @Slot(list)
    def set_models(self, models: List[str]):
        """Populates the Model combobox."""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.blockSignals(False)
        self.model_combo.setEnabled(bool(models))

    @Slot(str)
    def set_current_method(self, method: str):
        """Sets the current process method."""
        self.method_combo.blockSignals(True)
        self.method_combo.setCurrentText(method)
        self.method_combo.blockSignals(False)

    @Slot(str)
    def set_current_model(self, model: str):
        """Sets the current model."""
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentText(model)
        self.model_combo.blockSignals(False)

    @Slot(bool)
    def set_ensemble_checked(self, is_checked: bool):
        """Sets the ensemble mode checkbox state."""
        self.ensemble_checkbox.blockSignals(True)
        self.ensemble_checkbox.setChecked(is_checked)
        self.ensemble_checkbox.blockSignals(False)
