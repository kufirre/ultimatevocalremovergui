from PySide6.QtCore import QObject, Slot


class ProcessingSettingsPresenter(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view

        self._use_gpu: bool = False
        self._normalize: bool = False
        self._output_format: str = "WAV"
        self._primary_stem_only: bool = False
        self._secondary_stem_only: bool = False
        self._sample_mode: bool = False
        # self._sample_duration: int = 30 # This would come from app settings later

        self.view.gpu_conversion_changed.connect(self.handle_gpu_change)
        self.view.normalize_output_changed.connect(self.handle_normalize_change)
        self.view.output_format_changed.connect(self.handle_format_change)
        self.view.primary_stem_only_changed.connect(self.handle_primary_stem_change)
        self.view.secondary_stem_only_changed.connect(self.handle_secondary_stem_change)
        self.view.sample_mode_changed.connect(self.handle_sample_mode_change)

        self._update_view_with_current_settings()
        # Debug print removed

    def _update_view_with_current_settings(self):
        """Helper to set all view elements from current state."""
        # In a real app, you might check if GPU is available here
        # and call self.view.set_gpu_conversion_enabled(False/True)
        self.view.set_gpu_conversion_enabled(True)  # Assume available for now
        self.view.set_gpu_conversion_checked(self._use_gpu)
        self.view.set_normalize_checked(self._normalize)
        self.view.set_output_format(self._output_format)
        self.view.set_primary_stem_only_checked(self._primary_stem_only)
        self.view.set_secondary_stem_only_checked(self._secondary_stem_only)
        self.view.set_sample_mode_checked(self._sample_mode)
        # Update sample mode checkbox text if dynamic:
        # sample_duration = self.get_app_setting("sample_duration", 30) # Placeholder
        # self.view.sample_mode_checkbox.setText(f"Sample Mode ({sample_duration}s)" if self._sample_mode else "Sample Mode")

    @Slot(bool)
    def handle_gpu_change(self, is_checked: bool):
        if self._use_gpu != is_checked:
            self._use_gpu = is_checked
            # Debug print removed

    @Slot(bool)
    def handle_normalize_change(self, is_checked: bool):
        if self._normalize != is_checked:
            self._normalize = is_checked
            # Debug print removed

    @Slot(str)
    def handle_format_change(self, format_str: str):
        if self._output_format != format_str:
            self._output_format = format_str
            # Debug print removed

    @Slot(bool)
    def handle_primary_stem_change(self, is_checked: bool):
        if self._primary_stem_only != is_checked:
            self._primary_stem_only = is_checked
            # Debug print removed
            if is_checked and self._secondary_stem_only:  # Mutually exclusive
                self._secondary_stem_only = False
                self.view.set_secondary_stem_only_checked(False)  # Update view

    @Slot(bool)
    def handle_secondary_stem_change(self, is_checked: bool):
        if self._secondary_stem_only != is_checked:
            self._secondary_stem_only = is_checked
            # Debug print removed
            if is_checked and self._primary_stem_only:  # Mutually exclusive
                self._primary_stem_only = False
                self.view.set_primary_stem_only_checked(False)  # Update view

    @Slot(bool)
    def handle_sample_mode_change(self, is_checked: bool):
        if self._sample_mode != is_checked:
            self._sample_mode = is_checked
            # Debug print removed
            # sample_duration = self.get_app_setting("sample_duration", 30) # Placeholder
            # self.view.sample_mode_checkbox.setText(f"Sample Mode ({sample_duration}s)" if is_checked else "Sample Mode")

    def get_settings(self) -> dict:  # For ExecutionControlPresenter
        return {
            "use_gpu": self._use_gpu,
            "normalize": self._normalize,
            "output_format": self._output_format,
            "primary_stem_only": self._primary_stem_only,
            "secondary_stem_only": self._secondary_stem_only,
            "sample_mode": self._sample_mode,
            # "sample_duration": self.get_app_setting("sample_duration", 30) # If needed for backend
        }
