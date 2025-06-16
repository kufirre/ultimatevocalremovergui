"""Presenter for simplified ensemble view in main window."""

from typing import List

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

        self._current_main_stem_pair: str = (
            ac.ENSEMBLE_MAIN_STEM_OPTIONS[0] if ac.ENSEMBLE_MAIN_STEM_OPTIONS else ""
        )
        self._current_algorithm: str = (
            ac.ENSEMBLE_ALGORITHM_OPTIONS[0] if ac.ENSEMBLE_ALGORITHM_OPTIONS else ""
        )
        self._currently_selected_models: List[str] = []

        # Checkbox states
        self._save_all_outputs: bool = True
        self._append_ensemble_name: bool = False
        self._use_waveform: bool = False

        self._setup_connections()
        self._initialize_settings()

    def _setup_connections(self):
        """Set up signal connections."""
        self.view.main_stem_pair_changed.connect(self.on_main_stem_pair_changed)
        self.view.ensemble_algorithm_changed.connect(self.on_ensemble_algorithm_changed)
        self.view.advanced_settings_requested.connect(
            self.on_advanced_settings_requested
        )

        # Checkbox connections
        self.view.save_all_outputs_changed.connect(self.on_save_all_outputs_changed)
        self.view.append_ensemble_name_changed.connect(
            self.on_append_ensemble_name_changed
        )
        self.view.use_waveform_changed.connect(self.on_use_waveform_changed)

    def _initialize_settings(self):
        """Initialize ensemble settings."""
        # Set initial stem pair
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self._update_algorithm_options()
        self.view.update_selection_status(self._currently_selected_models)

        # Set initial checkbox states
        self.view.set_save_all_outputs(self._save_all_outputs)
        self.view.set_append_ensemble_name(self._append_ensemble_name)
        self.view.set_use_waveform(self._use_waveform)

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

    @Slot(bool)
    def on_save_all_outputs_changed(self, value: bool):
        """Handle save all outputs checkbox change."""
        self._save_all_outputs = value

    @Slot(bool)
    def on_append_ensemble_name_changed(self, value: bool):
        """Handle append ensemble name checkbox change."""
        self._append_ensemble_name = value

    @Slot(bool)
    def on_use_waveform_changed(self, value: bool):
        """Handle use waveform checkbox change."""
        self._use_waveform = value

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
                    ac.VR_ARCH_MODELS_KEY: self.adapter.get_available_models(
                        ac.VR_ARCH_MODELS_KEY
                    ),
                    ac.MDX_NET_MODELS_KEY: self.adapter.get_available_models(
                        ac.MDX_NET_MODELS_KEY
                    ),
                    ac.DEMUCS_MODELS_KEY: self.adapter.get_available_models(
                        ac.DEMUCS_MODELS_KEY
                    ),
                }
                dialog.set_available_models(available_models)
            except Exception as e:
                logger.warning(
                    f"Could not load available models for ensemble dialog: {e}"
                )

            # Connect to handle settings updates
            dialog.settings_updated.connect(self._on_advanced_settings_updated)

            dialog.exec()
        else:
            logger.warning(
                "Settings dialog presenter not available for advanced ensemble settings"
            )

    @Slot(dict)
    def _on_advanced_settings_updated(self, settings: dict):
        """Handle settings update from advanced dialog."""
        self._current_main_stem_pair = settings.get(
            "ensemble_main_stem_pair", self._current_main_stem_pair
        )
        self._current_algorithm = settings.get(
            "ensemble_algorithm", self._current_algorithm
        )
        self._currently_selected_models = settings.get("ensemble_selected_models", [])

        # Update checkbox states
        self._save_all_outputs = settings.get(
            "save_all_outputs", self._save_all_outputs
        )
        self._append_ensemble_name = settings.get(
            "append_ensemble_name", self._append_ensemble_name
        )
        self._use_waveform = settings.get("use_waveform_ensemble", self._use_waveform)

        # Update view
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self._update_algorithm_options()
        self.view.set_current_algorithm(self._current_algorithm)
        self.view.update_selection_status(self._currently_selected_models)

        # Update checkbox states in view
        self.view.set_save_all_outputs(self._save_all_outputs)
        self.view.set_append_ensemble_name(self._append_ensemble_name)
        self.view.set_use_waveform(self._use_waveform)

    def _update_algorithm_options(self):
        """Update algorithm options based on stem pair selection."""
        if self._current_main_stem_pair == "4 Stem Ensemble":
            # 4-stem ensembles use simpler algorithm options
            algorithms = ac.ENSEMBLE_ALGORITHM_4_STEM_OPTIONS
        else:
            # Standard 2-stem ensembles use full algorithm options
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
            "save_all_outputs": self._save_all_outputs,
            "append_ensemble_name": self._append_ensemble_name,
            "use_waveform_ensemble": self._use_waveform,
        }

    def load_settings(self, settings: dict):
        """Load ensemble settings from external source."""
        self._current_main_stem_pair = settings.get(
            "ensemble_main_stem_pair", self._current_main_stem_pair
        )
        self._current_algorithm = settings.get(
            "ensemble_algorithm", self._current_algorithm
        )
        self._currently_selected_models = settings.get("ensemble_selected_models", [])

        # Load checkbox states
        self._save_all_outputs = settings.get(
            "save_all_outputs", self._save_all_outputs
        )
        self._append_ensemble_name = settings.get(
            "append_ensemble_name", self._append_ensemble_name
        )
        self._use_waveform = settings.get("use_waveform_ensemble", self._use_waveform)

        # Update view
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self._update_algorithm_options()
        self.view.set_current_algorithm(self._current_algorithm)
        self.view.update_selection_status(self._currently_selected_models)

        # Update checkbox states in view
        self.view.set_save_all_outputs(self._save_all_outputs)
        self.view.set_append_ensemble_name(self._append_ensemble_name)
        self.view.set_use_waveform(self._use_waveform)

    def is_ensemble_configured(self) -> bool:
        """Check if ensemble is properly configured."""
        return (
            self._current_main_stem_pair
            != ac.ENSEMBLE_MAIN_STEM_OPTIONS[0]  # Not "Choose Stem Pair"
            and len(self._currently_selected_models) > 1  # At least 2 models selected
        )
