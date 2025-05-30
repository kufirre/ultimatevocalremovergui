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
        # Debug print removed

    @Slot(str)
    def set_window_size(self, value):
        self._window_size = value
        # Debug print removed

    @Slot(int)
    def set_aggression(self, value):
        self._aggression = value
        # Debug print removed

    @Slot(bool)
    def set_high_end(self, value):
        self._high_end = value
        # Debug print removed

    def get_settings(self):
        return {
            "window_size": self._window_size,
            "aggression": self._aggression,
            "high_end": self._high_end
        }
