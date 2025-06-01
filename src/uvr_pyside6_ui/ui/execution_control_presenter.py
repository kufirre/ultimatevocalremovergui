from PySide6.QtCore import QObject, Slot
from ..core import app_constants as ac # Import app_constants


# No QTimer needed here now, as adapter handles it

class ExecutionControlPresenter(QObject):
    """
    Presenter for Execution Control. Gathers all settings,
    initiates processing via the adapter, and updates progress via signals.
    """

    def __init__(self, view, main_window_presenters, adapter):  # Added adapter
        super().__init__()
        self.view = view
        self.presenters = main_window_presenters
        self.adapter = adapter  # Store the adapter

        self._is_processing = False

        # --- Connect View Signals ---
        self.view.start_processing_clicked.connect(self.handle_start_processing)
        # TODO: Connect stop button later

        # --- Connect Adapter Signals (NEW) ---
        self.adapter.progress_updated.connect(self.on_progress_update)
        self.adapter.processing_finished.connect(self.on_processing_finished)

        self.view.set_progress_text("Idle")
        self.view.set_start_button_enabled(True)

        # Debug print removed

    def _gather_all_settings(self) -> dict:
        """Helper to collect settings from all relevant presenters."""
        all_settings = {}

        file_io = self.presenters["file_io"]
        model_sel = self.presenters["model_selection"]
        proc_set = self.presenters["processing_settings"]

        input_path, output_path = file_io.get_paths()
        model_details = model_sel.get_current_selection()
        settings = proc_set.get_settings()

        all_settings.update({
            "input_paths": [input_path] if input_path else [], # Pass as a list
            "output_path": output_path,
        })
        # Add general processing settings
        all_settings.update(settings)

        # Add specific model settings based on selection
        internal_method_name = model_details.get('chosen_process_method')
        
        # Map internal method name back to UI key for presenter lookup
        ui_method_key = None
        if internal_method_name == ac.VR_ARCH_TYPE:
            ui_method_key = ac.VR_ARCH_MODELS_KEY
        elif internal_method_name == ac.MDX_ARCH_TYPE:
            ui_method_key = ac.MDX_NET_MODELS_KEY
        elif internal_method_name == ac.DEMUCS_ARCH_TYPE:
            ui_method_key = ac.DEMUCS_MODELS_KEY
        elif internal_method_name == ac.ENSEMBLE_MODE:
            ui_method_key = ac.ENSEMBLE_MODELS_KEY
            
        if ui_method_key and ui_method_key in self.presenters:
            all_settings.update(self.presenters[ui_method_key].get_settings())
        
        # Add model selection details last, so model_data can correctly pick up method and model
        all_settings.update(model_details)

        return all_settings

    @Slot()
    def handle_start_processing(self):
        """Gathers settings and tells the adapter to start processing."""
        if self._is_processing:
            self.view.append_log_message("Process is already running.")
            return

        self.view.clear_logs()
        self.view.append_log_message("Requesting process start...")
        self.view.set_start_button_enabled(False)
        self.view.set_start_button_text("Starting...")
        self._is_processing = True

        try:
            settings_dict = self._gather_all_settings()

            # Log collected settings
            self.view.append_log_message("--- Settings ---")
            for k, v in settings_dict.items():
                self.view.append_log_message(f"  {k}: {v}")
            self.view.append_log_message("------------------")

            if not settings_dict.get("input_paths") or not settings_dict.get("output_path"): # Check input_paths
                raise ValueError("Input and Output paths must be set!")

            # --- Call the Adapter ---
            self.adapter.start_processing(settings_dict)
            self.view.set_start_button_text("Processing...")
            self.view.set_progress_text("Waiting for process...")

        except Exception as e:
            self.view.append_log_message(f"ERROR: {e}")
            self.on_processing_finished(False, f"Setup Failed: {e}")

    @Slot(int, str)
    def on_progress_update(self, value: int, text: str):
        """Updates the view when the adapter sends progress."""
        if not self._is_processing: return  # Avoid updates after finishing
        # Debug print removed
        self.view.set_progress_value(value)
        self.view.set_progress_text(text)
        # Optionally add key progress steps to the log
        if value % 20 == 0 and value > 0:
            self.view.append_log_message(f"  Progress: {value}%...")

    @Slot(bool, str)
    def on_processing_finished(self, success: bool, message: str):
        """Updates the view when the adapter signals completion."""
        # Debug print removed
        self._is_processing = False
        self.view.append_log_message(message)
        self.view.set_progress_value(100 if success else 0)
        self.view.set_progress_text("Completed" if success else "Failed")
        self.view.set_start_button_enabled(True)
        self.view.set_start_button_text("Start Processing")
