from PySide6.QtCore import QObject, Slot

class DemucsSettingsPresenter(QObject):
    """Presenter for Demucs settings."""
    def __init__(self, view):
        super().__init__()
        self.view = view
        self._segments = 10
        self._shifts = 2
        self._split = True

        self.view.segments_changed.connect(self.set_segments)
        self.view.shifts_changed.connect(self.set_shifts)
        self.view.split_changed.connect(self.set_split)
        # print("DemucsSettingsPresenter Initialized.") # Removed unprofessional comment

    @Slot(int)
    def set_segments(self, value):
        self._segments = value
        # print(f"Presenter (Demucs): Segments = {value}") # Removed unprofessional comment

    @Slot(int)
    def set_shifts(self, value):
        self._shifts = value
        # print(f"Presenter (Demucs): Shifts = {value}") # Removed unprofessional comment

    @Slot(bool)
    def set_split(self, value):
        self._split = value
        # print(f"Presenter (Demucs): Split = {value}") # Removed unprofessional comment

    def get_settings(self):
        return {
            "segments": self._segments,
            "shifts": self._shifts,
            "split": self._split,
        }
