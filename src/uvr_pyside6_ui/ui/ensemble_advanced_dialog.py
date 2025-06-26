"""Advanced Ensemble Configuration Dialog for UVR PySide6 application."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..core import app_constants as ac
from ..core.logger_utils import get_logger

logger = get_logger(__name__)


@dataclass
class LightweightModelInfo:
    """Lightweight model information for ensemble filtering without file I/O."""

    model_name: str
    model_type: str
    model_status: bool = True
    primary_stem: str = ac.VOCAL_STEM
    secondary_stem: str = ac.INST_STEM
    process_method: str = ac.VR_ARCH_TYPE
    mdx_model_stems: Optional[List[str]] = None
    mdx_stem_count: int = 2
    demucs_source_list: Optional[List[str]] = None
    demucs_stem_count: int = 4


class ModelInferenceEngine:
    """Engine for inferring model properties from names and types."""

    @staticmethod
    def _infer_primary_stem_from_name(model_name: str) -> str:
        """Infer primary stem from model name patterns."""
        name_lower = model_name.lower()
        if any(pattern in name_lower for pattern in ["inst", "instrumental", "music"]):
            return ac.INST_STEM
        if any(pattern in name_lower for pattern in ["bass"]):
            return ac.BASS_STEM
        if any(pattern in name_lower for pattern in ["drum"]):
            return ac.DRUM_STEM
        if any(pattern in name_lower for pattern in ["other"]):
            return ac.OTHER_STEM
        return ac.VOCAL_STEM

    @staticmethod
    def _infer_secondary_stem(primary_stem: str) -> str:
        """Get the secondary stem for a given primary stem."""
        return ac.secondary_stem(primary_stem)

    @staticmethod
    def _infer_mdx_stems(model_name: str) -> list:
        """Infer MDX model stems from name patterns."""
        name_lower = model_name.lower()
        if any(pattern in name_lower for pattern in ["4stem", "4_stem", "multi"]):
            return [ac.VOCAL_STEM, ac.DRUM_STEM, ac.BASS_STEM, ac.OTHER_STEM]
        primary_stem = ModelInferenceEngine._infer_primary_stem_from_name(model_name)
        return [primary_stem, ModelInferenceEngine._infer_secondary_stem(primary_stem)]

    @staticmethod
    def _infer_demucs_sources(model_name: str) -> list:
        """Infer Demucs source list from name patterns."""
        name_lower = model_name.lower()
        if any(pattern in name_lower for pattern in ["6stem", "6_stem"]):
            return [
                ac.VOCAL_STEM,
                ac.DRUM_STEM,
                ac.BASS_STEM,
                ac.OTHER_STEM,
                "piano",
                "guitar",
            ]
        if any(pattern in name_lower for pattern in ["2stem", "2_stem", "vocals"]):
            return [ac.VOCAL_STEM, ac.INST_STEM]
        return [ac.VOCAL_STEM, ac.DRUM_STEM, ac.BASS_STEM, ac.OTHER_STEM]

    @classmethod
    def create_lightweight_model_info(
        cls, model_name: str, model_type: str
    ) -> LightweightModelInfo:
        """Create lightweight model info for the given model."""
        primary_stem = cls._infer_primary_stem_from_name(model_name)
        secondary_stem = cls._infer_secondary_stem(primary_stem)

        info = LightweightModelInfo(
            model_name=model_name,
            model_type=model_type,
            primary_stem=primary_stem,
            secondary_stem=secondary_stem,
        )

        if model_type == ac.VR_ARCH_MODELS_KEY:
            info.process_method = ac.VR_ARCH_TYPE
        elif model_type == ac.MDX_NET_MODELS_KEY:
            info.process_method = ac.MDX_ARCH_TYPE
            info.mdx_model_stems = cls._infer_mdx_stems(model_name)
            info.mdx_stem_count = len(info.mdx_model_stems)
        elif model_type == ac.DEMUCS_MODELS_KEY:
            info.process_method = ac.DEMUCS_ARCH_TYPE
            info.demucs_source_list = cls._infer_demucs_sources(model_name)
            info.demucs_stem_count = len(info.demucs_source_list)

        return info


class EnsembleAdvancedDialog(QDialog):
    """Advanced dialog for comprehensive ensemble configuration."""

    settings_updated = Signal(dict)

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.current_settings = current_settings.copy()
        self._available_models_by_type: Dict[str, List[str]] = {}
        self._current_main_stem_pair: str = current_settings.get(
            "ensemble_main_stem_pair", ac.ENSEMBLE_MAIN_STEM_OPTIONS[0]
        )
        self._current_algorithm: str = current_settings.get(
            "ensemble_algorithm", ac.ENSEMBLE_ALGORITHM_OPTIONS[0]
        )
        self._currently_selected_models: List[str] = current_settings.get(
            "ensemble_selected_models", []
        )

        self._setup_ui()
        self._setup_connections()
        self._initialize_data()

    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Advanced Ensemble Settings")
        self.setWindowIcon(QIcon(ac.QRC_ICON_PATH))
        self.setModal(True)
        self.setMinimumSize(580, 600)
        self.setMaximumSize(650, 750)
        self.resize(600, 680)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Configuration Section
        config_group = QGroupBox("Ensemble Settings")
        config_layout = QVBoxLayout(config_group)

        # Stem Pair Selection
        stem_pair_layout = QHBoxLayout()
        stem_pair_label = QLabel("Main Stem Pair:")
        stem_pair_label.setMinimumWidth(100)
        self.stem_pair_combo = QComboBox()
        self.stem_pair_combo.addItems(ac.ENSEMBLE_MAIN_STEM_OPTIONS)
        self.stem_pair_combo.setCurrentText(self._current_main_stem_pair)
        stem_pair_layout.addWidget(stem_pair_label)
        stem_pair_layout.addWidget(self.stem_pair_combo, 1)
        config_layout.addLayout(stem_pair_layout)

        # Algorithm Selection
        algorithm_layout = QHBoxLayout()
        algorithm_label = QLabel("Ensemble Algorithm:")
        algorithm_label.setMinimumWidth(100)
        self.algorithm_combo = QComboBox()
        algorithm_layout.addWidget(algorithm_label)
        algorithm_layout.addWidget(self.algorithm_combo, 1)
        config_layout.addLayout(algorithm_layout)

        # Ensemble Options Checkboxes
        options_layout = QHBoxLayout()

        # Save all outputs checkbox
        self.save_all_outputs_checkbox = QCheckBox(ac.SAVE_ALL_OUTPUTS_TEXT)
        self.save_all_outputs_checkbox.setChecked(
            self.current_settings.get("save_all_outputs", True)
        )
        self.save_all_outputs_checkbox.setToolTip(
            "Save all individual ensemble outputs"
        )

        # Append ensemble name checkbox
        self.append_ensemble_name_checkbox = QCheckBox(ac.APPEND_ENSEMBLE_NAME_TEXT)
        self.append_ensemble_name_checkbox.setChecked(
            self.current_settings.get("append_ensemble_name", False)
        )
        self.append_ensemble_name_checkbox.setToolTip(
            "Add ensemble name to output filename"
        )

        # Use waveform checkbox
        self.use_waveform_checkbox = QCheckBox(ac.WAVEFORM_ENSEMBLE_TEXT)
        self.use_waveform_checkbox.setChecked(
            self.current_settings.get("use_waveform_ensemble", False)
        )
        self.use_waveform_checkbox.setToolTip(
            "Use waveform ensemble instead of spectrogram"
        )

        options_layout.addWidget(self.save_all_outputs_checkbox)
        options_layout.addWidget(self.append_ensemble_name_checkbox)
        options_layout.addWidget(self.use_waveform_checkbox)
        options_layout.addStretch()

        config_layout.addLayout(options_layout)

        main_layout.addWidget(config_group)

        # Model Selection Section
        models_group = QGroupBox("Model Selection")
        models_layout = QHBoxLayout(models_group)

        # Available Models
        available_layout = QVBoxLayout()
        available_layout.addWidget(QLabel("Available Models (Local Library)"))
        self.available_models_list = QListWidget()
        self.available_models_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.available_models_list.setMinimumHeight(280)
        available_layout.addWidget(self.available_models_list)
        models_layout.addLayout(available_layout, 1)

        # Transfer Buttons
        transfer_layout = QVBoxLayout()
        transfer_layout.addStretch()

        self.add_button = QPushButton()
        self.add_button.setMaximumSize(35, 28)
        self.add_button.setToolTip("Add selected models to ensemble")
        try:
            add_icon = QIcon(":/uvr/img/right.png")
            if not add_icon.isNull():
                self.add_button.setIcon(add_icon)
                self.add_button.setIconSize(QSize(16, 16))
            else:
                self.add_button.setText(">>")
        except Exception:
            self.add_button.setText(">>")

        self.remove_button = QPushButton()
        self.remove_button.setMaximumSize(35, 28)
        self.remove_button.setToolTip("Remove selected models from ensemble")
        try:
            remove_icon = QIcon(":/uvr/img/left.png")
            if not remove_icon.isNull():
                self.remove_button.setIcon(remove_icon)
                self.remove_button.setIconSize(QSize(16, 16))
            else:
                self.remove_button.setText("<<")
        except Exception:
            self.remove_button.setText("<<")

        transfer_layout.addWidget(self.add_button)
        transfer_layout.addSpacing(8)
        transfer_layout.addWidget(self.remove_button)
        transfer_layout.addStretch()
        models_layout.addLayout(transfer_layout)

        # Selected Models
        selected_layout = QVBoxLayout()
        selected_layout.addWidget(QLabel("Models for Ensemble"))
        self.selected_models_list = QListWidget()
        self.selected_models_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.selected_models_list.setMinimumHeight(280)
        selected_layout.addWidget(self.selected_models_list)
        models_layout.addLayout(selected_layout, 1)

        main_layout.addWidget(models_group)

        # Ensemble Management Section
        management_group = QGroupBox("Ensemble Management")
        management_layout = QVBoxLayout(management_group)

        # Saved Ensembles
        saved_layout = QHBoxLayout()
        saved_layout.addWidget(QLabel("Saved Ensembles:"))
        self.saved_ensembles_combo = QComboBox()
        self.saved_ensembles_combo.setMinimumWidth(150)
        saved_layout.addWidget(self.saved_ensembles_combo, 1)

        # Management Buttons
        mgmt_buttons_layout = QHBoxLayout()
        self.load_ensemble_btn = QPushButton("Load")
        self.save_ensemble_btn = QPushButton("Save As...")
        self.delete_ensemble_btn = QPushButton("Delete")
        self.clear_selection_btn = QPushButton("Clear")

        mgmt_buttons_layout.addWidget(self.load_ensemble_btn)
        mgmt_buttons_layout.addWidget(self.save_ensemble_btn)
        mgmt_buttons_layout.addWidget(self.delete_ensemble_btn)
        mgmt_buttons_layout.addWidget(self.clear_selection_btn)
        mgmt_buttons_layout.addStretch()

        management_layout.addLayout(saved_layout)
        management_layout.addLayout(mgmt_buttons_layout)
        main_layout.addWidget(management_group)

        # Dialog Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setMinimumWidth(70)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setMinimumWidth(70)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(70)

        button_layout.addWidget(self.apply_btn)
        button_layout.addSpacing(8)
        button_layout.addWidget(self.ok_btn)
        button_layout.addSpacing(5)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

    def _setup_connections(self):
        """Set up signal connections."""
        # Configuration connections
        self.stem_pair_combo.currentTextChanged.connect(self._on_stem_pair_changed)
        self.algorithm_combo.currentTextChanged.connect(self._on_algorithm_changed)

        # Model transfer connections
        self.add_button.clicked.connect(self._add_models_to_ensemble)
        self.remove_button.clicked.connect(self._remove_models_from_ensemble)
        self.available_models_list.itemDoubleClicked.connect(
            self._add_models_to_ensemble
        )

        # Management connections
        self.load_ensemble_btn.clicked.connect(self._load_ensemble)
        self.save_ensemble_btn.clicked.connect(self._save_ensemble)
        self.delete_ensemble_btn.clicked.connect(self._delete_ensemble)
        self.clear_selection_btn.clicked.connect(self._clear_selection)

        # Dialog buttons
        self.apply_btn.clicked.connect(self._apply_settings)
        self.ok_btn.clicked.connect(self._ok_clicked)
        self.cancel_btn.clicked.connect(self.reject)

    def _initialize_data(self):
        """Initialize data and UI state."""
        # Load available models (this would need to be passed from main app)
        # For now, we'll use placeholder data
        self._load_available_models()
        self._update_algorithm_options()
        self._load_saved_ensembles()
        self._update_model_lists()
        self._update_selected_models()

    def _load_available_models(self):
        """Load available models from the adapter."""
        # This should be populated by the main application
        # For now, using placeholder data
        self._available_models_by_type = {
            ac.VR_ARCH_MODELS_KEY: ["VR Model 1", "VR Model 2"],
            ac.MDX_NET_MODELS_KEY: ["MDX Model 1", "MDX Model 2"],
            ac.DEMUCS_MODELS_KEY: ["Demucs Model 1", "Demucs Model 2"],
        }

    def _on_stem_pair_changed(self, stem_pair: str):
        """Handle stem pair selection change."""
        self._current_main_stem_pair = stem_pair
        self._update_algorithm_options()
        self._update_model_lists()

        # Filter currently selected models to only include compatible ones
        filtered_models = self._filter_models_by_stem_compatibility(stem_pair)
        display_models = []
        for model_entry in filtered_models:
            if ":" in model_entry:
                _, model_name = model_entry.split(":", 1)
                display_models.append(model_name)
            else:
                display_models.append(model_entry)

        # Remove incompatible models from current selection
        compatible_selected_models = [
            model
            for model in self._currently_selected_models
            if model in display_models
        ]
        self._currently_selected_models = compatible_selected_models
        self._update_selected_models()

    def _on_algorithm_changed(self, algorithm: str):
        """Handle algorithm selection change."""
        self._current_algorithm = algorithm

    def _update_algorithm_options(self):
        """Update algorithm options based on stem pair selection."""
        self.algorithm_combo.clear()

        if self._current_main_stem_pair == "4 Stem Ensemble":
            # 4-stem ensembles use simpler algorithm options
            algorithms = ac.ENSEMBLE_ALGORITHM_4_STEM_OPTIONS
        else:
            # Standard 2-stem ensembles use full algorithm options
            algorithms = ac.ENSEMBLE_ALGORITHM_OPTIONS

        self.algorithm_combo.addItems(algorithms)

        if self._current_algorithm in algorithms:
            self.algorithm_combo.setCurrentText(self._current_algorithm)
        else:
            self._current_algorithm = algorithms[0] if algorithms else ""
            if algorithms:
                self.algorithm_combo.setCurrentText(self._current_algorithm)

    def _update_model_lists(self):
        """Update available models list based on stem pair selection."""
        self.available_models_list.clear()

        # Apply stem filtering based on the selected stem pair
        filtered_models = self._filter_models_by_stem_compatibility(
            self._current_main_stem_pair
        )

        # Extract display names from the filtered models
        display_models = []
        for model_entry in filtered_models:
            if ":" in model_entry:
                _, model_name = model_entry.split(":", 1)
                display_models.append(model_name)
            else:
                display_models.append(model_entry)

        # Sort naturally and remove duplicates
        import natsort

        unique_display_models = natsort.natsorted(
            list(set(display_models)), key=str.lower
        )

        for model in unique_display_models:
            self.available_models_list.addItem(model)

    def _filter_models_by_stem_compatibility(self, stem_pair: str):
        """Filter models to only include those compatible with the selected stem pair."""
        # Parse stem pair to get primary and secondary stems
        primary_stem, secondary_stem = self._parse_stem_pair(stem_pair)

        # Determine filtering mode based on stem pair
        is_4_stem_check = stem_pair == "4 Stem Ensemble"
        is_multi_stem = stem_pair == "Multi-stem Ensemble"

        filtered_models = []

        # Get all available models with their metadata
        for model_type, models in self._available_models_by_type.items():
            for model_name in models:
                try:
                    # Create lightweight model info for filtering
                    model_info = self._get_model_data_for_filtering(
                        model_name, model_type
                    )

                    if not model_info or not model_info.model_status:
                        continue

                    # Apply the filtering logic
                    if is_multi_stem:
                        # Multi-stem ensemble: include all models
                        filtered_models.append(f"{model_type}:{model_name}")
                    elif is_4_stem_check:
                        # 4-stem ensemble: only models with 4+ stems
                        if (
                            hasattr(model_info, "demucs_stem_count")
                            and model_info.demucs_stem_count == 4
                        ) or (
                            hasattr(model_info, "mdx_model_stems")
                            and len(model_info.mdx_model_stems) == 4
                        ):
                            filtered_models.append(f"{model_type}:{model_name}")
                    else:
                        # Standard 2-stem filtering using matches_stem logic
                        if self._matches_stem(model_info, primary_stem, secondary_stem):
                            filtered_models.append(f"{model_type}:{model_name}")

                except Exception as e:
                    logger.debug(
                        f"Error checking model compatibility for {model_name}: {e}"
                    )
                    continue

        return filtered_models

    def _parse_stem_pair(self, stem_pair: str):
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

    def _get_model_data_for_filtering(
        self, model_name: str, model_type: str
    ) -> Optional[LightweightModelInfo]:
        """Create lightweight model compatibility checker without full ModelData instantiation."""
        try:
            return ModelInferenceEngine.create_lightweight_model_info(
                model_name, model_type
            )
        except Exception as e:
            logger.debug(
                f"Error creating lightweight model info for filtering {model_name}: {e}"
            )
            return None

    def _matches_stem(self, model_info, primary_stem: str, secondary_stem: str) -> bool:
        """Determines if a model is compatible with the selected stem pair."""
        try:
            # PRIMARY MATCH: Check if model's primary stem matches either primary or secondary stem
            primary_match = False
            if hasattr(model_info, "primary_stem") and model_info.primary_stem:
                primary_match = model_info.primary_stem in {
                    primary_stem,
                    secondary_stem,
                }

            # MDX STEM MATCH: Check MDX stem compatibility
            mdx_stem_match = False
            if hasattr(model_info, "mdx_model_stems") and model_info.mdx_model_stems:
                mdx_stem_match = primary_stem in model_info.mdx_model_stems

            # DEMUCS SOURCE MATCH: Check Demucs source compatibility
            demucs_source_match = False
            if (
                hasattr(model_info, "demucs_source_list")
                and model_info.demucs_source_list
            ):
                demucs_source_match = primary_stem.lower() in [
                    s.lower() for s in model_info.demucs_source_list
                ]

            return primary_match or mdx_stem_match or demucs_source_match

        except Exception as e:
            logger.debug(f"Error in matches_stem check: {e}")
            return False

    def _update_selected_models(self):
        """Update the selected models list."""
        self.selected_models_list.clear()
        for model in self._currently_selected_models:
            self.selected_models_list.addItem(model)

    def _add_models_to_ensemble(self):
        """Add selected models from available list to ensemble."""
        selected_items = self.available_models_list.selectedItems()
        for item in selected_items:
            model_name = item.text()
            if model_name not in self._currently_selected_models:
                self._currently_selected_models.append(model_name)

        self._update_selected_models()

    def _remove_models_from_ensemble(self):
        """Remove selected models from ensemble."""
        selected_items = self.selected_models_list.selectedItems()
        for item in selected_items:
            model_name = item.text()
            if model_name in self._currently_selected_models:
                self._currently_selected_models.remove(model_name)

        self._update_selected_models()

    def _clear_selection(self):
        """Clear all selected models."""
        self._currently_selected_models.clear()
        self._update_selected_models()

    def _load_saved_ensembles(self):
        """Load saved ensembles from filesystem."""
        self.saved_ensembles_combo.clear()
        self.saved_ensembles_combo.addItem("--- Select Saved Ensemble ---")

        ensemble_cache_dir = Path("config/saved_ensembles")
        if ensemble_cache_dir.exists():
            for json_file in ensemble_cache_dir.glob("*.json"):
                try:
                    display_name = json_file.stem.replace("_", " ")
                    self.saved_ensembles_combo.addItem(display_name)
                except Exception as e:
                    logger.warning(f"Error loading ensemble {json_file}: {e}")

    def _load_ensemble(self):
        """Load selected ensemble configuration."""
        ensemble_name = self.saved_ensembles_combo.currentText()
        if ensemble_name == "--- Select Saved Ensemble ---":
            return

        ensemble_file = f"config/saved_ensembles/{ensemble_name.replace(' ', '_')}.json"
        if not os.path.exists(ensemble_file):
            QMessageBox.warning(
                self, "Error", f"Ensemble file not found: {ensemble_name}"
            )
            return

        try:
            with open(ensemble_file, "r") as f:
                ensemble_data = json.load(f)

            self._current_main_stem_pair = ensemble_data.get(
                "ensemble_main_stem", self._current_main_stem_pair
            )
            self._current_algorithm = ensemble_data.get(
                "ensemble_type", self._current_algorithm
            )
            self._currently_selected_models = ensemble_data.get("selected_models", [])

            # Update UI
            self.stem_pair_combo.setCurrentText(self._current_main_stem_pair)
            self._update_algorithm_options()
            self.algorithm_combo.setCurrentText(self._current_algorithm)
            self._update_model_lists()
            self._update_selected_models()

            QMessageBox.information(
                self, "Success", f"Loaded ensemble: {ensemble_name}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load ensemble: {e}")

    def _save_ensemble(self):
        """Save current ensemble configuration."""
        if not self._currently_selected_models:
            QMessageBox.warning(self, "Warning", "No models selected for ensemble.")
            return

        name, ok = QInputDialog.getText(self, "Save Ensemble", "Enter ensemble name:")
        if not ok or not name.strip():
            return

        if not all(c.isalnum() or c in " -_" for c in name):
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Only letters, numbers, spaces, and dashes allowed.",
            )
            return

        name = name.strip()
        ensemble_data = {
            "ensemble_main_stem": self._current_main_stem_pair,
            "ensemble_type": self._current_algorithm,
            "selected_models": self._currently_selected_models.copy(),
        }

        ensemble_dir = Path("config/saved_ensembles")
        ensemble_dir.mkdir(parents=True, exist_ok=True)
        ensemble_file = ensemble_dir / f"{name.replace(' ', '_')}.json"

        try:
            with open(ensemble_file, "w") as f:
                json.dump(ensemble_data, f, indent=2)

            QMessageBox.information(self, "Success", f"Ensemble saved as: {name}")
            self._load_saved_ensembles()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save ensemble: {e}")

    def _delete_ensemble(self):
        """Delete selected ensemble."""
        ensemble_name = self.saved_ensembles_combo.currentText()
        if ensemble_name == "--- Select Saved Ensemble ---":
            QMessageBox.warning(self, "Warning", "Please select an ensemble to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the ensemble '{ensemble_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            ensemble_file = (
                f"config/saved_ensembles/{ensemble_name.replace(' ', '_')}.json"
            )
            try:
                if os.path.exists(ensemble_file):
                    os.remove(ensemble_file)
                    QMessageBox.information(
                        self, "Success", f"Deleted ensemble: {ensemble_name}"
                    )
                    self._load_saved_ensembles()
                else:
                    QMessageBox.warning(self, "Error", "Ensemble file not found.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete ensemble: {e}")

    def _apply_settings(self):
        """Apply current settings without closing dialog."""
        settings = self._get_current_settings()
        self.settings_updated.emit(settings)

    def _ok_clicked(self):
        """Handle OK button click."""
        self._apply_settings()
        self.accept()

    def _get_current_settings(self) -> dict:
        """Get current ensemble configuration as dictionary."""
        return {
            "ensemble_main_stem_pair": self._current_main_stem_pair,
            "ensemble_algorithm": self._current_algorithm,
            "ensemble_selected_models": self._currently_selected_models.copy(),
            "save_all_outputs": self.save_all_outputs_checkbox.isChecked(),
            "append_ensemble_name": self.append_ensemble_name_checkbox.isChecked(),
            "use_waveform_ensemble": self.use_waveform_checkbox.isChecked(),
        }

    def set_available_models(self, models_by_type: Dict[str, List[str]]):
        """Set available models from external source."""
        self._available_models_by_type = models_by_type.copy()
        self._update_model_lists()
