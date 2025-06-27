"""Batch file management view for UVR PySide6 application."""

import os
from typing import List

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.batch_manager import BatchFileItem
from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class BatchFileListWidget(QListWidget):
    """Custom list widget with drag-and-drop support for batch files."""

    files_dropped = Signal(list)  # List of file paths
    item_moved = Signal(int, int)  # from_index, to_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Enable drag and drop from external sources
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            # Check if any of the URLs are audio files
            audio_extensions = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma"}
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if any(file_path.lower().endswith(ext) for ext in audio_extensions):
                        event.acceptProposedAction()
                        return
        elif event.mimeData().hasText():
            # Accept text drops (might be file paths)
            event.acceptProposedAction()
            return

        # Also accept internal moves
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """Handle drag move events."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events."""
        if event.mimeData().hasUrls():
            # External file drop
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if os.path.isfile(file_path):
                        file_paths.append(file_path)
                    elif os.path.isdir(file_path):
                        # Add all audio files from directory
                        audio_extensions = {
                            ".wav",
                            ".mp3",
                            ".flac",
                            ".m4a",
                            ".aac",
                            ".ogg",
                            ".wma",
                        }
                        for root, dirs, files in os.walk(file_path):
                            for file in files:
                                if any(
                                    file.lower().endswith(ext)
                                    for ext in audio_extensions
                                ):
                                    file_paths.append(os.path.join(root, file))

            if file_paths:
                self.files_dropped.emit(file_paths)
                event.acceptProposedAction()
        else:
            # Internal move
            super().dropEvent(event)


class BatchFileView(QWidget):
    """View for managing batch file processing queue."""

    # Signals
    add_files_requested = Signal()
    add_folder_requested = Signal()
    remove_selected_requested = Signal()
    clear_all_requested = Signal()
    move_up_requested = Signal()
    move_down_requested = Signal()
    duplicate_selected_requested = Signal()
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main group box
        self.group_box = QGroupBox("Batch File Queue")
        group_layout = QVBoxLayout(self.group_box)

        # Info label
        self.info_label = QLabel(
            "Add audio files to process multiple files in sequence"
        )
        self.info_label.setStyleSheet("color: #bdc3c7; font-style: italic;")
        group_layout.addWidget(self.info_label)

        # Button row for file operations
        button_layout = QHBoxLayout()

        self.add_files_button = QPushButton("Add Files...")
        self.add_files_button.setToolTip(
            "Add individual audio files to the batch queue"
        )
        try:
            self.add_files_button.setIcon(QIcon(":/uvr/img/File.png"))
            self.add_files_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.debug(f"Could not load icon for add files button: {e}")

        self.add_folder_button = QPushButton("Add Folder...")
        self.add_folder_button.setToolTip(
            "Add all audio files from a folder to the batch queue"
        )

        self.clear_button = QPushButton("Clear All")
        self.clear_button.setToolTip("Remove all files from the batch queue")
        try:
            self.clear_button.setIcon(QIcon(":/uvr/img/clear.png"))
            self.clear_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.debug(f"Could not load icon for clear button: {e}")

        button_layout.addWidget(self.add_files_button)
        button_layout.addWidget(self.add_folder_button)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)

        group_layout.addLayout(button_layout)

        # File list widget
        self.file_list = BatchFileListWidget()
        self.file_list.setMinimumHeight(200)
        self.file_list.setAlternatingRowColors(True)
        group_layout.addWidget(self.file_list)

        # Control buttons row
        control_layout = QHBoxLayout()

        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.setToolTip("Move selected files up in the queue")
        try:
            self.move_up_button.setIcon(QIcon(":/uvr/img/up.png"))
            self.move_up_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.debug(f"Could not load icon for move up button: {e}")

        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.setToolTip("Move selected files down in the queue")
        try:
            self.move_down_button.setIcon(QIcon(":/uvr/img/down.png"))
            self.move_down_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.debug(f"Could not load icon for move down button: {e}")

        self.duplicate_button = QPushButton("Duplicate")
        self.duplicate_button.setToolTip("Duplicate selected files in the queue")
        try:
            self.duplicate_button.setIcon(QIcon(":/uvr/img/copy.png"))
            self.duplicate_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.debug(f"Could not load icon for duplicate button: {e}")

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.setToolTip("Remove selected files from the queue")

        control_layout.addWidget(self.move_up_button)
        control_layout.addWidget(self.move_down_button)
        control_layout.addWidget(self.duplicate_button)
        control_layout.addStretch()
        control_layout.addWidget(self.remove_button)

        group_layout.addLayout(control_layout)

        # Status label
        self.status_label = QLabel("No files in queue")
        self.status_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        group_layout.addWidget(self.status_label)

        layout.addWidget(self.group_box)

        # Initially disable control buttons
        self._update_button_states()

    def _setup_connections(self):
        """Set up signal connections."""
        self.add_files_button.clicked.connect(self.add_files_requested)
        self.add_folder_button.clicked.connect(self.add_folder_requested)
        self.clear_button.clicked.connect(self.clear_all_requested)
        self.move_up_button.clicked.connect(self.move_up_requested)
        self.move_down_button.clicked.connect(self.move_down_requested)
        self.duplicate_button.clicked.connect(self.duplicate_selected_requested)
        self.remove_button.clicked.connect(self.remove_selected_requested)

        # File list connections
        self.file_list.files_dropped.connect(self.files_dropped)
        self.file_list.itemSelectionChanged.connect(self._update_button_states)

    def _update_button_states(self):
        """Update button enabled/disabled states based on selection."""
        has_selection = len(self.file_list.selectedItems()) > 0
        has_items = self.file_list.count() > 0

        self.move_up_button.setEnabled(has_selection and has_items)
        self.move_down_button.setEnabled(has_selection and has_items)
        self.duplicate_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)
        self.clear_button.setEnabled(has_items)

    @Slot(BatchFileItem)
    def add_file_item(self, file_item: BatchFileItem):
        """Add a file item to the list."""
        list_item = QListWidgetItem()
        list_item.setText(f"{file_item.display_name}")
        list_item.setData(Qt.ItemDataRole.UserRole, file_item)

        # Set status-based styling
        self._update_item_appearance(list_item, file_item.status)

        self.file_list.addItem(list_item)
        self._update_status_label()
        self._update_button_states()

    @Slot(int)
    def remove_file_item(self, index: int):
        """Remove a file item from the list by index."""
        if 0 <= index < self.file_list.count():
            self.file_list.takeItem(index)
            self._update_status_label()
            self._update_button_states()

    @Slot()
    def clear_file_list(self):
        """Clear all items from the file list."""
        self.file_list.clear()
        self._update_status_label()
        self._update_button_states()

    def _update_item_appearance(self, list_item: QListWidgetItem, status: str):
        """Update the appearance of a list item based on its status."""
        file_item = list_item.data(Qt.ItemDataRole.UserRole)
        if not file_item:
            return

        # Update text with status indicator
        if status == "pending":
            list_item.setText(f"⏳ {file_item.display_name}")
            list_item.setToolTip(f"Pending: {file_item.file_path}")
        elif status == "processing":
            list_item.setText(f"🔄 {file_item.display_name}")
            list_item.setToolTip(f"Processing: {file_item.file_path}")
        elif status == "completed":
            list_item.setText(f"✅ {file_item.display_name}")
            list_item.setToolTip(f"Completed: {file_item.file_path}")
        elif status == "error":
            list_item.setText(f"❌ {file_item.display_name}")
            list_item.setToolTip(f"Error: {file_item.error_message}")
        else:
            list_item.setText(file_item.display_name)
            list_item.setToolTip(str(file_item.file_path))

    @Slot(int, str)
    def update_file_status(self, index: int, status: str):
        """Update the status of a file item."""
        if 0 <= index < self.file_list.count():
            list_item = self.file_list.item(index)
            if list_item:
                file_item = list_item.data(Qt.ItemDataRole.UserRole)
                if file_item:
                    file_item.status = status
                    self._update_item_appearance(list_item, status)

    def _update_status_label(self):
        """Update the status label with current queue information."""
        count = self.file_list.count()
        if count == 0:
            self.status_label.setText("No files in queue")
        elif count == 1:
            self.status_label.setText("1 file in queue")
        else:
            self.status_label.setText(f"{count} files in queue")

    def get_selected_indices(self) -> List[int]:
        """Get the indices of currently selected items."""
        indices = []
        for i in range(self.file_list.count()):
            if self.file_list.item(i).isSelected():
                indices.append(i)
        return indices

    def select_item(self, index: int):
        """Select an item by index."""
        if 0 <= index < self.file_list.count():
            self.file_list.setCurrentRow(index)

    def scroll_to_item(self, index: int):
        """Scroll to make an item visible."""
        if 0 <= index < self.file_list.count():
            item = self.file_list.item(index)
            if item:
                self.file_list.scrollToItem(item)

    @Slot(str)
    def set_info_text(self, text: str):
        """Set the info label text."""
        self.info_label.setText(text)

    @Slot(bool)
    def set_enabled(self, enabled: bool):
        """Enable or disable the entire widget."""
        self.group_box.setEnabled(enabled)

    def show_file_dialog(self) -> List[str]:
        """Show file dialog for selecting multiple audio files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files for Batch Processing",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.wma);;All Files (*)",
        )
        return file_paths

    def show_folder_dialog(self) -> str:
        """Show folder dialog for selecting a folder."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder Containing Audio Files", ""
        )
        return folder_path
