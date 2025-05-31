from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, List, Tuple, Optional
import gc
import gzip
import importlib
import librosa
import math
import numpy as np
import os # For os.path.join, os.stat, os.remove if not fully replaceable by pathlib
from pathlib import Path
import pydub
import soundfile as sf
import torch
import warnings

# Attempt to import onnxruntime, onnx, onnx2pytorch, demucs, lib_v5 related modules
# These should be available if listed in pyproject.toml and installed
try:
    onnxruntime = importlib.import_module('onnxruntime')
    onnx_load = importlib.import_module('onnx').load
    onnx2pytorch_ConvertModel = importlib.import_module('onnx2pytorch').ConvertModel
except ImportError:
    print("Warning: ONNX related packages not found. MDX-Net ONNX models may not work.")
    onnxruntime = None
    onnx_load = None
    onnx2pytorch_ConvertModel = None

try:
    demucs_apply = importlib.import_module('demucs.apply')
    demucs_hdemucs = importlib.import_module('demucs.hdemucs')
    demucs_model_v2 = importlib.import_module('demucs.model_v2')
    demucs_pretrained = importlib.import_module('demucs.pretrained')
    demucs_utils = importlib.import_module('demucs.utils')
except ImportError:
    print("Warning: Demucs package not found. Demucs models may not work.")
    demucs_apply = None
    demucs_hdemucs = None
    demucs_model_v2 = None
    demucs_pretrained = None
    demucs_utils = None

try:
    lib_v5_tfc_tdf_v3 = importlib.import_module('lib_v5.tfc_tdf_v3')
    lib_v5_spec_utils = importlib.import_module('lib_v5.spec_utils')
    lib_v5_vr_network_nets = importlib.import_module('lib_v5.vr_network.nets')
    lib_v5_vr_network_nets_new = importlib.import_module('lib_v5.vr_network.nets_new')
    lib_v5_vr_network_model_param_init = importlib.import_module('lib_v5.vr_network.model_param_init')
    lib_v5_mdxnet = importlib.import_module('lib_v5.mdxnet')
except ImportError:
    print("Warning: lib_v5 package not found. Some models may not work.")
    lib_v5_tfc_tdf_v3 = None
    lib_v5_spec_utils = None
    lib_v5_vr_network_nets = None
    lib_v5_vr_network_nets_new = None
    lib_v5_vr_network_model_param_init = None
    lib_v5_mdxnet = None

from scipy import signal
import audioread # May need to be added to pyproject.toml if not covered

from . import app_constants as ac
if TYPE_CHECKING:
    from .model_data import ModelData

warnings.filterwarnings("ignore")
cpu_device = torch.device('cpu') # Use ac.CPU_DEVICE

def clear_gpu_cache_logic(): # Renamed to avoid conflict if imported elsewhere
    gc.collect()
    if ac.IS_MACOS:
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    elif torch.cuda.is_available():
        torch.cuda.empty_cache()

class SeperateAttributesLogic: # Renamed
    def __init__(self, model_data: ModelData, process_data: dict, **kwargs):
        self.model_data = model_data
        self.process_data = process_data
        self.progress_value = 0
        
        # Callbacks from process_data
        self.set_progress_bar = process_data.get('set_progress_bar', lambda b, a=0: None)
        self.write_to_console = process_data.get('write_to_console', lambda m, b="": None)
        self.cached_source_callback = process_data.get('cached_source_callback', lambda pm, mn=None: (None,None))
        self.cached_model_source_holder = process_data.get('cached_model_source_holder', lambda pm, s, mn=None: None)
        self.process_iteration = process_data.get('process_iteration', lambda: None)

        # Populate attributes from model_data
        for key, value in model_data.to_dict().items(): # Use to_dict for safety
            setattr(self, key, value)

        # Overwrite with kwargs if any (e.g. for secondary model processing)
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        # Initialize device
        self.device = cpu_device
        self.run_type = ['CPUExecutionProvider'] # Default for ONNX
        self.is_other_gpu = False # For Demucs on MPS

        if self.is_gpu_conversion:
            if ac.IS_MACOS and torch.backends.mps.is_available():
                self.device = torch.device(ac.MPS_DEVICE)
                self.is_other_gpu = True # Demucs v1/v2 might not support MPS well
            elif torch.cuda.is_available():
                if self.device_set == ac.DEFAULT:
                    self.device = torch.device(ac.CUDA_DEVICE)
                else:
                    self.device = torch.device(f"{ac.CUDA_DEVICE}:{self.device_set}")
                self.run_type = ['CUDAExecutionProvider']
            # OpenCL/DirectML not implemented here based on original comments

        # Specific initializations based on process_method
        if self.process_method == ac.MDX_ARCH_TYPE:
            self._init_mdx()
        elif self.process_method == ac.DEMUCS_ARCH_TYPE:
            self._init_demucs()
        elif self.process_method == ac.VR_ARCH_TYPE:
            self._init_vr()
            
        # Vocal split specific paths
        vocal_stem_path_arg = kwargs.get('vocal_stem_path')
        if vocal_stem_path_arg:
            self.audio_file, self.audio_file_base = vocal_stem_path_arg
            self.audio_file_base_voc_split = lambda stem, split: os.path.join(self.export_path, f'{self.audio_file_base.replace("_(Vocals)", "")}_({stem}_{split}).wav')
        else:
            self.audio_file = process_data['audio_file'] # Already set from model_data
            self.audio_file_base = Path(self.audio_file).stem # Already set from model_data
            self.audio_file_base_voc_split = None


    def _init_mdx(self):
        self.primary_model_name, self.primary_sources = self.cached_source_callback(ac.MDX_ARCH_TYPE, model_name=self.model_basename)
        if not self.is_mdx_c: # is_mdx_c is a bool
            self.dim_f = self.mdx_dim_f_set
            self.dim_t = 2**self.mdx_dim_t_set
        self.n_fft = self.mdx_n_fft_scale_set
        self.chunks = int(self.chunks) if self.chunks != ac.AUTO_SELECT and self.chunks != "Full" else 0
        self.margin = int(self.margin) # Should be int
        self.adjust = 1.0 # from original
        self.dim_c = 4 # from original
        self.hop = 1024 # from original
        self.compensate = float(self.compensate) if self.compensate != ac.AUTO_SELECT else 1.035

    def _init_demucs(self):
        self.primary_model_name, self.primary_sources = self.cached_source_callback(ac.DEMUCS_ARCH_TYPE, model_name=self.model_basename)
        # Demucs v1/v2 might not work well on MPS, force CPU
        if self.is_other_gpu and self.demucs_version in [ac.DEMUCS_V1, ac.DEMUCS_V2]:
            self.device = cpu_device

    def _init_vr(self):
        self.primary_model_name, self.primary_sources = self.cached_source_callback(ac.VR_ARCH_TYPE, model_name=self.model_basename)
        if self.vr_model_param and lib_v5_vr_network_model_param_init:
            if isinstance(self.vr_model_param, str) and Path(self.vr_model_param).is_file():
                 self.mp = lib_v5_vr_network_model_param_init.ModelParameters(self.vr_model_param)
            elif isinstance(self.vr_model_param, dict): # If params are already a dict
                 self.mp = lib_v5_vr_network_model_param_init.ModelParameters(self.vr_model_param)
            else: # Fallback or error
                print(f"Warning: VR Model Param '{self.vr_model_param}' is not a valid path or dict. Using dummy params.")
                self.mp = ac.DummyModelParameters()
        else:
            self.mp = ac.DummyModelParameters()

        self.aggressiveness_settings = { # Renamed from self.aggressiveness to avoid conflict
            'value': self.aggression_setting,
            'split_bin': self.mp.param['band'][1]['crop_stop'] if self.mp and 'band' in self.mp.param and 1 in self.mp.param['band'] else 0,
            'aggr_correction': self.mp.param.get('aggr_correction') if self.mp else None
        }
        self.input_high_end_h = None # for VR high_end_process
        self.input_high_end = None # for VR high_end_process

    # ... (Port other methods from SeperateAttributes like check_label_secondary_stem_runs, start_inference_console_write etc.)
    # These methods will use self.write_to_console and self.set_progress_bar
    # Ensure all constants are prefixed with ac. or are available locally if defined above.

    def write_audio(self, stem_path: str, stem_source: np.ndarray, samplerate: int, stem_name: Optional[str] = None):
        """Writes the audio data to a file."""
        # This is a simplified version. The original has more complex logic for vocal splitting, de-reverb etc.
        # That logic needs to be carefully ported here or into sub-methods.
        self.write_to_console(f"{ac.SAVING_STEM_MESSAGE[0]}{stem_name or 'UnknownStem'}{ac.SAVING_STEM_MESSAGE[1]}")
        try:
            if lib_v5_spec_utils: # Check if module is available
                 normalized_source = lib_v5_spec_utils.normalize(stem_source, self.is_normalization)
            else: # Fallback
                 normalized_source = stem_source
            sf.write(stem_path, normalized_source, samplerate, subtype=self.wav_type_set) # Uses soundfile

            if self.save_format != ac.WAV:
                save_format_logic(stem_path, self.save_format, self.mp3_bit_set) # Needs save_format_logic

            self.write_to_console(ac.DONE_MESSAGE, base_text='')
            self.set_progress_bar(0.95) # Example progress
        except Exception as e:
            self.write_to_console(f"Error writing audio {stem_path}: {e}")
            # Consider emitting a failure signal or raising exception

    # Placeholder for other helper methods from original SeperateAttributes
    def pitch_fix(self, source, sr_pitched, org_mix):
        if not lib_v5_spec_utils: return source # Module check
        source = lib_v5_spec_utils.change_pitch_semitones(source, sr_pitched, semitone_shift=self.semitone_shift)[0]
        source = lib_v5_spec_utils.match_array_shapes(source, org_mix)
        return source

    def match_frequency_pitch(self, mix):
        source = mix
        if self.is_match_frequency_pitch and self.is_pitch_change and lib_v5_spec_utils:
            source, sr_pitched = lib_v5_spec_utils.change_pitch_semitones(mix, 44100, semitone_shift=-self.semitone_shift)
            source = self.pitch_fix(source, sr_pitched, mix)
        return source


# --- Ported Separation Classes ---
class SeperateMDXLogic(SeperateAttributesLogic):
    def seperate(self):
        # Simplified, actual logic needs full porting
        self.write_to_console("Starting MDX separation...")
        if not lib_v5_mdxnet or not onnxruntime or not onnx_load or not onnx2pytorch_ConvertModel or not lib_v5_tfc_tdf_v3:
            self.write_to_console("MDX or ONNX modules not available.")
            return {}

        mix = prepare_mix_logic(self.audio_file, self.wav_type_set)
        if not mix.any():
             self.write_to_console("Failed to load audio.")
             return {}
        
        # ... (Actual MDX demixing logic here, calling self.demix) ...
        # This is highly complex and involves porting the demix and run_model methods
        # For now, a placeholder:
        self.set_progress_bar(0.5)
        source_data = np.random.rand(*mix.shape).astype(np.float32) # Dummy output
        
        primary_stem_path = Path(self.export_path) / f"{self.audio_file_base}_({self.primary_stem}).wav"
        secondary_stem_path = Path(self.export_path) / f"{self.audio_file_base}_({self.secondary_stem}).wav"

        self.write_audio(str(primary_stem_path), source_data, 44100, self.primary_stem)
        if lib_v5_spec_utils:
            inverted_source = lib_v5_spec_utils.invert_stem(mix, source_data.T).T if self.is_invert_spec else mix - source_data
        else:
            inverted_source = mix - source_data # Fallback
        self.write_audio(str(secondary_stem_path), inverted_source, 44100, self.secondary_stem)
        
        clear_gpu_cache_logic()
        self.write_to_console("MDX separation finished (stub).")
        return {self.primary_stem: source_data, self.secondary_stem: inverted_source}

    def initialize_model_settings(self): # Ported from original
        if not lib_v5_tfc_tdf_v3: return
        self.n_bins = self.n_fft//2+1
        self.trim = self.n_fft//2
        self.chunk_size = self.hop * (self.mdx_segment_size-1)
        self.gen_size = self.chunk_size-2*self.trim
        self.stft = lib_v5_tfc_tdf_v3.STFT(self.n_fft, self.hop, self.dim_f, self.device)

    # ... (demix, run_model methods need to be ported here)

class SeperateMDXCLogic(SeperateAttributesLogic): # Renamed
    def seperate(self):
        self.write_to_console("MDXC separation (stub)")
        # ... port logic ...
        clear_gpu_cache_logic()
        return {}

class SeperateDemucsLogic(SeperateAttributesLogic): # Renamed
    def seperate(self):
        self.write_to_console("Demucs separation (stub)")
        # ... port logic ...
        clear_gpu_cache_logic()
        return {} # Should return dict of stem_name: audio_data

class SeperateVRLogic(SeperateAttributesLogic): # Renamed
    def seperate(self):
        self.write_to_console("VR separation (stub)")
        # ... port logic ...
        clear_gpu_cache_logic()
        return {}


# --- Ported Helper Functions ---
def prepare_mix_logic(mix_path_or_array: Any, wav_type_set: str = "PCM_16") -> np.ndarray: # Renamed
    """Loads and prepares the mix audio."""
    if isinstance(mix_path_or_array, np.ndarray):
        mix = mix_path_or_array
        if mix.ndim == 1:  # Mono to stereo
            mix = np.asfortranarray([mix, mix])
        # Ensure (channels, samples)
        return mix if mix.shape[0] == 2 else mix.T
    
    audio_path_str = str(mix_path_or_array)
    try:
        mix, sr = sf.read(audio_path_str, dtype='float32', always_2d=True)
        mix = mix.T  # Transpose to (channels, samples)
        if sr != 44100:
            mix = librosa.resample(mix, orig_sr=sr, target_sr=44100)
    except Exception as e:
        print(f"Error loading audio with soundfile/librosa: {audio_path_str}, {e}")
        # Fallback for audioread if it's a common issue like mp3 handling
        if audio_path_str.lower().endswith('.mp3'):
            try:
                return rerun_mp3_logic(audio_path_str)
            except Exception as e2:
                print(f"audioread fallback failed for {audio_path_str}: {e2}")
        return np.array([[],[]], dtype=np.float32) # Return empty stereo array on error

    if mix.ndim == 1: # Should be 2D now from always_2d=True
        mix = np.asfortranarray([mix,mix])
    return mix

def rerun_mp3_logic(audio_file_path: str, sample_rate: int = 44100) -> np.ndarray: # Renamed
    """Fallback for loading MP3s using audioread."""
    try:
        with audioread.audio_open(audio_file_path) as f:
            track_length = int(f.duration)
            pcm_data = []
            for buf in f:
                pcm_data.append(np.frombuffer(buf, dtype=np.int16)) # Assuming 16-bit PCM from audioread
            
            if not pcm_data: return np.array([[],[]], dtype=np.float32)

            full_pcm = np.concatenate(pcm_data)
            # Reshape based on channels
            num_channels = f.channels
            if num_channels == 1:
                full_pcm = np.repeat(full_pcm, 2) # Mono to stereo
            
            # Ensure correct shape (samples, channels) then normalize and transpose
            target_samples = track_length * f.samplerate
            if full_pcm.size < target_samples * num_channels: # Pad if needed
                full_pcm = np.pad(full_pcm, (0, target_samples * num_channels - full_pcm.size))

            audio_data_int16 = full_pcm[:target_samples * num_channels].reshape(-1, num_channels)
            audio_data_float32 = audio_data_int16.astype(np.float32) / 32768.0 # Normalize
            mix = audio_data_float32.T # (channels, samples)

        if f.samplerate != sample_rate:
            mix = librosa.resample(mix, orig_sr=f.samplerate, target_sr=sample_rate)
        return mix
    except Exception as e:
        print(f"Error in rerun_mp3_logic for {audio_file_path}: {e}")
        return np.array([[],[]], dtype=np.float32)


def save_format_logic(audio_path: str, save_format_val: str, mp3_bit_set_val: str): # Renamed
    """Converts WAV to other formats (FLAC, MP3) and removes original WAV."""
    if not Path(audio_path).exists():
        print(f"Error: {audio_path} does not exist for format conversion.")
        return
    try:
        musfile = pydub.AudioSegment.from_wav(audio_path)
        if save_format_val == ac.FLAC:
            audio_path_flac = audio_path.replace(".wav", ".flac")
            musfile.export(audio_path_flac, format="flac")
        elif save_format_val == ac.MP3:
            audio_path_mp3 = audio_path.replace(".wav", ".mp3")
            # pydub might need ffmpeg in PATH or explicit converter path set globally
            musfile.export(audio_path_mp3, format="mp3", bitrate=mp3_bit_set_val) # Removed codec for broader compatibility
        
        # Only remove original if conversion was successful and format is not WAV
        if save_format_val != ac.WAV:
            os.remove(audio_path)
    except Exception as e:
        print(f"Error in save_format_logic for {audio_path} to {save_format_val}: {e}")

# Other helper functions like process_secondary_model_logic, vr_denoiser_logic etc. would go here,
# carefully adapted to use constants from ac and modules imported at the top.
