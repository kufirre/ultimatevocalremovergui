"""Presenter for the Audio Alignment Tool."""

from PySide6.QtCore import QObject, Signal

from ..core.logger_utils import get_logger
from .audio_alignment_view import AudioAlignmentView

logger = get_logger(__name__)


class AudioAlignmentPresenter(QObject):
    """Presenter for audio alignment functionality."""

    # Signals
    alignment_settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self.parent_window = parent
        self._current_settings = self._get_default_settings()

    def _get_default_settings(self):
        """Get default alignment settings."""
        return {
            "auto_align": True,
            "time_shift_ms": 0,
            "phase_correction": "None",
            "correlation_window": "Medium",
            "sensitivity": 5,
            "threshold": 0.7,
            "apply_to_all": True,
            "save_settings": False,
        }

    def show_alignment_dialog(self):
        """Show the audio alignment dialog."""
        self.view = AudioAlignmentView(self.parent_window)
        
        # Load current settings
        self.view.set_settings(self._current_settings)
        
        # Connect signals
        self.view.alignment_applied.connect(self._on_alignment_applied)
        self.view.preview_requested.connect(self._on_preview_requested)
        
        # Show dialog
        self.view.exec()

    def _on_alignment_applied(self, settings):
        """Handle alignment settings being applied."""
        logger.info(f"Alignment settings applied: {settings}")
        
        # Update current settings
        self._current_settings.update(settings)
        
        # Save settings if requested
        if settings.get("save_settings", False):
            self._save_default_settings(settings)
        
        # Emit signal for other components
        self.alignment_settings_changed.emit(settings)

    def _on_preview_requested(self, settings):
        """Handle preview request."""
        logger.info(f"Preview requested with settings: {settings}")
        
        # In a real implementation, this would:
        # 1. Apply the alignment settings temporarily
        # 2. Process a small sample of audio
        # 3. Show the result in a preview window
        
        # For now, just log the request
        logger.info("Preview functionality not yet implemented")

    def _save_default_settings(self, settings):
        """Save settings as defaults."""
        # In a real implementation, this would save to a config file
        logger.info(f"Saving default alignment settings: {settings}")

    def get_current_settings(self):
        """Get current alignment settings."""
        return self._current_settings.copy()

    def apply_settings(self, settings):
        """Apply alignment settings programmatically."""
        self._current_settings.update(settings)
        self.alignment_settings_changed.emit(self._current_settings)
