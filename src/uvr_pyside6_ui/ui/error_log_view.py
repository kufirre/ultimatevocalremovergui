"""View for the Error Log viewer."""

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..core.logger_utils import get_logger

logger = get_logger(__name__)


class ErrorLogView(QDialog):
    """Dialog for displaying application error logs."""

    # Signals
    clear_log_requested = Signal()
    export_log_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error Log Viewer")
        self.setMinimumSize(800, 500)
        self.setModal(False)  # Non-modal so users can keep it open

        main_layout = QVBoxLayout(self)

        # Header with info
        header_layout = QHBoxLayout()

        info_label = QLabel(
            "Application error log - automatically refreshes every 5 seconds"
        )
        info_label.setStyleSheet("color: #bdc3c7; font-style: italic;")
        header_layout.addWidget(info_label)

        header_layout.addStretch()

        # Auto-refresh indicator
        self.refresh_label = QLabel("●")
        self.refresh_label.setStyleSheet("color: #2ecc71; font-size: 12px;")
        self.refresh_label.setToolTip("Auto-refresh active")
        header_layout.addWidget(self.refresh_label)

        main_layout.addLayout(header_layout)

        # Log display area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("SF Mono", 9))  # Monospace font for logs
        self.log_text.setObjectName("logConsole")  # For CSS styling
        main_layout.addWidget(self.log_text)

        # Button bar
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh Now")
        self.refresh_button.clicked.connect(self._on_refresh)

        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self._on_clear)

        self.export_button = QPushButton("Export Log")
        self.export_button.clicked.connect(self._on_export)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_auto_refresh)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

        # Track if we should auto-scroll to bottom
        self.auto_scroll = True
        self.log_text.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

    def _on_scroll_changed(self, value):
        """Track if user has scrolled away from bottom."""
        scrollbar = self.log_text.verticalScrollBar()
        # If user is at the bottom, enable auto-scroll
        self.auto_scroll = value >= scrollbar.maximum() - 10

    def _on_refresh(self):
        """Handle manual refresh button click."""
        self._refresh_log()

    def _on_auto_refresh(self):
        """Handle auto-refresh timer."""
        self._refresh_log()
        # Blink the refresh indicator
        self.refresh_label.setStyleSheet("color: #3498db; font-size: 12px;")
        QTimer.singleShot(
            200,
            lambda: self.refresh_label.setStyleSheet(
                "color: #2ecc71; font-size: 12px;"
            ),
        )

    def _refresh_log(self):
        """Refresh the log content."""
        # This would be implemented to read from the actual log file
        # For now, we'll just emit a signal for the presenter to handle
        pass

    def _on_clear(self):
        """Handle clear log button click."""
        self.clear_log_requested.emit()

    def _on_export(self):
        """Handle export log button click."""
        self.export_log_requested.emit()

    def set_log_content(self, content):
        """Set the log content."""
        # Save current cursor position
        cursor = self.log_text.textCursor()
        was_at_end = cursor.atEnd()

        # Update content
        self.log_text.setPlainText(content)

        # Auto-scroll to bottom if we were at the end or auto-scroll is enabled
        if was_at_end or self.auto_scroll:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_text.setTextCursor(cursor)

    def append_log_entry(self, entry):
        """Append a new log entry."""
        cursor = self.log_text.textCursor()
        was_at_end = cursor.atEnd()

        # Move to end and append
        cursor.movePosition(QTextCursor.End)
        if (
            not self.log_text.toPlainText().endswith("\n")
            and self.log_text.toPlainText()
        ):
            cursor.insertText("\n")
        cursor.insertText(entry)

        # Auto-scroll if enabled
        if was_at_end or self.auto_scroll:
            cursor.movePosition(QTextCursor.End)
            self.log_text.setTextCursor(cursor)

    def clear_log_display(self):
        """Clear the log display."""
        self.log_text.clear()

    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop the auto-refresh timer
        self.refresh_timer.stop()
        super().closeEvent(event)

    def showEvent(self, event):
        """Handle dialog show event."""
        # Start the auto-refresh timer when dialog is shown
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(5000)
        super().showEvent(event)
