from typing import List

from PySide6.QtCore import QObject, Signal, Slot


class FileIOPresenter(QObject):
    """
    Presenter for the File I/O View. Connects View signals to
    handling logic and supports both single file and batch processing modes.
    """

    # Signals
    processing_mode_changed = Signal(str)  # "single" or "batch"

    def __init__(self, view, batch_presenter=None):
        super().__init__()
        self.view = view
        self.batch_presenter = batch_presenter

        # --- Store the state ---
        self._input_path = ""
        self._output_path = ""
        self._processing_mode = "single"  # "single" or "batch"

        # --- Connect signals from View to Presenter's slots ---
        self.view.select_input_clicked.connect(self.handle_select_input)
        self.view.select_output_clicked.connect(self.handle_select_output)
        self.view.input_path_changed.connect(self.handle_input_path_update)
        self.view.output_path_changed.connect(self.handle_output_path_update)

        # Connect to batch presenter if available
        if self.batch_presenter:
            self.batch_presenter.batch_ready_changed.connect(
                self._on_batch_ready_changed
            )

        # Ensure view starts in single file mode
        self._initialize_single_file_mode()

    @Slot()
    def handle_select_input(self):
        """Handles the 'Browse...' click for input."""
        if self._processing_mode == "single":
            # Single file mode - use the existing dialog
            self.view.show_input_file_dialog()
        else:
            # Batch mode - this shouldn't happen as the button should be hidden
            # but handle gracefully
            pass

    @Slot()
    def handle_select_output(self):
        """Handles the 'Browse...' click for output."""
        self.view.show_output_folder_dialog()

    @Slot(str)
    def handle_input_path_update(self, path):
        """Updates the internal state when input path changes."""
        if self._input_path != path:
            self._input_path = path

    @Slot(str)
    def handle_output_path_update(self, path):
        """Updates the internal state when output path changes."""
        if self._output_path != path:
            self._output_path = path

    def set_processing_mode(self, mode: str):
        """Set the processing mode: 'single' or 'batch'."""
        if mode not in ["single", "batch"]:
            raise ValueError("Mode must be 'single' or 'batch'")

        if self._processing_mode != mode:
            self._processing_mode = mode
            self.processing_mode_changed.emit(mode)

            # Update view based on mode
            if mode == "batch":
                self.view.set_input_path_text("Batch mode: Use batch queue below")
                self.view.input_path_edit.setEnabled(False)
                self.view.select_input_button.setEnabled(False)
            else:
                # Restore single file mode functionality
                self.view.input_path_edit.setEnabled(True)
                self.view.select_input_button.setEnabled(True)
                self.view.output_path_edit.setEnabled(True)
                self.view.select_output_button.setEnabled(True)

                # Restore proper placeholder text
                self.view.input_path_edit.setPlaceholderText("Select Input File...")

                # Restore input field text
                if self._input_path:
                    self.view.set_input_path_text(self._input_path)
                else:
                    self.view.set_input_path_text("")

    def get_processing_mode(self) -> str:
        """Get the current processing mode."""
        return self._processing_mode

    @Slot(bool)
    def _on_batch_ready_changed(self, is_ready: bool):
        """Handle batch ready state changes."""
        if self._processing_mode == "batch":
            if is_ready:
                # Get file count from batch presenter
                if self.batch_presenter:
                    file_count = len(self.batch_presenter.get_file_paths())
                    self.view.set_input_path_text(
                        f"Batch mode: {file_count} files ready"
                    )
            else:
                self.view.set_input_path_text("Batch mode: No files in queue")

    def get_paths(self) -> tuple:
        """Provides the current paths to other components."""
        if self._processing_mode == "single":
            return self._input_path, self._output_path
        else:
            # In batch mode, return the batch file paths
            if self.batch_presenter:
                file_paths = self.batch_presenter.get_file_paths()
                return file_paths, self._output_path
            else:
                return [], self._output_path

    def get_input_paths(self) -> List[str]:
        """Get input paths as a list (for compatibility with batch processing)."""
        if self._processing_mode == "single":
            return [self._input_path] if self._input_path else []
        else:
            if self.batch_presenter:
                return self.batch_presenter.get_file_paths()
            else:
                return []

    def get_output_path(self) -> str:
        """Get the output path."""
        return self._output_path

    def set_input_path(self, path: str):
        """Set the input path (for single file mode)."""
        if self._processing_mode == "single":
            self._input_path = path
            self.view.set_input_path_text(path)

    def set_output_path(self, path: str):
        """Set the output path."""
        self._output_path = path
        self.view.set_output_path_text(path)

    def is_ready_for_processing(self) -> bool:
        """Check if the file I/O is ready for processing."""
        if not self._output_path:
            return False

        if self._processing_mode == "single":
            return bool(self._input_path)
        else:
            if self.batch_presenter:
                return self.batch_presenter.is_batch_ready()
            else:
                return False

    def validate_paths(self) -> tuple:
        """Validate current paths. Returns (is_valid, error_message)."""
        if not self._output_path:
            return False, "Output folder not selected"

        if self._processing_mode == "single":
            if not self._input_path:
                return False, "Input file not selected"
            # Could add more validation here (file exists, format, etc.)
        else:
            if not self.batch_presenter or not self.batch_presenter.is_batch_ready():
                return False, "No files in batch queue"

        return True, ""

    def _initialize_single_file_mode(self):
        """Initialize the view for single file mode."""
        # Ensure batch mode checkbox is unchecked
        self.view.set_batch_mode(False)

        # Ensure input controls are enabled
        self.view.input_path_edit.setEnabled(True)
        self.view.select_input_button.setEnabled(True)

        # Ensure output controls are enabled
        self.view.output_path_edit.setEnabled(True)
        self.view.select_output_button.setEnabled(True)

        # Clear any batch mode text
        if not self._input_path:
            self.view.set_input_path_text("")

        # Set proper placeholder text
        self.view.input_path_edit.setPlaceholderText("Select Input File...")
        self.view.output_path_edit.setPlaceholderText("Select Output Folder...")
