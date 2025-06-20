"""Application constants for UVR PySide6 application."""

import json
import platform
from pathlib import Path

# --- Online Catalog and Cache ---
DOWNLOAD_CHECKS_URL = "https://raw.githubusercontent.com/TRvlvr/application_data/main/filelists/download_checks.json"  # From UVR v5.6.0 constants
MODEL_REPO_URL_BASE = "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/"  # From UVR v5.6.0 constants
DEMUCS_URL_BASE = "https://dl.fbaipublicfiles.com/"  # For some Demucs models
DEMUCS_CONFIG_URL_BASE = "https://raw.githubusercontent.com/facebookresearch/demucs/main/demucs/remote/"  # For Demucs .yaml configs

CACHE_DIR_NAME = ".uvr_pyside6_cache"
ONLINE_CATALOG_CACHE_FILENAME = "online_model_catalog_v2.json"

# --- Model Type Keys (for UI consistency and mapping to online catalog) ---
VR_ARCH_MODELS_KEY = "VR Arch"
MDX_NET_MODELS_KEY = "MDX-Net"
DEMUCS_MODELS_KEY = "Demucs"
ENSEMBLE_MODELS_KEY = "Ensemble"  # Ensured Ensemble key

# --- Advanced Settings Options ---
ENSEMBLE_SETTINGS = "Ensemble Settings"
AUDIO_ALIGNMENT_SETTINGS = "Audio Alignment Settings"

# Subdirectories under the main 'models' folder for each type
MODEL_TYPE_SUBDIRS = {
    VR_ARCH_MODELS_KEY: "VR_Models",
    MDX_NET_MODELS_KEY: "MDX_Net_Models",
    DEMUCS_MODELS_KEY: "Demucs_Models",
    ENSEMBLE_MODELS_KEY: None,  # Ensemble doesn't have its own primary model scan folder
}

# Keys as they appear in the JSON fetched from DOWNLOAD_CHECKS_URL
ONLINE_VR_DOWNLOAD_LIST_KEY = "vr_download_list"
ONLINE_MDX_DOWNLOAD_LIST_KEY = "mdx_download_list"
ONLINE_MDX23C_DOWNLOAD_LIST_KEY = "mdx23c_download_list"
ONLINE_DEMUCS_DOWNLOAD_LIST_KEY = "demucs_download_list"

# Mapping our UI model types to the list of keys to check in the online catalog
ONLINE_CATALOG_MAP = {
    VR_ARCH_MODELS_KEY: [ONLINE_VR_DOWNLOAD_LIST_KEY],
    MDX_NET_MODELS_KEY: [ONLINE_MDX_DOWNLOAD_LIST_KEY, ONLINE_MDX23C_DOWNLOAD_LIST_KEY],
    DEMUCS_MODELS_KEY: [ONLINE_DEMUCS_DOWNLOAD_LIST_KEY],
    ENSEMBLE_MODELS_KEY: [],  # Ensemble models are typically composed, not directly downloaded as "Ensemble type"
}

DOWNLOADED_MODEL_PRIMARY_EXTENSIONS = [".pth", ".onnx", ".ckpt"]
DOWNLOADED_DEMUCS_CONFIG_EXT = [".yaml"]

FALLBACK_ONLINE_CATALOG = {  # Unchanged
    ONLINE_VR_DOWNLOAD_LIST_KEY: {
        "Fallback VR Model (HP-UVR)": "Example_VR_1.pth",
        "Fallback UVR-DeNoise": "UVR-DeNoise-Lite.pth",
    },
    ONLINE_MDX_DOWNLOAD_LIST_KEY: {
        "Fallback MDX-NET Inst HQ 1": "Example_MDX_A.onnx",
        "Fallback MDX-NET Model B": "Example_MDX_B.ckpt",
    },
    ONLINE_MDX23C_DOWNLOAD_LIST_KEY: {},
    ONLINE_DEMUCS_DOWNLOAD_LIST_KEY: {
        "Fallback Demucs v4 htdemucs_ft": {
            "config_name": "htdemucs_ft.yaml",
            "weight_file": "htdemucs_ft_weights.th",
        },
        "Fallback Demucs v2 tasnet": "tasnet-beb46fac.th",
    },
}

ENSEMBLE_MAIN_STEM_OPTIONS = [
    "4 Stem Ensemble",  # All 4 Demucs stems - moved to default
    "Vocals/Instrumental",
    "Other/No Other",
    "Drums/No Drums",
    "Bass/No Bass",
    "Multi-stem Ensemble",  # All available stems from selected models
]

ENSEMBLE_ALGORITHM_OPTIONS = [
    "Max Spec/Min Spec",
    "Max Spec/Max Spec",
    "Max Spec/Average",
    "Min Spec/Max Spec",
    "Min Spec/Min Spec",
    "Min Spec/Average",
    "Average/Max Spec",
    "Average/Min Spec",
    "Average/Average",
]
# For 4-Stem ensemble, UVR.py just uses Max Spec, Min Spec, Average directly. We can handle this in presenter.
ENSEMBLE_ALGORITHM_4_STEM_OPTIONS = ["Max Spec", "Min Spec", "Average"]

# Specific Ensemble Algorithm Types (used in logic and potentially in ensemble JSON files)
AVERAGE_ENSEMBLE = "Average"
MAX_SPEC_ENSEMBLE = "Max Spec"
MIN_SPEC_ENSEMBLE = "Min Spec"
DEMUCS_ENSEMBLE_TYPE = (
    "Demucs Ensemble"  # A special type for Demucs multi-stem ensembles
)

# Text for model selection combo when in Ensemble mode (it doesn't have its own primary models)
ENSEMBLE_MODEL_INFO_TEXT = "[Select models from Ensemble panel below]"

# Ensemble Action Constants (for EnsembleSettingsView action combo)
ENSEMBLE_ACTION_LOAD = "Load Saved Ensemble..."
ENSEMBLE_ACTION_SAVE_AS = "Save Current Ensemble As..."
ENSEMBLE_ACTION_CLEAR_SELECTION = "Clear Model Selection"

# Ensemble checkbox options text
SAVE_ALL_OUTPUTS_TEXT = "Save All Outputs"
APPEND_ENSEMBLE_NAME_TEXT = "Append Ensemble Name"
WAVEFORM_ENSEMBLE_TEXT = "Use Waveform"

DOWNLOAD_MORE_MODELS_TEXT = "--- Download More Models ---"

# --- Processing Method Constants ---
VR_ARCH_TYPE = "VR Arc"
MDX_ARCH_TYPE = "MDX-Net"
DEMUCS_ARCH_TYPE = "Demucs"
ENSEMBLE_MODE = "Ensemble Mode"

# --- Stem Constants ---
VOCAL_STEM = "Vocals"
INST_STEM = "Instrumental"
OTHER_STEM = "Other"
BASS_STEM = "Bass"
DRUM_STEM = "Drums"
GUITAR_STEM = "Guitar"
PIANO_STEM = "Piano"
SECTIONS = ["vocals", "bass", "drums", "other"]

# Non-accompaniment stems (everything except instrumental)
NON_ACCOM_STEMS = [
    VOCAL_STEM,
    BASS_STEM,
    DRUM_STEM,
    OTHER_STEM,
    GUITAR_STEM,
    PIANO_STEM,
]

# --- General Constants ---
ALL_STEMS = "All Stems"
CHOOSE_MODEL = "Choose Model"
DEFAULT = "Default"
AUTO_SELECT = "Auto"
DEFAULT_SAMPLE_RATE = 44100

# --- Audio Format Constants ---
WAV = "WAV"
FLAC = "FLAC"
MP3 = "MP3"

# --- Demucs Version Constants ---
DEMUCS_V1 = "v1"
DEMUCS_V2 = "v2"
DEMUCS_V3 = "v3"
DEMUCS_V4 = "v4"

# --- Demucs Source Mapping ---
DEMUCS_4_SOURCE_LIST = [BASS_STEM, DRUM_STEM, OTHER_STEM, VOCAL_STEM]
DEMUCS_4_SOURCE_MAPPER = {BASS_STEM: 0, DRUM_STEM: 1, OTHER_STEM: 2, VOCAL_STEM: 3}

# ... (MODEL_SUBDIRS and other constants as in response #35, ensure ac.ENSEMBLE_MODELS_KEY is used) ...
MODEL_SUBDIRS = {
    VR_ARCH_MODELS_KEY: "VR_Models",
    MDX_NET_MODELS_KEY: "MDX_Net_Models",
    DEMUCS_MODELS_KEY: "Demucs_Models",
    ENSEMBLE_MODELS_KEY: None,
}
VR_ARCH_SCAN_EXTENSIONS = [".pth"]
MDX_SCAN_EXTENSIONS = [".onnx", ".ckpt"]
DEMUCS_LEGACY_SCAN_EXTENSIONS = [".ckpt", ".gz", ".th"]
DEMUCS_V3_V4_REPO_DIR_NAME = "v3_v4_repo"
DEMUCS_V3_V4_SCAN_EXTENSIONS = [".yaml"]
MAPPER_FILE_REL_PATH = Path("model_data") / "model_name_mapper.json"
EXCLUDED_FILENAMES_STEMS = ["model_data", "model_name_mapper", "download_links"]


# --- Stem Pair Mapping Function ---
def secondary_stem(stem: str) -> str:
    """Determines secondary stem based on primary stem."""
    stem_pairs = {
        VOCAL_STEM: INST_STEM,
        INST_STEM: VOCAL_STEM,
        OTHER_STEM: f"No {OTHER_STEM}",
        BASS_STEM: f"No {BASS_STEM}",
        DRUM_STEM: f"No {DRUM_STEM}",
        GUITAR_STEM: f"No {GUITAR_STEM}",
        PIANO_STEM: f"No {PIANO_STEM}",
    }
    return stem_pairs.get(stem, f"No {stem}")


# --- Platform & System Constants ---
OPERATING_SYSTEM = platform.system()
SYSTEM_ARCH = platform.machine()  # machine() is more reliable for architecture
SYSTEM_PROC = platform.processor()
ARM = "arm"  # Standard string for ARM arch
CPU_DEVICE = "cpu"  # Renamed from original 'CPU' for clarity
CUDA_DEVICE = "cuda"
MPS_DEVICE = "mps"
IS_MACOS = OPERATING_SYSTEM == "Darwin"
IS_WINDOWS = OPERATING_SYSTEM == "Windows"
IS_LINUX = OPERATING_SYSTEM == "Linux"

# --- ONNX Runtime Execution Providers ---
CPU_EXECUTION_PROVIDER = "CPUExecutionProvider"
CUDA_EXECUTION_PROVIDER = "CUDAExecutionProvider"

# --- Additional Stem Constants ---
LEAD_VOCAL_STEM = "lead_only"
BV_VOCAL_STEM = "backing_only"
LEAD_VOCAL_STEM_I = "with_lead_vocals"  # Instrumental with lead
BV_VOCAL_STEM_I = "with_backing_vocals"  # Instrumental with backing
LEAD_VOCAL_STEM_LABEL = "Lead Vocals"
BV_VOCAL_STEM_LABEL = "Backing Vocals"
NO_STEM_TEXT = "No "  # Text prefix for "No Other", "No Bass" etc.
DENOISE_NONE, DENOISE_S, DENOISE_M = "None", "Standard", "Denoise Model"

# --- Demucs Specific Mappers ---
DEMUCS_2_SOURCE_MAPPER = {INST_STEM: 0, VOCAL_STEM: 1}
# DEMUCS_6_SOURCE_MAPPER will require GUITAR_STEM, PIANO_STEM to be defined first
# Let's add them to the stem list above
# (Already added GUITAR_STEM, PIANO_STEM to the main list)
DEMUCS_6_SOURCE_MAPPER = {
    BASS_STEM: 0,
    DRUM_STEM: 1,
    OTHER_STEM: 2,
    VOCAL_STEM: 3,
    GUITAR_STEM: 4,  # Ensure GUITAR_STEM is defined
    PIANO_STEM: 5,  # Ensure PIANO_STEM is defined
}

# --- Error Handling Placeholders (can be expanded) ---
# Example, real error messages/codes would be better.
ERROR_MAPPER = {
    "WINDOW_SIZE_ERROR": "The selected window size is not compatible with the model.",
    "GENERAL_PROCESSING_ERROR": "An unspecified error occurred during processing.",
}

# --- UI Message Placeholders (for console/logging in worker) ---
# These are more for the worker's internal logging/progress reporting if it mimics original print statements.
# The GUI itself should use its own text management.
SAVING_STEM_MESSAGE = ("Saving ", " stem...")
DONE_MESSAGE = " Done!\n"
INFERENCE_STEP_1_MESSAGE = "Running inference..."
# Add other messages as needed, e.g.:
# INFERENCE_STEP_2_SEC_MESSAGE_FORMAT = 'Loading secondary model ({process_method}: {model_basename})...'

# --- Model File Extensions (already have some in DOWNLOADED_MODEL_PRIMARY_EXTENSIONS) ---
ONNX_EXT = ".onnx"
CKPT_EXT = ".ckpt"
PTH_EXT = ".pth"
YAML_EXT = ".yaml"
# GZ_EXT = '.gz' # If needed for Demucs v1
# TH_EXT = '.th' # If needed for Demucs v1

# --- VR Model Specific ---
# These might be better suited inside ModelData or VR specific logic if they vary per model
# For now, if they are truly global for VR Arch in this app:
VR_WINDOW_SIZE_DEFAULT = 512
VR_AGGRESSION_DEFAULT = 5

# --- MDX Model Specific ---
MDX_SEGMENT_SIZE_DEFAULT = 256
MDX_OVERLAP_DEFAULT = 0.25


# --- Fallback for ModelParameters if lib_v5 is not fully integrated yet ---
# This is a temporary measure. Ideally, ModelParameters comes from lib_v5.
class DummyModelParameters:
    def __init__(self, model_path_or_json_str=None):
        self.param = {
            "bins": 0,  # Default, should be overridden by actual model params
            "band": {
                1: {"sr": 44100, "hl": 1024, "n_fft": 2048, "crop_stop": 0},
                # Add more bands if necessary for default/fallback
            },
            "pre_filter_start": 0,
            "pre_filter_stop": 0,
            "aggr_correction": None,
        }
        # If model_path_or_json_str is a path to a JSON, load it
        if model_path_or_json_str and Path(model_path_or_json_str).is_file():
            try:
                with open(model_path_or_json_str) as f:
                    json_params = json.load(f)
                    # Update self.param with loaded params, especially 'bins' and 'band'
                    self.param.update(
                        json_params
                    )  # Simple update, might need deeper merge
            except Exception as e:
                print(
                    f"Warning: Could not load dummy model parameters from {model_path_or_json_str}: {e}"
                )


# --- Ensure platform is imported if used by constants above ---
import json  # For DummyModelParameters
import platform

# --- Settings File ---
APP_SETTINGS_FILENAME = "uvr_pyside6_settings.json"

# --- Model Parameter Keys (from original UVR constants) ---
IS_KARAOKEE_KEY = "is_karaoke"
IS_BV_MODEL_KEY = "is_bv_model"
IS_BV_MODEL_REBAL_KEY = "is_bv_model_rebalance"
DEMUCS_UVR_MODEL_TAG = (
    "UVR_Model"  # Used in model_data.py to identify certain Demucs models
)
DEMUCS_6_STEM_TAG = "6_HP_Demucs"  # Used in model_data.py
NO_MODEL = "----No Model----"  # Used in model_data.py for secondary model checks
DEMUCS_VERSION_STRING_MAP = {  # Used in model_data.py
    DEMUCS_V1: ["v1", "v1.mdx"],
    DEMUCS_V2: ["v2", "v2.mdx"],
    DEMUCS_V3: ["v3", "v3.mdx"],
    DEMUCS_V4: ["v4", "v4.mdx"],
}
DEMUCS_2_SOURCE_LIST = [VOCAL_STEM, INST_STEM]  # Used in model_data.py

# --- Presenter Keys (for dictionary access) ---
FILE_IO_PRESENTER_KEY = "file_io"
MODEL_SELECTION_PRESENTER_KEY = "model_selection"
PROCESSING_SETTINGS_PRESENTER_KEY = "processing_settings"
VR_ARCH_PRESENTER_KEY = "vr_arch"
MDX_NET_PRESENTER_KEY = "mdx_net"
DEMUCS_PRESENTER_KEY = "demucs"
ENSEMBLE_PRESENTER_KEY = "ensemble"
EXECUTION_CONTROL_PRESENTER_KEY = "execution_control"
BATCH_FILE_PRESENTER_KEY = "batch_file"

# --- UI Constants ---
APP_TITLE = "UVR - PySide6 Edition"
APP_VERSION = "0.1.0"

# QT Styles
FUSION_STYLE = "Fusion"

# Fonts
CENTURY_GOTHIC_FONT = "Century Gothic"
MONTSERRAT_FONT = "Montserrat"

# QRC Resource Paths
QRC_CENTURY_GOTHIC_PATH = ":/uvr/fonts/CenturyGothic.ttf"
QRC_MONTSERRAT_PATH = ":/uvr/fonts/Montserrat.ttf"
QRC_MAIN_STYLESHEET_PATH = ":/uvr/theme/style.qss"
QRC_PROGRESS_STYLESHEET_PATH = ":/uvr/theme/progress_bars.qss"
QRC_ICON_PATH = ":/uvr/img/uvr-port-icon.png"

# Processing Status Messages
STATUS_IDLE = "Idle"
STATUS_READY = "Ready"
STATUS_WAITING_PROCESS = "Waiting for process to start..."
STATUS_PROCESSING_COMPLETE = "Processing Complete"
STATUS_PROCESSING_ERROR = "Processing Error"
STATUS_COMPLETED = "Completed"
STATUS_FAILED = "Failed"

# Button Text
BTN_START_PROCESSING = "Start Processing"
BTN_STARTING = "Starting..."
BTN_PROCESSING = "Processing..."

# Log Messages
MSG_PROCESS_ALREADY_RUNNING = "Processing is already running."
MSG_REQUESTING_PROCESS_START = "Requesting process start..."
MSG_SETTINGS_HEADER = "=== Processing Settings ==="
MSG_SETTINGS_FOOTER = "=== End Settings ==="
MSG_INPUT_OUTPUT_REQUIRED = "Both input and output paths are required."
MSG_PROGRESS_COMPLETED = "Processing completed successfully"

# Demucs Processing Messages
MSG_DEMUCS_LOADING_SECURE = "Loading Demucs model with secure safe_globals"
MSG_DEMUCS_FALLBACK_TRUSTED = "Falling back to trusted loading for Demucs models..."
MSG_DEMUCS_STARTING = "Starting Demucs processing..."
MSG_DEMUCS_COMPLETED = "demucs_apply_model completed successfully"

# File Extensions
JSON_EXT = ".json"
TH_EXT = ".th"
GZ_EXT = ".gz"

# Menu Constants
MENU_FILE = "&File"
MENU_EDIT = "&Edit"
MENU_HELP = "&Help"
ACTION_QUIT = "&Quit"
ACTION_PREFERENCES = "&Preferences..."
ACTION_ABOUT = "&About"

# Dialog Messages
ABOUT_MESSAGE = "UVR GUI PySide6 Refactor."
ABOUT_TITLE = "About UVR - PySide6 Edition"

# Keyboard Shortcuts
SHORTCUT_QUIT = "Ctrl+Q"
SHORTCUT_PREFERENCES = "Ctrl+,"

# Error Messages
ERROR_MODEL_NOT_FOUND = "Model file not found"
ERROR_LOADING_MODEL = "Error loading model"
ERROR_PROCESSING_FAILED = "Processing failed"
ERROR_INVALID_INPUT = "Invalid input"
ERROR_WINDOW_SIZE_ERROR_MESSAGE = (
    "The selected window size is not compatible with the model."
)

# VR Processing Messages
MSG_VR_SPEC_UTILS_ERROR = "VR spec_utils/params error."
MSG_VR_MODEL_ERROR = "VR model/spec_utils error."

# MDX Processing Messages
MSG_MDX_LOADING = "Loading MDX model"
MSG_MDX_PROCESSING = "Processing with MDX"

# Processing Status
DONE_MESSAGE = " Done!\n"
SAVING_STEM_MESSAGE = ("Saving ", " stem...")

# Device Constants
CPU_DEVICE = "cpu"
CUDA_DEVICE = "cuda"
MPS_DEVICE = "mps"

# Window Size Error (already defined above, removing duplicate)

# File Format Extensions (extending existing ones)
WAV_EXT = ".wav"
FLAC_EXT = ".flac"
MP3_EXT = ".mp3"

# Audio Quality Settings
QUALITY_PCM_16 = "PCM_16"
QUALITY_PCM_24 = "PCM_24"
QUALITY_PCM_32 = "PCM_32"
QUALITY_FLOAT = "FLOAT"
QUALITY_DOUBLE = "DOUBLE"

# Progress Messages
PROGRESS_LOADING = "Loading..."
PROGRESS_PROCESSING = "Processing..."
PROGRESS_SAVING = "Saving..."
PROGRESS_COMPLETE = "Complete"

# Logging Configuration
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# Default log level for production (can be overridden by environment variable)
DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO
DEBUG_LOG_LEVEL = LOG_LEVEL_DEBUG

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Settings Keys Constants
class SettingKeys:
    """Constants for settings dictionary keys to prevent typos and ensure consistency."""
    
    # General Settings
    IS_GPU = "is_gpu_conversion"
    GPU_DEVICE_INDEX = "gpu_device_index"
    DEVICE_SET = "device_set"
    PRIMARY_STEM_ONLY = "is_primary_stem_only"
    SECONDARY_STEM_ONLY = "is_secondary_stem_only"
    
    # Audio Settings
    AUDIO_FILE = "audio_file"
    EXPORT_PATH = "export_path"
    SAVE_FORMAT = "save_format"
    WAV_TYPE_SET = "wav_type_set"
    MP3_BIT_SET = "mp3_bit_set"
    IS_NORMALIZATION = "is_normalization"
    SAMPLE_RATE = "sample_rate"
    MODEL_SAMPLERATE = "model_samplerate"
    
    # Model Settings
    MODEL_NAME = "model_name"
    MODEL_BASENAME = "model_basename"
    MODEL_PATH = "model_path"
    MODEL_STATUS = "model_status"
    PROCESS_METHOD = "process_method"
    PRIMARY_STEM = "primary_stem"
    SECONDARY_STEM = "secondary_stem"
    
    # VR Settings
    VR_MODEL_PARAM = "vr_model_param"
    WINDOW_SIZE = "window_size"
    BATCH_SIZE = "batch_size"
    CROP_SIZE = "crop_size"
    IS_TTA = "is_tta"
    IS_POST_PROCESS = "is_post_process"
    POST_PROCESS_THRESHOLD = "post_process_threshold"
    AGGRESSION_SETTING = "aggression_setting"
    IS_HIGH_END_PROCESS = "is_high_end_process"
    IS_VR_51_MODEL = "is_vr_51_model"
    MODEL_CAPACITY = "model_capacity"
    
    # MDX Settings
    IS_MDX_C = "is_mdx_c"
    MDX_SEGMENT_SIZE = "mdx_segment_size"
    MDX_DIM_T_SET = "mdx_dim_t_set"
    MDX_DIM_F_SET = "mdx_dim_f_set"
    MDX_N_FFT_SCALE_SET = "mdx_n_fft_scale_set"
    MDX_STEM_COUNT = "mdx_stem_count"
    MDX_MODEL_STEMS = "mdx_model_stems"
    COMPENSATE = "compensate"
    IS_DENOISE = "is_denoise"
    IS_INVERT_SPEC = "is_invert_spec"
    MDX_BATCH_SIZE = "mdx_batch_size"
    
    # Demucs Settings
    DEMUCS_VERSION = "demucs_version"
    DEMUCS_SOURCE_LIST = "demucs_source_list"
    DEMUCS_SOURCE_MAP = "demucs_source_map"
    DEMUCS_STEMS = "demucs_stems"
    IS_DEMUCS_4_STEM_SECONDARIES_ACTIVATED = "is_demucs_4_stem_secondaries_activated"
    SECONDARY_MODEL_4_STEM_INSTANCES = "secondary_model_4_stem_instances"
    SECONDARY_MODEL_4_STEM_SCALES = "secondary_model_4_stem_scales"
    IS_DEMUCS_COMBINE_STEMS = "is_demucs_combine_stems"
    SEGMENT = "segment"
    OVERLAP = "overlap"
    SHIFTS = "shifts"
    IS_SPLIT_MODE = "is_split_mode"
    
    # Ensemble Settings
    IS_ENSEMBLE_MODE = "is_ensemble_mode"
    ENSEMBLE_MODELS = "ensemble_models"
    ENSEMBLE_MAIN_STEM = "ensemble_main_stem"
    ENSEMBLE_TYPE = "ensemble_type"
    ENSEMBLE_ALGORITHM = "ensemble_algorithm"
    IS_4_STEM_ENSEMBLE = "is_4_stem_ensemble"
    
    # Secondary Model Settings
    SECONDARY_MODEL = "secondary_model"
    IS_SECONDARY_MODEL_CHAIN_ACTIVATED = "is_secondary_model_chain"
    SECONDARY_MODEL_CHAIN_SCALE = "secondary_model_chain_scale"
    
    # Vocal Splitter Settings
    VOCAL_SPLIT_MODEL = "vocal_split_model"
    IS_VOCAL_SPLIT_MODEL_ACTIVATED = "is_vocal_split_model_activated"
    IS_SAVE_INST_VOCAL_SPLITTER = "is_save_inst_set"
    
    # Other Settings
    IS_PITCH_CHANGE = "is_pitch_change"
    SEMITONE_SHIFT = "semitone_shift"
    IS_SAVE_ALL_OUTPUTS = "is_save_all_outputs"
    IS_USING_GPU = "is_using_GPU"
    
    # Demucs-specific stem-only settings
    PRIMARY_STEM_ONLY_DEMUCS = "is_primary_stem_only_Demucs"
    SECONDARY_STEM_ONLY_DEMUCS = "is_secondary_stem_only_Demucs"
