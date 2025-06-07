from __future__ import annotations

import gc
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch

from . import app_constants as ac
from .logger_utils import get_logger
from .model_data import ModelData

logger = get_logger("separate_logic_base")

try:
    from lib_v5 import spec_utils
except ImportError as e:
    logger.warning(f"lib_v5 spec_utils not found: {e}")
    spec_utils = None

import warnings

import audioread
import librosa
import soundfile as sf

try:
    import pydub
except ImportError:
    logger.warning("Warning: pydub not found.")
    pydub = None

MPS_AVAILABLE = torch.backends.mps.is_available() if ac.IS_MACOS else False
CUDA_AVAILABLE = torch.cuda.is_available()
CPU_DEVICE = torch.device("cpu")
warnings.filterwarnings("ignore")


def clear_gpu_cache_logic():
    """Clear GPU cache to free memory."""
    gc.collect()
    if ac.IS_MACOS and MPS_AVAILABLE:
        torch.mps.empty_cache()
    elif CUDA_AVAILABLE:
        torch.cuda.empty_cache()


def prepare_mix_logic(audio_file_path_str: str) -> Optional[np.ndarray]:
    """Load and prepare audio file for processing."""
    audio_file_path = Path(audio_file_path_str)
    mix_audio = None
    try:
        mix_audio, sr = librosa.load(
            str(audio_file_path), mono=False, sr=ac.DEFAULT_SAMPLE_RATE
        )
    except Exception as e:
        logger.warning(
            f"Librosa failed to load {audio_file_path}: {e}. Trying audioread."
        )
        try:
            with audioread.audio_open(str(audio_file_path)) as f:
                track_length = int(f.duration)
            mix_audio, sr = librosa.load(
                str(audio_file_path),
                duration=track_length,
                mono=False,
                sr=ac.DEFAULT_SAMPLE_RATE,
            )
        except Exception as e2:
            logger.warning(f"Audioread also failed for {audio_file_path}: {e2}")
            return None
    if mix_audio.ndim == 1:
        mix_audio = np.asfortranarray([mix_audio, mix_audio])
    return mix_audio.T


def write_audio_logic(
    stem_path_str: str,
    stem_source: np.ndarray,
    samplerate: int,
    model_data: ModelData,
    stem_name: Optional[str] = None,
    process_data: Optional[Dict] = None,
):
    """Write processed audio stem to file."""
    stem_path = Path(stem_path_str)

    # Check if stem_source is empty or too small
    if stem_source.size == 0 or (stem_source.ndim > 1 and stem_source.shape[1] == 0):
        logger.debug(
            f"{stem_name} is empty (shape {stem_source.shape}). Generating silent output of original length."
        )

        # Get the original audio file to determine the length for silent output
        if process_data and "input_audio_array" in process_data:
            original_audio = process_data["input_audio_array"]
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
                stem_source = np.zeros(
                    (2, samplerate * 3)
                )  # 3 seconds of stereo silence

    # Ensure correct shape
    if stem_source.ndim == 1:
        stem_source = np.asfortranarray([stem_source, stem_source]).T
    elif stem_source.shape[0] < stem_source.shape[1]:
        stem_source = stem_source.T

    # Check for NaN/Inf values
    if np.isnan(np.sum(stem_source)):
        logger.debug(f"{stem_name} contains NaN values. Fixing...")
        stem_source = np.nan_to_num(stem_source, nan=0.0)
    if np.isinf(np.sum(stem_source)):
        logger.debug(f"{stem_name} contains Inf values. Fixing...")
        stem_source = np.nan_to_num(stem_source, posinf=1.0, neginf=-1.0)

    if model_data.is_normalization and spec_utils:
        stem_source = spec_utils.normalize(stem_source, True)

    # Map wav_type_set to valid soundfile subtypes
    subtype_map = {
        "PCM_16": "PCM_16",
        "PCM_24": "PCM_24",
        "PCM_32": "PCM_32",
        "FLOAT": "FLOAT",
        "DOUBLE": "DOUBLE",
    }
    subtype = subtype_map.get(model_data.wav_type_set, "PCM_16")

    # Debugging prints
    logger.debug(f"Attempting to write audio to: {stem_path}")
    logger.debug(f"Samplerate: {samplerate}")
    logger.debug(f"model_data.wav_type_set: {model_data.wav_type_set}")
    logger.debug(f"Determined subtype for sf.write: {subtype}")
    logger.debug(f"stem_source.dtype: {stem_source.dtype}")
    logger.debug(f"stem_source.shape: {stem_source.shape}")

    try:
        sf.write(str(stem_path), stem_source, samplerate, subtype=subtype)
    except Exception as e_sf_write:
        logger.warning(
            f"Error writing audio with soundfile: {e_sf_write}. Attempting fallback."
        )
        try:
            sf.write(str(stem_path), stem_source, samplerate)
        except Exception as e_sf_write_fallback:
            logger.error(f"Failed to write audio with fallback: {e_sf_write_fallback}")

    # Convert to desired output format if not WAV
    if model_data.save_format != ac.WAV and pydub:
        try:
            audio_segment = pydub.AudioSegment.from_wav(str(stem_path))

            export_params = {"format": model_data.save_format.lower()}
            if model_data.save_format == ac.MP3:
                export_params["bitrate"] = "320k"

            # Change file extension
            stem_path_new = stem_path.with_suffix(f".{model_data.save_format.lower()}")
            audio_segment.export(str(stem_path_new), **export_params)

            # Remove the temporary WAV file
            stem_path.unlink()

        except Exception as e_convert:
            logger.warning(f"Failed to convert audio format: {e_convert}")


class SeparatorAttributesLogic:
    """Base class for all separator implementations."""

    def __init__(self, model_data: ModelData, process_data: Dict[str, Any]):
        self.md = model_data
        self.process_data = process_data

        # Set up device
        if self.md.is_gpu_conversion:
            if ac.IS_MACOS and MPS_AVAILABLE:
                self.device = torch.device("mps")
            elif CUDA_AVAILABLE:
                self.device = torch.device("cuda")
            else:
                self.device = CPU_DEVICE
        else:
            self.device = CPU_DEVICE

        # Set up audio file paths
        if self.md.audio_file:
            self.audio_file_path = Path(self.md.audio_file)
            self.audio_file_base = self.audio_file_path.stem
        else:
            self.audio_file_path = None
            self.audio_file_base = "output"

        # Use export_path from process_data if provided, otherwise use model's export_path
        # This allows ensemble processing to use temporary directories
        if process_data.get("export_path"):
            self.export_path = Path(process_data["export_path"])
        elif self.md.export_path:
            self.export_path = Path(self.md.export_path)
        else:
            self.export_path = Path(".")

        # Set up callbacks
        self.set_progress_bar = process_data.get("set_progress_bar", lambda x: None)
        self.write_to_console = process_data.get("write_to_console", lambda x: None)
        self.process_iteration = process_data.get("process_iteration", lambda: None)
        self._is_running_check = process_data.get("_is_running_check", lambda: True)
        self.base_text_console = process_data.get("base_text_console", "")

    def _console_log_base(self, message: str):
        """Log message with base console text."""
        logger.info(message)

    def _console_log(self, message: str):
        """Log message and send to console."""
        self._console_log_base(message)
        if self.write_to_console:
            self.write_to_console(f"{self.base_text_console}{message}")

    def _update_progress(
        self, current_step_fraction: float, message: Optional[str] = None
    ):
        """Update progress bar and console."""
        if self.set_progress_bar:
            self.set_progress_bar(current_step_fraction)
        if message and self.write_to_console:
            self.write_to_console(f"{self.base_text_console}{message}")

    def _prepare_mix(self) -> Optional[np.ndarray]:
        """Prepare audio mix for processing."""
        if not self.md.audio_file:
            return None
        return prepare_mix_logic(self.md.audio_file)

    def _write_stem(self, stem_name: str, stem_data: np.ndarray, samplerate: int):
        """Write processed stem to file."""
        if self.md.export_path and self.audio_file_base:
            stem_path = (
                self.export_path / f"{self.audio_file_base}_{stem_name}.{ac.WAV}"
            )
            write_audio_logic(
                str(stem_path),
                stem_data,
                samplerate,
                self.md,
                stem_name,
                self.process_data,
            )

    def _pitch_fix(
        self, source_audio: np.ndarray, sr_pitched: int, org_mix_shape_ref: np.ndarray
    ) -> np.ndarray:
        """Apply pitch correction if needed."""
        if self.md.is_pitch_change and self.md.semitone_shift:
            try:
                source_audio = librosa.effects.pitch_shift(
                    source_audio.T, sr=sr_pitched, n_steps=self.md.semitone_shift
                ).T
            except Exception as e:
                logger.warning(f"Pitch shift failed: {e}")
        return source_audio

    def _final_process_stem(
        self,
        stem_path_str: str,
        source_data: np.ndarray,
        secondary_model_output: Optional[np.ndarray],
        stem_name: str,
        samplerate: int,
    ) -> Dict[str, np.ndarray]:
        """Final processing and writing of stem."""
        result = {}

        if secondary_model_output is not None:
            # Process with secondary model
            result[f"{stem_name}_secondary"] = secondary_model_output

        result[stem_name] = source_data
        return result

    def separate(self) -> Optional[Dict[str, np.ndarray]]:
        """Main separation method - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement separate method")
