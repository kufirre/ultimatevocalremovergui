from typing import Dict, List

import natsort
from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtWidgets import (  # Added QApplication for parent
    QInputDialog,
    QMessageBox,
)

from ..core import app_constants as ac
from ..core.uvr_core_adapter import UVRCoreAdapter


class EnsembleSettingsPresenter(QObject):
    """Presenter for Ensemble settings."""

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
        # Example structure for saved ensembles: {"UserEnsembleName": {"main_stem_pair": "...", "algorithm": "...", "models": [...]}}
        self._saved_ensembles: Dict[str, dict] = {}

        # Connect view signals
        self.view.main_stem_pair_changed.connect(self.on_main_stem_pair_changed)
        self.view.ensemble_algorithm_changed.connect(self.on_ensemble_algorithm_changed)
        self.view.selected_models_changed.connect(self.on_models_selected_for_ensemble)
        self.view.ensemble_action_requested.connect(self.handle_ensemble_action)

        self._initialize_settings()
        # Debug print removed

    def _initialize_settings(self):
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
        self.view.set_current_stem_pair(
            self._current_main_stem_pair
        )  # This will also emit main_stem_pair_changed
        # Ensure on_main_stem_pair_changed is robust to be called multiple times or sets state first
        self.on_main_stem_pair_changed(self._current_main_stem_pair)

        # TODO: Load saved ensembles from a persistent file (e.g., JSON)
        # self._load_saved_ensembles_from_store()
        # The view's action combo is now static, so we don't populate it with saved ensembles here.
        # Saved ensembles will be loaded via a dialog or a separate mechanism.

    def _filter_models_by_stem_compatibility(self, stem_pair: str) -> List[str]:
        """Filter models to only include those compatible with the selected stem pair.

        This mimics the filtering logic from UVR.py's model_list() function.
        """
        if stem_pair == "4 Stem Ensemble":
            # For 4-stem ensemble, include all Demucs 4-stem models and multi-stem MDX models
            filtered_models = []

            # Get all models and check which ones support 4-stem output
            for model_type, models in self._all_local_models_by_type.items():
                for model_name in models:
                    try:
                        # Check model capabilities through adapter
                        model_info = self.adapter.get_model_info(model_name, model_type)
                        if model_info:
                            # For Demucs models, check if they output 4 stems
                            if model_type == ac.DEMUCS_MODELS_KEY:
                                # Most Demucs models output 4 stems (vocals, drums, bass, other)
                                filtered_models.append(f"{model_type}:{model_name}")
                            # For MDX models, check if they output multiple stems
                            elif model_type == ac.MDX_NET_MODELS_KEY and hasattr(
                                model_info, "mdx_stem_count"
                            ):
                                if getattr(model_info, "mdx_stem_count", 0) >= 4:
                                    filtered_models.append(f"{model_type}:{model_name}")
                    except Exception:
                        # If we can't get model info, skip this model
                        continue

            return filtered_models

        elif stem_pair == "Multi-stem Ensemble":
            # Include all models for multi-stem ensemble
            all_models = []
            for model_type, models in self._all_local_models_by_type.items():
                for model_name in models:
                    all_models.append(f"{model_type}:{model_name}")
            return all_models

        else:
            # For specific stem pairs (Vocals/Instrumental, Bass/No Bass, etc.)
            # Parse the stem pair to get primary and secondary stems
            if "/" in stem_pair:
                primary_stem, secondary_stem = stem_pair.split("/", 1)
            else:
                primary_stem = stem_pair
                secondary_stem = f"No {primary_stem}"

            filtered_models = []

            for model_type, models in self._all_local_models_by_type.items():
                for model_name in models:
                    try:
                        # Check if model can produce the required stems
                        model_info = self.adapter.get_model_info(model_name, model_type)
                        if model_info:
                            model_can_produce_stems = False

                            # For VR models, check primary stem
                            if model_type == ac.VR_ARCH_MODELS_KEY:
                                if hasattr(model_info, "primary_stem"):
                                    model_primary = getattr(
                                        model_info, "primary_stem", ""
                                    )
                                    if model_primary in [primary_stem, secondary_stem]:
                                        model_can_produce_stems = True

                            # For MDX models, check if they can produce the required stems
                            elif model_type == ac.MDX_NET_MODELS_KEY:
                                if hasattr(model_info, "mdx_model_stems"):
                                    model_stems = getattr(
                                        model_info, "mdx_model_stems", []
                                    )
                                    if primary_stem in model_stems or any(
                                        stem in model_stems
                                        for stem in [primary_stem, secondary_stem]
                                    ):
                                        model_can_produce_stems = True
                                # Also check for common vocal/instrumental models
                                elif primary_stem in [ac.VOCAL_STEM, ac.INST_STEM]:
                                    # Most MDX models can do vocal/instrumental separation
                                    model_can_produce_stems = True

                            # For Demucs models, check if they output the required stem
                            elif model_type == ac.DEMUCS_MODELS_KEY:
                                # Demucs models typically output vocals, drums, bass, other
                                demucs_stems = [
                                    ac.VOCAL_STEM,
                                    ac.DRUM_STEM,
                                    ac.BASS_STEM,
                                    ac.OTHER_STEM,
                                ]
                                if primary_stem in demucs_stems:
                                    model_can_produce_stems = True

                            if model_can_produce_stems:
                                filtered_models.append(f"{model_type}:{model_name}")

                    except Exception:
                        # If we can't get model info, include it anyway (safer approach)
                        filtered_models.append(f"{model_type}:{model_name}")
                        continue

            return filtered_models

    @Slot(str)
    def handle_ensemble_action(self, action_text: str):
        # Debug print removed
        if action_text == ac.ENSEMBLE_ACTION_SAVE_AS:
            self.on_save_ensemble()
        elif action_text == ac.ENSEMBLE_ACTION_CLEAR_SELECTION:
            self.on_clear_model_selection()
        elif action_text == ac.ENSEMBLE_ACTION_LOAD:
            # Placeholder: In a real app, this would open a dialog to select a saved ensemble.
            # For now, let's just list available saved ensembles in a message box.
            saved_ensemble_names = natsort.natsorted(
                [
                    data.get("display_name", name)
                    for name, data in self._saved_ensembles.items()
                ]
            )
            if not saved_ensemble_names:
                QMessageBox.information(
                    self.view.window(),
                    "Load Ensemble",
                    "No saved ensembles available to load.",
                )
                return

            chosen_ensemble, ok = QInputDialog.getItem(
                self.view.window(),
                "Load Ensemble",
                "Select an ensemble to load:",
                saved_ensemble_names,
                0,  # current item index
                False,  # editable?
            )
            if ok and chosen_ensemble:
                self.on_load_ensemble(chosen_ensemble)
        # No 'else' needed here as the combo only contains predefined actions now.

    @Slot(str)
    def on_main_stem_pair_changed(self, stem_pair: str):
        # ... (Keep as before, ensure _current_algorithm is updated after set_ensemble_algorithms) ...
        # Debug print removed
        self._current_main_stem_pair = stem_pair

        if stem_pair == ac.ENSEMBLE_MAIN_STEM_OPTIONS[4]:  # "4 Stem Ensemble"
            self.view.set_ensemble_algorithms(ac.ENSEMBLE_ALGORITHM_4_STEM_OPTIONS)
        else:
            self.view.set_ensemble_algorithms(ac.ENSEMBLE_ALGORITHM_OPTIONS)

        if (
            self.view.algorithm_combo.count() > 0
        ):  # Update internal state after algorithms are set
            self._current_algorithm = self.view.algorithm_combo.itemText(0)
            self.view.set_current_algorithm(self._current_algorithm)  # Reflect in view

        # CRITICAL FIX: Filter models based on stem compatibility instead of showing all models
        filtered_models = self._filter_models_by_stem_compatibility(stem_pair)

        # Convert from "model_type:model_name" format back to just model names for display
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
        compatible_selected_models = []
        for selected_model in self._currently_selected_models_for_ensemble:
            if selected_model in unique_display_models:
                compatible_selected_models.append(selected_model)

        self._currently_selected_models_for_ensemble = compatible_selected_models
        self.view.set_selected_models_in_list(
            self._currently_selected_models_for_ensemble
        )

    @Slot(str)
    def on_ensemble_algorithm_changed(self, algorithm: str):  # Unchanged
        # Debug print removed
        self._current_algorithm = algorithm

    @Slot(list)
    def on_models_selected_for_ensemble(self, selected_models: List[str]):  # Unchanged
        # Debug print removed
        self._currently_selected_models_for_ensemble = selected_models

    # @Slot() # This is now triggered by handle_ensemble_action
    def on_save_ensemble(self):  # Keep internal method
        if not self._currently_selected_models_for_ensemble:
            QMessageBox.warning(
                self.view.window(),
                "Save Ensemble",
                "No models selected for the ensemble.",
            )
            return

        # Get MainWindow instance to use as parent for QInputDialog if possible
        parent_window = self.view.window()  # QWidget.window() gets the top-level window

        ensemble_name, ok = QInputDialog.getText(
            parent_window, "Save Ensemble", "Enter Ensemble Name:"
        )
        if ok and ensemble_name:
            clean_ensemble_name = ensemble_name.replace(" ", "_")

            if clean_ensemble_name in self._saved_ensembles:
                overwrite = QMessageBox.question(
                    parent_window,
                    "Overwrite Ensemble",
                    f"Ensemble '{ensemble_name}' already exists. Overwrite?",
                )
                if (
                    overwrite == QMessageBox.No or not overwrite
                ):  # Check for None if dialog is closed
                    return

            self._saved_ensembles[clean_ensemble_name] = {
                "display_name": ensemble_name,  # Store original display name too
                "main_stem_pair": self._current_main_stem_pair,
                "algorithm": self._current_algorithm,
                "models": self._currently_selected_models_for_ensemble,
            }
            # TODO: Save self._saved_ensembles to a persistent file
            # Debug print removed
            # The view's action combo is static, no need to update it with saved ensemble names.
            # The presenter will handle loading via a dialog.
            QMessageBox.information(
                self.view.window(),
                "Ensemble Saved",
                f"Ensemble '{ensemble_name}' has been saved.",
            )
        else:
            # Debug print removed
            pass  # Or log this event

    # This method is called by handle_ensemble_action after user selects from a dialog.
    def on_load_ensemble(
        self, ensemble_display_name_to_load: str
    ):  # Keep internal method
        if not ensemble_display_name_to_load:
            # Debug print removed
            return

        # Debug print removed

        # Find the internal key (name_with_underscores) from the display name
        internal_key_to_load = None
        for key, data in self._saved_ensembles.items():
            if data.get("display_name", key) == ensemble_display_name_to_load:
                internal_key_to_load = key
                break

        if not internal_key_to_load:
            QMessageBox.warning(
                self.view.window(),
                "Load Ensemble",
                f"Could not find configuration for ensemble: {ensemble_display_name_to_load}",
            )
            return

        saved_config = self._saved_ensembles.get(internal_key_to_load)
        if saved_config:
            self._current_main_stem_pair = saved_config["main_stem_pair"]
            self._current_algorithm = saved_config["algorithm"]
            self._currently_selected_models_for_ensemble = saved_config["models"]

            self.view.set_current_stem_pair(self._current_main_stem_pair)
            # on_main_stem_pair_changed will repopulate algorithms and available models
            # We need to ensure algorithm is set *after* algorithms are populated by stem_pair change
            # And models are selected *after* available models are populated

            # Defer setting algorithm and selected models until after stem pair change has propagated
            QTimer.singleShot(
                0, lambda: self.view.set_current_algorithm(self._current_algorithm)
            )
            QTimer.singleShot(
                0,
                lambda: self.view.set_selected_models_in_list(
                    self._currently_selected_models_for_ensemble
                ),
            )

            # Debug print removed
        else:
            # This case should ideally not be reached if lookup by display name worked
            QMessageBox.warning(
                self.view.window(),
                "Load Ensemble",
                f"Internal error finding config for: {ensemble_display_name_to_load}",
            )

    # @Slot() # This is now triggered by handle_ensemble_action
    def on_clear_model_selection(self):  # Keep internal method
        # Debug print removed
        self.view.available_models_list.clearSelection()  # This might be redundant if view handles it
        self.view.set_selected_models_in_list(
            []
        )  # Ensure presenter and view are in sync
        self._currently_selected_models_for_ensemble = []

    def get_settings(self):
        return {
            "ensemble_main_stem_pair": self._current_main_stem_pair,
            "ensemble_algorithm": self._current_algorithm,
            "ensemble_selected_models": self._currently_selected_models_for_ensemble,
        }
