"""
Ensemble Persistence Manager for UVR PySide6 application.

This module handles saving, loading, and managing ensemble configurations.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from . import app_constants as ac
from .logger_utils import get_logger

logger = get_logger(__name__)


class EnsemblePersistenceManager(QObject):
    """
    Manages ensemble configuration persistence.
    """

    # Signals for UI updates
    ensembles_loaded = Signal(list)  # List of available ensemble names
    ensemble_saved = Signal(str)  # Name of saved ensemble
    ensemble_deleted = Signal(str)  # Name of deleted ensemble
    error_occurred = Signal(str)  # Error message

    def __init__(self, ensemble_cache_dir: Optional[Path] = None):
        super().__init__()

        # Use provided directory or default
        self.ensemble_cache_dir = Path(
            ensemble_cache_dir or Path("config") / "saved_ensembles"
        )

        # Ensure directory exists
        self.ensemble_cache_dir.mkdir(parents=True, exist_ok=True)

        # Create placeholder file if directory is empty
        placeholder_file = self.ensemble_cache_dir / "saved_ensembles_go_here.txt"
        if not any(self.ensemble_cache_dir.iterdir()) and not placeholder_file.exists():
            placeholder_file.write_text("saved_ensembles_go_here\n")

    def save_ensemble(
        self,
        name: str,
        main_stem_pair: str,
        algorithm: str,
        selected_models: List[str],
        additional_settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save ensemble configuration to JSON file.

        Args:
            name: Display name for the ensemble
            main_stem_pair: Selected stem pair (e.g., "Vocals/Instrumental")
            algorithm: Ensemble algorithm (e.g., "Average/Average")
            selected_models: List of selected model names
            additional_settings: Optional additional settings to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate inputs
            if not self._validate_ensemble_data(
                name, main_stem_pair, algorithm, selected_models
            ):
                return False

            # Clean name for filesystem
            clean_name = name.replace(" ", "_")
            ensemble_file = self.ensemble_cache_dir / f"{clean_name}.json"

            # Create ensemble data structure
            ensemble_data = {
                "ensemble_main_stem": main_stem_pair,
                "ensemble_type": algorithm,
                "selected_models": selected_models.copy(),
            }

            # Add additional settings if provided
            if additional_settings:
                ensemble_data.update(additional_settings)

            # Add metadata for enhanced functionality
            ensemble_data["_metadata"] = {
                "display_name": name,  # Store original display name
                "version": "2.0",  # Version for future compatibility
                "created_by": "UVR_PySide6",  # Source identification
            }

            # Write to file
            with open(ensemble_file, "w", encoding="utf-8") as f:
                json.dump(ensemble_data, f, indent=4, ensure_ascii=False)

            logger.info(f"Successfully saved ensemble: {name} -> {ensemble_file}")
            self.ensemble_saved.emit(name)
            return True

        except Exception as e:
            error_msg = f"Failed to save ensemble '{name}': {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def load_ensemble(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load ensemble configuration from JSON file.

        Args:
            name: Display name of the ensemble to load

        Returns:
            Dictionary containing ensemble configuration, or None if failed
        """
        try:
            # Handle both display name and clean name formats
            clean_name = name.replace(" ", "_")
            ensemble_file = self.ensemble_cache_dir / f"{clean_name}.json"

            if not ensemble_file.exists():
                # Try with original name in case it's already clean
                ensemble_file = self.ensemble_cache_dir / f"{name}.json"
                if not ensemble_file.exists():
                    logger.warning(f"Ensemble file not found: {name}")
                    return None

            # Load and validate data
            with open(ensemble_file, "r", encoding="utf-8") as f:
                ensemble_data = json.load(f)

            # Validate loaded data structure
            if not self._validate_loaded_ensemble_data(ensemble_data):
                logger.error(f"Invalid ensemble data structure in: {ensemble_file}")
                return None

            # Normalize data for consistency (handling both old and new formats)
            normalized_data = self._normalize_ensemble_data(ensemble_data, name)

            logger.info(f"Successfully loaded ensemble: {name}")
            return normalized_data

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in ensemble file '{name}': {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None
        except Exception as e:
            error_msg = f"Failed to load ensemble '{name}': {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return None

    def get_available_ensembles(self) -> List[Dict[str, str]]:
        """
        Get list of available saved ensembles.

        Returns:
            List of dictionaries with 'name' and 'display_name' keys
        """
        ensembles = []

        try:
            if not self.ensemble_cache_dir.exists():
                return ensembles

            for json_file in self.ensemble_cache_dir.glob("*.json"):
                try:
                    # Load metadata to get display name
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Get display name from metadata or derive from filename
                    display_name = data.get("_metadata", {}).get(
                        "display_name"
                    ) or json_file.stem.replace("_", " ")

                    ensembles.append(
                        {
                            "name": json_file.stem,
                            "display_name": display_name,
                            "file_path": str(json_file),
                        }
                    )

                except Exception as e:
                    logger.warning(
                        f"Error reading ensemble metadata from {json_file}: {e}"
                    )
                    # Fallback to filename-based display name
                    ensembles.append(
                        {
                            "name": json_file.stem,
                            "display_name": json_file.stem.replace("_", " "),
                            "file_path": str(json_file),
                        }
                    )

            # Sort by display name for consistent UI presentation
            ensembles.sort(key=lambda x: x["display_name"].lower())

            logger.debug(f"Found {len(ensembles)} saved ensembles")
            self.ensembles_loaded.emit([e["display_name"] for e in ensembles])
            return ensembles

        except Exception as e:
            error_msg = f"Failed to get available ensembles: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []

    def _validate_ensemble_data(
        self, name: str, main_stem_pair: str, algorithm: str, selected_models: List[str]
    ) -> bool:
        """
        Validate ensemble data before saving.

        """
        # Check name validity
        if not name or not name.strip():
            self.error_occurred.emit("Ensemble name cannot be empty")
            return False

        # Check for invalid characters
        if not all(c.isalnum() or c in " -_" for c in name):
            self.error_occurred.emit("Ensemble name contains invalid characters")
            return False

        # Check main stem pair
        if not main_stem_pair or main_stem_pair == ac.ENSEMBLE_MAIN_STEM_OPTIONS[0]:
            self.error_occurred.emit("Please select a valid stem pair")
            return False

        # Check algorithm
        if not algorithm or algorithm not in ac.ENSEMBLE_ALGORITHM_OPTIONS:
            self.error_occurred.emit("Please select a valid ensemble algorithm")
            return False

        # Check selected models (minimum 2 for ensemble)
        if not selected_models or len(selected_models) < 2:
            self.error_occurred.emit("Please select at least 2 models for ensemble")
            return False

        return True

    def _validate_loaded_ensemble_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate loaded ensemble data structure.
        """
        required_keys = ["ensemble_main_stem", "ensemble_type", "selected_models"]

        for key in required_keys:
            if key not in data:
                logger.error(f"Missing required key in ensemble data: {key}")
                return False

        # Validate selected_models is a list
        if not isinstance(data["selected_models"], list):
            logger.error("selected_models must be a list")
            return False

        return True

    def _normalize_ensemble_data(
        self, data: Dict[str, Any], name: str
    ) -> Dict[str, Any]:
        """
        Normalize ensemble data for consistent format.
        """
        normalized = {
            # Core ensemble data
            "ensemble_main_stem": data.get("ensemble_main_stem", ""),
            "ensemble_type": data.get("ensemble_type", ""),
            "selected_models": data.get("selected_models", []),
            # Normalized keys for modern interface
            "ensemble_main_stem_pair": data.get("ensemble_main_stem", ""),
            "ensemble_algorithm": data.get("ensemble_type", ""),
            "ensemble_selected_models": data.get("selected_models", []),
            # Metadata
            "_metadata": data.get(
                "_metadata",
                {
                    "display_name": name,
                    "version": "1.0",  # Legacy format
                    "created_by": "UVR_Legacy",
                },
            ),
        }

        # Include any additional settings
        for key, value in data.items():
            if key not in normalized and not key.startswith("_"):
                normalized[key] = value

        return normalized
