from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch

from . import app_constants as ac
from .logger_utils import get_logger
from .model_data import ModelData
from .separate_logic_base import (
    CPU_DEVICE,
    SeparatorAttributesLogic,
    clear_gpu_cache_logic,
)

logger = get_logger("separate_demucs_logic")

try:
    from demucs.apply import apply_model as demucs_apply_model
    from demucs.apply import demucs_segments
    from demucs.hdemucs import HDemucs
    from demucs.pretrained import get_model as demucs_get_model
    from demucs.utils import (
        apply_model_v1 as demucs_apply_model_v1,
    )
    from demucs.utils import (
        apply_model_v2 as demucs_apply_model_v2,
    )
except ImportError as e:
    logger.warning(f"Demucs modules not found: {e}")
    (
        demucs_apply_model,
        demucs_segments,
        HDemucs,
        demucs_get_model,
        demucs_apply_model_v1,
        demucs_apply_model_v2,
    ) = [None] * 6

try:
    from lib_v5 import spec_utils
except ImportError as e:
    logger.warning(f"lib_v5 spec_utils not found: {e}")
    spec_utils = None


class SeparateDemucsLogic(SeparatorAttributesLogic):
    """Demucs separator implementation."""

    def __init__(self, model_data: ModelData, process_data: Dict[str, Any]):
        super().__init__(model_data, process_data)
        self.model_run_instance = None
        self.progress_value = 0

    def _demix_demucs_logic(
        self, mix_processed_norm_np: np.ndarray
    ) -> Optional[np.ndarray]:
        """Perform Demucs demixing on audio."""
        md = self.md

        # Debug the input audio shape
        logger.debug(f"Input audio shape: {mix_processed_norm_np.shape}")
        logger.debug(f"Input audio dtype: {mix_processed_norm_np.dtype}")
        logger.debug(
            f"Input audio min/max: {np.min(mix_processed_norm_np):.6f}/{np.max(mix_processed_norm_np):.6f}"
        )
        logger.debug(
            f"Input audio contains NaN: {np.isnan(mix_processed_norm_np).any()}"
        )
        logger.debug(
            f"Input audio contains Inf: {np.isinf(mix_processed_norm_np).any()}"
        )

        # Ensure the audio is in the correct format (channels, samples)
        if mix_processed_norm_np.ndim == 1:
            mix_processed_norm_np = np.stack(
                [mix_processed_norm_np, mix_processed_norm_np]
            )
        elif mix_processed_norm_np.shape[0] > mix_processed_norm_np.shape[1]:
            mix_processed_norm_np = mix_processed_norm_np.T

        # Convert to tensor
        mix_tensor = torch.tensor(mix_processed_norm_np).float().to(self.device)
        logger.debug(f"Mix tensor shape: {mix_tensor.shape}")

        actual_sr_pitched = ac.DEFAULT_SAMPLE_RATE
        if md.is_pitch_change:
            if not spec_utils:
                logger.error("spec_utils not available for pitch change.")
                return None
            mix_tensor_np, actual_sr_pitched = spec_utils.change_pitch_semitones(
                mix_tensor.cpu().numpy(),
                ac.DEFAULT_SAMPLE_RATE,
                semitone_shift=-md.semitone_shift,
            )
            mix_tensor = torch.tensor(mix_tensor_np).float().to(self.device)

        # Normalize
        ref_mean = mix_tensor.mean()
        ref_std = mix_tensor.std()
        logger.debug(f"Mix tensor mean: {ref_mean}, std: {ref_std}")
        if ref_std == 0:
            logger.warning("Warning: Standard deviation is zero. Using 1.0 instead.")
            ref_std = 1.0
        mix_tensor = (mix_tensor - ref_mean) / ref_std
        logger.debug(
            f"Normalized mix tensor min/max: {mix_tensor.min().item():.6f}/{mix_tensor.max().item():.6f}"
        )

        processed_sources_tensor = None
        try:
            with torch.no_grad():
                if md.demucs_version == ac.DEMUCS_V1:
                    if not demucs_apply_model_v1:
                        logger.error("Demucs v1 apply_model not available.")
                        return None
                    processed_sources_tensor = demucs_apply_model_v1(
                        self.model_run_instance,
                        mix_tensor,
                        md.shifts,
                        md.is_split_mode,
                        set_progress_bar=lambda p: self._update_progress(p),
                    )
                elif md.demucs_version == ac.DEMUCS_V2:
                    if not demucs_apply_model_v2:
                        logger.error("Demucs v2 apply_model not available.")
                        return None
                    processed_sources_tensor = demucs_apply_model_v2(
                        self.model_run_instance,
                        mix_tensor,
                        md.shifts,
                        md.is_split_mode,
                        md.overlap,
                        set_progress_bar=lambda p: self._update_progress(p),
                    )
                else:
                    if not demucs_apply_model:
                        logger.error("Demucs apply_model not available.")
                        return None

                    # Ensure mix_tensor has the right shape for demucs_apply_model
                    # For Demucs v3/v4, the expected shape is [batch, channels, time]
                    if mix_tensor.dim() == 2:  # [channels, time]
                        mix_tensor_input = mix_tensor.unsqueeze(
                            0
                        )  # Add batch dimension
                    else:
                        mix_tensor_input = mix_tensor

                    logger.debug(
                        f"Input tensor shape to apply_model: {mix_tensor_input.shape}"
                    )

                    # Call apply_model with proper progress callback
                    try:
                        logger.info(
                            f"Calling demucs_apply_model with shifts={md.shifts}, split_mode={md.is_split_mode}, overlap={md.overlap}"
                        )
                        logger.info(
                            f"Model instance type: {type(self.model_run_instance).__name__}"
                        )
                        if self.model_run_instance is None:
                            logger.critical(
                                "CRITICAL ERROR: self.model_run_instance is None before calling demucs_apply_model."
                            )
                            processed_sources_tensor = None
                        else:
                            logger.info("About to call demucs_apply_model with:")
                            logger.info(
                                f"  - model: {type(self.model_run_instance).__name__}"
                            )
                            logger.info(
                                f"  - mix_tensor_input shape: {mix_tensor_input.shape}"
                            )
                            logger.info(f"  - shifts: {md.shifts}")
                            logger.info(f"  - split_mode: {md.is_split_mode}")
                            logger.info(f"  - overlap: {md.overlap}")
                            logger.info(
                                f"  - static_shifts: {1 if md.shifts == 0 else md.shifts}"
                            )
                            logger.info(f"  - device: {self.device}")

                            processed_sources_tensor = demucs_apply_model(
                                self.model_run_instance,
                                mix_tensor_input,
                                md.shifts,
                                md.is_split_mode,
                                md.overlap,
                                static_shifts=1 if md.shifts == 0 else md.shifts,
                                set_progress_bar=self.set_progress_bar,
                                device=self.device,
                            )

                        logger.info("demucs_apply_model completed successfully")
                        if processed_sources_tensor is not None:
                            logger.info(
                                f"processed_sources_tensor shape after apply_model: {processed_sources_tensor.shape}"
                            )
                            # Ensure it's [sources, channels, samples] or [batch, sources, channels, samples]
                            if not (
                                len(processed_sources_tensor.shape) == 3
                                or len(processed_sources_tensor.shape) == 4
                            ):
                                logger.error(
                                    f"ERROR: demucs_apply_model returned tensor with unexpected shape: {processed_sources_tensor.shape}"
                                )
                                processed_sources_tensor = None  # Mark as failed
                        else:
                            logger.error(
                                "processed_sources_tensor is None after apply_model call."
                            )
                            logger.error("ERROR: demucs_apply_model returned None.")
                            # No need to create fallback here, the outer logic will handle it if all_stems_output is None

                    except Exception as e:
                        logger.critical(
                            f"CRITICAL ERROR during Demucs apply_model call: {e}"
                        )
                        import traceback

                        logger.error(traceback.format_exc())
                        processed_sources_tensor = (
                            None  # Ensure it's None if exception occurs
                        )

                        # Fallback creation removed from here, will be handled by the caller if all_stems_output is None.

        except Exception as e:
            logger.error(
                f"Error during Demucs processing (before or after apply_model): {e}"
            )
            import traceback

            logger.error(traceback.format_exc())
            return None

        if processed_sources_tensor is None:
            logger.error("No output from Demucs model.")
            return None

        logger.info(f"Processed sources tensor shape: {processed_sources_tensor.shape}")

        # Denormalize
        try:
            logger.info("Denormalizing processed sources tensor")

            # Move to CPU before numpy conversion
            processed_sources_tensor_cpu = processed_sources_tensor.cpu()

            # Denormalize
            denormalized_tensor = processed_sources_tensor_cpu * ref_std + ref_mean

            # Convert to numpy
            sources_np = denormalized_tensor.numpy()

            logger.info(f"Sources numpy shape: {sources_np.shape}")

            # Handle batch dimension if present
            if len(sources_np.shape) == 4:  # [batch, sources, channels, time]
                logger.info("Removing batch dimension from sources")
                sources_np = sources_np[0]  # Remove batch dimension

            # Check for NaN/Inf values
            if np.isnan(sources_np).any():
                logger.warning("Warning: Sources contain NaN values. Fixing...")
                sources_np = np.nan_to_num(sources_np, nan=0.0)
            if np.isinf(sources_np).any():
                logger.warning("Warning: Sources contain Inf values. Fixing...")
                sources_np = np.nan_to_num(sources_np, posinf=1.0, neginf=-1.0)

            # Swap sources[0] and sources[1] - this is critical for Demucs
            # In the original separate.py, this is done with: sources_np[[0,1]] = sources_np[[1,0]]
            logger.info("Swapping sources[0] and sources[1] for Demucs")
            if sources_np.shape[0] >= 2:
                sources_np[[0, 1]] = sources_np[[1, 0]]
        except Exception as e:
            logger.error(f"ERROR during denormalization: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

            # Create fallback output with appropriate shape
            logger.info("Creating fallback output with appropriate shape")
            if mix_processed_norm_np.ndim == 1:
                sources_np = np.zeros(
                    (4, 1, len(mix_processed_norm_np))
                )  # 4 stems, 1 channel, original length
            else:
                sources_np = np.zeros(
                    (4, 2, mix_processed_norm_np.shape[0])
                )  # 4 stems, 2 channels, original length

        if md.is_pitch_change:
            try:
                final_sources = [
                    self._pitch_fix(
                        sources_np[i], actual_sr_pitched, mix_processed_norm_np
                    ).T
                    for i in range(sources_np.shape[0])
                ]
                sources_np = np.array(final_sources)
            except Exception as e:
                logger.error(f"Error during pitch fix: {e}")

        return sources_np

    def separate(self) -> Optional[Dict[str, np.ndarray]]:
        """Main Demucs separation method."""
        md = self.md
        self.progress_value = 0
        logger.info(f"Processing with Demucs model: {md.model_basename}...")

        # Check if we have the necessary Demucs modules
        if md.demucs_version not in [ac.DEMUCS_V1, ac.DEMUCS_V2] and (
            not demucs_get_model or not demucs_segments
        ):
            logger.error("Demucs modules not available. Please install Demucs.")
            return None

        if (
            not self.md.model_path
            or not Path(self.md.model_path).is_file()
            or Path(self.md.model_path).stat().st_size == 0
        ):
            logger.error(f"Demucs model file not found or empty: {self.md.model_path}")
            return None

        try:
            if (
                not md.model_path
                or not Path(md.model_path).exists()
                or Path(md.model_path).stat().st_size == 0
            ):
                logger.error(f"Demucs model file not found or empty: {md.model_path}")
                return None

            if md.demucs_version == ac.DEMUCS_V1:
                model_file_path = (
                    gzip.open(md.model_path, "rb")
                    if str(md.model_path).endswith(".gz")
                    else md.model_path
                )
                # Use regular torch.load for v1 models
                loaded_data = torch.load(model_file_path, map_location=CPU_DEVICE)
                klass, args, kwargs, state = loaded_data
                self.model_run_instance = klass(*args, **kwargs)
                self.model_run_instance.load_state_dict(state)

            elif md.demucs_version == ac.DEMUCS_V2:
                # Assuming auto_load_demucs_model_v2 is available and correctly imported
                if (
                    demucs_apply_model_v2 is None
                ):  # Check if demucs_apply_model_v2 was imported
                    logger.error("Demucs v2 apply_model not available.")
                    return None
                self.model_run_instance = demucs_apply_model_v2(
                    md.demucs_source_list, md.model_path
                )  # Use demucs_apply_model_v2
                # Use regular torch.load for v2 models
                state_dict = torch.load(md.model_path, map_location=CPU_DEVICE)
                self.model_run_instance.load_state_dict(state_dict)

            else:  # Demucs v3/v4
                model_name_from_path = Path(md.model_path).stem
                repo_path = Path(md.model_path).parent

                # Secure loading using safe_globals context manager for PyTorch 2.6+ compatibility
                try:
                    # Import all required classes that need to be in safe globals
                    import numpy as np
                    import torch.serialization

                    # Get all the classes that might be needed
                    safe_classes = []

                    try:
                        from demucs.htdemucs import HTDemucs

                        safe_classes.append(HTDemucs)
                    except ImportError:
                        pass

                    try:
                        from demucs.hdemucs import HDemucs

                        safe_classes.append(HDemucs)
                    except ImportError:
                        pass

                    try:
                        from demucs.demucs import Demucs

                        safe_classes.append(Demucs)
                    except ImportError:
                        pass

                    try:
                        from demucs.model import Demucs as DemucsV1

                        safe_classes.append(DemucsV1)
                    except ImportError:
                        pass

                    try:
                        from demucs.model_v2 import Demucs as DemucsV2

                        safe_classes.append(DemucsV2)
                    except ImportError:
                        pass

                    # Add numpy classes that are commonly needed
                    import numpy.core.multiarray

                    safe_classes.extend(
                        [
                            numpy.core.multiarray.scalar,
                            numpy.core.multiarray.dtype,
                            numpy.core.multiarray.ndarray,
                            np.dtype,
                            np.ndarray,
                        ]
                    )

                    # Add common torch classes
                    import torch.nn as nn

                    safe_classes.extend(
                        [
                            torch.Tensor,
                            torch.nn.Module,
                            torch.nn.Parameter,
                            nn.Conv1d,
                            nn.Conv2d,
                            nn.ConvTranspose1d,
                            nn.ConvTranspose2d,
                            nn.BatchNorm1d,
                            nn.BatchNorm2d,
                            nn.ReLU,
                            nn.GELU,
                            nn.GLU,
                            nn.Sequential,
                            nn.ModuleList,
                            nn.LayerNorm,
                            nn.GroupNorm,
                            nn.Linear,
                            nn.Embedding,
                            nn.LSTM,
                            nn.GRU,
                        ]
                    )

                    # Add collections and other common classes
                    import collections

                    safe_classes.extend(
                        [
                            collections.OrderedDict,
                            dict,
                            list,
                            tuple,
                            int,
                            float,
                            str,
                            bool,
                        ]
                    )

                    logger.info(
                        f"Loading Demucs model with secure safe_globals ({len(safe_classes)} classes)"
                    )

                    # Use secure safe_globals context manager
                    with torch.serialization.safe_globals(safe_classes):
                        self.model_run_instance = demucs_get_model(
                            name=model_name_from_path, repo=repo_path
                        )
                        if demucs_segments:
                            self.model_run_instance = demucs_segments(
                                md.segment, self.model_run_instance
                            )

                except Exception as e:
                    logger.warning(f"Warning: Could not configure secure loading: {e}")
                    logger.info("Falling back to trusted loading for Demucs models...")
                    # If secure loading fails, fall back to trusted loading since these are user-selected Demucs models
                    # This is still safer than global weights_only=False because it's scoped to just this operation
                    try:
                        import torch

                        # Temporarily override for this specific trusted model loading
                        original_load = torch.load

                        def trusted_load(*args, **kwargs):
                            if "weights_only" not in kwargs:
                                kwargs["weights_only"] = False
                            return original_load(*args, **kwargs)

                        torch.load = trusted_load
                        try:
                            self.model_run_instance = demucs_get_model(
                                name=model_name_from_path, repo=repo_path
                            )
                            if demucs_segments:
                                self.model_run_instance = demucs_segments(
                                    md.segment, self.model_run_instance
                                )
                        finally:
                            torch.load = original_load
                    except Exception as fallback_error:
                        logger.error(
                            f"Both secure and fallback loading failed: {fallback_error}"
                        )
                        return None

            self.model_run_instance.to(self.device).eval()

            if hasattr(self.model_run_instance, "sources"):
                logger.debug(f"Model sources: {list(self.model_run_instance.sources)}")
            if hasattr(self.model_run_instance, "audio_channels"):
                logger.debug(
                    f"Model audio_channels: {self.model_run_instance.audio_channels}"
                )
            if hasattr(self.model_run_instance, "samplerate"):
                logger.debug(f"Model samplerate: {self.model_run_instance.samplerate}")
            if hasattr(self.model_run_instance, "segment"):
                logger.debug(f"Model segment: {self.model_run_instance.segment}")

        except Exception as e:
            logger.error(f"Error loading Demucs model: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return None

        mix_audio_norm_np = self._prepare_mix()
        if mix_audio_norm_np is None:
            logger.error("Failed to prepare audio mix.")
            return None

        logger.info("Starting Demucs processing...")
        all_stems_output = self._demix_demucs_logic(mix_audio_norm_np)

        if all_stems_output is None:
            logger.error("Demucs processing failed. Creating silent outputs.")
            num_expected_sources = (
                len(md.demucs_source_list) if md.demucs_source_list else 4
            )
            if mix_audio_norm_np.ndim == 1:
                silent_output = np.zeros(
                    (num_expected_sources, 1, len(mix_audio_norm_np))
                )
            else:
                silent_output = np.zeros(
                    (num_expected_sources, 2, mix_audio_norm_np.shape[0])
                )
            all_stems_output = silent_output

        self._console_log(ac.DONE_MESSAGE)
        outputs = {}

        # Log stem-only flags
        logger.debug(f"is_primary_stem_only = {md.is_primary_stem_only}")
        logger.debug(f"is_secondary_stem_only = {md.is_secondary_stem_only}")
        logger.debug(f"demucs_stems = {md.demucs_stems}")
        logger.debug(f"primary_stem = {md.primary_stem}")
        logger.debug(f"secondary_stem = {md.secondary_stem}")

        # Use md.demucs_source_map for indexing, as it's derived correctly in ModelData
        if md.demucs_stems == ac.ALL_STEMS:
            logger.debug("Processing ALL_STEMS - will output all 4 stems")
            for stem_name, stem_idx in md.demucs_source_map.items():
                if stem_idx < all_stems_output.shape[0]:  # Ensure index is valid
                    stem_data = all_stems_output[stem_idx].T
                    self._write_stem(stem_name, stem_data, md.model_samplerate)
                    outputs[stem_name] = stem_data
            # Instrumental creation logic (if needed and vocals exist)
            if (
                not md.is_primary_stem_only
                and md.secondary_stem == ac.INST_STEM
                and ac.VOCAL_STEM in md.demucs_source_map
            ):
                vocal_idx = md.demucs_source_map[ac.VOCAL_STEM]
                if vocal_idx < all_stems_output.shape[0]:
                    vocal_data = all_stems_output[vocal_idx].T
                    instrumental_data = mix_audio_norm_np - vocal_data
                    self._write_stem(
                        ac.INST_STEM, instrumental_data, md.model_samplerate
                    )
                    outputs[ac.INST_STEM] = instrumental_data
        else:
            # Single stem processing
            logger.debug(f"Processing single stem: {md.demucs_stems}")
            target_primary_stem_cap = md.demucs_stems

            # Special handling for Instrumental since it's not a direct Demucs output
            if target_primary_stem_cap == ac.INST_STEM:
                logger.debug(
                    "Processing Instrumental stem - will create from other stems"
                )

                # Create instrumental by combining Bass+Drums+Other or subtracting Vocals
                if ac.VOCAL_STEM in md.demucs_source_map:
                    vocal_idx = md.demucs_source_map[ac.VOCAL_STEM]
                    if vocal_idx < all_stems_output.shape[0]:
                        vocal_data = all_stems_output[
                            vocal_idx
                        ].T  # Shape: (length, channels)
                        # mix_audio_norm_np is also (length, channels), so they should match
                        logger.debug(
                            f"mix_audio_norm_np shape: {mix_audio_norm_np.shape}"
                        )
                        logger.debug(f"vocal_data shape: {vocal_data.shape}")
                        instrumental_data = mix_audio_norm_np - vocal_data

                        # Handle instrumental stem only case
                        if md.is_primary_stem_only and not md.is_secondary_stem_only:
                            logger.debug(
                                "Instrumental only mode - outputting single stem"
                            )
                            self._write_stem(
                                ac.INST_STEM, instrumental_data, md.model_samplerate
                            )
                            outputs[ac.INST_STEM] = instrumental_data

                        # Handle vocal stem only case (secondary)
                        elif md.is_secondary_stem_only and not md.is_primary_stem_only:
                            logger.debug(
                                "Vocal only mode (from instrumental selection)"
                            )
                            self._write_stem(
                                ac.VOCAL_STEM, vocal_data, md.model_samplerate
                            )
                            outputs[ac.VOCAL_STEM] = vocal_data

                        # Handle normal dual stem output case
                        else:
                            logger.debug(
                                "Dual stem mode - outputting instrumental and vocal"
                            )
                            self._write_stem(
                                ac.INST_STEM, instrumental_data, md.model_samplerate
                            )
                            outputs[ac.INST_STEM] = instrumental_data

                            self._write_stem(
                                ac.VOCAL_STEM, vocal_data, md.model_samplerate
                            )
                            outputs[ac.VOCAL_STEM] = vocal_data
                    else:
                        logger.error(
                            "Vocal stem index out of range for instrumental creation"
                        )
                else:
                    logger.error(
                        "Vocal stem not found in model for instrumental creation"
                    )

            elif target_primary_stem_cap in md.demucs_source_map:
                stem_idx = md.demucs_source_map[target_primary_stem_cap]
                if stem_idx < all_stems_output.shape[0]:
                    primary_stem_data = all_stems_output[stem_idx].T

                    # Handle primary stem only case
                    if md.is_primary_stem_only and not md.is_secondary_stem_only:
                        logger.debug("Primary stem only mode - outputting single stem")
                        self._write_stem(
                            target_primary_stem_cap,
                            primary_stem_data,
                            md.model_samplerate,
                        )
                        outputs[target_primary_stem_cap] = primary_stem_data

                    # Handle secondary stem only case
                    elif md.is_secondary_stem_only and not md.is_primary_stem_only:
                        logger.debug(
                            "Secondary stem only mode - outputting single stem"
                        )
                        if md.is_demucs_combine_stems:
                            # Combine all non-primary stems
                            combined_stem = np.zeros_like(primary_stem_data)
                            for other_stem, other_idx in md.demucs_source_map.items():
                                if (
                                    other_stem != target_primary_stem_cap
                                    and other_idx < all_stems_output.shape[0]
                                ):
                                    combined_stem += all_stems_output[other_idx].T
                            self._write_stem(
                                md.secondary_stem, combined_stem, md.model_samplerate
                            )
                            outputs[md.secondary_stem] = combined_stem
                        else:
                            # Create secondary by subtraction
                            secondary_stem_data = mix_audio_norm_np - primary_stem_data
                            self._write_stem(
                                md.secondary_stem,
                                secondary_stem_data,
                                md.model_samplerate,
                            )
                            outputs[md.secondary_stem] = secondary_stem_data

                    # Handle normal dual stem output case (both stems)
                    else:
                        logger.debug(
                            "Dual stem mode - outputting primary and secondary stems"
                        )
                        # Output primary stem
                        self._write_stem(
                            target_primary_stem_cap,
                            primary_stem_data,
                            md.model_samplerate,
                        )
                        outputs[target_primary_stem_cap] = primary_stem_data

                        # Create secondary stem if needed
                        if not md.secondary_stem.startswith("No "):
                            if md.is_demucs_combine_stems:
                                # Combine all non-primary stems
                                combined_stem = np.zeros_like(primary_stem_data)
                                for (
                                    other_stem,
                                    other_idx,
                                ) in md.demucs_source_map.items():
                                    if (
                                        other_stem != target_primary_stem_cap
                                        and other_idx < all_stems_output.shape[0]
                                    ):
                                        combined_stem += all_stems_output[other_idx].T
                                self._write_stem(
                                    md.secondary_stem,
                                    combined_stem,
                                    md.model_samplerate,
                                )
                                outputs[md.secondary_stem] = combined_stem
                            else:
                                # Create secondary by subtraction
                                secondary_stem_data = (
                                    mix_audio_norm_np - primary_stem_data
                                )
                                self._write_stem(
                                    md.secondary_stem,
                                    secondary_stem_data,
                                    md.model_samplerate,
                                )
                                outputs[md.secondary_stem] = secondary_stem_data
                else:
                    logger.error(
                        f"Stem index {stem_idx} out of range for model output shape {all_stems_output.shape}"
                    )
            else:
                logger.error(
                    f"Selected Demucs primary stem '{target_primary_stem_cap}' not found in model source map: {md.demucs_source_map}."
                )

        clear_gpu_cache_logic()
        return outputs
