from PySide6.QtCore import QObject, Slot, QTimer  # QTimer for mock processing


class ExecutionControlPresenter(QObject):
    """
    Presenter for Execution Control. Gathers all settings,
    initiates processing via the adapter, and updates progress.
    """

    def __init__(self, view, main_window_presenters):
        super().__init__()
        self.view = view
        self.presenters = main_window_presenters  # Access to other presenters
        # self.model = model # The uvr_core_adapter

        self._is_processing = False

        # --- Connect Signals ---
        self.view.start_processing_clicked.connect(self.handle_start_processing)

        # --- Initial State ---
        self.view.set_progress_text("Idle")
        self.view.set_start_button_enabled(True)  # Enable by default, maybe validate later

        print("ExecutionControlPresenter Initialized.")

    @Slot()
    def handle_start_processing(self):
        """Gathers settings and initiates the processing task."""
        if self._is_processing:
            print("Presenter: Already processing!")
            return

        self.view.clear_logs()
        self.view.append_log_message("Starting process...")
        self.view.set_start_button_enabled(False)
        self.view.set_start_button_text("Processing...")
        self._is_processing = True

        # --- Gather Settings from Other Presenters ---
        try:
            file_io = self.presenters["file_io"]
            model_sel = self.presenters["model_selection"]
            proc_set = self.presenters["processing_settings"]
            vr_set = self.presenters.get("vr_arch")  # Use .get for optional ones

            input_path, output_path = file_io.get_paths()
            model_details = model_sel.get_selection()
            settings = proc_set.get_settings()

            self.view.append_log_message(f"  Input: {input_path}")
            self.view.append_log_message(f"  Output: {output_path}")
            self.view.append_log_message(f"  Method: {model_details['method']}")
            self.view.append_log_message(f"  Model: {model_details['model']}")
            self.view.append_log_message(f"  GPU: {settings['use_gpu']}")
            self.view.append_log_message(f"  Format: {settings['output_format']}")

            if model_details['method'] == "VR Arch" and vr_set:
                vr_details = vr_set.get_settings()
                self.view.append_log_message(f"  VR Window: {vr_details['window_size']}")
                self.view.append_log_message(f"  VR Aggression: {vr_details['aggression']}")

            # TODO: Add validation here - are paths/models set?
            if not input_path or not output_path:
                raise ValueError("Input and Output paths must be set!")

            # --- Call the Model/Adapter (Mocked) ---
            self.view.append_log_message("Starting mock processing...")
            self.mock_process()  # Start the fake processing simulation

        except Exception as e:
            self.view.append_log_message(f"ERROR: {e}")
            self.processing_finished(success=False)

    def mock_process(self):
        """Simulates a processing task with progress updates."""
        self.progress_step = 0

        def update():
            self.progress_step += 10
            if self.progress_step <= 100:
                self.view.set_progress_value(self.progress_step)
                self.view.set_progress_text(f"Working on step {self.progress_step // 10}/10")
                self.view.append_log_message(f"  ... step {self.progress_step // 10} ...")
                QTimer.singleShot(500, update)  # Wait 0.5 sec
            else:
                self.processing_finished(success=True)

        # Start the first step
        QTimer.singleShot(100, update)  # Start after 0.1 sec

    def processing_finished(self, success=True):
        """Cleans up the UI after processing finishes or fails."""
        if success:
            self.view.append_log_message("Processing finished successfully!")
            self.view.set_progress_text("Completed")
            self.view.set_progress_value(100)
        else:
            self.view.append_log_message("Processing FAILED.")
            self.view.set_progress_text("Failed")
            self.view.set_progress_value(0)  # Or maybe show last known value

        self._is_processing = False
        self.view.set_start_button_enabled(True)
        self.view.set_start_button_text("Start Processing")
