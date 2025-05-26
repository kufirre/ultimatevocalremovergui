from PySide6.QtCore import QObject, Signal, QTimer, QThread
import time
from pathlib import Path
import os
import json
import natsort

MODEL_SUBDIRS = {
    "VR Arch": "VR_Models",
    "MDX-Net": "MDX_Net_Models",
    "Demucs": "Demucs_Models",
    "Ensemble": None
}

# Define specific extensions for each model type's initial scan, from UVR.py
VR_ARCH_SCAN_EXTENSIONS = ['.pth']
MDX_SCAN_EXTENSIONS = ['.onnx', '.ckpt']  # UVR.py primarily looks for these for MDX listing
DEMUCS_LEGACY_SCAN_EXTENSIONS = ['.ckpt', '.gz', '.th']
DEMUCS_V3_V4_REPO_DIR_NAME = "v3_v4_repo"
DEMUCS_V3_V4_SCAN_EXTENSIONS = ['.yaml']

# Mapper files are type-specific and within their respective model_data subfolders
# This constant defines the *relative path from the method's model directory*
# e.g. models/MDX_Net_Models / (Path("model_data") / "model_name_mapper.json")
MAPPER_FILE_REL_PATH = Path("model_data") / "model_name_mapper.json"

# Filename stems to generally ignore if they appear during scans
EXCLUDED_FILENAMES_STEMS = ["model_data", "model_name_mapper", "download_links"]  # This list seems fine


class MockProcessingWorker(QObject):  # This is fine
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


class UVRCoreAdapter(QObject):
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)
    models_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processing_thread = None
        self.worker = None
        print("UVRCoreAdapter Initialized.")

    def _get_project_models_dir(self) -> Path | None:  # Your version of this is good
        current = Path(__file__).resolve()
        for parent_dir in current.parents:
            candidate = parent_dir / "models"
            if candidate.is_dir():
                print(f"Adapter: Models base directory found at: {candidate}")
                return candidate
        cwd_candidate = Path.cwd() / "models"
        if cwd_candidate.is_dir():
            print(f"Adapter: Models base directory found relative to CWD: {cwd_candidate}")
            return cwd_candidate
        print(f"Adapter: ERROR: could not locate a 'models/' folder above {current} or in CWD.")
        return None

    def _scan_path_for_model_identifiers(self, scan_path: Path, extensions_to_scan: list,
                                   is_mdx_ckpt_special_case: bool = False,
                                   recursive: bool = False) -> list[str]:
        """
        Scans a given path for files with specified extensions.
        Returns list of identifiers (stems, or full filename for MDX .ckpt).
        """
        identifiers = []
        if not scan_path or not scan_path.is_dir():
            print(f"Adapter: Scan path for identifiers not found or not a dir: {scan_path}")
            return identifiers

        glob_pattern = '**/*' if recursive else '*'
        scan_type_msg = "recursively" if recursive else "non-recursively"
        print(f"Adapter: Scanning {scan_type_msg} in '{scan_path}' for {extensions_to_scan}")

        for item in scan_path.glob(glob_pattern):
            if item.is_file() and item.suffix.lower() in extensions_to_scan:
                file_stem = item.stem
                # Check against excluded stems FIRST
                if file_stem in EXCLUDED_FILENAMES_STEMS:
                    print(f"  -> Ignoring excluded file by stem: {item.name}")
                    continue

                identifier = file_stem
                if is_mdx_ckpt_special_case and item.suffix.lower() == ".ckpt":
                    identifier = item.name

                print(f"  -> Found identifier: '{identifier}' (from file: {item.name})")
                identifiers.append(identifier)
        return list(set(identifiers))

    def _load_name_mapper(self, method_specific_models_path: Path) -> dict:  # Path needs to be specific
        mapper_file_actual_path = method_specific_models_path / MAPPER_FILE_REL_PATH
        if mapper_file_actual_path.is_file():
            try:
                with open(mapper_file_actual_path, 'r', encoding='utf-8') as f:
                    mapper_content = json.load(f)
                    print(
                        f"Adapter: Successfully loaded name mapper: {mapper_file_actual_path.name} from {mapper_file_actual_path} (Keys sample: {list(mapper_content.keys())[:5]}...)")
                    return mapper_content
            except Exception as e:
                print(f"Adapter: ERROR loading/parsing name mapper {mapper_file_actual_path.name}: {e}")
        else:
            print(f"Adapter: Name mapper file not found at: {mapper_file_actual_path}")
        return {}

    def _get_display_name_from_mapper(self, scanned_identifier: str, name_mapper: dict) -> tuple[str, bool]:
        """
        Applies name mapping based on UVR.py's fix_name logic.
        Returns (display_name, was_mapped_to_a_different_name_flag).
        """
        if not name_mapper:
            return scanned_identifier, False

        for mapper_key_filename, display_name_from_mapper in name_mapper.items():
            if scanned_identifier in mapper_key_filename:
                print(f"    Mapping: ScannedID '{scanned_identifier}' in MapperKey '{mapper_key_filename}' "
                      f"-> Using DisplayName '{display_name_from_mapper}'")
                return display_name_from_mapper, display_name_from_mapper != scanned_identifier

        return scanned_identifier, False

    def get_available_methods(self) -> list:
        return list(MODEL_SUBDIRS.keys())

    def get_available_models(self, method_name: str) -> list:
        base_models_dir = self._get_project_models_dir()
        if not base_models_dir: return []

        method_subdir_name = MODEL_SUBDIRS.get(method_name)
        if not method_subdir_name: return []

        method_path = base_models_dir / method_subdir_name

        scanned_identifiers = []
        name_mapper = {}  # Default to empty mapper

        if method_name == "VR Arch":
            # VR: Scans VR_MODELS_DIR for .pth, returns stems. Recursive.
            scanned_identifiers = self._scan_path_for_model_identifiers(method_path, VR_ARCH_SCAN_EXTENSIONS,
                                                                        recursive=True)

        elif method_name == "MDX-Net":
            # MDX: UVR.py scans MDX_MODELS_DIR for .onnx (stem) and .ckpt (full name).
            # The scan should look for these primary weight files.
            scanned_identifiers = self._scan_path_for_model_identifiers(method_path, MDX_SCAN_EXTENSIONS,
                                                                        is_mdx_ckpt_special_case=True, recursive=True)
            name_mapper = self._load_name_mapper(method_path)
        elif method_name == "Demucs":
            # Demucs: Scans DEMUCS_MODELS_DIR (non-recursive) for .ckpt, .gz, .th (stems)
            ids_legacy = self._scan_path_for_model_identifiers(method_path, DEMUCS_LEGACY_SCAN_EXTENSIONS,
                                                               recursive=False)
            # And DEMUCS_NEWER_REPO_DIR (Demucs_Models/v3_v4_repo) for .yaml (stems) (recursive)
            newer_repo_path = method_path / DEMUCS_V3_V4_REPO_DIR_NAME
            ids_v3_v4_yaml = self._scan_path_for_model_identifiers(newer_repo_path, DEMUCS_V3_V4_SCAN_EXTENSIONS,
                                                                   recursive=True)
            scanned_identifiers = list(set(ids_legacy + ids_v3_v4_yaml))
            name_mapper = self._load_name_mapper(method_path)

        if not scanned_identifiers:
            print(f"Adapter: No model identifiers found by primary scan for {method_name}. List will be empty.")
            return []

        print(
            f"Adapter: Scanned Identifiers for {method_name} before mapping: {natsort.natsorted(scanned_identifiers)}")

        final_display_names = []
        for identifier in scanned_identifiers:
            display_name, was_mapped_and_truly_changed = self._get_display_name_from_mapper(identifier, name_mapper)

            if method_name in ["MDX-Net", "Demucs"]:
                if was_mapped_and_truly_changed:
                    final_display_names.append(display_name)
                else:
                    print(f"    Skipping '{identifier}' for {method_name} as it was not mapped to a *distinct* "
                          f"user-friendly name by the loaded mapper.")
            else:
                # For VR Arch (and Ensemble if it had models)
                # VR Arch has no mapper, so was_mapped_and_truly_changed will be False.
                # display_name will be the original identifier (stem).
                final_display_names.append(display_name)

        result = natsort.natsorted(list(set(final_display_names)))
        print(f"Adapter: Final display models for {method_name}: {result}")
        return result

    def start_processing(self, settings_dict: dict):
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

    def stop_processing(self):
        if self.worker and self.processing_thread and self.processing_thread.isRunning():
            print("Adapter: Requesting worker to stop...");
            self.worker.stop()
        else:
            print("Adapter: No process running to stop.")
