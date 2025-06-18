"""Batch processing manager for UVR PySide6 application."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from .logger_utils import get_logger

logger = get_logger(__name__)


class BatchFileItem:
    """Represents a single file in the batch processing queue."""
    
    def __init__(self, file_path: str, display_name: Optional[str] = None):
        self.file_path = Path(file_path)
        self.display_name = display_name or self.file_path.name
        self.status = "pending"  # pending, processing, completed, error
        self.error_message = ""
        self.output_files = []
        
    def __str__(self):
        return f"{self.display_name} ({self.status})"
        
    def __eq__(self, other):
        if isinstance(other, BatchFileItem):
            return self.file_path == other.file_path
        return False


class BatchManager(QObject):
    """Manages batch processing operations with file queue management."""
    
    # Signals
    file_added = Signal(BatchFileItem)
    file_removed = Signal(int)  # index
    files_reordered = Signal()
    batch_started = Signal(int)  # total files
    batch_completed = Signal(list)  # results
    batch_cancelled = Signal()
    file_processing_started = Signal(int, str)  # index, filename
    file_processing_completed = Signal(int, str, list)  # index, filename, output_files
    file_processing_error = Signal(int, str, str)  # index, filename, error
    
    def __init__(self):
        super().__init__()
        self._file_queue: List[BatchFileItem] = []
        self._is_processing = False
        self._current_file_index = -1
        self._supported_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
        
    def add_file(self, file_path: str) -> bool:
        """Add a single file to the batch queue."""
        try:
            file_path = Path(file_path)
            
            # Validate file exists and is supported
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False
                
            if file_path.suffix.lower() not in self._supported_extensions:
                logger.warning(f"Unsupported file format: {file_path.suffix}")
                return False
                
            # Check for duplicates
            new_item = BatchFileItem(str(file_path))
            if new_item in self._file_queue:
                logger.info(f"File already in queue: {file_path.name}")
                return False
                
            self._file_queue.append(new_item)
            self.file_added.emit(new_item)
            logger.debug(f"Added file to batch: {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding file to batch: {e}")
            return False
    
    def add_files(self, file_paths: List[str]) -> int:
        """Add multiple files to the batch queue. Returns number of files added."""
        added_count = 0
        for file_path in file_paths:
            if self.add_file(file_path):
                added_count += 1
        return added_count
    
    def add_folder(self, folder_path: str, recursive: bool = False) -> int:
        """Add all supported audio files from a folder. Returns number of files added."""
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                logger.warning(f"Invalid folder path: {folder_path}")
                return 0
                
            pattern = "**/*" if recursive else "*"
            audio_files = []
            
            for file_path in folder_path.glob(pattern):
                if file_path.is_file() and file_path.suffix.lower() in self._supported_extensions:
                    audio_files.append(str(file_path))
                    
            return self.add_files(audio_files)
            
        except Exception as e:
            logger.error(f"Error adding folder to batch: {e}")
            return 0
    
    def remove_file(self, index: int) -> bool:
        """Remove a file from the batch queue by index."""
        try:
            if 0 <= index < len(self._file_queue):
                removed_item = self._file_queue.pop(index)
                self.file_removed.emit(index)
                logger.debug(f"Removed file from batch: {removed_item.display_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing file from batch: {e}")
            return False
    
    def clear_queue(self) -> None:
        """Clear all files from the batch queue."""
        if self._is_processing:
            logger.warning("Cannot clear queue while processing")
            return
            
        self._file_queue.clear()
        self.files_reordered.emit()
        logger.debug("Cleared batch queue")
    
    def move_file(self, from_index: int, to_index: int) -> bool:
        """Move a file from one position to another in the queue."""
        try:
            if (0 <= from_index < len(self._file_queue) and 
                0 <= to_index < len(self._file_queue) and 
                from_index != to_index):
                
                item = self._file_queue.pop(from_index)
                self._file_queue.insert(to_index, item)
                self.files_reordered.emit()
                logger.debug(f"Moved file from {from_index} to {to_index}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error moving file in batch: {e}")
            return False
    
    def duplicate_file(self, index: int) -> bool:
        """Duplicate a file in the queue."""
        try:
            if 0 <= index < len(self._file_queue):
                original_item = self._file_queue[index]
                duplicate_item = BatchFileItem(
                    str(original_item.file_path),
                    f"{original_item.display_name} (Copy)"
                )
                self._file_queue.insert(index + 1, duplicate_item)
                self.file_added.emit(duplicate_item)
                logger.debug(f"Duplicated file: {original_item.display_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error duplicating file in batch: {e}")
            return False
    
    def get_queue(self) -> List[BatchFileItem]:
        """Get a copy of the current file queue."""
        return self._file_queue.copy()
    
    def get_queue_size(self) -> int:
        """Get the number of files in the queue."""
        return len(self._file_queue)
    
    def is_processing(self) -> bool:
        """Check if batch processing is currently active."""
        return self._is_processing
    
    def get_current_file_index(self) -> int:
        """Get the index of the currently processing file."""
        return self._current_file_index
    
    def get_supported_extensions(self) -> set:
        """Get the set of supported audio file extensions."""
        return self._supported_extensions.copy()
    
    def validate_queue(self) -> Tuple[bool, List[str]]:
        """Validate all files in the queue. Returns (is_valid, error_messages)."""
        errors = []
        
        if not self._file_queue:
            errors.append("No files in queue")
            
        for i, item in enumerate(self._file_queue):
            if not item.file_path.exists():
                errors.append(f"File {i+1} does not exist: {item.display_name}")
            elif not item.file_path.is_file():
                errors.append(f"Item {i+1} is not a file: {item.display_name}")
            elif item.file_path.suffix.lower() not in self._supported_extensions:
                errors.append(f"File {i+1} has unsupported format: {item.display_name}")
                
        return len(errors) == 0, errors
    
    def start_processing(self) -> bool:
        """Start batch processing. Returns True if started successfully."""
        if self._is_processing:
            logger.warning("Batch processing already in progress")
            return False
            
        is_valid, errors = self.validate_queue()
        if not is_valid:
            logger.error(f"Queue validation failed: {errors}")
            return False
            
        self._is_processing = True
        self._current_file_index = 0
        
        # Reset all file statuses
        for item in self._file_queue:
            item.status = "pending"
            item.error_message = ""
            item.output_files = []
            
        self.batch_started.emit(len(self._file_queue))
        logger.info(f"Started batch processing {len(self._file_queue)} files")
        return True
    
    def cancel_processing(self) -> None:
        """Cancel the current batch processing."""
        if self._is_processing:
            self._is_processing = False
            self._current_file_index = -1
            self.batch_cancelled.emit()
            logger.info("Batch processing cancelled")
    
    def mark_file_processing_started(self, index: int) -> None:
        """Mark a file as currently being processed."""
        if 0 <= index < len(self._file_queue):
            self._current_file_index = index
            self._file_queue[index].status = "processing"
            self.file_processing_started.emit(index, self._file_queue[index].display_name)
    
    def mark_file_processing_completed(self, index: int, output_files: List[str]) -> None:
        """Mark a file as successfully processed."""
        if 0 <= index < len(self._file_queue):
            self._file_queue[index].status = "completed"
            self._file_queue[index].output_files = output_files
            self.file_processing_completed.emit(
                index, 
                self._file_queue[index].display_name, 
                output_files
            )
    
    def mark_file_processing_error(self, index: int, error_message: str) -> None:
        """Mark a file as failed during processing."""
        if 0 <= index < len(self._file_queue):
            self._file_queue[index].status = "error"
            self._file_queue[index].error_message = error_message
            self.file_processing_error.emit(
                index, 
                self._file_queue[index].display_name, 
                error_message
            )
    
    def finish_processing(self) -> None:
        """Finish batch processing and emit results."""
        if self._is_processing:
            self._is_processing = False
            self._current_file_index = -1
            
            # Collect results
            results = []
            for i, item in enumerate(self._file_queue):
                results.append({
                    'index': i,
                    'file_path': str(item.file_path),
                    'display_name': item.display_name,
                    'status': item.status,
                    'error_message': item.error_message,
                    'output_files': item.output_files
                })
            
            self.batch_completed.emit(results)
            logger.info("Batch processing completed")
    
    def get_processing_statistics(self) -> Dict[str, int]:
        """Get statistics about the current batch processing state."""
        stats = {
            'total': len(self._file_queue),
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'error': 0
        }
        
        for item in self._file_queue:
            if item.status in stats:
                stats[item.status] += 1
                
        return stats 