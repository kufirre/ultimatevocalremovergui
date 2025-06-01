"""
Model data structure for UVR processing.
This replaces the original ModelData from UVR.py with a cleaner implementation.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import hashlib
import yaml 
from ml_collections import ConfigDict
import torch 

from . import app_constants as ac
try:
    from lib_v5.vr_network.model_param_init import ModelParameters
except ImportError:
    from .app_constants import DummyModelParameters as ModelParameters 

def get_project_root() -> Path:
    try: return Path(__file__).resolve().parents[3]
    except IndexError: return Path.cwd()

MODELS_DIR_PATH = get_project_root() / "models"
VR_MODELS_DIR_PATH = MODELS_DIR_PATH / ac.MODEL_TYPE_SUBDIRS[ac.VR_ARCH_MODELS_KEY]
MDX_MODELS_DIR_PATH = MODELS_DIR_PATH / ac.MODEL_TYPE_SUBDIRS[ac.MDX_NET_MODELS_KEY]
DEMUCS_MODELS_DIR_PATH = MODELS_DIR_PATH / ac.MODEL_TYPE_SUBDIRS[ac.DEMUCS_MODELS_KEY]
DEMUCS_NEWER_REPO_DIR_PATH = DEMUCS_MODELS_DIR_PATH / "v3_v4_repo" 
VR_PARAM_DIR_PATH = get_project_root() / "lib_v5" / "vr_network" / "modelparams"
MDX_HASH_DIR_PATH = MDX_MODELS_DIR_PATH / "model_data"
VR_HASH_DIR_PATH = VR_MODELS_DIR_PATH / "model_data"
MDX_C_CONFIG_PATH_DIR = MDX_HASH_DIR_PATH / "mdx_c_configs"
ENSEMBLE_CACHE_DIR = get_project_root() / "gui_data" / "saved_ensembles" 


@dataclass
class ModelData:
    process_method: str = ""
    model_name: str = "" 
    audio_file: Optional[str] = None
    export_path: Optional[str] = None
    model_path: Optional[str] = None 
    model_basename: Optional[str] = None
    model_hash: Optional[str] = None 
    mixer_path: Optional[str] = None

    is_gpu_conversion: bool = False
    device_set: str = ac.DEFAULT
    is_normalization: bool = False
    is_primary_stem_only: bool = False
    is_secondary_stem_only: bool = False
    save_format: str = ac.WAV
    wav_type_set: str = 'PCM_16'
    mp3_bit_set: str = '320k'
    
    aggression_setting: float = 0.05
    window_size: int = 512
    batch_size: int = 4 
    crop_size: int = 256 
    is_tta: bool = False
    is_post_process: bool = False
    is_high_end_process: bool = False
    post_process_threshold: float = 0.2
    
    mdx_segment_size: int = 256
    mdx_batch_size: int = 1
    compensate_str: str = ac.AUTO_SELECT 
    overlap_mdx: float = 0.25
    overlap_mdx23: str = "8" 
    margin: int = 44100
    denoise_option: str = ac.DENOISE_NONE
    is_mdx_c_seg_def: bool = True
    is_mdx_combine_stems: bool = True
    mdxnet_stem_select: str = ac.ALL_STEMS

    shifts: int = 2
    segment: str = ac.DEFAULT
    overlap: float = 0.25 
    is_split_mode: bool = True
    is_chunk_demucs: bool = False
    is_demucs_combine_stems: bool = True
    demucs_stems: str = ac.ALL_STEMS 
    
    semitone_shift: float = 0.0
    is_match_frequency_pitch: bool = True
    is_invert_spec: bool = False
    
    is_deverb_vocals: bool = False
    deverb_vocal_opt: str = ac.VOCAL_STEM
    is_vocal_split_model_activated: bool = False
    vocal_split_model_name: Optional[str] = None
    is_save_inst_vocal_splitter: bool = False
    is_inst_only_voc_splitter: bool = False
    is_save_vocal_only: bool = False

    is_secondary_model_chain_activated: bool = False 
    secondary_model_chain_name: Optional[str] = None 
    secondary_model_chain_scale: Optional[float] = None 
    
    vr_voc_inst_secondary_model: Optional[str] = None; vr_voc_inst_secondary_model_scale: Optional[float] = None
    vr_other_secondary_model: Optional[str] = None; vr_other_secondary_model_scale: Optional[float] = None
    vr_bass_secondary_model: Optional[str] = None; vr_bass_secondary_model_scale: Optional[float] = None
    vr_drums_secondary_model: Optional[str] = None; vr_drums_secondary_model_scale: Optional[float] = None
    mdx_voc_inst_secondary_model: Optional[str] = None; mdx_voc_inst_secondary_model_scale: Optional[float] = None
    mdx_other_secondary_model: Optional[str] = None; mdx_other_secondary_model_scale: Optional[float] = None
    mdx_bass_secondary_model: Optional[str] = None; mdx_bass_secondary_model_scale: Optional[float] = None
    mdx_drums_secondary_model: Optional[str] = None; mdx_drums_secondary_model_scale: Optional[float] = None
    demucs_voc_inst_secondary_model: Optional[str] = None; demucs_voc_inst_secondary_model_scale: Optional[float] = None
    demucs_other_secondary_model: Optional[str] = None; demucs_other_secondary_model_scale: Optional[float] = None
    demucs_bass_secondary_model: Optional[str] = None; demucs_bass_secondary_model_scale: Optional[float] = None
    demucs_drums_secondary_model: Optional[str] = None; demucs_drums_secondary_model_scale: Optional[float] = None
    
    secondary_model_4_stem_instances: List[Optional['ModelData']] = field(default_factory=lambda: [None]*4)
    secondary_model_4_stem_scales: List[Optional[float]] = field(default_factory=lambda: [None]*4)
    is_demucs_4_stem_secondaries_activated: bool = False 

    is_demucs_pre_proc_model_activate: bool = False
    demucs_pre_proc_model_name: Optional[str] = None
    is_demucs_pre_proc_model_inst_mix: bool = False

    primary_stem: str = ac.VOCAL_STEM
    secondary_stem: str = ac.INST_STEM
    primary_stem_native: Optional[str] = None
    
    vr_model_param: Optional[ModelParameters] = None
    model_samplerate: int = 44100
    model_capacity: List[int] = field(default_factory=lambda: [32, 128])
    is_vr_51_model: bool = False
    
    is_mdx_ckpt: bool = False
    is_mdx_c: bool = False
    mdx_c_configs: Optional[ConfigDict] = None 
    mdx_model_stems: List[str] = field(default_factory=list)
    mdx_dim_f_set: Optional[int] = None
    mdx_dim_t_set: Optional[int] = None
    mdx_n_fft_scale_set: Optional[int] = None
    compensate: Optional[float] = None 

    demucs_version: str = ac.DEMUCS_V4
    demucs_source_list: List[str] = field(default_factory=list) 
    demucs_source_map: Dict[str, int] = field(default_factory=dict) 
    demucs_stem_count: int = 0
    
    is_karaoke: bool = False
    is_bv_model: bool = False
    bv_model_rebalance: float = 0.0

    DENOISER_MODEL_PATH: Optional[str] = field(default_factory=lambda: str(VR_MODELS_DIR_PATH / "UVR-DeNoise-Lite.pth"))
    DEVERBER_MODEL_PATH: Optional[str] = field(default_factory=lambda: str(VR_MODELS_DIR_PATH / "UVR-DeEcho-DeReverb.pth"))
    is_denoise_model: bool = False

    secondary_model: Optional['ModelData'] = None 
    pre_proc_model: Optional['ModelData'] = None
    vocal_split_model: Optional['ModelData'] = None

    is_secondary_model: bool = False 
    is_pre_proc_model: bool = False  
    is_vocal_split_model: bool = False 
    is_primary_model_primary_stem_only: bool = False
    is_primary_model_secondary_stem_only: bool = False

    is_ensemble_mode: bool = False # True if this instance is the master ensemble config
    ensemble_models: List['ModelData'] = field(default_factory=list) 
    ensemble_type: str = ac.AVERAGE_ENSEMBLE # Default, e.g., "Average", "Max Spec", "Min Spec"
    ensemble_primary_stem: Optional[str] = None 
    ensemble_secondary_stem: Optional[str] = None 
    is_4_stem_ensemble: bool = False 
    is_multi_stem_ensemble: bool = False 
    model_and_process_tag: Optional[str] = None # Used by individual models within an ensemble run

    model_status: bool = True
    is_pitch_change: bool = False 

    def __post_init__(self):
        if self.model_name and not self.model_basename:
            self.model_basename = Path(self.model_name).stem
        if self.primary_stem: self.secondary_stem = ac.secondary_stem(self.primary_stem)
        try: self.is_pitch_change = float(self.semitone_shift) != 0.0
        except (ValueError, TypeError): self.is_pitch_change = False
        if self.DENOISER_MODEL_PATH and not Path(self.DENOISER_MODEL_PATH).exists(): self.DENOISER_MODEL_PATH = None
        if self.DEVERBER_MODEL_PATH and not Path(self.DEVERBER_MODEL_PATH).exists(): self.DEVERBER_MODEL_PATH = None
        if self.denoise_option != ac.DENOISE_NONE: self.is_denoise_model = True

    @classmethod
    def from_settings_dict(cls, settings: Dict[str, Any], 
                           _model_name_override: Optional[str] = None, 
                           _process_method_override: Optional[str] = None, 
                           _is_secondary_model_instance: bool = False,
                           _is_pre_proc_model_instance: bool = False,
                           _is_vocal_split_model_instance: bool = False,
                           _is_ensemble_member: bool = False, 
                           _primary_model_primary_stem_only: bool = False,
                           _primary_model_secondary_stem_only: bool = False
                           ) -> 'ModelData':
        
        init_kwargs = {}
        init_kwargs['is_secondary_model'] = _is_secondary_model_instance
        init_kwargs['is_pre_proc_model'] = _is_pre_proc_model_instance
        init_kwargs['is_vocal_split_model'] = _is_vocal_split_model_instance
        init_kwargs['is_primary_model_primary_stem_only'] = _primary_model_primary_stem_only
        init_kwargs['is_primary_model_secondary_stem_only'] = _primary_model_secondary_stem_only
        
        # This instance is an ensemble member if _is_ensemble_member is true.
        # If _is_ensemble_member is false, it could be a master ensemble object OR a single model.
        # This is determined by process_method.
        init_kwargs['is_ensemble_mode'] = _is_ensemble_member 

        process_method = _process_method_override if _process_method_override else settings.get('chosen_process_method', ac.VR_ARCH_TYPE)
        init_kwargs['process_method'] = process_method
        
        model_name = ""
        if _model_name_override: 
            model_name = _model_name_override
            if _is_ensemble_member and "==" in _model_name_override: 
                init_kwargs['model_and_process_tag'] = _model_name_override
                init_kwargs['process_method'], _, model_name = _model_name_override.partition("==")
        elif process_method == ac.ENSEMBLE_MODE:
            model_name = settings.get('ensemble_model', "") 
            init_kwargs['is_ensemble_mode'] = True # This instance IS the ensemble master
        elif process_method == ac.VR_ARCH_TYPE: model_name = settings.get('vr_model', "")
        elif process_method == ac.MDX_ARCH_TYPE: model_name = settings.get('mdx_net_model', "")
        elif process_method == ac.DEMUCS_ARCH_TYPE: model_name = settings.get('demucs_model', "")
        init_kwargs['model_name'] = model_name

        secondary_model_settings_keys = [
            'vr_voc_inst_secondary_model', 'vr_other_secondary_model', 'vr_bass_secondary_model', 'vr_drums_secondary_model',
            'mdx_voc_inst_secondary_model', 'mdx_other_secondary_model', 'mdx_bass_secondary_model', 'mdx_drums_secondary_model',
            'demucs_voc_inst_secondary_model', 'demucs_other_secondary_model', 'demucs_bass_secondary_model', 'demucs_drums_secondary_model',
            'vr_voc_inst_secondary_model_scale', 'vr_other_secondary_model_scale', 'vr_bass_secondary_model_scale', 'vr_drums_secondary_model_scale',
            'mdx_voc_inst_secondary_model_scale', 'mdx_other_secondary_model_scale', 'mdx_bass_secondary_model_scale', 'mdx_drums_secondary_model_scale',
            'demucs_voc_inst_secondary_model_scale', 'demucs_other_secondary_model_scale', 'demucs_bass_secondary_model_scale', 'demucs_drums_secondary_model_scale',
        ]
        for key in secondary_model_settings_keys:
            if key in settings:
                if "scale" in key: init_kwargs[key] = float(settings[key]) if settings[key] is not None and settings[key] != '' else None 
                else: init_kwargs[key] = settings[key] if settings[key] != ac.NO_MODEL else None

        field_map = { 
            'is_gpu_conversion': ('is_gpu_conversion', None), 'device_set': ('device_set', None),
            'is_normalization': ('is_normalization', None), 
            'save_format': ('save_format', None), 'wav_type_set': ('wav_type_set', None), 'mp3_bit_set': ('mp3_bit_set', None),
            'is_tta': ('is_tta', None), 'is_post_process': ('is_post_process', None), 
            'is_high_end_process': ('is_high_end_process', None), 'post_process_threshold': ('post_process_threshold', float),
            'aggression_setting': ('aggression_setting', lambda x: float(x)/100.0 if isinstance(x, (str,int)) and x != ac.DEFAULT else 0.05),
            'window_size': ('window_size', lambda x: int(x) if x != ac.DEFAULT else 512), 
            'batch_size': ('batch_size', lambda x: int(x) if x != ac.DEFAULT else 4), 
            'crop_size': ('crop_size', int),
            'mdx_segment_size': ('mdx_segment_size', int), 
            'mdx_batch_size': ('mdx_batch_size', lambda x: int(x) if x != ac.DEFAULT else 1),
            'compensate': ('compensate_str', None), 'overlap_mdx': ('overlap_mdx', float), 
            'overlap_mdx23': ('overlap_mdx23', str), 'margin': ('margin', int), 
            'denoise_option': ('denoise_option', None), 'is_mdx_c_seg_def': ('is_mdx_c_seg_def', None), 
            'is_mdx_combine_stems': ('is_mdx_combine_stems', None), 'mdxnet_stems': ('mdxnet_stem_select', None),
            'shifts': ('shifts', int), 'segment': ('segment', None), 'overlap': ('overlap', float), 
            'is_split_mode': ('is_split_mode', None), 'is_chunk_demucs': ('is_chunk_demucs', None),
            'is_demucs_combine_stems': ('is_demucs_combine_stems', None), 'demucs_stems': ('demucs_stems', None),
            'semitone_shift': ('semitone_shift', float), 
            'is_match_frequency_pitch': ('is_match_frequency_pitch', None), 'is_invert_spec': ('is_invert_spec', None),
            'is_deverb_vocals': ('is_deverb_vocals', None), 'deverb_vocal_opt': ('deverb_vocal_opt', None),
            'is_save_inst_vocal_splitter': ('is_save_inst_vocal_splitter', None),
            'is_inst_only_voc_splitter': ('is_inst_only_voc_splitter', None),
            'is_save_vocal_only': ('is_save_vocal_only', None),
            'is_use_opencl': ('is_use_opencl', None),
            f"{init_kwargs['process_method'].lower()}_is_secondary_model_activate": ('is_secondary_model_chain_activated', None), 
            'is_demucs_pre_proc_model_activate': ('is_demucs_pre_proc_model_activate', None),
            'demucs_pre_proc_model': ('demucs_pre_proc_model_name', None),
            'is_demucs_pre_proc_model_inst_mix': ('is_demucs_pre_proc_model_inst_mix', None),
            'is_set_vocal_splitter': ('is_vocal_split_model_activated', None),
            'set_vocal_splitter': ('vocal_split_model_name', None),
        }

        for settings_key, map_config in field_map.items():
            if settings_key in settings:
                attr_name, transform_func = map_config if isinstance(map_config, tuple) else (map_config, None)
                value = settings[settings_key]
                if transform_func:
                    try: value = transform_func(value)
                    except (ValueError, TypeError): print(f"Warning: Transform failed for {settings_key}"); continue
                init_kwargs[attr_name] = value
        
        if init_kwargs['process_method'] == ac.DEMUCS_ARCH_TYPE and not any([_is_secondary_model_instance, _is_pre_proc_model_instance, _is_vocal_split_model_instance, _is_ensemble_member]):
            init_kwargs['is_primary_stem_only'] = settings.get('is_primary_stem_only_Demucs', False)
            init_kwargs['is_secondary_stem_only'] = settings.get('is_secondary_stem_only_Demucs', False)
        elif not _is_ensemble_member : # For non-ensemble members, or non-Demucs primary models
            init_kwargs['is_primary_stem_only'] = settings.get('is_primary_stem_only', False)
            init_kwargs['is_secondary_stem_only'] = settings.get('is_secondary_stem_only', False)

        instance = cls(**init_kwargs)
        if 'input_paths' in settings and settings['input_paths']:
            raw_path = settings['input_paths'][0] if isinstance(settings['input_paths'], list) else settings['input_paths']
            instance.audio_file = str(Path(raw_path).resolve()) if raw_path else None
        
        # Use 'output_path' key from settings_dict as provided by ExecutionControlPresenter
        export_path_setting = settings.get('output_path') 
        if export_path_setting and isinstance(export_path_setting, str) and export_path_setting.strip():
            try:
                instance.export_path = str(Path(export_path_setting).resolve())
            except Exception as e:
                print(f"Warning: Error resolving export path '{export_path_setting}': {e}")
                instance.export_path = None
        else:
            instance.export_path = None

        if instance.model_status and instance.model_name and instance.model_name != ac.CHOOSE_MODEL:
            if instance.process_method == ac.ENSEMBLE_MODE and not _is_ensemble_member: 
                instance.model_path = str(ENSEMBLE_CACHE_DIR / instance.model_name) 
                if Path(instance.model_path).exists():
                    instance._load_ensemble_config(settings) 
                else:
                    print(f"Warning: Ensemble config file not found: {instance.model_path}")
                    instance.model_status = False
            elif not _is_ensemble_member or (instance.process_method != ac.ENSEMBLE_MODE): 
                instance.model_path = instance._determine_model_path()
                if instance.model_path and Path(instance.model_path).exists():
                    instance.model_hash = instance._get_model_hash(instance.model_path)
                    instance._load_and_derive_model_properties(settings) 
                else:
                    print(f"Warning: Model file not found: {instance.model_name} at {instance.model_path or 'undetermined'}")
                    instance.model_status = False
        elif not instance.model_name or instance.model_name == ac.CHOOSE_MODEL:
             instance.model_status = False
        
        instance.__post_init__()
        
        if instance.model_status and not any([_is_secondary_model_instance, _is_pre_proc_model_instance, _is_vocal_split_model_instance, _is_ensemble_member, instance.is_ensemble_mode]):
            if instance.is_secondary_model_chain_activated and instance.secondary_model_chain_name and \
               instance.secondary_model_chain_name != ac.NO_MODEL and \
               not instance.is_demucs_4_stem_secondaries_activated:
                sec_proc, _, sec_name = instance.secondary_model_chain_name.partition("==")
                instance.secondary_model = cls.from_settings_dict(settings, _model_name_override=sec_name, _process_method_override=sec_proc, _is_secondary_model_instance=True, _primary_model_primary_stem_only=instance.is_primary_stem_only, _primary_model_secondary_stem_only=instance.is_secondary_stem_only)
                if instance.secondary_model and not instance.secondary_model.model_status: instance.secondary_model = None
            
            if instance.is_demucs_4_stem_secondaries_activated:
                demucs_stem_map_to_ui_attr = {
                    ac.VOCAL_STEM: "demucs_voc_inst_secondary_model", ac.DRUMS_STEM: "demucs_drums_secondary_model",
                    ac.BASS_STEM: "demucs_bass_secondary_model", ac.OTHER_STEM: "demucs_other_secondary_model",
                }
                demucs_scale_map_to_ui_attr = {
                    ac.VOCAL_STEM: "demucs_voc_inst_secondary_model_scale", ac.DRUMS_STEM: "demucs_drums_secondary_model_scale",
                    ac.BASS_STEM: "demucs_bass_secondary_model_scale", ac.OTHER_STEM: "demucs_other_secondary_model_scale",
                }
                demucs_ordered_stems_for_secondary = instance.demucs_source_list 
                for i, stem_key in enumerate(demucs_ordered_stems_for_secondary):
                    if i >= len(instance.secondary_model_4_stem_instances): break 
                    model_attr_name = demucs_stem_map_to_ui_attr.get(stem_key); scale_attr_name = demucs_scale_map_to_ui_attr.get(stem_key)
                    sec_model_full_name = getattr(instance, model_attr_name, None); sec_model_scale = getattr(instance, scale_attr_name, None)
                    if sec_model_full_name and sec_model_full_name != ac.NO_MODEL:
                        sec_proc, _, sec_name = sec_model_full_name.partition("==")
                        secondary_model_instance = cls.from_settings_dict(settings, _model_name_override=sec_name, _process_method_override=sec_proc, _is_secondary_model_instance=True)
                        if secondary_model_instance and secondary_model_instance.model_status:
                            instance.secondary_model_4_stem_instances[i] = secondary_model_instance
                            instance.secondary_model_4_stem_scales[i] = sec_model_scale if sec_model_scale is not None else 0.9
            
            if instance.is_vocal_split_model_activated and instance.vocal_split_model_name and instance.vocal_split_model_name != ac.NO_MODEL:
                vs_proc, _, vs_name = instance.vocal_split_model_name.partition("==")
                instance.vocal_split_model = cls.from_settings_dict(settings, _model_name_override=vs_name, _process_method_override=vs_proc, _is_vocal_split_model_instance=True)
                if instance.vocal_split_model and not instance.vocal_split_model.model_status: instance.vocal_split_model = None

            if instance.is_demucs_pre_proc_model_activate and instance.demucs_pre_proc_model_name and instance.demucs_pre_proc_model_name != ac.NO_MODEL:
                pp_proc, _, pp_name = instance.demucs_pre_proc_model_name.partition("==")
                instance.pre_proc_model = cls.from_settings_dict(settings, _model_name_override=pp_name, _process_method_override=pp_proc, _is_pre_proc_model_instance=True)
                if instance.pre_proc_model and not instance.pre_proc_model.model_status: instance.pre_proc_model = None
        return instance

    def _determine_model_path(self) -> Optional[str]:
        if not self.model_name or self.model_name == ac.CHOOSE_MODEL: return None
        
        # Ensure this map uses the internal process_method constants (e.g., ac.VR_ARCH_TYPE which is 'VR Arc')
        # The directory paths (VR_MODELS_DIR_PATH etc.) are already correctly derived using UI keys from app_constants.
        models_dir_map = {
            ac.VR_ARCH_TYPE: VR_MODELS_DIR_PATH,        # 'VR Arc' -> project_root/models/VR_Models
            ac.MDX_ARCH_TYPE: MDX_MODELS_DIR_PATH,       # 'MDX-Net' -> project_root/models/MDX_Net_Models
            ac.DEMUCS_ARCH_TYPE: DEMUCS_MODELS_DIR_PATH  # 'Demucs' -> project_root/models/Demucs_Models
        }
        
        base_model_dir = models_dir_map.get(self.process_method)
        
        if not base_model_dir:
            # Fallback or error if self.process_method is not in the map (e.g. Ensemble Mode)
            # For Ensemble Mode, model_path is handled differently (points to ensemble config file)
            if self.process_method == ac.ENSEMBLE_MODE:
                 # This case should be handled before _determine_model_path is called for ensemble master,
                 # or this method should not be called for ensemble master.
                 # For ensemble members, self.process_method will be VR_ARCH_TYPE etc.
                return None 
            print(f"Warning: base_model_dir is None for process_method: {self.process_method}")
            return None
        current_model_name = self.model_name 
        current_model_basename = Path(current_model_name).stem
        if Path(current_model_name).is_file() and Path(current_model_name).exists(): return str(current_model_name)
        if (base_model_dir / current_model_name).exists(): return str(base_model_dir / current_model_name)
        extensions = []
        if self.process_method == ac.VR_ARCH_TYPE: extensions = ac.VR_ARCH_SCAN_EXTENSIONS
        elif self.process_method == ac.MDX_ARCH_TYPE: extensions = ac.MDX_SCAN_EXTENSIONS
        elif self.process_method == ac.DEMUCS_ARCH_TYPE:
            for ext in ac.DEMUCS_LEGACY_SCAN_EXTENSIONS + ac.DEMUCS_V3_V4_SCAN_EXTENSIONS:
                if (base_model_dir / f"{current_model_basename}{ext}").exists(): return str(base_model_dir / f"{current_model_basename}{ext}")
                if (DEMUCS_NEWER_REPO_DIR_PATH / f"{current_model_basename}{ext}").exists(): return str(DEMUCS_NEWER_REPO_DIR_PATH / f"{current_model_basename}{ext}")
            if current_model_name.endswith(".yaml") and (DEMUCS_NEWER_REPO_DIR_PATH / current_model_name).exists(): return str(DEMUCS_NEWER_REPO_DIR_PATH / current_model_name)
            return None
        for ext in extensions:
            if (base_model_dir / f"{current_model_basename}{ext}").exists(): return str(base_model_dir / f"{current_model_basename}{ext}")
        if self.process_method == ac.MDX_ARCH_TYPE and not current_model_basename.endswith(ac.CKPT_EXT):
             if (base_model_dir / f"{current_model_basename}{ac.CKPT_EXT}").exists(): return str(base_model_dir / f"{current_model_basename}{ac.CKPT_EXT}")
        return None

    def _get_model_hash(self, model_path_str: str) -> Optional[str]: # ... (content remains the same)
        model_path_obj = Path(model_path_str)
        if not model_path_obj.exists(): return None
        try:
            with open(model_path_obj, 'rb') as f: f.seek(-10000 * 1024, 2); return hashlib.md5(f.read()).hexdigest()
        except OSError:
            try: return hashlib.md5(model_path_obj.read_bytes()).hexdigest()
            except Exception: return None
        except Exception: return None

    def _get_secondary_model_settings(self, settings: Dict[str, Any]): # ... (content remains the same)
        prefix = self.process_method.lower()
        if self.primary_stem == ac.VOCAL_STEM or self.primary_stem == ac.INST_STEM:
            self.secondary_model_chain_name = getattr(self, f"{prefix}_voc_inst_secondary_model", None)
            self.secondary_model_chain_scale = getattr(self, f"{prefix}_voc_inst_secondary_model_scale", None)
        elif self.primary_stem == ac.BASS_STEM:
            self.secondary_model_chain_name = getattr(self, f"{prefix}_bass_secondary_model", None)
            self.secondary_model_chain_scale = getattr(self, f"{prefix}_bass_secondary_model_scale", None)
        elif self.primary_stem == ac.DRUMS_STEM:
            self.secondary_model_chain_name = getattr(self, f"{prefix}_drums_secondary_model", None)
            self.secondary_model_chain_scale = getattr(self, f"{prefix}_drums_secondary_model_scale", None)
        else: 
            self.secondary_model_chain_name = getattr(self, f"{prefix}_other_secondary_model", None)
            self.secondary_model_chain_scale = getattr(self, f"{prefix}_other_secondary_model_scale", None)
        if not (self.secondary_model_chain_name and self.secondary_model_chain_name != ac.NO_MODEL):
            self.is_secondary_model_chain_activated = False 
            self.secondary_model_chain_name = None
            self.secondary_model_chain_scale = None
        elif self.secondary_model_chain_scale is None: self.secondary_model_chain_scale = 0.9 
        if self.process_method == ac.DEMUCS_ARCH_TYPE and self.demucs_stems == ac.ALL_STEMS:
            demucs_stem_attrs = [self.demucs_voc_inst_secondary_model, self.demucs_drums_secondary_model, self.demucs_bass_secondary_model, self.demucs_other_secondary_model]
            if any(model_name and model_name != ac.NO_MODEL for model_name in demucs_stem_attrs): self.is_demucs_4_stem_secondaries_activated = True
            else: self.is_demucs_4_stem_secondaries_activated = False

    def _load_ensemble_config(self, settings: Dict[str, Any]):
        if not self.model_path or not Path(self.model_path).exists():
            print(f"Ensemble config file not found: {self.model_path}"); self.model_status = False; return
        try:
            with open(self.model_path, 'r', encoding='utf-8') as f: ensemble_data = json.load(f)
            self.ensemble_primary_stem = ensemble_data.get("ensemble_main_stem", ac.VOCAL_STEM)
            self.ensemble_secondary_stem = ac.secondary_stem(self.ensemble_primary_stem) 
            self.ensemble_type = ensemble_data.get("ensemble_type", ac.AVERAGE_ENSEMBLE) # Load ensemble type

            is_multi = False
            # A more robust check for multi-stem ensemble might be if ANY model in it is Demucs and outputs all stems
            # or if the ensemble_type itself implies it (e.g. a specific "Demucs_4_Stem_Average" type)
            # For now, using the original heuristic:
            if self.ensemble_type == ac.DEMUCS_ENSEMBLE_TYPE: is_multi = True 
            
            self.is_multi_stem_ensemble = is_multi
            self.is_4_stem_ensemble = is_multi 

            self.ensemble_models = []
            for model_config in ensemble_data.get("models", []):
                model_full_name = model_config.get("model_name") 
                if not model_full_name: continue
                member_settings = settings.copy() 
                member_settings.update(model_config.get("settings", {})) 
                member_model_data = ModelData.from_settings_dict(
                    member_settings, 
                    _model_name_override=model_full_name, 
                    _is_ensemble_member=True
                )
                if member_model_data.model_status: self.ensemble_models.append(member_model_data)
                else: print(f"Warning: Failed to load ensemble member: {model_full_name}")
            if not self.ensemble_models: print("Warning: Ensemble loaded no valid models."); self.model_status = False
        except Exception as e: print(f"Error loading ensemble config {self.model_path}: {e}"); self.model_status = False

    def _load_and_derive_model_properties(self, settings: Dict[str, Any]): 
        if not self.model_status or not self.model_path or not self.model_hash: self.model_status = False; return
        model_params_json = None; hash_dir = None
        if self.process_method == ac.VR_ARCH_TYPE: hash_dir = VR_HASH_DIR_PATH
        elif self.process_method == ac.MDX_ARCH_TYPE: hash_dir = MDX_HASH_DIR_PATH
        if hash_dir:
            hash_json_path = hash_dir / f"{self.model_hash}.json"
            if hash_json_path.exists():
                try:
                    with open(hash_json_path, 'r', encoding='utf-8') as f: model_params_json = json.load(f)
                except Exception as e: print(f"Error loading hash JSON {hash_json_path}: {e}"); self.model_status = False; return
            else: 
                print(f"Warning: Hash JSON not found: {hash_json_path} for {self.model_name}")
                # Fallback to master model_data.json
                master_json_path = hash_dir / "model_data.json"
                if master_json_path.exists():
                    print(f"Attempting to load parameters from master: {master_json_path}")
                    try:
                        with open(master_json_path, 'r', encoding='utf-8') as f_master:
                            master_data = json.load(f_master)
                        if self.model_hash in master_data:
                            model_params_json = master_data[self.model_hash]
                            print(f"Found parameters for hash {self.model_hash} in master JSON.")
                            # Optionally, create the specific hash.json file here for future faster lookups
                            # with open(hash_json_path, 'w', encoding='utf-8') as f_hash_specific:
                            #    json.dump(model_params_json, f_hash_specific, indent=4)
                            # print(f"Created specific hash JSON: {hash_json_path}")
                        else:
                            print(f"Warning: Hash {self.model_hash} not found in master JSON: {master_json_path}")
                    except Exception as e_master:
                        print(f"Error loading or parsing master JSON {master_json_path}: {e_master}")
                else:
                    print(f"Warning: Master JSON file not found: {master_json_path}")

        if self.process_method == ac.VR_ARCH_TYPE:
            if model_params_json:
                self.primary_stem = model_params_json.get("primary_stem", ac.VOCAL_STEM)
                param_file_name = model_params_json.get("vr_model_param")
                if param_file_name and ModelParameters is not ac.DummyModelParameters:
                    # Ensure the .json extension is present for the check and for ModelParameters
                    if not param_file_name.endswith(".json"):
                        param_file_name_with_ext = f"{param_file_name}.json"
                    else:
                        param_file_name_with_ext = param_file_name
                        
                    param_file = VR_PARAM_DIR_PATH / param_file_name_with_ext
                    
                    if param_file.exists(): 
                        self.vr_model_param = ModelParameters(str(param_file))
                    else: 
                        print(f"Warning: VR param file not found: {param_file}")
                        if param_file_name.endswith(".json"): 
                             param_file_no_ext = VR_PARAM_DIR_PATH / param_file_name.rsplit(".json",1)[0]
                             if param_file_no_ext.exists():
                                 self.vr_model_param = ModelParameters(str(param_file_no_ext))
                             else:
                                 self.model_status = False
                        else:
                             self.model_status = False
                elif not param_file_name and not self.is_secondary_model: 
                     print(f"Critical: 'vr_model_param' key missing or empty in JSON for {self.model_name}")
                     self.model_status = False
                
                if self.vr_model_param: self.model_samplerate = self.vr_model_param.param.get('sr', 44100)
                if "nout" in model_params_json and "nout_lstm" in model_params_json:
                    self.model_capacity = [model_params_json["nout"], model_params_json["nout_lstm"]]; self.is_vr_51_model = True
                self.is_karaoke = model_params_json.get(ac.IS_KARAOKEE_KEY, False)
                self.is_bv_model = model_params_json.get(ac.IS_BV_MODEL_KEY, False)
                if self.is_bv_model: self.bv_model_rebalance = model_params_json.get(ac.IS_BV_MODEL_REBAL_KEY, 0.0)
            elif not self.is_secondary_model: print(f"Critical: VR model params not found for {self.model_name}"); self.model_status = False
        elif self.process_method == ac.MDX_ARCH_TYPE:
            self.is_mdx_ckpt = self.model_path.endswith(ac.CKPT_EXT)
            self.mixer_path = str(MDX_MODELS_DIR_PATH / "mixer_val.ckpt")
            if model_params_json: 
                if "config_yaml" in model_params_json: 
                    self.is_mdx_c = True
                    config_yaml_path = MDX_C_CONFIG_PATH_DIR / model_params_json["config_yaml"]
                    if config_yaml_path.exists():
                        try:
                            with open(config_yaml_path, 'r', encoding='utf-8') as f_yaml: self.mdx_c_configs = ConfigDict(yaml.safe_load(f_yaml))
                            if self.mdx_c_configs:
                                target = self.mdx_c_configs.training.target_instrument
                                self.mdx_model_stems = [target] if target else self.mdx_c_configs.training.instruments
                                self.primary_stem = target if target else settings.get('mdxnet_stems', self.mdx_model_stems[0] if self.mdx_model_stems else ac.VOCAL_STEM)
                        except Exception as e: print(f"Error loading MDX-C YAML {config_yaml_path}: {e}"); self.model_status = False
                    else: print(f"Warning: MDX-C config YAML not found: {config_yaml_path}"); self.model_status = False
                else: 
                    self.compensate = float(model_params_json.get("compensate")) if self.compensate_str == ac.AUTO_SELECT else float(self.compensate_str)
                    self.mdx_dim_f_set = model_params_json.get("mdx_dim_f_set"); self.mdx_dim_t_set = model_params_json.get("mdx_dim_t_set")
                    self.mdx_n_fft_scale_set = model_params_json.get("mdx_n_fft_scale_set"); self.primary_stem = model_params_json.get("primary_stem", ac.VOCAL_STEM)
                self.is_karaoke = model_params_json.get(ac.IS_KARAOKEE_KEY, False)
                self.is_bv_model = model_params_json.get(ac.IS_BV_MODEL_KEY, False)
                if self.is_bv_model: self.bv_model_rebalance = model_params_json.get(ac.IS_BV_MODEL_REBAL_KEY, 0.0)
            elif self.is_mdx_ckpt and not self.is_mdx_c: 
                try:
                    ckpt = torch.load(self.model_path, map_location='cpu')
                    if 'hyper_parameters' in ckpt:
                        hparams = ckpt['hyper_parameters']
                        self.mdx_dim_f_set = hparams.get('dim_f', self.mdx_dim_f_set)
                        self.mdx_n_fft_scale_set = hparams.get('n_fft', self.mdx_n_fft_scale_set)
                        self.primary_stem = hparams.get('primary_stem', ac.VOCAL_STEM) 
                        self.mdx_c_configs = ConfigDict(hparams) 
                        print(f"Loaded hyper_parameters from CKPT for {self.model_name}")
                    else: print(f"Warning: hyper_parameters not found in MDX CKPT {self.model_name}")
                except Exception as e: print(f"Warning: Could not load hyper_parameters from MDX CKPT {self.model_name}: {e}")
            elif not self.is_secondary_model: print(f"Warning: MDX model params JSON not found for ONNX model {self.model_name}");
        elif self.process_method == ac.DEMUCS_ARCH_TYPE:
            self.demucs_version = ac.DEMUCS_V4 
            for ver_const, ver_str_list in ac.DEMUCS_VERSION_STRING_MAP.items():
                if any(s in self.model_name.lower() for s in ver_str_list): self.demucs_version = ver_const; break
            if ac.DEMUCS_UVR_MODEL_TAG in self.model_name: self.demucs_source_list, self.demucs_source_map, self.demucs_stem_count = ac.DEMUCS_2_SOURCE_LIST, ac.DEMUCS_2_SOURCE_MAPPER, 2
            elif self.demucs_version == ac.DEMUCS_V1 or self.demucs_version == ac.DEMUCS_V2: self.demucs_source_list, self.demucs_source_map, self.demucs_stem_count = ac.DEMUCS_2_SOURCE_LIST, ac.DEMUCS_2_SOURCE_MAPPER, 2
            elif ac.DEMUCS_6_STEM_TAG in self.model_name: self.demucs_source_list, self.demucs_source_map, self.demucs_stem_count = ac.DEMUCS_6_SOURCE_LIST, ac.DEMUCS_6_SOURCE_MAPPER, 6
            else: self.demucs_source_list, self.demucs_source_map, self.demucs_stem_count = ac.DEMUCS_4_SOURCE_LIST, ac.DEMUCS_4_SOURCE_MAPPER, 4
            chosen_demucs_stems_output = settings.get('demucs_stems', ac.ALL_STEMS) 
            self.primary_stem = chosen_demucs_stems_output if chosen_demucs_stems_output != ac.ALL_STEMS else self.demucs_source_list[0] if self.demucs_source_list else ac.VOCAL_STEM
        
        if not self.is_secondary_model and not self.is_pre_proc_model and not self.is_vocal_split_model:
             self.primary_stem_native = self.primary_stem 
        if self.primary_stem: self.secondary_stem = ac.secondary_stem(self.primary_stem)
        
        if self.is_secondary_model_chain_activated or self.is_demucs_4_stem_secondaries_activated:
            self._get_secondary_model_settings(settings)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__
