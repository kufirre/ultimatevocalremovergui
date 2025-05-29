"""Presenter coordinating model and method selections."""

from PySide6.QtCore import QObject, Slot, Signal
from ..core import app_constants as ac


class ModelSelectionPresenter(QObject):
    """Manage user interactions for selecting processing methods and models."""

    request_show_download_center = Signal(str)  # Emits originating_method

    def __init__(self, view, adapter):
        super().__init__()
        self.view = view
        self.adapter = adapter
        self._current_method = ""
        self._current_model = ""
        self.view.process_method_changed.connect(self.handle_method_change)
        self.view.model_selected_by_user.connect(self.process_model_selection)
        self.adapter.download_finished.connect(self._on_model_downloaded_elsewhere)

        self._available_methods = self.adapter.get_available_methods()
        self.view.set_process_methods(self._available_methods)

        if self._available_methods:
            self._current_method = self.view.method_combo.currentText()

            # self.view.set_ensemble_checked(self._is_advanced_ensemble_options) # REMOVED
        print("ModelSelectionPresenter Initialized.")

    @Slot(str, str, bool, str)
    def _on_model_downloaded_elsewhere(
        self,
        model_type_ui_name: str,
        model_display_name: str,
        success: bool,
        message: str,
    ):
    
        """Refresh models if a download from another presenter completes."""
        if success and model_type_ui_name == self._current_method:
            self.handle_method_change(self._current_method)

    @Slot(str)
    def handle_method_change(self, method: str) -> None:
        """Update available models when the processing method changes."""
        if not method:
            self.view.set_models([], "")
            self._current_method = ""
            self._current_model = ""
            self.view.show_settings_panel("")
            return
        self._current_method = method
        auto_selected_model = ""
        if method == ac.ENSEMBLE_MODELS_KEY:

            auto_selected_model = self.view.set_models(

                [], current_method=method
            )
        else:
            models_for_method = self.adapter.get_available_models(method)

            auto_selected_model = self.view.set_models(
                models_for_method, current_method=method
            )
        if (
            auto_selected_model
            and auto_selected_model != ac.DOWNLOAD_MORE_MODELS_TEXT
            and auto_selected_model != ac.ENSEMBLE_MODEL_INFO_TEXT
        ):
            self._current_model = auto_selected_model

        else:
            self._current_model = ""
        self.view.show_settings_panel(self._current_method)

    @Slot(str)
    def process_model_selection(self, selected_text: str) -> None:
        """Handle a user changing the selected model."""
        if selected_text == ac.DOWNLOAD_MORE_MODELS_TEXT:
            self.request_show_download_center.emit(
                self._current_method if self._current_method else ""
            )
            self.view.set_current_model_text(
                self._current_model if self._current_model else ""
            )
        elif selected_text and selected_text != ac.ENSEMBLE_MODEL_INFO_TEXT:
            if self._current_model != selected_text:
                self._current_model = selected_text
        elif not selected_text and self._current_model:
            self._current_model = ""

    def get_current_selection(self) -> dict:
        """Return the currently chosen processing method and model."""
        resolved_model_name = self._current_model
        if resolved_model_name == ac.DOWNLOAD_MORE_MODELS_TEXT or (
            self._current_method == ac.ENSEMBLE_MODELS_KEY
            and resolved_model_name == ac.ENSEMBLE_MODEL_INFO_TEXT
        ):
            resolved_model_name = ""
        return {
            "method": self._current_method,
            "model": resolved_model_name,
        }
