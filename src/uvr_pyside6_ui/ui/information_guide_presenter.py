"""Presenter for the Information Guide."""

from PySide6.QtCore import QObject

from ..core.logger_utils import get_logger
from .information_guide_view import InformationGuideView

logger = get_logger(__name__)


class InformationGuidePresenter(QObject):
    """Presenter for the information guide functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self.parent_window = parent

    def show_information_guide(self, topic=None):
        """Show the information guide dialog."""
        if self.view is None:
            self.view = InformationGuideView(self.parent_window)

        # Show specific topic if requested
        if topic:
            self.view.show_topic(topic)

        # Show the dialog
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def show_getting_started(self):
        """Show the Getting Started topic."""
        self.show_information_guide("Getting Started")

    def show_model_types(self):
        """Show the Model Types topic."""
        self.show_information_guide("Model Types")

    def show_processing_options(self):
        """Show the Processing Options topic."""
        self.show_information_guide("Processing Options")

    def show_ensemble_mode(self):
        """Show the Ensemble Mode topic."""
        self.show_information_guide("Ensemble Mode")

    def show_audio_formats(self):
        """Show the Audio Formats topic."""
        self.show_information_guide("Audio Formats")

    def show_gpu_acceleration(self):
        """Show the GPU Acceleration topic."""
        self.show_information_guide("GPU Acceleration")

    def show_batch_processing(self):
        """Show the Batch Processing topic."""
        self.show_information_guide("Batch Processing")

    def show_troubleshooting(self):
        """Show the Troubleshooting topic."""
        self.show_information_guide("Troubleshooting")

    def show_keyboard_shortcuts(self):
        """Show the Keyboard Shortcuts topic."""
        self.show_information_guide("Keyboard Shortcuts")

    def show_faq(self):
        """Show the FAQ topic."""
        self.show_information_guide("FAQ")

    def close_guide(self):
        """Close the information guide if open."""
        if self.view:
            self.view.close()
            self.view = None
