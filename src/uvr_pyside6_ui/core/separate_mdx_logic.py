from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np
import torch

from . import app_constants as ac
from .logger_utils import get_logger
from .model_data import ModelData
from .separate_logic_base import (
    SeparatorAttributesLogic,
    clear_gpu_cache_logic,
)

logger = get_logger("separate_mdx_logic")

try:
    from lib_v5 import mdxnet as MdxnetSet
    from lib_v5 import spec_utils
    from lib_v5.tfc_tdf_v3 import STFT as LibV5_STFT
except ImportError as e:
    logger.warning(f"lib_v5 MDX modules not found: {e}")
    MdxnetSet, spec_utils, LibV5_STFT = None, None, None

try:
    import onnxruntime as ort
    from onnx import load as onnx_load
    from onnx2pytorch import ConvertModel as onnx_ConvertModel
except ImportError:
    logger.warning("Warning: ONNX related modules not found.")
    ort, onnx_load, onnx_ConvertModel = None, None, None

# Import vr_denoiser_logic from VR module
try:
    from .separate_vr_logic import vr_denoiser_logic
except ImportError:
    logger.warning("Warning: vr_denoiser_logic not found.")
    vr_denoiser_logic = None


class SeperateMDXLogic(SeparatorAttributesLogic):
    """MDX separator implementation."""

    def __init__(self, model_data: ModelData, process_data: Dict[str, Any]):
        super().__init__(model_data, process_data)
        self.stft_tool = None
        self.n_bins = 0
        self.trim = 0
        self.chunk_size = 0
        self.gen_size = 0
        self.hop_length = 1024
        self.is_onnx_model = False
        self.model_run_instance = None
        self.progress_value = 0

        # Set up device execution providers
        if self.md.is_gpu_conversion:
            if self.device.type == "cuda":
                self.run_type = [ac.CUDA_EXECUTION_PROVIDER, ac.CPU_EXECUTION_PROVIDER]
            elif self.device.type == "mps":
                self.run_type = [
                    ac.CPU_EXECUTION_PROVIDER
                ]  # MPS not supported for ONNX
            else:
                self.run_type = [ac.CPU_EXECUTION_PROVIDER]
        else:
            self.run_type = [ac.CPU_EXECUTION_PROVIDER]

    def _initialize_model_settings(self):
        """Initialize MDX model settings."""
        md = self.md
        self.hop_length = 1024
        if md.is_mdx_ckpt:
            if md.mdx_c_configs and isinstance(md.mdx_c_configs, dict):
                self.hop_length = md.mdx_c_configs.get("hop_length", self.hop_length)

        if md.mdx_n_fft_scale_set is None or md.mdx_dim_f_set is None:
            raise ValueError(
                "MDX FFT scale or Dim F not set in ModelData for MDX model."
            )

        self.n_bins = md.mdx_n_fft_scale_set // 2 + 1
        self.trim = md.mdx_n_fft_scale_set // 2
        self.chunk_size = self.hop_length * (md.mdx_segment_size - 1)
        self.gen_size = self.chunk_size - 2 * self.trim

        if not LibV5_STFT:
            raise ImportError("LibV5_STFT not available.")
        self.stft_tool = LibV5_STFT(
            md.mdx_n_fft_scale_set, self.hop_length, md.mdx_dim_f_set, self.device
        )

    def _run_model_onnx_pytorch(
        self, mix_part_torch: torch.Tensor, is_match_freq_cut: bool
    ) -> np.ndarray:
        """Run MDX model inference on audio chunk."""
        md = self.md
        adjust = 1.0

        spec = self.stft_tool(mix_part_torch) * adjust
        spec[:, :, :3, :] *= 0

        if is_match_freq_cut:
            return spec.cpu().detach().numpy()

        if md.is_mdx_ckpt:
            spec_pred = self.model_run_instance(spec)
        elif self.is_onnx_model:
            if md.mdx_segment_size == md.mdx_dim_t_set and not (
                self.device.type == "mps"
            ):
                # For ONNX Runtime inference
                input_name = self.model_run_instance.get_inputs()[0].name
                output_name = self.model_run_instance.get_outputs()[0].name
                spec_cpu = spec.cpu().numpy()
                spec_pred_np = self.model_run_instance.run(
                    [output_name], {input_name: spec_cpu}
                )[0]
                spec_pred = torch.tensor(spec_pred_np).to(self.device)
            else:
                # For PyTorch converted ONNX model
                spec_pred = self.model_run_instance(spec)
        else:
            raise ValueError("MDX model type not recognized for running.")

        if not is_match_freq_cut and md.denoise_option != ac.DENOISE_NONE:
            spec_pred = (
                -self.model_run_instance(-spec) * 0.5
                + self.model_run_instance(spec) * 0.5
            )

        return self.stft_tool.inverse(spec_pred).cpu().detach().numpy()

    def _demix_mdx(self, mix_processed_norm_np: np.ndarray) -> Optional[np.ndarray]:
        """Perform MDX demixing on audio."""
        try:
            self._initialize_model_settings()
        except Exception as e:
            logger.error(f"Error initializing MDX settings: {e}")
            return None

        md = self.md
        org_mix_shape_ref = mix_processed_norm_np.T

        actual_sr_pitched = ac.DEFAULT_SAMPLE_RATE
        if md.is_pitch_change:
            if not spec_utils:
                logger.error("Error: spec_utils not available for pitch change.")
                return None
            mix_processed_norm_np, actual_sr_pitched = (
                spec_utils.change_pitch_semitones(
                    mix_processed_norm_np,
                    ac.DEFAULT_SAMPLE_RATE,
                    semitone_shift=-md.semitone_shift,
                )
            )

        pad_amount = (
            self.gen_size
            + self.trim
            - ((mix_processed_norm_np.shape[1]) % self.gen_size)
        )
        mixture_padded_np = np.concatenate(
            (
                np.zeros((2, self.trim), dtype="float32"),
                mix_processed_norm_np,
                np.zeros((2, pad_amount), dtype="float32"),
            ),
            axis=1,
        )

        overlap_val = (
            md.overlap_mdx
            if isinstance(md.overlap_mdx, (int, float)) and md.overlap_mdx != ac.DEFAULT
            else 0.25
        )
        step = (
            int((1 - overlap_val) * self.chunk_size)
            if overlap_val != 0
            else self.chunk_size
        )

        result_buff = np.zeros((1, 2, mixture_padded_np.shape[1]), dtype=np.float32)
        divider_buff = np.zeros((1, 2, mixture_padded_np.shape[1]), dtype=np.float32)

        total_chunks = math.ceil(mixture_padded_np.shape[1] / step) if step > 0 else 1
        self.progress_value = 0

        for i in range(0, mixture_padded_np.shape[1], step):
            if not self._is_running_check():
                raise InterruptedError("Processing stopped by user.")
            self.progress_value += 1
            self._update_progress(
                self.progress_value / total_chunks if total_chunks > 0 else 1.0
            )

            start_idx, end_idx = i, min(i + self.chunk_size, mixture_padded_np.shape[1])
            actual_chunk_size = end_idx - start_idx
            mix_chunk_np = mixture_padded_np[:, start_idx:end_idx]
            if actual_chunk_size < self.chunk_size:
                mix_chunk_np = np.concatenate(
                    (
                        mix_chunk_np,
                        np.zeros(
                            (2, self.chunk_size - actual_chunk_size), dtype="float32"
                        ),
                    ),
                    axis=1,
                )

            mix_chunk_torch = (
                torch.tensor(mix_chunk_np[None, ...]).float().to(self.device)
            )

            with torch.no_grad():
                processed_chunk_np = self._run_model_onnx_pytorch(
                    mix_chunk_torch, is_match_freq_cut=False
                )

            window = np.hanning(actual_chunk_size)
            window = np.tile(window[None, :], (2, 1)) if overlap_val != 0 else None

            if window is not None:
                result_buff[0, :, start_idx:end_idx] += (
                    processed_chunk_np[0, :, :actual_chunk_size] * window
                )
                divider_buff[0, :, start_idx:end_idx] += window
            else:
                result_buff[0, :, start_idx:end_idx] += processed_chunk_np[
                    0, :, :actual_chunk_size
                ]
                divider_buff[0, :, start_idx:end_idx] += 1

        divider_buff[divider_buff == 0] = 1.0
        processed_audio_np = result_buff / divider_buff
        processed_audio_np = processed_audio_np[
            0, :, self.trim : mixture_padded_np.shape[1] - self.trim - pad_amount
        ]

        if md.is_pitch_change:
            processed_audio_np = self._pitch_fix(
                processed_audio_np, actual_sr_pitched, org_mix_shape_ref
            )
        if md.compensate is not None:
            processed_audio_np *= md.compensate
        if md.is_denoise_model and md.DENOISER_MODEL_PATH and vr_denoiser_logic:
            logger.info("Denoising output...")
            processed_audio_np = vr_denoiser_logic(
                processed_audio_np, self.device, md.DENOISER_MODEL_PATH
            )

        return processed_audio_np.T

    def seperate(self) -> Optional[Dict[str, np.ndarray]]:
        """Main MDX separation method."""
        if not MdxnetSet or not ort or not onnx_load or not onnx_ConvertModel:
            logger.error("Error: MDX-Net or ONNX dependencies not available.")
            return None

        md = self.md
        self.progress_value = 0
        mix_audio_norm_np = self._prepare_mix()
        if mix_audio_norm_np is None:
            return None

        logger.info(f"Processing with {md.model_basename}...")

        if md.is_mdx_ckpt:
            if not MdxnetSet:
                logger.error("Error: MdxnetSet (for .ckpt) not available.")
                return None
            logger.info("Loading MDX CKPT model...")
            try:
                # Fix for PyTorch 2.6+ - add weights_only=False for model loading
                model_checkpoint = torch.load(
                    md.model_path,
                    map_location=lambda storage, loc: storage,
                    weights_only=False,
                )["hyper_parameters"]
                self.dim_c, self.hop_length = (
                    model_checkpoint["dim_c"],
                    model_checkpoint["hop_length"],
                )
                separator = MdxnetSet.ConvTDFNet(**model_checkpoint)
                # Fix for PyTorch 2.6+ - add weights_only=False for model loading
                self.model_run_instance = (
                    separator.load_from_checkpoint(md.model_path).to(self.device).eval()
                )
            except Exception as e:
                logger.error(f"Error loading MDX checkpoint: {e}")
                return None
        else:  # ONNX
            self.is_onnx_model = True
            if md.mdx_segment_size == md.mdx_dim_t_set and not (
                self.device.type == "mps"
            ):
                if not ort:
                    logger.error("Error: ONNX Runtime not available.")
                    return None
                self.model_run_instance = ort.InferenceSession(
                    md.model_path, providers=self.run_type
                )
            else:
                if not onnx_load or not onnx_ConvertModel:
                    logger.error("Error: ONNX conversion modules not available.")
                    return None
                onnx_mdl = onnx_load(md.model_path)
                self.model_run_instance = onnx_ConvertModel(onnx_mdl)
                self.model_run_instance.to(self.device).eval()

        primary_stem_data = self._demix_mdx(mix_audio_norm_np.T)
        if primary_stem_data is None:
            return None

        logger.info(ac.DONE_MESSAGE)
        outputs = {}

        if not md.is_primary_stem_only:
            if primary_stem_data.shape == mix_audio_norm_np.shape:
                secondary_stem_data = mix_audio_norm_np - primary_stem_data
                self.secondary_source = secondary_stem_data
                self.secondary_source_map = self._final_process_stem(
                    "",
                    secondary_stem_data,
                    getattr(self, "secondary_source_secondary", None),
                    md.secondary_stem,
                    md.model_samplerate,
                )
                outputs.update(self.secondary_source_map)
            else:
                logger.warning(
                    f"Warning: Shape mismatch for secondary stem {md.model_name}"
                )

        if not md.is_secondary_stem_only:
            self.primary_source = primary_stem_data
            self.primary_source_map = self._final_process_stem(
                "",
                primary_stem_data,
                getattr(self, "secondary_source_primary", None),
                md.primary_stem,
                md.model_samplerate,
            )
            outputs.update(self.primary_source_map)

        clear_gpu_cache_logic()
        return outputs
