"""
Model data structure for UVR processing.
This replaces the original ModelData from UVR.py with a cleaner implementation.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path

# Import our own constants - much cleaner!
from . import app_constants as ac


@dataclass
class ModelData:
    """
    Data class containing all model configuration and processing parameters.
    This replaces the original ModelData class from UVR.py.
    """
    # Basic model info
    model_name: str = ""
    model_path: str = ""
    model_basename: str = ""
    process_method: str = ac.VR_ARCH_TYPE
    
    # Audio processing settings
    audio_file: str = ""
    export_path: str = ""
    
    # Stems
    primary_stem: str = ac.VOCAL_STEM
    secondary_stem: str = ac.INST_STEM
    primary_stem_native: str = ac.VOCAL_STEM
    
    # VR Architecture settings
    aggression_setting: int = 5
    window_size: int = 512
    batch_size: str = "4"
    crop_size: int = 256
    is_tta: bool = False
    is_post_process: bool = False
    is_high_end_process: bool = False
    post_process_threshold: float = 0.2
    vr_model_param: Optional[Any] = None
    
    # MDX-Net settings
    mdx_segment_size: int = 256
    mdx_batch_size: str = "1"
    compensate: str = ac.AUTO_SELECT
    is_denoise: bool = False
    denoise_option: str = "None"
    is_mdx_c: bool = False
    mdx_c_configs: Optional[Any] = None
    mdxnet_stem_select: str = ac.ALL_STEMS
    mixer_path: Optional[str] = None
    overlap_mdx: float = 0.25
    overlap_mdx23: str = "8"
    is_mdx_combine_stems: bool = True
    mdx_dim_f_set: int = 2048
    mdx_dim_t_set: int = 8
    mdx_n_fft_scale_set: int = 6144
    chunks: str = ac.AUTO_SELECT
    margin: int = 44100
    is_mdx_ckpt: bool = False
    is_mdx_c_seg_def: bool = False
    
    # Demucs settings
    segment: str = ac.DEFAULT
    shifts: int = 2
    overlap: float = 0.25
    is_chunk_demucs: bool = False
    is_split_mode: bool = True
    is_demucs_combine_stems: bool = True
    demucs_version: str = ac.DEMUCS_V4
    demucs_stems: str = ac.ALL_STEMS
    demucs_source_list: List[str] = field(default_factory=lambda: ac.DEMUCS_4_SOURCE_LIST)
    demucs_source_map: Dict[str, int] = field(default_factory=lambda: ac.DEMUCS_4_SOURCE_MAPPER)
    demucs_stem_count: int = 4
    pre_proc_model: Optional['ModelData'] = None
    
    # General processing settings
    is_gpu_conversion: bool = False
    is_normalization: bool = False
    is_primary_stem_only: bool = False
    is_secondary_stem_only: bool = False
    save_format: str = ac.WAV
    wav_type_set: str = 'PCM_16'
    mp3_bit_set: str = '320k'
    device_set: str = ac.DEFAULT
    is_use_opencl: bool = False
    
    # Secondary model settings
    is_secondary_model_activated: bool = False
    secondary_model: Optional['ModelData'] = None
    secondary_model_scale: float = 0.9
    is_secondary_model: bool = False
    is_primary_model_primary_stem_only: bool = False
    is_primary_model_secondary_stem_only: bool = False
    
    # Ensemble settings
    is_ensemble_mode: bool = False
    ensemble_primary_stem: str = ac.VOCAL_STEM
    ensemble_secondary_stem: str = ac.INST_STEM
    is_multi_stem_ensemble: bool = False
    is_4_stem_ensemble: bool = False
    
    # Advanced settings
    is_pitch_change: bool = False
    semitone_shift: str = "0"
    is_match_frequency_pitch: bool = True
    is_invert_spec: bool = False
    is_mixer_mode: bool = False
    
    # Vocal processing
    is_deverb_vocals: bool = False
    deverb_vocal_opt: str = 'Main Vocals Only'
    is_vocal_split_model: bool = False
    vocal_split_model: Optional['ModelData'] = None
    is_karaoke: bool = False
    is_bv_model: bool = False
    bv_model_rebalance: float = 0.0
    is_sec_bv_rebalance: bool = False
    is_save_inst_vocal_splitter: bool = False
    is_inst_only_voc_splitter: bool = False
    is_save_vocal_only: bool = False
    
    # Model capacity and sample rate
    model_samplerate: int = 44100
    model_capacity: List[int] = field(default_factory=lambda: [32, 128])
    is_vr_51_model: bool = False
    
    # Pre-processing
    is_pre_proc_model: bool = False
    is_demucs_pre_proc_model_inst_mix: bool = False
    
    # Denoising models
    DENOISER_MODEL: Optional[str] = None
    DEVERBER_MODEL: Optional[str] = None
    is_denoise_model: bool = False
    
    # 4-stem secondary models
    secondary_model_4_stem: List[Optional['ModelData']] = field(default_factory=lambda: [None, None, None, None])
    secondary_model_4_stem_scale: List[float] = field(default_factory=lambda: [0.9, 0.7, 0.5, 0.5])
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.model_basename and self.model_name:
            self.model_basename = Path(self.model_name).stem
        
        # Set secondary stem based on primary stem
        if self.primary_stem and not self.secondary_stem:
            self.secondary_stem = ac.secondary_stem(self.primary_stem)
    
    @classmethod
    def from_settings_dict(cls, settings: Dict[str, Any]) -> 'ModelData':
        """Create ModelData from settings dictionary."""
        # Map settings keys to ModelData fields
        model_data = cls()
        
        # Basic mappings
        field_mappings = {
            'chosen_process_method': 'process_method',
            'vr_model': 'model_name',
            'mdx_net_model': 'model_name',
            'demucs_model': 'model_name',
            'aggression_setting': 'aggression_setting',
            'window_size': 'window_size',
            'mdx_segment_size': 'mdx_segment_size',
            'batch_size': 'batch_size',
            'crop_size': 'crop_size',
            'is_tta': 'is_tta',
            'is_post_process': 'is_post_process',
            'is_high_end_process': 'is_high_end_process',
            'post_process_threshold': 'post_process_threshold',
            'segment': 'segment',
            'shifts': 'shifts',
            'overlap': 'overlap',
            'overlap_mdx': 'overlap_mdx',
            'overlap_mdx23': 'overlap_mdx23',
            'is_chunk_demucs': 'is_chunk_demucs',
            'is_split_mode': 'is_split_mode',
            'is_demucs_combine_stems': 'is_demucs_combine_stems',
            'is_mdx23_combine_stems': 'is_mdx_combine_stems',
            'demucs_stems': 'demucs_stems',
            'chunks': 'chunks',
            'margin': 'margin',
            'compensate': 'compensate',
            'is_denoise': 'is_denoise',
            'denoise_option': 'denoise_option',
            'is_mdx_c_seg_def': 'is_mdx_c_seg_def',
            'is_invert_spec': 'is_invert_spec',
            'is_deverb_vocals': 'is_deverb_vocals',
            'deverb_vocal_opt': 'deverb_vocal_opt',
            'mdx_batch_size': 'mdx_batch_size',
            'is_gpu_conversion': 'is_gpu_conversion',
            'is_primary_stem_only': 'is_primary_stem_only',
            'is_secondary_stem_only': 'is_secondary_stem_only',
            'is_normalization': 'is_normalization',
            'is_use_opencl': 'is_use_opencl',
            'save_format': 'save_format',
            'wav_type_set': 'wav_type_set',
            'mp3_bit_set': 'mp3_bit_set',
            'device_set': 'device_set',
            'semitone_shift': 'semitone_shift',
            'is_match_frequency_pitch': 'is_match_frequency_pitch',
        }
        
        # Apply mappings
        for settings_key, model_key in field_mappings.items():
            if settings_key in settings:
                setattr(model_data, model_key, settings[settings_key])
        
        # Handle special cases
        if 'input_paths' in settings and settings['input_paths']:
            model_data.audio_file = settings['input_paths'][0] if isinstance(settings['input_paths'], list) else settings['input_paths']
        
        if 'export_path' in settings:
            model_data.export_path = settings['export_path']
        
        # Set model path based on process method and model name
        if model_data.model_name and model_data.model_name != ac.CHOOSE_MODEL:
            model_data.model_path = model_data._get_model_path()
            model_data.model_basename = Path(model_data.model_name).stem
        
        return model_data
    
    def _get_model_path(self) -> str:
        """Get the full path to the model file."""
        if not self.model_name or self.model_name == ac.CHOOSE_MODEL:
            return ""
        
        # Get project root and models directory
        try:
            current_file_path = Path(__file__).resolve()
            project_root = current_file_path.parents[3]
            models_dir = project_root / "models"
        except IndexError:
            models_dir = Path.cwd() / "models"
        
        # Use our app constants for model subdirectories
        subdir = ac.MODEL_TYPE_SUBDIRS.get(self.process_method)
        if not subdir:
            return ""
        
        model_path = models_dir / subdir / self.model_name
        return str(model_path) if model_path.exists() else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ModelData to dictionary for serialization."""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, ModelData):
                result[field_name] = field_value.to_dict()
            elif isinstance(field_value, list) and field_value and isinstance(field_value[0], ModelData):
                result[field_name] = [item.to_dict() if item else None for item in field_value]
            else:
                result[field_name] = field_value
        return result
