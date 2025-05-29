from pathlib import Path

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QWidget, QMessageBox  # Added QMessageBox
from .settings_dialog_view import SettingsDialogView
from ..core.uvr_core_adapter import UVRCoreAdapter
from ..core import app_constants as ac


class SettingsDialogPresenter(QObject):
    def __init__(self, adapter: UVRCoreAdapter, parent_qt_object: QObject = None):
        super().__init__(parent_qt_object)
        self.view: SettingsDialogView | None = None
        self.adapter = adapter
        self._full_online_catalog: dict = {}
        self._current_settings = {
            "check_updates": True, "theme": "Default",
            "default_output": str(Path.home() / "Music" / "UVR_Output"),
            "models_dir": str(Path.home() / "Documents" / "UVR_Models"),
        }
        self._is_download_in_progress = False  # NEW state variable
        print("SettingsDialogPresenter Initialized.")

    # ... (_load_settings_from_store, _save_settings_to_store as before) ...
    def _load_settings_from_store(self) -> dict:
        print("Presenter: Loading app settings from store (mocked).")
        return self._current_settings.copy()

    @Slot(dict)
    def _save_settings_to_store(self, settings_data: dict):
        print(f"Presenter: Saving app settings to store: {settings_data}")
        self._current_settings.update(settings_data)

    def _populate_download_center_on_show(self, default_model_type: str | None = None):
        if not self.view: return

        if not isinstance(self.adapter, UVRCoreAdapter):  # Should not happen with proper init
            print(f"Presenter (DC): ERROR - self.adapter is not correctly configured!")
            self.view.set_downloadable_models_list(["Error: Adapter unavailable."])
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
    def _on_dc_model_type_changed(self, ui_model_type: str):  # Unchanged from #35
        if not self.view or not self._full_online_catalog or not ui_model_type:
            self.view.set_downloadable_models_list([])
            return
        downloadable_models_dict = self.adapter.get_downloadable_models_for_type(ui_model_type)
        user_friendly_names_to_download = list(downloadable_models_dict.keys())
        if not user_friendly_names_to_download:
            self.view.set_downloadable_models_list([f"No new models to download for {ui_model_type}."])
        else:
            self.view.set_downloadable_models_list(user_friendly_names_to_download)

    @Slot()
    def _on_dc_download_button_clicked(self):
        if not self.view or not self._full_online_catalog or self._is_download_in_progress:
            return

        selected_ui_type = self.view.dc_model_type_combo.currentText()
        selected_list_items = self.view.dc_downloadable_models_list.selectedItems()

        if not selected_ui_type or not selected_list_items:
            # ... (message handling as before) ...
            message = "Status: Please select a model type and a model from the list to download."
            print(f"Presenter (DC): {message}")
            self.view.dc_status_label.setText(message)
            return

        user_friendly_model_name = selected_list_items[0].text()
        download_target_info = None
        online_catalog_source_keys = ac.ONLINE_CATALOG_MAP.get(selected_ui_type, [])
        for source_key in online_catalog_source_keys:
            models_in_online_category = self._full_online_catalog.get(source_key, {})
            if user_friendly_model_name in models_in_online_category:
                download_target_info = models_in_online_category[user_friendly_model_name];
                break

        if download_target_info:
            self._is_download_in_progress = True
            self.view.set_download_in_progress_state(True)  # Disable controls in view
            self.view.dc_status_label.setText(f"Status: Starting download for {user_friendly_model_name}...")
            self.adapter.download_model_mock(selected_ui_type, user_friendly_model_name, download_target_info)
        else:
            # ... (message handling as before) ...
            message = f"Status: Error: Could not find download target info for '{user_friendly_model_name}' in catalog."
            print(f"Presenter (DC): {message}");
            self.view.dc_status_label.setText(message)

    # MODIFIED show_dialog
    @Slot()
    def show_dialog(self, exec_dialog: bool = True, default_model_type: str | None = None):
        if not self.view:
            parent_widget = self.parent() if isinstance(self.parent(), QWidget) else None
            self.view = SettingsDialogView(parent=parent_widget)
            self.view.settings_saved.connect(self._save_settings_to_store)
            self.view.dc_model_type_combo.currentTextChanged.connect(self._on_dc_model_type_changed)
            self.view.dc_download_button.clicked.connect(self._on_dc_download_button_clicked)
            self.adapter.download_progress.connect(self._on_adapter_download_progress)
            self.adapter.download_finished.connect(self._on_adapter_download_finished)

        settings_to_load = self._load_settings_from_store();
        self.view.load_settings(settings_to_load)

        # Pass default_model_type to setup function
        self._populate_download_center_on_show(default_model_type=default_model_type)

        if exec_dialog:
            print("Presenter: Showing Settings Dialog (modal).")
            result = self.view.exec()
            if result == SettingsDialogView.Accepted:
                print("Presenter: Settings Dialog was Accepted.")
            else:
                print("Presenter: Settings Dialog was Rejected.")
        else:
            print("Presenter: Ensuring Settings Dialog is visible (non-modal).")
            if not self.view.isVisible(): self.view.show()
            self.view.activateWindow();
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
                    print(f"Presenter (DC): Download finished for '{model_display_name}' of type '{model_type_ui_name}'"
                          f", refreshing DC list.")
                    self._on_dc_model_type_changed(model_type_ui_name)  # Use the type from the signal
