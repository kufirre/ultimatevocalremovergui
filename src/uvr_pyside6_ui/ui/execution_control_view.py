from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QPushButton,
    QProgressBar, QTextEdit, QLabel, QHBoxLayout
)
from PySide6.QtGui import QIcon # Import QIcon
from PySide6.QtCore import Signal, Slot, QSize # Import QSize


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
        self.start_button.setObjectName("prominentButton") # Set object name for QSS
        try:
            play_icon = QIcon(":/uvr/img/play.png")
            if not play_icon.isNull():
                self.start_button.setIcon(play_icon)
                self.start_button.setIconSize(QSize(18, 18)) # Adjust size as needed
            else:
                print("Warning: Could not load play.png icon for Start button.")
        except Exception as e:
            print(f"Error loading play icon: {e}")
        self.start_button.clicked.connect(self.start_processing_clicked)
        exec_layout.addWidget(self.start_button)

        # --- Progress Bar with Label ---
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(2)
        
        # Add label above progress bar
        self.progress_label = QLabel("Ready")
        self.progress_label.setProperty("progressLabel", True)  # For QSS styling
        progress_layout.addWidget(self.progress_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("mainProgressBar")  # Set object name for QSS
        self.progress_bar.setTextVisible(False)  # Hide text inside progress bar
        self.progress_bar.setValue(0)  # Start at 0
        progress_layout.addWidget(self.progress_bar)
        
        exec_layout.addWidget(progress_container)

        # --- Status/Log Area ---
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        
        self.log_text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        self.log_text_edit.setFixedHeight(100) # Give it a fixed height for now
        self.log_text_edit.setObjectName("logConsole") # Set object name for QSS
        exec_layout.addWidget(self.log_text_edit)

        layout.addWidget(exec_group)
        self.setLayout(layout)

    # --- Slots (Called by the Presenter) ---

    @Slot(int)
    def set_progress_value(self, value: int):
        """Updates the progress bar value."""
        self.progress_bar.setValue(value)

    @Slot(str)
    def set_progress_text(self, text: str):
        """Sets the text displayed in the progress label."""
        self.progress_label.setText(text)

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
