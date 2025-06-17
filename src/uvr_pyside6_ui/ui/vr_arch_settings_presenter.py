from PySide6.QtCore import QObject, Signal, Slot

from ..core.logger_utils import get_logger

logger = get_logger("vr_settings_presenter")


class VRArchSettingsPresenter(QObject):
    """Presenter for VR Architecture settings."""

    # Signals
    settings_changed = Signal(dict)

    def __init__(self, view):
        super().__init__()
        self.view = view
        # Basic settings (visible on main page)
        self._window_size = "512"
        self._aggression = 5
        self._high_end = False
        self._tta = False
        self._post_process = False
        self._post_process_threshold = 0.2
        self._batch_size = 4

        # Advanced settings (from advanced dialog)
        self._advanced_settings = {
            # Secondary model settings
            "vr_is_secondary_model_activate": False,
            "vr_vocals_secondary_model": "No Model",
            "vr_bass_secondary_model": "No Model",
            "vr_drums_secondary_model": "No Model",
            "vr_other_secondary_model": "No Model",
            "vr_vocals_secondary_model_scale": 0.9,
            "vr_bass_secondary_model_scale": 0.5,
            "vr_drums_secondary_model_scale": 0.5,
            "vr_other_secondary_model_scale": 0.7,
            # Vocal splitter settings
            "vr_is_vocal_split_mode": False,
            "vr_vocal_model": "No Model",
            "vr_deverb_option": "Main Vocals Only",
            "vr_save_vocal_only": False,
            "vr_save_inst_only": False,
        }

        # Connect all view signals
        self.view.window_size_changed.connect(self.set_window_size)
        self.view.aggression_changed.connect(self.set_aggression)
        self.view.high_end_changed.connect(self.set_high_end)
        self.view.tta_changed.connect(self.set_tta)
        self.view.post_process_changed.connect(self.set_post_process)
        self.view.post_process_threshold_changed.connect(
            self.set_post_process_threshold
        )
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
        # Combine basic and advanced settings
        basic_settings = {
            "window_size": self._window_size,
            "aggression_setting": self._aggression,
            "is_high_end_process": self._high_end,
            "is_tta": self._tta,
            "is_post_process": self._post_process,
            "post_process_threshold": self._post_process_threshold,
            "batch_size": self._batch_size,
        }
        return {**basic_settings, **self._advanced_settings}

    def load_settings(self, settings_dict):
        """Load settings from saved configuration."""
        if settings_dict:
            # Load basic settings
            if "window_size" in settings_dict:
                self.set_window_size(str(settings_dict["window_size"]))
                self.view.set_window_size(str(settings_dict["window_size"]))
            if "aggression_setting" in settings_dict:
                self.set_aggression(settings_dict["aggression_setting"])
                self.view.set_aggression(settings_dict["aggression_setting"])
            if "is_high_end_process" in settings_dict:
                self.set_high_end(settings_dict["is_high_end_process"])
                self.view.set_high_end(settings_dict["is_high_end_process"])
            if "is_tta" in settings_dict:
                self.set_tta(settings_dict["is_tta"])
                self.view.set_tta(settings_dict["is_tta"])
            if "is_post_process" in settings_dict:
                self.set_post_process(settings_dict["is_post_process"])
                self.view.set_post_process(settings_dict["is_post_process"])
            if "post_process_threshold" in settings_dict:
                self.set_post_process_threshold(settings_dict["post_process_threshold"])
                self.view.set_post_process_threshold(
                    settings_dict["post_process_threshold"]
                )
            if "batch_size" in settings_dict:
                self.set_batch_size(settings_dict["batch_size"])
                self.view.set_batch_size(settings_dict["batch_size"])

            # Load advanced settings
            for key in self._advanced_settings.keys():
                if key in settings_dict:
                    self._advanced_settings[key] = settings_dict[key]

    def show_advanced_settings(self, is_vr_mode=False):
        """Show the advanced VR settings dialog."""
        from .vr_arch_advanced_dialog import VRArchAdvancedDialog

        # Get current settings
        current_settings = self.get_settings()

        # Create and show dialog
        dialog = VRArchAdvancedDialog(current_settings, is_vr_mode, self.view)
        dialog.settings_updated.connect(self.update_advanced_settings)

        return dialog.exec()

    def update_advanced_settings(self, advanced_settings):
        """Update settings from the advanced dialog."""
        logger.debug(f"Updating VR advanced settings: {advanced_settings}")

        # Update basic settings that affect the view
        for key, value in advanced_settings.items():
            if key == "window_size":
                self.set_window_size(str(value))
                self.view.set_window_size(str(value))
            elif key == "aggression_setting":
                self.set_aggression(value)
                self.view.set_aggression(value)
            elif key == "is_high_end_process":
                self.set_high_end(value)
                self.view.set_high_end(value)
            elif key == "is_tta":
                self.set_tta(value)
                self.view.set_tta(value)
            elif key == "is_post_process":
                self.set_post_process(value)
                self.view.set_post_process(value)
            elif key == "post_process_threshold":
                self.set_post_process_threshold(value)
                self.view.set_post_process_threshold(value)
            elif key == "batch_size":
                self.set_batch_size(value)
                self.view.set_batch_size(value)
            elif key in self._advanced_settings:
                # Update advanced settings that don't affect the main view
                self._advanced_settings[key] = value

        # Emit settings changed signal for any listeners
        self.settings_changed.emit(self.get_settings())
