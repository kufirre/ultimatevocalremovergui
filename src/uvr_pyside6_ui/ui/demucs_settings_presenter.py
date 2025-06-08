"""Presenter for Advanced Demucs Settings."""

import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from ..core.logger_utils import get_logger
from .demucs_settings_view import AdvancedDemucsSettingsView

logger = get_logger(__name__)


class AdvancedDemucsSettingsPresenter(QObject):
    """Presenter for advanced Demucs settings matching original UVR."""

    # Signals
    settings_changed = Signal(dict)
    vocal_splitter_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self.parent_window = parent
        self._current_settings = self._get_default_settings()

    def _get_default_settings(self):
        """Get default advanced Demucs settings matching original UVR structure."""
        return {
            # Core Demucs settings (matching original UVR variable names)
            "segment": "Default",
            "shifts": 2,
            "overlap": 0.25,
            "semitone_shift": 0,
            
            # Processing options (matching original UVR variable names)
            "is_split_mode": False,
            "is_demucs_combine_stems": False,
            "is_invert_spec": False,
            
            # Pre-processing model settings (matching original UVR variable names)
            "demucs_pre_proc_model": "No Pre-processing Model",
            "is_demucs_pre_proc_model_activate": False,
            "is_demucs_pre_proc_model_inst_mix": False,
        }

    def show_settings_dialog(self, is_demucs_mode=False):
        """Show the advanced Demucs settings dialog."""
        # Pass is_demucs_mode to control segments visibility
        self.view = AdvancedDemucsSettingsView(self.parent_window, is_demucs_mode=is_demucs_mode)
        
        # Load current settings
        self.view.set_settings(self._current_settings)
        
        # Connect signals
        self.view.settings_applied.connect(self._on_settings_applied)
        self.view.vocal_splitter_requested.connect(self._on_vocal_splitter_requested)
        self.view.open_models_folder_requested.connect(self._on_open_models_folder_requested)
        
        # Show dialog
        self.view.exec()

    def _on_settings_applied(self, settings):
        """Handle settings being applied."""
        logger.info(f"Advanced Demucs settings applied: {settings}")
        
        # Update current settings
        self._current_settings.update(settings)
        
        # Emit signal for other components
        self.settings_changed.emit(settings)

    def _on_vocal_splitter_requested(self):
        """Handle vocal splitter button click."""
        logger.info("Vocal splitter requested from Advanced Demucs Settings")
        self.vocal_splitter_requested.emit()

    def _on_open_models_folder_requested(self):
        """Handle open models folder button click."""
        logger.info("Open Demucs models folder requested")
        
        try:
            # Determine the Demucs models directory
            demucs_models_dir = Path.home() / "Documents" / "UVR_Models" / "Demucs"
            
            # Create the directory if it doesn't exist
            demucs_models_dir.mkdir(parents=True, exist_ok=True)
            
            # Open the folder in the system file manager
            import platform
            import subprocess
            
            system = platform.system()
            if system == "Windows":
                os.startfile(str(demucs_models_dir))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(demucs_models_dir)])
            elif system == "Linux":
                subprocess.run(["xdg-open", str(demucs_models_dir)])
            else:
                logger.warning(f"Unsupported platform for opening folder: {system}")
                if self.view:
                    QMessageBox.information(
                        self.view,
                        "Models Folder",
                        f"Demucs models folder: {demucs_models_dir}"
                    )
                    
        except Exception as e:
            logger.error(f"Error opening models folder: {e}")
            if self.view:
                QMessageBox.warning(
                    self.view,
                    "Open Folder Error",
                    f"Failed to open models folder: {str(e)}"
                )

    def get_current_settings(self):
        """Get current advanced Demucs settings."""
        return self._current_settings.copy()

    def apply_settings(self, settings):
        """Apply advanced Demucs settings programmatically."""
        self._current_settings.update(settings)
        self.settings_changed.emit(self._current_settings)


# Keep the original DemucsSettingsPresenter for compatibility with existing code
class DemucsSettingsPresenter(QObject):
    """Presenter for Demucs simple settings (stems and segments on main separation page)."""

    # Signals
    settings_changed = Signal(dict)

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view
        # Simple settings (on main separation page) + defaults for advanced settings
        self._settings = {
            # Simple settings (visible on main separation page)
            "stems": "All Stems",
            "demucs_stems": "All Stems",  # For compatibility
            "segments": "Default",  # Also a simple setting in UVR
            
            # Advanced settings with sensible defaults (controlled by advanced dialog)
            "shifts": 2,
            "overlap": 0.25,
            "semitone_shift": 0,
            "is_split_mode": False,
            "is_demucs_combine_stems": False,
            "is_invert_spec": False,
            
            # Secondary model settings (defaults)
            "is_secondary_model_activate": False,
            "voc_inst_secondary_model": "No Model",
            "other_secondary_model": "No Model", 
            "bass_secondary_model": "No Model",
            "drums_secondary_model": "No Model",
            "voc_inst_secondary_model_scale": 0.9,
            "other_secondary_model_scale": 0.7,
            "bass_secondary_model_scale": 0.5,
            "drums_secondary_model_scale": 0.5,
            
            # Preprocess model settings (defaults)
            "is_demucs_pre_proc_model_activate": False,
            "demucs_pre_proc_model": "No Model",
            "is_demucs_pre_proc_model_inst_mix": False,
            
            # Vocal splitter settings (defaults)
            "is_karaoke": False,
            "is_bv_model": False,
            "is_bv_model_rebalanced": False
        }

        # Connect to view signals
        self._connect_signals()
        
        # Set initial values
        self._sync_view_to_settings()

    def _connect_signals(self):
        """Connect view signals to handlers."""
        self.view.stems_changed.connect(self._on_stems_changed)
        self.view.segments_changed.connect(self._on_segments_changed)

    def _on_stems_changed(self, stems):
        """Handle stem selection change."""
        self._settings["stems"] = stems
        self._settings["demucs_stems"] = stems  # For compatibility
        self.settings_changed.emit(self._settings.copy())

    def _on_segments_changed(self, segments):
        """Handle segments change."""
        self._settings["segments"] = segments
        self.settings_changed.emit(self._settings.copy())

    def _sync_view_to_settings(self):
        """Sync view to current settings."""
        self.view.set_stems(self._settings["stems"])
        if isinstance(self._settings["segments"], int):
            self.view.set_segments(self._settings["segments"])
        else:
            # Handle string values like "Default"
            if self._settings["segments"] == "Default":
                self.view.set_segments(40)
            else:
                try:
                    self.view.set_segments(int(self._settings["segments"]))
                except (ValueError, TypeError):
                    self.view.set_segments(40)  # Fallback to default

    def get_settings(self):
        """Get current settings for processing."""
        return self._settings.copy()

    def update_settings(self, settings_dict):
        """Update settings from external source."""
        self._settings.update(settings_dict)
        self._sync_view_to_settings()
        self.settings_changed.emit(self._settings.copy())

    def load_settings(self, settings_dict):
        """Load settings from saved configuration."""
        if settings_dict:
            # Update simple settings
            if "stems" in settings_dict:
                self._settings["stems"] = settings_dict["stems"]
                self._settings["demucs_stems"] = settings_dict["stems"]
            if "demucs_stems" in settings_dict and "stems" not in settings_dict:
                self._settings["stems"] = settings_dict["demucs_stems"]
                self._settings["demucs_stems"] = settings_dict["demucs_stems"]
            if "segments" in settings_dict:
                self._settings["segments"] = settings_dict["segments"]
            
            # Update advanced settings while preserving defaults for missing keys
            advanced_keys = [
                "shifts", "overlap", "semitone_shift", "is_split_mode", 
                "is_demucs_combine_stems", "is_invert_spec",
                "is_secondary_model_activate", "voc_inst_secondary_model",
                "other_secondary_model", "bass_secondary_model", "drums_secondary_model",
                "voc_inst_secondary_model_scale", "other_secondary_model_scale",
                "bass_secondary_model_scale", "drums_secondary_model_scale",
                "is_demucs_pre_proc_model_activate", "demucs_pre_proc_model",
                "is_demucs_pre_proc_model_inst_mix", "is_karaoke", "is_bv_model",
                "is_bv_model_rebalanced"
            ]
            
            for key in advanced_keys:
                if key in settings_dict:
                    self._settings[key] = settings_dict[key]
            
            self._sync_view_to_settings()
            self.settings_changed.emit(self._settings.copy())

    def update_advanced_settings(self, advanced_settings):
        """Update advanced settings from the advanced dialog."""
        logger.debug(f"Updating advanced Demucs settings: {advanced_settings}")
        
        # Update internal settings
        for key, value in advanced_settings.items():
            if key in self._settings:
                self._settings[key] = value
        
        # Emit settings changed signal for any listeners
        self.settings_changed.emit(self._settings.copy())
        
    def get_advanced_settings(self):
        """Get only the advanced settings for the advanced dialog."""
        advanced_keys = [
            "shifts", "overlap", "semitone_shift", "is_split_mode", 
            "is_demucs_combine_stems", "is_invert_spec",
            "is_secondary_model_activate", "voc_inst_secondary_model",
            "other_secondary_model", "bass_secondary_model", "drums_secondary_model",
            "voc_inst_secondary_model_scale", "other_secondary_model_scale",
            "bass_secondary_model_scale", "drums_secondary_model_scale",
            "is_demucs_pre_proc_model_activate", "demucs_pre_proc_model",
            "is_demucs_pre_proc_model_inst_mix", "is_karaoke", "is_bv_model",
            "is_bv_model_rebalanced"
        ]
        
        return {key: self._settings[key] for key in advanced_keys if key in self._settings}
        
    def show_advanced_settings(self):
        """Show the advanced settings dialog."""
        from .demucs_advanced_dialog import DemucsAdvancedDialog
        
        # Get current advanced settings
        current_settings = self.get_advanced_settings()
        
        # Create and show dialog
        dialog = DemucsAdvancedDialog(current_settings, self.view)
        dialog.settings_updated.connect(self.update_advanced_settings)
        
        return dialog.exec()
