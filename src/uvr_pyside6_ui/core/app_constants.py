# src/uvr_pyside6_ui/core/app_constants.py
from pathlib import Path

# --- Online Catalog and Cache ---
DOWNLOAD_CHECKS_URL = "https://raw.githubusercontent.com/TRvlvr/application_data/main/filelists/download_checks.json"
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

# Text for model selection combo when in Ensemble mode (it doesn't have its own primary models)
ENSEMBLE_MODEL_INFO_TEXT = "[Select models from Ensemble panel below]"

# Ensemble Action Constants (for EnsembleSettingsView action combo)
ENSEMBLE_ACTION_LOAD = "Load Saved Ensemble..."
ENSEMBLE_ACTION_SAVE_AS = "Save Current Ensemble As..."
ENSEMBLE_ACTION_CLEAR_SELECTION = "Clear Model Selection"

DOWNLOAD_MORE_MODELS_TEXT = "--- Download More Models ---"
