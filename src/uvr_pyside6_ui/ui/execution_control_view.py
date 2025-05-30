from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QPushButton, 
    QProgressBar, QTextEdit # <-- Make sure QTextEdit is here
)
from PySide6.QtCore import Signal, Slot
# We don't need QTextOption for this anymore
# from PySide6.QtGui import QTextOption 

class ExecutionControlView(QWidget):
    """
    View for starting the process and displaying progress/logs.
    """
    start_processing_clicked = Signal()
    stop_processing_clicked = Signal() # Good to plan for a stop button

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        exec_group = QGroupBox("Execution & Progress")
        exec_layout = QVBoxLayout(exec_group)

        # --- Start/Stop Button ---
        self.start_button = QPushButton("Start Processing")
        self.start_button.setStyleSheet("font-size: 14px; padding: 10px;") # A bit more prominent
        self.start_button.clicked.connect(self.start_processing_clicked)
        exec_layout.addWidget(self.start_button)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0) # Start at 0
        exec_layout.addWidget(self.progress_bar)

        # --- Status/Log Area ---
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        
        # --- THIS IS THE CORRECTED LINE ---
        self.log_text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap) 
        # --- END OF CORRECTION ---
        
        self.log_text_edit.setFixedHeight(100) # Give it a fixed height for now
        self.log_text_edit.setStyleSheet("font-family: monospace; font-size: 10px;")
        exec_layout.addWidget(self.log_text_edit)

        layout.addWidget(exec_group)
        self.setLayout(layout)

        # print("ExecutionControlView Initialized.") # Removed unprofessional comment

    # --- Slots (Called by the Presenter) ---

    @Slot(int)
    def set_progress_value(self, value: int):
        """Updates the progress bar value."""
        self.progress_bar.setValue(value)

    @Slot(str)
    def set_progress_text(self, text: str):
        """Sets the text displayed on the progress bar."""
        self.progress_bar.setFormat(f"{text} - %p%")

    @Slot(str)
    def append_log_message(self, message: str):
        """Adds a message to the log area."""
        self.log_text_edit.append(message)
        # Auto-scroll to the bottom
        self.log_text_edit.verticalScrollBar().setValue(
            self.log_text_edit.verticalScrollBar().maximum()
        )

    @Slot(bool)
    def set_start_button_enabled(self, is_enabled: bool):
        """Enables or disables the Start button."""
        self.start_button.setEnabled(is_enabled)

    @Slot(str)
    def set_start_button_text(self, text: str):
        """Changes the text on the Start button."""
        self.start_button.setText(text)
        
    @Slot()
    def clear_logs(self):
        """Clears the log area."""
        self.log_text_edit.clear()
