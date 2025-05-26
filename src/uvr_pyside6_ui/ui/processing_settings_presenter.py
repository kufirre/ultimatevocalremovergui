from PySide6.QtCore import QObject, Slot


class ProcessingSettingsPresenter(QObject):
    """
    Presenter for the Processing Settings View. Manages the state
    of these settings and will interact with the Model/Adapter.
    """
    def __init__(self, view):
        super().__init__()
        self.view = view
        # self.model = model # To be added later

        # --- Internal State ---
        self._use_gpu = False
        self._normalize = False
        self._output_format = "WAV" # Default

        # --- Connect View Signals to Presenter Slots ---
        self.view.gpu_conversion_changed.connect(self.handle_gpu_change)
        self.view.normalize_output_changed.connect(self.handle_normalize_change)
        self.view.output_format_changed.connect(self.handle_format_change)

        # --- Initial Setup ---
        # In a real app, you might check if GPU is available here
        # and call self.view.set_gpu_conversion_enabled(False/True)
        self.view.set_gpu_conversion_enabled(True) # Assume available for now
        self.view.set_gpu_conversion_checked(self._use_gpu)
        self.view.set_normalize_checked(self._normalize)
        self.view.set_output_format(self._output_format)

        print("ProcessingSettingsPresenter Initialized.")

    @Slot(bool)
    def handle_gpu_change(self, is_checked):
        """Handles changes to the GPU checkbox."""
        if self._use_gpu != is_checked:
            self._use_gpu = is_checked
            print(f"Presenter: Use GPU set to {self._use_gpu}")
            # TODO: Update model/app state

    @Slot(bool)
    def handle_normalize_change(self, is_checked):
        """Handles changes to the Normalize checkbox."""
        if self._normalize != is_checked:
            self._normalize = is_checked
            print(f"Presenter: Normalize Output set to {self._normalize}")
            # TODO: Update model/app state

    @Slot(str)
    def handle_format_change(self, format_str):
        """Handles changes to the Output Format combobox."""
        if self._output_format != format_str:
            self._output_format = format_str
            print(f"Presenter: Output Format set to {self._output_format}")
            # TODO: Update model/app state

    # --- Public methods ---
    def get_settings(self):
        """Returns the current processing settings."""
        return {
            "use_gpu": self._use_gpu,
            "normalize": self._normalize,
            "output_format": self._output_format,
        }
