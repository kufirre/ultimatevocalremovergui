from PySide6.QtCore import QObject, Slot


class ModelSelectionPresenter(QObject):
    """
    Presenter for Model Selection. Fetches models via the Adapter,
    handles changes, and controls visibility.
    """

    def __init__(self, view, adapter):  # Added adapter
        super().__init__()
        self.view = view
        self.adapter = adapter  # Store the adapter

        self._current_method = ""
        self._current_model = ""
        self._ensemble_mode = False

        # --- Use Adapter (NEW) ---
        self._available_methods = self.adapter.get_available_methods()
        # We'll fetch specific models within handle_method_change now.

        self.view.process_method_changed.connect(self.handle_method_change)
        self.view.model_changed.connect(self.handle_model_change)
        self.view.ensemble_mode_changed.connect(self.handle_ensemble_change)

        self.view.set_process_methods(self._available_methods)
        if self._available_methods:
            self.view.set_current_method(self._available_methods[0])

        self.view.set_ensemble_checked(self._ensemble_mode)
        print("ModelSelectionPresenter Initialized (with Adapter).")

    @Slot(str)
    def handle_method_change(self, method: str):
        if self._current_method != method and method:
            self._current_method = method
            print(f"Presenter: Process Method set to {self._current_method}")

            # --- Use Adapter (NEW) ---
            models_for_method = self.adapter.get_available_models(method)
            self.view.set_models(models_for_method)

            if models_for_method:
                self.handle_model_change(models_for_method[0])
            else:
                self.handle_model_change("")

            self.view.show_settings_panel(method)

            # ... (rest of the class remains the same) ...

    @Slot(str)
    def handle_model_change(self, model: str):
        if self._current_model != model:
            self._current_model = model
            print(f"Presenter: Model set to {self._current_model}")

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
