from PySide6.QtCore import QObject, Slot
from ..core.logger_utils import get_logger

logger = get_logger("vr_settings_presenter")


class VRArchSettingsPresenter(QObject):
    """Presenter for VR Architecture settings."""
    def __init__(self, view):
        super().__init__()
        self.view = view
        self._window_size = "512"
        self._aggression = 5
        self._high_end = False
        self._tta = False
        self._post_process = False
        self._post_process_threshold = 0.2
        self._batch_size = 4

        # Connect all view signals
        self.view.window_size_changed.connect(self.set_window_size)
        self.view.aggression_changed.connect(self.set_aggression)
        self.view.high_end_changed.connect(self.set_high_end)
        self.view.tta_changed.connect(self.set_tta)
        self.view.post_process_changed.connect(self.set_post_process)
        self.view.post_process_threshold_changed.connect(self.set_post_process_threshold)
        self.view.batch_size_changed.connect(self.set_batch_size)
        
        logger.debug("VRArchSettingsPresenter initialized")

    @Slot(str)
    def set_window_size(self, value):
        self._window_size = value
        logger.debug(f"Window size changed to: {value}")

    @Slot(int)
    def set_aggression(self, value):
        self._aggression = value
        logger.debug(f"Aggression changed to: {value}")

    @Slot(bool)
    def set_high_end(self, value):
        self._high_end = value
        logger.debug(f"High End Process changed to: {value}")

    @Slot(bool)
    def set_tta(self, value):
        self._tta = value
        logger.debug(f"TTA changed to: {value}")

    @Slot(bool)
    def set_post_process(self, value):
        self._post_process = value
        logger.debug(f"Post Process changed to: {value}")

    @Slot(float)
    def set_post_process_threshold(self, value):
        self._post_process_threshold = value
        logger.debug(f"Post Process Threshold changed to: {value}")

    @Slot(int)
    def set_batch_size(self, value):
        self._batch_size = value
        logger.debug(f"Batch size changed to: {value}")

    def get_settings(self):
        return {
            "window_size": self._window_size,
            "aggression_setting": self._aggression,
            "is_high_end_process": self._high_end,
            "is_tta": self._tta,
            "is_post_process": self._post_process,
            "post_process_threshold": self._post_process_threshold,
            "batch_size": self._batch_size
        }
