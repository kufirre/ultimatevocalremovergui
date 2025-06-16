"""Advanced Ensemble Configuration Dialog for UVR PySide6 application."""

import json
import os
from pathlib import Path
from typing import Dict, List

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

        # Determine which models are compatible with the selected stem pair
        compatible_models = []

        # This logic should match the original ensemble filtering logic
        for model_type, models in self._available_models_by_type.items():
            compatible_models.extend(models)

        # Sort naturally
        import natsort

        compatible_models = natsort.natsorted(compatible_models, key=str.lower)

        for model in compatible_models:
            self.available_models_list.addItem(model)

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

        ensemble_cache_dir = Path("gui_data/saved_ensembles")
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

        ensemble_file = (
            f"gui_data/saved_ensembles/{ensemble_name.replace(' ', '_')}.json"
        )
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

        # Validate name
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

        # Ensure directory exists
        ensemble_dir = Path("gui_data/saved_ensembles")
        ensemble_dir.mkdir(parents=True, exist_ok=True)

        ensemble_file = ensemble_dir / f"{name.replace(' ', '_')}.json"

        try:
            with open(ensemble_file, "w") as f:
                json.dump(ensemble_data, f, indent=2)

            QMessageBox.information(self, "Success", f"Ensemble saved as: {name}")
            self._load_saved_ensembles()  # Refresh the dropdown

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
                f"gui_data/saved_ensembles/{ensemble_name.replace(' ', '_')}.json"
            )
            try:
                if os.path.exists(ensemble_file):
                    os.remove(ensemble_file)
                    QMessageBox.information(
                        self, "Success", f"Deleted ensemble: {ensemble_name}"
                    )
                    self._load_saved_ensembles()  # Refresh the dropdown
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
