from PySide6.QtCore import QObject, Slot

from ..core import app_constants as ac
from ..core.batch_processing_worker import BatchProcessingWorker

# No QTimer needed here now, as adapter handles it


class ExecutionControlPresenter(QObject):
    """
    Presenter for Execution Control. Gathers all settings,
    initiates processing via the adapter, and updates progress via signals.
    Supports both single file and batch processing modes.
    """

    def __init__(self, view, main_window_presenters, adapter):
        super().__init__()
        self.view = view
        self.presenters = main_window_presenters
        self.adapter = adapter

        self._is_processing = False
        self._batch_worker = None

        # --- Connect View Signals ---
        self.view.start_processing_clicked.connect(self.handle_start_processing)
        # TODO: Connect stop button later

        # --- Connect Adapter Signals (for single file processing) ---
        self.adapter.progress_updated.connect(self.on_progress_update)
        self.adapter.processing_finished.connect(self.on_processing_finished)

        # --- Connect Batch Processing Signals ---
        if ac.BATCH_FILE_PRESENTER_KEY in self.presenters:
            batch_presenter = self.presenters[ac.BATCH_FILE_PRESENTER_KEY]
            self._batch_worker = BatchProcessingWorker(
                batch_presenter.get_batch_manager(), 
                self.adapter
            )
            
            # Connect batch worker signals
            self._batch_worker.batch_started.connect(self._on_batch_started)
            self._batch_worker.batch_completed.connect(self._on_batch_completed)
            self._batch_worker.batch_cancelled.connect(self._on_batch_cancelled)
            self._batch_worker.overall_progress.connect(self.on_progress_update)

        self.view.set_progress_text(ac.STATUS_IDLE)
        self.view.set_start_button_enabled(True)

    def _gather_all_settings(self) -> dict:
        """Helper to collect settings from all relevant presenters."""
        all_settings = {}

        file_io = self.presenters[ac.FILE_IO_PRESENTER_KEY]
        model_sel = self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY]
        proc_set = self.presenters[ac.PROCESSING_SETTINGS_PRESENTER_KEY]

        # Get input paths (supports both single and batch modes)
        input_paths = file_io.get_input_paths()
        output_path = file_io.get_output_path()
        
        model_details = model_sel.get_current_selection()
        settings = proc_set.get_settings()

        all_settings.update(
            {
                "input_paths": input_paths,
                "output_path": output_path,
                "processing_mode": file_io.get_processing_mode(),
            }
        )

        # Add general processing settings, but map stem-only keys based on method
        internal_method_name = model_details.get("chosen_process_method")

        # Map stem-only keys to method-specific keys
        if internal_method_name == ac.DEMUCS_ARCH_TYPE:
            # For Demucs, use Demucs-specific keys
            all_settings.update(
                {
                    "use_gpu": settings.get("use_gpu", False),
                    "is_gpu_conversion": settings.get("use_gpu", False),
                    "normalize": settings.get("normalize", False),
                    "is_normalization": settings.get("normalize", False),
                    "output_format": settings.get("output_format", "WAV"),
                    "sample_mode": settings.get("sample_mode", False),
                    "is_primary_stem_only_Demucs": settings.get(
                        "primary_stem_only", False
                    ),
                    "is_secondary_stem_only_Demucs": settings.get(
                        "secondary_stem_only", False
                    ),
                    "save_format": settings.get("output_format", "WAV"),
                }
            )
        else:
            # For other methods, use generic keys
            all_settings.update(
                {
                    "use_gpu": settings.get("use_gpu", False),
                    "is_gpu_conversion": settings.get("use_gpu", False),
                    "normalize": settings.get("normalize", False),
                    "is_normalization": settings.get("normalize", False),
                    "output_format": settings.get("output_format", "WAV"),
                    "sample_mode": settings.get("sample_mode", False),
                    "is_primary_stem_only": settings.get("primary_stem_only", False),
                    "is_secondary_stem_only": settings.get(
                        "secondary_stem_only", False
                    ),
                    "save_format": settings.get("output_format", "WAV"),
                }
            )

        # Add specific model settings based on selection
        # Map internal method name back to UI key for presenter lookup
        ui_method_key = None
        if internal_method_name == ac.VR_ARCH_TYPE:
            ui_method_key = ac.VR_ARCH_PRESENTER_KEY
        elif internal_method_name == ac.MDX_ARCH_TYPE:
            ui_method_key = ac.MDX_NET_PRESENTER_KEY
        elif internal_method_name == ac.DEMUCS_ARCH_TYPE:
            ui_method_key = ac.DEMUCS_PRESENTER_KEY
        elif internal_method_name == ac.ENSEMBLE_MODE:
            ui_method_key = ac.ENSEMBLE_PRESENTER_KEY

        if ui_method_key and ui_method_key in self.presenters:
            all_settings.update(self.presenters[ui_method_key].get_settings())

        # Add stem information for proper VR processing
        if internal_method_name == ac.VR_ARCH_TYPE:
            # Get current stem names from model selection
            model_sel_presenter = self.presenters[ac.MODEL_SELECTION_PRESENTER_KEY]
            primary_stem, secondary_stem = model_sel_presenter._get_stems_for_model(
                model_sel_presenter._current_method, model_sel_presenter._current_model
            )
            all_settings.update({
                "primary_stem_text": primary_stem,
                "secondary_stem_text": secondary_stem,
            })

        # Add model selection details last, so model_data can correctly pick up method and model
        all_settings.update(model_details)

        return all_settings

    @Slot()
    def handle_start_processing(self):
        """Gathers settings and tells the adapter to start processing."""
        if self._is_processing:
            self.view.append_log_message(ac.MSG_PROCESS_ALREADY_RUNNING)
            return

        self.view.clear_logs()
        self.view.append_log_message(ac.MSG_REQUESTING_PROCESS_START)
        self.view.set_start_button_enabled(False)
        self.view.set_start_button_text(ac.BTN_STARTING)
        self._is_processing = True

        # Reset completion logging flag for new processing session
        if hasattr(self, "_logged_completion"):
            delattr(self, "_logged_completion")

        try:
            settings_dict = self._gather_all_settings()

            # Log collected settings
            self.view.append_log_message(ac.MSG_SETTINGS_HEADER)

            # Filter out unnecessary keys for cleaner logging
            keys_to_skip = {
                "ensemble_model",  # Usually empty or not needed in debug
                "chosen_process_method",  # Already shown as method
                "vr_model",
                "mdx_net_model",
                "demucs_model",  # Already shown as model name
            }

            for k, v in settings_dict.items():
                if k not in keys_to_skip and v:  # Skip empty values too
                    self.view.append_log_message(f"  {k}: {v}")
            self.view.append_log_message(ac.MSG_SETTINGS_FOOTER)

            if not settings_dict.get("input_paths") or not settings_dict.get(
                "output_path"
            ):
                raise ValueError(ac.MSG_INPUT_OUTPUT_REQUIRED)

            # Determine processing mode
            processing_mode = settings_dict.get("processing_mode", "single")
            
            if processing_mode == "batch":
                # Start batch processing
                self._start_batch_processing(settings_dict)
            else:
                # Start single file processing
                self._start_single_processing(settings_dict)

        except Exception as e:
            self.view.append_log_message(f"ERROR: {e}")
            self.on_processing_finished(False, f"Setup Failed: {e}")

    def _start_single_processing(self, settings_dict: dict):
        """Start single file processing."""
        self.view.append_log_message("Starting single file processing...")
        self.adapter.start_processing(settings_dict)
        self.view.set_start_button_text(ac.BTN_PROCESSING)
        self.view.set_progress_text(ac.STATUS_WAITING_PROCESS)

    def _start_batch_processing(self, settings_dict: dict):
        """Start batch processing."""
        if not self._batch_worker:
            raise ValueError("Batch processing not initialized")
            
        input_paths = settings_dict.get("input_paths", [])
        if not input_paths:
            raise ValueError("No files in batch queue")
            
        self.view.append_log_message(f"Starting batch processing of {len(input_paths)} files...")
        
        if self._batch_worker.start_batch_processing(settings_dict):
            self.view.set_start_button_text("Processing Batch")
            self.view.set_progress_text("Starting batch processing...")
        else:
            raise ValueError("Failed to start batch processing")

    @Slot(int)
    def _on_batch_started(self, total_files: int):
        """Handle batch processing started."""
        self.view.append_log_message(f"Batch processing started: {total_files} files in queue")

    @Slot(list)
    def _on_batch_completed(self, results: list):
        """Handle batch processing completed."""
        completed_count = sum(1 for r in results if r['status'] == 'completed')
        error_count = sum(1 for r in results if r['status'] == 'error')
        
        self.view.append_log_message(f"Batch processing completed:")
        self.view.append_log_message(f"  ✓ Successfully processed: {completed_count} files")
        if error_count > 0:
            self.view.append_log_message(f"  ✗ Files with errors: {error_count}")
            
        # Log individual results
        for result in results:
            if result['status'] == 'completed':
                self.view.append_log_message(f"  ✓ {result['display_name']}")
            elif result['status'] == 'error':
                self.view.append_log_message(f"  ✗ {result['display_name']}: {result.get('error_message', 'Unknown error')}")
        
        success = error_count == 0
        message = f"Batch completed: {completed_count} successful, {error_count} errors"
        self.on_processing_finished(success, message)

    @Slot()
    def _on_batch_cancelled(self):
        """Handle batch processing cancelled."""
        self.view.append_log_message("Batch processing cancelled")
        self.on_processing_finished(False, "Batch processing cancelled")

    @Slot(int, str)
    def on_progress_update(self, value: int, text: str):
        """Updates the view when the adapter sends progress."""
        if not self._is_processing:
            return

        self.view.set_progress_value(value)
        self.view.set_progress_text(text)

        # Only log progress at key milestones and avoid repetitive 100% logs
        if value == 100:
            # Only log 100% once per processing session
            if not hasattr(self, "_logged_completion"):
                self.view.append_log_message(f"  ✓ {ac.MSG_PROGRESS_COMPLETED}")
                self._logged_completion = True

    @Slot(bool, str)
    def on_processing_finished(self, success: bool, message: str):
        """Updates the view when the adapter signals completion."""
        self._is_processing = False

        # Reset completion logging flag for next processing session
        if hasattr(self, "_logged_completion"):
            delattr(self, "_logged_completion")

        self.view.set_start_button_enabled(True)
        self.view.set_start_button_text(ac.BTN_START_PROCESSING)

        if success:
            self.view.set_progress_text(ac.STATUS_PROCESSING_COMPLETE)
            self.view.set_progress_value(100)
            self.view.append_log_message(f"✓ {message}")
        else:
            self.view.set_progress_text(ac.STATUS_PROCESSING_ERROR)
            self.view.set_progress_value(0)
            self.view.append_log_message(f"✗ {message}")

    def is_processing(self) -> bool:
        """Check if processing is currently active."""
        return self._is_processing

    def cancel_processing(self):
        """Cancel the current processing operation."""
        if not self._is_processing:
            return
            
        file_io = self.presenters[ac.FILE_IO_PRESENTER_KEY]
        processing_mode = file_io.get_processing_mode()
        
        if processing_mode == "batch" and self._batch_worker:
            self._batch_worker.cancel_batch_processing()
        else:
            # Cancel single file processing (if adapter supports it)
            # TODO: Implement cancellation in adapter
            pass
