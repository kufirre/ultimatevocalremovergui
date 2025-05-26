from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QHBoxLayout,
    QLineEdit, QPushButton, QFileDialog
)
from PySide6.QtCore import Signal, Slot


class FileIOView(QWidget):
    """
    View for selecting input files/folders and the output folder.
    Emits signals when user interacts, and has slots to update display.
    It should be 'passive' - it doesn't contain complex logic.
    """
    # Signals that the Presenter will connect to
    select_input_clicked = Signal()
    select_output_clicked = Signal()
    # Emit the new path when it changes, either by dialog or typing
    input_path_changed = Signal(str)
    output_path_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout for this widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Use group box margins instead

        # --- Input/Output Group Box ---
        io_group = QGroupBox("Select Input & Output")
        io_layout = QVBoxLayout(io_group)

        # Input Path Row
        input_hbox = QHBoxLayout()
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Select Input File(s) or Folder...")
        # Connect textChanged to our signal
        self.input_path_edit.textChanged.connect(self.input_path_changed)
        self.select_input_button = QPushButton("Browse...")
        # Connect clicked to our signal
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
        self.select_output_button.clicked.connect(self.select_output_clicked)
        output_hbox.addWidget(self.output_path_edit)
        output_hbox.addWidget(self.select_output_button)
        io_layout.addLayout(output_hbox)

        # Add the group box to the main layout
        layout.addWidget(io_group)
        self.setLayout(layout)

        print("FileIOView Initialized.")

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

    @Slot()
    def show_input_file_dialog(self):
        """
        Shows a file dialog for input. Returns the selected path or None.
        The Presenter calls this, and we emit the path back if selected.
        """
        # We can expand this later to support multiple files/folders based on UVR needs
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input Audio File",
            "",  # Start directory (can be set by presenter later)
            "Audio Files (*.wav *.mp3 *.flac *.m4a);;All Files (*)"
        )
        if file_path:
            self.set_input_path_text(file_path)  # Update text
            self.input_path_changed.emit(file_path)  # Notify presenter explicitly

    @Slot()
    def show_output_folder_dialog(self):
        """Shows a folder dialog for output. Returns the selected path or None."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            ""  # Start directory
        )
        if folder_path:
            self.set_output_path_text(folder_path)  # Update text
            self.output_path_changed.emit(folder_path)  # Notify presenter explicitly
