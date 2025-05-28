from PySide6.QtCore import QObject, Slot, Signal
from ..core import app_constants as ac


class ModelSelectionPresenter(QObject):
    request_show_download_center = Signal()

    def __init__(self, view, adapter):
        super().__init__()
        self.view = view
        self.adapter = adapter
        self._current_method = ""
        self._current_model = ""
        self._is_advanced_ensemble_options = False

        self.view.process_method_changed.connect(self.handle_method_change)
        self.view.model_selected_by_user.connect(self.handle_model_selection_by_user)
        self.view.ensemble_mode_changed.connect(self.handle_advanced_ensemble_options_change)

        self._available_methods = self.adapter.get_available_methods()
        self.view.set_process_methods(self._available_methods)

        if self._available_methods:
            self._current_method = self.view.method_combo.currentText()
            print(f"ModelSelectionPresenter __init__: Initial method set to '{self._current_method}'")

        self.view.set_ensemble_checked(self._is_advanced_ensemble_options)
        print("ModelSelectionPresenter Initialized.")

    @Slot(str)
    def handle_method_change(self, method: str):
        print(f"Presenter: handle_method_change received method: '{method}'")
        if not method:
            self.view.set_models([], "")
            self._current_method = ""
            self._current_model = ""
            self.view.show_settings_panel("")
            return

        self._current_method = method

        if method == ac.ENSEMBLE_MODELS_KEY:
            programmatically_selected_model = self.view.set_models([], current_method=method)
        else:
            models_for_method = self.adapter.get_available_models(method)
            programmatically_selected_model = self.view.set_models(models_for_method, current_method=method)

        if (programmatically_selected_model and programmatically_selected_model != ac.DOWNLOAD_MORE_MODELS_TEXT and
                programmatically_selected_model != ac.ENSEMBLE_MODEL_INFO_TEXT):
            self._current_model = programmatically_selected_model
            print(f"Presenter: For method '{method}', current model state updated to: '{self._current_model}'")
        else:
            self._current_model = ""
            print(f"Presenter: For method '{method}', no actual model selected or placeholder/download shown.")

        self.view.show_settings_panel(self._current_method)

    @Slot(str)
    def handle_model_selection_by_user(self, selected_text: str):
        print(f"Presenter: User explicitly selected model via combo: '{selected_text}'")
        if selected_text == ac.DOWNLOAD_MORE_MODELS_TEXT:
            print("Presenter: User selected 'Download More Models...'. Emitting request.")
            self.request_show_download_center.emit()
            self.view.set_current_model_text(self._current_model if self._current_model else "")
        elif selected_text and selected_text != ac.ENSEMBLE_MODEL_INFO_TEXT:
            if self._current_model != selected_text:
                self._current_model = selected_text
                print(f"Presenter: User selected Model now set to '{self._current_model}'")
        elif not selected_text and self._current_model:
            self._current_model = ""
            print(f"Presenter: Model selection cleared by user.")

    @Slot(bool)
    def handle_advanced_ensemble_options_change(self, is_checked: bool):
        if self._is_advanced_ensemble_options != is_checked:
            self._is_advanced_ensemble_options = is_checked
            print(f"Presenter: Advanced Ensemble Options (checkbox) set to {self._is_advanced_ensemble_options}")

    def get_selection(self):
        actual_model_name = self._current_model
        if (actual_model_name == ac.DOWNLOAD_MORE_MODELS_TEXT or
                self._current_method == ac.ENSEMBLE_MODELS_KEY and actual_model_name == ac.ENSEMBLE_MODEL_INFO_TEXT):
            actual_model_name = ""
        return {
            "method": self._current_method,
            "model": actual_model_name,
            "ensemble_advanced_opts": self._is_advanced_ensemble_options,
        }
