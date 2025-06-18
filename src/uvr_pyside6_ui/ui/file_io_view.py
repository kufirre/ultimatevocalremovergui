"""File I/O view for UVR PySide6 application."""

from PySide6.QtCore import QSize, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class FileIOView(QWidget):
    """
    View for selecting input files/folders and the output folder.
    Supports both single file and batch processing modes.
    Emits signals when user interacts, and has slots to update display.
    """

    # Signals that the Presenter will connect to
    select_input_clicked = Signal()
    select_output_clicked = Signal()
    # Emit the new path when it changes, either by dialog or typing
    input_path_changed = Signal(str)
    output_path_changed = Signal(str)
    # Batch mode toggle
    batch_mode_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout for this widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Use group box margins instead

        # --- Input/Output Group Box ---
        io_group = QGroupBox("Select Input & Output")
        io_layout = QVBoxLayout(io_group)

        # Processing mode toggle
        mode_layout = QHBoxLayout()
        self.batch_mode_checkbox = QCheckBox("Batch Processing Mode")
        self.batch_mode_checkbox.setToolTip(
            "Enable to process multiple files in sequence"
        )
        self.batch_mode_checkbox.setChecked(False)  # Ensure single file mode is default
        self.batch_mode_checkbox.toggled.connect(self.batch_mode_toggled)
        mode_layout.addWidget(self.batch_mode_checkbox)
        mode_layout.addStretch()
        io_layout.addLayout(mode_layout)

        # Input Path Row
        input_hbox = QHBoxLayout()
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select Input File(s) or Folder...")
        self.input_path_edit.textChanged.connect(self.input_path_changed)

        self.select_input_button = QPushButton("Browse...")
        try:
            browse_icon = QIcon(":/uvr/img/File.png")
            if not browse_icon.isNull():
                self.select_input_button.setIcon(browse_icon)
                self.select_input_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.error(f"Error loading browse_icon for input button: {e}")
        self.select_input_button.clicked.connect(self.select_input_clicked)
        input_hbox.addWidget(self.input_path_edit)
        input_hbox.addWidget(self.select_input_button)
        io_layout.addLayout(input_hbox)

        # Output Path Row
        output_hbox = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Select Output Folder...")
        self.output_path_edit.textChanged.connect(self.output_path_changed)

        self.select_output_button = QPushButton("Browse...")
        try:
            browse_icon = QIcon(":/uvr/img/File.png")
            if not browse_icon.isNull():
                self.select_output_button.setIcon(browse_icon)
                self.select_output_button.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.error(f"Error loading browse_icon for output button: {e}")
        self.select_output_button.clicked.connect(self.select_output_clicked)
        output_hbox.addWidget(self.output_path_edit)
        output_hbox.addWidget(self.select_output_button)
        io_layout.addLayout(output_hbox)

        # Add the group box to the main layout
        layout.addWidget(io_group)
        self.setLayout(layout)

    # --- Slots (Called by the Presenter) ---

    @Slot(str)
    def set_input_path_text(self, path):
        """Updates the input path QLineEdit without emitting textChanged signal."""
        # Block signals temporarily to avoid loops if presenter sets text
        self.input_path_edit.blockSignals(True)
        self.input_path_edit.setText(path)
        self.input_path_edit.blockSignals(False)

    @Slot(str)
    def set_output_path_text(self, path):
        """Updates the output path QLineEdit without emitting textChanged signal."""
        self.output_path_edit.blockSignals(True)
        self.output_path_edit.setText(path)
        self.output_path_edit.blockSignals(False)

    @Slot(bool)
    def set_batch_mode(self, enabled: bool):
        """Set the batch mode checkbox state."""
        self.batch_mode_checkbox.blockSignals(True)
        self.batch_mode_checkbox.setChecked(enabled)
        self.batch_mode_checkbox.blockSignals(False)

    @Slot(bool)
    def set_input_controls_enabled(self, enabled: bool):
        """Enable or disable input path controls."""
        self.input_path_edit.setEnabled(enabled)
        self.select_input_button.setEnabled(enabled)

    @Slot()
    def show_input_file_dialog(self):
        """
        Shows a file dialog for input. Returns the selected path or None.
        The Presenter calls this, and we emit the path back if selected.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input Audio File",
            "",  # Start directory (can be set by presenter later)
            "Audio Files (*.wav *.mp3 *.flac *.m4a *.aac *.ogg *.wma);;All Files (*)",
        )
        if file_path:
            self.set_input_path_text(file_path)  # Update text
            self.input_path_changed.emit(file_path)  # Notify presenter explicitly

    @Slot()
    def show_output_folder_dialog(self):
        """Shows a folder dialog for output. Returns the selected path or None."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", ""  # Start directory
        )
        if folder_path:
            self.set_output_path_text(folder_path)  # Update text
            self.output_path_changed.emit(folder_path)  # Notify presenter explicitly

    def is_batch_mode_enabled(self) -> bool:
        """Check if batch mode is currently enabled."""
        return self.batch_mode_checkbox.isChecked()
