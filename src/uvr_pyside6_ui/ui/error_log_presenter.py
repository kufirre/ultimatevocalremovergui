"""Presenter for the Error Log viewer."""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..core.logger_utils import get_logger
from .error_log_view import ErrorLogView

logger = get_logger(__name__)


class ErrorLogPresenter(QObject):
    """Presenter for the error log functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self.parent_window = parent
        self.log_file_path = self._get_log_file_path()

    def _get_log_file_path(self):
        """Get the path to the application log file."""
        # In a real implementation, this would point to the actual log file
        # For now, we'll use a placeholder path
        try:
            # Try to get the application data directory
            app_data_dir = Path.home() / ".uvr_pyside6"
            app_data_dir.mkdir(exist_ok=True)
            return app_data_dir / "application.log"
        except Exception as e:
            logger.warning(f"Could not determine log file path: {e}")
            return Path("application.log")

    def show_error_log(self):
        """Show the error log viewer."""
        if self.view is None:
            self.view = ErrorLogView(self.parent_window)

            # Connect signals
            self.view.clear_log_requested.connect(self._on_clear_log)
            self.view.export_log_requested.connect(self._on_export_log)

        # Load current log content
        self._refresh_log_content()

        # Show the dialog
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def _refresh_log_content(self):
        """Refresh the log content from file."""
        if not self.view:
            return

        try:
            if self.log_file_path.exists():
                with open(self.log_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.view.set_log_content(content)
            else:
                self.view.set_log_content(
                    "No log file found. Logs will appear here when the application generates them."
                )
        except Exception as e:
            error_msg = f"Error reading log file: {e}"
            logger.error(error_msg)
            self.view.set_log_content(error_msg)

    def _on_clear_log(self):
        """Handle clear log request."""
        try:
            # Ask for confirmation
            reply = QMessageBox.question(
                self.view,
                "Clear Log",
                "Are you sure you want to clear the error log?\n\nThis action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                # Clear the log file
                if self.log_file_path.exists():
                    with open(self.log_file_path, "w", encoding="utf-8") as f:
                        f.write("")

                # Clear the display
                self.view.clear_log_display()

                # Log the action
                logger.info("Error log cleared by user")

        except Exception as e:
            error_msg = f"Error clearing log file: {e}"
            logger.error(error_msg)
            QMessageBox.critical(
                self.view, "Error", f"Failed to clear log file:\n{error_msg}"
            )

    def _on_export_log(self):
        """Handle export log request."""
        try:
            # Get current timestamp for default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"uvr_error_log_{timestamp}.txt"

            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self.view,
                "Export Error Log",
                default_filename,
                "Text Files (*.txt);;All Files (*)",
            )

            if file_path:
                # Read current log content
                if self.log_file_path.exists():
                    with open(self.log_file_path, "r", encoding="utf-8") as source:
                        content = source.read()
                else:
                    content = "No log content available."

                # Write to export file
                with open(file_path, "w", encoding="utf-8") as export_file:
                    export_file.write("UVR Error Log Export\n")
                    export_file.write(
                        f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    export_file.write("=" * 50 + "\n\n")
                    export_file.write(content)

                # Show success message
                QMessageBox.information(
                    self.view,
                    "Export Complete",
                    f"Error log exported successfully to:\n{file_path}",
                )

                logger.info(f"Error log exported to: {file_path}")

        except Exception as e:
            error_msg = f"Error exporting log file: {e}"
            logger.error(error_msg)
            QMessageBox.critical(
                self.view, "Export Error", f"Failed to export log file:\n{error_msg}"
            )

    def add_log_entry(self, entry):
        """Add a new log entry (called by the logging system)."""
        if self.view:
            self.view.append_log_entry(entry)

    def close_log_viewer(self):
        """Close the log viewer if open."""
        if self.view:
            self.view.close()
            self.view = None
