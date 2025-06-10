"""Presenter for simplified ensemble view in main window."""

from typing import Dict, List

from PySide6.QtCore import QObject, Slot

from ..core import app_constants as ac
from ..core.logger_utils import get_logger
from ..core.uvr_core_adapter import UVRCoreAdapter

logger = get_logger(__name__)


class EnsembleSimplePresenter(QObject):
    """Presenter for simplified ensemble settings in main window."""

    def __init__(self, view, adapter: UVRCoreAdapter, settings_dialog_presenter=None):
        super().__init__()
        self.view = view
        self.adapter = adapter
        self.settings_dialog_presenter = settings_dialog_presenter

        self._current_main_stem_pair: str = ac.ENSEMBLE_MAIN_STEM_OPTIONS[0] if ac.ENSEMBLE_MAIN_STEM_OPTIONS else ""
        self._current_algorithm: str = ac.ENSEMBLE_ALGORITHM_OPTIONS[0] if ac.ENSEMBLE_ALGORITHM_OPTIONS else ""
        self._currently_selected_models: List[str] = []

        self._setup_connections()
        self._initialize_settings()

    def _setup_connections(self):
        """Set up signal connections."""
        self.view.main_stem_pair_changed.connect(self.on_main_stem_pair_changed)
        self.view.ensemble_algorithm_changed.connect(self.on_ensemble_algorithm_changed)
        self.view.advanced_settings_requested.connect(self.on_advanced_settings_requested)

    def _initialize_settings(self):
        """Initialize ensemble settings."""
        # Set initial stem pair
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self._update_algorithm_options()
        self.view.update_selection_status(self._currently_selected_models)

    @Slot(str)
    def on_main_stem_pair_changed(self, stem_pair: str):
        """Handle main stem pair change."""
        self._current_main_stem_pair = stem_pair
        self._update_algorithm_options()
        
        # Clear model selection when stem pair changes
        self._currently_selected_models.clear()
        self.view.update_selection_status(self._currently_selected_models)

    @Slot(str)
    def on_ensemble_algorithm_changed(self, algorithm: str):
        """Handle ensemble algorithm change."""
        self._current_algorithm = algorithm

    @Slot()
    def on_advanced_settings_requested(self):
        """Handle request to open advanced ensemble settings."""
        if self.settings_dialog_presenter:
            # Prepare current settings to pass to advanced dialog
            current_settings = self.get_settings()
            
            # Get the advanced dialog from settings dialog presenter
            from .ensemble_advanced_dialog import EnsembleAdvancedDialog
            
            dialog = EnsembleAdvancedDialog(current_settings, self.view)
            
            # Set available models
            try:
                available_models = {
                    ac.VR_ARCH_MODELS_KEY: self.adapter.get_available_models(ac.VR_ARCH_MODELS_KEY),
                    ac.MDX_NET_MODELS_KEY: self.adapter.get_available_models(ac.MDX_NET_MODELS_KEY),
                    ac.DEMUCS_MODELS_KEY: self.adapter.get_available_models(ac.DEMUCS_MODELS_KEY),
                }
                dialog.set_available_models(available_models)
            except Exception as e:
                logger.warning(f"Could not load available models for ensemble dialog: {e}")
            
            # Connect to handle settings updates
            dialog.settings_updated.connect(self._on_advanced_settings_updated)
            
            dialog.exec()
        else:
            logger.warning("Settings dialog presenter not available for advanced ensemble settings")

    @Slot(dict)
    def _on_advanced_settings_updated(self, settings: dict):
        """Handle settings update from advanced dialog."""
        self._current_main_stem_pair = settings.get("ensemble_main_stem_pair", self._current_main_stem_pair)
        self._current_algorithm = settings.get("ensemble_algorithm", self._current_algorithm)
        self._currently_selected_models = settings.get("ensemble_selected_models", [])
        
        # Update view
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self._update_algorithm_options()
        self.view.set_current_algorithm(self._current_algorithm)
        self.view.update_selection_status(self._currently_selected_models)

    def _update_algorithm_options(self):
        """Update algorithm options based on stem pair selection."""
        if self._current_main_stem_pair == "4 Stem Ensemble":
            # 4-stem ensembles have different algorithm options
            algorithms = [ac.ENSEMBLE_ALGORITHM_OPTIONS[0]] if ac.ENSEMBLE_ALGORITHM_OPTIONS else []
        else:
            algorithms = ac.ENSEMBLE_ALGORITHM_OPTIONS
            
        self.view.update_algorithm_options(algorithms)
        
        # Update current algorithm if it's not in the new list
        if self._current_algorithm not in algorithms and algorithms:
            self._current_algorithm = algorithms[0]
            self.view.set_current_algorithm(self._current_algorithm)

    def get_settings(self) -> dict:
        """Get current ensemble settings."""
        return {
            "ensemble_main_stem_pair": self._current_main_stem_pair,
            "ensemble_algorithm": self._current_algorithm,
            "ensemble_selected_models": self._currently_selected_models.copy(),
        }

    def load_settings(self, settings: dict):
        """Load ensemble settings from external source."""
        self._current_main_stem_pair = settings.get("ensemble_main_stem_pair", self._current_main_stem_pair)
        self._current_algorithm = settings.get("ensemble_algorithm", self._current_algorithm)
        self._currently_selected_models = settings.get("ensemble_selected_models", [])
        
        # Update view
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self._update_algorithm_options()
        self.view.set_current_algorithm(self._current_algorithm)
        self.view.update_selection_status(self._currently_selected_models)

    def is_ensemble_configured(self) -> bool:
        """Check if ensemble is properly configured."""
        return (
            self._current_main_stem_pair != ac.ENSEMBLE_MAIN_STEM_OPTIONS[0] and  # Not "Choose Stem Pair"
            len(self._currently_selected_models) > 1  # At least 2 models selected
        ) 