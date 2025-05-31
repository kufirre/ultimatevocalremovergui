"""
Real processing worker that wraps the original UVR processing logic.
This replaces MockProcessingWorker with actual audio separation functionality.
"""
from PySide6.QtCore import QObject, Signal, QThread
from pathlib import Path
import traceback
from typing import Dict, Any, Optional

from .model_data import ModelData
from . import app_constants as ac

try:
    from .separate_logic import (
        SeperateVRLogic, SeperateMDXLogic, SeperateMDXCLogic, SeperateDemucsLogic,
        clear_gpu_cache_logic
    )
except ImportError as e:
    print(f"Warning: Could not import separation logic modules: {e}")
    SeperateVRLogic = None
    SeperateMDXLogic = None
    SeperateMDXCLogic = None
    SeperateDemucsLogic = None
    clear_gpu_cache_logic = None


class RealProcessingWorker(QObject):
    """
    Real processing worker that performs actual audio separation.
    Emits progress updates and completion signals.
    """
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)

    def __init__(self, settings_dict: Dict[str, Any]):
        super().__init__()
        self.settings = settings_dict
        self._is_running = True
        self.model_data: Optional[ModelData] = None
        self.progress_value = 0
        
        # Create ModelData from settings
        try:
            self.model_data = ModelData.from_settings_dict(settings_dict)
        except Exception as e:
            print(f"Error creating ModelData: {e}")
            self.model_data = None

    def run(self):
        """Main processing method."""
        if not self.model_data:
            self.processing_finished.emit(False, "Error: Could not create model data from settings")
            return
            
        if not self._is_running:
            self.processing_finished.emit(False, "Processing Canceled")
            return

        # Check if separation logic modules are available
        if not all([SeperateVRLogic, SeperateMDXLogic, SeperateMDXCLogic, SeperateDemucsLogic, clear_gpu_cache_logic]):
            self.processing_finished.emit(False, "Error: Separation logic modules not available. Check separate_logic.py and its imports.")
            return

        try:
            # Validate inputs
            if not self.model_data.audio_file:
                self.processing_finished.emit(False, "Error: No input audio file specified")
                return
                
            if not Path(self.model_data.audio_file).exists():
                self.processing_finished.emit(False, f"Error: Input file does not exist: {self.model_data.audio_file}")
                return
                
            if not self.model_data.export_path:
                self.processing_finished.emit(False, "Error: No export path specified")
                return
                
            if not Path(self.model_data.export_path).exists():
                self.processing_finished.emit(False, f"Error: Export directory does not exist: {self.model_data.export_path}")
                return

            # Check if model is selected and exists
            if not self.model_data.model_name or self.model_data.model_name == ac.CHOOSE_MODEL:
                self.processing_finished.emit(False, "Error: No model selected")
                return
                
            if not self.model_data.model_path or not Path(self.model_data.model_path).exists():
                self.processing_finished.emit(False, f"Error: Model file not found: {self.model_data.model_path}")
                return

            # Create process data dictionary (similar to original UVR.py)
            process_data = self._create_process_data()
            
            # Start processing based on method
            self.progress_updated.emit(10, "Initializing processing...")
            
            if self.model_data.process_method == ac.VR_ARCH_TYPE:
                self._process_vr_arch(process_data)
            elif self.model_data.process_method == ac.MDX_ARCH_TYPE:
                self._process_mdx_net(process_data)
            elif self.model_data.process_method == ac.DEMUCS_ARCH_TYPE:
                self._process_demucs(process_data)
            elif self.model_data.process_method == ac.ENSEMBLE_MODE:
                self.processing_finished.emit(False, "Error: Ensemble mode not yet implemented")
                return
            else:
                self.processing_finished.emit(False, f"Error: Unsupported processing method: {self.model_data.process_method}")
                return

        except Exception as e:
            error_msg = f"Processing failed with error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.processing_finished.emit(False, error_msg)

    def _create_process_data(self) -> Dict[str, Any]:
        """Create process data dictionary for the separation classes."""
        return {
            'audio_file': self.model_data.audio_file,
            'audio_file_base': Path(self.model_data.audio_file).stem,
            'export_path': self.model_data.export_path,
            'set_progress_bar': self._set_progress_bar,
            'write_to_console': self._write_to_console,
            'cached_source_callback': self._cached_source_callback,
            'cached_model_source_holder': self._cached_model_source_holder,
            'is_4_stem_ensemble': self.model_data.is_4_stem_ensemble,
            'list_all_models': [self.model_data.model_basename],
            'process_iteration': self._process_iteration,
            'is_ensemble_master': False,
        }

    def _set_progress_bar(self, base_progress: float, additional_progress: float = 0):
        """Update progress bar (callback for separation classes)."""
        if not self._is_running:
            return
        total_progress = int((base_progress + additional_progress) * 100)
        total_progress = min(max(total_progress, 0), 100)
        self.progress_updated.emit(total_progress, f"Processing... {total_progress}%")

    def _write_to_console(self, message: str, base_text: str = ""):
        """Write message to console (callback for separation classes)."""
        if not self._is_running:
            return
        full_message = f"{base_text}{message}" if base_text else message
        # Extract progress info if available
        if "%" in full_message:
            try:
                # Try to extract percentage from message
                import re
                match = re.search(r'(\d+)%', full_message)
                if match:
                    progress = int(match.group(1))
                    self.progress_updated.emit(progress, full_message)
                    return
            except:
                pass
        # Default progress update
        self.progress_updated.emit(self.progress_value, full_message)

    def _cached_source_callback(self, process_method: str, model_name: str = None):
        """Handle cached source callback (stub for now)."""
        return None, None

    def _cached_model_source_holder(self, process_method: str, sources, model_name: str = None):
        """Handle cached model source holder (stub for now)."""
        pass

    def _process_iteration(self):
        """Process iteration callback (stub for now)."""
        pass

    def _process_vr_arch(self, process_data: Dict[str, Any]):
        """Process using VR Architecture method."""
        if not self._is_running:
            return
            
        self.progress_updated.emit(20, "Loading VR model...")
        
        try:
            # Create VR separator
            separator = SeperateVRLogic( # Use SeperateVRLogic
                model_data=self.model_data,
                process_data=process_data
            )
            
            # Run separation
            self.progress_updated.emit(30, "Running VR separation...")
            result = separator.seperate() # This will call the ported logic
            
            if self._is_running:
                self.progress_updated.emit(100, "VR processing complete!")
                self.processing_finished.emit(True, "Successfully processed using VR Architecture")
                
        except Exception as e:
            self.processing_finished.emit(False, f"VR processing failed: {str(e)}\n{traceback.format_exc()}")
        finally:
            if clear_gpu_cache_logic: # Use renamed clear_gpu_cache_logic
                clear_gpu_cache_logic()
        
    def _process_mdx_net(self, process_data: Dict[str, Any]):
        """Process using MDX-Net method."""
        if not self._is_running:
            return
            
        self.progress_updated.emit(20, "Loading MDX-Net model...")
        
        try:
            # Choose the right MDX separator based on model type
            if self.model_data.is_mdx_c:
                separator = SeperateMDXCLogic( # Use SeperateMDXCLogic
                    model_data=self.model_data,
                    process_data=process_data
                )
            else:
                separator = SeperateMDXLogic( # Use SeperateMDXLogic
                    model_data=self.model_data,
                    process_data=process_data
                )
            
            # Run separation
            self.progress_updated.emit(30, "Running MDX-Net separation...")
            result = separator.seperate() # This will call the ported logic
            
            if self._is_running:
                self.progress_updated.emit(100, "MDX-Net processing complete!")
                self.processing_finished.emit(True, "Successfully processed using MDX-Net")
                
        except Exception as e:
            self.processing_finished.emit(False, f"MDX-Net processing failed: {str(e)}\n{traceback.format_exc()}")
        finally:
            if clear_gpu_cache_logic: # Use renamed clear_gpu_cache_logic
                clear_gpu_cache_logic()
        
    def _process_demucs(self, process_data: Dict[str, Any]):
        """Process using Demucs method."""
        if not self._is_running:
            return
            
        self.progress_updated.emit(20, "Loading Demucs model...")
        
        try:
            # Create Demucs separator
            separator = SeperateDemucsLogic( # Use SeperateDemucsLogic
                model_data=self.model_data,
                process_data=process_data
            )
            
            # Run separation
            self.progress_updated.emit(30, "Running Demucs separation...")
            result = separator.seperate() # This will call the ported logic
            
            if self._is_running:
                self.progress_updated.emit(100, "Demucs processing complete!")
                self.processing_finished.emit(True, "Successfully processed using Demucs")
                
        except Exception as e:
            self.processing_finished.emit(False, f"Demucs processing failed: {str(e)}\n{traceback.format_exc()}")
        finally:
            if clear_gpu_cache_logic: # Use renamed clear_gpu_cache_logic
                clear_gpu_cache_logic()

    def stop(self):
        """Stop the processing."""
        self._is_running = False


class ProcessingThread(QThread):
    """
    Thread wrapper for the processing worker.
    """
    progress_updated = Signal(int, str)
    processing_finished = Signal(bool, str)

    def __init__(self, settings_dict: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.settings_dict = settings_dict
        self.worker: Optional[RealProcessingWorker] = None

    def run(self):
        """Run the processing in this thread."""
        try:
            self.worker = RealProcessingWorker(self.settings_dict)
            self.worker.progress_updated.connect(self.progress_updated)
            self.worker.processing_finished.connect(self.processing_finished)
            self.worker.run()
        except Exception as e:
            self.processing_finished.emit(False, f"Thread error: {str(e)}")

    def stop_processing(self):
        """Stop the processing worker."""
        if self.worker:
            self.worker.stop()
