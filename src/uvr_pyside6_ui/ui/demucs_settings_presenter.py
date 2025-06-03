from PySide6.QtCore import QObject, Slot

class DemucsSettingsPresenter(QObject):
    """Presenter for Demucs settings."""
    def __init__(self, view):
        super().__init__()
        self.view = view
        self._segments = 10
        self._shifts = 2
        self._split = True
        self._stems = "All Stems"
        self._combine_stems = True

        self.view.segments_changed.connect(self.set_segments)
        self.view.shifts_changed.connect(self.set_shifts)
        self.view.split_changed.connect(self.set_split)
        self.view.stems_changed.connect(self.set_stems)
        self.view.combine_stems_changed.connect(self.set_combine_stems)
        # Debug print removed

    @Slot(int)
    def set_segments(self, value):
        self._segments = value
        # Debug print removed

    @Slot(int)
    def set_shifts(self, value):
        self._shifts = value
        # Debug print removed

    @Slot(bool)
    def set_split(self, value):
        self._split = value
        # Debug print removed

    @Slot(str)
    def set_stems(self, value):
        self._stems = value
        # Debug print removed

    @Slot(bool)
    def set_combine_stems(self, value):
        self._combine_stems = value
        # Debug print removed

    def get_settings(self):
        return {
            "segment": self._segments,
            "shifts": self._shifts,
            "is_split_mode": self._split,
            "demucs_stems": self._stems,
            "is_demucs_combine_stems": self._combine_stems,
        }
