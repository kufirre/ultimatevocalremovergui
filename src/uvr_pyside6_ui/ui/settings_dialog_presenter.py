from pathlib import Path

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QWidget  # For parent type hint
from .settings_dialog_view import SettingsDialogView
from ..core.uvr_core_adapter import UVRCoreAdapter
from ..core import app_constants as ac


class SettingsDialogPresenter(QObject):
    def __init__(self, adapter: UVRCoreAdapter, parent_qt_object: QObject = None):  # Clarified parent name
        super().__init__(parent_qt_object)
        self.view: SettingsDialogView | None = None
        self.adapter = adapter  # This should correctly assign the UVRCoreAdapter instance
        self._full_online_catalog: dict = {}
        self._current_settings = {
            "check_updates": True, "theme": "Default",
            "default_output": str(Path.home() / "Music" / "UVR_Output"),  # Using pathlib for default
            "models_dir": str(Path.home() / "Documents" / "UVR_Models"),
        }
        print("SettingsDialogPresenter Initialized.")

    # ... (Keep _load_settings_from_store, _save_settings_to_store as before) ...
    def _load_settings_from_store(self) -> dict:
        print("Presenter: Loading app settings from store (mocked).")
        return self._current_settings.copy()

    @Slot(dict)
    def _save_settings_to_store(self, settings_data: dict):
        print(f"Presenter: Saving app settings to store: {settings_data}")
        self._current_settings.update(settings_data)

    def _populate_download_center_on_show(self):
        if not self.view:
            print("Presenter (DC): View not available for populating catalog.")
            return

        # Ensure self.adapter is indeed a UVRCoreAdapter instance
        if not isinstance(self.adapter, UVRCoreAdapter):
            print(f"Presenter (DC): ERROR - self.adapter is not a UVRCoreAdapter instance, it is {type(self.adapter)}!")
            self.view.set_downloadable_models_list(["Error: Adapter misconfigured in Presenter."])
            return

        if not self._full_online_catalog:
            self._full_online_catalog = self.adapter.get_online_catalog()
            print(f"Presenter (DC): Fetched full online catalog (keys: {list(self._full_online_catalog.keys())})")

        if self._full_online_catalog:
            ui_model_types = [
                ac.VR_ARCH_MODELS_KEY,
                ac.MDX_NET_MODELS_KEY,
                ac.DEMUCS_MODELS_KEY
            ]
            self.view.set_download_center_model_types(ui_model_types)

            if ui_model_types and self.view.dc_model_type_combo.count() > 0:
                # Set current index without explicit emit; currentTextChanged will fire if text changes
                self.view.dc_model_type_combo.setCurrentIndex(0)
                # If it didn't fire (e.g. first item was already selected), manually call
                if self.view.dc_model_type_combo.currentText() == ui_model_types[0]:
                    self._on_dc_model_type_changed(ui_model_types[0])
            else:
                self.view.set_downloadable_models_list(["No model types available."])
        else:
            self.view.set_download_center_model_types([])
            self.view.set_downloadable_models_list(["Error: Could not load any download catalog."])
            print("Presenter (DC): Full online catalog is empty after all fallbacks.")

    @Slot(str)
    def _on_dc_model_type_changed(self, ui_model_type: str):
        if not self.view or not self._full_online_catalog or not ui_model_type:
            print(f"Presenter (DC): View, catalog, or UI model type not ready. UI Type: '{ui_model_type}'")
            self.view.set_downloadable_models_list([])
            return
        print(f"Presenter (DC): UI Model type selected for download list: {ui_model_type}")
        downloadable_models_dict = self.adapter.get_downloadable_models_for_type(ui_model_type)
        user_friendly_names_to_download = list(downloadable_models_dict.keys())
        if not user_friendly_names_to_download:
            print(f"Presenter (DC): No new downloadable models found for type '{ui_model_type}'.")
            self.view.set_downloadable_models_list([f"No new models to download for {ui_model_type}."])
        else:
            self.view.set_downloadable_models_list(user_friendly_names_to_download)

    @Slot()
    def _on_dc_download_button_clicked(self):
        if not self.view or not self._full_online_catalog: return

        selected_ui_type = self.view.dc_model_type_combo.currentText()
        selected_list_items = self.view.dc_downloadable_models_list.selectedItems()

        if not selected_ui_type or not selected_list_items:
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
                download_target_info = models_in_online_category[user_friendly_model_name]
                break

        if download_target_info:
            self.view.dc_status_label.setText(f"Status: Starting download for {user_friendly_model_name}...")
            self.view.dc_download_button.setEnabled(False)  # Disable button during download
            self.view.dc_model_type_combo.setEnabled(False)  # Disable type selection
            self.view.dc_downloadable_models_list.setEnabled(False)  # Disable list

            self.adapter.download_model_mock(selected_ui_type, user_friendly_model_name, download_target_info)
        else:
            message = f"Status: Error: Could not find download target info for '{user_friendly_model_name}' in catalog."
            print(f"Presenter (DC): {message}")
            self.view.dc_status_label.setText(message)

    @Slot()
    def show_dialog(self, exec_dialog: bool = True):
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
        self._populate_download_center_on_show()
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

    @Slot(str, bool, str)
    def _on_adapter_download_finished(self, model_name: str, success: bool, message: str):
        if self.view and self.view.isVisible() and self.view.tab_widget.currentIndex() == 2:
            self.view.dc_status_label.setText(message)
            self.view.dc_download_button.setEnabled(True)  # Re-enable button
            self.view.dc_model_type_combo.setEnabled(True)  # Re-enable type selection
            self.view.dc_downloadable_models_list.setEnabled(True)  # Re-enable list

            if success:
                current_type = self.view.dc_model_type_combo.currentText()
                if current_type:
                    print(f"Presenter (DC): Download finished for {model_name}, refreshing list for {current_type}.")
                    self._on_dc_model_type_changed(current_type)