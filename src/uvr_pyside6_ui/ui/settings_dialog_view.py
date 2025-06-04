from PySide6.QtCore import QSize, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsDialogView(QDialog):
    settings_saved = Signal(dict)

    # download_model_requested = Signal(str, str) # This was an example, presenter connects to button directly

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)
        self._is_download_in_progress = False  # Internal state flag

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # General Tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        self.check_updates_checkbox = QCheckBox("Check for updates on startup")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Default", "Dark", "Light"])
        general_layout.addRow(self.check_updates_checkbox)
        general_layout.addRow(QLabel("Theme:"), self.theme_combo)
        try:
            general_icon = QIcon(":/uvr/img/key.png")
            self.tab_widget.addTab(general_tab, general_icon, "General")
        except Exception as e:
            print(f"Error loading general_icon for settings tab: {e}")
            self.tab_widget.addTab(general_tab, "General")

        # Paths Tab
        paths_tab = QWidget()
        paths_layout = QFormLayout(paths_tab)
        self.default_output_edit = QLineEdit()
        self.models_dir_edit = QLineEdit()
        paths_layout.addRow(QLabel("Default Output Folder:"), self.default_output_edit)
        paths_layout.addRow(QLabel("Models Directory:"), self.models_dir_edit)
        try:
            paths_icon = QIcon(":/uvr/img/File.png")
            self.tab_widget.addTab(paths_tab, paths_icon, "Paths")
        except Exception as e:
            print(f"Error loading paths_icon for settings tab: {e}")
            self.tab_widget.addTab(paths_tab, "Paths")

        # Download Center Tab
        self.download_center_tab = QWidget()
        dc_main_layout = QVBoxLayout(self.download_center_tab)
        dc_type_layout = QHBoxLayout()
        dc_type_label = QLabel("Model Type:")
        self.dc_model_type_combo = QComboBox()
        dc_type_layout.addWidget(dc_type_label)
        dc_type_layout.addWidget(self.dc_model_type_combo, 1)
        dc_main_layout.addLayout(dc_type_layout)
        dc_list_label = QLabel("Available for Download:")
        self.dc_downloadable_models_list = QListWidget()
        self.dc_downloadable_models_list.setAlternatingRowColors(True)
        dc_main_layout.addWidget(dc_list_label)
        dc_main_layout.addWidget(self.dc_downloadable_models_list, 1)
        self.dc_download_button = QPushButton("Download Selected Model")
        try:
            download_icon = QIcon(":/uvr/img/download.png")
            if not download_icon.isNull():
                self.dc_download_button.setIcon(download_icon)
                self.dc_download_button.setIconSize(QSize(16, 16))  # Adjust as needed
        except Exception as e:
            print(f"Error loading download_icon for button: {e}")
        self.dc_download_button.setEnabled(False)
        dc_main_layout.addWidget(self.dc_download_button)
        # Progress container with label and progress bar
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(2)

        # Status label above progress bar
        self.dc_status_label = QLabel("💤 Ready to download")
        self.dc_status_label.setProperty("progressLabel", True)  # For QSS styling
        progress_layout.addWidget(self.dc_status_label)

        # Progress bar
        self.dc_progress_bar = QProgressBar()
        self.dc_progress_bar.setObjectName(
            "downloadProgressBar"
        )  # Set object name for QSS
        self.dc_progress_bar.setValue(0)
        self.dc_progress_bar.setTextVisible(False)  # Hide text inside progress bar
        self.dc_progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.dc_progress_bar)

        dc_main_layout.addWidget(progress_container)
        try:
            dc_tab_icon = QIcon(":/uvr/img/download.png")
            self.tab_widget.addTab(
                self.download_center_tab, dc_tab_icon, "Download Center"
            )
        except Exception as e:
            print(f"Error loading dc_tab_icon for settings tab: {e}")
            self.tab_widget.addTab(self.download_center_tab, "Download Center")

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.dialog_status_label = QLabel(" ")  # General status label for the dialog
        main_layout.addWidget(self.dialog_status_label)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

        self.dc_downloadable_models_list.itemSelectionChanged.connect(
            self._on_dc_list_selection_changed
        )
        # Initial state for download button
        self._on_dc_list_selection_changed()

    def _on_dc_list_selection_changed(self):
        """Handles selection changes in the downloadable models list."""
        has_selection = bool(self.dc_downloadable_models_list.selectedItems())
        self.dc_download_button.setEnabled(
            has_selection and not self._is_download_in_progress
        )

        # Reset status and progress if selection changes or is cleared, and not downloading
        if not self._is_download_in_progress:
            self.dc_status_label.setText("💤 Ready to download")
            self.dc_progress_bar.setValue(0)

    def set_download_in_progress_state(self, in_progress: bool):
        """Enable/disable controls based on download state."""
        self._is_download_in_progress = in_progress
        self.dc_model_type_combo.setEnabled(not in_progress)
        self.dc_downloadable_models_list.setEnabled(not in_progress)
        # Download button is enabled only if an item is selected AND not in progress
        self.dc_download_button.setEnabled(
            bool(self.dc_downloadable_models_list.selectedItems()) and not in_progress
        )
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(not in_progress)
        self.button_box.button(QDialogButtonBox.Cancel).setEnabled(not in_progress)
        # Disable other tabs too?
        for i in range(self.tab_widget.count()):
            if (
                i != self.tab_widget.currentIndex()
                and self.tab_widget.tabText(i) == "Download Center"
            ):  # only disable other tabs if DC is active
                continue
            self.tab_widget.setTabEnabled(i, not in_progress)

    def closeEvent(self, event: QCloseEvent):
        """Override close event to prevent closing during download."""
        if self._is_download_in_progress:
            QMessageBox.warning(
                self,
                "Download in Progress",
                "A model download is currently in progress. Please wait for it to complete.",
            )
            event.ignore()  # Prevent dialog from closing
        else:
            super().closeEvent(event)  # Allow normal close

    def accept(self):
        if self._is_download_in_progress:
            QMessageBox.warning(
                self,
                "Download in Progress",
                "Cannot save settings while a download is in progress.",
            )
            return
        # Debug print removed
        self.settings_saved.emit(self.get_settings())
        super().accept()

    def reject(self):
        if self._is_download_in_progress:
            QMessageBox.warning(
                self,
                "Download in Progress",
                "Cannot cancel dialog while a download is in progress. Please wait.",
            )
            return
        # Debug print removed
        super().reject()

    # ... (set_download_center_model_types, set_downloadable_models_list, get_settings, load_settings as in response #33) ...
    @Slot(list)
    def set_download_center_model_types(self, types: list[str]):
        self.dc_model_type_combo.blockSignals(True)
        self.dc_model_type_combo.clear()
        self.dc_model_type_combo.addItems(types)
        self.dc_model_type_combo.blockSignals(False)
        if types and self.dc_model_type_combo.count() > 0:
            self.dc_model_type_combo.setCurrentIndex(0)

    @Slot(list)
    def set_downloadable_models_list(self, model_names: list[str]):
        self.dc_downloadable_models_list.clear()
        self.dc_downloadable_models_list.addItems(model_names)
        self.dc_download_button.setEnabled(False)

    def get_settings(self) -> dict:
        return {
            "check_updates": self.check_updates_checkbox.isChecked(),
            "theme": self.theme_combo.currentText(),
            "default_output": self.default_output_edit.text(),
            "models_dir": self.models_dir_edit.text(),
        }

    @Slot(dict)
    def load_settings(self, settings_data: dict):
        self.check_updates_checkbox.setChecked(settings_data.get("check_updates", True))
        self.theme_combo.setCurrentText(settings_data.get("theme", "Default"))
        self.default_output_edit.setText(settings_data.get("default_output", ""))
        self.models_dir_edit.setText(settings_data.get("models_dir", ""))
        # Debug print removed

    def show_status_message(self, message: str, timeout: int = 0):
        """Displays a message on the dialog's status label."""
        self.dialog_status_label.setText(message)
        if timeout > 0:
            # Use QTimer to clear the message after the timeout
            # Note: QStatusBar.showMessage has this built-in, but QLabel doesn't.
            # For simplicity, if a status bar is added later, this can be improved.
            # For now, the message will persist until overwritten or dialog closes if timeout is 0.
            # If a temporary message is needed, the caller should handle clearing it or use dc_status_label for tab-specific messages.
            # Let's make it simple: it just sets the text. Presenter can clear if needed.
            # If timeout is used, we'd need a QTimer here.
            # For now, let's assume the presenter wants a persistent message until next action.
            pass
            # If you want timeout:
            # QTimer.singleShot(timeout, lambda: self.dialog_status_label.setText(" "))
