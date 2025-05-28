from PySide6.QtCore import QObject, Signal, QTimer, QThread, QStandardPaths
import time
from pathlib import Path
import os
import json
import natsort
import requests

from . import app_constants as ac

# ... (MODEL_SUBDIRS and other constants as in response #35, ensure ac.ENSEMBLE_MODELS_KEY is used) ...
MODEL_SUBDIRS = {
    ac.VR_ARCH_MODELS_KEY: "VR_Models",
    ac.MDX_NET_MODELS_KEY: "MDX_Net_Models",
    ac.DEMUCS_MODELS_KEY: "Demucs_Models",
    ac.ENSEMBLE_MODELS_KEY: None
}
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
                progress = i * 10
                message = f"Processing step {i}/10..."
                self.progress_updated.emit(progress, message)
                time.sleep(0.5)
            self.processing_finished.emit(True, "Processing Completed Successfully!")
        except Exception as e:
            self.processing_finished.emit(False, f"Error during processing: {e}")

    def stop(self):
        self._is_running = False


class UVRCoreAdapter(QObject):
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)
    download_progress = Signal(str, int)  # model_display_name, percentage
    # MODIFIED SIGNAL: Add model_type_ui_name
    download_finished = Signal(str, str, bool, str)  # model_type_ui_name, model_display_name, success, message

    def __init__(self, parent=None):  # Unchanged
        super().__init__(parent)
        self.processing_thread = None
        self.worker = None
        self._online_catalog_data_cache: dict | None = None
        self._local_catalog_cache_file_path = self._get_local_catalog_cache_file_path()
        print(f"UVRCoreAdapter Initialized. Cache path: {self._local_catalog_cache_file_path}")

    # ... (_get_project_models_dir, _get_local_catalog_cache_file_path,
    #      _fetch_and_cache_online_catalog, get_online_catalog,
    #      _get_primary_filename_from_download_info,
    #      _get_locally_installed_primary_model_filenames,
    #      get_downloadable_models_for_type - all these as in response #35) ...
    def _get_project_models_dir(self) -> Path | None:  # Unchanged
        try:
            current_file_path = Path(__file__).resolve()
            project_root = current_file_path.parents[3]
            models_path = project_root / "models"
            if models_path.is_dir(): return models_path
            print(f"Adapter: WARNING: 'models' directory not found at expected project root: {models_path}")
            cwd_candidate = Path.cwd() / "models"
            if cwd_candidate.is_dir(): return cwd_candidate
            return None
        except IndexError:
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
            response = requests.get(ac.DOWNLOAD_CHECKS_URL, timeout=10)
            response.raise_for_status()
            catalog = response.json()
            try:
                with open(self._local_catalog_cache_file_path, 'w', encoding='utf-8') as f:
                    json.dump(catalog, f, indent=4)
            except IOError as e:
                print(f"Adapter: ERROR caching: {e}")
            return catalog
        except requests.exceptions.RequestException as e:
            print(f"Adapter: ERROR fetching: {e}"); return {}

    def get_online_catalog(self) -> dict:  # Unchanged
        if self._online_catalog_data_cache: return self._online_catalog_data_cache
        catalog = self._fetch_and_cache_online_catalog()
        if not catalog and self._local_catalog_cache_file_path.is_file():
            try:
                with open(self._local_catalog_cache_file_path, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
            except Exception as e:
                print(f"Adapter: ERROR loading cache: {e}"); catalog = {}
        if not catalog: catalog = ac.FALLBACK_ONLINE_CATALOG.copy()
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
        found_filenames = set()
        if not base_models_dir: return found_filenames
        method_subdir_key = MODEL_SUBDIRS.get(method_name)
        if not method_subdir_key: return found_filenames
        method_path = base_models_dir / method_subdir_key
        extensions_to_check = []
        recursive_scan = False
        if method_name == ac.VR_ARCH_MODELS_KEY:
            extensions_to_check = VR_ARCH_SCAN_EXTENSIONS; recursive_scan = True
        elif method_name == ac.MDX_NET_MODELS_KEY:
            extensions_to_check = MDX_SCAN_EXTENSIONS; recursive_scan = True
        elif method_name == ac.DEMUCS_MODELS_KEY:
            if method_path.is_dir():
                for item in method_path.iterdir():
                    if item.is_file() and item.suffix.lower() in DEMUCS_LEGACY_SCAN_EXTENSIONS and item.stem not in EXCLUDED_FILENAMES_STEMS:
                        found_filenames.add(item.name)
            v3_v4_path = method_path / DEMUCS_V3_V4_REPO_DIR_NAME
            if v3_v4_path.is_dir():
                for item in v3_v4_path.rglob('*'):
                    if item.is_file() and item.suffix.lower() in DEMUCS_V3_V4_SCAN_EXTENSIONS and item.stem not in EXCLUDED_FILENAMES_STEMS:
                        found_filenames.add(item.name)
            return found_filenames
        if method_path.is_dir():
            scan_items = method_path.rglob('*') if recursive_scan else method_path.iterdir()
            for item in scan_items:
                if item.is_file() and item.suffix.lower() in extensions_to_check and item.stem not in EXCLUDED_FILENAMES_STEMS:
                    found_filenames.add(item.name)
        return found_filenames

    def get_downloadable_models_for_type(self, ui_model_type: str) -> dict:  # Unchanged
        full_online_catalog = self.get_online_catalog()
        downloadable_models = {}
        if not full_online_catalog: return downloadable_models
        locally_installed_filenames = self._get_locally_installed_primary_model_filenames(ui_model_type)
        online_catalog_source_keys = ac.ONLINE_CATALOG_MAP.get(ui_model_type, [])
        for source_key in online_catalog_source_keys:
            models_in_online_category = full_online_catalog.get(source_key, {})
            for display_name, download_info in models_in_online_category.items():
                primary_filename_to_check = self._get_primary_filename_from_download_info(download_info)
                if primary_filename_to_check and primary_filename_to_check not in locally_installed_filenames:
                    if display_name not in downloadable_models: downloadable_models[display_name] = download_info
        return downloadable_models

    # --- download_model_mock MODIFIED ---
    def download_model_mock(self, model_type_ui_name: str, model_display_name: str, download_target_info: any):
        target_filename = self._get_primary_filename_from_download_info(download_target_info)
        if not target_filename: target_filename = "UnknownFile_" + model_display_name.replace(" ", "_")

        print(
            f"Adapter: Mock download requested for '{model_display_name}' (Target: {target_filename}) for type '{model_type_ui_name}'")

        self._current_download_step = 0
        # Store model_type_ui_name as well for the finished signal
        self._current_download_model_type = model_type_ui_name
        self._current_download_display_name = model_display_name  # Use display name for progress signal

        def _update_mock_download():
            self._current_download_step += 20
            if self._current_download_step <= 100:
                self.download_progress.emit(self._current_download_display_name, self._current_download_step)
                QTimer.singleShot(300, _update_mock_download)
            else:
                base_models_dir = self._get_project_models_dir()
                # Use ac.MODEL_TYPE_SUBDIRS to get the correct local folder name
                method_subdir_key = ac.MODEL_TYPE_SUBDIRS.get(self._current_download_model_type)
                if base_models_dir and method_subdir_key:
                    save_path = base_models_dir / method_subdir_key / Path(target_filename).name
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with open(save_path, 'w') as f:
                            f.write("mock model data for " + target_filename)
                        print(f"Adapter: Mock downloaded and placed '{target_filename}' at '{save_path}'")
                        # Emit with model_type_ui_name
                        self.download_finished.emit(self._current_download_model_type,
                                                    self._current_download_display_name, True,
                                                    f"'{self._current_download_display_name}' downloaded (mock).")
                    except IOError as e:
                        print(f"Adapter: ERROR creating mock file {save_path}: {e}")
                        self.download_finished.emit(self._current_download_model_type,
                                                    self._current_download_display_name, False,
                                                    f"Error saving mock '{self._current_download_display_name}'.")
                else:
                    self.download_finished.emit(self._current_download_model_type, self._current_download_display_name,
                                                False,
                                                f"Download path error (mock) - no subdir for {self._current_download_model_type}.")

        QTimer.singleShot(100, _update_mock_download)

    # --- END OF MODIFICATION ---

    # --- Methods for listing LOCAL models (Keep as in response #35) ---
    def _scan_path_for_identifiers(self, scan_path: Path, extensions: list, is_mdx_ckpt_special_case: bool = False,
                                   recursive: bool = False) -> list[str]:
        identifiers = []
        if not scan_path or not scan_path.is_dir(): return identifiers
        glob_pattern = '**/*' if recursive else '*'
        for item in scan_path.glob(glob_pattern):
            if item.is_file() and item.suffix.lower() in extensions:
                file_stem = item.stem
                if file_stem in EXCLUDED_FILENAMES_STEMS: continue
                identifier = file_stem
                if is_mdx_ckpt_special_case and item.suffix.lower() == ".ckpt": identifier = item.name
                identifiers.append(identifier)
        return list(set(identifiers))

    def _load_name_mapper(self, method_specific_models_path: Path) -> dict:
        mapper_file_path = method_specific_models_path / MAPPER_FILE_REL_PATH
        if mapper_file_path.is_file():
            try:
                with open(mapper_file_path, 'r', encoding='utf-8') as f:
                    mapper_content = json.load(f)
                    return mapper_content
            except Exception as e:
                print(f"Adapter: ERROR loading name mapper {mapper_file_path.name}: {e}")
        return {}

    def _get_display_name_from_mapper(self, scanned_identifier: str, name_mapper: dict) -> tuple[str, bool]:
        if not name_mapper: return scanned_identifier, False
        for mapper_key_filename, display_name_from_mapper in name_mapper.items():
            if scanned_identifier in mapper_key_filename:
                return display_name_from_mapper, display_name_from_mapper != scanned_identifier
        return scanned_identifier, False

    def get_available_methods(self) -> list:  # Corrected in response #35
        print("Adapter: Getting available UI method names.")
        return [ac.VR_ARCH_MODELS_KEY, ac.MDX_NET_MODELS_KEY, ac.DEMUCS_MODELS_KEY, ac.ENSEMBLE_MODELS_KEY]

    def get_available_models(self, method_name: str) -> list:  # Logic from response #35
        base_models_dir = self._get_project_models_dir()
        if not base_models_dir: return []
        method_subdir_key = MODEL_SUBDIRS.get(method_name)
        if not method_subdir_key: return []
        method_path = base_models_dir / method_subdir_key
        scanned_identifiers = []
        name_mapper = {}
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
        if not scanned_identifiers: return []
        final_display_names = []
        for identifier in scanned_identifiers:
            display_name, was_mapped_and_changed = self._get_display_name_from_mapper(identifier, name_mapper)
            if method_name in [ac.MDX_NET_MODELS_KEY, ac.DEMUCS_MODELS_KEY]:
                if was_mapped_and_changed: final_display_names.append(display_name)
            else:
                final_display_names.append(display_name)
        return natsort.natsorted(list(set(final_display_names)))

    def start_processing(self, settings_dict: dict):  # Unchanged
        print(f"Adapter: Received request to start processing.")
        if self.processing_thread and self.processing_thread.isRunning():
            print("Adapter: Processing is already running.")
            return
        self.worker = MockProcessingWorker(settings_dict)
        self.processing_thread = QThread()
        self.worker.moveToThread(self.processing_thread)
        self.processing_thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(self.progress_updated)
        self.worker.processing_finished.connect(self.processing_finished)
        self.worker.processing_finished.connect(self.processing_thread.quit)
        self.worker.processing_finished.connect(self.worker.deleteLater)
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)
        print("Adapter: Starting processing thread...")
        self.processing_thread.start()

    def stop_processing(self):  # Unchanged
        if self.worker and self.processing_thread and self.processing_thread.isRunning():
            print("Adapter: Requesting worker to stop...")
            self.worker.stop()
        else:
            print("Adapter: No process running to stop.")
