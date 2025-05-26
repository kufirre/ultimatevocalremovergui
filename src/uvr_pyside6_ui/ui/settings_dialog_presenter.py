from PySide6.QtCore import QObject, Slot
from .settings_dialog_view import SettingsDialogView


class SettingsDialogPresenter(QObject):
    """
    Presenter for the Settings Dialog. Handles loading/saving
    settings (mocked) and showing the dialog.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None  # Will be created when needed

        # --- Mock Settings Store ---
        self._current_settings = {
            "check_updates": True,
            "theme": "Default",
            "default_output": "/Users/kufy/Music/UVR_Output",  # Example
            "models_dir": "/Users/kufy/Models/UVR",  # Example
            "experimental_backend": False,
        }
        print("SettingsDialogPresenter Initialized.")

    def _load_from_store(self):
        """(Future) Loads settings from a config file/database."""
        print("Presenter: Loading settings from store (mocked).")
        return self._current_settings

    def _save_to_store(self, settings_data: dict):
        """(Future) Saves settings to a config file/database."""
        print(f"Presenter: Saving settings to store: {settings_data}")
        self._current_settings = settings_data
        # In a real app, this would write to disk.

    @Slot()
    def show_dialog(self):
        """Creates (if needed) and shows the settings dialog."""
        if not self.view:
            # We create it here, passing the main window as parent
            # to make it modal relative to the main window.
            # We'd need a way to get the main window ref, or pass None.
            # Passing None is simpler for now.
            self.view = SettingsDialogView(parent=None)
            self.view.settings_saved.connect(self._save_to_store)

        # Load current settings *before* showing
        settings_to_load = self._load_from_store()
        self.view.load_settings(settings_to_load)

        print("Presenter: Showing Settings Dialog.")
        # exec() shows the dialog modally and waits for it to close.
        result = self.view.exec()

        if result == SettingsDialogView.Accepted:
            print("Presenter: Settings Dialog Accepted.")
            # Saving is handled via the signal now.
        else:
            print("Presenter: Settings Dialog Canceled.")
