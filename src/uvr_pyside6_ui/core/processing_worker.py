"""
Processing worker.
"""

import gzip
import math
import os
import shutil
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import audioread
import librosa
import numpy as np
import onnxruntime  # noqa: F401 - used conditionally in processing methods
import soundfile as sf
import torch
from onnx import load
from onnx2pytorch import ConvertModel
from PySide6.QtCore import QObject, QThread, Signal

import lib_v5.mdxnet as MdxnetSet
from demucs.apply import apply_model, demucs_segments
from demucs.pretrained import get_model
from demucs.utils import apply_model_v1, apply_model_v2
from lib_v5 import spec_utils

# from demucs.demucs import HDemucs
from lib_v5.tfc_tdf_v3 import STFT, TFC_TDF_net

# from lib_v5.vr_network.model_param_init import ModelParameters
from lib_v5.vr_network import nets, nets_new

from . import app_constants as ac
from .logger_utils import get_logger
from .model_data import ModelData
from .separate_demucs_logic import SeparateDemucsLogic
from .separate_logic_base import (
    clear_gpu_cache_logic,
    prepare_mix_logic,
    write_audio_logic,
)
from .separate_mdx_logic import SeparateMDXLogic
from .separate_mdxc_logic import SeparateMDXCLogic
from .separate_vr_logic import SeparateVRLogic

logger = get_logger(__name__)


class ProcessingWorker(QObject):
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)

    def __init__(self, settings_dict: Dict[str, Any]):
        super().__init__()
        self.settings_dict = settings_dict
        self.model_data = ModelData.from_settings_dict(settings_dict)
        self._is_running = True
        self.progress_value = 0
        self.progress_count = 0  # Track incremental progress steps
        self.total_progress_steps = 100  # Will be set based on processing type
        self.original_mix_audio: Optional[np.ndarray] = None

        # Multi-file progress tracking
        self._multi_file_context = {
            "total_files": 1,
            "current_file": 1,
            "file_progress_start": 0,
            "file_progress_range": 100,
            "is_multi_file": False,
        }

        # Initialize device based on model data settings
        self.device = "cpu"  # Default to CPU string

        try:
            self.model_data = ModelData.from_settings_dict(settings_dict)

            # Initialize device
            if (
                hasattr(self.model_data, "is_gpu_conversion")
                and self.model_data.is_gpu_conversion >= 0
            ):

                # Check for MPS first (Apple Silicon)
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self.device = "mps"
                # Then check for CUDA
                elif hasattr(torch, "cuda") and torch.cuda.is_available():
                    device_set = getattr(self.model_data, "device_set", "DEFAULT")
                    if device_set != "DEFAULT":
                        self.device = f"cuda:{device_set}"
                    else:
                        self.device = "cuda"

        except Exception as e:
            logger.error(f"Error creating ModelData: {e}\n{traceback.format_exc()}")
            self.model_data = None

    @property
    def settings(self):
        """Compatibility property for tests"""
        return self.settings_dict

    @property
    def device_torch(self):
        """Convert device string to PyTorch device object when needed"""
        return torch.device(self.device)

    def run(self):
        """Execute the audio processing task."""
        logger.info("ProcessingWorker started")

        # Debug log the relevant settings
        logger.info("=== SETTINGS DEBUG ===")
        logger.info(f"save_format: {self.settings.get('save_format', 'NOT SET')}")
        logger.info(
            f"is_primary_stem_only: {self.settings.get('is_primary_stem_only', 'NOT SET')}"
        )
        logger.info(
            f"is_secondary_stem_only: {self.settings.get('is_secondary_stem_only', 'NOT SET')}"
        )
        logger.info(
            f"is_primary_stem_only_Demucs: {self.settings.get('is_primary_stem_only_Demucs', 'NOT SET')}"
        )
        logger.info(
            f"is_secondary_stem_only_Demucs: {self.settings.get('is_secondary_stem_only_Demucs', 'NOT SET')}"
        )
        logger.info("=====================")

        try:
            # Initial progress (10%)
            self._emit_progress_update(10, "Loading model and preparing audio...")

            # Only create ModelData if it wasn't created in __init__
            if self.model_data is None:
                self.model_data = ModelData.from_settings_dict(self.settings_dict)

            logger.info(f"Model: {self.model_data.model_basename}")
            logger.info(f"Method: {self.model_data.process_method}")
            logger.info(f"Audio file: {self.model_data.audio_file}")
            logger.info(f"Device: {self.device}")
            logger.info(f"Is ensemble mode: {self.model_data.is_ensemble_mode}")
            logger.info(
                f"Is ensemble member: {getattr(self.model_data, 'is_ensemble_member', False)}"
            )
            if self.model_data.is_ensemble_mode:
                logger.info(
                    f"Ensemble models count: {len(getattr(self.model_data, 'ensemble_models', []))}"
                )
                logger.info(
                    f"Ensemble type: {getattr(self.model_data, 'ensemble_type', 'Unknown')}"
                )
                logger.info(
                    f"Ensemble primary stem: {getattr(self.model_data, 'ensemble_primary_stem', 'Unknown')}"
                )

            # Load and prepare audio (20%)
            self._emit_progress_update(20, "Loading audio file...")
            self.original_mix_audio = self._load_audio()
            if self.original_mix_audio is None:
                self.processing_finished.emit(False, "Failed to load audio file")
                return

            # Track processing success
            processing_success = True
            processing_message = "Processing completed successfully"

            # Process based on method - check ensemble mode first
            if self.model_data.is_ensemble_mode:
                # Ensemble processing handles its own completion signaling
                logger.info("🎯 Starting ensemble processing...")
                self._process_ensemble(self.original_mix_audio)
                return  # Don't emit completion signal here, ensemble handles it
            else:
                # Create the main process_data dictionary ONCE (25%)
                self._emit_progress_update(25, "Preparing processing data...")
                process_data = self._create_process_data(
                    input_audio_array_for_main_model=self.original_mix_audio
                )

                # Use the pipeline for ALL processing methods
                processing_success = self._execute_separation_pipeline(
                    self.model_data.process_method, process_data
                )

            # Only proceed with final completion if processing was successful
            if processing_success:
                # Final completion (100%)
                self._emit_progress_update(100, "Processing completed successfully!")
                self.processing_finished.emit(True, processing_message)
            # If processing failed, the individual method should have already emitted failure

        except Exception as e:
            logger.error(f"Processing error: {e}")
            logger.error(traceback.format_exc())
            self.processing_finished.emit(False, f"Processing failed: {str(e)}")
        finally:
            logger.info("ProcessingWorker finished")

    def _load_audio(self) -> Optional[np.ndarray]:
        """Load and prepare audio file for processing."""
        if (
            not self.model_data.audio_file
            or not Path(self.model_data.audio_file).exists()
        ):
            logger.error(f"Audio file not found: {self.model_data.audio_file}")
            return None

        try:
            audio_data = prepare_mix_logic(str(self.model_data.audio_file))
            if audio_data is None:
                logger.error("Failed to load audio data")
            return audio_data
        except Exception as e:
            logger.error(f"Error loading audio: {e}")
            return None

    def _execute_separation_pipeline(
        self, method_name: str, process_data_initial: Dict[str, Any]
    ) -> bool:
        if not self._is_running:
            return False

        primary_separator = self._get_separator_for_model(
            self.model_data, process_data_initial
        )
        if not primary_separator:
            self.processing_finished.emit(
                False,
                f"Could not create separator for primary model {self.model_data.model_name}",
            )
            return False

        # Start inference (30% base, will reach ~80% during inference)
        self._emit_progress_update(30, f"Running {method_name} inference...")
        primary_results = primary_separator.separate()
        if not self._is_running or not primary_results:
            if self._is_running:
                self.processing_finished.emit(
                    False,
                    f"{method_name} primary separation failed to produce results.",
                )
            return False

        current_stems = primary_results.copy()

        # After inference, we should be at ~80%
        # Secondary processing: 80-85% (dynamic based on number of secondary models)
        if (
            self.model_data.process_method == ac.DEMUCS_ARCH_TYPE
            and self.model_data.demucs_stems == ac.ALL_STEMS
            and self.model_data.is_demucs_4_stem_secondaries_activated
        ):
            demucs_stems_order = self.model_data.demucs_source_list
            total_secondary_models = len(
                [
                    m
                    for m in self.model_data.secondary_model_4_stem_instances
                    if m and m.model_name != ac.NO_MODEL
                ]
            )

            for i, stem_name_to_refine in enumerate(demucs_stems_order):
                if i >= len(self.model_data.secondary_model_4_stem_instances):
                    break
                if not self._is_running:
                    return False
                secondary_model_for_stem_obj = (
                    self.model_data.secondary_model_4_stem_instances[i]
                )

                if (
                    secondary_model_for_stem_obj
                    and secondary_model_for_stem_obj.model_name != ac.NO_MODEL
                ):
                    # Dynamic progress from 80% to 85% based on secondary model count
                    progress_val = 80 + int((i / max(total_secondary_models, 1)) * 5)
                    self._emit_progress_update(
                        progress_val,
                        f"Processing Demucs {stem_name_to_refine} with secondary: {secondary_model_for_stem_obj.model_basename}...",
                    )
                    input_audio_for_secondary = current_stems.get(stem_name_to_refine)
                    if input_audio_for_secondary is not None:
                        sec_proc_data = self._create_process_data_for_chained_model(
                            secondary_model_for_stem_obj,
                            input_audio_for_secondary,
                            for_demucs_sub_stem=stem_name_to_refine,
                        )
                        sec_separator = self._get_separator_for_model(
                            secondary_model_for_stem_obj, sec_proc_data
                        )
                        if sec_separator:
                            sec_results = sec_separator.separate()
                            if sec_results and self._is_running:
                                refined_stem_audio = sec_results.get(
                                    secondary_model_for_stem_obj.primary_stem
                                )
                                if refined_stem_audio is not None:
                                    scale = (
                                        self.model_data.secondary_model_4_stem_scales[i]
                                    )
                                    if scale is None:
                                        scale = 0.9
                                    blended_stem = (
                                        input_audio_for_secondary * (1 - scale)
                                    ) + (refined_stem_audio * scale)
                                    current_stems[stem_name_to_refine] = blended_stem
                                    primary_separator._write_stem(
                                        stem_name_to_refine,
                                        blended_stem,
                                        self.model_data.model_samplerate,
                                    )
                                    self._write_to_console(
                                        f"Applied secondary model to Demucs {stem_name_to_refine}.",
                                        "",
                                    )
                    else:
                        self._write_to_console(
                            f"Could not create separator for Demucs {stem_name_to_refine} secondary model.",
                            "",
                        )
        elif (
            self.model_data.secondary_model
            and self.model_data.is_secondary_model_chain_activated
        ):
            self._emit_progress_update(
                70,
                f"Processing with secondary model: {self.model_data.secondary_model.model_basename}...",
            )
            input_stem_name_for_secondary = self.model_data.primary_stem
            input_audio_for_secondary = current_stems.get(input_stem_name_for_secondary)
            if input_audio_for_secondary is not None:
                sec_model_data = self.model_data.secondary_model
                sec_process_data = self._create_process_data_for_chained_model(
                    sec_model_data, input_audio_for_secondary
                )
                sec_separator = self._get_separator_for_model(
                    sec_model_data, sec_process_data
                )
                if sec_separator:
                    sec_results = sec_separator.separate()
                    if sec_results and self._is_running:
                        scale = (
                            sec_model_data.secondary_model_chain_scale
                            if sec_model_data.secondary_model_chain_scale is not None
                            else 0.9
                        )
                        refined_primary_from_sec = sec_results.get(
                            sec_model_data.primary_stem
                        )
                        if refined_primary_from_sec is not None:
                            blended_stem = (input_audio_for_secondary * (1 - scale)) + (
                                refined_primary_from_sec * scale
                            )
                            current_stems[input_stem_name_for_secondary] = blended_stem
                            if (
                                self.original_mix_audio is not None
                                and blended_stem.shape == self.original_mix_audio.shape
                            ):
                                accompanying_stem_name = self.model_data.secondary_stem
                                current_stems[accompanying_stem_name] = (
                                    self.original_mix_audio - blended_stem
                                )
                                primary_separator._write_stem(
                                    input_stem_name_for_secondary,
                                    blended_stem,
                                    self.model_data.model_samplerate,
                                )
                                primary_separator._write_stem(
                                    accompanying_stem_name,
                                    current_stems[accompanying_stem_name],
                                    self.model_data.model_samplerate,
                                )
                                self._write_to_console(
                                    f"Applied secondary model, saved blended {input_stem_name_for_secondary} and recalculated {accompanying_stem_name}.",
                                    "",
                                )
                            else:
                                self._write_to_console(
                                    f"Could not recalculate/resave accompanying stem for {input_stem_name_for_secondary}.",
                                    "",
                                )
                        else:
                            self._write_to_console(
                                f"Secondary model did not output its target stem: {sec_model_data.primary_stem}.",
                                "",
                            )
                else:
                    self._write_to_console(
                        "Could not create separator for secondary model.", ""
                    )
            else:
                self._write_to_console(
                    f"Input stem '{input_stem_name_for_secondary}' for secondary model not found.",
                    "",
                )

        if not self._is_running:
            return False

        if (
            self.model_data.vocal_split_model
            and self.model_data.is_vocal_split_model_activated
        ):
            self._emit_progress_update(
                85,
                f"Processing with vocal splitter: {self.model_data.vocal_split_model.model_basename}...",
            )
            vocal_input_for_splitter = current_stems.get(ac.VOCAL_STEM)
            if vocal_input_for_splitter is not None:
                splitter_model_data = self.model_data.vocal_split_model
                splitter_process_data = self._create_process_data_for_chained_model(
                    splitter_model_data, vocal_input_for_splitter, is_vocal_split=True
                )
                splitter_separator = self._get_separator_for_model(
                    splitter_model_data, splitter_process_data
                )
                if splitter_separator:
                    splitter_results = splitter_separator.separate()
                    if (
                        splitter_results
                        and self.model_data.is_save_inst_vocal_splitter
                        and self._is_running
                    ):
                        lead_vocals_from_splitter = splitter_results.get(
                            ac.LEAD_VOCAL_STEM
                        )
                        if (
                            lead_vocals_from_splitter is not None
                            and lead_vocals_from_splitter.shape
                            == vocal_input_for_splitter.shape
                        ):
                            inst_from_splitter = (
                                vocal_input_for_splitter - lead_vocals_from_splitter
                            )
                            splitter_separator._write_stem(
                                f"{ac.INST_STEM}_(VocalSplitter)",
                                inst_from_splitter,
                                splitter_model_data.model_samplerate,
                            )
                        else:
                            self._write_to_console(
                                "Could not generate instrumental from vocal splitter.",
                                "",
                            )
                else:
                    self._write_to_console(
                        "Could not create separator for vocal splitter.", ""
                    )
            else:
                self._write_to_console("Vocal input for vocal splitter not found.", "")

        if self._is_running:
            self._emit_progress_update(85, "Finalizing processed stems...")

            # Save the primary results to disk
            if primary_results and primary_separator:
                total_stems = len(primary_results)
                saved_count = 0
                for stem_name, stem_audio in primary_results.items():
                    if stem_audio is not None and self._is_running:
                        try:
                            primary_separator._write_stem(
                                stem_name, stem_audio, self.model_data.model_samplerate
                            )
                            saved_count += 1
                            # Dynamic progress from 85% to 95% while saving stems
                            save_progress = 85 + int((saved_count / total_stems) * 10)
                            self._emit_progress_update(
                                save_progress, f"Saved {stem_name}"
                            )
                        except Exception as e:
                            logger.error(f"Failed to write {stem_name}: {e}")
                            self._write_to_console(f"Error saving {stem_name}: {e}", "")

            # File saving complete - ready for final completion in main run() method
            return True

        return False

    def _create_process_data(
        self, input_audio_array_for_main_model: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        return {
            "audio_file": (
                self.model_data.audio_file
                if input_audio_array_for_main_model is None
                else None
            ),
            "input_audio_array": input_audio_array_for_main_model,
            "audio_file_base": (
                Path(self.model_data.audio_file).stem
                if self.model_data.audio_file
                else "output"
            ),
            "export_path": self.model_data.export_path,
            "set_progress_bar": self._set_progress_bar_callback,
            "write_to_console": self._write_to_console,
            "cached_source_callback": self._cached_source_callback,
            "cached_model_source_holder": self._cached_model_source_holder,
            "is_4_stem_ensemble": self.model_data.is_4_stem_ensemble,
            "list_all_models": [self.model_data.model_basename],
            "process_iteration": self._process_iteration,
            "_is_running_check": lambda: self._is_running,
            "is_ensemble_master": False,
        }

    def _create_process_data_for_chained_model(
        self,
        chained_model: "ModelData",
        input_audio: np.ndarray,
        for_demucs_sub_stem: Optional[str] = None,
        is_vocal_split: bool = False,
    ) -> Dict[str, Any]:
        """
        Create process data dictionary for chained/secondary model processing.

        This method creates the necessary process data structure for secondary models,
        vocal splitters, and Demucs 4-stem processing. Unlike the main process data,
        this uses input audio arrays instead of file paths and creates combined
        model names for proper output file naming.

        Args:
            chained_model: The secondary/chained model data object
            input_audio: The input audio array from the primary model processing
            for_demucs_sub_stem: Optional stem name for Demucs 4-stem processing
            is_vocal_split: Whether this is for vocal splitter processing

        Returns:
            Dict[str, Any]: Process data dictionary for the chained model
        """
        # Create combined model name for audio_file_base
        if for_demucs_sub_stem:
            # For Demucs 4-stem processing: "MainModel_DemucsModel_SubStem"
            combined_name = f"{self.model_data.model_basename}_{chained_model.model_basename}_{for_demucs_sub_stem}"
        elif is_vocal_split:
            # For vocal splitter: "MainModel_VocalSplitter"
            combined_name = (
                f"{self.model_data.model_basename}_{chained_model.model_basename}"
            )
        else:
            # For standard secondary model: "MainModel_SecondaryModel"
            combined_name = (
                f"{self.model_data.model_basename}_{chained_model.model_basename}"
            )

        return {
            "audio_file": None,  # No file path for chained processing
            "input_audio_array": input_audio,  # Use the audio array from previous processing
            "audio_file_base": combined_name,  # Combined model names
            "export_path": chained_model.export_path,
            "set_progress_bar": self._set_progress_bar_callback,
            "write_to_console": self._write_to_console,
            "cached_source_callback": self._cached_source_callback,
            "cached_model_source_holder": self._cached_model_source_holder,
            "is_4_stem_ensemble": False,  # Chained models are not ensemble masters
            "list_all_models": [
                self.model_data.model_basename,
                chained_model.model_basename,
            ],
            "process_iteration": self._process_iteration,
            "_is_running_check": lambda: self._is_running,
            "is_ensemble_master": False,  # Chained models are never ensemble masters
        }

    def _set_progress_bar_callback(
        self, current_step_fraction: float, message: Optional[str] = None
    ):
        """Update progress: 5% start, 10-80% processing, 95% complete.

        Ensures monotonous progress (only increments, never decreases).
        """
        if not self._is_running:
            return

        # Calculate new progress
        if current_step_fraction <= 0.05:
            # Initial progress (0-5%)
            new_progress = int(current_step_fraction * 100)
        elif current_step_fraction >= 0.95:
            # Final completion (95-100%)
            new_progress = int(current_step_fraction * 100)
        else:
            # Incremental processing progress (10-80%)
            # This matches the pattern: 0.1 + (0.8/length * progress_value)
            self.progress_count += 1
            base_progress = 10  # Start at 10%
            processing_range = 70  # 80% - 10% = 70% range for processing

            # Calculate progress within the processing window
            if self.total_progress_steps > 0:
                processing_progress = min(
                    (self.progress_count / self.total_progress_steps)
                    * processing_range,
                    processing_range,
                )
            else:
                processing_progress = current_step_fraction * processing_range

            new_progress = int(base_progress + processing_progress)

        # Ensure progress is within bounds
        new_progress = min(max(new_progress, 0), 100)

        # MONOTONOUS CONSTRAINT: Only allow progress to increase, never decrease
        if new_progress > self.progress_value:
            self.progress_value = new_progress
        # If new_progress <= self.progress_value, keep current value (don't go backwards)

        # Format message
        if not message:
            if self.progress_value < 10:
                message = "Initializing..."
            elif self.progress_value >= 95:
                message = "Finalizing..."
            else:
                message = "Processing..."

        self.progress_updated.emit(self.progress_value, message)

    def _setup_multi_file_progress(self, total_files: int, base_message: str):
        """Setup progress tracking for multi-file operations (like Demucs models)."""
        self._multi_file_context = {
            "total_files": total_files,
            "current_file": 1,
            "file_progress_start": 0,
            "file_progress_range": 100 // total_files if total_files > 1 else 100,
            "is_multi_file": total_files > 1,
            "base_message": base_message,
        }
        logger.info(
            f"Setup multi-file progress: {total_files} files, {self._multi_file_context['file_progress_range']}% per file"
        )

    def _start_file_progress(self, file_number: int, file_name: str = ""):
        """Start progress tracking for a specific file in multi-file operation."""
        if self._multi_file_context["is_multi_file"]:
            self._multi_file_context["current_file"] = file_number
            self._multi_file_context["file_progress_start"] = (
                file_number - 1
            ) * self._multi_file_context["file_progress_range"]

            # Create message : "Downloading Item X/Y..."
            base_msg = self._multi_file_context.get("base_message", "Processing")
            file_msg = (
                f"{base_msg} {file_number}/{self._multi_file_context['total_files']}"
            )
            if file_name:
                file_msg += f" ({file_name})"
            file_msg += "..."

            start_progress = self._multi_file_context["file_progress_start"]
            self._emit_progress_update(start_progress, file_msg)
            logger.info(
                f"Started file {file_number}/{self._multi_file_context['total_files']}: {file_name}"
            )

    def _emit_file_progress_update(self, file_progress: int, message: str = ""):
        """Emit progress for current file, mapping to overall progress range."""
        if not self._is_running:
            return

        if self._multi_file_context["is_multi_file"]:
            # Map file progress (0-100) to the allocated range for this file
            file_range = self._multi_file_context["file_progress_range"]
            file_start = self._multi_file_context["file_progress_start"]
            overall_progress = file_start + int((file_progress / 100) * file_range)

            # Create contextual message
            if not message:
                current_file = self._multi_file_context["current_file"]
                total_files = self._multi_file_context["total_files"]
                base_msg = self._multi_file_context.get("base_message", "Processing")
                message = f"{base_msg} {current_file}/{total_files}... {file_progress}%"
        else:
            # Single file - use progress directly
            overall_progress = file_progress

        self._emit_progress_update(overall_progress, message)

    def _emit_progress_update(self, new_progress: int, message: str):
        """Emit progress update ensuring monotonous progression (only increments)."""
        if not self._is_running:
            return

        # Ensure progress is within bounds
        new_progress = min(max(new_progress, 0), 100)

        # MONOTONOUS CONSTRAINT: Only allow progress to increase, never decrease
        if new_progress > self.progress_value:
            self.progress_value = new_progress
        # If new_progress <= self.progress_value, keep current value (don't go backwards)

        self.progress_updated.emit(self.progress_value, message)

    def _write_to_console(self, message: str, base_text: str = ""):
        """Write console message without changing progress value (maintains monotonous progress)."""
        if not self._is_running:
            return
        full_message = f"{base_text}{message}" if base_text else message
        # Only emit message update, don't change progress value
        self.progress_updated.emit(self.progress_value, full_message)

    def _cached_source_callback(self, process_method: str, model_name: str = None):
        return None, None

    def _cached_model_source_holder(
        self, process_method: str, sources, model_name: str = None
    ):
        pass

    def _process_iteration(self):
        pass

    def _process_vr_arch(self, process_data: Dict[str, Any]) -> bool:
        """Process using VR (Vocal Remover) architecture"""
        self._write_to_console(
            f"Loading VR model: {self.model_data.model_basename}", ""
        )

        # Initialize device
        device = self.device_torch

        # Determine model architecture based on file size
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
        vr_5_1_models = [56817, 218409]
        model_size = math.ceil(os.stat(self.model_data.model_path).st_size / 1024)
        nn_arch_size = min(nn_arch_sizes, key=lambda x: abs(x - model_size))

        # Load model
        if nn_arch_size in vr_5_1_models or self.model_data.is_vr_51_model:
            model_run = nets_new.CascadedNet(
                self.model_data.vr_model_param.param["bins"] * 2,
                nn_arch_size,
                nout=self.model_data.model_capacity[0],
                nout_lstm=self.model_data.model_capacity[1],
            )
            is_vr_51_model = True
        else:
            model_run = nets.determine_model_capacity(
                self.model_data.vr_model_param.param["bins"] * 2, nn_arch_size
            )
            is_vr_51_model = False

        model_run.load_state_dict(
            torch.load(
                self.model_data.model_path, map_location="cpu", weights_only=False
            )
        )
        model_run.to(device)
        model_run.eval()

        self._write_to_console("Running VR inference...", "")

        # Load and prepare audio mix
        X_spec = self._loading_mix_vr()
        if X_spec is None:
            self.processing_finished.emit(
                False, "Failed to load audio for VR processing"
            )
            return False

        # Run inference
        y_spec, v_spec = self._inference_vr(X_spec, device, model_run, is_vr_51_model)

        if y_spec is None or v_spec is None:
            self.processing_finished.emit(False, "VR inference failed")
            return False

        # Convert to audio and save
        primary_audio = self._spec_to_wav_vr(y_spec, is_vr_51_model).T
        secondary_audio = self._spec_to_wav_vr(v_spec, is_vr_51_model).T

        # Resample if needed
        if self.model_data.model_samplerate != 44100:
            primary_audio = librosa.resample(
                primary_audio.T,
                orig_sr=self.model_data.model_samplerate,
                target_sr=44100,
            ).T
            secondary_audio = librosa.resample(
                secondary_audio.T,
                orig_sr=self.model_data.model_samplerate,
                target_sr=44100,
            ).T

        # Save results
        if not self.model_data.is_secondary_stem_only:
            primary_path = os.path.join(
                self.model_data.export_path,
                f"{Path(self.model_data.audio_file).stem}_({self.model_data.primary_stem}).wav",
            )
            self._write_stem_file(
                primary_path, primary_audio, self.model_data.primary_stem
            )

        if not self.model_data.is_primary_stem_only:
            secondary_path = os.path.join(
                self.model_data.export_path,
                f"{Path(self.model_data.audio_file).stem}_({self.model_data.secondary_stem}).wav",
            )
            self._write_stem_file(
                secondary_path, secondary_audio, self.model_data.secondary_stem
            )

        del model_run
        if hasattr(torch.cuda, "empty_cache"):
            torch.cuda.empty_cache()

        return True

    def _process_mdx_net(self, process_data: Dict[str, Any]) -> bool:
        """Process using MDX architecture"""
        if self.model_data.is_mdx_c:
            return self._process_mdx_c()
        else:
            return self._process_mdx_regular()

    def _process_mdx_regular(self) -> bool:
        """Process using regular MDX"""
        self._write_to_console(
            f"Loading MDX model: {self.model_data.model_basename}", ""
        )

        # Load model
        if self.model_data.is_mdx_ckpt:
            model_params = torch.load(
                self.model_data.model_path, map_location=lambda storage, loc: storage
            )["hyper_parameters"]
            dim_c, hop_length = model_params["dim_c"], model_params["hop_length"]
            separator = MdxnetSet.ConvTDFNet(**model_params)
            model_run = (
                separator.load_from_checkpoint(self.model_data.model_path)
                .to(self.device_torch)
                .eval()
            )
        else:
            dim_c, hop_length = 4, 1024
            if (
                self.model_data.mdx_segment_size == self.model_data.mdx_dim_t_set
                and self.device != "mps"
            ):
                providers = (
                    ["CUDAExecutionProvider", "CPUExecutionProvider"]
                    if self.device.startswith("cuda")
                    else ["CPUExecutionProvider"]
                )
                ort_session = onnxruntime.InferenceSession(
                    self.model_data.model_path, providers=providers
                )

                def model_run(spek):
                    return ort_session.run(None, {"input": spek.cpu().numpy()})[0]

            else:
                model_run = ConvertModel(load(self.model_data.model_path))
                model_run.to(self.device_torch).eval()

        # Load audio
        mix = prepare_mix_logic(self.model_data.audio_file)
        if mix is None:
            self.processing_finished.emit(
                False, "Failed to load audio for MDX processing"
            )
            return False

        # Ensure correct audio format for MDX processing
        if mix.ndim == 1:
            # Convert mono to stereo: (N,) -> (2, N)
            mix = np.asfortranarray([mix, mix])
        elif mix.ndim == 2:
            if mix.shape[0] > mix.shape[1]:
                # If shape is (N, 2), transpose to (2, N)
                mix = mix.T
            # If already (2, N), keep as is

        self._write_to_console(f"Audio shape for MDX processing: {mix.shape}", "")

        self._write_to_console("Running MDX demixing...", "")

        # Run separation
        source = self._demix_mdx(mix, model_run, hop_length, dim_c)
        if source is None:
            self.processing_finished.emit(False, "MDX demixing failed")
            return False

        # Process results and save
        if not self.model_data.is_secondary_stem_only:
            primary_path = os.path.join(
                self.model_data.export_path,
                f"{Path(self.model_data.audio_file).stem}_({self.model_data.primary_stem}).wav",
            )
            primary_audio = source.T
            self._write_stem_file(
                primary_path, primary_audio, self.model_data.primary_stem
            )

        if not self.model_data.is_primary_stem_only:
            secondary_path = os.path.join(
                self.model_data.export_path,
                f"{Path(self.model_data.audio_file).stem}_({self.model_data.secondary_stem}).wav",
            )
            raw_mix = mix.T if hasattr(mix, "T") else mix
            if self.model_data.is_invert_spec:

                secondary_audio = spec_utils.invert_stem(raw_mix, source.T)
            else:
                secondary_audio = raw_mix - source.T
            self._write_stem_file(
                secondary_path, secondary_audio, self.model_data.secondary_stem
            )

        if hasattr(torch.cuda, "empty_cache"):
            torch.cuda.empty_cache()

        return True

    def _process_mdx_c(self) -> bool:
        """Process using MDX-C"""
        self._write_to_console(
            f"Loading MDX-C model: {self.model_data.model_basename}", ""
        )

        # Load model
        model = TFC_TDF_net(self.model_data.mdx_c_configs, device=self.device_torch)
        model.load_state_dict(
            torch.load(
                self.model_data.model_path, map_location="cpu", weights_only=False
            )
        )
        model.to(self.device_torch).eval()

        # Load audio
        mix = prepare_mix_logic(self.model_data.audio_file)
        if mix is None:
            self.processing_finished.emit(
                False, "Failed to load audio for MDX-C processing"
            )
            return False

        # Ensure correct audio format for MDX-C processing - should be (2, N)
        if mix.ndim == 1:
            # Convert mono to stereo: (N,) -> (2, N)
            mix = np.asfortranarray([mix, mix])
        elif mix.ndim == 2:
            if mix.shape[0] > mix.shape[1]:
                # If shape is (N, 2), transpose to (2, N)
                mix = mix.T
            # If already (2, N), keep as is

        self._write_to_console(f"Audio shape for MDX-C processing: {mix.shape}", "")

        self._write_to_console("Running MDX-C demixing...", "")

        # Run separation
        sources = self._demix_mdx_c(mix, model)
        if sources is None:
            self.processing_finished.emit(False, "MDX-C demixing failed")
            return False

        # Save results
        stem_list = (
            [self.model_data.mdx_c_configs.training.target_instrument]
            if self.model_data.mdx_c_configs.training.target_instrument
            else [i for i in self.model_data.mdx_c_configs.training.instruments]
        )

        if len(stem_list) == 1:
            source_primary = sources
        else:
            # Handle stem selection for multi-stem models
            if isinstance(sources, dict):
                # Log available stems for debugging
                self._write_to_console(f"Available stems: {list(sources.keys())}", "")
                self._write_to_console(
                    f"Requested stem: {self.model_data.mdxnet_stem_select}", ""
                )

                # Handle special cases
                if (
                    self.model_data.mdxnet_stem_select == "All Stems"
                    or self.model_data.mdxnet_stem_select not in sources
                ):
                    # If 'All Stems' or invalid selection, use the primary stem (usually vocals)
                    # Try common primary stem names in order of preference
                    primary_stem_candidates = [
                        self.model_data.primary_stem,
                        "vocals",
                        "vocal",
                        "Vocals",
                        "Vocal",
                    ]
                    source_primary = None

                    for candidate in primary_stem_candidates:
                        if candidate in sources:
                            source_primary = sources[candidate]
                            self._write_to_console(
                                f"Using primary stem: {candidate}", ""
                            )
                            break

                    # If no primary stem found, use the first available stem
                    if source_primary is None and sources:
                        first_stem = list(sources.keys())[0]
                        source_primary = sources[first_stem]
                        self._write_to_console(
                            f"Using first available stem: {first_stem}", ""
                        )
                    elif source_primary is None:
                        self.processing_finished.emit(
                            False, "No stems found in MDX-C output"
                        )
                        return False
                else:
                    # Use the specifically requested stem
                    source_primary = sources[self.model_data.mdxnet_stem_select]
            else:
                source_primary = sources

        if not self.model_data.is_secondary_stem_only:
            primary_path = os.path.join(
                self.model_data.export_path,
                f"{Path(self.model_data.audio_file).stem}_({self.model_data.primary_stem}).wav",
            )
            primary_audio = (
                source_primary.T if hasattr(source_primary, "T") else source_primary
            )
            self._write_stem_file(
                primary_path, primary_audio, self.model_data.primary_stem
            )

        if not self.model_data.is_primary_stem_only:
            secondary_path = os.path.join(
                self.model_data.export_path,
                f"{Path(self.model_data.audio_file).stem}_({self.model_data.secondary_stem}).wav",
            )
            if isinstance(sources, dict) and len(stem_list) >= 2:
                secondary_audio = sources[self.model_data.secondary_stem].T
            else:
                raw_mix = mix.T if hasattr(mix, "T") else mix
                if self.model_data.is_invert_spec:
                    secondary_audio = spec_utils.invert_stem(raw_mix, primary_audio)
                else:
                    secondary_audio = raw_mix - primary_audio
            self._write_stem_file(
                secondary_path, secondary_audio, self.model_data.secondary_stem
            )

        del model
        if hasattr(torch.cuda, "empty_cache"):
            torch.cuda.empty_cache()

        return True

    def _process_demucs(self, process_data: Dict[str, Any]) -> bool:
        logger.info("Starting Demucs processing")
        logger.info(f"Model path: {self.model_data.model_path}")
        logger.info(f"Model basename: {self.model_data.model_basename}")
        logger.info(f"Demucs version: {self.model_data.demucs_version}")
        logger.info(f"Demucs stems: {self.model_data.demucs_stems}")
        logger.info(f"Demucs source list: {self.model_data.demucs_source_list}")

        # Check if model file exists
        if self.model_data.model_path:
            model_path = Path(self.model_data.model_path)
            if model_path.exists():
                logger.info(f"Model file exists: {model_path}")
                logger.info(f"Model file size: {model_path.stat().st_size} bytes")
            else:
                logger.info(f"Model file does not exist: {model_path}")

            # Check parent directory
            model_dir = model_path.parent
            if model_dir.exists():
                logger.info(f"Model directory exists: {model_dir}")
                logger.info("Files in model directory:")
                for file in model_dir.iterdir():
                    logger.info(f"  - {file.name}")
            else:
                logger.info(f"Model directory does not exist: {model_dir}")

        return self._execute_separation_pipeline(ac.DEMUCS_ARCH_TYPE, process_data)

    def _align_spectrograms(
        self, spec_list: List[np.ndarray]
    ) -> Optional[List[np.ndarray]]:
        """Aligns a list of spectograms to a common shape by padding/trimming the time axis."""
        if not spec_list:
            return None

        # Assuming all specs have same number of channels and frequency bins
        # This should be ensured by consistent STFT params during their creation
        ref_channels, ref_freq_bins, _ = spec_list[0].shape
        max_time_frames = max(s.shape[2] for s in spec_list)

        aligned_specs = []
        for spec_to_align in spec_list:
            if (
                spec_to_align.shape[0] != ref_channels
                or spec_to_align.shape[1] != ref_freq_bins
            ):
                self._write_to_console(
                    "Warning: Spectrogram channel/frequency mismatch during alignment. Skipping.",
                    "",
                )
                return None  # Critical mismatch

            if spec_to_align.shape[2] < max_time_frames:
                padding_time = max_time_frames - spec_to_align.shape[2]
                padding = [(0, 0)] * spec_to_align.ndim
                padding[2] = (0, padding_time)
                aligned_spec = np.pad(spec_to_align, padding, mode="constant")
            elif spec_to_align.shape[2] > max_time_frames:
                aligned_spec = spec_to_align[:, :, :max_time_frames]
            else:
                aligned_spec = spec_to_align
            aligned_specs.append(aligned_spec)

        return aligned_specs

    def _process_ensemble(self, initial_input_audio: np.ndarray):
        self._write_to_console("====== STARTING ENSEMBLE PROCESSING ======", "")
        if not self.model_data or not self.model_data.ensemble_models:
            self.processing_finished.emit(
                False, "Ensemble not configured or no models in ensemble."
            )
            return

        # Check minimum models for ensemble
        num_models = len(self.model_data.ensemble_models)
        if num_models < 2:
            error_msg = f"Ensemble requires at least 2 models, but only {num_models} model(s) selected"
            if num_models == 1:
                error_msg += f": '{self.model_data.ensemble_models[0].model_basename}'"
            self._write_to_console(f"❌ {error_msg}", "")
            self.processing_finished.emit(False, f"Ensemble failed: {error_msg}")
            return

        self._emit_progress_update(
            10, f"Starting Ensemble: {self.model_data.model_basename}..."
        )
        self._write_to_console(f"Starting ensemble with {num_models} models", "")

        # Get the primary and secondary stems for this ensemble
        ensemble_primary_stem = getattr(self.model_data, "ensemble_primary_stem", ac.VOCAL_STEM)
        ensemble_secondary_stem = getattr(
            self.model_data, "ensemble_secondary_stem", ac.INST_STEM
        )

        # Check the actual stem-only settings from the master model_data
        is_primary_stem_only = getattr(self.model_data, "is_primary_stem_only", False)
        is_secondary_stem_only = getattr(
            self.model_data, "is_secondary_stem_only", False
        )

        # Determine the actual target stem based on user selection
        # When user selects "instrumental only", we want instrumental as the main target
        if is_secondary_stem_only and not is_primary_stem_only:
            # User wants secondary stem only (e.g., instrumental only)
            primary_stem = ensemble_secondary_stem  # Make instrumental the primary target
            secondary_stem = ensemble_primary_stem
            self._write_to_console(f"🎯 Adjusted for secondary-stem-only: target={primary_stem}", "")
        elif is_primary_stem_only and not is_secondary_stem_only:
            # User wants primary stem only (e.g., vocals only)
            primary_stem = ensemble_primary_stem
            secondary_stem = ensemble_secondary_stem
            self._write_to_console(f"🎯 Using primary-stem-only: target={primary_stem}", "")
        else:
            # User wants both stems or default behavior
            primary_stem = ensemble_primary_stem
            secondary_stem = ensemble_secondary_stem
            self._write_to_console(f"🎯 Using standard stem assignment", "")

        self._write_to_console(f"🎯 Ensemble primary stem: {primary_stem}", "")
        self._write_to_console(f"🎯 Ensemble secondary stem: {secondary_stem}", "")

        self._write_to_console(f"🎯 Primary stem only: {is_primary_stem_only}", "")
        self._write_to_console(f"🎯 Secondary stem only: {is_secondary_stem_only}", "")

        # Determine what stems to process based on ensemble settings
        stems_to_process = []

        # If not is_secondary_stem_only, process primary; if not is_primary_stem_only, process secondary
        if not is_secondary_stem_only:
            stems_to_process.append(primary_stem)
            self._write_to_console(f"  ✓ Will process primary stem: {primary_stem}", "")
        if not is_primary_stem_only:
            stems_to_process.append(secondary_stem)
            self._write_to_console(
                f"  ✓ Will process secondary stem: {secondary_stem}", ""
            )

        if not stems_to_process:
            self.processing_finished.emit(
                False, "No stems to process based on ensemble settings"
            )
            return

        self._write_to_console(f"🎯 Stems to process: {stems_to_process}", "")

        # Store all outputs from ensemble models grouped by stem
        all_outputs_by_stem: Dict[str, List[np.ndarray]] = {}
        all_saved_files_by_stem: Dict[str, List[str]] = (
            {}
        )  # Track saved file paths for ensemble combination
        for stem in stems_to_process:
            all_outputs_by_stem[stem] = []
            all_saved_files_by_stem[stem] = []

        ensemble_output_base = (
            Path(self.model_data.audio_file).stem
            if self.model_data.audio_file
            else "ensemble_output"
        )

        # Check if we should save all individual outputs (equivalent to is_save_all_outputs_ensemble_var)
        # Get from settings - this setting now comes from the Additional Settings tab
        save_all_outputs = getattr(
            self.model_data, "is_save_all_outputs_ensemble", True
        )

        # Also check settings from the comprehensive settings system
        if hasattr(self.model_data, "additional_settings"):
            settings = self.model_data.additional_settings
            save_all_outputs = settings.get(
                "is_save_all_outputs_ensemble", save_all_outputs
            )

            # Apply other ensemble settings
            use_wav_ensemble = settings.get("is_wav_ensemble", False)
            algorithm = settings.get("choose_algorithm", "Average")
            normalization = settings.get("is_normalization", False)

            self._write_to_console(
                f"🎯 Using settings: save_all={save_all_outputs}, algorithm={algorithm}, normalize={normalization}",
                "",
            )

        self._write_to_console(
            f"🎯 Save all individual outputs: {save_all_outputs}", ""
        )

        # Process each model in the ensemble
        successful_models = 0
        for i, member_model_data in enumerate(self.model_data.ensemble_models):
            if not self._is_running:
                return
            self._emit_progress_update(
                15 + int(i / num_models * 60),
                f"Ensemble: Processing model {i+1}/{num_models} ({member_model_data.model_basename})...",
            )

            # Process individual model directly
            member_results = self._process_individual_model(
                member_model_data, initial_input_audio
            )

            if member_results and self._is_running:
                successful_models += 1
                self._write_to_console(
                    f"✓ {member_model_data.model_basename} completed successfully", ""
                )
                self._write_to_console(
                    f"  Produced stems: {list(member_results.keys())}", ""
                )

                # Save individual model outputs:
                # - Only save individual files for stems that are part of the ensemble (stems_to_process)
                # - If save_all_outputs=True: keep these individual files after ensemble creation
                # - If save_all_outputs=False: delete these individual files after ensemble creation
                for stem_name, stem_audio in member_results.items():
                    if stem_audio is not None and stem_audio.size > 0:
                        self._write_to_console(
                            f"  {stem_name} shape: {stem_audio.shape}", ""
                        )

                        # Only save and process stems that are part of the ensemble
                        if stem_name in stems_to_process:
                            # Store for ensemble combination
                            all_outputs_by_stem[stem_name].append(stem_audio)
                            
                            # Save individual file (will be kept or deleted later based on save_all_outputs)
                            # Use the same format as the ensemble output
                            save_format = getattr(self.model_data, "save_format", "WAV").upper()
                            file_ext = save_format.lower()
                            
                            cleaned_model_name = self._clean_model_name_for_filename(
                                member_model_data.model_basename
                            )
                            individual_output_filename = f"{ensemble_output_base}_{cleaned_model_name}_({stem_name}).{file_ext}"
                            individual_output_path = (
                                Path(self.model_data.export_path)
                                / individual_output_filename
                            )

                            try:
                                # Ensure proper audio format for writing
                                if stem_audio.ndim == 1:
                                    stem_audio_to_save = np.column_stack(
                                        [stem_audio, stem_audio]
                                    )
                                elif stem_audio.ndim == 2:
                                    if stem_audio.shape[0] == 2:
                                        stem_audio_to_save = stem_audio.T
                                    else:
                                        stem_audio_to_save = stem_audio
                                else:
                                    self._write_to_console(
                                        f"❌ Invalid audio dimensions for {stem_name}: {stem_audio.shape}",
                                        "",
                                    )
                                    continue

                                # Save individual output
                                sf.write(
                                    str(individual_output_path),
                                    stem_audio_to_save,
                                    44100,
                                )

                                # Track saved files for potential cleanup
                                all_saved_files_by_stem[stem_name].append(
                                    str(individual_output_path)
                                )

                                self._write_to_console(
                                    f"  💾 Saved for ensemble: {individual_output_filename}",
                                    "",
                                )

                            except Exception as save_error:
                                self._write_to_console(
                                    f"❌ Error saving individual output {individual_output_filename}: {save_error}",
                                    "",
                                )
                            
                            self._write_to_console(
                                f"  ✓ Added {stem_name} to ensemble collection", ""
                            )
                        else:
                            self._write_to_console(
                                f"  ℹ️ {stem_name} not needed for ensemble (stems_to_process: {stems_to_process}) - skipping", ""
                            )
                    else:
                        self._write_to_console(
                            f"  {stem_name} is None or empty, skipping", ""
                        )
            elif self._is_running:
                self._write_to_console(
                    f"❌ {member_model_data.model_basename} failed to produce results",
                    "",
                )

            if clear_gpu_cache_logic:
                clear_gpu_cache_logic()

        if not self._is_running:
            return

        # Check if we have enough successful models
        if successful_models < 2:
            error_msg = f"Ensemble requires at least 2 successful models, but only {successful_models} out of {num_models} models produced results"
            self._write_to_console(f"❌ {error_msg}", "")
            self.processing_finished.emit(False, f"Ensemble failed: {error_msg}")
            return

        # Check if any stems have valid outputs
        valid_stems = [
            stem for stem in stems_to_process if len(all_outputs_by_stem[stem]) >= 2
        ]
        if not valid_stems:
            self.processing_finished.emit(
                False,
                "Ensemble processing failed: No stems have enough model outputs for ensembling.",
            )
            return

        self._emit_progress_update(90, "Combining ensemble results...")

        # Process each stem with valid outputs
        stems_saved = 0
        for stem_name in valid_stems:
            if not self._is_running:
                return

            stem_outputs = all_outputs_by_stem[stem_name]
            self._write_to_console(
                f"Processing stem: {stem_name} with {len(stem_outputs)} outputs", ""
            )

            if len(stem_outputs) < 2:
                self._write_to_console(
                    f"⚠️ Only {len(stem_outputs)} outputs for {stem_name}, need at least 2 for ensemble - skipping",
                    "",
                )
                continue

            # Determine algorithm for this stem
            ensemble_algorithm = self.model_data.ensemble_type
            if "/" in ensemble_algorithm:
                # Primary/Secondary algorithm pair like "Max Spec/Min Spec"
                primary_alg, secondary_alg = ensemble_algorithm.split("/", 1)
                if stem_name == primary_stem:
                    algorithm_for_stem = primary_alg.strip()
                else:
                    algorithm_for_stem = secondary_alg.strip()
            else:
                # Single algorithm for all stems
                algorithm_for_stem = ensemble_algorithm

            self._write_to_console(
                f"  Using algorithm '{algorithm_for_stem}' for {stem_name}", ""
            )

            # Apply ensemble algorithm
            ensembled_audio = self._combine_ensemble_outputs(
                stem_outputs, algorithm_for_stem
            )

            if ensembled_audio is not None and ensembled_audio.size > 0:
                self._write_to_console(
                    f"✓ Successfully ensembled {stem_name} - shape: {ensembled_audio.shape}",
                    "",
                )

                # Save the ensembled result
                try:
                    samplerate_to_save = 44100

                    # Ensure proper audio format for writing
                    if ensembled_audio.ndim == 1:
                        ensembled_audio_final = np.column_stack(
                            [ensembled_audio, ensembled_audio]
                        )
                    elif ensembled_audio.ndim == 2:
                        if ensembled_audio.shape[0] == 2:
                            ensembled_audio_final = ensembled_audio.T
                        else:
                            ensembled_audio_final = ensembled_audio
                    else:
                        self._write_to_console(
                            f"❌ Invalid audio dimensions: {ensembled_audio.shape}", ""
                        )
                        continue

                    # Save ensemble output with clear naming
                    save_format = getattr(self.model_data, "save_format", "WAV").upper()
                    file_ext = save_format.lower()

                    ensemble_output_filename = (
                        f"{ensemble_output_base}_Ensemble_({stem_name}).{file_ext}"
                    )
                    ensemble_output_path = (
                        Path(self.model_data.export_path) / ensemble_output_filename
                    )

                    self._write_to_console(
                        f"Saving ensemble {stem_name} to: {ensemble_output_filename}",
                        "",
                    )

                    # Save the ensemble result
                    sf.write(
                        str(ensemble_output_path),
                        ensembled_audio_final,
                        samplerate_to_save,
                    )

                    stems_saved += 1
                    self._write_to_console(
                        f"✓ Saved ensemble {stem_name} successfully", ""
                    )

                    # Clean up individual files if not saving all outputs
                    # Only clean up files that were part of the ensemble combination
                    if not save_all_outputs:
                        for individual_file in all_saved_files_by_stem[stem_name]:
                            try:
                                Path(individual_file).unlink()
                                self._write_to_console(
                                    f"  🗑️ Cleaned up ensemble source: {Path(individual_file).name}", ""
                                )
                            except Exception:
                                pass

                except Exception as save_error:
                    self._write_to_console(
                        f"❌ Error saving ensemble {stem_name}: {save_error}", ""
                    )
                    self._write_to_console(
                        f"❌ Save traceback: {traceback.format_exc()}", ""
                    )
            else:
                self._write_to_console(
                    f"❌ Ensemble combination failed for {stem_name}", ""
                )

        # Final completion
        if stems_saved > 0:
            self._emit_progress_update(100, "Ensemble processing complete!")
            success_msg = f"Ensemble processing completed successfully. Saved {stems_saved} ensemble stem(s)"
            if save_all_outputs:
                total_individual_files = sum(
                    len(files) for files in all_saved_files_by_stem.values()
                )
                success_msg += (
                    f" plus {total_individual_files} individual model outputs"
                )
            self.processing_finished.emit(True, success_msg)
        else:
            self.processing_finished.emit(
                False, "Ensemble processing failed: No stems were saved successfully."
            )

    def _process_individual_model(
        self, model_data: ModelData, input_audio: np.ndarray
    ) -> Optional[Dict[str, np.ndarray]]:
        """Process a single model and return its results"""
        try:
            self._write_to_console(
                f"🔄 Processing model: {model_data.model_basename}", ""
            )
            self._write_to_console(f"  Method: {model_data.process_method}", "")
            self._write_to_console(f"  Model path: {model_data.model_path}", "")
            self._write_to_console(f"  Model status: {model_data.model_status}", "")
            self._write_to_console(f"  Input audio shape: {input_audio.shape}", "")

            # Check model status first
            if not model_data.model_status:
                self._write_to_console(
                    f"❌ Model {model_data.model_basename} has invalid status", ""
                )
                return None

            # Check model path exists
            if not model_data.model_path or not Path(model_data.model_path).exists():
                self._write_to_console(
                    f"❌ Model file not found: {model_data.model_path}", ""
                )
                return None

            # Pass ensemble master's stem-only settings to individual models
            # This ensures individual models only process the requested stems
            if hasattr(self.model_data, "is_primary_stem_only"):
                model_data.is_primary_stem_only = self.model_data.is_primary_stem_only
                self._write_to_console(
                    f"  📋 Inherited primary stem only: {model_data.is_primary_stem_only}",
                    "",
                )
            if hasattr(self.model_data, "is_secondary_stem_only"):
                model_data.is_secondary_stem_only = (
                    self.model_data.is_secondary_stem_only
                )
                self._write_to_console(
                    f"  📋 Inherited secondary stem only: {model_data.is_secondary_stem_only}",
                    "",
                )

            # Save input audio to temp file - all separators expect file paths
            temp_audio_file = self._save_temp_audio(input_audio)
            self._write_to_console(
                f"  ✓ Created temp audio file: {temp_audio_file}", ""
            )

            # Create process_data for the separator
            # Use a temporary directory so separators don't save files in the main export path
            temp_export_dir = tempfile.mkdtemp(prefix="ensemble_temp_")
            process_data = {
                "audio_file": temp_audio_file,
                "audio_file_base": Path(temp_audio_file).stem,
                "export_path": temp_export_dir,  # Use temp directory to prevent unwanted file saves
                "set_progress_bar": self._set_progress_bar_callback,
                "write_to_console": self._write_to_console,
                "cached_source_callback": self._cached_source_callback,
                "cached_model_source_holder": self._cached_model_source_holder,
                "is_4_stem_ensemble": False,  # Individual models in ensemble
                "list_all_models": [model_data.model_basename],
                "process_iteration": self._process_iteration,
                "is_ensemble_master": False,  # This is an ensemble member
                "input_audio_array": input_audio,
            }

            # Create the appropriate separator
            separator = None
            try:
                if model_data.process_method == ac.VR_ARCH_TYPE:
                    self._write_to_console("  🎵 Creating VR separator...", "")
                    separator = SeparateVRLogic(
                        model_data=model_data, process_data=process_data
                    )
                elif model_data.process_method == ac.MDX_ARCH_TYPE:
                    if model_data.is_mdx_c:
                        self._write_to_console("  🎛️ Creating MDX-C separator...", "")
                        separator = SeparateMDXCLogic(
                            model_data=model_data, process_data=process_data
                        )
                    else:
                        self._write_to_console("  🎛️ Creating MDX separator...", "")
                        separator = SeparateMDXLogic(
                            model_data=model_data, process_data=process_data
                        )
                elif model_data.process_method == ac.DEMUCS_ARCH_TYPE:
                    self._write_to_console("  🎸 Creating Demucs separator...", "")
                    separator = SeparateDemucsLogic(
                        model_data=model_data, process_data=process_data
                    )
                else:
                    self._write_to_console(
                        f"❌ Unsupported method: {model_data.process_method}", ""
                    )
                    return None

                if not separator:
                    self._write_to_console(
                        f"❌ Failed to create separator for {model_data.model_basename}",
                        "",
                    )
                    return None

            except Exception as separator_error:
                self._write_to_console(
                    f"❌ Error creating separator for {model_data.model_basename}: {separator_error}",
                    "",
                )
                self._write_to_console(
                    f"❌ Separator creation traceback: {traceback.format_exc()}", ""
                )
                return None

            # Run the separator
            try:
                self._write_to_console("  🎯 Running separation...", "")
                self._write_to_console(f"  🔍 Temp export dir: {temp_export_dir}", "")
                self._write_to_console(
                    f"  🔍 Model stem settings - Primary only: {getattr(model_data, 'is_primary_stem_only', False)}",
                    "",
                )
                self._write_to_console(
                    f"  🔍 Model stem settings - Secondary only: {getattr(model_data, 'is_secondary_stem_only', False)}",
                    "",
                )
                self._write_to_console(
                    f"  🔍 Model primary stem: {getattr(model_data, 'primary_stem', 'Unknown')}",
                    "",
                )
                self._write_to_console(
                    f"  🔍 Model secondary stem: {getattr(model_data, 'secondary_stem', 'Unknown')}",
                    "",
                )

                # List files in export directory before separation
                export_files_before = set()
                try:
                    export_files_before = set(os.listdir(self.model_data.export_path))
                    self._write_to_console(
                        f"  📁 Export dir before: {len(export_files_before)} files", ""
                    )
                except (OSError, FileNotFoundError):  # noqa: S110
                    pass

                # Call the separate method - this should return audio results
                results = separator.separate()

                # List files in export directory after separation
                export_files_after = set()
                try:
                    export_files_after = set(os.listdir(self.model_data.export_path))
                    new_files = export_files_after - export_files_before
                    if new_files:
                        self._write_to_console(
                            f"  ⚠️ Separator created {len(new_files)} files in main export dir: {list(new_files)}",
                            "",
                        )
                    else:
                        self._write_to_console(
                            "  ✓ No files created in main export dir", ""
                        )
                except (OSError, FileNotFoundError):  # noqa: S110
                    pass

                # List files in temp directory
                try:
                    temp_files = os.listdir(temp_export_dir)
                    self._write_to_console(
                        f"  📁 Temp dir after: {len(temp_files)} files: {temp_files}",
                        "",
                    )
                except (OSError, FileNotFoundError):  # noqa: S110
                    pass

                if results is None:
                    self._write_to_console(
                        f"❌ Separator returned None for {model_data.model_basename}",
                        "",
                    )
                    return None

                self._write_to_console(
                    f"  ✓ Separation completed, type: {type(results)}", ""
                )

                # Handle different result types
                if isinstance(results, dict):
                    # Dictionary format - this is what we want for ensemble
                    self._write_to_console(
                        f"  📋 Results dictionary keys: {list(results.keys())}", ""
                    )

                    # Validate that we have audio arrays
                    valid_results = {}
                    for stem_name, stem_audio in results.items():
                        if isinstance(stem_audio, np.ndarray) and stem_audio.size > 0:
                            valid_results[stem_name] = stem_audio
                            self._write_to_console(
                                f"    ✓ {stem_name}: {stem_audio.shape}", ""
                            )
                        else:
                            self._write_to_console(
                                f"    ⚠️ {stem_name}: invalid or empty", ""
                            )

                    if valid_results:
                        return valid_results
                    else:
                        self._write_to_console(
                            f"❌ No valid audio results from {model_data.model_basename}",
                            "",
                        )
                        return None

                elif isinstance(results, tuple) and len(results) == 2:
                    # Tuple format (primary, secondary) - convert to dictionary
                    primary_audio, secondary_audio = results

                    if isinstance(primary_audio, np.ndarray) and isinstance(
                        secondary_audio, np.ndarray
                    ):
                        result_dict = {
                            model_data.primary_stem: primary_audio,
                            model_data.secondary_stem: secondary_audio,
                        }
                        self._write_to_console(
                            f"  📋 Converted tuple to dict: {list(result_dict.keys())}",
                            "",
                        )
                        return result_dict
                    else:
                        self._write_to_console(
                            f"❌ Invalid tuple results from {model_data.model_basename}",
                            "",
                        )
                        return None

                elif isinstance(results, np.ndarray):
                    # Single array - assume it's the primary stem
                    self._write_to_console(
                        f"  📋 Single array result, treating as {model_data.primary_stem}",
                        "",
                    )
                    return {model_data.primary_stem: results}

                else:
                    self._write_to_console(
                        f"❌ Unsupported result type from {model_data.model_basename}: {type(results)}",
                        "",
                    )
                    return None

            except Exception as processing_error:
                self._write_to_console(
                    f"❌ Processing error for {model_data.model_basename}: {processing_error}",
                    "",
                )
                self._write_to_console(
                    f"❌ Processing traceback: {traceback.format_exc()}", ""
                )
                return None

        except Exception as e:
            self._write_to_console(
                f"❌ General error processing {model_data.model_basename}: {e}", ""
            )
            self._write_to_console(
                f"❌ General traceback: {traceback.format_exc()}", ""
            )
            return None
        finally:
            # Clean up temp file and temp directory
            try:
                if "temp_audio_file" in locals():
                    os.unlink(temp_audio_file)
                    self._write_to_console("  🗑️ Cleaned up temp audio file", "")
            except (OSError, FileNotFoundError):  # noqa: S110
                pass
            try:
                if "temp_export_dir" in locals():
                    shutil.rmtree(temp_export_dir, ignore_errors=True)
                    self._write_to_console("  🗑️ Cleaned up temp export directory", "")
            except (OSError, FileNotFoundError):  # noqa: S110
                pass

    def _process_vr_arch_direct(self, input_audio: np.ndarray) -> bool:
        """Process VR model directly for ensemble - returns audio in memory"""
        try:
            # Save input audio to temporary file for processing
            temp_audio_file = self._save_temp_audio(input_audio)

            self._write_to_console(
                f"  Loading VR model: {self.model_data.model_basename}", ""
            )

            # Initialize device
            device = self.device_torch

            # Determine model architecture based on file size
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
            vr_5_1_models = [56817, 218409]
            model_size = math.ceil(os.stat(self.model_data.model_path).st_size / 1024)
            nn_arch_size = min(nn_arch_sizes, key=lambda x: abs(x - model_size))

            # Load model
            if nn_arch_size in vr_5_1_models or self.model_data.is_vr_51_model:
                model_run = nets_new.CascadedNet(
                    self.model_data.vr_model_param.param["bins"] * 2,
                    nn_arch_size,
                    nout=self.model_data.model_capacity[0],
                    nout_lstm=self.model_data.model_capacity[1],
                )
                is_vr_51_model = True
            else:
                model_run = nets.determine_model_capacity(
                    self.model_data.vr_model_param.param["bins"] * 2, nn_arch_size
                )
                is_vr_51_model = False

            model_run.load_state_dict(
                torch.load(
                    self.model_data.model_path, map_location="cpu", weights_only=False
                )
            )
            model_run.to(device)
            model_run.eval()

            # Set temp audio file for loading_mix_vr
            original_audio_file = self.model_data.audio_file
            self.model_data.audio_file = temp_audio_file

            # Load and prepare audio mix
            X_spec = self._loading_mix_vr()
            if X_spec is None:
                self._write_to_console("❌ Failed to load audio for VR processing", "")
                return False

            # Run inference
            y_spec, v_spec = self._inference_vr(
                X_spec, device, model_run, is_vr_51_model
            )

            if y_spec is None or v_spec is None:
                self._write_to_console("❌ VR inference failed", "")
                return False

            # Convert to audio
            primary_audio = self._spec_to_wav_vr(y_spec, is_vr_51_model).T
            secondary_audio = self._spec_to_wav_vr(v_spec, is_vr_51_model).T

            # Resample if needed
            if self.model_data.model_samplerate != 44100:
                primary_audio = librosa.resample(
                    primary_audio.T,
                    orig_sr=self.model_data.model_samplerate,
                    target_sr=44100,
                ).T
                secondary_audio = librosa.resample(
                    secondary_audio.T,
                    orig_sr=self.model_data.model_samplerate,
                    target_sr=44100,
                ).T

            # Store results temporarily
            self._temp_primary_result = primary_audio
            self._temp_secondary_result = secondary_audio

            # Restore original audio file
            self.model_data.audio_file = original_audio_file

            # Cleanup
            del model_run
            if hasattr(torch.cuda, "empty_cache"):
                torch.cuda.empty_cache()

            # Remove temp file
            try:
                os.unlink(temp_audio_file)
            except (OSError, FileNotFoundError):  # noqa: S110
                pass

            return True

        except Exception as e:
            self._write_to_console(f"❌ VR processing error: {e}", "")
            self._write_to_console(f"❌ VR traceback: {traceback.format_exc()}", "")
            return False

    def _process_mdx_regular_direct(self, input_audio: np.ndarray) -> bool:
        """Process regular MDX model directly for ensemble"""
        try:
            self._write_to_console(
                f"  Loading MDX model: {self.model_data.model_basename}", ""
            )

            # Load model (same as before)
            if self.model_data.is_mdx_ckpt:

                def map_location_fn(storage, loc):
                    return storage

                model_params = torch.load(
                    self.model_data.model_path, map_location=map_location_fn
                )["hyper_parameters"]
                dim_c, hop_length = model_params["dim_c"], model_params["hop_length"]
                separator = MdxnetSet.ConvTDFNet(**model_params)
                model_run = (
                    separator.load_from_checkpoint(self.model_data.model_path)
                    .to(self.device_torch)
                    .eval()
                )
            else:
                dim_c, hop_length = 4, 1024
                if (
                    self.model_data.mdx_segment_size == self.model_data.mdx_dim_t_set
                    and self.device != "mps"
                ):
                    providers = (
                        ["CUDAExecutionProvider", "CPUExecutionProvider"]
                        if self.device.startswith("cuda")
                        else ["CPUExecutionProvider"]
                    )
                    ort_session = onnxruntime.InferenceSession(
                        self.model_data.model_path, providers=providers
                    )

                    def model_run(spek):
                        return ort_session.run(None, {"input": spek.cpu().numpy()})[0]

                else:
                    model_run = ConvertModel(load(self.model_data.model_path))
                    model_run.to(self.device_torch).eval()

            # Use input audio directly - ensure it's in (2, N) format
            mix = input_audio
            self._write_to_console(f"  Input audio shape: {mix.shape}", "")

            # Run separation
            source = self._demix_mdx(mix, model_run, hop_length, dim_c)
            if source is None:
                self._write_to_console("❌ MDX demixing failed", "")
                return False

            # Store results
            self._temp_primary_result = source.T
            raw_mix = mix.T if hasattr(mix, "T") else mix
            if self.model_data.is_invert_spec:
                secondary_audio = spec_utils.invert_stem(raw_mix, source.T)
            else:
                secondary_audio = raw_mix - source.T
            self._temp_secondary_result = secondary_audio

            if hasattr(torch.cuda, "empty_cache"):
                torch.cuda.empty_cache()

            return True

        except Exception as e:
            self._write_to_console(f"❌ MDX processing error: {e}", "")
            self._write_to_console(f"❌ MDX traceback: {traceback.format_exc()}", "")
            return False

    def _process_mdx_c_direct(self, input_audio: np.ndarray) -> bool:
        """Process MDX-C model directly for ensemble"""
        try:
            self._write_to_console(
                f"  Loading MDX-C model: {self.model_data.model_basename}", ""
            )

            # Load model
            model = TFC_TDF_net(self.model_data.mdx_c_configs, device=self.device_torch)
            model.load_state_dict(
                torch.load(self.model_data.model_path, map_location="cpu")
            )
            model.to(self.device_torch).eval()

            # Use input audio directly - ensure it's in (2, N) format
            mix = input_audio
            self._write_to_console(f"  Input audio shape: {mix.shape}", "")

            # Run separation
            sources = self._demix_mdx_c(mix, model)
            if sources is None:
                self._write_to_console("❌ MDX-C demixing failed", "")
                return False

            # Store results
            stem_list = (
                [self.model_data.mdx_c_configs.training.target_instrument]
                if self.model_data.mdx_c_configs.training.target_instrument
                else [i for i in self.model_data.mdx_c_configs.training.instruments]
            )

            if len(stem_list) == 1:
                source_primary = sources
            else:
                # Handle stem selection for multi-stem models
                if isinstance(sources, dict):
                    # Log available stems for debugging
                    self._write_to_console(
                        f"  Available stems: {list(sources.keys())}", ""
                    )
                    self._write_to_console(
                        f"  Requested stem: {self.model_data.mdxnet_stem_select}", ""
                    )

                    # Handle special cases
                    if (
                        self.model_data.mdxnet_stem_select == "All Stems"
                        or self.model_data.mdxnet_stem_select not in sources
                    ):
                        # If 'All Stems' or invalid selection, use the primary stem (usually vocals)
                        # Try common primary stem names in order of preference
                        primary_stem_candidates = [
                            self.model_data.primary_stem,
                            "vocals",
                            "vocal",
                            "Vocals",
                            "Vocal",
                        ]
                        source_primary = None

                        for candidate in primary_stem_candidates:
                            if candidate in sources:
                                source_primary = sources[candidate]
                                self._write_to_console(
                                    f"  Using primary stem: {candidate}", ""
                                )
                                break

                        # If no primary stem found, use the first available stem
                        if source_primary is None and sources:
                            first_stem = list(sources.keys())[0]
                            source_primary = sources[first_stem]
                            self._write_to_console(
                                f"  Using first available stem: {first_stem}", ""
                            )
                        elif source_primary is None:
                            self._write_to_console(
                                "❌ No stems found in MDX-C output", ""
                            )
                            return False
                    else:
                        # Use the specifically requested stem
                        source_primary = sources[self.model_data.mdxnet_stem_select]
                else:
                    source_primary = sources

            self._temp_primary_result = (
                source_primary.T if hasattr(source_primary, "T") else source_primary
            )

            if isinstance(sources, dict) and len(stem_list) >= 2:
                secondary_audio = sources[self.model_data.secondary_stem].T
            else:
                raw_mix = mix.T if hasattr(mix, "T") else mix
                if self.model_data.is_invert_spec:
                    secondary_audio = spec_utils.invert_stem(
                        raw_mix, self._temp_primary_result
                    )
                else:
                    secondary_audio = raw_mix - self._temp_primary_result
            self._temp_secondary_result = secondary_audio

            del model
            if hasattr(torch.cuda, "empty_cache"):
                torch.cuda.empty_cache()

            return True

        except Exception as e:
            self._write_to_console(f"❌ MDX-C processing error: {e}", "")
            self._write_to_console(f"❌ MDX-C traceback: {traceback.format_exc()}", "")
            return False

    def _process_demucs_direct(self, input_audio: np.ndarray) -> bool:
        """Process Demucs model directly for ensemble"""
        try:
            self._write_to_console("  📂 Importing Demucs modules...", "")

            self._write_to_console("  ✓ Demucs modules imported successfully", "")
        except ImportError as e:
            self._write_to_console(f"❌ Required Demucs modules not available: {e}", "")
            return False

        self._write_to_console(
            f"  Loading Demucs model: {self.model_data.model_basename}", ""
        )
        self._write_to_console(f"  Model path: {self.model_data.model_path}", "")

        # Save input audio to temporary file for processing
        try:
            temp_audio_file = self._save_temp_audio(input_audio)
            self._write_to_console(
                f"  ✓ Created temp audio file: {temp_audio_file}", ""
            )
        except Exception as temp_error:
            self._write_to_console(
                f"❌ Failed to create temp audio file: {temp_error}", ""
            )
            return False

        try:
            # Prepare audio
            self._write_to_console("  📄 Loading audio from temp file...", "")
            mix = prepare_mix_logic(temp_audio_file)
            if mix is None:
                self._write_to_console(
                    "❌ Failed to load audio for Demucs processing", ""
                )
                return False

            self._write_to_console(f"  ✓ Loaded audio shape: {mix.shape}", "")

            # Load model based on version
            try:
                self._write_to_console(
                    f"  🤖 Loading Demucs model (version: {self.model_data.demucs_version})...",
                    "",
                )

                if self.model_data.demucs_version == ac.DEMUCS_V1:
                    self._write_to_console("  Loading V1 model...", "")
                    if str(self.model_data.model_path).endswith(".gz"):
                        model_path = gzip.open(self.model_data.model_path, "rb")
                    else:
                        model_path = self.model_data.model_path
                    klass, args, kwargs, state = torch.load(
                        model_path, map_location=ac.CPU_DEVICE, weights_only=False
                    )
                    demucs_model = klass(*args, **kwargs)
                    demucs_model.to(self.device_torch)
                    demucs_model.load_state_dict(state)
                    self._write_to_console("  ✓ V1 model loaded", "")
                elif self.model_data.demucs_version == ac.DEMUCS_V2:
                    self._write_to_console("  Loading V2 model...", "")
                    # Load v2 model - using simplified approach for ensemble
                    demucs_model = torch.load(
                        self.model_data.model_path,
                        map_location="cpu",
                        weights_only=False,
                    )
                    demucs_model.to(self.device_torch)
                    demucs_model.eval()
                    self._write_to_console("  ✓ V2 model loaded", "")
                else:  # V3/V4
                    self._write_to_console(
                        f"  Loading V3/V4 model from: {self.model_data.model_path}", ""
                    )

                    # For V3/V4, load using get_model
                    model_name = os.path.splitext(
                        os.path.basename(self.model_data.model_path)
                    )[0]
                    model_dir = Path(os.path.dirname(self.model_data.model_path))

                    self._write_to_console(f"  Model name: {model_name}", "")
                    self._write_to_console(f"  Model dir: {model_dir}", "")

                    # Check if model directory exists and contains files
                    if not model_dir.exists():
                        self._write_to_console(
                            f"❌ Model directory does not exist: {model_dir}", ""
                        )
                        return False

                    dir_contents = list(model_dir.iterdir())
                    self._write_to_console(
                        f"  Directory contents: {[f.name for f in dir_contents]}", ""
                    )

                    # Load the model using get_model
                    self._write_to_console(
                        f"  Calling get_model(name={model_name}, repo={model_dir})...",
                        "",
                    )
                    demucs_model = get_model(name=model_name, repo=model_dir)

                    if demucs_model is None:
                        self._write_to_console(
                            f"❌ get_model returned None for {model_name} from {model_dir}",
                            "",
                        )
                        return False

                    self._write_to_console(
                        "  ✓ get_model succeeded, applying segments wrapper...", ""
                    )

                    # Apply segments wrapper
                    segment_value = getattr(self.model_data, "segment", ac.DEFAULT)
                    self._write_to_console(f"  Segment value: {segment_value}", "")
                    demucs_model = demucs_segments(segment_value, demucs_model)

                    demucs_model.to(self.device_torch)
                    demucs_model.eval()
                    self._write_to_console("  ✓ V3/V4 model loaded and configured", "")

                self._write_to_console("  ✓ Model loaded successfully", "")
            except Exception as model_error:
                self._write_to_console(
                    f"❌ Failed to load Demucs model: {model_error}", ""
                )
                self._write_to_console(
                    f"❌ Model loading traceback: {traceback.format_exc()}", ""
                )
                return False

            self._write_to_console("  🎯 Running Demucs demixing...", "")

            # Process audio like in demix_demucs method
            org_mix = mix

            if getattr(self.model_data, "is_pitch_change", False):
                self._write_to_console(
                    f"  🎵 Applying pitch change (semitones: {self.model_data.semitone_shift})...",
                    "",
                )
                mix, sr_pitched = spec_utils.change_pitch_semitones(
                    mix, 44100, semitone_shift=-self.model_data.semitone_shift
                )

            processed = {}
            mix = torch.tensor(mix, dtype=torch.float32)
            ref = mix.mean(0)
            mix = (mix - ref.mean()) / ref.std()
            mix_infer = mix

            self._write_to_console(
                f"  📊 Audio preprocessing complete. Mix shape: {mix_infer.shape}", ""
            )

            with torch.no_grad():
                try:
                    shifts = getattr(self.model_data, "shifts", 1)
                    overlap = getattr(self.model_data, "overlap", 0.25)
                    is_split_mode = getattr(self.model_data, "is_split_mode", True)

                    self._write_to_console(
                        f"  🔄 Starting inference with params - shifts: {shifts}, overlap: {overlap}, split_mode: {is_split_mode}",
                        "",
                    )

                    if self.model_data.demucs_version == ac.DEMUCS_V1:
                        self._write_to_console("  Using V1 inference...", "")
                        sources = apply_model_v1(
                            demucs_model,
                            mix_infer.to(self.device_torch),
                            shifts,
                            is_split_mode,
                            set_progress_bar=self._set_progress_bar_callback,
                        )
                    elif self.model_data.demucs_version == ac.DEMUCS_V2:
                        self._write_to_console("  Using V2 inference...", "")
                        sources = apply_model_v2(
                            demucs_model,
                            mix_infer.to(self.device_torch),
                            shifts,
                            is_split_mode,
                            overlap,
                            set_progress_bar=self._set_progress_bar_callback,
                        )
                    else:  # V3/V4
                        self._write_to_console("  Using V3/V4 inference...", "")
                        sources = apply_model(
                            demucs_model,
                            mix_infer[None],
                            shifts,
                            is_split_mode,
                            overlap,
                            static_shifts=1 if shifts == 0 else shifts,
                            set_progress_bar=self._set_progress_bar_callback,
                            device=self.device_torch,
                        )[0]

                    self._write_to_console("  ✓ Demucs inference completed", "")
                    self._write_to_console(
                        f"  Raw sources shape: {sources.shape if hasattr(sources, 'shape') else type(sources)}",
                        "",
                    )
                except Exception as inference_error:
                    self._write_to_console(
                        f"❌ Demucs inference failed: {inference_error}", ""
                    )
                    self._write_to_console(
                        f"❌ Inference traceback: {traceback.format_exc()}", ""
                    )
                    return False

            # Post-process
            try:
                self._write_to_console("  🔧 Post-processing results...", "")
                sources = (sources * ref.std() + ref.mean()).cpu().numpy()
                self._write_to_console(f"  After denormalization: {sources.shape}", "")

                sources[[0, 1]] = sources[[1, 0]]  # Swap first two channels
                self._write_to_console(f"  After channel swap: {sources.shape}", "")

                processed[mix] = sources[:, :, 0:None].copy()
                sources = list(processed.values())
                sources = [s[:, :, 0:None] for s in sources]
                sources = np.concatenate(sources, axis=-1)

                self._write_to_console(
                    f"  Final processed sources shape: {sources.shape}", ""
                )
            except Exception as postprocess_error:
                self._write_to_console(
                    f"❌ Post-processing failed: {postprocess_error}", ""
                )
                self._write_to_console(
                    f"❌ Post-processing traceback: {traceback.format_exc()}", ""
                )
                return False

            if getattr(self.model_data, "is_pitch_change", False):
                self._write_to_console("  🎵 Applying pitch correction...", "")
                sources = np.stack(
                    [
                        self._pitch_fix_demucs(stem, sr_pitched, org_mix)
                        for stem in sources
                    ]
                )

            self._write_to_console(f"  ✓ Processed {len(sources)} source(s)", "")

            # Map sources to stem names using demucs source map
            try:
                demucs_source_map = self._get_demucs_source_map(len(sources))
                self._write_to_console(
                    f"  🗺️ Source mapping for {len(sources)} sources: {demucs_source_map}",
                    "",
                )

                # Create results dictionary matching expected format
                results = {}
                for stem_name, stem_idx in demucs_source_map.items():
                    if stem_idx < len(sources):
                        stem_audio = sources[
                            stem_idx
                        ].T  # Transpose to match expected format
                        results[stem_name] = stem_audio
                        self._write_to_console(
                            f"    ✓ {stem_name}: {stem_audio.shape}", ""
                        )
                    else:
                        self._write_to_console(
                            f"    ⚠️ {stem_name}: index {stem_idx} >= {len(sources)}", ""
                        )

                if not results:
                    self._write_to_console(
                        "❌ No valid results after source mapping", ""
                    )
                    return False

                # Store results temporarily for ensemble processing
                self._temp_demucs_results = results
                self._write_to_console(
                    f"  ✅ Stored {len(results)} results: {list(results.keys())}", ""
                )

            except Exception as mapping_error:
                self._write_to_console(f"❌ Source mapping failed: {mapping_error}", "")
                self._write_to_console(
                    f"❌ Mapping traceback: {traceback.format_exc()}", ""
                )
                return False

        except Exception as e:
            self._write_to_console(f"❌ Demucs processing failed: {e}", "")
            self._write_to_console(f"❌ Full traceback: {traceback.format_exc()}", "")
            return False
        finally:
            # Clean up
            if "demucs_model" in locals():
                del demucs_model
                if hasattr(torch.cuda, "empty_cache"):
                    torch.cuda.empty_cache()
            # Remove temp file
            try:
                if "temp_audio_file" in locals():
                    os.unlink(temp_audio_file)
                    self._write_to_console("  🗑️ Cleaned up temp file", "")
            except (OSError, FileNotFoundError):  # noqa: S110
                pass

        return True

    def _save_temp_audio(self, audio: np.ndarray) -> str:
        """Save audio array to a temporary file"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                # Ensure audio is in correct format for saving
                if audio.ndim == 1:
                    # Mono audio
                    sf.write(f.name, audio, 44100)
                elif audio.ndim == 2:
                    if audio.shape[0] == 2:
                        # (2, N) format - transpose to (N, 2) for soundfile
                        sf.write(f.name, audio.T, 44100)
                    else:
                        # (N, 2) format - use as is
                        sf.write(f.name, audio, 44100)
                return f.name
        except Exception as e:
            self._write_to_console(f"❌ Error saving temp audio: {e}", "")
            # Fallback: try with simple format
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                if audio.ndim == 2 and audio.shape[0] == 2:
                    sf.write(f.name, audio.T, 44100)
                else:
                    sf.write(f.name, audio, 44100)
                return f.name

    def _get_separator_for_model(
        self, model_data_obj: ModelData, process_data_dict: Dict[str, Any]
    ) -> Optional[Any]:
        if not model_data_obj or not model_data_obj.model_status:
            self._write_to_console(
                f"Cannot create separator: ModelData for {model_data_obj.model_name if model_data_obj else 'unknown'} is invalid or missing.",
                "",
            )
            return None
        if process_data_dict.get("input_audio_array") is not None:
            process_data_dict["audio_file"] = None
        elif model_data_obj == self.model_data:
            process_data_dict["audio_file"] = self.model_data.audio_file
            process_data_dict["input_audio_array"] = None
        if model_data_obj.process_method == ac.VR_ARCH_TYPE:
            return SeparateVRLogic(
                model_data=model_data_obj, process_data=process_data_dict
            )
        elif model_data_obj.process_method == ac.MDX_ARCH_TYPE:
            if model_data_obj.is_mdx_c:
                return SeparateMDXCLogic(
                    model_data=model_data_obj, process_data=process_data_dict
                )
            else:
                return SeparateMDXLogic(
                    model_data=model_data_obj, process_data=process_data_dict
                )
        elif model_data_obj.process_method == ac.DEMUCS_ARCH_TYPE:
            return SeparateDemucsLogic(
                model_data=model_data_obj, process_data=process_data_dict
            )
        self._write_to_console(
            f"Unknown process method for separator: {model_data_obj.process_method}", ""
        )
        return None

    def stop(self):
        self._is_running = False

    def _write_stem_file(self, stem_path: str, stem_audio: np.ndarray, stem_name: str):
        """Write stem audio to file using write_audio_logic"""
        try:
            if write_audio_logic:
                write_audio_logic(
                    stem_path_str=stem_path,
                    stem_source=stem_audio,
                    samplerate=44100,
                    model_data=self.model_data,
                    stem_name=stem_name,
                    process_data=self._create_process_data(),
                )
                self._write_to_console(
                    f"Saved {stem_name} to {Path(stem_path).name}", ""
                )
            else:
                # Fallback using soundfile
                sf.write(stem_path, stem_audio, 44100)
                self._write_to_console(
                    f"Saved {stem_name} to {Path(stem_path).name}", ""
                )
        except Exception as e:
            self._write_to_console(f"Error saving {stem_name}: {e}", "")

    def _loading_mix_vr(self) -> Optional[np.ndarray]:
        """Load audio mix for VR processing"""
        X_wave = {}
        X_spec_s = {}
        mp = self.model_data.vr_model_param
        bands_n = len(mp.param["band"])
        audio_file = self.model_data.audio_file
        is_mp3 = audio_file.endswith(".mp3") if isinstance(audio_file, str) else False

        for d in range(bands_n, 0, -1):
            bp = mp.param["band"][d]
            wav_resolution = "polyphase"

            if d == bands_n:  # high-end band
                X_wave[d], _ = librosa.load(
                    audio_file,
                    sr=bp["sr"],
                    mono=False,
                    dtype=np.float32,
                    res_type=wav_resolution,
                )

                if not np.any(X_wave[d]) and is_mp3:
                    try:
                        with audioread.audio_open(audio_file) as f:
                            track_length = int(f.duration)
                        X_wave[d], _ = librosa.load(
                            audio_file,
                            sr=bp["sr"],
                            mono=False,
                            dtype=np.float32,
                            res_type=wav_resolution,
                            duration=track_length,
                        )
                    except (OSError, EOFError, ValueError):  # noqa: S110
                        pass

                if X_wave[d].ndim == 1:
                    X_wave[d] = np.asarray([X_wave[d], X_wave[d]])
            else:  # lower bands
                X_wave[d] = librosa.resample(
                    X_wave[d + 1],
                    orig_sr=mp.param["band"][d + 1]["sr"],
                    target_sr=bp["sr"],
                    res_type=wav_resolution,
                )

            X_spec_s[d] = spec_utils.wave_to_spectrogram(
                X_wave[d],
                bp["hl"],
                bp["n_fft"],
                mp,
                band=d,
                is_v51_model=self.model_data.is_vr_51_model,
            )

            if d == bands_n and self.model_data.is_high_end_process not in [
                False,
                "none",
                "None",
            ]:
                self.input_high_end_h = (bp["n_fft"] // 2 - bp["crop_stop"]) + (
                    mp.param["pre_filter_stop"] - mp.param["pre_filter_start"]
                )
                self.input_high_end = X_spec_s[d][
                    :, bp["n_fft"] // 2 - self.input_high_end_h : bp["n_fft"] // 2, :
                ]

        X_spec = spec_utils.combine_spectrograms(
            X_spec_s, mp, is_v51_model=self.model_data.is_vr_51_model
        )

        del X_wave, X_spec_s
        return X_spec

    def _inference_vr(
        self, X_spec: np.ndarray, device, model_run, is_vr_51_model: bool
    ):
        """VR inference"""

        def _execute(X_mag_pad, roi_size):
            X_dataset = []
            patches = (X_mag_pad.shape[2] - 2 * model_run.offset) // roi_size
            total_iterations = (
                patches // self.model_data.batch_size
                if not self.model_data.is_tta
                else (patches // self.model_data.batch_size) * 2
            )

            for i in range(patches):
                start = i * roi_size
                X_mag_window = X_mag_pad[
                    :, :, start : start + self.model_data.window_size
                ]
                X_dataset.append(X_mag_window)

            X_dataset = np.asarray(X_dataset)
            model_run.eval()

            with torch.no_grad():
                mask = []
                for i in range(0, patches, self.model_data.batch_size):
                    self.progress_value += 1
                    if self.progress_value >= total_iterations:
                        self.progress_value = total_iterations
                    self._set_progress_bar_callback(
                        0.1 + (0.8 / total_iterations * self.progress_value),
                        "Processing...",
                    )

                    X_batch = X_dataset[i : i + self.model_data.batch_size]
                    X_batch = torch.from_numpy(X_batch).to(device)
                    pred = model_run.predict_mask(X_batch)

                    if not pred.size()[3] > 0:
                        raise Exception("Window size error")

                    pred = pred.detach().cpu().numpy()
                    pred = np.concatenate(pred, axis=2)
                    mask.append(pred)

                if len(mask) == 0:
                    raise Exception("Window size error")

                mask = np.concatenate(mask, axis=2)
            return mask

        def postprocess(mask, X_mag, X_phase):
            # Create proper aggressiveness dictionary structure
            mp = self.model_data.vr_model_param
            aggressiveness = {
                "value": self.model_data.aggression_setting,
                "split_bin": mp.param["band"][1]["crop_stop"],
                "aggr_correction": mp.param.get("aggr_correction"),
            }

            # Apply aggressiveness adjustment
            if aggressiveness and aggressiveness["value"] != 0.04:
                mask = spec_utils.adjust_aggr(mask, False, aggressiveness)

            if self.model_data.is_post_process:
                mask = spec_utils.merge_artifacts(
                    mask, thres=self.model_data.post_process_threshold
                )

            y_spec = mask * X_mag * np.exp(1.0j * X_phase)
            v_spec = (1 - mask) * X_mag * np.exp(1.0j * X_phase)

            return y_spec, v_spec

        X_mag, X_phase = spec_utils.preprocess(X_spec)
        n_frame = X_mag.shape[2]
        pad_l, pad_r, roi_size = spec_utils.make_padding(
            n_frame, self.model_data.window_size, model_run.offset
        )
        X_mag_pad = np.pad(X_mag, ((0, 0), (0, 0), (pad_l, pad_r)), mode="constant")
        X_mag_pad /= X_mag_pad.max()

        mask = _execute(X_mag_pad, roi_size)

        if self.model_data.is_tta:
            pad_l += roi_size // 2
            pad_r += roi_size // 2
            X_mag_pad = np.pad(X_mag, ((0, 0), (0, 0), (pad_l, pad_r)), mode="constant")
            X_mag_pad /= X_mag_pad.max()
            mask_tta = _execute(X_mag_pad, roi_size)
            mask_tta = mask_tta[:, :, roi_size // 2 :]
            mask = (mask[:, :, :n_frame] + mask_tta[:, :, :n_frame]) * 0.5
        else:
            mask = mask[:, :, :n_frame]

        y_spec, v_spec = postprocess(mask, X_mag, X_phase)
        return y_spec, v_spec

    def _combine_ensemble_outputs(
        self, outputs: List[np.ndarray], algorithm: str
    ) -> np.ndarray:
        """Combine multiple audio outputs using the specified ensemble algorithm."""
        if not outputs or len(outputs) < 2:
            return None

        self._write_to_console(
            f"Combining {len(outputs)} outputs with algorithm: {algorithm}", ""
        )

        # Log shapes before combining
        for i, output in enumerate(outputs):
            self._write_to_console(f"Output {i} shape: {output.shape}", "")

        try:
            # Parse complex algorithm strings like "Max Spec/Min Spec"
            if "/" in algorithm:
                # For primary/secondary algorithms, use first part (primary)
                primary_algorithm = algorithm.split("/")[0].strip()
                self._write_to_console(
                    f"Using primary algorithm: {primary_algorithm}", ""
                )
                algorithm = primary_algorithm

            # Map algorithm names to internal constants
            if algorithm == "Max Spec":
                return self._spectral_ensemble(outputs, is_max=True)
            elif algorithm == "Min Spec":
                return self._spectral_ensemble(outputs, is_max=False)
            elif algorithm == "Average":
                return self._average_ensemble(outputs)
            elif algorithm == ac.AVERAGE_ENSEMBLE:
                return self._average_ensemble(outputs)
            elif algorithm == ac.MAX_SPEC_ENSEMBLE:
                return self._spectral_ensemble(outputs, is_max=True)
            elif algorithm == ac.MIN_SPEC_ENSEMBLE:
                return self._spectral_ensemble(outputs, is_max=False)
            else:
                self._write_to_console(
                    f"Unknown ensemble algorithm: {algorithm}, using average", ""
                )
                return self._average_ensemble(outputs)
        except Exception as e:
            self._write_to_console(f"Error during ensemble combination: {e}", "")
            # Fallback to average
            return self._average_ensemble(outputs)

    def _average_ensemble(self, outputs: List[np.ndarray]) -> np.ndarray:
        """Combine outputs using averaging (similar to spec_utils.average_audio)."""
        if not outputs:
            return None

        self._write_to_console(f"  Averaging {len(outputs)} outputs", "")

        # Log input shapes for debugging
        for i, output in enumerate(outputs):
            self._write_to_console(
                f"    Input {i}: shape={output.shape}, dtype={output.dtype}", ""
            )

        # Normalize all outputs to the same format: (N, 2) for stereo
        normalized_outputs = []
        for i, output in enumerate(outputs):
            if output.ndim == 1:
                # Convert mono to stereo
                normalized = np.column_stack([output, output])
            elif output.ndim == 2:
                if output.shape[0] == 2 and output.shape[1] > 2:
                    # Convert (2, N) to (N, 2)
                    normalized = output.T
                elif output.shape[1] == 2:
                    # Already (N, 2)
                    normalized = output
                elif output.shape[0] > output.shape[1]:
                    # Likely (N, 2) but check
                    normalized = output
                else:
                    # Default: assume (2, N) and transpose
                    normalized = output.T
            else:
                self._write_to_console(
                    f"    ❌ Invalid output {i} dimensions: {output.shape}", ""
                )
                continue

            normalized_outputs.append(normalized)
            self._write_to_console(f"    Normalized {i}: {normalized.shape}", "")

        if not normalized_outputs:
            self._write_to_console("  ❌ No valid outputs after normalization", "")
            return None

        # Find the minimum length to align all outputs
        min_length = min(output.shape[0] for output in normalized_outputs)
        self._write_to_console(f"  Aligning to min length: {min_length}", "")

        # Align all outputs to the same length
        aligned_outputs = []
        for output in normalized_outputs:
            aligned = output[:min_length, :]
            aligned_outputs.append(aligned)

        # Stack and average
        try:
            stacked = np.stack(aligned_outputs, axis=0)
            averaged = np.mean(stacked, axis=0)
            self._write_to_console(f"  ✓ Averaged result shape: {averaged.shape}", "")
            return averaged
        except Exception as e:
            self._write_to_console(f"  ❌ Error during averaging: {e}", "")
            return None

    def _spectral_ensemble(
        self, outputs: List[np.ndarray], is_max: bool = True
    ) -> np.ndarray:
        """Combine outputs using spectral ensemble (min/max magnitude) in frequency domain"""
        if not outputs:
            return None

        self._write_to_console(
            f"  Spectral ensemble ({'max' if is_max else 'min'}) with {len(outputs)} outputs",
            "",
        )

        # Log input shapes for debugging
        for i, output in enumerate(outputs):
            self._write_to_console(
                f"    Input {i}: shape={output.shape}, dtype={output.dtype}", ""
            )

        try:
            # Normalize all outputs to the same format: (2, N) for spectral processing
            normalized_outputs = []
            for i, output in enumerate(outputs):
                if output.ndim == 1:
                    # Convert mono to stereo: (N,) -> (2, N)
                    normalized = np.array([output, output])
                elif output.ndim == 2:
                    if output.shape[1] == 2 and output.shape[0] > 2:
                        # Convert (N, 2) to (2, N)
                        normalized = output.T
                    elif output.shape[0] == 2:
                        # Already (2, N)
                        normalized = output
                    else:
                        # Default: transpose to get (2, N)
                        normalized = output.T
                else:
                    self._write_to_console(
                        f"    ❌ Invalid output {i} dimensions: {output.shape}", ""
                    )
                    continue

                normalized_outputs.append(normalized)
                self._write_to_console(f"    Normalized {i}: {normalized.shape}", "")

            if not normalized_outputs:
                self._write_to_console("  ❌ No valid outputs after normalization", "")
                return None

            # Find the minimum length to align all outputs
            min_length = min(output.shape[1] for output in normalized_outputs)
            self._write_to_console(f"  Aligning to min length: {min_length}", "")

            # Align all outputs to the same length and convert to spectrograms
            spectrograms = []
            for i, output in enumerate(normalized_outputs):
                aligned = output[:, :min_length]
                # Convert to spectrogram using STFT
                spec = spec_utils.wave_to_spectrogram_old(aligned, 1024, 2048)
                spectrograms.append(spec)
                self._write_to_console(f"    Spectrogram {i}: {spec.shape}", "")

            # Apply spectral ensemble in frequency domain
            result_spec = spectrograms[0].copy()

            for i in range(1, len(spectrograms)):
                current_spec = spectrograms[i]

                # Compare magnitudes in frequency domain
                current_mag = np.abs(current_spec)
                result_mag = np.abs(result_spec)

                if is_max:
                    # Use spectrogram with maximum magnitude at each bin
                    mask = current_mag >= result_mag
                    result_spec = np.where(mask, current_spec, result_spec)
                else:
                    # Use spectrogram with minimum magnitude at each bin
                    mask = current_mag <= result_mag
                    result_spec = np.where(mask, current_spec, result_spec)

            # Convert back to audio using ISTFT
            result_audio = spec_utils.spectrogram_to_wave_old(result_spec, 1024)

            # Convert back to (N, 2) format
            if result_audio.shape[0] == 2:
                result_audio = result_audio.T

            self._write_to_console(
                f"  ✓ Spectral ensemble result shape: {result_audio.shape}", ""
            )
            return result_audio

        except Exception as e:
            self._write_to_console(f"  ❌ Error in spectral ensemble: {e}", "")
            self._write_to_console(
                f"  ❌ Spectral traceback: {traceback.format_exc()}", ""
            )
            # Fallback to simple method
            self._write_to_console("  🔄 Falling back to simple spectral ensemble", "")
            return self._simple_spectral_ensemble(outputs, is_max)

    def _simple_spectral_ensemble(
        self, outputs: List[np.ndarray], is_max: bool = True
    ) -> np.ndarray:
        """Simple spectral ensemble using magnitude comparison in time domain as fallback"""
        try:
            # Normalize all outputs to the same format: (N, 2) for stereo
            normalized_outputs = []
            for i, output in enumerate(outputs):
                if output.ndim == 1:
                    # Convert mono to stereo
                    normalized = np.column_stack([output, output])
                elif output.ndim == 2:
                    if output.shape[0] == 2 and output.shape[1] > 2:
                        # Convert (2, N) to (N, 2)
                        normalized = output.T
                    elif output.shape[1] == 2:
                        # Already (N, 2)
                        normalized = output
                    elif output.shape[0] > output.shape[1]:
                        # Likely (N, 2) but check
                        normalized = output
                    else:
                        # Default: assume (2, N) and transpose
                        normalized = output.T
                else:
                    self._write_to_console(
                        f"    ❌ Invalid output {i} dimensions: {output.shape}", ""
                    )
                    continue

                normalized_outputs.append(normalized)

            if not normalized_outputs:
                return None

            # Find the minimum length to align all outputs
            min_length = min(output.shape[0] for output in normalized_outputs)

            # Align all outputs to the same length
            aligned_outputs = []
            for output in normalized_outputs:
                aligned = output[:min_length, :]
                aligned_outputs.append(aligned)

            # Apply simple spectral ensemble by comparing magnitudes
            result = aligned_outputs[0].copy()

            for i in range(1, len(aligned_outputs)):
                current = aligned_outputs[i]
                if is_max:
                    # Use maximum magnitude
                    mask = np.abs(current) >= np.abs(result)
                    result = np.where(mask, current, result)
                else:
                    # Use minimum magnitude
                    mask = np.abs(current) <= np.abs(result)
                    result = np.where(mask, current, result)

            return result

        except Exception as e:
            self._write_to_console(f"  ❌ Error in simple spectral ensemble: {e}", "")
            # Ultimate fallback to average
            return self._average_ensemble(outputs)

    def _spec_to_wav_vr(self, spec: np.ndarray, is_v51_model: bool) -> np.ndarray:
        """Convert spectrogram to audio"""
        mp = self.model_data.vr_model_param

        # Handle both boolean and string values for high_end_process
        high_end_process = self.model_data.is_high_end_process
        is_mirroring = False

        if isinstance(high_end_process, str) and high_end_process.startswith(
            "mirroring"
        ):
            is_mirroring = True
        elif high_end_process is True:  # Handle boolean True as mirroring
            is_mirroring = True

        if (
            is_mirroring
            and hasattr(self, "input_high_end")
            and self.input_high_end is not None
            and hasattr(self, "input_high_end_h")
        ):
            # Use string value for mirroring function
            mirroring_process = (
                high_end_process if isinstance(high_end_process, str) else "mirroring"
            )
            input_high_end_ = spec_utils.mirroring(
                mirroring_process, spec, self.input_high_end, mp
            )
            wav = spec_utils.cmb_spectrogram_to_wave(
                spec,
                mp,
                self.input_high_end_h,
                input_high_end_,
                is_v51_model=is_v51_model,
            )
        else:
            wav = spec_utils.cmb_spectrogram_to_wave(
                spec, mp, is_v51_model=is_v51_model
            )

        return wav

    def _demix_mdx(
        self, mix: np.ndarray, model_run, hop_length: int, dim_c: int
    ) -> Optional[np.ndarray]:
        """MDX demixing"""
        # Initialize settings
        n_fft = self.model_data.mdx_n_fft_scale_set
        n_bins = n_fft // 2 + 1
        trim = n_fft // 2
        chunk_size = hop_length * (self.model_data.mdx_segment_size - 1)
        gen_size = chunk_size - 2 * trim
        stft = STFT(n_fft, hop_length, self.model_data.mdx_dim_f_set, self.device_torch)

        org_mix = mix
        tar_waves_ = []

        if self.model_data.is_pitch_change:
            mix, sr_pitched = spec_utils.change_pitch_semitones(
                mix, 44100, semitone_shift=-self.model_data.semitone_shift
            )

        pad = gen_size + trim - ((mix.shape[-1]) % gen_size)
        mixture = np.concatenate(
            (
                np.zeros((2, trim), dtype="float32"),
                mix,
                np.zeros((2, pad), dtype="float32"),
            ),
            1,
        )

        overlap = (
            self.model_data.overlap_mdx
            if self.model_data.overlap_mdx != ac.DEFAULT
            else 0.25
        )
        step = (
            chunk_size - n_fft
            if overlap == ac.DEFAULT
            else int((1 - overlap) * chunk_size)
        )
        result = np.zeros((1, 2, mixture.shape[-1]), dtype=np.float32)
        divider = np.zeros((1, 2, mixture.shape[-1]), dtype=np.float32)
        total_chunks = (mixture.shape[-1] + step - 1) // step

        for i in range(0, mixture.shape[-1], step):
            start = i
            end = min(i + chunk_size, mixture.shape[-1])
            chunk_size_actual = end - start

            if overlap == 0:
                window = None
            else:
                window = np.hanning(chunk_size_actual)
                window = np.tile(window[None, None, :], (1, 2, 1))

            mix_part_ = mixture[:, start:end]
            if end != i + chunk_size:
                pad_size = (i + chunk_size) - end
                mix_part_ = np.concatenate(
                    (mix_part_, np.zeros((2, pad_size), dtype="float32")), axis=-1
                )

            mix_part = torch.tensor([mix_part_], dtype=torch.float32).to(
                self.device_torch
            )

            with torch.no_grad():
                self.progress_value += 1
                self._set_progress_bar_callback(
                    0.1 + (0.8 * self.progress_value / total_chunks), "Processing..."
                )

                # Run model
                spek = stft(mix_part.to(self.device_torch))
                spek[:, :, :3, :] *= 0

                if self.model_data.is_mdx_ckpt or callable(model_run):
                    if hasattr(model_run, "__call__") and not hasattr(
                        model_run, "parameters"
                    ):
                        # ONNX model
                        spec_pred = model_run(spek.cpu().numpy())
                        tar_waves = stft.inverse(
                            torch.tensor(spec_pred).to(self.device_torch)
                        )
                    else:
                        # PyTorch model
                        spec_pred = model_run(spek)
                        tar_waves = stft.inverse(spec_pred)
                else:
                    spec_pred = model_run(spek)
                    tar_waves = stft.inverse(spec_pred)

                tar_waves = tar_waves.cpu().detach().numpy()

                if window is not None:
                    tar_waves[..., :chunk_size_actual] *= window
                    divider[..., start:end] += window
                else:
                    divider[..., start:end] += 1

                result[..., start:end] += tar_waves[..., : end - start]

        tar_waves = result / divider
        tar_waves = tar_waves[:, :, trim:-trim]
        tar_waves = tar_waves[:, :, : mix.shape[-1]]

        source = tar_waves[0, :, :]

        if self.model_data.is_pitch_change:
            source = self._pitch_fix_mdx(source, sr_pitched, org_mix)

        source = source * self.model_data.compensate

        return source

    def _demix_mdx_c(self, mix: np.ndarray, model) -> Optional[np.ndarray]:
        """MDX-C demixing"""

        org_mix = mix
        if self.model_data.is_pitch_change:
            mix, sr_pitched = spec_utils.change_pitch_semitones(
                mix, 44100, semitone_shift=-self.model_data.semitone_shift
            )

        mix = torch.tensor(mix, dtype=torch.float32)

        try:
            S = model.num_target_instruments
        except Exception:
            S = model.module.num_target_instruments

        mdx_segment_size = (
            self.model_data.mdx_c_configs.inference.dim_t
            if self.model_data.is_mdx_c_seg_def
            else self.model_data.mdx_segment_size
        )
        batch_size = self.model_data.mdx_batch_size
        chunk_size = self.model_data.mdx_c_configs.audio.hop_length * (
            mdx_segment_size - 1
        )

        # Ensure overlap is an integer (convert from string if necessary)
        overlap = self.model_data.overlap_mdx23
        if isinstance(overlap, str):
            try:
                overlap = int(overlap)
            except ValueError:
                # Default overlap value if conversion fails
                overlap = 4
        elif overlap is None:
            overlap = 4

        hop_size = chunk_size // overlap
        mix_shape = mix.shape[1]
        pad_size = hop_size - (mix_shape - chunk_size) % hop_size
        mix = torch.cat(
            [
                torch.zeros(2, chunk_size - hop_size),
                mix,
                torch.zeros(2, pad_size + chunk_size - hop_size),
            ],
            1,
        )

        chunks = mix.unfold(1, chunk_size, hop_size).transpose(0, 1)
        batches = [
            chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)
        ]

        X = torch.zeros(S, *mix.shape) if S > 1 else torch.zeros_like(mix)
        X = X.to(self.device_torch)

        with torch.no_grad():
            cnt = 0
            for batch in batches:
                self.progress_value += 1
                self._set_progress_bar_callback(
                    0.1 + (0.8 * self.progress_value / len(batches)), "Processing..."
                )

                x = model(batch.to(self.device_torch))

                for w in x:
                    X[..., cnt * hop_size : cnt * hop_size + chunk_size] += w
                    cnt += 1

        estimated_sources = (
            X[..., chunk_size - hop_size : -(pad_size + chunk_size - hop_size)]
            / overlap
        )
        del X

        if S > 1:
            sources = {
                k: v
                for k, v in zip(
                    self.model_data.mdx_c_configs.training.instruments,
                    estimated_sources.cpu().detach().numpy(),
                )
            }
            del estimated_sources

            if self.model_data.is_pitch_change:
                sources = {
                    k: self._pitch_fix_mdx(v, sr_pitched, org_mix)
                    for k, v in sources.items()
                }

            return sources
        else:
            est_s = estimated_sources.cpu().detach().numpy()
            del estimated_sources
            return (
                self._pitch_fix_mdx(est_s, sr_pitched, org_mix)
                if self.model_data.is_pitch_change
                else est_s
            )

    def _pitch_fix_mdx(
        self, source: np.ndarray, sr_pitched: int, org_mix: np.ndarray
    ) -> np.ndarray:
        """Apply pitch correction for MDX"""
        try:
            source = spec_utils.change_pitch_semitones(
                source, sr_pitched, semitone_shift=self.model_data.semitone_shift
            )[0]
            source = spec_utils.match_array_shapes(source, org_mix)
            return source
        except Exception:  # noqa: S110
            return source

    def _get_demucs_source_map(self, num_sources: int) -> dict:
        """Get Demucs source mapping based on number of sources"""
        if num_sources == 2:
            return {ac.VOCAL_STEM: 1, ac.INST_STEM: 0}
        elif num_sources == 6:
            return {
                ac.VOCAL_STEM: 4,
                ac.INST_STEM: 3,
                ac.BASS_STEM: 0,
                ac.DRUM_STEM: 1,
                ac.OTHER_STEM: 2,
                ac.GUITAR_STEM: 5,
                ac.PIANO_STEM: 5,  # Same as guitar for 6-stem
            }
        else:  # 4 sources
            return {
                ac.VOCAL_STEM: 3,
                ac.INST_STEM: 2,
                ac.BASS_STEM: 0,
                ac.DRUM_STEM: 1,
                ac.OTHER_STEM: 2,
            }

    def _pitch_fix_demucs(
        self, source: np.ndarray, sr_pitched: int, org_mix: np.ndarray
    ) -> np.ndarray:
        """Apply pitch correction for Demucs"""
        try:
            source = spec_utils.change_pitch_semitones(
                source, sr_pitched, semitone_shift=self.model_data.semitone_shift
            )[0]
            source = spec_utils.match_array_shapes(source, org_mix)
            return source
        except Exception:  # noqa: S110
            return source

    def _clean_model_name_for_filename(self, model_basename: str) -> str:
        """Clean model basename by removing version prefixes like 'v4 | ' or 'v3 | '"""
        if not model_basename:
            return "unknown_model"

        # Remove version prefixes commonly found in Demucs model names
        version_prefixes = ["v1 | ", "v2 | ", "v3 | ", "v4 | ", "v5 | "]
        cleaned_name = model_basename

        for prefix in version_prefixes:
            if cleaned_name.startswith(prefix):
                cleaned_name = cleaned_name[len(prefix) :]
                break

        return cleaned_name

    def _align_spectrograms(
        self, spec_list: List[np.ndarray]
    ) -> Optional[List[np.ndarray]]:
        """Aligns a list of spectrograms to a common shape by padding/trimming the time axis."""
        if not spec_list:
            return None

        # Assuming all specs have same number of channels and frequency bins
        # This should be ensured by consistent STFT params during their creation
        ref_channels, ref_freq_bins, _ = spec_list[0].shape
        max_time_frames = max(s.shape[2] for s in spec_list)

        aligned_specs = []
        for spec_to_align in spec_list:
            if (
                spec_to_align.shape[0] != ref_channels
                or spec_to_align.shape[1] != ref_freq_bins
            ):
                self._write_to_console(
                    "Warning: Spectrogram channel/frequency mismatch during alignment. Skipping.",
                    "",
                )
                return None  # Critical mismatch

            if spec_to_align.shape[2] < max_time_frames:
                padding_time = max_time_frames - spec_to_align.shape[2]
                padding = [(0, 0)] * spec_to_align.ndim
                padding[2] = (0, padding_time)
                aligned_spec = np.pad(spec_to_align, padding, mode="constant")
            elif spec_to_align.shape[2] > max_time_frames:
                aligned_spec = spec_to_align[:, :, :max_time_frames]
            else:
                aligned_spec = spec_to_align
            aligned_specs.append(aligned_spec)

        return aligned_specs


class ProcessingThread(QThread):
    """Thread for running audio processing tasks."""

    progress_updated = Signal(int, str)  # progress, message
    processing_finished = Signal(bool, str)  # success, message

    def __init__(self, settings_dict: dict):
        super().__init__()
        self.settings_dict = settings_dict
        self.worker: Optional[ProcessingWorker] = None

    def run(self):
        try:
            self.worker = ProcessingWorker(self.settings_dict)
            self.worker.progress_updated.connect(self.progress_updated)
            self.worker.processing_finished.connect(self.processing_finished)
            self.worker.run()
        except Exception as e:
            self.processing_finished.emit(
                False, f"Thread error: {str(e)}\n{traceback.format_exc()}"
            )

    def stop_processing(self):
        if self.worker:
            self.worker.stop()
