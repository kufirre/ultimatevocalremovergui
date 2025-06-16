from __future__ import annotations

import gc
from typing import Any, Dict, Optional

import numpy as np
import torch

from lib_v5 import spec_utils
from lib_v5.tfc_tdf_v3 import TFC_TDF_net

from . import app_constants as ac
from .logger_utils import get_logger
from .model_data import ModelData
from .separate_logic_base import (
    CPU_DEVICE,
    CUDA_AVAILABLE,
    SeparatorAttributesLogic,
    clear_gpu_cache_logic,
)
from .separate_vr_logic import vr_denoiser_logic

logger = get_logger("separate_mdxc_logic")


class SeparateMDXCLogic(SeparatorAttributesLogic):
    """MDX-C separator implementation."""

    def __init__(self, model_data: ModelData, process_data: Dict[str, Any]):
        super().__init__(model_data, process_data)
        self.model_run_instance = None
        self.progress_value = 0

    def _demix_mdxc(
        self, mix_processed_norm_np: np.ndarray
    ) -> Optional[Dict[str, np.ndarray] | np.ndarray]:  # mix is (channels, length)
        """Perform MDX-C demixing on audio."""
        md = self.md
        if not md.mdx_c_configs or not TFC_TDF_net:
            logger.error("MDX-C configs or TFC_TDF_net not available.")
            return None

        org_mix_shape_ref = mix_processed_norm_np.T  # (length, channels) for pitch fix
        actual_sr_pitched = ac.DEFAULT_SAMPLE_RATE
        if md.is_pitch_change:
            if not spec_utils:
                logger.error("spec_utils not available for pitch change.")
                return None
            mix_processed_norm_np, actual_sr_pitched = (
                spec_utils.change_pitch_semitones(
                    mix_processed_norm_np,
                    ac.DEFAULT_SAMPLE_RATE,
                    semitone_shift=-md.semitone_shift,
                )
            )

        mix_tensor = torch.tensor(mix_processed_norm_np, dtype=torch.float32).to(
            self.device
        )

        try:
            num_target_instruments = self.model_run_instance.num_target_instruments
        except AttributeError:
            num_target_instruments = (
                self.model_run_instance.module.num_target_instruments
            )

        segment_size = (
            md.mdx_c_configs.inference.dim_t
            if md.is_mdx_c_seg_def
            else md.mdx_segment_size
        )

        batch_size_mdxc = md.mdx_batch_size
        chunk_size_mdxc = md.mdx_c_configs.audio.hop_length * (segment_size - 1)

        overlap_mdxc_float = float(md.overlap_mdx23) if md.overlap_mdx23 else 8.0
        overlap_mdxc_int = int(overlap_mdxc_float)
        if overlap_mdxc_int == 0:
            overlap_mdxc_int = 1

        hop_size = chunk_size_mdxc // overlap_mdxc_int

        mix_shape_len = mix_tensor.shape[1]
        pad_size = hop_size - (mix_shape_len - chunk_size_mdxc) % hop_size

        mix_tensor_padded = torch.cat(
            [
                torch.zeros(2, chunk_size_mdxc - hop_size, device=self.device),
                mix_tensor,
                torch.zeros(
                    2, pad_size + chunk_size_mdxc - hop_size, device=self.device
                ),
            ],
            dim=1,
        )

        chunks = mix_tensor_padded.unfold(1, chunk_size_mdxc, hop_size).transpose(0, 1)
        batches = [
            chunks[i : i + batch_size_mdxc]
            for i in range(0, len(chunks), batch_size_mdxc)
        ]

        estimated_sources_tensor = (
            torch.zeros(
                num_target_instruments, *mix_tensor_padded.shape, device=self.device
            )
            if num_target_instruments > 1
            else torch.zeros_like(mix_tensor_padded)
        )

        self.progress_value = 0
        total_batches = len(batches)

        with torch.no_grad():
            cnt = 0
            for batch_idx, batch_data in enumerate(batches):
                if not self._is_running_check():
                    raise InterruptedError("Processing stopped by user.")
                self.progress_value = batch_idx + 1
                self._update_progress(
                    self.progress_value / total_batches if total_batches > 0 else 1.0
                )
                processed_batch = self.model_run_instance(batch_data)
                for source_idx_in_batch in range(processed_batch.shape[0]):
                    current_source_output = processed_batch[source_idx_in_batch]
                    start_frame = cnt * hop_size
                    end_frame = start_frame + chunk_size_mdxc

                    # Ensure we don't exceed tensor bounds (using padded tensor size)
                    max_frames = estimated_sources_tensor.shape[-1]
                    actual_end_frame = min(end_frame, max_frames)
                    actual_chunk_size = actual_end_frame - start_frame

                    # Skip invalid chunks but don't warn for end-of-audio edge cases
                    if actual_chunk_size <= 0:
                        if (
                            start_frame < max_frames
                        ):  # Only warn if not expected end condition
                            logger.warning(
                                f"Skipping chunk with invalid size: {actual_chunk_size} (start: {start_frame}, end: {end_frame}, max: {max_frames})"
                            )
                        cnt += 1
                        continue

                    if num_target_instruments > 1:
                        # Ensure output chunk matches expected size
                        if current_source_output.shape[-1] > actual_chunk_size:
                            current_source_output = current_source_output[
                                ..., :actual_chunk_size
                            ]
                        elif current_source_output.shape[-1] < actual_chunk_size:
                            # Pad if too small
                            pad_size = (
                                actual_chunk_size - current_source_output.shape[-1]
                            )
                            current_source_output = torch.cat(
                                [
                                    current_source_output,
                                    torch.zeros(
                                        *current_source_output.shape[:-1],
                                        pad_size,
                                        device=current_source_output.device,
                                    ),
                                ],
                                dim=-1,
                            )

                        estimated_sources_tensor[
                            ..., start_frame:actual_end_frame
                        ] += current_source_output
                    else:
                        # Handle single instrument case
                        output_to_add = (
                            current_source_output[0]
                            if current_source_output.dim() > 2
                            else current_source_output
                        )

                        # Ensure output chunk matches expected size
                        if output_to_add.shape[-1] > actual_chunk_size:
                            output_to_add = output_to_add[..., :actual_chunk_size]
                        elif output_to_add.shape[-1] < actual_chunk_size:
                            # Pad if too small
                            pad_size = actual_chunk_size - output_to_add.shape[-1]
                            output_to_add = torch.cat(
                                [
                                    output_to_add,
                                    torch.zeros(
                                        *output_to_add.shape[:-1],
                                        pad_size,
                                        device=output_to_add.device,
                                    ),
                                ],
                                dim=-1,
                            )

                        estimated_sources_tensor[
                            ..., start_frame:actual_end_frame
                        ] += output_to_add
                    cnt += 1

        final_sources_tensor = (
            estimated_sources_tensor[
                ...,
                chunk_size_mdxc - hop_size : -(pad_size + chunk_size_mdxc - hop_size),
            ]
            / overlap_mdxc_int
        )
        final_sources_np = final_sources_tensor.cpu().detach().numpy()
        del estimated_sources_tensor, chunks, batches, mix_tensor_padded, mix_tensor
        gc.collect()
        if CUDA_AVAILABLE:
            torch.cuda.empty_cache()

        if num_target_instruments > 1:
            result_dict = {}
            for i, stem_name in enumerate(md.mdx_model_stems):
                stem_audio = final_sources_np[i]
                if md.is_pitch_change:
                    stem_audio = self._pitch_fix(
                        stem_audio, actual_sr_pitched, org_mix_shape_ref
                    )
                result_dict[stem_name] = stem_audio.T
                if (
                    md.is_denoise_model
                    and md.DENOISER_MODEL_PATH
                    and stem_name == ac.VOCAL_STEM
                    and ac.INST_STEM in result_dict
                    and vr_denoiser_logic
                ):
                    logger.info(f"Denoising {ac.VOCAL_STEM} (MDX-C)...")
                    denoised_vocals = vr_denoiser_logic(
                        result_dict[ac.VOCAL_STEM].T,
                        self.device,
                        md.DENOISER_MODEL_PATH,
                    ).T
                    if denoised_vocals.shape == org_mix_shape_ref.T.shape:
                        result_dict[ac.INST_STEM] = (
                            org_mix_shape_ref.T - denoised_vocals
                        ).T
                    result_dict[ac.VOCAL_STEM] = denoised_vocals.T
            return result_dict
        else:
            stem_audio = final_sources_np
            if md.is_pitch_change:
                stem_audio = self._pitch_fix(
                    stem_audio, actual_sr_pitched, org_mix_shape_ref
                )
            return stem_audio.T

    def separate(self) -> Optional[Dict[str, np.ndarray]]:
        """Main MDX-C separation method."""
        if not TFC_TDF_net or not self.md.mdx_c_configs:
            logger.error("MDX-C dependencies (TFC_TDF_net/configs) not available.")
            return None

        md = self.md
        self.progress_value = 0
        mix_audio_norm_np = self._prepare_mix()
        if mix_audio_norm_np is None:
            return None

        logger.info(f"Processing with MDX-C model: {md.model_basename}...")
        try:
            self.model_run_instance = TFC_TDF_net(md.mdx_c_configs, device=self.device)
            # Fix for PyTorch 2.6+ - add weights_only=False for model loading
            self.model_run_instance.load_state_dict(
                torch.load(md.model_path, map_location=CPU_DEVICE, weights_only=False)
            )
            self.model_run_instance.to(self.device).eval()
        except Exception as e:
            logger.error(f"Error loading MDX-C model: {e}")
            return None

        processed_output = self._demix_mdxc(mix_audio_norm_np.T)
        if processed_output is None:
            return None

        logger.info(ac.DONE_MESSAGE)
        outputs = {}

        if isinstance(processed_output, dict):
            for stem_name, stem_data_np in processed_output.items():
                if (
                    md.mdxnet_stem_select == ac.ALL_STEMS
                    or stem_name == md.mdxnet_stem_select
                ):
                    current_stem_map = self._final_process_stem(
                        "", stem_data_np, None, stem_name, md.model_samplerate
                    )
                    outputs.update(current_stem_map)
        else:
            primary_stem_data = processed_output
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
                        f"Warning: Shape mismatch for MDX-C secondary stem {md.model_name}"
                    )

        clear_gpu_cache_logic()
        return outputs
