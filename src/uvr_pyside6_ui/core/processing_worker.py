"""
Real processing worker that wraps the original UVR processing logic.
This replaces MockProcessingWorker with actual audio separation functionality.
"""
from PySide6.QtCore import QObject, Signal, QThread
from pathlib import Path
import traceback
import numpy as np 
from typing import Dict, Any, Optional, List

from .model_data import ModelData
from . import app_constants as ac

try:
    from .separate_logic import (
        SeperateVRLogic, SeperateMDXLogic, SeperateMDXCLogic, SeperateDemucsLogic,
        clear_gpu_cache_logic, prepare_mix_logic, write_audio_logic 
    )
    from lib_v5 import spec_utils 
except ImportError as e:
    print(f"Warning: Could not import separation logic modules or spec_utils: {e}")
    SeperateVRLogic, SeperateMDXLogic, SeperateMDXCLogic, SeperateDemucsLogic = None, None, None, None
    clear_gpu_cache_logic, prepare_mix_logic, write_audio_logic = None, None, None
    spec_utils = None


class RealProcessingWorker(QObject):
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)

    def __init__(self, settings_dict: Dict[str, Any]):
        super().__init__()
        self.settings = settings_dict
        self._is_running = True
        self.model_data: Optional[ModelData] = None
        self.progress_value = 0
        self.original_mix_audio: Optional[np.ndarray] = None 
        
        try:
            self.model_data = ModelData.from_settings_dict(settings_dict)
        except Exception as e:
            print(f"Error creating ModelData: {e}\n{traceback.format_exc()}")
            self.model_data = None

    def run(self):
        if not self.model_data or not self.model_data.model_status:
            error_msg = "Error: Could not create valid model data from settings."
            if self.model_data and not self.model_data.model_status:
                error_msg = f"Error: Model data initialization failed for {self.model_data.model_name if self.model_data.model_name else 'Unknown Model'}."
            else: 
                error_msg = "Error: ModelData object is None."
            self.processing_finished.emit(False, error_msg)
            return
            
        if not self._is_running:
            self.processing_finished.emit(False, "Processing Canceled"); return

        if not all([SeperateVRLogic, SeperateMDXLogic, SeperateMDXCLogic, SeperateDemucsLogic, clear_gpu_cache_logic, prepare_mix_logic, write_audio_logic]):
            self.processing_finished.emit(False, "Error: Core separation logic modules not fully available."); return

        try:
            if not self.model_data.is_ensemble_mode and (not self.model_data.audio_file or not Path(self.model_data.audio_file).exists()):
                self.processing_finished.emit(False, f"Error: Input file missing or invalid: {self.model_data.audio_file}"); return
            if not self.model_data.export_path or not Path(self.model_data.export_path).is_dir():
                self.processing_finished.emit(False, f"Error: Export directory invalid: {self.model_data.export_path}"); return
            
            if not self.model_data.is_ensemble_mode and (not self.model_data.model_path or not Path(self.model_data.model_path).exists()):
                self.processing_finished.emit(False, f"Error: Primary model file not found: {self.model_data.model_path}"); return
            elif self.model_data.is_ensemble_mode:
                # For live ensembles, check if we have ensemble_models instead of a model_path file
                if self.model_data.ensemble_models:
                    # Live ensemble - no model_path file needed, models are in ensemble_models list
                    pass
                elif not self.model_data.model_path or not Path(self.model_data.model_path).exists():
                    # Saved ensemble - requires model_path file
                    self.processing_finished.emit(False, f"Error: Ensemble configuration file not found: {self.model_data.model_path}"); return

            self.progress_updated.emit(5, "Loading audio file...")
            current_input_audio = None
            audio_file_to_load = self.model_data.audio_file 
            if not audio_file_to_load and self.model_data.is_ensemble_mode and self.model_data.ensemble_models:
                audio_file_to_load = self.model_data.ensemble_models[0].audio_file

            if audio_file_to_load:
                current_input_audio = prepare_mix_logic(str(audio_file_to_load))
                if current_input_audio is None:
                    self.processing_finished.emit(False, f"Failed to load audio from {audio_file_to_load}"); return
                self.original_mix_audio = current_input_audio 
            else: 
                 self.processing_finished.emit(False, "Error: No valid audio input file specified."); return

            if self.model_data.pre_proc_model and self.model_data.is_demucs_pre_proc_model_activate:
                if current_input_audio is None: 
                     self.processing_finished.emit(False, "Error: Audio not loaded for pre-processing."); return
                self.progress_updated.emit(10, f"Pre-processing with: {self.model_data.pre_proc_model.model_basename}...")
                pre_proc_pd = self._create_process_data_for_chained_model(self.model_data.pre_proc_model, current_input_audio, is_pre_proc=True)
                pre_proc_separator = self._get_separator_for_model(self.model_data.pre_proc_model, pre_proc_pd)
                if pre_proc_separator:
                    pre_proc_results = pre_proc_separator.seperate() 
                    if pre_proc_results and self.model_data.pre_proc_model.primary_stem in pre_proc_results and self._is_running:
                        current_input_audio = pre_proc_results[self.model_data.pre_proc_model.primary_stem]
                        self.original_mix_audio = current_input_audio 
                        self._write_to_console("Pre-processing complete. Using output as input for main model.", "")
                        if self.model_data.is_demucs_pre_proc_model_inst_mix:
                             inst_stem_name = self.model_data.pre_proc_model.secondary_stem 
                             if inst_stem_name and inst_stem_name in pre_proc_results:
                                 pre_proc_separator._write_stem(f"{inst_stem_name}_(PreProc)", pre_proc_results[inst_stem_name], self.model_data.pre_proc_model.model_samplerate)
                    elif self._is_running:
                        self._write_to_console(f"Pre-processing model {self.model_data.pre_proc_model.model_basename} did not return expected output.", "")
                        self.processing_finished.emit(False, "Pre-processing failed."); return
                else:
                    self._write_to_console(f"Could not create separator for pre-processing model.", "")
                    self.processing_finished.emit(False, "Pre-processing setup failed."); return
            
            if not self._is_running: return

            self._write_to_console(f"DEBUG: is_ensemble_mode = {self.model_data.is_ensemble_mode}", "")
            self._write_to_console(f"DEBUG: is_ensemble_member = {self.model_data.is_ensemble_member}", "")
            self._write_to_console(f"DEBUG: process_method = {self.model_data.process_method}", "")
            self._write_to_console(f"DEBUG: model_basename = {self.model_data.model_basename}", "")

            if self.model_data.is_ensemble_mode and not self.model_data.is_ensemble_member:
                self._write_to_console("DEBUG: ====== CALLING _process_ensemble ======", "")
                self._process_ensemble(current_input_audio)
            else: 
                main_process_data = self._create_process_data(current_input_audio if current_input_audio is not None else None)
                self.progress_updated.emit(15, f"Processing with primary model: {self.model_data.model_basename}...")
                if self.model_data.process_method == ac.VR_ARCH_TYPE: self._execute_separation_pipeline(ac.VR_ARCH_TYPE, main_process_data)
                elif self.model_data.process_method == ac.MDX_ARCH_TYPE: self._execute_separation_pipeline(ac.MDX_ARCH_TYPE, main_process_data)
                elif self.model_data.process_method == ac.DEMUCS_ARCH_TYPE: self._execute_separation_pipeline(ac.DEMUCS_ARCH_TYPE, main_process_data)
                else: self.processing_finished.emit(False, f"Error: Unsupported primary processing method: {self.model_data.process_method}")

        except Exception as e:
            error_msg = f"Processing failed: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.processing_finished.emit(False, error_msg)
        finally:
            if clear_gpu_cache_logic: clear_gpu_cache_logic()

    def _execute_separation_pipeline(self, method_name: str, process_data_initial: Dict[str, Any]):
        if not self._is_running: return

        primary_separator = self._get_separator_for_model(self.model_data, process_data_initial)
        if not primary_separator:
            self.processing_finished.emit(False, f"Could not create separator for primary model {self.model_data.model_name}"); return
        
        self.progress_updated.emit(30, f"Running {method_name} separation...")
        primary_results = primary_separator.seperate()
        if not self._is_running or not primary_results:
            if self._is_running: self.processing_finished.emit(False, f"{method_name} primary separation failed to produce results.")
            return
        
        current_stems = primary_results.copy()

        if self.model_data.process_method == ac.DEMUCS_ARCH_TYPE and self.model_data.demucs_stems == ac.ALL_STEMS and self.model_data.is_demucs_4_stem_secondaries_activated:
            demucs_stems_order = self.model_data.demucs_source_list 
            for i, stem_name_to_refine in enumerate(demucs_stems_order):
                if i >= len(self.model_data.secondary_model_4_stem_instances): break 
                if not self._is_running: return
                secondary_model_for_stem_obj = self.model_data.secondary_model_4_stem_instances[i]
                
                if secondary_model_for_stem_obj and secondary_model_for_stem_obj.model_name != ac.NO_MODEL:
                    self.progress_updated.emit(70 + i*5, f"Processing Demucs {stem_name_to_refine} with secondary: {secondary_model_for_stem_obj.model_basename}...")
                    input_audio_for_secondary = current_stems.get(stem_name_to_refine)
                    if input_audio_for_secondary is not None:
                        sec_proc_data = self._create_process_data_for_chained_model(secondary_model_for_stem_obj, input_audio_for_secondary, for_demucs_sub_stem=stem_name_to_refine)
                        sec_separator = self._get_separator_for_model(secondary_model_for_stem_obj, sec_proc_data)
                        if sec_separator:
                            sec_results = sec_separator.seperate()
                            if sec_results and self._is_running:
                                refined_stem_audio = sec_results.get(secondary_model_for_stem_obj.primary_stem)
                                if refined_stem_audio is not None:
                                    scale = self.model_data.secondary_model_4_stem_scales[i]
                                    if scale is None: scale = 0.9 
                                    blended_stem = (input_audio_for_secondary * (1-scale)) + (refined_stem_audio * scale)
                                    current_stems[stem_name_to_refine] = blended_stem
                                    primary_separator._write_stem(stem_name_to_refine, blended_stem, self.model_data.model_samplerate) 
                                    self._write_to_console(f"Applied secondary model to Demucs {stem_name_to_refine}.", "")
                    else: self._write_to_console(f"Could not create separator for Demucs {stem_name_to_refine} secondary model.", "")
        elif self.model_data.secondary_model and self.model_data.is_secondary_model_chain_activated:
            self.progress_updated.emit(70, f"Processing with secondary model: {self.model_data.secondary_model.model_basename}...")
            input_stem_name_for_secondary = self.model_data.primary_stem 
            input_audio_for_secondary = current_stems.get(input_stem_name_for_secondary)
            if input_audio_for_secondary is not None:
                sec_model_data = self.model_data.secondary_model
                sec_process_data = self._create_process_data_for_chained_model(sec_model_data, input_audio_for_secondary)
                sec_separator = self._get_separator_for_model(sec_model_data, sec_process_data)
                if sec_separator:
                    sec_results = sec_separator.seperate() 
                    if sec_results and self._is_running:
                        scale = sec_model_data.secondary_model_chain_scale if sec_model_data.secondary_model_chain_scale is not None else 0.9
                        refined_primary_from_sec = sec_results.get(sec_model_data.primary_stem) 
                        if refined_primary_from_sec is not None:
                            blended_stem = (input_audio_for_secondary * (1 - scale)) + (refined_primary_from_sec * scale)
                            current_stems[input_stem_name_for_secondary] = blended_stem 
                            if self.original_mix_audio is not None and blended_stem.shape == self.original_mix_audio.shape:
                                accompanying_stem_name = self.model_data.secondary_stem
                                current_stems[accompanying_stem_name] = self.original_mix_audio - blended_stem
                                primary_separator._write_stem(input_stem_name_for_secondary, blended_stem, self.model_data.model_samplerate)
                                primary_separator._write_stem(accompanying_stem_name, current_stems[accompanying_stem_name], self.model_data.model_samplerate)
                                self._write_to_console(f"Applied secondary model, saved blended {input_stem_name_for_secondary} and recalculated {accompanying_stem_name}.", "")
                            else: self._write_to_console(f"Could not recalculate/resave accompanying stem for {input_stem_name_for_secondary}.", "")
                        else: self._write_to_console(f"Secondary model did not output its target stem: {sec_model_data.primary_stem}.", "")
                else: self._write_to_console(f"Could not create separator for secondary model.", "")
            else: self._write_to_console(f"Input stem '{input_stem_name_for_secondary}' for secondary model not found.", "")
        
        if not self._is_running: return

        if self.model_data.vocal_split_model and self.model_data.is_vocal_split_model_activated:
            self.progress_updated.emit(85, f"Processing with vocal splitter: {self.model_data.vocal_split_model.model_basename}...")
            vocal_input_for_splitter = current_stems.get(ac.VOCAL_STEM) 
            if vocal_input_for_splitter is not None:
                splitter_model_data = self.model_data.vocal_split_model
                splitter_process_data = self._create_process_data_for_chained_model(splitter_model_data, vocal_input_for_splitter, is_vocal_split=True)
                splitter_separator = self._get_separator_for_model(splitter_model_data, splitter_process_data)
                if splitter_separator:
                    splitter_results = splitter_separator.seperate() 
                    if splitter_results and self.model_data.is_save_inst_vocal_splitter and self._is_running:
                        main_vocals_from_splitter = splitter_results.get(ac.MAIN_VOCAL_STEM)
                        if main_vocals_from_splitter is not None and main_vocals_from_splitter.shape == vocal_input_for_splitter.shape:
                            inst_from_splitter = vocal_input_for_splitter - main_vocals_from_splitter
                            splitter_separator._write_stem(f"{ac.INST_STEM}_(VocalSplitter)", inst_from_splitter, splitter_model_data.model_samplerate)
                        else: self._write_to_console("Could not generate instrumental from vocal splitter.", "")
                else: self._write_to_console(f"Could not create separator for vocal splitter.", "")
            else: self._write_to_console(f"Vocal input for vocal splitter not found.", "")

        if self._is_running:
            self.progress_updated.emit(100, f"{method_name} processing pipeline complete!")
            self.processing_finished.emit(True, f"Successfully processed using {method_name} pipeline.")

    def _create_process_data(self, input_audio_array_for_main_model: Optional[np.ndarray] = None) -> Dict[str, Any]:
        return {
            'audio_file': self.model_data.audio_file if input_audio_array_for_main_model is None else None,
            'input_audio_array': input_audio_array_for_main_model,
            'audio_file_base': Path(self.model_data.audio_file).stem if self.model_data.audio_file else "output",
            'export_path': self.model_data.export_path,
            'set_progress_bar': self._set_progress_bar_callback,
            'write_to_console': self._write_to_console,
            'cached_source_callback': self._cached_source_callback,
            'cached_model_source_holder': self._cached_model_source_holder,
            'is_4_stem_ensemble': self.model_data.is_4_stem_ensemble,
            'list_all_models': [self.model_data.model_basename],
            'process_iteration': self._process_iteration,
            '_is_running_check': lambda: self._is_running,
            'is_ensemble_master': False, 
        }

    def _set_progress_bar_callback(self, current_step_fraction: float, message: Optional[str] = None): 
        if not self._is_running: return
        total_progress = int(current_step_fraction * 100) 
        total_progress = min(max(total_progress, 0), 100) 
        self.progress_value = total_progress 
        self.progress_updated.emit(total_progress, message if message else f"Processing... {total_progress}%")

    def _write_to_console(self, message: str, base_text: str = ""):
        if not self._is_running: return
        full_message = f"{base_text}{message}" if base_text else message
        self.progress_updated.emit(self.progress_value, full_message)

    def _cached_source_callback(self, process_method: str, model_name: str = None): return None, None
    def _cached_model_source_holder(self, process_method: str, sources, model_name: str = None): pass
    def _process_iteration(self): pass 

    def _process_vr_arch(self, process_data: Dict[str, Any]):
        self._execute_separation_pipeline(ac.VR_ARCH_TYPE, process_data)
        
    def _process_mdx_net(self, process_data: Dict[str, Any]):
        self._execute_separation_pipeline(ac.MDX_ARCH_TYPE, process_data)
        
    def _process_demucs(self, process_data: Dict[str, Any]):
        print("DEBUG: Starting Demucs processing")
        print(f"DEBUG: Model path: {self.model_data.model_path}")
        print(f"DEBUG: Model basename: {self.model_data.model_basename}")
        print(f"DEBUG: Demucs version: {self.model_data.demucs_version}")
        print(f"DEBUG: Demucs stems: {self.model_data.demucs_stems}")
        print(f"DEBUG: Demucs source list: {self.model_data.demucs_source_list}")
        
        # Check if model file exists
        if self.model_data.model_path:
            model_path = Path(self.model_data.model_path)
            if model_path.exists():
                print(f"DEBUG: Model file exists: {model_path}")
                print(f"DEBUG: Model file size: {model_path.stat().st_size} bytes")
            else:
                print(f"DEBUG: Model file does not exist: {model_path}")
                
            # Check parent directory
            model_dir = model_path.parent
            if model_dir.exists():
                print(f"DEBUG: Model directory exists: {model_dir}")
                print("DEBUG: Files in model directory:")
                for file in model_dir.iterdir():
                    print(f"  - {file.name}")
            else:
                print(f"DEBUG: Model directory does not exist: {model_dir}")
        
        self._execute_separation_pipeline(ac.DEMUCS_ARCH_TYPE, process_data)

    def _align_spectrograms(self, spec_list: List[np.ndarray]) -> Optional[List[np.ndarray]]:
        """Aligns a list of spectrograms to a common shape by padding/trimming the time axis."""
        if not spec_list: return None
        
        # Assuming all specs have same number of channels and frequency bins
        # This should be ensured by consistent STFT params during their creation
        ref_channels, ref_freq_bins, _ = spec_list[0].shape
        max_time_frames = max(s.shape[2] for s in spec_list)
        
        aligned_specs = []
        for spec_to_align in spec_list:
            if spec_to_align.shape[0] != ref_channels or spec_to_align.shape[1] != ref_freq_bins:
                self._write_to_console(f"Warning: Spectrogram channel/frequency mismatch during alignment. Skipping.", "")
                return None # Critical mismatch

            if spec_to_align.shape[2] < max_time_frames:
                padding_time = max_time_frames - spec_to_align.shape[2]
                padding = [(0,0)] * spec_to_align.ndim; padding[2] = (0, padding_time)
                aligned_spec = np.pad(spec_to_align, padding, mode='constant')
            elif spec_to_align.shape[2] > max_time_frames:
                aligned_spec = spec_to_align[:, :, :max_time_frames]
            else:
                aligned_spec = spec_to_align
            aligned_specs.append(aligned_spec)
            
        return aligned_specs

    def _process_ensemble(self, initial_input_audio: np.ndarray):
        self._write_to_console("DEBUG: ====== ENTERING _process_ensemble ======", "")
        if not self.model_data or not self.model_data.ensemble_models:
            self.processing_finished.emit(False, "Ensemble not configured or no models in ensemble."); return

        self.progress_updated.emit(10, f"Starting Ensemble: {self.model_data.model_basename}...")
        self._write_to_console(f"DEBUG: Starting ensemble with {len(self.model_data.ensemble_models)} models", "")
        
        # Store all outputs from ensemble models
        all_outputs: Dict[str, List[np.ndarray]] = {}
        num_models = len(self.model_data.ensemble_models)
        
        ensemble_output_base = Path(self.model_data.audio_file).stem if self.model_data.audio_file else "ensemble_output"

        # Process each model in the ensemble
        for i, member_model_data in enumerate(self.model_data.ensemble_models):
            if not self._is_running: return
            self.progress_updated.emit(15 + int(i/num_models * 60), f"Ensemble: Processing model {i+1}/{num_models} ({member_model_data.model_basename})...")
            
            member_process_data = self._create_process_data_for_chained_model(
                member_model_data, initial_input_audio, is_ensemble_run=True, 
                ensemble_audio_file_base=ensemble_output_base
            )
            member_separator = self._get_separator_for_model(member_model_data, member_process_data)
            
            if not member_separator:
                self._write_to_console(f"Skipping ensemble member {member_model_data.model_basename}: Could not create separator.", "")
                continue
                
            member_results = member_separator.seperate() 
            if member_results and self._is_running:
                self._write_to_console(f"DEBUG: Model {member_model_data.model_basename} produced stems: {list(member_results.keys())}", "")
                
                # Store outputs by stem name
                for stem_name, stem_audio in member_results.items():
                    if stem_audio is not None and stem_audio.size > 0:
                        self._write_to_console(f"DEBUG: {stem_name} shape: {stem_audio.shape}", "")
                        if stem_name not in all_outputs:
                            all_outputs[stem_name] = []
                        all_outputs[stem_name].append(stem_audio)
                    else:
                        self._write_to_console(f"DEBUG: {stem_name} is None or empty, skipping", "")
            elif self._is_running: 
                self._write_to_console(f"Ensemble member {member_model_data.model_basename} produced no results.", "")
                
            if clear_gpu_cache_logic: 
                clear_gpu_cache_logic()

        if not self._is_running or not all_outputs:
            if self._is_running: 
                self.processing_finished.emit(False, "Ensemble processing failed: No results from members."); 
            return

        self.progress_updated.emit(90, "Combining ensemble results...")
        
        # Available stems from models
        available_stems = list(all_outputs.keys())
        self._write_to_console(f"DEBUG: Available stems from all models: {available_stems}", "")
        self._write_to_console(f"DEBUG: Ensemble primary stem: {self.model_data.ensemble_primary_stem}", "")
        self._write_to_console(f"DEBUG: Ensemble secondary stem: {self.model_data.ensemble_secondary_stem}", "")
        self._write_to_console(f"DEBUG: Ensemble type: {self.model_data.ensemble_type}", "")
        
        # Process each available stem
        for stem_name in available_stems:
            if not self._is_running: return
            
            stem_outputs = all_outputs[stem_name]
            if len(stem_outputs) < 2:
                self._write_to_console(f"DEBUG: Only {len(stem_outputs)} outputs for {stem_name}, skipping ensemble", "")
                continue
                
            self._write_to_console(f"DEBUG: Processing stem: {stem_name} with {len(stem_outputs)} outputs", "")
            
            # Apply ensemble algorithm
            ensembled_audio = self._combine_ensemble_outputs(stem_outputs, self.model_data.ensemble_type)
            
            if ensembled_audio is not None and ensembled_audio.size > 0:
                self._write_to_console(f"DEBUG: Ensembled {stem_name} shape: {ensembled_audio.shape}", "")
                
                # Save the ensembled result
                save_md = ModelData(save_format=self.model_data.save_format, wav_type_set=self.model_data.wav_type_set, 
                                  mp3_bit_set=self.model_data.mp3_bit_set, is_normalization=self.model_data.is_normalization)
                samplerate_to_save = self.model_data.ensemble_models[0].model_samplerate if self.model_data.ensemble_models else ac.DEFAULT_SAMPLE_RATE
                
                # Ensure proper audio format for writing
                if ensembled_audio.ndim == 1: 
                    ensembled_audio = np.asfortranarray([ensembled_audio, ensembled_audio])
                if ensembled_audio.shape[0] < ensembled_audio.shape[1] and ensembled_audio.ndim == 2: 
                    ensembled_audio = ensembled_audio.T
                
                output_path = Path(self.model_data.export_path) / f"{ensemble_output_base}_({stem_name}_Ensemble).{save_md.save_format.lower()}"
                
                write_audio_logic(
                    stem_path_str=str(output_path),
                    stem_source=ensembled_audio, 
                    samplerate=samplerate_to_save, 
                    model_data=save_md,
                    stem_name=f"{stem_name} (Ensemble)", 
                    process_data=self._create_process_data()
                )
            else:
                self._write_to_console(f"DEBUG: Failed to ensemble {stem_name}: empty result", "")

        if self._is_running:
            self.progress_updated.emit(100, "Ensemble processing complete!")
            self.processing_finished.emit(True, "Successfully processed ensemble.")

    def _combine_ensemble_outputs(self, outputs: List[np.ndarray], algorithm: str) -> np.ndarray:
        """Combine multiple audio outputs using the specified ensemble algorithm."""
        if not outputs or len(outputs) < 2:
            return None
            
        self._write_to_console(f"DEBUG: Combining {len(outputs)} outputs with algorithm: {algorithm}", "")
        
        # Log shapes before combining
        for i, output in enumerate(outputs):
            self._write_to_console(f"DEBUG: Output {i} shape: {output.shape}", "")
        
        try:
            if algorithm == ac.AVERAGE_ENSEMBLE:
                return self._average_ensemble(outputs)
            elif algorithm == ac.MAX_SPEC_ENSEMBLE:
                return self._spectral_ensemble(outputs, is_max=True)
            elif algorithm == ac.MIN_SPEC_ENSEMBLE:
                return self._spectral_ensemble(outputs, is_max=False)
            else:
                self._write_to_console(f"DEBUG: Unknown ensemble algorithm: {algorithm}, using average", "")
                return self._average_ensemble(outputs)
        except Exception as e:
            self._write_to_console(f"DEBUG: Error during ensemble combination: {e}", "")
            return None
    
    def _average_ensemble(self, outputs: List[np.ndarray]) -> np.ndarray:
        """Combine outputs using averaging (similar to spec_utils.average_audio)."""
        if not outputs:
            return None
            
        # Find the minimum length to align all outputs
        min_length = min(output.shape[-1] for output in outputs)  # Use last dimension (time)
        self._write_to_console(f"DEBUG: Aligning outputs to min length: {min_length}", "")
        
        # Align all outputs to the same length
        aligned_outputs = []
        for output in outputs:
            if output.ndim == 1:
                aligned = output[:min_length]
            elif output.ndim == 2:
                aligned = output[:, :min_length]
            else:
                aligned = output  # Keep as is for higher dimensions
            aligned_outputs.append(aligned)
        
        # Stack and average
        stacked = np.stack(aligned_outputs, axis=0)
        averaged = np.mean(stacked, axis=0)
        
        self._write_to_console(f"DEBUG: Averaged result shape: {averaged.shape}", "")
        return averaged
    
    def _spectral_ensemble(self, outputs: List[np.ndarray], is_max: bool = True) -> np.ndarray:
        """Combine outputs using spectral ensemble (min/max magnitude)."""
        if not outputs or not spec_utils:
            return None
            
        try:
            # Convert audio to spectrograms
            spectrograms = []
            for output in outputs:
                # Ensure audio is in the right format for spectrogram conversion
                if output.ndim == 2 and output.shape[0] < output.shape[1]:
                    audio_for_spec = output.T  # Transpose if needed
                else:
                    audio_for_spec = output
                    
                if audio_for_spec.ndim == 1:
                    audio_for_spec = np.asfortranarray([audio_for_spec, audio_for_spec])
                
                spec = spec_utils.wave_to_spectrogram_old(audio_for_spec, hop_length=1024, n_fft=2048)
                spectrograms.append(spec)
            
            # Align spectrograms to same shape
            aligned_spectrograms = self._align_spectrograms(spectrograms)
            if not aligned_spectrograms:
                self._write_to_console(f"DEBUG: Failed to align spectrograms for spectral ensemble", "")
                return None
            
            # Apply spectral ensemble algorithm (similar to spec_utils.ensembling)
            result_spec = aligned_spectrograms[0]
            for i in range(1, len(aligned_spectrograms)):
                if is_max:
                    result_spec = np.where(np.abs(aligned_spectrograms[i]) >= np.abs(result_spec), 
                                         aligned_spectrograms[i], result_spec)
                else:
                    result_spec = np.where(np.abs(aligned_spectrograms[i]) <= np.abs(result_spec), 
                                         aligned_spectrograms[i], result_spec)
            
            # Convert back to audio
            result_audio = spec_utils.spectrogram_to_wave_old(result_spec, hop_length=1024)
            if result_audio.ndim == 2:
                result_audio = result_audio.T  # Transpose back if needed
                
            self._write_to_console(f"DEBUG: Spectral ensemble result shape: {result_audio.shape}", "")
            return result_audio
            
        except Exception as e:
            self._write_to_console(f"DEBUG: Error in spectral ensemble: {e}", "")
            return None

    def _create_process_data_for_chained_model(self, chained_model_data: ModelData, 
                                             input_audio_array: np.ndarray, 
                                             is_vocal_split: bool = False, is_pre_proc: bool = False,
                                             is_ensemble_run: bool = False, ensemble_audio_file_base: Optional[str] = None,
                                             for_demucs_sub_stem: Optional[str] = None 
                                             ) -> Dict[str, Any]:
        original_audio_base = Path(self.model_data.audio_file).stem if self.model_data.audio_file and not is_ensemble_run else ensemble_audio_file_base or "output"
        
        if is_pre_proc: chained_output_base = f"{original_audio_base}_(PreProcessedWith_{chained_model_data.model_basename})"
        elif is_ensemble_run: chained_output_base = f"{original_audio_base}_ens_member_{chained_model_data.model_basename}"
        elif for_demucs_sub_stem: chained_output_base = f"{original_audio_base}_{self.model_data.model_basename}_{for_demucs_sub_stem}_then_{chained_model_data.model_basename}"
        else: chained_output_base = f"{original_audio_base}_{self.model_data.model_basename}_then_{chained_model_data.model_basename}"
        
        return {
            'audio_file': None, 'input_audio_array': input_audio_array, 'audio_file_base': chained_output_base, 
            'export_path': self.model_data.export_path, 'set_progress_bar': self._set_progress_bar_callback, 
            'write_to_console': self._write_to_console, 'cached_source_callback': self._cached_source_callback, 
            'cached_model_source_holder': self._cached_model_source_holder, 'is_4_stem_ensemble': False, 
            'list_all_models': [self.model_data.model_basename, chained_model_data.model_basename], 
            'process_iteration': self._process_iteration, '_is_running_check': lambda: self._is_running,
            'is_ensemble_master': False, 'is_vocal_split_model_call': is_vocal_split 
        }

    def _get_separator_for_model(self, model_data_obj: ModelData, process_data_dict: Dict[str, Any]) -> Optional[Any]:
        if not model_data_obj or not model_data_obj.model_status:
            self._write_to_console(f"Cannot create separator: ModelData for {model_data_obj.model_name if model_data_obj else 'unknown'} is invalid or missing.", ""); return None
        if process_data_dict.get('input_audio_array') is not None: process_data_dict['audio_file'] = None 
        elif model_data_obj == self.model_data: 
             process_data_dict['audio_file'] = self.model_data.audio_file 
             process_data_dict['input_audio_array'] = None
        if model_data_obj.process_method == ac.VR_ARCH_TYPE: return SeperateVRLogic(model_data=model_data_obj, process_data=process_data_dict)
        elif model_data_obj.process_method == ac.MDX_ARCH_TYPE:
            if model_data_obj.is_mdx_c: return SeperateMDXCLogic(model_data=model_data_obj, process_data=process_data_dict)
            else: return SeperateMDXLogic(model_data=model_data_obj, process_data=process_data_dict)
        elif model_data_obj.process_method == ac.DEMUCS_ARCH_TYPE: return SeperateDemucsLogic(model_data=model_data_obj, process_data=process_data_dict)
        self._write_to_console(f"Unknown process method for separator: {model_data_obj.process_method}", ""); return None

    def stop(self): self._is_running = False

class ProcessingThread(QThread): 
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)
    def __init__(self, settings_dict: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.settings_dict = settings_dict
        self.worker: Optional[RealProcessingWorker] = None
    def run(self):
        try:
            self.worker = RealProcessingWorker(self.settings_dict)
            self.worker.progress_updated.connect(self.progress_updated)
            self.worker.processing_finished.connect(self.processing_finished)
            self.worker.run()
        except Exception as e:
            self.processing_finished.emit(False, f"Thread error: {str(e)}\n{traceback.format_exc()}")
    def stop_processing(self):
        if self.worker: self.worker.stop()
