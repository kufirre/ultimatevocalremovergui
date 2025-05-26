import os

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QWidget # For type hinting parent if it's MainWindowView
from .settings_dialog_view import SettingsDialogView

class SettingsDialogPresenter(QObject):
    """
    Presenter for the Settings Dialog.
    Manages the lifecycle of the settings dialog, including loading data into it
    and saving data from it.
    """
    def __init__(self, parent_main_window_view=None): # Can take MainWindowView as QObject parent
        super().__init__(parent_main_window_view)
        self.view: SettingsDialogView | None = None # The dialog view instance, created on demand

        # Mock application settings store
        # In a real application, this would be loaded from/saved to a config file (e.g., JSON, INI, QSettings)
        self._current_settings = {
            "check_updates": True,
            "theme": "Default",
            "default_output": os.path.expanduser("~/Music/UVR_Output"), # Example using home dir
            "models_dir": os.path.expanduser("~/Documents/UVR_Models"), # Example
            "experimental_backend": False,
        }
        print("SettingsDialogPresenter Initialized.")

    def _load_settings_from_store(self) -> dict:
        """
        (Future Implementation) Loads settings from a persistent store
        (e.g., config file, QSettings).
        For now, returns mock settings.
        """
        print("Presenter: Loading settings from store (mocked).")
        # TODO: Implement actual loading from QSettings or a JSON/INI file
        return self._current_settings.copy()

    @Slot(dict)
    def _save_settings_to_store(self, settings_data: dict):
        """
        (Future Implementation) Saves settings to a persistent store.
        For now, updates in-memory mock settings.
        Args:
            settings_data: A dictionary of settings to save.
        """
        print(f"Presenter: Saving settings to store: {settings_data}")
        self._current_settings.update(settings_data)
        # TODO: Implement actual saving to QSettings or a JSON/INI file

    @Slot()
    def show_dialog(self, exec_dialog: bool = True):
        """
        Creates (if it doesn't exist), configures, and shows the settings dialog.
        Args:
            exec_dialog: If True (default), shows the dialog modally (.exec()).
                         If False, shows the dialog non-modally (.show()).
        """
        if not self.view:
            # Determine parent for the dialog. If self.parent() is a QWidget, use it.
            # This helps with proper dialog behavior (e.g., centering over parent).
            parent_widget = self.parent() if isinstance(self.parent(), QWidget) else None
            self.view = SettingsDialogView(parent=parent_widget)
            # Connect the custom signal from the view for when settings are accepted
            self.view.settings_saved.connect(self._save_settings_to_store)

        # Always load current settings into the view before showing
        settings_to_load = self._load_settings_from_store()
        self.view.load_settings(settings_to_load)

        if exec_dialog:
            print("Presenter: Showing Settings Dialog (modal).")
            result = self.view.exec()  # Modal execution, blocks until closed
            if result == SettingsDialogView.Accepted: # QDialog.Accepted is an int
                print("Presenter: Settings Dialog was Accepted (OK clicked).")
                # Settings are saved via the settings_saved signal connection now
            else:
                print("Presenter: Settings Dialog was Rejected (Cancel clicked or closed).")
        else:
            # Show non-modally, typically used if we need to interact with it
            # programmatically after opening (e.g., switch tabs).
            print("Presenter: Ensuring Settings Dialog is visible (non-modal for tab switch).")
            self.view.show()
            self.view.activateWindow() # Bring it to the front
            self.view.raise_() # Ensure it's on top of other windows
