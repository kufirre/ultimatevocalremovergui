from PySide6.QtCore import QObject, Slot

class MDXNetSettingsPresenter(QObject):
    """Presenter for MDX-Net settings."""
    def __init__(self, view):
        super().__init__()
        self.view = view
        self._segment_size = 256
        self._overlap = 0.25
        self._match_method = "Default"

        self.view.segment_size_changed.connect(self.set_segment_size)
        self.view.overlap_changed.connect(self.set_overlap)
        self.view.match_method_changed.connect(self.set_match_method)
        # Debug print removed

    @Slot(int)
    def set_segment_size(self, value):
        self._segment_size = value
        # Debug print removed

    @Slot(float)
    def set_overlap(self, value):
        self._overlap = value
        # Debug print removed

    @Slot(str)
    def set_match_method(self, value):
        self._match_method = value
        # Debug print removed

    def get_settings(self):
        return {
            "segment_size": self._segment_size,
            "overlap": self._overlap,
            "match_method": self._match_method,
        }
