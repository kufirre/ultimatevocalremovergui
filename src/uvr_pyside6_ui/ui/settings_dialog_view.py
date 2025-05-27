from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QDialogButtonBox,
    QLabel, QComboBox, QListWidget, QHBoxLayout
)
from PySide6.QtCore import Signal, Slot


class SettingsDialogView(QDialog):
    """
    Dialog window for application-wide settings/preferences, including
    a Download Center tab.
    """
    settings_saved = Signal(dict)  # Emitted when user clicks OK

    # Example signal if view needed to emit structured download request:
    # download_model_requested = Signal(str, str) # model_type, user_friendly_model_name

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Preferences")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- General Tab ---
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        self.check_updates_checkbox = QCheckBox("Check for updates on startup")
        self.theme_combo = QComboBox()
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

        # --- Download Center Tab ---
        self.download_center_tab = QWidget()  # Ensure this tab widget is created
        dc_main_layout = QVBoxLayout(self.download_center_tab)

        # Model type selection
        dc_type_layout = QHBoxLayout()
        dc_type_label = QLabel("Model Type:")
        # This is the critical attribute:
        self.dc_model_type_combo = QComboBox()
        dc_type_layout.addWidget(dc_type_label)
        dc_type_layout.addWidget(self.dc_model_type_combo, 1)
        dc_main_layout.addLayout(dc_type_layout)

        # List of downloadable models
        dc_list_label = QLabel("Available for Download:")
        self.dc_downloadable_models_list = QListWidget()
        self.dc_downloadable_models_list.setAlternatingRowColors(True)
        dc_main_layout.addWidget(dc_list_label)
        dc_main_layout.addWidget(self.dc_downloadable_models_list, 1)

        # Download button
        self.dc_download_button = QPushButton("Download Selected Model")
        self.dc_download_button.setEnabled(False)
        dc_main_layout.addWidget(self.dc_download_button)

        # Status/Progress
        self.dc_status_label = QLabel("Status: Idle")
        dc_main_layout.addWidget(self.dc_status_label)

        self.tab_widget.addTab(self.download_center_tab, "Download Center")

        # --- OK / Cancel Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)
        print("SettingsDialogView Initialized with Download Center tab UI.")

        # Connect selection change in list to enable download button
        self.dc_downloadable_models_list.itemSelectionChanged.connect(
            lambda: self.dc_download_button.setEnabled(
                bool(self.dc_downloadable_models_list.selectedItems())
            )
        )

    @Slot(list)
    def set_download_center_model_types(self, types: list[str]):
        """Populates the model type combobox in the Download Center."""
        self.dc_model_type_combo.blockSignals(True)
        self.dc_model_type_combo.clear()
        self.dc_model_type_combo.addItems(types)
        self.dc_model_type_combo.blockSignals(False)
        if types and self.dc_model_type_combo.count() > 0:
            self.dc_model_type_combo.setCurrentIndex(0)
            # The currentTextChanged signal will be connected by the presenter.

    @Slot(list)
    def set_downloadable_models_list(self, model_names: list[str]):
        """Populates the list of downloadable models in the Download Center."""
        self.dc_downloadable_models_list.clear()
        self.dc_downloadable_models_list.addItems(model_names)
        self.dc_download_button.setEnabled(False)

    def get_settings(self) -> dict:  # For General and Paths tabs
        return {
            "check_updates": self.check_updates_checkbox.isChecked(),
            "theme": self.theme_combo.currentText(),
            "default_output": self.default_output_edit.text(),
            "models_dir": self.models_dir_edit.text(),
        }

    @Slot(dict)
    def load_settings(self, settings_data: dict):  # For General and Paths tabs
        self.check_updates_checkbox.setChecked(settings_data.get("check_updates", True))
        self.theme_combo.setCurrentText(settings_data.get("theme", "Default"))
        self.default_output_edit.setText(settings_data.get("default_output", ""))
        self.models_dir_edit.setText(settings_data.get("models_dir", ""))
        print("Settings loaded into dialog.")

    def accept(self):
        print("OK Clicked - Emitting general/path settings.")
        self.settings_saved.emit(self.get_settings())
        super().accept()

    def reject(self):
        print("Cancel Clicked.")
        super().reject()
