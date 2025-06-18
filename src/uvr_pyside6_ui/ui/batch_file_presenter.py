"""Batch file processing presenter for UVR PySide6 application."""

from typing import List

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QMessageBox

from ..core.batch_manager import BatchManager
from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class BatchFilePresenter(QObject):
    """Presenter for batch file processing operations."""
    
    # Signals
    batch_ready_changed = Signal(bool)  # True if batch is ready to process
    processing_status_changed = Signal(bool)  # True if currently processing
    
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.batch_manager = BatchManager()
        
        self._setup_connections()
        
    def _setup_connections(self):
        """Set up signal connections between view and batch manager."""
        # View to presenter connections
        self.view.add_files_requested.connect(self.handle_add_files)
        self.view.add_folder_requested.connect(self.handle_add_folder)
        self.view.remove_selected_requested.connect(self.handle_remove_selected)
        self.view.clear_all_requested.connect(self.handle_clear_all)
        self.view.move_up_requested.connect(self.handle_move_up)
        self.view.move_down_requested.connect(self.handle_move_down)
        self.view.duplicate_selected_requested.connect(self.handle_duplicate_selected)
        self.view.files_dropped.connect(self.handle_files_dropped)
        
        # Batch manager to view connections
        self.batch_manager.file_added.connect(self.view.add_file_item)
        self.batch_manager.file_removed.connect(self.view.remove_file_item)
        self.batch_manager.files_reordered.connect(self._refresh_view)
        
        # Batch manager processing signals
        self.batch_manager.batch_started.connect(self._on_batch_started)
        self.batch_manager.batch_completed.connect(self._on_batch_completed)
        self.batch_manager.batch_cancelled.connect(self._on_batch_cancelled)
        self.batch_manager.file_processing_started.connect(self._on_file_processing_started)
        self.batch_manager.file_processing_completed.connect(self._on_file_processing_completed)
        self.batch_manager.file_processing_error.connect(self._on_file_processing_error)
        
    @Slot()
    def handle_add_files(self):
        """Handle add files request from view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        file_paths = self.view.show_file_dialog()
        if file_paths:
            added_count = self.batch_manager.add_files(file_paths)
            if added_count > 0:
                self.view.set_info_text(f"Added {added_count} file(s) to batch queue")
                QTimer.singleShot(3000, lambda: self.view.set_info_text(
                    "Add audio files to process multiple files in sequence"
                ))
            else:
                self.view.set_info_text("No valid audio files were added")
                QTimer.singleShot(3000, lambda: self.view.set_info_text(
                    "Add audio files to process multiple files in sequence"
                ))
            self._update_batch_ready_state()
    
    @Slot()
    def handle_add_folder(self):
        """Handle add folder request from view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        folder_path = self.view.show_folder_dialog()
        if folder_path:
            # Ask user about recursive search
            reply = QMessageBox.question(
                self.view,
                "Add Folder",
                "Include files from subfolders?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            recursive = reply == QMessageBox.StandardButton.Yes
            
            added_count = self.batch_manager.add_folder(folder_path, recursive)
            if added_count > 0:
                self.view.set_info_text(f"Added {added_count} file(s) from folder")
                QTimer.singleShot(3000, lambda: self.view.set_info_text(
                    "Add audio files to process multiple files in sequence"
                ))
            else:
                self.view.set_info_text("No audio files found in folder")
                QTimer.singleShot(3000, lambda: self.view.set_info_text(
                    "Add audio files to process multiple files in sequence"
                ))
            self._update_batch_ready_state()
    
    @Slot()
    def handle_remove_selected(self):
        """Handle remove selected files request from view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        selected_indices = self.view.get_selected_indices()
        if not selected_indices:
            return
            
        # Remove in reverse order to maintain indices
        removed_count = 0
        for index in sorted(selected_indices, reverse=True):
            if self.batch_manager.remove_file(index):
                removed_count += 1
                
        if removed_count > 0:
            self.view.set_info_text(f"Removed {removed_count} file(s) from queue")
            QTimer.singleShot(3000, lambda: self.view.set_info_text(
                "Add audio files to process multiple files in sequence"
            ))
        self._update_batch_ready_state()
    
    @Slot()
    def handle_clear_all(self):
        """Handle clear all files request from view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        if self.batch_manager.get_queue_size() == 0:
            return
            
        reply = QMessageBox.question(
            self.view,
            "Clear All Files",
            "Are you sure you want to remove all files from the batch queue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.batch_manager.clear_queue()
            self.view.clear_file_list()
            self.view.set_info_text("Cleared all files from queue")
            QTimer.singleShot(3000, lambda: self.view.set_info_text(
                "Add audio files to process multiple files in sequence"
            ))
            self._update_batch_ready_state()
    
    @Slot()
    def handle_move_up(self):
        """Handle move up request from view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        selected_indices = self.view.get_selected_indices()
        if not selected_indices:
            return
            
        # Move the first selected item up
        index = selected_indices[0]
        if index > 0:
            if self.batch_manager.move_file(index, index - 1):
                self.view.select_item(index - 1)
    
    @Slot()
    def handle_move_down(self):
        """Handle move down request from view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        selected_indices = self.view.get_selected_indices()
        if not selected_indices:
            return
            
        # Move the first selected item down
        index = selected_indices[0]
        if index < self.batch_manager.get_queue_size() - 1:
            if self.batch_manager.move_file(index, index + 1):
                self.view.select_item(index + 1)
    
    @Slot()
    def handle_duplicate_selected(self):
        """Handle duplicate selected files request from view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        selected_indices = self.view.get_selected_indices()
        if not selected_indices:
            return
            
        # Duplicate the first selected item
        index = selected_indices[0]
        if self.batch_manager.duplicate_file(index):
            self.view.set_info_text("Duplicated selected file")
            QTimer.singleShot(3000, lambda: self.view.set_info_text(
                "Add audio files to process multiple files in sequence"
            ))
            self._update_batch_ready_state()
    
    @Slot(list)
    def handle_files_dropped(self, file_paths: List[str]):
        """Handle files dropped on the view."""
        if self.batch_manager.is_processing():
            self._show_processing_warning()
            return
            
        added_count = self.batch_manager.add_files(file_paths)
        if added_count > 0:
            self.view.set_info_text(f"Added {added_count} file(s) via drag & drop")
            QTimer.singleShot(3000, lambda: self.view.set_info_text(
                "Add audio files to process multiple files in sequence"
            ))
        else:
            self.view.set_info_text("No valid audio files were added")
            QTimer.singleShot(3000, lambda: self.view.set_info_text(
                "Add audio files to process multiple files in sequence"
            ))
        self._update_batch_ready_state()
    
    def _show_processing_warning(self):
        """Show warning that operation cannot be performed during processing."""
        QMessageBox.warning(
            self.view,
            "Processing in Progress",
            "Cannot modify batch queue while processing is in progress."
        )
    
    def _refresh_view(self):
        """Refresh the entire view from the batch manager state."""
        self.view.clear_file_list()
        for file_item in self.batch_manager.get_queue():
            self.view.add_file_item(file_item)
        self._update_batch_ready_state()
    
    def _update_batch_ready_state(self):
        """Update the batch ready state and emit signal."""
        is_ready = (self.batch_manager.get_queue_size() > 0 and 
                   not self.batch_manager.is_processing())
        self.batch_ready_changed.emit(is_ready)
    
    @Slot(int)
    def _on_batch_started(self, total_files: int):
        """Handle batch processing started."""
        self.view.set_enabled(False)  # Disable UI during processing
        self.view.set_info_text(f"Processing {total_files} files...")
        self.processing_status_changed.emit(True)
        logger.info(f"Batch processing started: {total_files} files")
    
    @Slot(list)
    def _on_batch_completed(self, results: list):
        """Handle batch processing completed."""
        self.view.set_enabled(True)  # Re-enable UI
        self.processing_status_changed.emit(False)
        
        # Count results
        completed = sum(1 for r in results if r['status'] == 'completed')
        errors = sum(1 for r in results if r['status'] == 'error')
        
        if errors == 0:
            self.view.set_info_text(f"Batch completed successfully: {completed} files processed")
        else:
            self.view.set_info_text(f"Batch completed: {completed} successful, {errors} errors")
        
        # Show completion dialog
        if errors == 0:
            QMessageBox.information(
                self.view,
                "Batch Processing Complete",
                f"Successfully processed {completed} files."
            )
        else:
            QMessageBox.warning(
                self.view,
                "Batch Processing Complete",
                f"Processed {completed} files successfully.\n{errors} files had errors."
            )
        
        self._update_batch_ready_state()
        logger.info(f"Batch processing completed: {completed} successful, {errors} errors")
    
    @Slot()
    def _on_batch_cancelled(self):
        """Handle batch processing cancelled."""
        self.view.set_enabled(True)  # Re-enable UI
        self.processing_status_changed.emit(False)
        self.view.set_info_text("Batch processing cancelled")
        self._update_batch_ready_state()
        logger.info("Batch processing cancelled")
    
    @Slot(int, str)
    def _on_file_processing_started(self, index: int, filename: str):
        """Handle individual file processing started."""
        self.view.update_file_status(index, "processing")
        self.view.scroll_to_item(index)
        logger.debug(f"Started processing file {index + 1}: {filename}")
    
    @Slot(int, str, list)
    def _on_file_processing_completed(self, index: int, filename: str, output_files: list):
        """Handle individual file processing completed."""
        self.view.update_file_status(index, "completed")
        logger.debug(f"Completed processing file {index + 1}: {filename}")
    
    @Slot(int, str, str)
    def _on_file_processing_error(self, index: int, filename: str, error: str):
        """Handle individual file processing error."""
        self.view.update_file_status(index, "error")
        logger.warning(f"Error processing file {index + 1} ({filename}): {error}")
    
    # Public methods for external control
    
    def get_batch_manager(self) -> BatchManager:
        """Get the batch manager instance."""
        return self.batch_manager
    
    def is_batch_ready(self) -> bool:
        """Check if batch is ready for processing."""
        return (self.batch_manager.get_queue_size() > 0 and 
                not self.batch_manager.is_processing())
    
    def is_processing(self) -> bool:
        """Check if batch processing is currently active."""
        return self.batch_manager.is_processing()
    
    def get_file_paths(self) -> List[str]:
        """Get list of file paths in the current batch queue."""
        return [str(item.file_path) for item in self.batch_manager.get_queue()]
    
    def start_batch_processing(self) -> bool:
        """Start batch processing. Returns True if started successfully."""
        return self.batch_manager.start_processing()
    
    def cancel_batch_processing(self):
        """Cancel the current batch processing."""
        self.batch_manager.cancel_processing()
    
    def get_processing_statistics(self) -> dict:
        """Get current processing statistics."""
        return self.batch_manager.get_processing_statistics() 