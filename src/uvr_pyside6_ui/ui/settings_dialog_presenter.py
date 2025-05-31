"""Presenter for the settings and download center dialogs."""

from pathlib import Path
import json
from PySide6.QtCore import QObject, Slot, QStandardPaths
from PySide6.QtWidgets import QWidget, QMessageBox
from .settings_dialog_view import SettingsDialogView
from ..core.uvr_core_adapter import UVRCoreAdapter
from ..core import app_constants as ac


class SettingsDialogPresenter(QObject):
    """Handle user preferences and model downloads."""

    def __init__(self, adapter: UVRCoreAdapter, parent_qt_object: QObject = None):
        super().__init__(parent_qt_object)
        self.view: SettingsDialogView | None = None
        self.adapter = adapter
        self._full_online_catalog: dict = {}
        self._settings_file_path = self._get_settings_file_path()
        self._current_settings = self._load_settings_from_store()
        self._is_download_in_progress = False

    def _get_settings_file_path(self) -> Path:
        """Determines the path for the settings JSON file."""
        # Using QStandardPaths for platform-agnostic config location
        config_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / ac.APP_SETTINGS_FILENAME

    def _load_settings_from_store(self) -> dict:
        default_settings = {
            "check_updates": True, "theme": "Default",
            "default_output": str(Path.home() / "Music" / "UVR_Output"),
            "models_dir": str(Path.home() / "Documents" / "UVR_Models"), # Default models dir
        }
        if self._settings_file_path.exists():
            try:
                with open(self._settings_file_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys are present
                    default_settings.update(loaded_settings)
                    return default_settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings from {self._settings_file_path}: {e}. Using defaults.")
                return default_settings
        return default_settings

    @Slot(dict)
    def _save_settings_to_store(self, settings_data: dict):
        self._current_settings.update(settings_data)
        try:
            with open(self._settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._current_settings, f, indent=4)
            if self.view: # Update status if view is available
                 self.view.show_status_message("Settings saved.", 2000)
        except IOError as e:
            print(f"Error saving settings to {self._settings_file_path}: {e}")
            if self.view:
                QMessageBox.warning(self.view, "Save Error", f"Could not save settings: {e}")


    def _populate_download_center_on_show(self, default_model_type: str | None = None):
        if not self.view: return

        if not isinstance(self.adapter, UVRCoreAdapter):  # Should not happen with proper init
            # Debug print removed
            self.view.set_downloadable_models_list(["Error: Adapter unavailable."]) # Keep this user-facing error
            return

        if not self._full_online_catalog:
            self._full_online_catalog = self.adapter.get_online_catalog()

        if self._full_online_catalog:
            ui_model_types = [ac.VR_ARCH_MODELS_KEY, ac.MDX_NET_MODELS_KEY, ac.DEMUCS_MODELS_KEY]
            self.view.set_download_center_model_types(ui_model_types)

            if ui_model_types and self.view.dc_model_type_combo.count() > 0:
                # Set default model type if provided and valid
                if default_model_type and default_model_type in ui_model_types:
                    self.view.dc_model_type_combo.setCurrentText(default_model_type)
                    # Manually call because setCurrentText might not emit if value is already set
                    self._on_dc_model_type_changed(default_model_type)
                else:  # Default to first in list if no valid default_model_type
                    self.view.dc_model_type_combo.setCurrentIndex(0)
                    self._on_dc_model_type_changed(self.view.dc_model_type_combo.currentText())
            else:
                self.view.set_downloadable_models_list(["No model types available."])
        else:
            self.view.set_download_center_model_types([])
            self.view.set_downloadable_models_list(["Error: Could not load any download catalog."])

    @Slot(str)
    def _on_dc_model_type_changed(self, model_type_name: str) -> None:
        """Populate the downloadable models list when the type changes."""
        if not self.view or not self._full_online_catalog or not model_type_name:
            self.view.set_downloadable_models_list([])
            return
        downloadable_models_dict = self.adapter.get_downloadable_models_for_type(model_type_name)
        user_friendly_names_to_download = list(downloadable_models_dict.keys())
        if not user_friendly_names_to_download:
            self.view.set_downloadable_models_list([
                f"No new models to download for {model_type_name}."
            ])
        else:
            self.view.set_downloadable_models_list(user_friendly_names_to_download)

    @Slot()
    def _on_dc_download_button_clicked(self) -> None:
        """Start downloading the selected model."""
        if not self.view or not self._full_online_catalog or self._is_download_in_progress:
            return

        selected_ui_type = self.view.dc_model_type_combo.currentText()
        selected_list_items = self.view.dc_downloadable_models_list.selectedItems()

        if not selected_ui_type or not selected_list_items:
            # ... (message handling as before) ...
            message = "Status: Please select a model type and a model from the list to download."
            # Debug print removed
            self.view.dc_status_label.setText(message)
            return

        user_friendly_model_name = selected_list_items[0].text()
        target_model_info = None
        online_catalog_source_keys = ac.ONLINE_CATALOG_MAP.get(selected_ui_type, [])
        for source_key in online_catalog_source_keys:
            models_in_online_category = self._full_online_catalog.get(source_key, {})
            if user_friendly_model_name in models_in_online_category:
                target_model_info = models_in_online_category[user_friendly_model_name]
                break

        if target_model_info:
            self._is_download_in_progress = True
            self.view.set_download_in_progress_state(True)  # Disable controls in view
            self.view.dc_status_label.setText(f"Status: Starting download for {user_friendly_model_name}...")
            self.adapter.download_model_mock(selected_ui_type, user_friendly_model_name, target_model_info)
        else:
            # ... (message handling as before) ...
            message = f"Status: Error: Could not find download target info for '{user_friendly_model_name}' in catalog."
            # Debug print removed
            self.view.dc_status_label.setText(message)

    @Slot()
    def show_dialog(self, exec_dialog: bool = True, default_model_type: str | None = None) -> None:
        """Display the settings dialog, optionally modal."""
        if not self.view:
            parent_widget = self.parent() if isinstance(self.parent(), QWidget) else None
            self.view = SettingsDialogView(parent=parent_widget)
            self.view.settings_saved.connect(self._save_settings_to_store)
            self.view.dc_model_type_combo.currentTextChanged.connect(self._on_dc_model_type_changed)
            self.view.dc_download_button.clicked.connect(self._on_dc_download_button_clicked)
            self.adapter.download_progress.connect(self._on_adapter_download_progress)
            self.adapter.download_finished.connect(self._on_adapter_download_finished)

        settings_to_load = self._load_settings_from_store()
        self.view.load_settings(settings_to_load)

        # Pass default_model_type to setup function
        self._populate_download_center_on_show(default_model_type=default_model_type)

        if exec_dialog:
            # Debug print removed
            result = self.view.exec()
            # Debug print removed
            # Debug print removed
        else:
            # Debug print removed
            if not self.view.isVisible():
                self.view.show()
            self.view.activateWindow()
            self.view.raise_()

    @Slot(str, int)
    def _on_adapter_download_progress(self, model_name: str, percentage: int):
        if self.view and self.view.isVisible() and self.view.tab_widget.currentIndex() == 2:
            self.view.dc_status_label.setText(f"Downloading {model_name}: {percentage}%")

    @Slot(str, str, bool, str)  # model_type_ui_name, model_display_name, success, message
    def _on_adapter_download_finished(self, model_type_ui_name: str, model_display_name: str, success: bool,
                                      message: str):
        self._is_download_in_progress = False  # Reset flag
        if self.view and self.view.isVisible():  # Check if view still exists
            self.view.set_download_in_progress_state(False)  # Re-enable controls in view
            if self.view.tab_widget.currentIndex() == 2:  # If Download Center is active tab
                self.view.dc_status_label.setText(message)
                if success:
                    # Debug print removed
                    self._on_dc_model_type_changed(model_type_ui_name)  # Use the type from the signal
