from PySide6.QtCore import QObject, Slot


class EnsembleSettingsPresenter(QObject):
    """Presenter for Ensemble settings."""
    def __init__(self, view):
        super().__init__()
        self.view = view
        # --- Internal State ---
        # (Will hold a list of models and their configs later)
        self._ensemble_models = [
            ("VR Arch - VR Model 2 (HP)", "Vocals"),
            ("MDX-Net - Kim Vocal 1", "Vocals")
        ]
        self._merge_method = "Average"

        # --- Connect Signals ---
        self.view.add_model_clicked.connect(self.handle_add_model)
        self.view.remove_model_clicked.connect(self.handle_remove_model)
        self.view.merge_method_changed.connect(self.handle_merge_change)

        print("EnsembleSettingsPresenter Initialized (Improved Stub).")

    @Slot()
    def handle_add_model(self):
        """Handles the 'Add Model' button click."""
        print("Presenter (Ensemble): Add Model Clicked - (Future: Show Dialog)")
        # In a real app, this would open a dialog to select a model
        # For now, let's just add a dummy one:
        new_model = ("Demucs - htdemucs_ft", "Drums")
        self._ensemble_models.append(new_model)
        self.view.add_ensemble_item(new_model[0], new_model[1])

    @Slot()
    def handle_remove_model(self):
        """Handles the 'Remove Selected' button click."""
        print("Presenter (Ensemble): Remove Model Clicked")
        # In a real app, we'd need to know which item was selected
        # and update our internal list. The view can handle removing its item.
        self.view.remove_selected_item()
        # We'd need to update self._ensemble_models here too.

    @Slot(str)
    def handle_merge_change(self, method: str):
        """Handles changes to the merge method."""
        self._merge_method = method
        print(f"Presenter (Ensemble): Merge Method = {method}")

    def get_settings(self):
        """Returns the current ensemble configuration."""
        return {
            "mode": "Ensemble",
            "models": self._ensemble_models,
            "merge_method": self._merge_method
        }
