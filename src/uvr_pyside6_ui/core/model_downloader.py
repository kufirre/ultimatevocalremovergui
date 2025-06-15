"""Model downloader module for UVR PySide6 application."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from . import app_constants as ac
from .logger_utils import get_logger

logger = get_logger(__name__)

# Ensure the main models directory and subdirectories exist
MODELS_DIR = Path.cwd() / "models"
MODEL_TYPE_PATHS = {
    ac.VR_ARCH_MODELS_KEY: MODELS_DIR / ac.MODEL_TYPE_SUBDIRS[ac.VR_ARCH_MODELS_KEY],
    ac.MDX_NET_MODELS_KEY: MODELS_DIR / ac.MODEL_TYPE_SUBDIRS[ac.MDX_NET_MODELS_KEY],
    ac.DEMUCS_MODELS_KEY: MODELS_DIR / ac.MODEL_TYPE_SUBDIRS[ac.DEMUCS_MODELS_KEY],
}

for path in MODEL_TYPE_PATHS.values():
    if path:
        path.mkdir(parents=True, exist_ok=True)  # Check if path is not None

CACHE_DIR = Path.home() / ac.CACHE_DIR_NAME
CACHE_DIR.mkdir(parents=True, exist_ok=True)
ONLINE_CATALOG_CACHE_FILE = CACHE_DIR / ac.ONLINE_CATALOG_CACHE_FILENAME


def fetch_online_model_catalog() -> Dict[str, Any]:
    """Fetches the online model catalog, using cache if available and recent."""
    if ONLINE_CATALOG_CACHE_FILE.exists():
        try:
            # TODO: Add cache expiry (e.g., if file is older than 1 day, refresh)
            with open(ONLINE_CATALOG_CACHE_FILE, encoding="utf-8") as f:
                logger.info("Using cached online model catalog.")
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading cached catalog: {e}. Fetching fresh.")

    try:
        response = requests.get(ac.DOWNLOAD_CHECKS_URL, timeout=10)
        response.raise_for_status()
        catalog_data = response.json()
        with open(ONLINE_CATALOG_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=4)
        logger.info("Fetched and cached online model catalog.")
        return catalog_data
    except requests.RequestException as e:
        logger.error(f"Error fetching online model catalog: {e}")
        logger.info("Using fallback catalog.")
        return ac.FALLBACK_ONLINE_CATALOG.copy()  # Ensure it's a copy
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding online model catalog JSON: {e}")
        logger.info("Using fallback catalog.")
        return ac.FALLBACK_ONLINE_CATALOG.copy()


def download_model_file(
    model_name: str,
    download_url: str,
    model_type: str,
    config_url: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Downloads a model file and its optional config to the appropriate directory.
    Reports progress via the progress_callback(filename, percentage).
    Returns (success, message_or_main_file_path, local_config_path).
    """
    target_dir = MODEL_TYPE_PATHS.get(model_type)
    if not target_dir:
        return False, f"Unknown model type: {model_type}", None

    local_model_filename = Path(download_url).name
    local_model_path = target_dir / local_model_filename
    local_config_path_str: Optional[str] = None

    # Handle Demucs models specially - check if this should go in v3_v4_repo
    if model_type == ac.DEMUCS_MODELS_KEY:
        # Check if this is a v3/v4 model that should go in the v3_v4_repo directory
        # This checks for:
        # 1. v3/v4 in model name
        # 2. .yaml extension in the main file
        # 3. .yaml extension in the config file (if provided)
        should_use_v3_v4_repo = (
            any(tag in model_name.lower() for tag in [ac.DEMUCS_V3, ac.DEMUCS_V4])
            or local_model_filename.endswith(".yaml")
            or (config_url and Path(config_url).name.endswith(".yaml"))
        )

        if should_use_v3_v4_repo:
            # Create the v3_v4_repo directory if it doesn't exist
            v3_v4_repo_dir = target_dir / ac.DEMUCS_V3_V4_REPO_DIR_NAME
            v3_v4_repo_dir.mkdir(exist_ok=True)

            # Update the local path to save in the v3_v4_repo directory
            local_model_path = v3_v4_repo_dir / local_model_filename

    files_to_download = [(download_url, local_model_path, "model")]

    if config_url:
        local_config_filename = Path(config_url).name
        # Config files should go in the same directory as the model
        config_target_dir = local_model_path.parent
        local_config_path = config_target_dir / local_config_filename
        local_config_path_str = str(local_config_path)
        files_to_download.append((config_url, local_config_path, "config"))

    try:
        for url, local_path, file_type_name in files_to_download:
            if progress_callback:
                progress_callback(Path(url).name, 0)

            logger.info(
                f"Downloading {file_type_name} {Path(url).name} from {url} to {local_path}..."
            )
            response = requests.get(url, stream=True, timeout=60)  # Increased timeout
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0 and progress_callback:
                        percentage = int((downloaded_size / total_size) * 100)
                        # Call progress callback more frequently for smooth updates
                        progress_callback(Path(url).name, percentage)
                    elif progress_callback:
                        # If no total size, show indeterminate progress
                        progress_callback(
                            Path(url).name, min(50, downloaded_size // 1024)
                        )  # Rough progress based on KB

            if progress_callback:
                progress_callback(Path(url).name, 100)
            logger.info(f"Successfully downloaded {Path(url).name}")

        return True, str(local_model_path), local_config_path_str

    except requests.RequestException as e:
        msg = f"Error downloading {model_name}: {e}"
        logger.error(msg)
        # Clean up any partial downloads
        for _, local_p, _ in files_to_download:
            if local_p.exists():
                local_p.unlink(missing_ok=True)
        return False, msg, None
    except Exception as e_gen:
        msg = f"An unexpected error occurred downloading {model_name}: {e_gen}"
        logger.error(msg)
        for _, local_p, _ in files_to_download:
            if local_p.exists():
                local_p.unlink(missing_ok=True)
        return False, msg, None


if __name__ == "__main__":
    catalog = fetch_online_model_catalog()
    if catalog:
        logger.info("\nSample of fetched catalog:")
        for key, value in list(catalog.items())[:2]:
            if isinstance(value, dict):
                logger.info(f"  {key}: {list(value.keys())[:3]}...")
            else:
                logger.info(f"  {key}: {str(value)[:100]}...")

