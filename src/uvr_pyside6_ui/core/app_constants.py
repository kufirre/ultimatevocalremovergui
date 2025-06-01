# src/uvr_pyside6_ui/core/app_constants.py
from pathlib import Path
import platform

# --- Online Catalog and Cache ---
DOWNLOAD_CHECKS_URL = "https://raw.githubusercontent.com/TRvlvr/application_data/main/filelists/download_checks.json" # From UVR v5.6.0 constants
MODEL_REPO_URL_BASE = "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/" # From UVR v5.6.0 constants
DEMUCS_URL_BASE = "https://dl.fbaipublicfiles.com/" # For some Demucs models
DEMUCS_CONFIG_URL_BASE = "https://raw.githubusercontent.com/facebookresearch/demucs/main/demucs/remote/" # For Demucs .yaml configs

CACHE_DIR_NAME = ".uvr_pyside6_cache"
ONLINE_CATALOG_CACHE_FILENAME = "online_model_catalog_v2.json"

# --- Model Type Keys (for UI consistency and mapping to online catalog) ---
VR_ARCH_MODELS_KEY = "VR Arch"
MDX_NET_MODELS_KEY = "MDX-Net"
DEMUCS_MODELS_KEY = "Demucs"
ENSEMBLE_MODELS_KEY = "Ensemble" # Ensured Ensemble key

# Subdirectories under the main 'models' folder for each type
MODEL_TYPE_SUBDIRS = {
    VR_ARCH_MODELS_KEY: "VR_Models",
    MDX_NET_MODELS_KEY: "MDX_Net_Models",
    DEMUCS_MODELS_KEY: "Demucs_Models",
    ENSEMBLE_MODELS_KEY: None # Ensemble doesn't have its own primary model scan folder
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
    ENSEMBLE_MODELS_KEY: [] # Ensemble models are typically composed, not directly downloaded as "Ensemble type"
}

DOWNLOADED_MODEL_PRIMARY_EXTENSIONS = ['.pth', '.onnx', '.ckpt']
DOWNLOADED_DEMUCS_CONFIG_EXT = ['.yaml']

FALLBACK_ONLINE_CATALOG = { # Unchanged
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
        "Fallback Demucs v4 htdemucs_ft": {"config_name": "htdemucs_ft.yaml", "weight_file": "htdemucs_ft_weights.th"},
        "Fallback Demucs v2 tasnet": "tasnet-beb46fac.th"
    }
}

ENSEMBLE_MAIN_STEM_OPTIONS = [
    "Vocals/Instrumental",
    "Other/No Other",
    "Drums/No Drums",
    "Bass/No Bass",
    "4 Stem Ensemble", # All 4 Demucs stems
    "Multi-stem Ensemble" # All available stems from selected models
] # Based on UVR.py's ENSEMBLE_MAIN_STEM

ENSEMBLE_ALGORITHM_OPTIONS = [
    "Max Spec/Min Spec",
    "Max Spec/Max Spec",
    "Max Spec/Average",
    "Min Spec/Max Spec",
    "Min Spec/Min Spec",
    "Min Spec/Average",
    "Average/Max Spec",
    "Average/Min Spec",
    "Average/Average"
] # Based on UVR.py's ENSEMBLE_TYPE
# For 4-Stem ensemble, UVR.py just uses Max Spec, Min Spec, Average directly. We can handle this in presenter.
ENSEMBLE_ALGORITHM_4_STEM_OPTIONS = ["Max Spec", "Min Spec", "Average"]

# Specific Ensemble Algorithm Types (used in logic and potentially in ensemble JSON files)
AVERAGE_ENSEMBLE = "Average"
MAX_SPEC_ENSEMBLE = "Max Spec"
MIN_SPEC_ENSEMBLE = "Min Spec"
DEMUCS_ENSEMBLE_TYPE = "Demucs Ensemble" # A special type for Demucs multi-stem ensembles

# Text for model selection combo when in Ensemble mode (it doesn't have its own primary models)
ENSEMBLE_MODEL_INFO_TEXT = "[Select models from Ensemble panel below]"

# Ensemble Action Constants (for EnsembleSettingsView action combo)
ENSEMBLE_ACTION_LOAD = "Load Saved Ensemble..."
ENSEMBLE_ACTION_SAVE_AS = "Save Current Ensemble As..."
ENSEMBLE_ACTION_CLEAR_SELECTION = "Clear Model Selection"

DOWNLOAD_MORE_MODELS_TEXT = "--- Download More Models ---"

# --- Processing Method Constants ---
VR_ARCH_TYPE = 'VR Arc'
MDX_ARCH_TYPE = 'MDX-Net'
DEMUCS_ARCH_TYPE = 'Demucs'
ENSEMBLE_MODE = 'Ensemble Mode'

# --- Stem Constants ---
VOCAL_STEM = 'Vocals'
INST_STEM = 'Instrumental'
OTHER_STEM = 'Other'
BASS_STEM = 'Bass'
DRUM_STEM = 'Drums'
GUITAR_STEM = 'Guitar'
PIANO_STEM = 'Piano'

# --- General Constants ---
ALL_STEMS = 'All Stems'
CHOOSE_MODEL = 'Choose Model'
DEFAULT = 'Default'
AUTO_SELECT = 'Auto'

# --- Audio Format Constants ---
WAV = 'WAV'
FLAC = 'FLAC'
MP3 = 'MP3'

# --- Demucs Version Constants ---
DEMUCS_V1 = 'v1'
DEMUCS_V2 = 'v2'
DEMUCS_V3 = 'v3'
DEMUCS_V4 = 'v4'

# --- Demucs Source Mapping ---
DEMUCS_4_SOURCE_LIST = [BASS_STEM, DRUM_STEM, OTHER_STEM, VOCAL_STEM]
DEMUCS_4_SOURCE_MAPPER = {
    BASS_STEM: 0,
    DRUM_STEM: 1,
    OTHER_STEM: 2,
    VOCAL_STEM: 3
}

# --- Stem Pair Mapping Function ---
def secondary_stem(stem: str) -> str:
    """Determines secondary stem based on primary stem."""
    stem_pairs = {
        VOCAL_STEM: INST_STEM,
        INST_STEM: VOCAL_STEM,
        OTHER_STEM: f'No {OTHER_STEM}',
        BASS_STEM: f'No {BASS_STEM}',
        DRUM_STEM: f'No {DRUM_STEM}',
        GUITAR_STEM: f'No {GUITAR_STEM}',
        PIANO_STEM: f'No {PIANO_STEM}',
    }
    return stem_pairs.get(stem, f'No {stem}')

# --- Platform & System Constants ---
OPERATING_SYSTEM = platform.system()
SYSTEM_ARCH = platform.machine() # machine() is more reliable for architecture
SYSTEM_PROC = platform.processor()
ARM = 'arm' # Standard string for ARM arch
CPU_DEVICE = 'cpu' # Renamed from original 'CPU' for clarity
CUDA_DEVICE = 'cuda'
MPS_DEVICE = 'mps'
IS_MACOS = (OPERATING_SYSTEM == 'Darwin')
IS_WINDOWS = (OPERATING_SYSTEM == 'Windows')
IS_LINUX = (OPERATING_SYSTEM == 'Linux')

# --- Additional Stem Constants (from separate.py context) ---
LEAD_VOCAL_STEM = "lead_only"
BV_VOCAL_STEM = "backing_only"
LEAD_VOCAL_STEM_I = "with_lead_vocals" # Instrumental with lead
BV_VOCAL_STEM_I = "with_backing_vocals"  # Instrumental with backing
LEAD_VOCAL_STEM_LABEL = "Lead Vocals"
BV_VOCAL_STEM_LABEL = "Backing Vocals"
NO_STEM_TEXT = "No " # Text prefix for "No Other", "No Bass" etc.
DENOISE_NONE, DENOISE_S, DENOISE_M = 'None', 'Standard', 'Denoise Model'

# --- Demucs Specific Mappers (extending existing ones) ---
DEMUCS_2_SOURCE_MAPPER = {
    INST_STEM: 0,
    VOCAL_STEM: 1
}
# DEMUCS_6_SOURCE_MAPPER will require GUITAR_STEM, PIANO_STEM to be defined first
# Let's add them to the stem list above
# (Already added GUITAR_STEM, PIANO_STEM to the main list)
DEMUCS_6_SOURCE_MAPPER = {
    BASS_STEM: 0,
    DRUM_STEM: 1,
    OTHER_STEM: 2,
    VOCAL_STEM: 3,
    GUITAR_STEM: 4, # Ensure GUITAR_STEM is defined
    PIANO_STEM: 5   # Ensure PIANO_STEM is defined
}

# --- Error Handling Placeholders (can be expanded) ---
# Example, real error messages/codes would be better.
ERROR_MAPPER = {
    "WINDOW_SIZE_ERROR": "The selected window size is not compatible with the model.",
    "GENERAL_PROCESSING_ERROR": "An unspecified error occurred during processing."
}

# --- UI Message Placeholders (for console/logging in worker) ---
# These are more for the worker's internal logging/progress reporting if it mimics original print statements.
# The GUI itself should use its own text management.
SAVING_STEM_MESSAGE = ('Saving ', ' stem...')
DONE_MESSAGE = ' Done!\n'
INFERENCE_STEP_1_MESSAGE = 'Running inference...'
# Add other messages as needed, e.g.:
# INFERENCE_STEP_2_SEC_MESSAGE_FORMAT = 'Loading secondary model ({process_method}: {model_basename})...'

# --- Model File Extensions (already have some in DOWNLOADED_MODEL_PRIMARY_EXTENSIONS) ---
ONNX_EXT = '.onnx'
CKPT_EXT = '.ckpt'
PTH_EXT = '.pth'
YAML_EXT = '.yaml'
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
            'bins': 0, # Default, should be overridden by actual model params
            'band': {
                1: {'sr': 44100, 'hl': 1024, 'n_fft': 2048, 'crop_stop': 0},
                # Add more bands if necessary for default/fallback
            },
            'pre_filter_start': 0,
            'pre_filter_stop': 0,
            'aggr_correction': None
        }
        # If model_path_or_json_str is a path to a JSON, load it
        if model_path_or_json_str and Path(model_path_or_json_str).is_file():
            try:
                with open(model_path_or_json_str, 'r') as f:
                    json_params = json.load(f)
                    # Update self.param with loaded params, especially 'bins' and 'band'
                    self.param.update(json_params) # Simple update, might need deeper merge
            except Exception as e:
                print(f"Warning: Could not load dummy model parameters from {model_path_or_json_str}: {e}")

# --- Ensure platform is imported if used by constants above ---
import platform
import json # For DummyModelParameters

# --- Settings File ---
APP_SETTINGS_FILENAME = "uvr_pyside6_settings.json"
