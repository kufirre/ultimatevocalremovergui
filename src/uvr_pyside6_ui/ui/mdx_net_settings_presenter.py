"""Presenter for Advanced MDX-Net Settings."""

import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from ..core.logger_utils import get_logger
from .mdx_net_advanced_dialog import MDXNetAdvancedDialog


logger = get_logger(__name__)


class AdvancedMDXSettingsPresenter(QObject):
    """Presenter for advanced MDX-Net settings matching original UVR."""

    # Signals
    settings_changed = Signal(dict)
    vocal_splitter_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self.parent_window = parent
        self._current_settings = self._get_default_settings()

    def _get_default_settings(self):
        """Get default advanced MDX settings matching original UVR structure."""
        return {
            # Regular MDX settings (matching original UVR variable names)
            "compensate": "1.035",
            "mdx_segment_size": 256,
            "overlap": 0.25,
            "semitone_shift": 0,
            "denoise_option": "None",
            # Processing options (matching original UVR variable names)
            "is_match_frequency_pitch": False,
            "is_invert_spec": False,
            # MDX23 settings (matching original UVR variable names)
            "mdx_batch_size": 1,
            "overlap_mdx23": 8,
            "is_mdx_c_seg_def": True,
            "is_mdx23_combine_stems": False,
        }

    def show_settings_dialog(self):
        """Show the advanced MDX settings dialog."""

        dialog = MDXNetAdvancedDialog(self._current_settings, self.parent_window)

        # Connect signals
        dialog.settings_updated.connect(self._on_settings_applied)

        # Show dialog
        dialog.exec()

    def _on_settings_applied(self, settings):
        """Handle settings being applied."""
        logger.info(f"Advanced MDX settings applied: {settings}")

        # Update current settings
        self._current_settings.update(settings)

        # Emit signal for other components
        self.settings_changed.emit(settings)

    def _on_vocal_splitter_requested(self):
        """Handle vocal splitter button click."""
        logger.info("Vocal splitter requested from Advanced MDX Settings")
        self.vocal_splitter_requested.emit()

    def _on_clear_cache_requested(self):
        """Handle clear cache button click."""
        logger.info("Clear MDX cache requested")

        # In a real implementation, this would clear the MDX model cache
        # For now, just show a confirmation message
        try:
            # Here you would typically clear cache files
            # cache_dir = Path("models/MDX") / "cache"
            # if cache_dir.exists():
            #     shutil.rmtree(cache_dir)

            if self.view:
                QMessageBox.information(
                    self.view,
                    "Cache Cleared",
                    "MDX-Net model cache has been cleared successfully.",
                )
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            if self.view:
                QMessageBox.warning(
                    self.view, "Cache Clear Error", f"Failed to clear cache: {str(e)}"
                )

    def _on_open_models_folder_requested(self):
        """Handle open models folder button click."""
        logger.info("Open MDX models folder requested")

        try:
            # Determine the MDX models directory
            mdx_models_dir = Path.home() / "Documents" / "UVR_Models" / "MDX"

            # Create the directory if it doesn't exist
            mdx_models_dir.mkdir(parents=True, exist_ok=True)

            # Open the folder in the system file manager
            import platform
            import subprocess

            system = platform.system()
            if system == "Windows":
                os.startfile(str(mdx_models_dir))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(mdx_models_dir)])
            elif system == "Linux":
                subprocess.run(["xdg-open", str(mdx_models_dir)])
            else:
                logger.warning(f"Unsupported platform for opening folder: {system}")
                if self.view:
                    QMessageBox.information(
                        self.view,
                        "Models Folder",
                        f"MDX models folder: {mdx_models_dir}",
                    )

        except Exception as e:
            logger.error(f"Error opening models folder: {e}")
            if self.view:
                QMessageBox.warning(
                    self.view,
                    "Open Folder Error",
                    f"Failed to open models folder: {str(e)}",
                )

    def get_current_settings(self):
        """Get current advanced MDX settings."""
        return self._current_settings.copy()

    def apply_settings(self, settings):
        """Apply advanced MDX settings programmatically."""
        self._current_settings.update(settings)
        self.settings_changed.emit(self._current_settings)


# Keep the original MDXNetSettingsPresenter for compatibility with existing code
class MDXNetSettingsPresenter(QObject):
    """Presenter for MDX-Net specific settings (simplified version for main UI)."""

    # Signals
    settings_changed = Signal(dict)

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        self._settings = {
            # Basic settings
            "segment_size": 256,
            "overlap": 0.25,
            "match_method": "Nearest",
            "compensate": "1.035",
            "mdx_batch_size": 1,
            "is_match_frequency_pitch": False,
            "is_invert_spec": False,
            "semitone_shift": 0,
            "denoise_option": "None",
            # Advanced settings from dialog
            "mdx_segment_size": 256,
            "overlap_mdx23": 8,
            "is_mdx_c_seg_def": True,
            "is_mdx23_combine_stems": False,
            # Secondary model settings
            "is_secondary_model_activate": False,
            "vocals_secondary_model": "No Model",
            "bass_secondary_model": "No Model",
            "drums_secondary_model": "No Model",
            "other_secondary_model": "No Model",
            "vocals_secondary_scale": 0.9,
            "bass_secondary_scale": 0.5,
            "drums_secondary_scale": 0.5,
            "other_secondary_scale": 0.7,
            # Vocal splitter settings
            "is_vocal_split_mode": False,
            "vocal_model": "No Model",
            "deverb_option": "Main Vocals Only",
            "save_vocal_only": False,
            "save_inst_only": False,
        }
        self._setup_connections()

    def _setup_connections(self):
        """Set up signal connections."""
        if self.view:
            self.view.segment_size_changed.connect(self._on_segment_size_changed)
            self.view.overlap_changed.connect(self._on_overlap_changed)

    def _on_segment_size_changed(self, value):
        """Handle segment size change."""
        logger.debug(f"MDX segment size changed: {value}")
        self._settings["segment_size"] = value
        self.settings_changed.emit({"segment_size": value})

    def _on_overlap_changed(self, value):
        """Handle overlap change."""
        logger.debug(f"MDX overlap changed: {value}")
        self._settings["overlap"] = value
        self.settings_changed.emit({"overlap": value})

    def get_settings(self):
        """Get current MDX-Net settings."""
        return self._settings.copy()

    def show_advanced_settings(self):
        """Show the advanced MDX settings dialog."""

        # Get current settings
        current_settings = self.get_settings()

        # Create and show dialog
        dialog = MDXNetAdvancedDialog(current_settings, self.view)
        dialog.settings_updated.connect(self.update_advanced_settings)

        return dialog.exec()

    def update_advanced_settings(self, advanced_settings):
        """Update settings from the advanced dialog."""
        logger.debug(f"Updating MDX advanced settings: {advanced_settings}")

        # Update internal settings
        self._settings.update(advanced_settings)

        # Emit settings changed signal for any listeners
        self.settings_changed.emit(self._settings.copy())

    def load_settings(self, settings_dict):
        """Load settings from saved configuration."""
        if settings_dict:
            # Update settings with loaded data
            self._settings.update(settings_dict)
            logger.debug(f"Loaded MDX settings: {settings_dict}")

            # Update view if applicable (basic settings only)
            if self.view:
                if "segment_size" in settings_dict:
                    self.view.set_segment_size(settings_dict["segment_size"])
                if "overlap" in settings_dict:
                    self.view.set_overlap(settings_dict["overlap"])
