from __future__ import annotations

import hashlib
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import audioread
import librosa
import numpy as np
import torch

from lib_v5 import spec_utils
from lib_v5.vr_network import nets as nets_vr
from lib_v5.vr_network import nets_new as nets_new_vr
from lib_v5.vr_network.model_param_init import ModelParameters

from . import app_constants as ac
from .logger_utils import get_logger
from .model_data import ModelData
from .separate_logic_base import (
    CPU_DEVICE,
    SeparatorAttributesLogic,
    clear_gpu_cache_logic,
)

logger = get_logger("separate_vr_logic")


class SeparateVRLogic(SeparatorAttributesLogic):
    """VR (Vocal Remover) separator implementation."""

    def __init__(self, model_data: ModelData, process_data: Dict[str, Any]):
        super().__init__(model_data, process_data)

        # VR-specific attributes
        self.model_run_instance = None
        self.input_high_end = None
        self.input_high_end_h = None
        self.primary_source = None
        self.secondary_source = None
        self.primary_source_map = {}
        self.secondary_source_map = {}
        self.secondary_source_primary = None
        self.secondary_source_secondary = None
        self.progress_value = 0

    def _loading_mix_vr(self, audio_file_path_str: str) -> Optional[np.ndarray]:
        """Load and process audio for VR separation."""
        X_wave: Dict[int, np.ndarray] = {}
        X_spec_s: Dict[int, np.ndarray] = {}
        mp = self.md.vr_model_param
        bands_n = len(mp.param["band"])
        is_mp3 = Path(audio_file_path_str).suffix.lower() == ".mp3"

        for d_idx in range(bands_n, 0, -1):
            bp = mp.param["band"][d_idx]
            wav_resolution = "polyphase"

            if d_idx == bands_n:
                X_wave[d_idx], _ = librosa.load(
                    str(audio_file_path_str),
                    sr=bp["sr"],
                    mono=False,
                    dtype=np.float32,
                    res_type=wav_resolution,
                )

                if not np.any(X_wave[d_idx]) and is_mp3:
                    try:
                        with audioread.audio_open(str(audio_file_path_str)) as f:
                            track_length = int(f.duration)
                        X_wave[d_idx], _ = librosa.load(
                            str(audio_file_path_str),
                            sr=bp["sr"],
                            mono=False,
                            dtype=np.float32,
                            res_type=wav_resolution,
                            duration=track_length,
                        )
                    except Exception as e:
                        logger.error(f"Audioread fallback for MP3 failed: {e}")

                if X_wave[d_idx].ndim == 1:
                    X_wave[d_idx] = np.asarray([X_wave[d_idx], X_wave[d_idx]])
            else:
                X_wave[d_idx] = librosa.resample(
                    X_wave[d_idx + 1],
                    orig_sr=mp.param["band"][d_idx + 1]["sr"],
                    target_sr=bp["sr"],
                    res_type=wav_resolution,
                )

            X_spec_s[d_idx] = spec_utils.wave_to_spectrogram(
                X_wave[d_idx],
                bp["hl"],
                bp["n_fft"],
                mp,
                band=d_idx,
                is_v51_model=self.md.is_vr_51_model,
            )

            if d_idx == bands_n and self.md.is_high_end_process:
                self.input_high_end_h = (bp["n_fft"] // 2 - bp["crop_stop"]) + (
                    mp.param["pre_filter_stop"] - mp.param["pre_filter_start"]
                )
                self.input_high_end = X_spec_s[d_idx][
                    :, bp["n_fft"] // 2 - self.input_high_end_h : bp["n_fft"] // 2, :
                ]

        combined_spec = spec_utils.combine_spectrograms(
            X_spec_s, mp, is_v51_model=self.md.is_vr_51_model
        )
        return combined_spec

    def _inference_vr_logic(
        self, X_spec: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Run VR model inference on spectrogram."""
        if not self.model_run_instance or not spec_utils:
            logger.error("VR model/spec_utils error.")
            return None, None

        md = self.md
        model_run = self.model_run_instance

        def _execute(X_mag_pad, roi_size):
            X_dataset = []
            patches = (X_mag_pad.shape[2] - 2 * model_run.offset) // roi_size

            if patches == 0:
                logger.warning(
                    f"Warning: Not enough data for patches (patches = {patches})."
                )
                return np.array([])

            self.progress_value = 0

            for i in range(patches):
                patch = X_mag_pad[:, :, i * roi_size : i * roi_size + md.window_size]
                X_dataset.append(patch)

            X_dataset_np = np.asarray(X_dataset)
            mask_chunks = []

            with torch.no_grad():
                total_batches = (
                    patches + md.batch_size - 1
                ) // md.batch_size  # Ceiling division
                batch_count = 0

                for i in range(0, patches, md.batch_size):
                    if not self._is_running_check():
                        raise InterruptedError("Processing stopped.")

                    batch_count += 1
                    # Progress from 30% to 75% during inference
                    progress_fraction = 0.30 + (
                        0.45 * (batch_count / max(total_batches, 1))
                    )
                    self._update_progress(progress_fraction)

                    X_batch = torch.from_numpy(X_dataset_np[i : i + md.batch_size]).to(
                        self.device
                    )
                    pred = model_run.predict_mask(X_batch)

                    if not pred.shape[3] > 0:
                        raise ValueError(ac.WINDOW_SIZE_ERROR_MESSAGE)
                    mask_chunks.append(pred.detach().cpu().numpy())

                if not mask_chunks:
                    logger.warning("Warning: No mask chunks.")
                    return np.array([])

                # Concatenate each chunk along time axis
                concatenated_chunks = [
                    np.concatenate(chunk, axis=2) for chunk in mask_chunks
                ]
                mask = np.concatenate(concatenated_chunks, axis=2)
            return mask

        X_mag, X_phase = spec_utils.preprocess(X_spec)
        n_frame = X_mag.shape[2]

        pad_l, pad_r, roi_size = spec_utils.make_padding(
            n_frame, md.window_size, model_run.offset
        )

        X_mag_pad = np.pad(X_mag, ((0, 0), (0, 0), (pad_l, pad_r)), mode="constant")
        X_mag_pad /= X_mag_pad.max() if X_mag_pad.max() > 0 else 1.0
        mask_pred = _execute(X_mag_pad, roi_size)

        if mask_pred.size == 0:
            logger.warning(
                "Warning: Mask prediction failed (mask_pred is empty). This usually means the audio is too short for the model's window size."
            )
            # Return appropriately shaped zero spectrograms to avoid downstream errors with empty arrays
            # This will lead to silent output stems instead of a crash.
            zero_spec_shape = X_mag.shape  # (2, freq_bins, n_frame)
            return np.zeros(zero_spec_shape, dtype=complex), np.zeros(
                zero_spec_shape, dtype=complex
            )

        if md.is_tta:
            X_mag_pad_tta = np.pad(
                X_mag,
                ((0, 0), (0, 0), (pad_l + roi_size // 2, pad_r + roi_size // 2)),
                mode="constant",
            )
            X_mag_pad_tta /= X_mag_pad_tta.max() if X_mag_pad_tta.max() > 0 else 1.0
            mask_tta_pred = _execute(X_mag_pad_tta, roi_size)
            if mask_tta_pred.size != 0:
                mask_pred = (
                    mask_pred[:, :, :n_frame]
                    + mask_tta_pred[:, :, roi_size // 2 : roi_size // 2 + n_frame]
                ) * 0.5
            else:
                logger.warning("Warning: TTA mask prediction failed.")
        else:
            mask_pred = mask_pred[:, :, :n_frame]

        is_non_accom_stem = any(stem == md.primary_stem for stem in ac.NON_ACCOM_STEMS)
        agg_split_bin = (
            md.vr_model_param.param["band"][1]["crop_stop"]
            if md.vr_model_param
            and "band" in md.vr_model_param.param
            and len(md.vr_model_param.param["band"]) > 1
            else 1024
        )
        agg_correction = (
            md.vr_model_param.param.get("aggr_correction")
            if md.vr_model_param
            else None
        )
        mask_final = spec_utils.adjust_aggr(
            mask_pred,
            is_non_accom_stem,
            {
                "value": md.aggression_setting,
                "split_bin": agg_split_bin,
                "aggr_correction": agg_correction,
            },
        )

        if md.is_post_process:
            mask_final = spec_utils.merge_artifacts(
                mask_final, thres=md.post_process_threshold
            )

        y_spec = mask_final * X_mag * np.exp(1.0j * X_phase)
        v_spec = (1 - mask_final) * X_mag * np.exp(1.0j * X_phase)
        return y_spec, v_spec

    def _spec_to_wav_vr_logic(self, spec: np.ndarray) -> Optional[np.ndarray]:
        """Convert spectrogram back to waveform using VR parameters."""
        if not spec_utils or not self.md.vr_model_param:
            logger.error("VR spec_utils/params error.")
            return None

        # Debug info about the input spectrogram
        stem_name = (
            self.md.primary_stem
            if not self.md.is_secondary_stem_only
            else self.md.secondary_stem
        )
        logger.debug(
            f"{stem_name} spec shape before _spec_to_wav_vr_logic: {spec.shape}"
        )

        # Check for NaN/Inf values in the spectrogram
        if np.isnan(np.sum(spec)):
            logger.warning(
                "Warning: Spectrogram contains NaN values. Attempting to fix..."
            )
            spec = np.nan_to_num(spec, nan=0.0)
        if np.isinf(np.sum(spec)):
            logger.warning(
                "Warning: Spectrogram contains Inf values. Attempting to fix..."
            )
            spec = np.nan_to_num(spec, posinf=1.0, neginf=-1.0)

        # Additional check for zero values
        if np.all(np.abs(spec) < 1e-10):
            logger.warning(
                f"Warning: Spectrogram for {stem_name} contains all zeros or very small values."
            )
            # Create a small non-zero spectrogram instead of returning empty array
            # This helps avoid downstream issues with empty arrays
            dummy_spec = np.ones_like(spec) * 1e-5
            spec = dummy_spec

        # Proceed with conversion
        result = None
        try:
            # Proceed with actual conversion
            if (
                self.md.is_high_end_process
                and isinstance(self.input_high_end, np.ndarray)
                and self.input_high_end_h is not None
            ):
                try:
                    input_high_end_mirrored = spec_utils.mirroring(
                        "mirroring", spec, self.input_high_end, self.md.vr_model_param
                    )
                    result = spec_utils.cmb_spectrogram_to_wave(
                        spec,
                        self.md.vr_model_param,
                        self.input_high_end_h,
                        input_high_end_mirrored,
                        is_v51_model=self.md.is_vr_51_model,
                    )
                except Exception as e:
                    logger.error(f"Error in high-end processing: {e}")
                    # Fall back to regular processing
                    result = spec_utils.cmb_spectrogram_to_wave(
                        spec,
                        self.md.vr_model_param,
                        is_v51_model=self.md.is_vr_51_model,
                    )
            else:
                result = spec_utils.cmb_spectrogram_to_wave(
                    spec, self.md.vr_model_param, is_v51_model=self.md.is_vr_51_model
                )
        except Exception as e:
            logger.error(f"Error in spectrogram to wave conversion: {e}")

            logger.error(f"Traceback: {traceback.format_exc()}")
            # Create a small non-zero waveform instead of empty array
            return np.ones((2, 1000)) * 1e-5  # Small non-zero array

        # Debug info about the output waveform
        logger.debug(
            f"{stem_name} shape after _spec_to_wav_vr_logic: {result.shape if result is not None else 'None'}"
        )

        # Check if result is empty or None
        if result is None:
            logger.warning(f"Warning: Conversion returned None for {stem_name}.")
            return np.ones((2, 1000)) * 1e-5  # Small non-zero array

        if result.size == 0 or result.shape[1] == 0:
            logger.warning(
                f"{stem_name} is empty (shape {result.shape}) BEFORE resampling. Creating non-empty output."
            )
            logger.warning(
                f"Warning: Conversion produced empty output for {stem_name}. Creating non-empty output."
            )

            # Get the original audio file to determine the length for silent output
            original_mix_audio_array = self.process_data.get("input_audio_array")
            if original_mix_audio_array is not None:
                # Create silent output with same length as original audio
                if original_mix_audio_array.ndim == 1:
                    # Original is mono, create stereo silent output
                    return np.zeros((2, len(original_mix_audio_array)))
                else:
                    # Original is stereo, match its shape
                    if (
                        original_mix_audio_array.shape[0]
                        > original_mix_audio_array.shape[1]
                    ):
                        # If (length, channels), transpose to (channels, length)
                        return np.zeros_like(original_mix_audio_array.T)
                    else:
                        # Already (channels, length)
                        return np.zeros_like(original_mix_audio_array)

            # If we don't have the original audio, create a default silent output
            return np.ones((2, 1000)) * 1e-5  # Small non-zero array

        # Check for NaN/Inf values in the result
        if np.isnan(np.sum(result)):
            logger.warning("Warning: Result contains NaN values. Fixing...")
            result = np.nan_to_num(result, nan=0.0)
        if np.isinf(np.sum(result)):
            logger.warning("Warning: Result contains Inf values. Fixing...")
            result = np.nan_to_num(result, posinf=1.0, neginf=-1.0)

        return result

    def separate(self) -> Optional[Dict[str, np.ndarray]]:
        """Main VR separation method."""
        if not all(
            [nets_new_vr, nets_vr, ModelParameters, spec_utils, self.md.vr_model_param]
        ):
            logger.error("VR dependencies/params error.")
            return None

        md = self.md
        self.progress_value = 0

        # Prepare original mix to get its shape for silent output generation if needed
        original_mix_audio_array = self._prepare_mix()
        if original_mix_audio_array is None:
            logger.error("Failed to load original audio, cannot proceed.")
            return None
        # original_mix_audio_array is (length, channels)

        logger.info(f"Processing with VR model: {md.model_basename}...")
        try:
            # Get model hash for debugging
            with open(md.model_path, "rb") as f:
                model_hash = hashlib.md5(f.read(), usedforsecurity=False).hexdigest()
            logger.info(f"Model file hash: {model_hash}")

            # Check if hash exists in model_data.json
            model_hash_found = False
            if hasattr(md, "vr_model_param") and md.vr_model_param:
                logger.info(
                    f"Using VR model parameters: {md.vr_model_param.param['band'][1]['sr']} Hz, {md.vr_model_param.param['band'][1]['n_fft']} FFT"
                )
                model_hash_found = True
            else:
                logger.warning("Warning: VR model parameters not found or invalid")

            nn_arch_sizes = [
                31191,
                33966,
                56817,
                123821,
                123812,
                129605,
                218409,
                537238,
                537227,
            ]
            vr_5_1_models_sizes = [56817, 218409]
            model_size_kb = Path(md.model_path).stat().st_size / 1024
            nn_arch_size = min(nn_arch_sizes, key=lambda x: abs(x - model_size_kb))
            logger.info(
                f"Model size: {model_size_kb} KB, Selected architecture size: {nn_arch_size}"
            )

            if nn_arch_size in vr_5_1_models_sizes or md.is_vr_51_model:
                logger.info("Using VR 5.1 model architecture")
                self.model_run_instance = nets_new_vr.CascadedNet(
                    md.vr_model_param.param["bins"] * 2,
                    nn_arch_size,
                    nout=md.model_capacity[0],
                    nout_lstm=md.model_capacity[1],
                )
            else:
                logger.info("Using standard VR model architecture")
                self.model_run_instance = nets_vr.determine_model_capacity(
                    md.vr_model_param.param["bins"] * 2, nn_arch_size
                )

            # Fix for PyTorch 2.6+ - add weights_only=False for model loading
            self.model_run_instance.load_state_dict(
                torch.load(md.model_path, map_location=CPU_DEVICE, weights_only=False)
            )
            self.model_run_instance.to(self.device).eval()
        except Exception as e:
            logger.error(f"Error loading VR model: {e}")
            logger.error(traceback.format_exc())
            return None

        self._update_progress(0.25, message="Preprocessing audio...")
        X_spec = self._loading_mix_vr(str(self.audio_file_path))
        if X_spec is None:
            return None

        # Check spectrogram
        if np.all(np.abs(X_spec) < 1e-10):
            logger.warning(
                "Warning: Input spectrogram contains all zeros or very small values"
            )

        self._update_progress(0.30, message="Running VR inference...")

        y_spec, v_spec = self._inference_vr_logic(X_spec)

        if y_spec is None or v_spec is None:
            logger.error("VR inference error.")
            return None

        self._update_progress(0.75, message="Converting spectrograms to audio...")

        # NaN/Inf check for y_spec and v_spec
        if np.isnan(np.sum(y_spec)):
            logger.warning(
                "Warning: Primary stem spectrogram contains NaN values. Attempting to fix..."
            )
            y_spec = np.nan_to_num(y_spec, nan=0.0)
        if np.isinf(np.sum(y_spec)):
            logger.warning(
                "Warning: Primary stem spectrogram contains Inf values. Attempting to fix..."
            )
            y_spec = np.nan_to_num(y_spec, posinf=1.0, neginf=-1.0)

        if np.isnan(np.sum(v_spec)):
            logger.warning(
                "Warning: Secondary stem spectrogram contains NaN values. Attempting to fix..."
            )
            v_spec = np.nan_to_num(v_spec, nan=0.0)
        if np.isinf(np.sum(v_spec)):
            logger.warning(
                "Warning: Secondary stem spectrogram contains Inf values. Attempting to fix..."
            )
            v_spec = np.nan_to_num(v_spec, posinf=1.0, neginf=-1.0)

        outputs = {}

        # Map model outputs to deliver what the user actually requested
        # VR models produce: y_spec (masked portion) and v_spec (inverted mask portion)
        # Model's JSON defines which stem type is in the masked portion (primary_stem)
        logger.info(
            f"VR processing: model primary_stem={md.primary_stem}, secondary_stem={md.secondary_stem}"
        )

        # Check if user made a specific stem request
        user_requested_specific_stem = getattr(md, "user_requested_stem", None)
        model_primary_stem = md.primary_stem
        model_secondary_stem = md.secondary_stem

        if user_requested_specific_stem:
            logger.info(f"User specifically requested: {user_requested_specific_stem}")
            logger.info(
                f"Model outputs: primary={model_primary_stem}, secondary={model_secondary_stem}"
            )

            # Determine which spectrogram contains the user's requested stem
            if user_requested_specific_stem == model_primary_stem:
                # User wants what's in the primary stem (y_spec)
                target_primary_spec = y_spec
                target_secondary_spec = v_spec
                logger.info(
                    f"User wants primary stem: using y_spec for {user_requested_specific_stem}"
                )
            elif user_requested_specific_stem == model_secondary_stem:
                # User wants what's in the secondary stem (v_spec)
                target_primary_spec = v_spec
                target_secondary_spec = y_spec
                logger.info(
                    f"User wants secondary stem: using v_spec for {user_requested_specific_stem}"
                )
            else:
                # Fallback: user requested something not in this model's capabilities
                target_primary_spec = y_spec
                target_secondary_spec = v_spec
                logger.warning(
                    f"User requested {user_requested_specific_stem} but model only has {model_primary_stem}/{model_secondary_stem}"
                )
        else:
            # No specific user request - use standard mapping
            target_primary_spec = y_spec
            target_secondary_spec = v_spec
            logger.info("No specific user request: using standard mapping")

        self._update_progress(0.80, message="Processing stems...")

        if not md.is_secondary_stem_only:
            primary_wave = self._spec_to_wav_vr_logic(target_primary_spec)

            if primary_wave is not None:
                if primary_wave.size == 0:
                    logger.warning(
                        "Warning: output wave is empty. Creating silent output."
                    )
                    primary_wave = np.zeros_like(original_mix_audio_array)

                if (
                    md.model_samplerate != ac.DEFAULT_SAMPLE_RATE
                    and primary_wave.size > 0
                ):  # Ensure not resampling empty array
                    primary_wave = librosa.resample(
                        primary_wave.T,
                        orig_sr=md.model_samplerate,
                        target_sr=ac.DEFAULT_SAMPLE_RATE,
                    ).T
                elif (
                    primary_wave.size == 0
                    and md.model_samplerate != ac.DEFAULT_SAMPLE_RATE
                ):
                    # If it was empty and SR mismatch, it remains an empty array correctly shaped by np.zeros_like
                    pass

                self.primary_source = primary_wave

                # Use the user's requested stem name if available, otherwise use model's primary stem
                output_stem_name = (
                    user_requested_specific_stem
                    if user_requested_specific_stem
                    else md.primary_stem
                )

                self.primary_source_map = self._final_process_stem(
                    "",
                    primary_wave,
                    self.secondary_source_primary,
                    output_stem_name,
                    ac.DEFAULT_SAMPLE_RATE,
                )
                outputs.update(self.primary_source_map)
            else:
                logger.warning(f"Failed to convert {md.primary_stem} (returned None).")

        self._update_progress(0.90, message="Finalizing...")

        if not md.is_primary_stem_only:
            secondary_wave = self._spec_to_wav_vr_logic(target_secondary_spec)

            if secondary_wave is not None:
                if secondary_wave.size == 0:
                    logger.warning(
                        "Warning: secondary output wave is empty. Creating silent output."
                    )
                    secondary_wave = np.zeros_like(original_mix_audio_array)

                if (
                    md.model_samplerate != ac.DEFAULT_SAMPLE_RATE
                    and secondary_wave.size > 0
                ):  # Ensure not resampling empty array
                    secondary_wave = librosa.resample(
                        secondary_wave.T,
                        orig_sr=md.model_samplerate,
                        target_sr=ac.DEFAULT_SAMPLE_RATE,
                    ).T
                elif (
                    secondary_wave.size == 0
                    and md.model_samplerate != ac.DEFAULT_SAMPLE_RATE
                ):
                    pass

                # VR secondary stem is just the converted spectrogram
                self.secondary_source = secondary_wave

                # Determine the secondary stem name based on what we're outputting
                if user_requested_specific_stem:
                    # If user requested a specific stem, the secondary is the other one
                    secondary_stem_name = (
                        model_primary_stem
                        if user_requested_specific_stem == model_secondary_stem
                        else model_secondary_stem
                    )
                else:
                    secondary_stem_name = md.secondary_stem

                self.secondary_source_map = self._final_process_stem(
                    "",
                    secondary_wave,
                    self.secondary_source_secondary,
                    secondary_stem_name,
                    ac.DEFAULT_SAMPLE_RATE,
                )
                outputs.update(self.secondary_source_map)
            else:
                logger.warning(
                    f"Failed to convert {md.secondary_stem} (returned None)."
                )

        clear_gpu_cache_logic()
        return outputs


def vr_denoiser_logic(
    audio_input: np.ndarray,
    device: torch.device,
    model_path_str: str,
    is_deverber: bool = False,
    hop_length: int = 1024,
    n_fft: int = 2048,
    cropsize: int = 256,
) -> np.ndarray:
    """Apply VR denoiser/deverber processing to audio."""
    if not nets_new_vr or not spec_utils:
        logger.warning("Warning: VR denoiser dependencies missing.")
        return audio_input

    model_path = Path(model_path_str)
    if not model_path.exists():
        logger.warning(f"Warning: Denoiser/Deverber model not found: {model_path}")
        return audio_input

    nout, nout_lstm = (64, 128) if is_deverber else (16, 128)

    try:
        model = nets_new_vr.CascadedNet(n_fft, nout=nout, nout_lstm=nout_lstm)
        model.load_state_dict(
            torch.load(str(model_path), map_location=CPU_DEVICE, weights_only=False)
        )
        model.to(device)
        model.eval()
    except Exception as e:
        logger.error(f"Error loading denoiser/deverber model {model_path}: {e}")
        return audio_input

    if audio_input.shape[0] > audio_input.shape[1]:  # Ensure (channels, length)
        audio_input = audio_input.T

    X_spec = spec_utils.wave_to_spectrogram_old(audio_input, hop_length, n_fft)

    X_mag, X_phase = np.abs(X_spec), np.angle(X_spec)
    n_frame = X_mag.shape[2]
    pad_l, pad_r, roi_size = spec_utils.make_padding(n_frame, cropsize, model.offset)
    X_mag_pad = np.pad(X_mag, ((0, 0), (0, 0), (pad_l, pad_r)), mode="constant")
    if X_mag_pad.max() > 0:  # Avoid division by zero if X_mag_pad is all zeros
        X_mag_pad /= X_mag_pad.max()

    X_dataset = [
        X_mag_pad[:, :, i * roi_size : i * roi_size + cropsize]
        for i in range((X_mag_pad.shape[2] - 2 * model.offset) // roi_size)
    ]
    if not X_dataset:
        return audio_input

    X_dataset_np = np.asarray(X_dataset)
    mask_list = []

    with torch.no_grad():
        for i in range(0, X_dataset_np.shape[0], 4):
            X_batch = torch.from_numpy(X_dataset_np[i : i + 4]).to(device)
            pred = model.predict_mask(X_batch)
            batch_masks_np = pred.detach().cpu().numpy()
            for single_mask_in_batch in batch_masks_np:
                mask_list.append(single_mask_in_batch)

    if not mask_list:
        return audio_input

    mask = np.concatenate(mask_list, axis=2)
    mask = mask[:, :, :n_frame]

    v_spec = (mask if is_deverber else (1 - mask)) * X_mag * np.exp(1.0j * X_phase)
    wave = spec_utils.spectrogram_to_wave_old(v_spec, hop_length=hop_length)

    if wave.shape[0] > wave.shape[1]:
        wave = wave.T

    return spec_utils.match_array_shapes(wave.T, audio_input.T).T
