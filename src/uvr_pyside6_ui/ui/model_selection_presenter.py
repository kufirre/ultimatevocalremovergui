from PySide6.QtCore import QObject, Slot, Signal
from .model_selection_view import DOWNLOAD_MORE_MODELS_TEXT


class ModelSelectionPresenter(QObject):
    request_show_download_center = Signal()

    def __init__(self, view, adapter):
        super().__init__()
        self.view = view
        self.adapter = adapter

        self._current_method = ""
        self._current_model = ""
        self._ensemble_mode = False

        self.view.process_method_changed.connect(self.handle_method_change)
        self.view.model_selected_by_user.connect(self.handle_model_selection_by_user)
        self.view.ensemble_mode_changed.connect(self.handle_ensemble_change)

        # Populate available methods in the view's combobox
        self._available_methods = self.adapter.get_available_methods()
        self.view.set_process_methods(self._available_methods)  # This populates and sets index 0

        # Set initial internal state for _current_method.
        # The actual loading of models and showing panel for this initial method
        # will be triggered by MainWindowView after all UI setup is complete.
        if self._available_methods:
            self._current_method = self.view.method_combo.currentText()  # Get what view set
            print(
                f"ModelSelectionPresenter __init__: Initial method set to '{self._current_method}' (models and panel will be loaded by MainWindow trigger)")

        self.view.set_ensemble_checked(self._ensemble_mode)
        print("ModelSelectionPresenter Initialized.")

    @Slot(str)
    def handle_method_change(self, method: str):
        """
        Called when the process method changes (either by user or initial setup).
        Loads models for the new method and tells the view to show the corresponding panel.
        """
        print(f"Presenter: handle_method_change received method: '{method}'")
        if not method:
            self.view.set_models([])
            self._current_method = ""
            self._current_model = ""
            self.view.show_settings_panel("")  # Attempt to show a default/empty panel
            return

        # Set current method and load its models
        self._current_method = method

        models_for_method = self.adapter.get_available_models(method)
        # set_models populates the combo and returns what it programmatically selected
        programmatically_selected_model = self.view.set_models(models_for_method)

        # Update internal _current_model based on what set_models selected.
        # This is a programmatic update, not a user action.
        if programmatically_selected_model and programmatically_selected_model != DOWNLOAD_MORE_MODELS_TEXT:
            self._current_model = programmatically_selected_model
            print(f"Presenter: For method '{method}', current model state updated to: '{self._current_model}'")
        else:
            self._current_model = ""
            print(f"Presenter: For method '{method}', no actual model selected or 'Download More...' is default.")

        # Now, tell the view to show the correct settings panel for the method.
        # This should happen after models are set, ensuring view is ready.
        self.view.show_settings_panel(self._current_method)

    @Slot(str)
    def handle_model_selection_by_user(self, selected_text: str):
        # ... (This method remains unchanged from response #29) ...
        print(f"Presenter: User explicitly selected model via combo: '{selected_text}'")
        if selected_text == DOWNLOAD_MORE_MODELS_TEXT:
            print("Presenter: User selected 'Download More Models...'. Emitting request.")
            self.request_show_download_center.emit()
            self.view.set_current_model_text(self._current_model if self._current_model else "")
        elif selected_text:
            if self._current_model != selected_text:
                self._current_model = selected_text
                print(f"Presenter: User selected Model now set to '{self._current_model}'")
        elif not selected_text and self._current_model:
            self._current_model = ""
            print(f"Presenter: User cleared model selection.")

    @Slot(bool)
    def handle_ensemble_change(self, is_checked: bool):  # Unchanged
        if self._ensemble_mode != is_checked:
            self._ensemble_mode = is_checked
            print(f"Presenter: Ensemble Mode set to {self._ensemble_mode}")

    def get_selection(self):  # Unchanged
        return {
            "method": self._current_method,
            "model": self._current_model,
            "ensemble": self._ensemble_mode,
        }