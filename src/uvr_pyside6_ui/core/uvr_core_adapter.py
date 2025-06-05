import json
from pathlib import Path
from typing import Any

import natsort
from PySide6.QtCore import QObject, Signal

from . import app_constants as ac
from .download_worker import DownloadManager
from .model_downloader import fetch_online_model_catalog
from .processing_worker import ProcessingThread

# ... (MODEL_SUBDIRS and other constants as in response #35, ensure ac.ENSEMBLE_MODELS_KEY is used) ...
MODEL_SUBDIRS = {
    ac.VR_ARCH_MODELS_KEY: "VR_Models",
    ac.MDX_NET_MODELS_KEY: "MDX_Net_Models",
    ac.DEMUCS_MODELS_KEY: "Demucs_Models",
    ac.ENSEMBLE_MODELS_KEY: None,  # Ensemble configs are in gui_data/saved_ensembles
}
VR_ARCH_SCAN_EXTENSIONS = [".pth"]
MDX_SCAN_EXTENSIONS = [".onnx", ".ckpt"]
DEMUCS_LEGACY_SCAN_EXTENSIONS = [".ckpt", ".gz", ".th"]
DEMUCS_V3_V4_REPO_DIR_NAME = "v3_v4_repo"
DEMUCS_V3_V4_SCAN_EXTENSIONS = [".yaml"]
MAPPER_FILE_REL_PATH = Path("model_data") / "model_name_mapper.json"
EXCLUDED_FILENAMES_STEMS = ["model_data", "model_name_mapper", "download_links"]


class UVRCoreAdapter(QObject):
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)
    download_progress = Signal(str, int)  # model_display_name, percentage
    download_finished = Signal(
        str, str, bool, str
    )  # model_type_ui_name, model_display_name, success, message
    model_download_completed = Signal(
        str
    )  # model_type_ui_name, emitted after a successful download

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processing_thread: ProcessingThread | None = None
        self._online_catalog_data_cache: dict | None = None
        self.download_manager = DownloadManager()

        # Connect download manager signals to our signals
        self.download_manager.download_progress.connect(self.download_progress)
        self.download_manager.download_finished.connect(self._on_download_finished)

    def _on_processing_thread_finished(self):
        # Slot to safely nullify the thread reference after it has finished
        if self.processing_thread:
            # Ensure signals are disconnected if necessary, though deleteLater should handle much of this.
            # For safety, explicitly disconnect signals we connected if problems persist.
            # self.processing_thread.progress_updated.disconnect(self.progress_updated)
            # self.processing_thread.processing_finished.disconnect(self.processing_finished)
            # self.processing_thread.finished.disconnect(self._on_processing_thread_finished)
            # self.processing_thread.finished.connect(self.processing_thread.deleteLater) # Already connected
            pass
        self.processing_thread = None
        # print("Processing thread has finished and reference cleared.")

    def _get_project_models_dir(self) -> Path | None:
        try:
            current_file_path = Path(__file__).resolve()
            # Assuming this file (uvr_core_adapter.py) is in src/uvr_pyside6_ui/core/
            # parents[0] is core/
            # parents[1] is uvr_pyside6_ui/
            # parents[2] is src/
            # parents[3] is ultimatevocalremovergui/ (the project root)
            ultimate_project_root = current_file_path.parents[3]
            models_path = ultimate_project_root / "models"
            if models_path.is_dir():
                return models_path

            # Fallback if the above pathing is not as expected
            cwd_candidate = Path.cwd() / "models"
            if cwd_candidate.is_dir():
                return cwd_candidate

            print(
                f"Warning: Could not determine models directory. Tried: {models_path} and {cwd_candidate}"
            )
            return None
        except (
            IndexError
        ):  # If parents[3] doesn't exist (e.g., if file structure is different)
            # Last resort fallback
            cwd_candidate = Path.cwd() / "models"
            if cwd_candidate.is_dir():
                return cwd_candidate
            print(
                f"Warning: Could not determine models directory due to IndexError. Tried: {cwd_candidate}"
            )
            return None

    # _get_local_catalog_cache_file_path is removed as model_downloader handles its own cache path

    # _fetch_and_cache_online_catalog is replaced by model_downloader.fetch_online_model_catalog

    def get_online_catalog(self) -> dict:
        if self._online_catalog_data_cache is None:
            # Debug print removed
            self._online_catalog_data_cache = fetch_online_model_catalog()
        return (
            self._online_catalog_data_cache
            if self._online_catalog_data_cache
            else ac.FALLBACK_ONLINE_CATALOG.copy()
        )

    def _construct_full_url(
        self, path_or_url: str, model_type: str, is_config: bool = False
    ) -> str:
        """Constructs a full URL if a relative path/filename is given."""
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url

        # Determine appropriate base URL
        base_url_to_use = ac.MODEL_REPO_URL_BASE  # Default base
        if model_type == ac.DEMUCS_MODELS_KEY:
            if is_config and path_or_url.endswith(
                ".yaml"
            ):  # Demucs .yaml configs often from facebookresearch
                base_url_to_use = ac.DEMUCS_CONFIG_URL_BASE

        # Ensure no double slashes when joining, and handle cases where base_url might not end with /
        # or path_or_url might start with /

        final_url = base_url_to_use.rstrip("/") + "/" + path_or_url.lstrip("/")

        return final_url

    def _get_primary_filename_from_download_info(self, download_info: any) -> str:
        if isinstance(download_info, str):
            return Path(download_info).name
        elif isinstance(download_info, dict):
            for key, value in download_info.items():
                if key.endswith(".yaml"):
                    return key
                if isinstance(value, str) and value.endswith(".yaml"):
                    return Path(value).name
            for key, value in download_info.items():
                if key.endswith(tuple(ac.DOWNLOADED_MODEL_PRIMARY_EXTENSIONS)):
                    return key
                if isinstance(value, str) and value.endswith(
                    tuple(ac.DOWNLOADED_MODEL_PRIMARY_EXTENSIONS)
                ):
                    return Path(value).name
            for key_or_val in list(download_info.keys()) + list(download_info.values()):
                if isinstance(key_or_val, str) and any(
                    key_or_val.endswith(ext)
                    for ext in ac.DOWNLOADED_MODEL_PRIMARY_EXTENSIONS
                    + ac.DOWNLOADED_DEMUCS_CONFIG_EXT
                ):
                    return Path(key_or_val).name
        return ""

    def _get_locally_installed_primary_model_filenames(
        self, method_name: str
    ) -> set[str]:  # Unchanged
        base_models_dir = self._get_project_models_dir()
        found_filenames = set()
        if not base_models_dir:
            return found_filenames
        method_subdir_key = MODEL_SUBDIRS.get(method_name)
        if not method_subdir_key:
            return found_filenames
        method_path = base_models_dir / method_subdir_key
        extensions_to_check = []
        recursive_scan = False
        if method_name == ac.VR_ARCH_MODELS_KEY:
            extensions_to_check = VR_ARCH_SCAN_EXTENSIONS
            recursive_scan = True
        elif method_name == ac.MDX_NET_MODELS_KEY:
            extensions_to_check = MDX_SCAN_EXTENSIONS
            recursive_scan = True
        elif method_name == ac.DEMUCS_MODELS_KEY:
            if method_path.is_dir():
                for item in method_path.iterdir():
                    if (
                        item.is_file()
                        and item.suffix.lower() in DEMUCS_LEGACY_SCAN_EXTENSIONS
                        and item.stem not in EXCLUDED_FILENAMES_STEMS
                    ):
                        found_filenames.add(item.name)
            v3_v4_path = method_path / DEMUCS_V3_V4_REPO_DIR_NAME
            if v3_v4_path.is_dir():
                for item in v3_v4_path.rglob("*"):
                    if (
                        item.is_file()
                        and item.suffix.lower() in DEMUCS_V3_V4_SCAN_EXTENSIONS
                        and item.stem not in EXCLUDED_FILENAMES_STEMS
                    ):
                        found_filenames.add(item.name)
            return found_filenames
        if method_path.is_dir():
            scan_items = (
                method_path.rglob("*") if recursive_scan else method_path.iterdir()
            )
            for item in scan_items:
                if (
                    item.is_file()
                    and item.suffix.lower() in extensions_to_check
                    and item.stem not in EXCLUDED_FILENAMES_STEMS
                ):
                    found_filenames.add(item.name)
        return found_filenames

    def get_downloadable_models_for_type(self, ui_model_type: str) -> dict:  # Unchanged
        full_online_catalog = self.get_online_catalog()
        downloadable_models = {}
        if not full_online_catalog:
            return downloadable_models
        locally_installed_filenames = (
            self._get_locally_installed_primary_model_filenames(ui_model_type)
        )
        online_catalog_source_keys = ac.ONLINE_CATALOG_MAP.get(ui_model_type, [])
        for source_key in online_catalog_source_keys:
            models_in_online_category = full_online_catalog.get(source_key, {})
            for display_name, download_info in models_in_online_category.items():
                primary_filename_to_check = (
                    self._get_primary_filename_from_download_info(download_info)
                )
                if (
                    primary_filename_to_check
                    and primary_filename_to_check not in locally_installed_filenames
                ):
                    if display_name not in downloadable_models:
                        downloadable_models[display_name] = download_info
        return downloadable_models

    def _on_download_finished(
        self, success: bool, model_path: str, config_path: str, message: str
    ):
        """Handle download completion from the download manager."""
        # Extract model type and display name from the model path
        model_type_ui_name = ""
        model_display_name = ""

        # Determine model type from path
        if "VR_Models" in model_path:
            model_type_ui_name = ac.VR_ARCH_MODELS_KEY
        elif "MDX_Net_Models" in model_path:
            model_type_ui_name = ac.MDX_NET_MODELS_KEY
        elif "Demucs_Models" in model_path:
            model_type_ui_name = ac.DEMUCS_MODELS_KEY

        # Extract display name from filename
        if model_path:
            model_display_name = Path(model_path).stem

        # Emit our signal with the extracted information
        self.download_finished.emit(
            model_type_ui_name, model_display_name, success, message
        )

        # If successful, emit model download completed signal
        if success:
            self.model_download_completed.emit(model_type_ui_name)

    def get_model_info(self, model_name: str, model_type: str) -> dict | None:
        """Get basic model information for filtering purposes.

        This is a simplified version of the ModelData functionality from the original UVR
        to help with ensemble model filtering.
        """
        try:
            base_models_dir = self._get_project_models_dir()
            if not base_models_dir:
                return None

            model_info = {
                "model_name": model_name,
                "model_type": model_type,
                "primary_stem": None,
                "mdx_model_stems": [],
                "mdx_stem_count": 0,
                "is_4_stem": False,
                "demucs_stems": [],
            }

            # For VR models, most are vocal/instrumental separation
            if model_type == ac.VR_ARCH_MODELS_KEY:
                # Most VR models output vocals as primary stem
                model_info["primary_stem"] = ac.VOCAL_STEM

            # For MDX models, check if it's a multi-stem model or vocal/instrumental
            elif model_type == ac.MDX_NET_MODELS_KEY:
                # Most MDX models can do vocal/instrumental separation
                model_info["mdx_model_stems"] = [ac.VOCAL_STEM, ac.INST_STEM]
                model_info["mdx_stem_count"] = 2

                # Check for specific multi-stem models (these are usually named specifically)
                model_lower = model_name.lower()
                if any(
                    keyword in model_lower for keyword in ["4stem", "4-stem", "multi"]
                ):
                    model_info["mdx_model_stems"] = [
                        ac.VOCAL_STEM,
                        ac.INST_STEM,
                        ac.BASS_STEM,
                        ac.DRUM_STEM,
                    ]
                    model_info["mdx_stem_count"] = 4
                    model_info["is_4_stem"] = True

            # For Demucs models, most are 4-stem (vocals, drums, bass, other)
            elif model_type == ac.DEMUCS_MODELS_KEY:
                model_info["demucs_stems"] = [
                    ac.VOCAL_STEM,
                    ac.DRUM_STEM,
                    ac.BASS_STEM,
                    ac.OTHER_STEM,
                ]
                model_info["is_4_stem"] = True

                # Check if it's a 2-stem model (some Demucs models are vocal/instrumental only)
                model_lower = model_name.lower()
                if any(
                    keyword in model_lower
                    for keyword in ["2stem", "2-stem", "vocal", "inst"]
                ):
                    model_info["demucs_stems"] = [ac.VOCAL_STEM, ac.INST_STEM]
                    model_info["is_4_stem"] = False

            return model_info

        except Exception as e:
            print(f"Error getting model info for {model_name}: {e}")
            return None

    def download_model(
        self,
        model_type_ui_name: str,
        model_display_name: str,
        download_target_info: Any,
    ):
        """Downloads the specified model using the download manager."""
        # Initial progress
        self.download_progress.emit(model_display_name, 0)

        # Check if this is a multi-file Demucs model
        is_multi_file_demucs = False
        if model_type_ui_name == ac.DEMUCS_MODELS_KEY and isinstance(
            download_target_info, dict
        ):
            if any(tag in model_display_name for tag in [ac.DEMUCS_V3, ac.DEMUCS_V4]):
                if all(isinstance(v, str) for v in download_target_info.values()):
                    is_multi_file_demucs = True
            elif (
                not any(
                    k in download_target_info
                    for k in ["model_url", "weight_file", "config_name"]
                )
                and all(isinstance(v, str) for v in download_target_info.values())
                and len(download_target_info) > 1
            ):
                is_multi_file_demucs = True

        if is_multi_file_demucs:
            # For multi-file Demucs models, we need to download each file separately
            all_files_successful = True
            error_messages = []
            num_files = len(download_target_info)
            files_processed = 0

            # Check if this is a v3/v4 model set that should go to v3_v4_repo
            is_v3_v4_model_set = (
                any(tag in model_display_name for tag in [ac.DEMUCS_V3, ac.DEMUCS_V4])
                or any(
                    file_name.endswith(".yaml")
                    for file_name in download_target_info.keys()
                )
                or any(url.endswith(".yaml") for url in download_target_info.values())
            )

            for file_name_in_dict, url_or_path_in_dict in download_target_info.items():
                files_processed += 1
                current_file_display_name = f"{model_display_name} ({file_name_in_dict} {files_processed}/{num_files})"

                actual_download_url = self._construct_full_url(
                    url_or_path_in_dict,
                    model_type_ui_name,
                    is_config=file_name_in_dict.endswith(".yaml"),
                )

                # Pass the original model display name to preserve v3/v4 context
                # This ensures all files from a v3/v4 model set go to the right directory
                model_name_for_download = (
                    model_display_name if is_v3_v4_model_set else file_name_in_dict
                )

                # Start download for this file
                self.download_manager.start_download(
                    model_name=model_name_for_download,
                    download_url=actual_download_url,
                    model_type=model_type_ui_name,
                    config_url=None,  # Each part is handled as a main download
                )
        else:
            # Original logic for single file or model+config
            raw_model_url_str = None
            raw_config_url_str = None

            if isinstance(download_target_info, str):
                raw_model_url_str = download_target_info
            elif isinstance(download_target_info, dict):
                if "model_url" in download_target_info:
                    raw_model_url_str = download_target_info["model_url"]
                if "config_url" in download_target_info:
                    raw_config_url_str = download_target_info["config_url"]
                if not raw_model_url_str and "weight_file" in download_target_info:
                    raw_model_url_str = download_target_info["weight_file"]
                if not raw_config_url_str and "config_name" in download_target_info:
                    raw_config_url_str = download_target_info["config_name"]
                if not raw_model_url_str:
                    if len(download_target_info) == 1:
                        raw_model_url_str = list(download_target_info.values())[0]
                    else:
                        primary_filename = (
                            self._get_primary_filename_from_download_info(
                                download_target_info
                            )
                        )
                        if primary_filename in download_target_info and isinstance(
                            download_target_info[primary_filename], str
                        ):
                            raw_model_url_str = download_target_info[primary_filename]
                if not raw_config_url_str and not (
                    raw_model_url_str and raw_model_url_str.endswith(".yaml")
                ):
                    yaml_val = next(
                        (
                            v
                            for k, v in download_target_info.items()
                            if isinstance(v, str) and v.endswith(".yaml")
                        ),
                        None,
                    )
                    if not yaml_val:
                        yaml_val = next(
                            (
                                k
                                for k, v in download_target_info.items()
                                if isinstance(k, str)
                                and k.endswith(".yaml")
                                and v == download_target_info[k]
                            ),
                            None,
                        )
                    if yaml_val:
                        raw_config_url_str = yaml_val

            model_url = None
            config_url = None

            if raw_model_url_str:
                model_url = self._construct_full_url(
                    raw_model_url_str,
                    model_type_ui_name,
                    is_config=raw_model_url_str.endswith(".yaml"),
                )
            if raw_config_url_str:
                config_url = self._construct_full_url(
                    raw_config_url_str, model_type_ui_name, is_config=True
                )

            if model_url and model_url.endswith(".yaml") and model_url == config_url:
                config_url = None
            if not model_url and config_url and config_url.endswith(".yaml"):
                model_url = config_url
                config_url = None

            if not model_url:
                self.download_finished.emit(
                    model_type_ui_name,
                    model_display_name,
                    False,
                    f"Could not determine download URL for {model_display_name}.",
                )
                return

            # For single file downloads, get the filename to save
            filename_to_save = (
                raw_model_url_str
                if isinstance(download_target_info, str)
                else self._get_primary_filename_from_download_info(download_target_info)
            )
            if not filename_to_save:
                filename_to_save = model_display_name  # Fallback

            # Start the download using the download manager
            self.download_manager.start_download(
                model_name=filename_to_save,
                download_url=model_url,
                model_type=model_type_ui_name,
                config_url=config_url,
            )

    def _scan_path_for_identifiers(
        self,
        scan_path: Path,
        extensions: list,
        is_mdx_ckpt_special_case: bool = False,
        recursive: bool = False,
    ) -> list[str]:
        identifiers = []
        if not scan_path or not scan_path.is_dir():
            return identifiers
        glob_pattern = "**/*" if recursive else "*"
        for item in scan_path.glob(glob_pattern):
            if item.is_file() and item.suffix.lower() in extensions:
                file_stem = item.stem
                if file_stem in EXCLUDED_FILENAMES_STEMS:
                    continue
                identifier = file_stem
                if is_mdx_ckpt_special_case and item.suffix.lower() == ".ckpt":
                    identifier = item.name
                identifiers.append(identifier)
        return list(set(identifiers))

    def _load_name_mapper(self, method_specific_models_path: Path) -> dict:
        mapper_file_path = method_specific_models_path / MAPPER_FILE_REL_PATH
        if mapper_file_path.is_file():
            try:
                with open(mapper_file_path, encoding="utf-8") as f:
                    mapper_content = json.load(f)
                    # print(f"Successfully loaded name mapper from: {mapper_file_path}")
                    return mapper_content
            except json.JSONDecodeError as e:
                print(
                    f"ERROR: JSONDecodeError when loading name mapper from {mapper_file_path}: {e}"
                )
                # Consider logging this error more formally.
                pass
            except Exception as e:
                print(
                    f"ERROR: Unexpected error loading name mapper from {mapper_file_path}: {e}"
                )
                # Consider logging this error.
                pass
        else:
            print(f"Warning: Name mapper file not found at: {mapper_file_path}")
        return {}

    def _get_display_name_from_mapper(
        self, scanned_identifier: str, name_mapper: dict
    ) -> tuple[str, bool]:
        if not name_mapper:
            return scanned_identifier, False
        for mapper_key_filename, display_name_from_mapper in name_mapper.items():
            if scanned_identifier in mapper_key_filename:
                return (
                    display_name_from_mapper,
                    display_name_from_mapper != scanned_identifier,
                )
        return scanned_identifier, False

    def get_available_methods(self) -> list:  # Corrected in response #35
        # Debug print removed
        return [
            ac.VR_ARCH_MODELS_KEY,
            ac.MDX_NET_MODELS_KEY,
            ac.DEMUCS_MODELS_KEY,
            ac.ENSEMBLE_MODELS_KEY,
        ]

    def get_available_models(self, method_name: str) -> list:  # Logic from response #35
        base_models_dir = self._get_project_models_dir()
        if not base_models_dir:
            return []
        method_subdir_key = MODEL_SUBDIRS.get(method_name)
        if not method_subdir_key:
            return []
        method_path = base_models_dir / method_subdir_key
        scanned_identifiers = []
        name_mapper = {}
        if method_name == ac.VR_ARCH_MODELS_KEY:
            scanned_identifiers = self._scan_path_for_identifiers(
                method_path, VR_ARCH_SCAN_EXTENSIONS, recursive=True
            )
        elif method_name == ac.MDX_NET_MODELS_KEY:
            scanned_identifiers = self._scan_path_for_identifiers(
                method_path,
                MDX_SCAN_EXTENSIONS,
                is_mdx_ckpt_special_case=True,
                recursive=True,
            )
            name_mapper = self._load_name_mapper(method_path)
        elif method_name == ac.DEMUCS_MODELS_KEY:
            ids_legacy = self._scan_path_for_identifiers(
                method_path, DEMUCS_LEGACY_SCAN_EXTENSIONS, recursive=False
            )
            newer_repo_path = method_path / DEMUCS_V3_V4_REPO_DIR_NAME
            ids_v3_v4_yaml = self._scan_path_for_identifiers(
                newer_repo_path, DEMUCS_V3_V4_SCAN_EXTENSIONS, recursive=True
            )
            scanned_identifiers = list(set(ids_legacy + ids_v3_v4_yaml))
            name_mapper = self._load_name_mapper(method_path)
        if not scanned_identifiers:
            return []
        final_display_names = []
        for identifier in scanned_identifiers:
            display_name, was_mapped = self._get_display_name_from_mapper(
                identifier, name_mapper
            )
            if was_mapped:  # Add if it was successfully mapped to a display name
                final_display_names.append(display_name)
            elif (
                not name_mapper
            ):  # If no mapper exists (like for VR models), add the identifier directly
                # Strip file extensions for cleaner display
                clean_name = self._strip_model_extension(identifier)
                final_display_names.append(clean_name)
            else:  # Mapper exists but model wasn't found - add the identifier anyway
                # This ensures newly downloaded models show up even if not in mapper
                # Strip file extensions for cleaner display
                clean_name = self._strip_model_extension(identifier)
                final_display_names.append(clean_name)

        return natsort.natsorted(list(set(final_display_names)))

    def _strip_model_extension(self, model_name: str) -> str:
        """Remove common model file extensions for cleaner display."""
        # Common model extensions
        extensions_to_strip = [".pth", ".onnx", ".ckpt", ".pt", ".bin", ".pkl"]

        for ext in extensions_to_strip:
            if model_name.lower().endswith(ext.lower()):
                return model_name[: -len(ext)]

        return model_name

    def start_processing(self, settings_dict: dict):
        # Debug print removed
        if self.processing_thread and self.processing_thread.isRunning():
            # Debug print removed
            # Optionally, emit a signal here indicating processing is already active
            return

        # Use the new ProcessingThread
        self.processing_thread = ProcessingThread(settings_dict)

        # Connect signals from the thread (which relays them from the worker)
        self.processing_thread.progress_updated.connect(self.progress_updated)
        self.processing_thread.processing_finished.connect(self.processing_finished)

        # Clean up thread when finished
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)
        self.processing_thread.finished.connect(
            self._on_processing_thread_finished
        )  # Connect to our new slot

        # Debug print removed
        self.processing_thread.start()

    def stop_processing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            # Debug print removed
            self.processing_thread.stop_processing()  # Call the method on our ProcessingThread
            # The thread will manage stopping its worker.
            # We might want to wait for it to actually finish or provide a timeout.
        else:
            # Debug print removed
            pass  # Or emit a signal
