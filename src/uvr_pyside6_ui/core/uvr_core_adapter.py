from PySide6.QtCore import QObject, Signal, QTimer, QThread, QStandardPaths
import time
from pathlib import Path
import os
import json
import natsort
import requests

from . import app_constants as ac

# MODEL_SUBDIRS is used by get_available_models to find the folder for a method.
# If a method (like Ensemble) has 'None' or is missing, get_available_models will return [] for it.
MODEL_SUBDIRS = {
    ac.VR_ARCH_MODELS_KEY: "VR_Models",
    ac.MDX_NET_MODELS_KEY: "MDX_Net_Models",
    ac.DEMUCS_MODELS_KEY: "Demucs_Models",
    "Ensemble": None  # Ensemble doesn't have its own primary model folder to scan for listing
}
# Ensure ac.VR_ARCH_MODELS_KEY, etc. are defined in your app_constants.py as "VR Arch", "MDX-Net", "Demucs"

VR_ARCH_SCAN_EXTENSIONS = ['.pth']
MDX_SCAN_EXTENSIONS = ['.onnx', '.ckpt']
DEMUCS_LEGACY_SCAN_EXTENSIONS = ['.ckpt', '.gz', '.th']
DEMUCS_V3_V4_REPO_DIR_NAME = "v3_v4_repo"
DEMUCS_V3_V4_SCAN_EXTENSIONS = ['.yaml']
MAPPER_FILE_REL_PATH = Path("model_data") / "model_name_mapper.json"
EXCLUDED_FILENAMES_STEMS = ["model_data", "model_name_mapper", "download_links"]


class MockProcessingWorker(QObject):  # Unchanged
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)

    def __init__(self, settings_dict):
        super().__init__(); self.settings = settings_dict; self._is_running = True

    def run(self):
        print("Adapter Worker: Starting simulation...")
        try:
            for i in range(11):
                if not self._is_running: self.processing_finished.emit(False, "Processing Canceled"); return
                progress = i * 10;
                message = f"Processing step {i}/10...";
                self.progress_updated.emit(progress, message);
                time.sleep(0.5)
            self.processing_finished.emit(True, "Processing Completed Successfully!")
        except Exception as e:
            self.processing_finished.emit(False, f"Error during processing: {e}")

    def stop(self):
        self._is_running = False


# In UVRCoreAdapter.py (only showing the changed method and its dependencies)
# Ensure all other methods from response #33 remain.

# ... (all other imports and constants like MODEL_SUBDIRS, VR_ARCH_SCAN_EXTENSIONS etc. from #33) ...
# from . import app_constants as ac  # Make sure this import is correct


# ... (MockProcessingWorker and most of UVRCoreAdapter class as in response #33) ...

class UVRCoreAdapter(QObject):
    # ... (signals, __init__, _get_project_models_dir, _get_local_catalog_cache_file_path,
    #      _fetch_and_cache_online_catalog, get_online_catalog,
    #      _get_primary_filename_from_download_info,
    #      _get_locally_installed_primary_model_filenames,
    #      get_downloadable_models_for_type, download_model_mock,
    #      _scan_path_for_identifiers, _load_name_mapper,
    #      _get_display_name_from_mapper - ALL THESE SHOULD BE AS PER RESPONSE #33)

    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)
    download_progress = Signal(str, int)
    download_finished = Signal(str, bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processing_thread = None
        self.worker = None
        self._online_catalog_data_cache: dict | None = None
        self._local_catalog_cache_file_path = self._get_local_catalog_cache_file_path()
        print(f"UVRCoreAdapter Initialized. Cache path: {self._local_catalog_cache_file_path}")

    def _get_project_models_dir(self) -> Path | None:
        try:
            current_file_path = Path(__file__).resolve()
            project_root = current_file_path.parents[3]
            models_path = project_root / "models"
            if models_path.is_dir():
                # print(f"Adapter: Models base directory found at: {models_path}") # Less verbose
                return models_path
            print(f"Adapter: WARNING: 'models' directory not found at expected project root: {models_path}")
            cwd_candidate = Path.cwd() / "models"
            if cwd_candidate.is_dir():
                print(f"Adapter: Models base directory found relative to CWD: {cwd_candidate}")
                return cwd_candidate
            return None
        except IndexError:
            print("Adapter: ERROR: Could not determine project root. Ensure correct structure.")
            return None

    def _get_local_catalog_cache_file_path(self) -> Path:  # Unchanged
        try:
            current_file_path = Path(__file__).resolve()
            project_root = current_file_path.parents[3]
            cache_dir = project_root / ac.CACHE_DIR_NAME
        except IndexError:
            cache_dir = Path(QStandardPaths.writableLocation(QStandardPaths.CacheLocation)) / "UVR_PySide6_Cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / ac.ONLINE_CATALOG_CACHE_FILENAME

    def _fetch_and_cache_online_catalog(self) -> dict:  # Unchanged
        try:
            print(f"Adapter: Attempting to fetch online catalog from {ac.DOWNLOAD_CHECKS_URL}...")
            response = requests.get(ac.DOWNLOAD_CHECKS_URL, timeout=10)
            response.raise_for_status()
            catalog = response.json()
            print("Adapter: Successfully fetched online catalog.")
            try:
                with open(self._local_catalog_cache_file_path, 'w', encoding='utf-8') as f:
                    json.dump(catalog, f, indent=4)
                print(f"Adapter: Online catalog cached to {self._local_catalog_cache_file_path}")
            except IOError as e:
                print(f"Adapter: ERROR caching online catalog: {e}")
            return catalog
        except requests.exceptions.RequestException as e:
            print(f"Adapter: ERROR fetching online catalog: {e}.")
            return {}

    def get_online_catalog(self) -> dict:  # Unchanged
        if self._online_catalog_data_cache:
            print("Adapter: Returning in-memory cached online catalog.")
            return self._online_catalog_data_cache
        catalog = self._fetch_and_cache_online_catalog()
        if not catalog:
            print("Adapter: Fetching online catalog failed. Trying local cache file.")
            if self._local_catalog_cache_file_path.is_file():
                try:
                    with open(self._local_catalog_cache_file_path, 'r', encoding='utf-8') as f:
                        catalog = json.load(f)
                    print(
                        f"Adapter: Successfully loaded catalog from local cache: {self._local_catalog_cache_file_path}")
                except Exception as e_cache:
                    print(f"Adapter: ERROR loading from local cache {self._local_catalog_cache_file_path}: {e_cache}")
                    catalog = {}
            else:
                print(f"Adapter: Local cache file not found at {self._local_catalog_cache_file_path}.")
                catalog = {}
        if not catalog:
            print("Adapter: Using fallback mock catalog.")
            catalog = ac.FALLBACK_ONLINE_CATALOG.copy()
        self._online_catalog_data_cache = catalog
        return catalog

    def _get_primary_filename_from_download_info(self, download_info: any) -> str:  # Unchanged
        if isinstance(download_info, str):
            return Path(download_info).name
        elif isinstance(download_info, dict):
            for key, value in download_info.items():
                if key.endswith(".yaml"): return key
                if isinstance(value, str) and value.endswith(".yaml"): return Path(value).name
            for key, value in download_info.items():
                if key.endswith(tuple(ac.DOWNLOADED_MODEL_PRIMARY_EXTENSIONS)): return key
                if isinstance(value, str) and value.endswith(
                    tuple(ac.DOWNLOADED_MODEL_PRIMARY_EXTENSIONS)): return Path(value).name
            for key_or_val in list(download_info.keys()) + list(download_info.values()):
                if isinstance(key_or_val, str) and any(key_or_val.endswith(ext) for ext in
                                                       ac.DOWNLOADED_MODEL_PRIMARY_EXTENSIONS + ac.DOWNLOADED_DEMUCS_CONFIG_EXT):
                    return Path(key_or_val).name
        return ""

    def _get_locally_installed_primary_model_filenames(self, method_name: str) -> set[str]:  # Unchanged
        base_models_dir = self._get_project_models_dir()
        if not base_models_dir: return set()
        method_subdir_key = MODEL_SUBDIRS.get(method_name)
        if not method_subdir_key: return set()  # Important for Ensemble which has None
        method_path = base_models_dir / method_subdir_key
        found_filenames = set()
        extensions_to_check = []
        recursive_scan = False
        if method_name == ac.VR_ARCH_MODELS_KEY:
            extensions_to_check = VR_ARCH_SCAN_EXTENSIONS;
            recursive_scan = True
        elif method_name == ac.MDX_NET_MODELS_KEY:
            extensions_to_check = MDX_SCAN_EXTENSIONS;
            recursive_scan = True
        elif method_name == ac.DEMUCS_MODELS_KEY:
            if method_path.is_dir():
                for item in method_path.iterdir():
                    if item.is_file() and item.suffix.lower() in DEMUCS_LEGACY_SCAN_EXTENSIONS:
                        if item.name not in EXCLUDED_FILENAMES_STEMS and item.stem not in EXCLUDED_FILENAMES_STEMS:
                            found_filenames.add(item.name)
            v3_v4_path = method_path / DEMUCS_V3_V4_REPO_DIR_NAME
            if v3_v4_path.is_dir():
                for item in v3_v4_path.rglob('*'):
                    if item.is_file() and item.suffix.lower() in DEMUCS_V3_V4_SCAN_EXTENSIONS:
                        if item.name not in EXCLUDED_FILENAMES_STEMS and item.stem not in EXCLUDED_FILENAMES_STEMS:
                            found_filenames.add(item.name)
                            # print(f"Adapter: Locally installed filenames for {method_name}: {found_filenames}") # Less verbose
            return found_filenames
        if method_path.is_dir():
            scan_items = method_path.rglob('*') if recursive_scan else method_path.iterdir()
            for item in scan_items:
                if item.is_file() and item.suffix.lower() in extensions_to_check:
                    if item.name not in EXCLUDED_FILENAMES_STEMS and item.stem not in EXCLUDED_FILENAMES_STEMS:
                        found_filenames.add(item.name)
                        # print(f"Adapter: Locally installed filenames for {method_name}: {found_filenames}") # Less verbose
        return found_filenames

    def get_downloadable_models_for_type(self, ui_model_type: str) -> dict:  # Unchanged
        full_online_catalog = self.get_online_catalog()
        if not full_online_catalog:
            print("Adapter (Download List): Full online catalog not available.")
            return {}
        locally_installed_filenames = self._get_locally_installed_primary_model_filenames(ui_model_type)
        # print(f"Adapter (Download List): For {ui_model_type}, local files found: {locally_installed_filenames}")
        downloadable_models = {}
        online_catalog_source_keys = ac.ONLINE_CATALOG_MAP.get(ui_model_type, [])
        for source_key in online_catalog_source_keys:
            models_in_online_category = full_online_catalog.get(source_key, {})
            for display_name, download_info in models_in_online_category.items():
                primary_filename_to_check = self._get_primary_filename_from_download_info(download_info)
                if primary_filename_to_check and primary_filename_to_check not in locally_installed_filenames:
                    if display_name not in downloadable_models:
                        downloadable_models[display_name] = download_info
                        # print(f"Adapter (Download List): Adding '{display_name}' (file: {primary_filename_to_check})")
                # else: # Too verbose for regular operation
                # if primary_filename_to_check: print(f"Adapter (Download List): Skipping '{display_name}' (file: {primary_filename_to_check}) as it's local or unidentifiable.")
                # else: print(f"Adapter (Download List): Skipping '{display_name}' as primary filename couldn't be determined from download_info: {download_info}")
        print(
            f"Adapter: Final list of downloadable models for {ui_model_type}: {list(downloadable_models.keys())[:5]}...")  # Log sample
        return downloadable_models

    def download_model_mock(self, model_type_ui_name: str, model_display_name: str,
                            download_target_info: any):  # Unchanged
        target_filename = self._get_primary_filename_from_download_info(download_target_info)
        if not target_filename: target_filename = "UnknownFile"
        print(f"Adapter: Mock download requested for '{model_display_name}' (Target: {target_filename})")
        self._current_download_step = 0
        self._current_download_name = model_display_name

        def _update_mock_download():
            self._current_download_step += 20
            if self._current_download_step <= 100:
                self.download_progress.emit(self._current_download_name, self._current_download_step)
                QTimer.singleShot(300, _update_mock_download)
            else:
                base_models_dir = self._get_project_models_dir()
                method_subdir_key = ac.MODEL_TYPE_SUBDIRS.get(model_type_ui_name)
                if base_models_dir and method_subdir_key:
                    save_path = base_models_dir / method_subdir_key / Path(target_filename).name
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with open(save_path, 'w') as f:
                            f.write("mock model data for " + target_filename)
                        print(f"Adapter: Mock downloaded and placed '{target_filename}' at '{save_path}'")
                        self.download_finished.emit(self._current_download_name, True,
                                                    f"'{self._current_download_name}' downloaded (mock).")
                    except IOError as e:
                        print(f"Adapter: ERROR creating mock file {save_path}: {e}")
                        self.download_finished.emit(self._current_download_name, False,
                                                    f"Error saving mock '{self._current_download_name}'.")
                else:  # This case includes if method_subdir_key is None (like for Ensemble)
                    self.download_finished.emit(self._current_download_name, False,
                                                f"Download path error (mock) - no subdir for {model_type_ui_name}.")

        QTimer.singleShot(100, _update_mock_download)

    def _scan_path_for_identifiers(self, scan_path: Path, extensions: list, is_mdx_ckpt_special_case: bool = False,
                                   recursive: bool = False) -> list[str]:  # Unchanged
        identifiers = []
        if not scan_path or not scan_path.is_dir(): return identifiers
        glob_pattern = '**/*' if recursive else '*'
        # scan_type_msg = "recursively" if recursive else "non-recursively" # Less verbose
        # print(f"Adapter (Local Scan): Scanning {scan_type_msg} in '{scan_path}' for {extensions}")
        for item in scan_path.glob(glob_pattern):
            if item.is_file() and item.suffix.lower() in extensions:
                file_stem = item.stem
                if file_stem in EXCLUDED_FILENAMES_STEMS: continue
                identifier = file_stem
                if is_mdx_ckpt_special_case and item.suffix.lower() == ".ckpt": identifier = item.name
                identifiers.append(identifier)
        return list(set(identifiers))

    def _load_name_mapper(self, method_specific_models_path: Path) -> dict:  # Unchanged
        mapper_file_path = method_specific_models_path / MAPPER_FILE_REL_PATH
        if mapper_file_path.is_file():
            try:
                with open(mapper_file_path, 'r', encoding='utf-8') as f:
                    mapper_content = json.load(f)
                    # print(f"Adapter: Successfully loaded name mapper: {mapper_file_path.name} (Keys sample: {list(mapper_content.keys())[:5]}...)") # Less verbose
                    return mapper_content
            except Exception as e:
                print(f"Adapter: ERROR loading/parsing name mapper {mapper_file_path.name}: {e}")
        # else: print(f"Adapter: Name mapper file not found at: {mapper_file_path}") # Less verbose
        return {}

    def _get_display_name_from_mapper(self, scanned_identifier: str, name_mapper: dict) -> tuple[
        str, bool]:  # Unchanged
        if not name_mapper: return scanned_identifier, False
        for mapper_key_filename, display_name_from_mapper in name_mapper.items():
            if scanned_identifier in mapper_key_filename:
                return display_name_from_mapper, display_name_from_mapper != scanned_identifier
        return scanned_identifier, False

    # --- METHOD CORRECTED TO INCLUDE ENSEMBLE ---
    def get_available_methods(self) -> list:
        """Returns a list of available processing method UI names."""
        print("Adapter: Getting available UI method names.")
        # These should be the user-facing names for the Process Method combobox
        return [
            ac.VR_ARCH_MODELS_KEY,
            ac.MDX_NET_MODELS_KEY,
            ac.DEMUCS_MODELS_KEY,
            ac.ENSEMBLE_MODELS_KEY  # Ensure this constant is defined in app_constants.py as "Ensemble"
        ]

    # --- END OF CORRECTION ---

    def get_available_models(self, method_name: str) -> list:  # For local models
        base_models_dir = self._get_project_models_dir()
        if not base_models_dir: return []

        method_subdir_key = MODEL_SUBDIRS.get(method_name)  # Uses MODEL_SUBDIRS from this file
        if not method_subdir_key:
            print(
                f"Adapter (Local Scan): No model subdirectory defined for UI method '{method_name}'. (e.g., Ensemble)")
            return []

        method_path = base_models_dir / method_subdir_key
        scanned_identifiers = []
        name_mapper = {}

        # print(f"Adapter (Local Scan): Preparing to scan for method '{method_name}' in path '{method_path}'") # Less verbose

        if method_name == ac.VR_ARCH_MODELS_KEY:
            scanned_identifiers = self._scan_path_for_identifiers(method_path, VR_ARCH_SCAN_EXTENSIONS, recursive=True)
        elif method_name == ac.MDX_NET_MODELS_KEY:
            scanned_identifiers = self._scan_path_for_identifiers(method_path, MDX_SCAN_EXTENSIONS,
                                                                  is_mdx_ckpt_special_case=True, recursive=True)
            name_mapper = self._load_name_mapper(method_path)
        elif method_name == ac.DEMUCS_MODELS_KEY:
            ids_legacy = self._scan_path_for_identifiers(method_path, DEMUCS_LEGACY_SCAN_EXTENSIONS, recursive=False)
            newer_repo_path = method_path / DEMUCS_V3_V4_REPO_DIR_NAME
            ids_v3_v4_yaml = self._scan_path_for_identifiers(newer_repo_path, DEMUCS_V3_V4_SCAN_EXTENSIONS,
                                                             recursive=True)
            scanned_identifiers = list(set(ids_legacy + ids_v3_v4_yaml))
            name_mapper = self._load_name_mapper(method_path)

        if not scanned_identifiers:
            # print(f"Adapter (Local Scan): No model identifiers found for {method_name}.") # Less verbose
            return []
        # print(f"Adapter (Local Scan): Scanned Identifiers for {method_name} before mapping: {natsort.natsorted(scanned_identifiers)}") # Less verbose
        final_display_names = []
        for identifier in scanned_identifiers:
            display_name, was_mapped_and_changed = self._get_display_name_from_mapper(identifier, name_mapper)
            if method_name in [ac.MDX_NET_MODELS_KEY, ac.DEMUCS_MODELS_KEY]:
                if was_mapped_and_changed: final_display_names.append(display_name)
                # else: print(f"    Skipping '{identifier}' for {method_name} (local) as not distinctly mapped.") # Less verbose
            else:
                final_display_names.append(display_name)
        result = natsort.natsorted(list(set(final_display_names)))
        # print(f"Adapter (Local Scan): Final display models for {method_name}: {result}") # Less verbose
        return result

    def start_processing(self, settings_dict: dict):  # Unchanged
        print(f"Adapter: Received request to start processing.")
        if self.processing_thread and self.processing_thread.isRunning():
            print("Adapter: Processing is already running.");
            return
        self.worker = MockProcessingWorker(settings_dict);
        self.processing_thread = QThread()
        self.worker.moveToThread(self.processing_thread);
        self.processing_thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(self.progress_updated);
        self.worker.processing_finished.connect(self.processing_finished)
        self.worker.processing_finished.connect(self.processing_thread.quit);
        self.worker.processing_finished.connect(self.worker.deleteLater)
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)
        print("Adapter: Starting processing thread...");
        self.processing_thread.start()

    def stop_processing(self):  # Unchanged
        if self.worker and self.processing_thread and self.processing_thread.isRunning():
            print("Adapter: Requesting worker to stop...");
            self.worker.stop()
        else:
            print("Adapter: No process running to stop.")