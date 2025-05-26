from PySide6.QtCore import QObject, Slot


class ModelSelectionPresenter(QObject):
    """
    Presenter for Model Selection. Fetches models, handles changes,
    and controls visibility of detailed settings via the QStackedWidget.
    """

    def __init__(self, view):
        super().__init__()
        self.view = view
        # self.model = model

        self._current_method = ""
        self._current_model = ""
        self._ensemble_mode = False

        self._available_methods = ["VR Arch", "MDX-Net", "Demucs", "Ensemble"]
        self._available_models = {
            "VR Arch": ["VR Model 1", "VR Model 2 (HP)", "VR 5_1_Arch"],
            "MDX-Net": ["MDX23 Main", "UVR-MDX-NET Inst HQ 1", "Kim Vocal 1"],
            "Demucs": ["htdemucs", "htdemucs_ft", "mdx_extra"],
            "Ensemble": []
        }

        self.view.process_method_changed.connect(self.handle_method_change)
        self.view.model_changed.connect(self.handle_model_change)
        self.view.ensemble_mode_changed.connect(self.handle_ensemble_change)

        self.view.set_process_methods(self._available_methods)
        if self._available_methods:
            # Set initial method - IMPORTANT: Do this *after* panels are added
            # We will call this again from MainWindow after setup.
            # self.handle_method_change(self._available_methods[0])
            self.view.set_current_method(self._available_methods[0])

        self.view.set_ensemble_checked(self._ensemble_mode)
        print("ModelSelectionPresenter Initialized.")

    @Slot(str)
    def handle_method_change(self, method: str):
        """Handles changes to the Process Method."""
        if self._current_method != method and method:
            self._current_method = method
            print(f"Presenter: Process Method set to {self._current_method}")

            models_for_method = self._available_models.get(method, [])
            self.view.set_models(models_for_method)

            if models_for_method:
                self.handle_model_change(models_for_method[0])
            else:
                self.handle_model_change("")

            # --- Tell the View which panel to show (NEW) ---
            # We use the method name as the key.
            # We'll need a mapping if names differ.
            self.view.show_settings_panel(method)

    @Slot(str)
    def handle_model_change(self, model: str):
        # ... (no changes needed here) ...
        if self._current_model != model:
            self._current_model = model
            print(f"Presenter: Model set to {self._current_model}")

    @Slot(bool)
    def handle_ensemble_change(self, is_checked: bool):
        # ... (no changes needed here) ...
        if self._ensemble_mode != is_checked:
            self._ensemble_mode = is_checked
            print(f"Presenter: Ensemble Mode set to {self._ensemble_mode}")

    def get_selection(self):
        return {
            "method": self._current_method,
            "model": self._current_model,
            "ensemble": self._ensemble_mode,
        }
