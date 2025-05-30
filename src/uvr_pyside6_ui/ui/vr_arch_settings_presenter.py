from PySide6.QtCore import QObject, Slot


class VRArchSettingsPresenter(QObject):
    """Presenter for VR Architecture settings."""
    def __init__(self, view):
        super().__init__()
        self.view = view
        self._window_size = "512"
        self._aggression = 5
        self._high_end = False

        self.view.window_size_changed.connect(self.set_window_size)
        self.view.aggression_changed.connect(self.set_aggression)
        self.view.high_end_changed.connect(self.set_high_end)
        # print("VRArchSettingsPresenter Initialized.") # Removed unprofessional comment

    @Slot(str)
    def set_window_size(self, value):
        self._window_size = value
        # print(f"Presenter (VR): Window Size = {value}") # Removed unprofessional comment

    @Slot(int)
    def set_aggression(self, value):
        self._aggression = value
        # print(f"Presenter (VR): Aggression = {value}") # Removed unprofessional comment

    @Slot(bool)
    def set_high_end(self, value):
        self._high_end = value
        # print(f"Presenter (VR): High End = {value}") # Removed unprofessional comment

    def get_settings(self):
        return {
            "window_size": self._window_size,
            "aggression": self._aggression,
            "high_end": self._high_end
        }
