from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, Optional, Tuple, List
from pathlib import Path
import gc
import numpy as np
import torch
import os 
import time

from . import app_constants as ac
from .model_data import ModelData

try:
    from demucs.apply import apply_model as demucs_apply_model, demucs_segments
    from demucs.hdemucs import HDemucs
    from demucs.pretrained import get_model as demucs_get_model
    from demucs.utils import apply_model_v1 as demucs_apply_model_v1
    from demucs.utils import apply_model_v2 as demucs_apply_model_v2
except ImportError as e:
    print(f"Warning: Demucs modules not found: {e}")
    demucs_apply_model, demucs_segments, HDemucs, demucs_get_model, demucs_apply_model_v1, demucs_apply_model_v2 = [None]*6

try:
    from lib_v5.tfc_tdf_v3 import TFC_TDF_net, STFT as LibV5_STFT
    from lib_v5 import spec_utils
    from lib_v5.vr_network import nets as nets_vr
    from lib_v5.vr_network import nets_new as nets_new_vr
    from lib_v5.vr_network.model_param_init import ModelParameters
    from lib_v5 import mdxnet as MdxnetSet
except ImportError as e:
    print(f"Warning: lib_v5 modules not found: {e}")
    LibV5_STFT, TFC_TDF_net, spec_utils, nets_vr, nets_new_vr, ModelParameters, MdxnetSet = [None]*7

import audioread
import gzip
import librosa
import math
import soundfile as sf
import warnings

try:
    import onnxruntime as ort
    from onnx import load as onnx_load
    from onnx2pytorch import ConvertModel as onnx_ConvertModel
except ImportError:
    print("Warning: ONNX related modules not found.")
    ort, onnx_load, onnx_ConvertModel = None, None, None

try:
    import pydub
except ImportError:
    print("Warning: pydub not found.")
    pydub = None

MPS_AVAILABLE = torch.backends.mps.is_available() if ac.IS_MACOS else False
CUDA_AVAILABLE = torch.cuda.is_available()
CPU_DEVICE = torch.device('cpu')
warnings.filterwarnings("ignore")

def clear_gpu_cache_logic():
    gc.collect()
    if ac.IS_MACOS and MPS_AVAILABLE: torch.mps.empty_cache()
    elif CUDA_AVAILABLE: torch.cuda.empty_cache()

def prepare_mix_logic(audio_file_path_str: str) -> Optional[np.ndarray]:
    audio_file_path = Path(audio_file_path_str)
    mix_audio = None
    try:
        mix_audio, sr = librosa.load(str(audio_file_path), mono=False, sr=ac.DEFAULT_SAMPLE_RATE)
    except Exception as e:
        print(f"Librosa failed to load {audio_file_path}: {e}. Trying audioread.")
        try:
            with audioread.audio_open(str(audio_file_path)) as f: track_length = int(f.duration)
            mix_audio, sr = librosa.load(str(audio_file_path), duration=track_length, mono=False, sr=ac.DEFAULT_SAMPLE_RATE)
        except Exception as e2:
            print(f"Audioread also failed for {audio_file_path}: {e2}"); return None
    if mix_audio.ndim == 1: mix_audio = np.asfortranarray([mix_audio, mix_audio])
    return mix_audio.T

def write_audio_logic(stem_path_str: str, stem_source: np.ndarray, samplerate: int, 
                      model_data: ModelData, stem_name: Optional[str] = None, 
                      process_data: Optional[Dict]=None):
    stem_path = Path(stem_path_str)
    
    # Check if stem_source is empty or too small
    if stem_source.size == 0 or (stem_source.ndim > 1 and stem_source.shape[1] == 0):
        print(f"DEBUG: {stem_name} is empty (shape {stem_source.shape}). Generating silent output of original length.")
        
        # Get the original audio file to determine the length for silent output
        if process_data and 'input_audio_array' in process_data:
            original_audio = process_data['input_audio_array']
            # Create silent output with same length as original audio
            if original_audio is not None:
                if stem_source.ndim == 1:
                    stem_source = np.zeros_like(original_audio)
                else:
                    # For stereo, create appropriate shape
                    if original_audio.ndim == 1:
                        # Original is mono, create stereo silent output
                        stem_source = np.zeros((2, len(original_audio)))
                    else:
                        # Original is stereo, match its shape
                        stem_source = np.zeros_like(original_audio)
        else:
            # If we don't have the original audio, create a short silent output
            if stem_source.ndim == 1:
                stem_source = np.zeros(samplerate * 3)  # 3 seconds of silence
            else:
                stem_source = np.zeros((2, samplerate * 3))  # 3 seconds of stereo silence
    
    # Ensure correct shape
    if stem_source.ndim == 1: 
        stem_source = np.asfortranarray([stem_source, stem_source]).T
    elif stem_source.shape[0] < stem_source.shape[1]: 
        stem_source = stem_source.T

    # Check for NaN/Inf values
    if np.isnan(np.sum(stem_source)):
        print(f"DEBUG: {stem_name} contains NaN values. Fixing...")
        stem_source = np.nan_to_num(stem_source, nan=0.0)
    if np.isinf(np.sum(stem_source)):
        print(f"DEBUG: {stem_name} contains Inf values. Fixing...")
        stem_source = np.nan_to_num(stem_source, posinf=1.0, neginf=-1.0)

    if model_data.is_normalization and spec_utils: 
        stem_source = spec_utils.normalize(stem_source, True)
    
    # Map wav_type_set to valid soundfile subtypes
    subtype_map = {
        'PCM_16': 'PCM_16',
        'PCM_24': 'PCM_24',
        'PCM_32': 'PCM_32',
        'FLOAT': 'FLOAT',
        'DOUBLE': 'DOUBLE'
    }
    subtype = subtype_map.get(model_data.wav_type_set, 'PCM_16')
    
    # Debugging prints
    print(f"DEBUG: Attempting to write audio to: {stem_path}")
    print(f"DEBUG: Samplerate: {samplerate}")
    print(f"DEBUG: model_data.wav_type_set: {model_data.wav_type_set}")
    print(f"DEBUG: Determined subtype for sf.write: {subtype}")
    print(f"DEBUG: stem_source.dtype: {stem_source.dtype}")
    print(f"DEBUG: stem_source.shape: {stem_source.shape}")

    try:
        sf.write(str(stem_path), stem_source, samplerate, subtype=subtype)
    except Exception as e_sf_write:
        print(f"ERROR during sf.write: {e_sf_write}")
        print(f"  stem_path: {stem_path}")
        print(f"  samplerate: {samplerate}")
        print(f"  subtype: {subtype}")
        print(f"  stem_source.dtype: {stem_source.dtype}")
        print(f"  stem_source.shape: {stem_source.shape}")
        # Instead of raising, try to write a silent file as fallback
        try:
            silent_output = np.zeros((samplerate * 3, 2))  # 3 seconds of stereo silence
            sf.write(str(stem_path), silent_output, samplerate, subtype=subtype)
            print(f"Wrote silent fallback file to {stem_path}")
        except Exception as e_fallback:
            print(f"Failed to write fallback silent file: {e_fallback}")

    console_logger = process_data.get('write_to_console') if process_data else None
    base_text_console = process_data.get('base_text_console', "") if process_data else ""
    if console_logger: console_logger(f"{ac.SAVING_STEM_MESSAGE[0]}{stem_name or 'stem'}{ac.SAVING_STEM_MESSAGE[1]}", base_text=base_text_console)

    if model_data.save_format != ac.WAV:
        if pydub:
            try:
                audio_segment = pydub.AudioSegment.from_wav(str(stem_path))
                target_format_path = stem_path.with_suffix(f".{model_data.save_format.lower()}")
                if model_data.save_format == ac.FLAC: audio_segment.export(str(target_format_path), format="flac")
                elif model_data.save_format == ac.MP3: audio_segment.export(str(target_format_path), format="mp3", bitrate=model_data.mp3_bit_set)
                if target_format_path.exists():
                    try: stem_path.unlink()
                    except OSError: pass
            except Exception as e:
                print(f"Error converting {stem_path} to {model_data.save_format}: {e}")
                if console_logger: console_logger(f"Warning: Could not convert to {model_data.save_format}, WAV saved.", base_text=base_text_console)
        elif console_logger: console_logger(f"Warning: pydub not found. Cannot convert to {model_data.save_format}. WAV saved.", base_text=base_text_console)
    if console_logger: console_logger(ac.DONE_MESSAGE, base_text="")

class SeparatorAttributesLogic:
    def __init__(self, model_data: ModelData, process_data: Dict[str, Any]):
        self.md: ModelData = model_data 
        self.process_data: Dict[str,Any] = process_data
        
        self.set_progress_bar = process_data.get('set_progress_bar', lambda b, a=0: None)
        self.write_to_console = process_data.get('write_to_console', lambda m, b="": None)
        self.base_text_console = process_data.get('base_text_console', "")
        self.process_iteration_callback = process_data.get('process_iteration', lambda: None)
        self._is_running_check = process_data.get('_is_running_check', lambda: True)

        self.audio_file_path = Path(model_data.audio_file) if model_data.audio_file else None
        self.export_path = Path(model_data.export_path) if model_data.export_path else None
        self.audio_file_base = self.audio_file_path.stem if self.audio_file_path else "output"
        
        self.device = CPU_DEVICE
        if model_data.is_gpu_conversion:
            if MPS_AVAILABLE: self.device = torch.device('mps')
            elif CUDA_AVAILABLE: self.device = torch.device(f'cuda:{model_data.device_set}' if model_data.device_set != ac.DEFAULT else 'cuda')
        self.run_type = [ac.CPU_EXECUTION_PROVIDER]
        if self.device.type == 'cuda': self.run_type = [ac.CUDA_EXECUTION_PROVIDER]

        self.progress_value = 0 
        self.primary_source_map: Dict[str, np.ndarray] = {}
        self.secondary_source_map: Dict[str, np.ndarray] = {}
        self.primary_source: Optional[np.ndarray] = None
        self.secondary_source: Optional[np.ndarray] = None
        self.secondary_source_primary: Optional[np.ndarray] = None 
        self.secondary_source_secondary: Optional[np.ndarray] = None 
        self.cached_source_callback = process_data.get('cached_source_callback', lambda pm, mn: (None,None))
        self.cached_model_source_holder = process_data.get('cached_model_source_holder', lambda pm, s, mn: None)
        self.list_all_models = process_data.get('list_all_models', [])
        
        self.input_high_end_h: Optional[int] = None
        self.input_high_end: Optional[np.ndarray] = None
        self.model_run_instance = None 

    def _console_log_base(self, message: str): self.write_to_console(message, base_text=self.base_text_console)
    def _console_log(self, message: str): self.write_to_console(message, base_text="")
    def _update_progress(self, current_step_fraction: float, message: Optional[str] = None):
        scaled_progress = 0.1 + (current_step_fraction * 0.8)
        self.set_progress_bar(scaled_progress)
        if message: self._console_log_base(message)

    def _prepare_mix(self) -> Optional[np.ndarray]:
        input_audio_array = self.process_data.get('input_audio_array')
        
        if input_audio_array is not None:
            self._console_log_base(f"Using provided audio array for {self.md.model_basename}...")
            # Ensure it's (length, channels)
            if input_audio_array.shape[0] < input_audio_array.shape[1] and input_audio_array.ndim == 2: # (channels, length)
                return input_audio_array.T
            return input_audio_array # Already (length, channels) or mono
            
        elif self.audio_file_path:
            self._console_log_base(f"Loading audio file: {self.audio_file_path.name} for {self.md.model_basename}...")
            mix_audio = prepare_mix_logic(str(self.audio_file_path)) 
            if mix_audio is None: 
                self._console_log_base(f"Error: Failed to load audio from {self.audio_file_path}")
                return None
            self._console_log(ac.DONE_MESSAGE)
            return mix_audio # (length, channels)
        else:
            self._console_log_base(f"Error: No audio input (file or array) for {self.md.model_basename}.")
            return None

    def _write_stem(self, stem_name: str, stem_data: np.ndarray, samplerate: int):
        if not self.export_path: self._console_log_base("Error: Export path not set."); return
        
        # Ensure the export directory exists
        self.export_path.mkdir(parents=True, exist_ok=True)
        
        filename_parts = [self.audio_file_base, f"({stem_name})"]
        stem_filename = "_".join(filter(None, filename_parts)) + f".{self.md.save_format.lower()}"
        stem_save_path = str(self.export_path / stem_filename)
        write_audio_logic(stem_save_path, stem_data, samplerate, self.md, stem_name, self.process_data)

    def _pitch_fix(self, source_audio: np.ndarray, sr_pitched: int, org_mix_shape_ref: np.ndarray) -> np.ndarray:
        if not spec_utils: return source_audio
        if source_audio.shape[0] > source_audio.shape[1]: source_audio = source_audio.T
        changed_pitch_audio = spec_utils.change_pitch_semitones(source_audio, sr_pitched, semitone_shift=self.md.semitone_shift)[0]
        if org_mix_shape_ref.shape[0] > org_mix_shape_ref.shape[1]: org_mix_shape_ref = org_mix_shape_ref.T
        return spec_utils.match_array_shapes(changed_pitch_audio, org_mix_shape_ref)

    def _final_process_stem(self, stem_path_str: str, source_data: np.ndarray, 
                         secondary_model_output: Optional[np.ndarray],
                         stem_name: str, samplerate: int) -> Dict[str, np.ndarray]:
        self._write_stem(stem_name, source_data, samplerate)
        return {stem_name: source_data}

    def seperate(self) -> Optional[Dict[str, np.ndarray]]: raise NotImplementedError

class SeperateMDXLogic(SeparatorAttributesLogic):
    def __init__(self, model_data: ModelData, process_data: Dict[str, Any]):
        super().__init__(model_data, process_data)
        self.stft_tool = None 
        self.n_bins = 0; self.trim = 0; self.chunk_size = 0; self.gen_size = 0; self.hop_length = 1024
        self.is_onnx_model = False

    def _initialize_model_settings(self):
        md = self.md
        self.hop_length = 1024 
        if md.is_mdx_ckpt: 
            if md.mdx_c_configs and isinstance(md.mdx_c_configs, dict):
                 self.hop_length = md.mdx_c_configs.get('hop_length', self.hop_length)
        
        if md.mdx_n_fft_scale_set is None or md.mdx_dim_f_set is None:
            raise ValueError("MDX FFT scale or Dim F not set in ModelData for MDX model.")

        self.n_bins = md.mdx_n_fft_scale_set // 2 + 1
        self.trim = md.mdx_n_fft_scale_set // 2
        self.chunk_size = self.hop_length * (md.mdx_segment_size - 1)
        self.gen_size = self.chunk_size - 2 * self.trim
        
        if not LibV5_STFT: raise ImportError("LibV5_STFT not available.")
        self.stft_tool = LibV5_STFT(md.mdx_n_fft_scale_set, self.hop_length, md.mdx_dim_f_set, self.device)

    def _run_model_onnx_pytorch(self, mix_part_torch: torch.Tensor, is_match_freq_cut: bool) -> np.ndarray:
        md = self.md
        adjust = 1.0 
        
        spec = self.stft_tool(mix_part_torch) * adjust
        spec[:, :, :3, :] *= 0 

        if is_match_freq_cut: return spec.cpu().detach().numpy() 
        
        if md.is_mdx_ckpt: 
            spec_pred = self.model_run_instance(spec)
        elif self.is_onnx_model:
            if md.mdx_segment_size == md.mdx_dim_t_set and not (self.device.type == 'mps'):
                # For ONNX Runtime inference
                input_name = self.model_run_instance.get_inputs()[0].name
                output_name = self.model_run_instance.get_outputs()[0].name
                spec_cpu = spec.cpu().numpy()
                spec_pred_np = self.model_run_instance.run([output_name], {input_name: spec_cpu})[0]
                spec_pred = torch.tensor(spec_pred_np).to(self.device)
            else: 
                # For PyTorch converted ONNX model
                spec_pred = self.model_run_instance(spec)
        else: 
            raise ValueError("MDX model type not recognized for running.")

        if not is_match_freq_cut and md.denoise_option != ac.DENOISE_NONE:
             spec_pred = -self.model_run_instance(-spec) * 0.5 + self.model_run_instance(spec) * 0.5
        
        return self.stft_tool.inverse(spec_pred).cpu().detach().numpy()

    def _demix_mdx(self, mix_processed_norm_np: np.ndarray) -> Optional[np.ndarray]: 
        try:
            self._initialize_model_settings()
        except Exception as e:
            self._console_log_base(f"Error initializing MDX settings: {e}"); return None
            
        md = self.md
        org_mix_shape_ref = mix_processed_norm_np.T 
        
        actual_sr_pitched = ac.DEFAULT_SAMPLE_RATE
        if md.is_pitch_change:
            if not spec_utils: self._console_log_base("Error: spec_utils not available for pitch change."); return None
            mix_processed_norm_np, actual_sr_pitched = spec_utils.change_pitch_semitones(
                mix_processed_norm_np, ac.DEFAULT_SAMPLE_RATE, semitone_shift=-md.semitone_shift)
        
        pad_amount = self.gen_size + self.trim - ((mix_processed_norm_np.shape[1]) % self.gen_size)
        mixture_padded_np = np.concatenate(
            (np.zeros((2, self.trim), dtype='float32'), mix_processed_norm_np, np.zeros((2, pad_amount), dtype='float32')), axis=1)

        overlap_val = md.overlap_mdx if isinstance(md.overlap_mdx, (int, float)) and md.overlap_mdx != ac.DEFAULT else 0.25
        step = int((1 - overlap_val) * self.chunk_size) if overlap_val != 0 else self.chunk_size
        
        result_buff = np.zeros((1, 2, mixture_padded_np.shape[1]), dtype=np.float32)
        divider_buff = np.zeros((1, 2, mixture_padded_np.shape[1]), dtype=np.float32)
        
        total_chunks = math.ceil(mixture_padded_np.shape[1] / step) if step > 0 else 1
        self.progress_value = 0

        for i in range(0, mixture_padded_np.shape[1], step):
            if not self._is_running_check(): raise InterruptedError("Processing stopped by user.")
            self.progress_value += 1
            self._update_progress(self.progress_value / total_chunks if total_chunks > 0 else 1.0)

            start_idx, end_idx = i, min(i + self.chunk_size, mixture_padded_np.shape[1])
            actual_chunk_size = end_idx - start_idx
            mix_chunk_np = mixture_padded_np[:, start_idx:end_idx]
            if actual_chunk_size < self.chunk_size:
                mix_chunk_np = np.concatenate((mix_chunk_np, np.zeros((2, self.chunk_size - actual_chunk_size), dtype='float32')), axis=1)

            mix_chunk_torch = torch.tensor(mix_chunk_np[None, ...]).float().to(self.device)
            
            with torch.no_grad(): processed_chunk_np = self._run_model_onnx_pytorch(mix_chunk_torch, is_match_freq_cut=False)
            
            window = np.hanning(actual_chunk_size); window = np.tile(window[None, :], (2, 1)) if overlap_val != 0 else None
            
            if window is not None:
                result_buff[0, :, start_idx:end_idx] += processed_chunk_np[0, :, :actual_chunk_size] * window
                divider_buff[0, :, start_idx:end_idx] += window
            else:
                result_buff[0, :, start_idx:end_idx] += processed_chunk_np[0, :, :actual_chunk_size]
                divider_buff[0, :, start_idx:end_idx] += 1
        
        divider_buff[divider_buff == 0] = 1.0
        processed_audio_np = result_buff / divider_buff
        processed_audio_np = processed_audio_np[0, :, self.trim : mixture_padded_np.shape[1]-self.trim-pad_amount]
        
        if md.is_pitch_change: processed_audio_np = self._pitch_fix(processed_audio_np, actual_sr_pitched, org_mix_shape_ref)
        if md.compensate is not None: processed_audio_np *= md.compensate
        if md.is_denoise_model and md.DENOISER_MODEL_PATH: 
            self._console_log("Denoising output...")
            processed_audio_np = vr_denoiser_logic(processed_audio_np, self.device, md.DENOISER_MODEL_PATH)

        return processed_audio_np.T

    def seperate(self) -> Optional[Dict[str, np.ndarray]]:
        if not MdxnetSet or not ort or not onnx_load or not onnx_ConvertModel:
            self._console_log_base("Error: MDX-Net or ONNX dependencies not available."); return None
        md = self.md; self.progress_value = 0
        mix_audio_norm_np = self._prepare_mix()
        if mix_audio_norm_np is None: return None
        self._console_log_base(f"Processing with {md.model_basename}...")
        
        if md.is_mdx_ckpt:
            if not MdxnetSet: self._console_log_base("Error: MdxnetSet (for .ckpt) not available."); return None
            self._console_log_base("Loading MDX CKPT model...")
            try:
                model_checkpoint = torch.load(md.model_path, map_location=lambda storage, loc: storage)
                hyper_parameters = model_checkpoint['hyper_parameters']
                md.mdx_c_configs = hyper_parameters 
                md.mdx_dim_f_set = hyper_parameters.get('dim_f', md.mdx_dim_f_set)
                md.mdx_n_fft_scale_set = hyper_parameters.get('n_fft', md.mdx_n_fft_scale_set)

                separator = MdxnetSet.ConvTDFNet(**hyper_parameters)
                self.model_run_instance = separator.load_from_checkpoint(md.model_path)
                self.model_run_instance.to(self.device).eval()
                self.is_onnx_model = False
            except Exception as e:
                self._console_log_base(f"Error loading MDX CKPT model: {e}"); return None
        else: # ONNX
            self.is_onnx_model = True
            if md.mdx_segment_size == md.mdx_dim_t_set and not (self.device.type == 'mps'):
                if not ort: self._console_log_base("Error: ONNX Runtime not available."); return None
                self.model_run_instance = ort.InferenceSession(md.model_path, providers=self.run_type)
            else:
                if not onnx_load or not onnx_ConvertModel: self._console_log_base("Error: ONNX conversion modules not available."); return None
                onnx_mdl = onnx_load(md.model_path)
                self.model_run_instance = onnx_ConvertModel(onnx_mdl); self.model_run_instance.to(self.device).eval()
        
        primary_stem_data = self._demix_mdx(mix_audio_norm_np.T)
        if primary_stem_data is None: return None
        self._console_log(ac.DONE_MESSAGE); outputs = {}

        if not md.is_primary_stem_only:
            if primary_stem_data.shape == mix_audio_norm_np.shape:
                 secondary_stem_data = mix_audio_norm_np - primary_stem_data
                 self.secondary_source = secondary_stem_data
                 self.secondary_source_map = self._final_process_stem( "", secondary_stem_data, self.secondary_source_secondary, md.secondary_stem, md.model_samplerate)
                 outputs.update(self.secondary_source_map)
            else: self._console_log_base(f"Warning: Shape mismatch for secondary stem {md.model_name}")
        if not md.is_secondary_stem_only:
            self.primary_source = primary_stem_data
            self.primary_source_map = self._final_process_stem("", primary_stem_data, self.secondary_source_primary, md.primary_stem, md.model_samplerate)
            outputs.update(self.primary_source_map)
        clear_gpu_cache_logic(); return outputs

class SeperateMDXCLogic(SeparatorAttributesLogic):
    def _demix_mdxc(self, mix_processed_norm_np: np.ndarray) -> Optional[Dict[str, np.ndarray] | np.ndarray]: # mix is (channels, length)
        md = self.md
        if not md.mdx_c_configs or not TFC_TDF_net:
            self._console_log_base("Error: MDX-C configs or TFC_TDF_net not available."); return None
        
        org_mix_shape_ref = mix_processed_norm_np.T # (length, channels) for pitch fix
        actual_sr_pitched = ac.DEFAULT_SAMPLE_RATE
        if md.is_pitch_change:
            if not spec_utils: self._console_log_base("Error: spec_utils not available for pitch change."); return None
            mix_processed_norm_np, actual_sr_pitched = spec_utils.change_pitch_semitones(
                mix_processed_norm_np, ac.DEFAULT_SAMPLE_RATE, semitone_shift=-md.semitone_shift)

        mix_tensor = torch.tensor(mix_processed_norm_np, dtype=torch.float32).to(self.device)

        try:
            num_target_instruments = self.model_run_instance.num_target_instruments
        except AttributeError: 
            num_target_instruments = self.model_run_instance.module.num_target_instruments
        
        segment_size = md.mdx_c_configs.inference.dim_t if md.is_mdx_c_seg_def else md.mdx_segment_size
        
        batch_size_mdxc = md.mdx_batch_size 
        chunk_size_mdxc = md.mdx_c_configs.audio.hop_length * (segment_size - 1)
        
        overlap_mdxc_float = float(md.overlap_mdx23) if md.overlap_mdx23 else 8.0 
        overlap_mdxc_int = int(overlap_mdxc_float)
        if overlap_mdxc_int == 0: overlap_mdxc_int = 1 

        hop_size = chunk_size_mdxc // overlap_mdxc_int
        
        mix_shape_len = mix_tensor.shape[1]
        pad_size = hop_size - (mix_shape_len - chunk_size_mdxc) % hop_size
        
        mix_tensor_padded = torch.cat([torch.zeros(2, chunk_size_mdxc - hop_size, device=self.device), 
                                       mix_tensor, 
                                       torch.zeros(2, pad_size + chunk_size_mdxc - hop_size, device=self.device)], dim=1)

        chunks = mix_tensor_padded.unfold(1, chunk_size_mdxc, hop_size).transpose(0, 1)
        batches = [chunks[i : i + batch_size_mdxc] for i in range(0, len(chunks), batch_size_mdxc)]
        
        estimated_sources_tensor = torch.zeros(num_target_instruments, *mix_tensor.shape, device=self.device) if num_target_instruments > 1 else torch.zeros_like(mix_tensor)
        
        self.progress_value = 0; total_batches = len(batches)

        with torch.no_grad():
            cnt = 0
            for batch_idx, batch_data in enumerate(batches):
                if not self._is_running_check(): raise InterruptedError("Processing stopped by user.")
                self.progress_value = batch_idx + 1
                self._update_progress(self.progress_value / total_batches if total_batches > 0 else 1.0)
                processed_batch = self.model_run_instance(batch_data)
                for source_idx_in_batch in range(processed_batch.shape[0]):
                    current_source_output = processed_batch[source_idx_in_batch] 
                    start_frame = cnt * hop_size; end_frame = start_frame + chunk_size_mdxc
                    if num_target_instruments > 1: estimated_sources_tensor[..., start_frame:end_frame] += current_source_output 
                    else: estimated_sources_tensor[..., start_frame:end_frame] += current_source_output[0]
                    cnt += 1

        final_sources_tensor = estimated_sources_tensor[..., chunk_size_mdxc - hop_size : -(pad_size + chunk_size_mdxc - hop_size)] / overlap_mdxc_int
        final_sources_np = final_sources_tensor.cpu().detach().numpy()
        del estimated_sources_tensor, chunks, batches, mix_tensor_padded, mix_tensor
        gc.collect()
        if CUDA_AVAILABLE:
            torch.cuda.empty_cache()

        if num_target_instruments > 1:
            result_dict = {}
            for i, stem_name in enumerate(md.mdx_model_stems):
                stem_audio = final_sources_np[i]
                if md.is_pitch_change: stem_audio = self._pitch_fix(stem_audio, actual_sr_pitched, org_mix_shape_ref)
                result_dict[stem_name] = stem_audio.T 
                if md.is_denoise_model and md.DENOISER_MODEL_PATH and stem_name == ac.VOCAL_STEM and ac.INST_STEM in result_dict:
                    self._console_log(f"Denoising {ac.VOCAL_STEM} (MDX-C)...")
                    denoised_vocals = vr_denoiser_logic(result_dict[ac.VOCAL_STEM].T, self.device, md.DENOISER_MODEL_PATH).T
                    if denoised_vocals.shape == org_mix_shape_ref.T.shape: result_dict[ac.INST_STEM] = (org_mix_shape_ref.T - denoised_vocals).T
                    result_dict[ac.VOCAL_STEM] = denoised_vocals.T
            return result_dict
        else: 
            stem_audio = final_sources_np 
            if md.is_pitch_change: stem_audio = self._pitch_fix(stem_audio, actual_sr_pitched, org_mix_shape_ref)
            return stem_audio.T

    def seperate(self) -> Optional[Dict[str, np.ndarray]]:
        if not TFC_TDF_net or not self.md.mdx_c_configs:
            self._console_log_base("Error: MDX-C dependencies (TFC_TDF_net/configs) not available."); return None
        md = self.md; self.progress_value = 0
        mix_audio_norm_np = self._prepare_mix()
        if mix_audio_norm_np is None: return None
        self._console_log_base(f"Processing with MDX-C model: {md.model_basename}...")
        try:
            self.model_run_instance = TFC_TDF_net(md.mdx_c_configs, device=self.device) 
            self.model_run_instance.load_state_dict(torch.load(md.model_path, map_location=CPU_DEVICE))
            self.model_run_instance.to(self.device).eval()
        except Exception as e: self._console_log_base(f"Error loading MDX-C model: {e}"); return None

        processed_output = self._demix_mdxc(mix_audio_norm_np.T) 
        if processed_output is None: return None
        self._console_log(ac.DONE_MESSAGE); outputs = {}

        if isinstance(processed_output, dict): 
            for stem_name, stem_data_np in processed_output.items():
                if md.mdxnet_stem_select == ac.ALL_STEMS or stem_name == md.mdxnet_stem_select:
                    current_stem_map = self._final_process_stem("", stem_data_np, None, stem_name, md.model_samplerate)
                    outputs.update(current_stem_map)
        else: 
            primary_stem_data = processed_output 
            if not md.is_secondary_stem_only:
                self.primary_source = primary_stem_data
                self.primary_source_map = self._final_process_stem("", primary_stem_data, self.secondary_source_primary, md.primary_stem, md.model_samplerate)
                outputs.update(self.primary_source_map)
            if not md.is_primary_stem_only: 
                if primary_stem_data.shape == mix_audio_norm_np.shape:
                    secondary_stem_data = mix_audio_norm_np - primary_stem_data
                    self.secondary_source = secondary_stem_data
                    self.secondary_source_map = self._final_process_stem("", secondary_stem_data, self.secondary_source_secondary, md.secondary_stem, md.model_samplerate)
                    outputs.update(self.secondary_source_map)
                else: self._console_log_base(f"Warning: Shape mismatch for MDX-C secondary stem {md.model_name}")
        clear_gpu_cache_logic(); return outputs
        
class SeperateDemucsLogic(SeparatorAttributesLogic):
    def _demix_demucs_logic(self, mix_processed_norm_np: np.ndarray) -> Optional[np.ndarray]:
        md = self.md

        # Debug the input audio shape
        self._console_log_base(f"DEBUG: Input audio shape: {mix_processed_norm_np.shape}")
        self._console_log_base(f"DEBUG: Input audio dtype: {mix_processed_norm_np.dtype}")
        self._console_log_base(f"DEBUG: Input audio min/max: {np.min(mix_processed_norm_np):.6f}/{np.max(mix_processed_norm_np):.6f}")
        self._console_log_base(f"DEBUG: Input audio contains NaN: {np.isnan(mix_processed_norm_np).any()}")
        self._console_log_base(f"DEBUG: Input audio contains Inf: {np.isinf(mix_processed_norm_np).any()}")

        # Ensure the audio is in the correct format (channels, samples)
        if mix_processed_norm_np.ndim == 1:
            mix_processed_norm_np = np.stack([mix_processed_norm_np, mix_processed_norm_np])
        elif mix_processed_norm_np.shape[0] > mix_processed_norm_np.shape[1]:
            mix_processed_norm_np = mix_processed_norm_np.T

        # Convert to tensor
        mix_tensor = torch.tensor(mix_processed_norm_np).float().to(self.device)
        self._console_log_base(f"Mix tensor shape: {mix_tensor.shape}")

        actual_sr_pitched = ac.DEFAULT_SAMPLE_RATE
        if md.is_pitch_change:
            if not spec_utils:
                self._console_log_base("Error: spec_utils not available for pitch change.")
                return None
            mix_tensor_np, actual_sr_pitched = spec_utils.change_pitch_semitones(mix_tensor.cpu().numpy(), ac.DEFAULT_SAMPLE_RATE, semitone_shift=-md.semitone_shift)
            mix_tensor = torch.tensor(mix_tensor_np).float().to(self.device)

        # Normalize
        ref_mean = mix_tensor.mean()
        ref_std = mix_tensor.std()
        self._console_log_base(f"DEBUG: Mix tensor mean: {ref_mean}, std: {ref_std}")
        if ref_std == 0:
            self._console_log_base("Warning: Standard deviation is zero. Using 1.0 instead.")
            ref_std = 1.0
        mix_tensor = (mix_tensor - ref_mean) / ref_std
        self._console_log_base(f"DEBUG: Normalized mix tensor min/max: {mix_tensor.min().item():.6f}/{mix_tensor.max().item():.6f}")

        processed_sources_tensor = None
        try:
            with torch.no_grad():
                if md.demucs_version == ac.DEMUCS_V1:
                    if not demucs_apply_model_v1:
                        self._console_log_base("Demucs v1 apply_model not available.")
                        return None
                    processed_sources_tensor = demucs_apply_model_v1(self.model_run_instance, mix_tensor, md.shifts, md.is_split_mode, set_progress_bar=lambda p: self._update_progress(p))
                elif md.demucs_version == ac.DEMUCS_V2:
                    if not demucs_apply_model_v2:
                        self._console_log_base("Demucs v2 apply_model not available.")
                        return None
                    processed_sources_tensor = demucs_apply_model_v2(self.model_run_instance, mix_tensor, md.shifts, md.is_split_mode, md.overlap, set_progress_bar=lambda p: self._update_progress(p))
                else:
                    if not demucs_apply_model:
                        self._console_log_base("Demucs apply_model not available.")
                        return None

                    # Ensure mix_tensor has the right shape for demucs_apply_model
                    # For Demucs v3/v4, the expected shape is [batch, channels, time]
                    if mix_tensor.dim() == 2:  # [channels, time]
                        mix_tensor_input = mix_tensor.unsqueeze(0)  # Add batch dimension
                    else:
                        mix_tensor_input = mix_tensor

                    self._console_log_base(f"Input tensor shape to apply_model: {mix_tensor_input.shape}")

                    # Call apply_model with proper progress callback
                    try:
                        self._console_log_base(f"DEBUG: Calling demucs_apply_model with shifts={md.shifts}, split_mode={md.is_split_mode}, overlap={md.overlap}")
                        self._console_log_base(f"DEBUG: Model instance type: {type(self.model_run_instance).__name__}")
                        
                        print(f"DEBUG: About to call demucs_apply_model with:")
                        print(f"DEBUG:   - model: {type(self.model_run_instance).__name__}")
                        print(f"DEBUG:   - mix_tensor_input shape: {mix_tensor_input.shape}")
                        print(f"DEBUG:   - shifts: {md.shifts}")
                        print(f"DEBUG:   - split_mode: {md.is_split_mode}")
                        print(f"DEBUG:   - overlap: {md.overlap}")
                        print(f"DEBUG:   - static_shifts: {1 if md.shifts == 0 else md.shifts}")
                        print(f"DEBUG:   - device: {self.device}")
                        
                        processed_sources_tensor = demucs_apply_model(
                            self.model_run_instance,
                            mix_tensor_input,
                            md.shifts,
                            md.is_split_mode,
                            md.overlap,
                            static_shifts=1 if md.shifts == 0 else md.shifts,
                            set_progress_bar=lambda p, t: self._update_progress(p/t if t > 0 else p),
                            device=self.device
                        )
                        
                        print(f"DEBUG: demucs_apply_model completed successfully")
                        if processed_sources_tensor is not None:
                            print(f"DEBUG: processed_sources_tensor shape: {processed_sources_tensor.shape}")
                        else:
                            print(f"DEBUG: processed_sources_tensor is None")
                    except Exception as e:
                        self._console_log_base(f"Error during Demucs apply_model: {e}")
                        import traceback
                        self._console_log_base(traceback.format_exc())
                        
                        # Check if model file exists and is valid
                        if hasattr(self.model_run_instance, 'sources'):
                            self._console_log_base(f"Model sources before error: {self.model_run_instance.sources}")
                        
                        # Check input tensor for issues
                        self._console_log_base(f"Input tensor shape: {mix_tensor_input.shape}")
                        self._console_log_base(f"Input tensor device: {mix_tensor_input.device}")
                        self._console_log_base(f"Input tensor dtype: {mix_tensor_input.dtype}")
                        self._console_log_base(f"Input tensor contains NaN: {torch.isnan(mix_tensor_input).any().item()}")
                        self._console_log_base(f"Input tensor contains Inf: {torch.isinf(mix_tensor_input).any().item()}")
                        
                        # Create a fallback output with the right shape
                        self._console_log_base("Creating fallback output...")
                        # Determine the expected output shape based on the model
                        if hasattr(self.model_run_instance, 'sources'):
                            num_sources = len(self.model_run_instance.sources)
                        else:
                            num_sources = 4  # Default to 4 sources (drums, bass, other, vocals)
                        
                        # Create a tensor of zeros with the right shape
                        if mix_tensor_input.dim() == 3:  # [batch, channels, time]
                            processed_sources_tensor = torch.zeros(
                                (mix_tensor_input.shape[0], num_sources, mix_tensor_input.shape[1], mix_tensor_input.shape[2]),
                                device=self.device
                            )
                        else:  # [channels, time]
                            processed_sources_tensor = torch.zeros(
                                (num_sources, mix_tensor_input.shape[0], mix_tensor_input.shape[1]),
                                device=self.device
                            )

                        # For Demucs v3/v4, the output shape should be [batch, sources, channels, time]
                        # We need to extract the first batch item
                        if processed_sources_tensor is not None:
                            print(f"DEBUG: processed_sources_tensor shape before batch extraction: {processed_sources_tensor.shape}")
                            print(f"DEBUG: processed_sources_tensor type: {type(processed_sources_tensor)}")
                            print(f"DEBUG: processed_sources_tensor device: {processed_sources_tensor.device}")
                            
                            if len(processed_sources_tensor.shape) == 4:  # [batch, sources, channels, time]
                                processed_sources_tensor = processed_sources_tensor[0]  # Remove batch dimension
                                print(f"DEBUG: Removed batch dimension, new shape: {processed_sources_tensor.shape}")
                            elif len(processed_sources_tensor.shape) == 3:  # [sources, channels, time]
                                # Already in the right format
                                print(f"DEBUG: Already in correct format [sources, channels, time]")
                            else:
                                self._console_log_base(f"Unexpected output shape from Demucs: {processed_sources_tensor.shape}")
                                print(f"DEBUG: Unexpected output shape from Demucs: {processed_sources_tensor.shape}")
                                return None
        except Exception as e:
            self._console_log_base(f"Error during Demucs processing: {e}")
            import traceback
            self._console_log_base(traceback.format_exc())
            return None

        if processed_sources_tensor is None:
            self._console_log_base("No output from Demucs model.")
            return None

        self._console_log_base(f"Processed sources tensor shape: {processed_sources_tensor.shape}")

        # Denormalize
        try:
            self._console_log_base(f"Denormalizing processed sources tensor")
            
            # Move to CPU before numpy conversion
            processed_sources_tensor_cpu = processed_sources_tensor.cpu()
            
            # Denormalize
            denormalized_tensor = processed_sources_tensor_cpu * ref_std + ref_mean
            
            # Convert to numpy
            sources_np = denormalized_tensor.numpy()
            
            self._console_log_base(f"Sources numpy shape: {sources_np.shape}")
            
            # Handle batch dimension if present
            if len(sources_np.shape) == 4:  # [batch, sources, channels, time]
                self._console_log_base(f"Removing batch dimension from sources")
                sources_np = sources_np[0]  # Remove batch dimension
            
            # Check for NaN/Inf values
            if np.isnan(sources_np).any():
                self._console_log_base(f"Warning: Sources contain NaN values. Fixing...")
                sources_np = np.nan_to_num(sources_np, nan=0.0)
            if np.isinf(sources_np).any():
                self._console_log_base(f"Warning: Sources contain Inf values. Fixing...")
                sources_np = np.nan_to_num(sources_np, posinf=1.0, neginf=-1.0)
                
            # Swap sources[0] and sources[1] - this is critical for Demucs
            # In the original separate.py, this is done with: sources_np[[0,1]] = sources_np[[1,0]]
            self._console_log_base(f"Swapping sources[0] and sources[1] for Demucs")
            if sources_np.shape[0] >= 2:
                sources_np[[0,1]] = sources_np[[1,0]]
        except Exception as e:
            self._console_log_base(f"ERROR during denormalization: {e}")
            import traceback
            self._console_log_base(f"Traceback: {traceback.format_exc()}")
            
            # Create fallback output with appropriate shape
            self._console_log_base(f"Creating fallback output with appropriate shape")
            if mix_processed_norm_np.ndim == 1:
                sources_np = np.zeros((4, 1, len(mix_processed_norm_np)))  # 4 stems, 1 channel, original length
            else:
                sources_np = np.zeros((4, 2, mix_processed_norm_np.shape[0]))  # 4 stems, 2 channels, original length

        if md.is_pitch_change:
            try:
                final_sources = [self._pitch_fix(sources_np[i], actual_sr_pitched, mix_processed_norm_np).T for i in range(sources_np.shape[0])]
                sources_np = np.array(final_sources)
            except Exception as e:
                self._console_log_base(f"Error during pitch fix: {e}")

        return sources_np

    def seperate(self) -> Optional[Dict[str, np.ndarray]]:
        md = self.md
        self.progress_value = 0
        self._console_log_base(f"Processing with Demucs model: {md.model_basename}...")
        print(f"DEBUG: Starting Demucs separation with model: {md.model_basename}")
        print(f"DEBUG: Model path: {md.model_path}")
        print(f"DEBUG: Demucs version: {md.demucs_version}")
        print(f"DEBUG: Demucs stems: {md.demucs_stems}")
        print(f"DEBUG: Demucs source list: {md.demucs_source_list}")
        print(f"DEBUG: Demucs source map: {md.demucs_source_map}")
        
        # Check if we have the necessary Demucs modules
        if md.demucs_version not in [ac.DEMUCS_V1, ac.DEMUCS_V2] and (not demucs_get_model or not demucs_segments):
            self._console_log_base("Demucs modules not available. Please install Demucs.")
            return None
            
        try:
            if md.demucs_version == ac.DEMUCS_V1:
                if not os.path.exists(md.model_path) or os.path.getsize(md.model_path) == 0:
                    self._console_log_base(f"Error: Demucs model file not found or empty: {md.model_path}")
                    return None
                    
                model_file = gzip.open(md.model_path, "rb") if str(md.model_path).endswith(".gz") else md.model_path
                klass, args, kwargs, state = torch.load(model_file, map_location=CPU_DEVICE)
                self.model_run_instance = klass(*args, **kwargs)
                self.model_run_instance.load_state_dict(state)
            elif md.demucs_version == ac.DEMUCS_V2:
                if not os.path.exists(md.model_path) or os.path.getsize(md.model_path) == 0:
                    self._console_log_base(f"Error: Demucs v2 model file not found or empty: {md.model_path}")
                    return None
                    
                self._console_log_base("Loading Demucs v2 model...")
                # Implement specific v2 loading if needed
                self._console_log_base("Demucs v2 model loading needs specific implementation.")
                return None
            else:
                # For v3 and v4 models
                model_dir = Path(os.path.dirname(md.model_path))
                model_file = Path(md.model_path)
                model_name = os.path.splitext(os.path.basename(md.model_path))[0]
                self._console_log_base(f"Loading Demucs v3/v4 model: {model_name} from {model_dir}")
                
                # Check if this is a YAML file (bag of models)
                if model_file.suffix.lower() == '.yaml':
                    self._console_log_base(f"Loading Demucs bag of models from YAML: {model_file}")
                    
                    # Check if the YAML file exists
                    if not model_file.exists() or model_file.stat().st_size == 0:
                        self._console_log_base(f"Error: YAML file not found or empty: {model_file}")
                        return None
                    
                    try:
                        # Read the YAML file to get model IDs
                        import yaml
                        print(f"DEBUG: Opening YAML file: {model_file}")
                        with open(model_file, 'r') as f:
                            yaml_content = f.read()
                            print(f"DEBUG: YAML content: {yaml_content[:500]}...")  # Print first 500 chars
                            yaml_data = yaml.safe_load(yaml_content)
                        
                        print(f"DEBUG: YAML data keys: {yaml_data.keys() if yaml_data else 'None'}")
                        model_ids = yaml_data.get('models', [])
                        self._console_log_base(f"Found model IDs in YAML: {model_ids}")
                        print(f"DEBUG: Found model IDs in YAML: {model_ids}")
                        
                        # Check if all referenced model files exist
                        missing_models = []
                        for model_id in model_ids:
                            # Look for files that start with the model ID
                            found = False
                            for file in model_dir.glob(f"{model_id}*.th"):
                                if file.exists() and file.stat().st_size > 0:
                                    found = True
                                    break
                            if not found:
                                missing_models.append(model_id)
                        
                        if missing_models:
                            self._console_log_base(f"Warning: Some model files referenced in YAML are missing: {missing_models}")
                    except Exception as e:
                        self._console_log_base(f"Error parsing YAML file: {e}")
                        import traceback
                        self._console_log_base(traceback.format_exc())
                
                # Try to load the model
                try:
                    self._console_log_base(f"DEBUG: Attempting to load model from path: {md.model_path}")
                    print(f"DEBUG: Attempting to load model from path: {md.model_path}")
                    print(f"DEBUG: Model file exists: {os.path.exists(md.model_path)}")
                    print(f"DEBUG: Model file size: {os.path.getsize(md.model_path) if os.path.exists(md.model_path) else 'N/A'}")
                    if not os.path.exists(md.model_path):
                        self._console_log_base(f"ERROR: Demucs model file not found: {md.model_path}")
                        # List files in the directory to help diagnose
                        model_dir = os.path.dirname(md.model_path)
                        if os.path.exists(model_dir):
                            self._console_log_base(f"DEBUG: Files in model directory {model_dir}:")
                            for file in os.listdir(model_dir):
                                self._console_log_base(f"  - {file}")
                        else:
                            self._console_log_base(f"ERROR: Model directory does not exist: {model_dir}")
                        
                        # Try to use a pre-trained model from the demucs library
                        self._console_log_base("Attempting to use pre-trained model from demucs library...")
                        model_name = "htdemucs"  # Default to htdemucs if available
                        self.model_run_instance = demucs_get_model(name=model_name)
                        self._console_log_base(f"Successfully loaded pre-trained model: {model_name}")
                    elif os.path.getsize(md.model_path) == 0:
                        self._console_log_base(f"ERROR: Demucs model file is empty: {md.model_path}")
                        # Try to use a pre-trained model from the demucs library
                        self._console_log_base("Attempting to use pre-trained model from demucs library...")
                        model_name = "htdemucs"  # Default to htdemucs if available
                        self.model_run_instance = demucs_get_model(name=model_name)
                        self._console_log_base(f"Successfully loaded pre-trained model: {model_name}")
                    else:
                        # Check if this is a hash-based model file (like 92cfc3b6-ef3bcb9c.th)
                        model_path = Path(md.model_path)
                        print(f"DEBUG: Model path: {model_path}")
                        print(f"DEBUG: Model suffix: {model_path.suffix.lower()}")
                        print(f"DEBUG: Model stem: {model_path.stem}")
                        print(f"DEBUG: Is hash-based model: {model_path.suffix.lower() == '.th' and '-' in model_path.stem}")
                        
                        if model_path.suffix.lower() == '.th' and '-' in model_path.stem:
                            # This is likely a hash-based model file
                            self._console_log_base(f"Loading model from file: {model_path}")
                            print(f"DEBUG: Loading hash-based model file: {model_path}")
                            try:
                                # Try to load directly as a torch model
                                print(f"DEBUG: Attempting to load torch model from: {model_path}")
                                
                                # Import necessary modules
                                import torch
                                import importlib
                                import sys
                                
                                # Check if we have the required dependencies
                                try:
                                    import einops
                                    print(f"DEBUG: einops is available")
                                except ImportError:
                                    print(f"DEBUG: einops is not available - installing...")
                                    try:
                                        # Try to install einops
                                        import subprocess
                                        subprocess.check_call([sys.executable, "-m", "pip", "install", "einops"])
                                        print(f"DEBUG: einops installed successfully")
                                        import einops
                                    except Exception as e:
                                        print(f"DEBUG: Failed to install einops: {e}")
                                
                                # Try different approaches to load the model
                                try:
                                    # First try with weights_only=False (less secure but compatible with older code)
                                    print(f"DEBUG: Trying to load with weights_only=False")
                                    model_data = torch.load(model_path, map_location=CPU_DEVICE, weights_only=False)
                                    print(f"DEBUG: Successfully loaded model with weights_only=False")
                                except Exception as load_err:
                                    print(f"DEBUG: Error loading with weights_only=False: {load_err}")
                                    
                                    # Try to dynamically import and add safe globals for Demucs classes
                                    try:
                                        print(f"DEBUG: Trying to add safe globals")
                                        
                                        # Try to import the modules first
                                        try:
                                            from demucs.htdemucs import HTDemucs
                                            print(f"DEBUG: Successfully imported HTDemucs")
                                            torch.serialization.add_safe_globals([HTDemucs])
                                            print(f"DEBUG: Added HTDemucs to safe globals")
                                        except Exception as e:
                                            print(f"DEBUG: Could not import HTDemucs: {e}")
                                            
                                        try:
                                            from demucs.hdemucs import HDemucs
                                            print(f"DEBUG: Successfully imported HDemucs")
                                            torch.serialization.add_safe_globals([HDemucs])
                                            print(f"DEBUG: Added HDemucs to safe globals")
                                        except Exception as e:
                                            print(f"DEBUG: Could not import HDemucs: {e}")
                                        
                                        # Try loading again with default settings
                                        print(f"DEBUG: Trying to load model after adding safe globals")
                                        model_data = torch.load(model_path, map_location=CPU_DEVICE)
                                        print(f"DEBUG: Successfully loaded model after adding safe globals")
                                    except Exception as safe_err:
                                        print(f"DEBUG: Error with safe globals approach: {safe_err}")
                                        # Last resort: try to use a pre-trained model
                                        raise
                                
                                print(f"DEBUG: Model data type: {type(model_data)}")
                                print(f"DEBUG: Model data keys: {model_data.keys() if isinstance(model_data, dict) else 'Not a dict'}")
                                
                                if isinstance(model_data, dict):
                                    if 'state_dict' in model_data:
                                        # This is a state dict
                                        self._console_log_base("Loading model from state dict...")
                                        print(f"DEBUG: Loading model from state dict, state_dict keys: {list(model_data['state_dict'].keys())[:5]}...")
                                        from demucs.hdemucs import HDemucs
                                        self.model_run_instance = HDemucs(sources=["drums", "bass", "other", "vocals"])
                                        self.model_run_instance.load_state_dict(model_data['state_dict'])
                                        self._console_log_base("Successfully loaded model from state dict")
                                    elif 'klass' in model_data and 'args' in model_data and 'kwargs' in model_data and 'state' in model_data:
                                        # This is a Demucs v1 style model
                                        self._console_log_base("Loading Demucs model from klass/args/kwargs/state...")
                                        print(f"DEBUG: Loading Demucs model from klass/args/kwargs/state format")
                                        try:
                                            klass = model_data['klass']
                                            args = model_data['args']
                                            kwargs = model_data['kwargs']
                                            state = model_data['state']
                                            
                                            # Initialize the model with the class and arguments
                                            print(f"DEBUG: Initializing model with klass={klass}, args={args}, kwargs={kwargs}")
                                            self.model_run_instance = klass(*args, **kwargs)
                                            
                                            # Load the state dict
                                            print(f"DEBUG: Loading state dict")
                                            self.model_run_instance.load_state_dict(state)
                                            self._console_log_base("Successfully loaded model from klass/args/kwargs/state")
                                        except Exception as e:
                                            self._console_log_base(f"Error initializing model from klass/args/kwargs/state: {e}")
                                            print(f"DEBUG: Error initializing model: {e}")
                                            import traceback
                                            print(f"DEBUG: Traceback: {traceback.format_exc()}")
                                            # Fall back to using a pre-trained model
                                            self._console_log_base("Falling back to pre-trained model...")
                                            self.model_run_instance = demucs_get_model(name="htdemucs")
                                    else:
                                        # Unknown dictionary format, try to use as is
                                        self._console_log_base("Unknown model dictionary format, attempting to use as is...")
                                        print(f"DEBUG: Unknown model dictionary format with keys: {list(model_data.keys())}")
                                        # Fall back to using a pre-trained model
                                        self._console_log_base("Falling back to pre-trained model...")
                                        self.model_run_instance = demucs_get_model(name="htdemucs")
                                else:
                                    # Try to load as a complete model
                                    self._console_log_base("Loading complete model...")
                                    self.model_run_instance = model_data
                                    self._console_log_base("Successfully loaded complete model")
                            except Exception as e:
                                self._console_log_base(f"Error loading model directly: {e}")
                                # Fall back to demucs_get_model
                                self._console_log_base("Falling back to demucs_get_model...")
                                model_name = model_path.stem
                                self.model_run_instance = demucs_get_model(name=model_name, repo=model_dir)
                        else:
                            # Load from file using demucs_get_model
                            self._console_log_base(f"Loading model {model_name} from {model_dir}...")
                            self.model_run_instance = demucs_get_model(name=model_name, repo=model_dir)
                            self._console_log_base(f"Successfully loaded model: {model_name}")
                except Exception as e:
                    self._console_log_base(f"Error loading Demucs model: {e}")
                    import traceback
                    self._console_log_base(traceback.format_exc())
                    return None
                
                # Apply segmentation if needed
                segment_val = None
                if md.segment != ac.DEFAULT:
                    try:
                        segment_val = int(md.segment)
                        self._console_log_base(f"Using segment size: {segment_val}")
                        print(f"DEBUG: Using segment size: {segment_val}")
                    except ValueError:
                        self._console_log_base(f"Warning: Invalid Demucs segment value '{md.segment}'.")
                        print(f"DEBUG: Invalid Demucs segment value '{md.segment}'.")
                
                # Check if demucs_source_list is properly set
                if hasattr(self.model_run_instance, 'sources'):
                    print(f"DEBUG: Model sources from model: {self.model_run_instance.sources}")
                    print(f"DEBUG: Model sources from md.demucs_source_list: {md.demucs_source_list}")
                    print(f"DEBUG: Model source map: {md.demucs_source_map}")
                    
                    # Check if there's a mismatch
                    if set(self.model_run_instance.sources) != set(md.demucs_source_list):
                        self._console_log_base(f"WARNING: Mismatch between model sources and demucs_source_list")
                        print(f"DEBUG: WARNING: Mismatch between model sources and demucs_source_list")
                        print(f"DEBUG: Model has: {self.model_run_instance.sources}")
                        print(f"DEBUG: Config has: {md.demucs_source_list}")
                
                if segment_val is not None:
                    try:
                        self._console_log_base(f"DEBUG: Applying segmentation with value: {segment_val}")
                        if not demucs_segments:
                            self._console_log_base("ERROR: demucs_segments function not available")
                        else:
                            self.model_run_instance = demucs_segments(segment_val, self.model_run_instance)
                            self._console_log_base("DEBUG: Successfully applied segmentation")
                    except Exception as e:
                        self._console_log_base(f"ERROR during segmentation: {e}")
                        import traceback
                        self._console_log_base(f"Traceback: {traceback.format_exc()}")
            
                # Move model to device and set to eval mode
                try:
                    self.model_run_instance.to(self.device).eval()
                    self._console_log_base(f"Model loaded and moved to {self.device}")
                    print(f"DEBUG: Model successfully moved to {self.device} and set to eval mode")
                except Exception as e:
                    self._console_log_base(f"Error moving model to device: {e}")
                    print(f"DEBUG: Error moving model to device: {e}")
                    import traceback
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
            
            # Debug model information
            if hasattr(self.model_run_instance, 'sources'):
                self._console_log_base(f"DEBUG: Model sources: {self.model_run_instance.sources}")
            if hasattr(self.model_run_instance, 'audio_channels'):
                self._console_log_base(f"DEBUG: Model audio_channels: {self.model_run_instance.audio_channels}")
            if hasattr(self.model_run_instance, 'samplerate'):
                self._console_log_base(f"DEBUG: Model samplerate: {self.model_run_instance.samplerate}")
            if hasattr(self.model_run_instance, 'segment'):
                self._console_log_base(f"DEBUG: Model segment: {self.model_run_instance.segment}")
            
        except Exception as e:
            self._console_log_base(f"Error loading Demucs model: {e}")
            import traceback
            self._console_log_base(traceback.format_exc())
            return None

        # Prepare the audio mix
        mix_audio_norm_np = self._prepare_mix()
        if mix_audio_norm_np is None:
            self._console_log_base("Failed to prepare audio mix.")
            return None
            
        # Process the audio
        self._console_log_base("Starting Demucs processing...")
        all_stems_output = self._demix_demucs_logic(mix_audio_norm_np)
        
        # If processing failed completely, create silent outputs
        if all_stems_output is None:
            self._console_log_base("Demucs processing failed. Creating silent outputs.")
            # Create silent outputs with the same shape as the input
            if mix_audio_norm_np.ndim == 1:
                # For mono input
                silent_output = np.zeros((4, 1, len(mix_audio_norm_np)))  # 4 stems, 1 channel, original length
            else:
                # For stereo input
                silent_output = np.zeros((4, 2, mix_audio_norm_np.shape[0]))  # 4 stems, 2 channels, original length
            all_stems_output = silent_output
        self._console_log(ac.DONE_MESSAGE); outputs = {}

        if md.demucs_stems == ac.ALL_STEMS:
            for stem_name, stem_idx in md.demucs_source_map.items():
                if stem_idx < all_stems_output.shape[0]:
                    stem_data = all_stems_output[stem_idx].T 
                    self._write_stem(stem_name, stem_data, md.model_samplerate); outputs[stem_name] = stem_data
            
            # If we need an instrumental stem (combination of non-vocal stems)
            if not md.is_primary_stem_only and md.secondary_stem == "instrumental" and "vocals" in md.demucs_source_map:
                self._console_log_base("Creating instrumental stem by combining non-vocal stems...")
                instrumental_data = np.zeros_like(mix_audio_norm_np)
                for stem_name, stem_idx in md.demucs_source_map.items():
                    if stem_name != "vocals" and stem_idx < all_stems_output.shape[0]:
                        instrumental_data += all_stems_output[stem_idx].T
                self._write_stem("instrumental", instrumental_data, md.model_samplerate)
                outputs["instrumental"] = instrumental_data
        else: 
            primary_stem_idx = md.demucs_source_map.get(md.primary_stem)
            if primary_stem_idx is not None and primary_stem_idx < all_stems_output.shape[0]:
                primary_data = all_stems_output[primary_stem_idx].T
                if not md.is_secondary_stem_only: self._write_stem(md.primary_stem, primary_data, md.model_samplerate); outputs[md.primary_stem] = primary_data
                if not md.is_primary_stem_only:
                    secondary_data = None
                    if md.secondary_stem == "instrumental" and md.primary_stem == "vocals":
                        # Create instrumental stem by combining all non-vocal stems
                        self._console_log_base("Creating instrumental stem by combining non-vocal stems...")
                        secondary_data = np.zeros_like(primary_data)
                        for s_name, s_idx in md.demucs_source_map.items():
                            if s_name != "vocals" and s_idx < all_stems_output.shape[0]:
                                secondary_data += all_stems_output[s_idx].T
                    elif md.is_demucs_combine_stems:
                        secondary_sum = np.zeros_like(primary_data)
                        for s_name, s_idx in md.demucs_source_map.items():
                            if s_name != md.primary_stem and s_idx < all_stems_output.shape[0]: 
                                secondary_sum += all_stems_output[s_idx].T
                        secondary_data = secondary_sum
                    else: 
                        secondary_data = mix_audio_norm_np - primary_data
                    
                    if secondary_data is not None: 
                        self._write_stem(md.secondary_stem, secondary_data, md.model_samplerate)
                        outputs[md.secondary_stem] = secondary_data
            else: self._console_log_base(f"Error: Selected Demucs stem '{md.primary_stem}' not found.")
        clear_gpu_cache_logic(); return outputs
        
class SeperateVRLogic(SeparatorAttributesLogic):
    def _loading_mix_vr(self, audio_file_path_str: str) -> Optional[np.ndarray]:
        if not spec_utils or not self.md.vr_model_param: self._console_log_base("VR spec_utils/params error."); return None
        X_wave: Dict[int, np.ndarray] = {}; X_spec_s: Dict[int, np.ndarray] = {}
        mp = self.md.vr_model_param; bands_n = len(mp.param['band'])
        is_mp3 = Path(audio_file_path_str).suffix.lower() == '.mp3'
        for d_idx in range(bands_n, 0, -1): 
            bp = mp.param['band'][d_idx]; wav_resolution = 'polyphase'
            if d_idx == bands_n: 
                X_wave[d_idx], _ = librosa.load(str(audio_file_path_str), sr=bp['sr'], mono=False, dtype=np.float32, res_type=wav_resolution)

                if not np.any(X_wave[d_idx]) and is_mp3: 
                    try:
                        with audioread.audio_open(str(audio_file_path_str)) as f: track_length = int(f.duration)
                        X_wave[d_idx], _ = librosa.load(str(audio_file_path_str), sr=bp['sr'], mono=False, dtype=np.float32, res_type=wav_resolution, duration=track_length)

                    except Exception as e: print(f"Audioread fallback for MP3 failed: {e}")
                if X_wave[d_idx].ndim == 1: X_wave[d_idx] = np.asarray([X_wave[d_idx], X_wave[d_idx]])
            else: 
                X_wave[d_idx] = librosa.resample(X_wave[d_idx+1], orig_sr=mp.param['band'][d_idx+1]['sr'], target_sr=bp['sr'], res_type=wav_resolution)

            X_spec_s[d_idx] = spec_utils.wave_to_spectrogram(X_wave[d_idx], bp['hl'], bp['n_fft'], mp, band=d_idx, is_v51_model=self.md.is_vr_51_model)

            if d_idx == bands_n and self.md.is_high_end_process: 
                self.input_high_end_h = (bp['n_fft']//2 - bp['crop_stop']) + (mp.param['pre_filter_stop'] - mp.param['pre_filter_start'])
                self.input_high_end = X_spec_s[d_idx][:, bp['n_fft']//2-self.input_high_end_h : bp['n_fft']//2, :]
        combined_spec = spec_utils.combine_spectrograms(X_spec_s, mp, is_v51_model=self.md.is_vr_51_model)

        return combined_spec

    def _inference_vr_logic(self, X_spec: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        if not self.model_run_instance or not spec_utils: self._console_log_base("VR model/spec_utils error."); return None, None
        md = self.md; model_run = self.model_run_instance
        def _execute(X_mag_pad, roi_size):
            X_dataset = []; 
            patches = (X_mag_pad.shape[2] - 2 * model_run.offset) // roi_size

            if patches == 0: self._console_log_base(f"Warning: Not enough data for patches (patches = {patches})."); return np.array([])
            total_iterations = patches // md.batch_size if not md.is_tta else (patches // md.batch_size) * 2; self.progress_value = 0
            for i in range(patches): 
                patch = X_mag_pad[:, :, i*roi_size : i*roi_size + md.window_size]

                X_dataset.append(patch)
            X_dataset_np = np.asarray(X_dataset); mask_chunks = []
            with torch.no_grad():
                for i in range(0, patches, md.batch_size):
                    if not self._is_running_check(): raise InterruptedError("Processing stopped.")
                    self.progress_value += 1; self._update_progress(self.progress_value / total_iterations if total_iterations > 0 else 1.0)
                    X_batch = torch.from_numpy(X_dataset_np[i : i + md.batch_size]).to(self.device)
                    pred = model_run.predict_mask(X_batch) 

                    if not pred.shape[3] > 0: raise ValueError(ac.WINDOW_SIZE_ERROR_MESSAGE)
                    mask_chunks.append(pred.detach().cpu().numpy())
                if not mask_chunks: self._console_log_base("Warning: No mask chunks."); return np.array([])
                # Concatenate each chunk along time axis
                concatenated_chunks = [np.concatenate(chunk, axis=2) for chunk in mask_chunks]
                mask = np.concatenate(concatenated_chunks, axis=2)
            return mask
        X_mag, X_phase = spec_utils.preprocess(X_spec); n_frame = X_mag.shape[2]

        pad_l, pad_r, roi_size = spec_utils.make_padding(n_frame, md.window_size, model_run.offset)

        X_mag_pad = np.pad(X_mag, ((0,0),(0,0),(pad_l,pad_r)), mode='constant'); X_mag_pad /= X_mag_pad.max() if X_mag_pad.max() > 0 else 1.0
        mask_pred = _execute(X_mag_pad, roi_size)
        if mask_pred.size == 0: 
            self._console_log_base("Error: Mask prediction failed (mask_pred is empty). This usually means the audio is too short for the model's window size."); 
            # Return appropriately shaped zero spectrograms to avoid downstream errors with empty arrays
            # This will lead to silent output stems instead of a crash.
            zero_spec_shape = X_mag.shape # (2, freq_bins, n_frame)

            return np.zeros(zero_spec_shape, dtype=complex), np.zeros(zero_spec_shape, dtype=complex)

        if md.is_tta:
            X_mag_pad_tta = np.pad(X_mag, ((0,0),(0,0),(pad_l+roi_size//2,pad_r+roi_size//2)), mode='constant'); X_mag_pad_tta /= X_mag_pad_tta.max() if X_mag_pad_tta.max() > 0 else 1.0
            mask_tta_pred = _execute(X_mag_pad_tta, roi_size)
            if mask_tta_pred.size != 0: mask_pred = (mask_pred[:,:,:n_frame] + mask_tta_pred[:,:,roi_size//2:roi_size//2+n_frame]) * 0.5
            else: self._console_log_base("Warning: TTA mask prediction failed.")
        else: mask_pred = mask_pred[:,:,:n_frame]
        is_non_accom_stem = any(stem == md.primary_stem for stem in ac.NON_ACCOM_STEMS)
        agg_split_bin = md.vr_model_param.param['band'][1]['crop_stop'] if md.vr_model_param and 'band' in md.vr_model_param.param and len(md.vr_model_param.param['band']) > 1 else 1024
        agg_correction = md.vr_model_param.param.get('aggr_correction') if md.vr_model_param else None
        mask_final = spec_utils.adjust_aggr(mask_pred, is_non_accom_stem, {'value': md.aggression_setting, 'split_bin': agg_split_bin, 'aggr_correction': agg_correction})
        if md.is_post_process: mask_final = spec_utils.merge_artifacts(mask_final, thres=md.post_process_threshold)
        y_spec = mask_final * X_mag * np.exp(1.j * X_phase); v_spec = (1 - mask_final) * X_mag * np.exp(1.j * X_phase)
        return y_spec, v_spec

    def _spec_to_wav_vr_logic(self, spec: np.ndarray) -> Optional[np.ndarray]:
        if not spec_utils or not self.md.vr_model_param:
            self._console_log_base("VR spec_utils/params error.")
            return None

        # Debug info about the input spectrogram
        stem_name = self.md.primary_stem if not self.md.is_secondary_stem_only else self.md.secondary_stem
        print(f"DEBUG: {stem_name} spec shape before _spec_to_wav_vr_logic: {spec.shape}")

        # Check for NaN/Inf values in the spectrogram
        if np.isnan(np.sum(spec)):
            self._console_log_base("Warning: Spectrogram contains NaN values. Attempting to fix...")
            spec = np.nan_to_num(spec, nan=0.0)
        if np.isinf(np.sum(spec)):
            self._console_log_base("Warning: Spectrogram contains Inf values. Attempting to fix...")
            spec = np.nan_to_num(spec, posinf=1.0, neginf=-1.0)

        # Additional check for zero values
        if np.all(np.abs(spec) < 1e-10):
            self._console_log_base(f"Warning: Spectrogram for {stem_name} contains all zeros or very small values.")
            # Create a small non-zero spectrogram instead of returning empty array
            # This helps avoid downstream issues with empty arrays
            dummy_spec = np.ones_like(spec) * 1e-5
            spec = dummy_spec

        # Proceed with conversion
        result = None
        try:
            # Proceed with actual conversion
            if self.md.is_high_end_process and isinstance(self.input_high_end, np.ndarray) and self.input_high_end_h is not None:
                try:
                    input_high_end_mirrored = spec_utils.mirroring('mirroring', spec, self.input_high_end, self.md.vr_model_param)
                    result = spec_utils.cmb_spectrogram_to_wave(spec, self.md.vr_model_param, self.input_high_end_h, input_high_end_mirrored, is_v51_model=self.md.is_vr_51_model)
                except Exception as e:
                    self._console_log_base(f"Error in high-end processing: {e}")
                    # Fall back to regular processing
                    result = spec_utils.cmb_spectrogram_to_wave(spec, self.md.vr_model_param, is_v51_model=self.md.is_vr_51_model)
            else:
                result = spec_utils.cmb_spectrogram_to_wave(spec, self.md.vr_model_param, is_v51_model=self.md.is_vr_51_model)
        except Exception as e:
            self._console_log_base(f"Error in spectrogram to wave conversion: {e}")
            import traceback
            self._console_log_base(f"Traceback: {traceback.format_exc()}")
            # Create a small non-zero waveform instead of empty array
            return np.ones((2, 1000)) * 1e-5  # Small non-zero array

        # Debug info about the output waveform
        print(f"DEBUG: {stem_name} shape after _spec_to_wav_vr_logic: {result.shape if result is not None else 'None'}")

        # Check if result is empty or None
        if result is None:
            self._console_log_base(f"Warning: Conversion returned None for {stem_name}.")
            return np.ones((2, 1000)) * 1e-5  # Small non-zero array

        if result.size == 0 or result.shape[1] == 0:
            print(f"DEBUG: {stem_name} is empty (shape {result.shape}) BEFORE resampling. Creating non-empty output.")
            self._console_log_base(f"Warning: Conversion produced empty output for {stem_name}. Creating non-empty output.")
            
            # Get the original audio file to determine the length for silent output
            original_mix_audio_array = self.process_data.get('input_audio_array')
            if original_mix_audio_array is not None:
                # Create silent output with same length as original audio
                if original_mix_audio_array.ndim == 1:
                    # Original is mono, create stereo silent output
                    return np.zeros((2, len(original_mix_audio_array)))
                else:
                    # Original is stereo, match its shape
                    if original_mix_audio_array.shape[0] > original_mix_audio_array.shape[1]:
                        # If (length, channels), transpose to (channels, length)
                        return np.zeros_like(original_mix_audio_array.T)
                    else:
                        # Already (channels, length)
                        return np.zeros_like(original_mix_audio_array)
            
            # If we don't have the original audio, create a default silent output
            return np.ones((2, 1000)) * 1e-5  # Small non-zero array

        # Check for NaN/Inf values in the result
        if np.isnan(np.sum(result)):
            self._console_log_base(f"Warning: Result contains NaN values. Fixing...")
            result = np.nan_to_num(result, nan=0.0)
        if np.isinf(np.sum(result)):
            self._console_log_base(f"Warning: Result contains Inf values. Fixing...")
            result = np.nan_to_num(result, posinf=1.0, neginf=-1.0)

        return result

    def seperate(self) -> Optional[Dict[str, np.ndarray]]:
        if not all([nets_new_vr, nets_vr, ModelParameters, spec_utils, self.md.vr_model_param]): self._console_log_base("VR dependencies/params error."); return None
        md = self.md; self.progress_value = 0; 
        
        # Prepare original mix to get its shape for silent output generation if needed
        original_mix_audio_array = self._prepare_mix()
        if original_mix_audio_array is None:
            self._console_log_base("Failed to load original audio, cannot proceed.")
            return None
        # original_mix_audio_array is (length, channels)

        self._console_log_base(f"Processing with VR model: {md.model_basename}...")
        try:
            # Get model hash for debugging
            import hashlib
            with open(md.model_path, 'rb') as f:
                model_hash = hashlib.md5(f.read()).hexdigest()
            self._console_log_base(f"Model file hash: {model_hash}")
            
            # Check if hash exists in model_data.json
            model_hash_found = False
            if hasattr(md, 'vr_model_param') and md.vr_model_param:
                self._console_log_base(f"Using VR model parameters: {md.vr_model_param.param['band'][1]['sr']} Hz, {md.vr_model_param.param['band'][1]['n_fft']} FFT")
                model_hash_found = True
            else:
                self._console_log_base("Warning: VR model parameters not found or invalid")
            
            nn_arch_sizes=[31191,33966,56817,123821,123812,129605,218409,537238,537227]; vr_5_1_models_sizes=[56817,218409]
            model_size_kb = Path(md.model_path).stat().st_size/1024; nn_arch_size=min(nn_arch_sizes, key=lambda x:abs(x-model_size_kb))
            self._console_log_base(f"Model size: {model_size_kb} KB, Selected architecture size: {nn_arch_size}")
            
            if nn_arch_size in vr_5_1_models_sizes or md.is_vr_51_model:
                self._console_log_base("Using VR 5.1 model architecture")
                self.model_run_instance = nets_new_vr.CascadedNet(md.vr_model_param.param['bins']*2, nn_arch_size, nout=md.model_capacity[0], nout_lstm=md.model_capacity[1])
            else:
                self._console_log_base("Using standard VR model architecture")
                self.model_run_instance = nets_vr.determine_model_capacity(md.vr_model_param.param['bins']*2, nn_arch_size)
            
            self.model_run_instance.load_state_dict(torch.load(md.model_path, map_location=CPU_DEVICE))
            self.model_run_instance.to(self.device).eval()
        except Exception as e: 
            self._console_log_base(f"Error loading VR model: {e}")
            import traceback
            self._console_log_base(f"Traceback: {traceback.format_exc()}")
            return None
            
        self._update_progress(0.0, message="Loading audio mix...")
        X_spec = self._loading_mix_vr(str(self.audio_file_path))
        if X_spec is None: return None
        
        # Check spectrogram
        if np.all(np.abs(X_spec) < 1e-10):
            self._console_log_base("Warning: Input spectrogram contains all zeros or very small values")
        
        self._console_log_base("Running VR inference...")
        y_spec, v_spec = self._inference_vr_logic(X_spec)
        
        if y_spec is None or v_spec is None: 
            self._console_log_base("VR inference error.")
            return None

        # NaN/Inf check for y_spec and v_spec
        if np.isnan(np.sum(y_spec)):
            self._console_log_base("Warning: Primary stem spectrogram contains NaN values. Attempting to fix...")
            y_spec = np.nan_to_num(y_spec, nan=0.0)
        if np.isinf(np.sum(y_spec)):
            self._console_log_base("Warning: Primary stem spectrogram contains Inf values. Attempting to fix...")
            y_spec = np.nan_to_num(y_spec, posinf=1.0, neginf=-1.0)
            
        if np.isnan(np.sum(v_spec)):
            self._console_log_base("Warning: Secondary stem spectrogram contains NaN values. Attempting to fix...")
            v_spec = np.nan_to_num(v_spec, nan=0.0)
        if np.isinf(np.sum(v_spec)):
            self._console_log_base("Warning: Secondary stem spectrogram contains Inf values. Attempting to fix...")
            v_spec = np.nan_to_num(v_spec, posinf=1.0, neginf=-1.0)

        self._console_log(ac.DONE_MESSAGE); outputs = {}
        if not md.is_secondary_stem_only:
            self._console_log_base(f"Converting {md.primary_stem}..."); 

            primary_wave = self._spec_to_wav_vr_logic(y_spec)

            if primary_wave is not None:
                if primary_wave.size == 0:
                    self._console_log_base(f"Warning: {md.primary_stem} wave is empty. Creating silent output.")
                    primary_wave = np.zeros_like(original_mix_audio_array) 
                
                if md.model_samplerate!=ac.DEFAULT_SAMPLE_RATE and primary_wave.size > 0: # Ensure not resampling empty array
                    self._console_log_base(f"Resampling {md.primary_stem} from {md.model_samplerate} Hz to {ac.DEFAULT_SAMPLE_RATE} Hz")
                    primary_wave=librosa.resample(primary_wave.T,orig_sr=md.model_samplerate,target_sr=ac.DEFAULT_SAMPLE_RATE).T
                elif primary_wave.size == 0 and md.model_samplerate != ac.DEFAULT_SAMPLE_RATE:
                    # If it was empty and SR mismatch, it remains an empty array correctly shaped by np.zeros_like
                    pass

                self.primary_source=primary_wave; self.primary_source_map=self._final_process_stem("",primary_wave,self.secondary_source_primary,md.primary_stem,ac.DEFAULT_SAMPLE_RATE); outputs.update(self.primary_source_map)
            else: self._console_log_base(f"Failed to convert {md.primary_stem} (returned None).")
        
        if not md.is_primary_stem_only:
            self._console_log_base(f"Converting {md.secondary_stem}..."); 

            secondary_wave = self._spec_to_wav_vr_logic(v_spec)

            if secondary_wave is not None:
                if secondary_wave.size == 0:
                    self._console_log_base(f"Warning: {md.secondary_stem} wave is empty. Creating silent output.")
                    secondary_wave = np.zeros_like(original_mix_audio_array)

                if md.model_samplerate!=ac.DEFAULT_SAMPLE_RATE and secondary_wave.size > 0: # Ensure not resampling empty array
                    self._console_log_base(f"Resampling {md.secondary_stem} from {md.model_samplerate} Hz to {ac.DEFAULT_SAMPLE_RATE} Hz")
                    secondary_wave=librosa.resample(secondary_wave.T,orig_sr=md.model_samplerate,target_sr=ac.DEFAULT_SAMPLE_RATE).T
                elif secondary_wave.size == 0 and md.model_samplerate != ac.DEFAULT_SAMPLE_RATE:
                    pass
                    
                self.secondary_source=secondary_wave; self.secondary_source_map=self._final_process_stem("",secondary_wave,self.secondary_source_secondary,md.secondary_stem,ac.DEFAULT_SAMPLE_RATE); outputs.update(self.secondary_source_map)
            else: 
                self._console_log_base(f"Failed to convert {md.secondary_stem} (returned None).")
        clear_gpu_cache_logic(); return outputs

def vr_denoiser_logic(audio_input: np.ndarray, device: torch.device, model_path_str: str, 
                      is_deverber: bool = False, 
                      hop_length: int = 1024, n_fft: int = 2048, cropsize: int = 256) -> np.ndarray:
    if not nets_new_vr or not spec_utils:
        print("Warning: VR denoiser dependencies missing.")
        return audio_input 
    
    model_path = Path(model_path_str)
    if not model_path.exists():
        print(f"Warning: Denoiser/Deverber model not found: {model_path}")
        return audio_input

    nout, nout_lstm = (64,128) if is_deverber else (16,128)
    
    try:
        model = nets_new_vr.CascadedNet(n_fft, nout=nout, nout_lstm=nout_lstm)
        model.load_state_dict(torch.load(str(model_path), map_location=CPU_DEVICE))
        model.to(device)
        model.eval()
    except Exception as e:
        print(f"Error loading denoiser/deverber model {model_path}: {e}")
        return audio_input

    if audio_input.shape[0] > audio_input.shape[1]: # Ensure (channels, length)
        audio_input = audio_input.T 
        
    X_spec = spec_utils.wave_to_spectrogram_old(audio_input, hop_length, n_fft)
   
    X_mag, X_phase = np.abs(X_spec), np.angle(X_spec)
    n_frame = X_mag.shape[2]
    pad_l, pad_r, roi_size = spec_utils.make_padding(n_frame, cropsize, model.offset)
    X_mag_pad = np.pad(X_mag, ((0,0),(0,0),(pad_l,pad_r)), mode='constant')
    if X_mag_pad.max() > 0: # Avoid division by zero if X_mag_pad is all zeros
        X_mag_pad /= X_mag_pad.max()
    
    X_dataset = [X_mag_pad[:,:,i*roi_size:i*roi_size+cropsize] for i in range((X_mag_pad.shape[2]-2*model.offset)//roi_size)]
    if not X_dataset: 
        return audio_input 
    
    X_dataset_np = np.asarray(X_dataset)
    mask_list = []
    
    with torch.no_grad():
        for i in range(0, X_dataset_np.shape[0], 4): 
            X_batch = torch.from_numpy(X_dataset_np[i:i+4]).to(device)
            pred = model.predict_mask(X_batch)
            # Assuming pred is (batch_actual, C, F, T_roi)
            # We need to concatenate along time for each item in batch, then collect these.
            # Original UVR's _execute in SeperateVR.inference_vr had:
            # mask_chunks.append(pred.detach().cpu().numpy())
            # ...
            # mask = np.concatenate([np.concatenate(chunk, axis=2) for chunk in mask_chunks], axis=2)
            # This implies pred.detach().cpu().numpy() is a batch of masks, and each mask in that batch
            # is then concatenated along its time axis (axis=2).
            # However, if pred is already (batch_size, C, F, T_roi), then np.concatenate(pred_numpy, axis=2)
            # would try to treat the batch_size dim as the sequence to concatenate, which is wrong.
            # It should be that each item *within* the batch (if pred is a list of tensors) is concatenated,
            # or if pred is a single tensor (batch, C, F, T_roi), then it's used directly or split.

            # Let's assume pred.detach().cpu().numpy() is (actual_batch_size, C, F, T_roi)
            batch_masks_np = pred.detach().cpu().numpy()
            # We want to append each mask in the batch to mask_list, after ensuring it's (C,F,T_roi)
            # The original code `np.concatenate(pred.detach().cpu().numpy(), axis=2)` was likely intended
            # if `predict_mask` returned a list of tensors. If it returns a single batched tensor,
            # we need to iterate through the batch.
            for single_mask_in_batch in batch_masks_np: # single_mask_in_batch is (C,F,T_roi)
                 mask_list.append(single_mask_in_batch) # Append each (C,F,T_roi)

    if not mask_list: 
        return audio_input
        
    # Now mask_list contains individual masks of shape (C,F,T_roi)
    # We need to concatenate them along the time axis (axis=2)
    mask = np.concatenate(mask_list, axis=2)
    mask = mask[:,:,:n_frame] # Trim to original n_frame

    v_spec = (mask if is_deverber else (1-mask)) * X_mag * np.exp(1.j * X_phase)
    wave = spec_utils.spectrogram_to_wave_old(v_spec, hop_length=hop_length) # Expects (C,F,T)
    
    # Ensure wave is (channels, length) before transposing for match_array_shapes
    if wave.shape[0] > wave.shape[1]: wave = wave.T 
    
    # audio_input was (channels, length), org_mix_shape_ref for match_array_shapes should be (length, channels)
    return spec_utils.match_array_shapes(wave.T, audio_input.T).T # Return (channels, length)
