from typing import Dict, List

import natsort
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMessageBox

from uvr_pyside6_ui.core.logger_utils import get_logger

from ..core import app_constants as ac
from ..core.uvr_core_adapter import UVRCoreAdapter
from .ensemble_advanced_dialog import EnsembleAdvancedDialog

logger = get_logger(__name__)


class EnsembleSettingsPresenter(QObject):
    """Presenter for Ensemble settings that delegates persistence to advanced dialog."""

    def __init__(self, view, adapter: UVRCoreAdapter):
        super().__init__()
        self.view = view
        self.adapter = adapter

        self._all_local_models_by_type: Dict[str, List[str]] = {}
        self._current_main_stem_pair: str = (
            ac.ENSEMBLE_MAIN_STEM_OPTIONS[0] if ac.ENSEMBLE_MAIN_STEM_OPTIONS else ""
        )
        self._current_algorithm: str = (
            ac.ENSEMBLE_ALGORITHM_OPTIONS[0] if ac.ENSEMBLE_ALGORITHM_OPTIONS else ""
        )
        self._currently_selected_models_for_ensemble: List[str] = []

        # Connect view signals
        self.view.main_stem_pair_changed.connect(self.on_main_stem_pair_changed)
        self.view.ensemble_algorithm_changed.connect(self.on_ensemble_algorithm_changed)
        self.view.selected_models_changed.connect(self.on_models_selected_for_ensemble)
        self.view.ensemble_action_requested.connect(self.handle_ensemble_action)

        self._initialize_settings()

    def _initialize_settings(self):
        """Initialize ensemble settings and load available models."""
        self._all_local_models_by_type = {
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

        # Set initial stem pair, which triggers algorithm and model list update
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self.on_main_stem_pair_changed(self._current_main_stem_pair)

    @Slot(str)
    def handle_ensemble_action(self, action_text: str):
        """Handle ensemble actions by delegating to the advanced dialog."""
        if action_text == ac.ENSEMBLE_ACTION_SAVE_AS:
            self._open_advanced_dialog_for_save()
        elif action_text == ac.ENSEMBLE_ACTION_CLEAR_SELECTION:
            self.on_clear_model_selection()
        elif action_text == ac.ENSEMBLE_ACTION_LOAD:
            self._open_advanced_dialog_for_load()

    def _open_advanced_dialog_for_save(self):
        """Open advanced dialog for saving ensemble."""
        if not self._currently_selected_models_for_ensemble:
            QMessageBox.warning(
                self.view.window(),
                "Save Ensemble",
                "No models selected for the ensemble.",
            )
            return

        self._open_advanced_dialog()

    def _open_advanced_dialog_for_load(self):
        """Open advanced dialog for loading ensemble."""
        self._open_advanced_dialog()

    def _open_advanced_dialog(self):
        """Open the advanced dialog with current settings."""
        current_settings = self.get_settings()
        dialog = EnsembleAdvancedDialog(current_settings, self.view.window())

        # Set available models
        try:
            dialog.set_available_models(self._all_local_models_by_type)
        except Exception as e:
            logger.warning(f"Could not load available models for ensemble dialog: {e}")

        # Connect to handle settings updates
        dialog.settings_updated.connect(self._on_advanced_dialog_settings_updated)

        dialog.exec()

    @Slot(dict)
    def _on_advanced_dialog_settings_updated(self, settings: dict):
        """Handle settings update from advanced dialog."""
        self._current_main_stem_pair = settings.get(
            "ensemble_main_stem_pair", self._current_main_stem_pair
        )
        self._current_algorithm = settings.get(
            "ensemble_algorithm", self._current_algorithm
        )
        self._currently_selected_models_for_ensemble = settings.get(
            "ensemble_selected_models", []
        )

        # Update view to reflect changes
        self.view.set_current_stem_pair(self._current_main_stem_pair)
        self.on_main_stem_pair_changed(self._current_main_stem_pair)
        self.view.set_current_algorithm(self._current_algorithm)
        self.view.set_selected_models_in_list(
            self._currently_selected_models_for_ensemble
        )

    @Slot(str)
    def on_main_stem_pair_changed(self, stem_pair: str):
        """Handle stem pair change and update available algorithms and models."""
        self._current_main_stem_pair = stem_pair

        if stem_pair == ac.ENSEMBLE_MAIN_STEM_OPTIONS[4]:  # "4 Stem Ensemble"
            self.view.set_ensemble_algorithms(ac.ENSEMBLE_ALGORITHM_4_STEM_OPTIONS)
        else:
            self.view.set_ensemble_algorithms(ac.ENSEMBLE_ALGORITHM_OPTIONS)

        if self.view.algorithm_combo.count() > 0:
            self._current_algorithm = self.view.algorithm_combo.itemText(0)
            self.view.set_current_algorithm(self._current_algorithm)

        # Filter and display compatible models
        filtered_models = self._filter_models_by_stem_compatibility(stem_pair)
        display_models = []
        for model_entry in filtered_models:
            if ":" in model_entry:
                _, model_name = model_entry.split(":", 1)
                display_models.append(model_name)
            else:
                display_models.append(model_entry)

        unique_display_models = natsort.natsorted(list(set(display_models)))
        self.view.populate_available_models(unique_display_models)

        # Filter currently selected models to only include compatible ones
        compatible_selected_models = [
            model
            for model in self._currently_selected_models_for_ensemble
            if model in unique_display_models
        ]
        self._currently_selected_models_for_ensemble = compatible_selected_models
        self.view.set_selected_models_in_list(
            self._currently_selected_models_for_ensemble
        )

    def _filter_models_by_stem_compatibility(self, stem_pair: str) -> List[str]:
        """Filter models to only include those compatible with the selected stem pair.

        This implements the exact logic from UVR.py's matches_stem function and model_list method.
        """
        # Parse stem pair to get primary and secondary stems
        primary_stem, secondary_stem = self._parse_stem_pair(stem_pair)

        # Determine filtering mode based on stem pair
        is_4_stem_check = stem_pair == "4 Stem Ensemble"
        is_multi_stem = stem_pair == "Multi-stem Ensemble"

        filtered_models = []

        # Get all available models with their metadata
        for model_type, models in self._all_local_models_by_type.items():
            for model_name in models:
                try:
                    # Create minimal ModelData to check compatibility
                    model_data = self._get_model_data_for_filtering(
                        model_name, model_type
                    )

                    if not model_data or not model_data.model_status:
                        continue

                    # Apply the filtering logic from UVR.py
                    if is_multi_stem:
                        # Multi-stem ensemble: include all models
                        filtered_models.append(f"{model_type}:{model_name}")
                    elif is_4_stem_check:
                        # 4-stem ensemble: only models with 4+ stems
                        if (
                            hasattr(model_data, "demucs_stem_count")
                            and model_data.demucs_stem_count == 4
                        ) or (
                            hasattr(model_data, "mdx_model_stems")
                            and len(model_data.mdx_model_stems) == 4
                        ):
                            filtered_models.append(f"{model_type}:{model_name}")
                    else:
                        # Standard 2-stem filtering using matches_stem logic
                        if self._matches_stem(model_data, primary_stem, secondary_stem):
                            filtered_models.append(f"{model_type}:{model_name}")

                except Exception as e:
                    logger.debug(
                        f"Error checking model compatibility for {model_name}: {e}"
                    )
                    continue

        return filtered_models

    def _parse_stem_pair(self, stem_pair: str) -> tuple[str, str]:
        """Parse stem pair string to get primary and secondary stems."""
        if stem_pair == "4 Stem Ensemble":
            return ac.VOCAL_STEM, ac.INST_STEM  # Default for 4-stem
        elif stem_pair == "Multi-stem Ensemble":
            return ac.VOCAL_STEM, ac.INST_STEM  # Default for multi-stem
        elif stem_pair == "Vocals/Instrumental":
            return ac.VOCAL_STEM, ac.INST_STEM
        elif stem_pair == "Other/No Other":
            return ac.OTHER_STEM, ac.secondary_stem(ac.OTHER_STEM)
        elif stem_pair == "Drums/No Drums":
            return ac.DRUM_STEM, ac.secondary_stem(ac.DRUM_STEM)
        elif stem_pair == "Bass/No Bass":
            return ac.BASS_STEM, ac.secondary_stem(ac.BASS_STEM)
        elif "/" in stem_pair:
            # Generic parsing for any "Primary/Secondary" format
            primary, secondary = stem_pair.split("/", 1)
            primary = primary.strip()
            secondary = secondary.strip()

            # Map common UI names to internal constants
            stem_name_map = {
                "Vocals": ac.VOCAL_STEM,
                "Vocal": ac.VOCAL_STEM,
                "Instrumental": ac.INST_STEM,
                "Instruments": ac.INST_STEM,
                "Bass": ac.BASS_STEM,
                "Drums": ac.DRUM_STEM,
                "Drum": ac.DRUM_STEM,
                "Other": ac.OTHER_STEM,
                "Others": ac.OTHER_STEM,
            }

            primary_stem = stem_name_map.get(primary, primary)
            secondary_stem = stem_name_map.get(secondary, secondary)

            return primary_stem, secondary_stem
        else:
            return ac.VOCAL_STEM, ac.INST_STEM  # Default fallback

    def _get_model_data_for_filtering(self, model_name: str, model_type: str):
        """Create minimal ModelData instance for filtering purposes."""
        try:
            from ..core.model_data import ModelData

            # Create minimal settings for ModelData creation
            temp_settings = {
                "chosen_process_method": self._get_process_method_for_model_type(
                    model_type
                ),
                "is_gpu_conversion": False,
                "is_normalization": False,
            }

            # Map model type to process method
            process_method = self._get_process_method_for_model_type(model_type)

            # Create ModelData instance for filtering
            model_data = ModelData.from_settings_dict(
                temp_settings,
                _model_name_override=model_name,
                _process_method_override=process_method,
                _is_secondary_model_instance=True,  # For filtering purposes
            )

            return model_data

        except Exception as e:
            logger.debug(f"Error creating ModelData for filtering {model_name}: {e}")
            return None

    def _get_process_method_for_model_type(self, model_type: str) -> str:
        """Map model type key to process method constant."""
        type_map = {
            ac.VR_ARCH_MODELS_KEY: ac.VR_ARCH_TYPE,
            ac.MDX_NET_MODELS_KEY: ac.MDX_ARCH_TYPE,
            ac.DEMUCS_MODELS_KEY: ac.DEMUCS_ARCH_TYPE,
        }
        return type_map.get(model_type, ac.VR_ARCH_TYPE)

    def _matches_stem(self, model_data, primary_stem: str, secondary_stem: str) -> bool:
        """Implement the exact matches_stem logic from UVR.py.

        This is the core filtering logic that determines if a model is compatible
        with the selected stem pair.
        """
        try:
            # Check if model's primary stem matches either primary or secondary stem
            primary_match = False
            if hasattr(model_data, "primary_stem") and model_data.primary_stem:
                primary_match = model_data.primary_stem in {
                    primary_stem,
                    secondary_stem,
                }

            # Check MDX stem compatibility (for 2-stem models only)
            mdx_stem_match = False
            if hasattr(model_data, "mdx_model_stems") and model_data.mdx_model_stems:
                if (
                    hasattr(model_data, "mdx_stem_count")
                    and getattr(model_data, "mdx_stem_count", 1) <= 2
                ):
                    mdx_stem_match = primary_stem in model_data.mdx_model_stems
                else:
                    # For models with more than 2 stems, check if primary stem is in the list
                    mdx_stem_match = primary_stem in model_data.mdx_model_stems

            # Check Demucs source compatibility
            demucs_source_match = False
            if (
                hasattr(model_data, "demucs_source_list")
                and model_data.demucs_source_list
            ):
                demucs_source_match = primary_stem.lower() in [
                    s.lower() for s in model_data.demucs_source_list
                ]

            # Return primary_match or mdx_stem_match if is_no_demucs else primary_match or primary_stem in model.mdx_model_stems
            # For ensemble filtering, we include all compatible models (not excluding Demucs)
            return primary_match or mdx_stem_match or demucs_source_match

        except Exception as e:
            logger.debug(f"Error in matches_stem check: {e}")
            return False

    @Slot(str)
    def on_ensemble_algorithm_changed(self, algorithm: str):
        """Handle algorithm change."""
        self._current_algorithm = algorithm

    @Slot(list)
    def on_models_selected_for_ensemble(self, selected_models: List[str]):
        """Handle model selection change."""
        self._currently_selected_models_for_ensemble = selected_models

    def on_clear_model_selection(self):
        """Clear model selection."""
        self.view.available_models_list.clearSelection()
        self.view.set_selected_models_in_list([])
        self._currently_selected_models_for_ensemble = []

    def get_settings(self):
        """Get current ensemble settings."""
        return {
            "chosen_process_method": ac.ENSEMBLE_MODE,  # Tell ModelData this is ensemble processing
            "ensemble_main_stem_pair": self._current_main_stem_pair,
            "ensemble_algorithm": self._current_algorithm,
            "ensemble_selected_models": self._currently_selected_models_for_ensemble,
        }
