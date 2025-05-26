from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QDialogButtonBox,
    QLabel, QComboBox
)
from PySide6.QtCore import Signal, Slot


class SettingsDialogView(QDialog):
    """
    Dialog window for application-wide settings/preferences.
    """
    settings_saved = Signal(dict)  # Emits all settings when OK is clicked

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Preferences")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)

        # --- Tab Widget ---
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- General Tab ---
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        self.check_updates_checkbox = QCheckBox("Check for updates on startup")
        self.theme_combo = QComboBox()  # Now QComboBox is known!
        self.theme_combo.addItems(["Default", "Dark", "Light"])
        general_layout.addRow(self.check_updates_checkbox)
        general_layout.addRow(QLabel("Theme:"), self.theme_combo)
        self.tab_widget.addTab(general_tab, "General")

        # --- Paths Tab ---
        paths_tab = QWidget()
        paths_layout = QFormLayout(paths_tab)
        self.default_output_edit = QLineEdit()
        self.models_dir_edit = QLineEdit()
        paths_layout.addRow(QLabel("Default Output Folder:"), self.default_output_edit)
        paths_layout.addRow(QLabel("Models Directory:"), self.models_dir_edit)
        self.tab_widget.addTab(paths_tab, "Paths")

        # --- Backend Tab ---
        backend_tab = QWidget()
        backend_layout = QFormLayout(backend_tab)
        self.some_backend_setting = QCheckBox("Use Experimental Backend Feature")
        backend_layout.addRow(self.some_backend_setting)
        self.tab_widget.addTab(backend_tab, "Backend")

        # --- OK / Cancel Buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)
        print("SettingsDialogView Initialized.")

    def get_settings(self) -> dict:
        """Retrieves all settings from the UI fields."""
        return {
            "check_updates": self.check_updates_checkbox.isChecked(),
            "theme": self.theme_combo.currentText(),
            "default_output": self.default_output_edit.text(),
            "models_dir": self.models_dir_edit.text(),
            "experimental_backend": self.some_backend_setting.isChecked(),
        }

    @Slot(dict)
    def load_settings(self, settings_data: dict):
        """Populates the UI fields from a settings dictionary."""
        self.check_updates_checkbox.setChecked(settings_data.get("check_updates", True))
        self.theme_combo.setCurrentText(settings_data.get("theme", "Default"))
        self.default_output_edit.setText(settings_data.get("default_output", ""))
        self.models_dir_edit.setText(settings_data.get("models_dir", ""))
        self.some_backend_setting.setChecked(settings_data.get("experimental_backend", False))
        print("Settings loaded into dialog.")

    def accept(self):
        """Override accept to emit signal before closing."""
        print("OK Clicked - Emitting settings.")
        self.settings_saved.emit(self.get_settings())
        super().accept()

    def reject(self):
        """Handles Cancel button."""
        print("Cancel Clicked.")
        super().reject()
