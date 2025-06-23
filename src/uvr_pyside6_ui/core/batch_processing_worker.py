"""Batch processing worker for UVR PySide6 application."""

import os
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import QObject, Signal, Slot

from .batch_manager import BatchManager
from .logger_utils import get_logger
from .processing_worker import ProcessingThread
from .uvr_core_adapter import UVRCoreAdapter

logger = get_logger(__name__)


class BatchProcessingWorker(QObject):
    """Worker for processing multiple files in batch mode."""

    # Signals
    batch_started = Signal(int)  # total files
    batch_progress = Signal(int, int)  # current_file_index, total_files
    file_started = Signal(int, str)  # file_index, filename
    file_completed = Signal(int, str, list)  # file_index, filename, output_files
    file_error = Signal(int, str, str)  # file_index, filename, error_message
    batch_completed = Signal(list)  # results list
    batch_cancelled = Signal()
    overall_progress = Signal(int, str)  # progress_value, status_text

    def __init__(self, batch_manager: BatchManager, adapter: UVRCoreAdapter):
        super().__init__()
        self.batch_manager = batch_manager
        self.adapter = adapter
        self._is_processing = False
        self._should_cancel = False
        self._current_file_index = 0
        self._total_files = 0
        self._settings_template = {}
        self._processing_thread = None

    def start_batch_processing(self, settings_template: Dict) -> bool:
        """Start batch processing with the given settings template."""
        if self._is_processing:
            logger.warning("Batch processing already in progress")
            return False

        if not self.batch_manager.start_processing():
            logger.error("Failed to start batch processing in batch manager")
            return False

        self._is_processing = True
        self._should_cancel = False
        self._current_file_index = 0
        self._settings_template = settings_template.copy()

        file_queue = self.batch_manager.get_queue()
        self._total_files = len(file_queue)

        if self._total_files == 0:
            logger.warning("No files to process")
            self._finish_batch()
            return False

        logger.info(f"Starting batch processing of {self._total_files} files")
        self.batch_started.emit(self._total_files)
        self._process_next_file()
        return True

    def cancel_batch_processing(self):
        """Cancel the current batch processing."""
        if not self._is_processing:
            return

        self._should_cancel = True
        logger.info("Batch processing cancellation requested")

        # Cancel current processing if active
        if self._processing_thread and self._processing_thread.isRunning():
            self._processing_thread.cancel_processing()
        else:
            self._handle_batch_cancelled()

    def _process_next_file(self):
        """Process the next file in the queue."""
        if self._should_cancel:
            self._handle_batch_cancelled()
            return

        if self._current_file_index >= self._total_files:
            self._finish_batch()
            return

        file_queue = self.batch_manager.get_queue()
        if self._current_file_index >= len(file_queue):
            logger.error("File index out of range")
            self._finish_batch()
            return

        current_file = file_queue[self._current_file_index]

        try:
            # Mark file as processing started
            self.batch_manager.mark_file_processing_started(self._current_file_index)
            self.file_started.emit(self._current_file_index, current_file.display_name)
            self.batch_progress.emit(self._current_file_index + 1, self._total_files)

            # Calculate overall progress (file-level)
            file_progress = int((self._current_file_index / self._total_files) * 100)
            self.overall_progress.emit(
                file_progress,
                f"Processing file {self._current_file_index + 1}/{self._total_files}: {current_file.display_name}",
            )

            # Prepare settings for this file
            file_settings = self._prepare_file_settings(current_file)

            # Start processing this file
            self._start_file_processing(file_settings)

        except Exception as e:
            logger.error(
                f"Error starting processing for file {self._current_file_index}: {e}"
            )
            self._handle_file_error(str(e))

    def _prepare_file_settings(self, file_item) -> Dict:
        """Prepare settings for processing a specific file."""
        settings = self._settings_template.copy()

        # Update input path for this specific file
        settings["input_paths"] = [str(file_item.file_path)]

        # Generate unique output names if needed
        output_path = settings.get("output_path", "")
        if output_path:
            # Ensure output directory exists
            os.makedirs(output_path, exist_ok=True)

        return settings

    def _start_file_processing(self, settings: Dict):
        """Start processing a single file using the existing processing system."""
        try:
            # Create a new processing thread for this file
            self._processing_thread = ProcessingThread(settings)

            # Connect signals
            self._processing_thread.progress_updated.connect(
                self._on_file_progress_updated
            )
            self._processing_thread.processing_finished.connect(
                self._on_file_processing_finished
            )

            # Start the thread
            self._processing_thread.start()

        except Exception as e:
            logger.error(f"Error creating processing thread: {e}")
            self._handle_file_error(str(e))

    @Slot(int, str)
    def _on_file_progress_updated(self, progress: int, message: str):
        """Handle progress updates from the current file processing."""
        if self._should_cancel:
            return

        # Calculate overall progress including file-level and within-file progress
        files_completed = self._current_file_index
        current_file_progress = progress / 100.0  # Convert to 0-1 range

        overall_progress = (
            (files_completed + current_file_progress) / self._total_files
        ) * 100
        overall_progress = min(
            int(overall_progress), 99
        )  # Cap at 99% until truly complete

        current_file = self.batch_manager.get_queue()[self._current_file_index]
        status_text = f"File {self._current_file_index + 1}/{self._total_files}: {current_file.display_name} - {message}"

        self.overall_progress.emit(overall_progress, status_text)

    @Slot(bool, str)
    def _on_file_processing_finished(self, success: bool, message: str):
        """Handle completion of a single file processing."""
        if self._should_cancel:
            self._handle_batch_cancelled()
            return

        current_file = self.batch_manager.get_queue()[self._current_file_index]

        if success:
            # Extract output files from the processing results
            output_files = self._extract_output_files(current_file)

            # Mark file as completed
            self.batch_manager.mark_file_processing_completed(
                self._current_file_index, output_files
            )
            self.file_completed.emit(
                self._current_file_index, current_file.display_name, output_files
            )
            logger.info(
                f"Completed processing file {self._current_file_index + 1}: {current_file.display_name}"
            )
        else:
            # Mark file as error
            self._handle_file_error(message)

        # Clean up processing thread
        if self._processing_thread:
            self._processing_thread.deleteLater()
            self._processing_thread = None

        # Move to next file
        self._current_file_index += 1
        self._process_next_file()

    def _extract_output_files(self, file_item) -> List[str]:
        """Extract the list of output files generated for a processed file."""
        output_files = []

        try:
            # Get the output directory from settings
            output_path = self._settings_template.get("output_path", "")
            if not output_path:
                return output_files

            output_dir = Path(output_path)
            if not output_dir.exists():
                return output_files

            # Get the base filename without extension
            input_path = Path(file_item.file_path)
            base_name = input_path.stem

            # Common output file patterns based on processing type
            # These patterns match what UVR typically generates
            common_patterns = [
                f"{base_name}_(Vocals).wav",
                f"{base_name}_(Instrumental).wav",
                f"{base_name}_(Drums).wav",
                f"{base_name}_(Bass).wav",
                f"{base_name}_(Other).wav",
                f"{base_name}_vocals.wav",
                f"{base_name}_instrumental.wav",
                f"{base_name}_drums.wav",
                f"{base_name}_bass.wav",
                f"{base_name}_other.wav",
            ]

            # Check for files matching common patterns
            for pattern in common_patterns:
                output_file = output_dir / pattern
                if output_file.exists():
                    output_files.append(str(output_file))

            # If no common patterns found, look for any files with the base name
            if not output_files:
                for output_file in output_dir.glob(f"{base_name}*"):
                    if output_file.is_file() and output_file.suffix.lower() in [
                        ".wav",
                        ".flac",
                        ".mp3",
                    ]:
                        output_files.append(str(output_file))

            logger.debug(
                f"Found {len(output_files)} output files for {file_item.display_name}"
            )

        except Exception as e:
            logger.error(
                f"Error extracting output files for {file_item.display_name}: {e}"
            )

        return output_files

    def _handle_file_error(self, error_message: str):
        """Handle an error for the current file."""
        current_file = self.batch_manager.get_queue()[self._current_file_index]

        # Mark file as error
        self.batch_manager.mark_file_processing_error(
            self._current_file_index, error_message
        )
        self.file_error.emit(
            self._current_file_index, current_file.display_name, error_message
        )

        logger.error(
            f"Error processing file {self._current_file_index + 1} ({current_file.display_name}): {error_message}"
        )

        # Clean up processing thread
        if self._processing_thread:
            self._processing_thread.deleteLater()
            self._processing_thread = None

        # Move to next file (continue processing despite error)
        self._current_file_index += 1
        self._process_next_file()

    def _handle_batch_cancelled(self):
        """Handle batch processing cancellation."""
        self._is_processing = False
        self._should_cancel = False

        # Clean up processing thread
        if self._processing_thread:
            self._processing_thread.deleteLater()
            self._processing_thread = None

        self.batch_manager.cancel_processing()
        self.batch_cancelled.emit()
        self.overall_progress.emit(0, "Batch processing cancelled")

        logger.info("Batch processing cancelled")

    def _finish_batch(self):
        """Finish batch processing and emit results."""
        self._is_processing = False

        # Clean up processing thread
        if self._processing_thread:
            self._processing_thread.deleteLater()
            self._processing_thread = None

        # Finish batch processing in manager
        self.batch_manager.finish_processing()

        # Get final statistics
        stats = self.batch_manager.get_processing_statistics()

        # Emit completion signal
        results = []
        for i, file_item in enumerate(self.batch_manager.get_queue()):
            results.append(
                {
                    "index": i,
                    "file_path": str(file_item.file_path),
                    "display_name": file_item.display_name,
                    "status": file_item.status,
                    "error_message": file_item.error_message,
                    "output_files": file_item.output_files,
                }
            )

        self.batch_completed.emit(results)
        self.overall_progress.emit(
            100,
            f"Batch completed: {stats['completed']} successful, {stats['error']} errors",
        )

        logger.info(
            f"Batch processing finished: {stats['completed']} successful, {stats['error']} errors"
        )

    def is_processing(self) -> bool:
        """Check if batch processing is currently active."""
        return self._is_processing

    def get_current_file_index(self) -> int:
        """Get the index of the currently processing file."""
        return self._current_file_index

    def get_total_files(self) -> int:
        """Get the total number of files to process."""
        return self._total_files
