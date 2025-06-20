"""
Utility functions for model management and scanning.
This module provides shared functionality without circular dependencies.
"""

import json
from pathlib import Path
from typing import List, Optional

from . import app_constants as ac
from .logger_utils import get_logger

logger = get_logger(__name__)

# Import ModelData here to avoid in-method imports
# Note: This may cause circular import in some cases, in which case the import
# should be moved back inside the function
try:
    from .model_data import ModelData
except ImportError:
    # If circular import occurs, we'll handle it in the function
    ModelData = None


def get_project_root() -> Path:
    """Get the project root directory."""
    try:
        return Path(__file__).resolve().parents[3]
    except IndexError:
        return Path.cwd()


def get_models_dir_paths():
    """Get the model directory paths."""
    models_dir_path = get_project_root() / "models"
    return {
        ac.VR_ARCH_TYPE: models_dir_path / ac.MODEL_TYPE_SUBDIRS[ac.VR_ARCH_MODELS_KEY],
        ac.MDX_ARCH_TYPE: models_dir_path
        / ac.MODEL_TYPE_SUBDIRS[ac.MDX_NET_MODELS_KEY],
        ac.DEMUCS_ARCH_TYPE: models_dir_path
        / ac.MODEL_TYPE_SUBDIRS[ac.DEMUCS_MODELS_KEY],
    }


def scan_models_directory(model_type: str) -> List[str]:
    """Scan a model directory and return available model display names."""
    model_dirs = get_models_dir_paths()
    model_dir = model_dirs.get(model_type)

    if not model_dir or not model_dir.exists():
        return []

    # Define extensions for each model type using app constants
    extensions_map = {
        ac.VR_ARCH_TYPE: ac.VR_ARCH_SCAN_EXTENSIONS,
        ac.MDX_ARCH_TYPE: ac.MDX_SCAN_EXTENSIONS,
        ac.DEMUCS_ARCH_TYPE: ac.DEMUCS_LEGACY_SCAN_EXTENSIONS
        + ac.DEMUCS_V3_V4_SCAN_EXTENSIONS,
    }

    extensions = extensions_map.get(model_type, [])
    scanned_identifiers = []

    try:
        # Scan for file identifiers (stems without extension, or full filename for specific cases)
        if model_type == ac.VR_ARCH_TYPE:
            scanned_identifiers = _scan_path_for_identifiers(
                model_dir, extensions, recursive=True
            )
        elif model_type == ac.MDX_ARCH_TYPE:
            scanned_identifiers = _scan_path_for_identifiers(
                model_dir, extensions, is_mdx_ckpt_special_case=True, recursive=True
            )
        elif model_type == ac.DEMUCS_ARCH_TYPE:
            # Scan legacy models in main directory
            ids_legacy = _scan_path_for_identifiers(
                model_dir, ac.DEMUCS_LEGACY_SCAN_EXTENSIONS, recursive=False
            )
            # Scan v3/v4 models in subdirectory
            v3_v4_repo_dir = model_dir / "v3_v4_repo"
            ids_v3_v4 = _scan_path_for_identifiers(
                v3_v4_repo_dir, ac.DEMUCS_V3_V4_SCAN_EXTENSIONS, recursive=True
            )
            scanned_identifiers = list(set(ids_legacy + ids_v3_v4))

        if not scanned_identifiers:
            return []

        # Apply display name mapping and clean up
        final_display_names = []
        name_mapper = {}

        # Load name mapper for MDX and Demucs
        if model_type in [ac.MDX_ARCH_TYPE, ac.DEMUCS_ARCH_TYPE]:
            name_mapper = _load_name_mapper(model_dir)

        for identifier in scanned_identifiers:
            display_name, was_mapped = _get_display_name_from_mapper(
                identifier, name_mapper
            )

            if was_mapped:  # Successfully mapped to a display name
                final_display_names.append(display_name)
            elif not name_mapper:  # No mapper exists (like for VR models)
                # Strip file extensions for cleaner display
                clean_name = _strip_model_extension(identifier)
                final_display_names.append(clean_name)
            else:  # Mapper exists but model wasn't found - add the identifier anyway
                # This ensures newly downloaded models show up even if not in mapper
                clean_name = _strip_model_extension(identifier)
                final_display_names.append(clean_name)

        # Use natsort for natural sorting (handles numbers properly)
        try:
            import natsort

            return natsort.natsorted(list(set(final_display_names)))
        except ImportError:
            return sorted(list(set(final_display_names)))

    except Exception as e:
        logger.warning(f"Error scanning {model_type} models directory: {e}")
        return []


def _scan_path_for_identifiers(
    scan_path: Path,
    extensions: list,
    is_mdx_ckpt_special_case: bool = False,
    recursive: bool = False,
) -> List[str]:
    """Scan a path for model identifiers based on file extensions."""
    identifiers = []
    if not scan_path or not scan_path.is_dir():
        return identifiers

    # Define excluded filenames (from original adapter)
    excluded_filenames = [
        "model_data",
        "model_name_mapper",
        "download_links",
        "mixer",
        "mixer_val",
    ]

    glob_pattern = "**/*" if recursive else "*"
    for item in scan_path.glob(glob_pattern):
        if item.is_file() and item.suffix.lower() in extensions:
            file_stem = item.stem
            if file_stem in excluded_filenames:
                continue
            identifier = file_stem
            if is_mdx_ckpt_special_case and item.suffix.lower() == ".ckpt":
                identifier = item.name  # Keep full filename for .ckpt files
            identifiers.append(identifier)
    return list(set(identifiers))


def _load_name_mapper(model_dir: Path) -> dict:
    """Load name mapper from model directory."""
    mapper_file_path = model_dir / "model_data" / "model_name_mapper.json"
    if mapper_file_path.is_file():
        try:
            with open(mapper_file_path, encoding="utf-8") as f:
                mapper_content = json.load(f)
                return mapper_content
        except json.JSONDecodeError as e:
            logger.error(
                f"JSONDecodeError when loading name mapper from {mapper_file_path}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error loading name mapper from {mapper_file_path}: {e}"
            )
    else:
        logger.debug(f"Name mapper file not found at: {mapper_file_path}")
    return {}


def _get_display_name_from_mapper(
    scanned_identifier: str, name_mapper: dict
) -> tuple[str, bool]:
    """Get display name from mapper, returns (display_name, was_mapped)."""
    if not name_mapper:
        return scanned_identifier, False

    for mapper_key_filename, display_name_from_mapper in name_mapper.items():
        if scanned_identifier in mapper_key_filename:
            return (
                display_name_from_mapper,
                display_name_from_mapper != scanned_identifier,
            )
    return scanned_identifier, False


def _strip_model_extension(model_name: str) -> str:
    """Remove common model file extensions for cleaner display."""
    extensions_to_strip = [
        ".pth",
        ".onnx",
        ".ckpt",
        ".pt",
        ".bin",
        ".pkl",
        ".yaml",
        ".th",
        ".gz",
    ]

    for ext in extensions_to_strip:
        if model_name.lower().endswith(ext.lower()):
            return model_name[: -len(ext)]

    return model_name


def determine_model_process_method(model_name: str) -> Optional[str]:
    """Determine the process method (VR/MDX/Demucs) for a given model name."""
    # Use file extension to determine model type - this is more reliable than scanning directories
    model_path = Path(model_name)
    extension = model_path.suffix.lower()

    if extension == ".pth":
        return ac.VR_ARCH_TYPE
    elif extension in [".onnx", ".ckpt"]:
        return ac.MDX_ARCH_TYPE
    elif extension in [".yaml", ".th", ".gz"]:
        return ac.DEMUCS_ARCH_TYPE
    else:
        # Fallback: check if it's in model directories by scanning
        try:
            vr_models = scan_models_directory(ac.VR_ARCH_TYPE)
            if model_name in vr_models:
                return ac.VR_ARCH_TYPE

            mdx_models = scan_models_directory(ac.MDX_ARCH_TYPE)
            if model_name in mdx_models:
                return ac.MDX_ARCH_TYPE

            demucs_models = scan_models_directory(ac.DEMUCS_ARCH_TYPE)
            if model_name in demucs_models:
                return ac.DEMUCS_ARCH_TYPE
        except Exception:
            pass

    logger.warning(
        f"Warning: Could not determine process method for model: {model_name}"
    )
    return None


def get_karaoke_models() -> List[str]:
    """Get models that are suitable for vocal splitting using proper ModelData metadata detection.

    This function is shared across all advanced dialogs to avoid code duplication.
    Returns list of model names that have is_karaoke or is_bv_model flags set.

    Note: Uses minimal settings dict for ModelData instantiation to check model metadata.
    This approach follows the pattern used in UVR.py for model compatibility checking.
    """
    karaoke_models = [ac.NO_MODEL]

    try:
        # Handle potential circular import
        local_ModelData = ModelData
        if local_ModelData is None:
            from .model_data import ModelData as local_ModelData

        # Create minimal settings using SettingKeys for consistency
        # This is needed to instantiate ModelData objects for metadata checking
        minimal_settings = {
            ac.SettingKeys.IS_GPU: False,
            ac.SettingKeys.DEVICE_SET: ac.DEFAULT,
            ac.SettingKeys.IS_NORMALIZATION: False,
            ac.SettingKeys.SAVE_FORMAT: ac.WAV,
            ac.SettingKeys.WAV_TYPE_SET: ac.PCM_16,
            ac.SettingKeys.MP3_BIT_SET: "320k",
            ac.SettingKeys.AGGRESSION_SETTING: 5,
            ac.SettingKeys.WINDOW_SIZE: 512,
            ac.SettingKeys.BATCH_SIZE: 4,
            ac.SettingKeys.CROP_SIZE: 256,
            ac.SettingKeys.IS_TTA: False,
            ac.SettingKeys.IS_POST_PROCESS: False,
            ac.SettingKeys.IS_HIGH_END_PROCESS: False,
            ac.SettingKeys.POST_PROCESS_THRESHOLD: 0.2,
        }

        # Check VR models for karaoke flags
        vr_models = scan_models_directory(ac.VR_ARCH_TYPE)
        for model_name in vr_models:
            try:
                temp_settings = minimal_settings.copy()
                temp_settings[ac.SettingKeys.PROCESS_METHOD] = ac.VR_ARCH_TYPE

                model_data = local_ModelData.from_settings_dict(
                    temp_settings,
                    _model_name_override=model_name,
                    _process_method_override=ac.VR_ARCH_TYPE,
                    _is_secondary_model_instance=True,  # Skip secondary model loading
                )

                # Check actual model metadata for karaoke or BV model flags
                if model_data.model_status and (
                    model_data.is_karaoke or model_data.is_bv_model
                ):
                    karaoke_models.append(model_name)

            except Exception as model_error:
                logger.debug(
                    f"Could not check karaoke metadata for VR model {model_name}: {model_error}"
                )
                continue

        # Check MDX models for karaoke flags
        mdx_models = scan_models_directory(ac.MDX_ARCH_TYPE)
        for model_name in mdx_models:
            try:
                temp_settings = minimal_settings.copy()
                temp_settings[ac.SettingKeys.PROCESS_METHOD] = ac.MDX_ARCH_TYPE

                model_data = local_ModelData.from_settings_dict(
                    temp_settings,
                    _model_name_override=model_name,
                    _process_method_override=ac.MDX_ARCH_TYPE,
                    _is_secondary_model_instance=True,  # Skip secondary model loading
                )

                # Check actual model metadata for karaoke or BV model flags
                if model_data.model_status and (
                    model_data.is_karaoke or model_data.is_bv_model
                ):
                    karaoke_models.append(model_name)

            except Exception as model_error:
                logger.debug(
                    f"Could not check karaoke metadata for MDX model {model_name}: {model_error}"
                )
                continue

    except Exception as e:
        logger.error(f"Error loading karaoke models: {e}")

    return karaoke_models
