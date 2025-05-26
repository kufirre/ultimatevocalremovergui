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

        # Connect signals from the view
        self.view.process_method_changed.connect(self.handle_method_change)
        # IMPORTANT CHANGE: Connect to the user-activated signal
        self.view.model_selected_by_user.connect(self.handle_model_selection_by_user)
        self.view.ensemble_mode_changed.connect(self.handle_ensemble_change)

        self._available_methods = self.adapter.get_available_methods()
        # This will populate the method_combo and emit process_method_changed for the first method,
        # which in turn calls our handle_method_change below.
        self.view.set_process_methods(self._available_methods)

        self.view.set_ensemble_checked(self._ensemble_mode)
        print("ModelSelectionPresenter Initialized.")

    @Slot(str)
    def handle_method_change(self, method: str):
        print(f"Presenter: handle_method_change received method: '{method}'")
        if not method:
            self.view.set_models([])
            self._current_method = ""
            self._current_model = ""
            self.view.show_settings_panel("")
            return

        self._current_method = method

        models_for_method = self.adapter.get_available_models(method)
        # set_models will populate the combo and return the text it programmatically selected
        programmatically_selected_model = self.view.set_models(models_for_method)

        # Update internal state based on what set_models programmatically selected.
        # This is NOT a user action, so it should not trigger Download Center.
        if programmatically_selected_model and programmatically_selected_model != DOWNLOAD_MORE_MODELS_TEXT:
            self._current_model = programmatically_selected_model
            print(f"Presenter: For method '{method}', current model set to: '{self._current_model}'")
        else:
            self._current_model = ""  # No actual model, or "Download More..." was the only option
            print(f"Presenter: For method '{method}', no actual model selected or 'Download More...' is default.")

        self.view.show_settings_panel(self._current_method)

    @Slot(str)
    def handle_model_selection_by_user(self, selected_text: str):
        """This slot is triggered ONLY by explicit user interaction with model_combo."""
        print(f"Presenter: User explicitly selected model via combo: '{selected_text}'")
        if selected_text == DOWNLOAD_MORE_MODELS_TEXT:
            print("Presenter: User selected 'Download More Models...'. Emitting request.")
            self.request_show_download_center.emit()
            # Restore previous valid model selection in the view after dialog action.
            # _current_model should hold the last *actual* model, not "Download..."
            self.view.set_current_model_text(self._current_model if self._current_model else "")
        elif selected_text:  # A real model name selected by user
            if self._current_model != selected_text:  # Check if it's a change
                self._current_model = selected_text
                print(f"Presenter: User selected Model now set to '{self._current_model}'")
        # If selected_text is empty (e.g. if combo allows clearing, though not typical for non-editable)
        # or some other unhandled case, _current_model remains as is or could be cleared.
        # For now, we only update _current_model if it's a new, valid, non-action string.

    @Slot(bool)
    def handle_ensemble_change(self, is_checked: bool):
        if self._ensemble_mode != is_checked:
            self._ensemble_mode = is_checked
            print(f"Presenter: Ensemble Mode set to {self._ensemble_mode}")

    def get_selection(self):
        return {
            "method": self._current_method,
            "model": self._current_model,
            "ensemble": self._ensemble_mode,
        }
