from PySide6.QtCore import QObject, Signal, QTimer, QThread  # Import QObject & Signal
import time

# --- Mock Data ---
# We'll keep this here temporarily, representing what the 'real' adapter would fetch.
MOCK_AVAILABLE_MODELS = {
    "VR Arch": ["VR Model 1", "VR Model 2 (HP)", "VR 5_1_Arch"],
    "MDX-Net": ["MDX23 Main", "UVR-MDX-NET Inst HQ 1", "Kim Vocal 1"],
    "Demucs": ["htdemucs", "htdemucs_ft", "mdx_extra"],
    "Ensemble": []
}


# --- Mock Worker for Threading Simulation ---
class MockProcessingWorker(QObject):
    """
    A QObject worker that simulates processing in a thread.
    Emits signals for progress.
    """
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)

    def __init__(self, settings_dict):
        super().__init__()
        self.settings = settings_dict
        self._is_running = True

    def run(self):
        """Simulates the long-running process."""
        print("Adapter Worker: Starting simulation...")
        try:
            for i in range(11):  # Simulate 10 steps
                if not self._is_running:
                    print("Adapter Worker: Stop requested.")
                    self.processing_finished.emit(False, "Processing Canceled")
                    return

                progress = i * 10
                message = f"Processing step {i}/10..."
                print(f"Adapter Worker: Emitting progress {progress}% - {message}")
                self.progress_updated.emit(progress, message)
                time.sleep(0.5)  # Simulate work

            print("Adapter Worker: Simulation finished.")
            self.processing_finished.emit(True, "Processing Completed Successfully!")

        except Exception as e:
            print(f"Adapter Worker: Error - {e}")
            self.processing_finished.emit(False, f"Error during processing: {e}")

    def stop(self):
        """Requests the worker to stop."""
        self._is_running = False


# --- The Adapter Class ---
class UVRCoreAdapter(QObject):
    """
    Acts as an interface/facade to the core UVR processing logic.
    Inherits QObject to leverage signals/slots.
    """
    # Signals to communicate back to the UI (Presenters)
    progress_updated = Signal(int, str)  # (percentage, message)
    processing_finished = Signal(bool, str)  # (success_flag, final_message)
    models_updated = Signal(dict)  # (Optional: For dynamic model loading)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processing_thread = None
        self.worker = None
        print("UVRCoreAdapter Initialized.")

    def get_available_methods(self) -> list:
        """(Mocked) Returns a list of available processing methods."""
        print("Adapter: Getting available methods (mocked).")
        return list(MOCK_AVAILABLE_MODELS.keys())

    def get_available_models(self, method_name: str) -> list:
        """(Mocked) Returns a list of models for a given method."""
        print(f"Adapter: Getting models for {method_name} (mocked).")
        return MOCK_AVAILABLE_MODELS.get(method_name, [])

    def start_processing(self, settings_dict: dict):
        """
        Starts the UVR processing in a separate thread.
        Takes a dictionary containing all settings.
        """
        print(f"Adapter: Received request to start processing with settings:")
        for key, value in settings_dict.items():
            print(f"  - {key}: {value}")

        if self.processing_thread and self.processing_thread.isRunning():
            print("Adapter: Processing is already running.")
            return

        # 1. Create a worker
        self.worker = MockProcessingWorker(settings_dict)
        # 2. Create a thread
        self.processing_thread = QThread()
        # 3. Move worker to thread
        self.worker.moveToThread(self.processing_thread)
        # 4. Connect signals:
        #    - Thread started -> Worker's run method
        self.processing_thread.started.connect(self.worker.run)
        #    - Worker's signals -> Adapter's signals (to re-emit)
        self.worker.progress_updated.connect(self.progress_updated)
        self.worker.processing_finished.connect(self.processing_finished)
        #    - Worker finished -> Thread quit
        self.worker.processing_finished.connect(self.processing_thread.quit)
        #    - Worker/Thread cleanup
        self.worker.processing_finished.connect(self.worker.deleteLater)
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)

        # 5. Start the thread
        print("Adapter: Starting processing thread...")
        self.processing_thread.start()

    def stop_processing(self):
        """Stops the currently running process (if any)."""
        if self.worker and self.processing_thread and self.processing_thread.isRunning():
            print("Adapter: Requesting worker to stop...")
            self.worker.stop()
        else:
            print("Adapter: No process running to stop.")

    # TODO: Add methods for validation, getting backend details, etc.
