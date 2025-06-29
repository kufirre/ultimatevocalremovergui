"""
Audio utility functions and context managers for UVR processing.

This module contains reusable audio utilities including context managers for
temporary file/directory management and GPU memory cleanup.
"""

import gc
import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Generator

import numpy as np
import soundfile as sf
import torch

from . import app_constants as ac
from .logger_utils import get_logger

logger = get_logger(__name__)


@contextmanager
def temporary_audio_file(audio: np.ndarray) -> Generator[str, None, None]:
    """Context manager for temporary audio files with automatic cleanup.

    Args:
        audio: Audio array to save to temporary file

    Yields:
        str: Path to the temporary audio file
    """
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_file_path = f.name
            # Ensure audio is in correct format for saving
            if audio.ndim == 1:
                # Mono audio
                sf.write(temp_file_path, audio, ac.DEFAULT_SAMPLE_RATE)
            elif audio.ndim == 2:
                if audio.shape[0] == 2:
                    # (2, N) format - transpose to (N, 2) for soundfile
                    sf.write(temp_file_path, audio.T, ac.DEFAULT_SAMPLE_RATE)
                else:
                    # (N, 2) format - use as is
                    sf.write(temp_file_path, audio, ac.DEFAULT_SAMPLE_RATE)

        yield temp_file_path

    except Exception as e:
        logger.warning(f"Error creating temporary audio file: {e}")
        # Fallback: try with simple format
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_file_path = f.name
            if audio.ndim == 2 and audio.shape[0] == 2:
                sf.write(temp_file_path, audio.T, ac.DEFAULT_SAMPLE_RATE)
            else:
                sf.write(temp_file_path, audio, ac.DEFAULT_SAMPLE_RATE)

        yield temp_file_path

    finally:
        # Cleanup temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary audio file: {temp_file_path}")
            except OSError as e:
                logger.warning(
                    f"Failed to clean up temporary audio file {temp_file_path}: {e}"
                )


@contextmanager
def temporary_directory(prefix: str = "temp_") -> Generator[str, None, None]:
    """Context manager for temporary directories with automatic cleanup.

    Args:
        prefix: Prefix for the temporary directory name

    Yields:
        str: Path to the temporary directory
    """
    temp_dir_path = None
    try:
        temp_dir_path = tempfile.mkdtemp(prefix=prefix)
        yield temp_dir_path
    finally:
        # Cleanup temporary directory
        if temp_dir_path and os.path.exists(temp_dir_path):
            try:
                shutil.rmtree(temp_dir_path, ignore_errors=True)
                logger.debug(f"Cleaned up temporary directory: {temp_dir_path}")
            except OSError as e:
                logger.warning(
                    f"Failed to clean up temporary directory {temp_dir_path}: {e}"
                )


@contextmanager
def gpu_memory_management() -> Generator[None, None, None]:
    """Context manager for GPU memory cleanup."""
    try:
        yield
    finally:
        # Clear GPU cache if available
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                logger.debug("Cleared GPU cache")
            except Exception as e:
                logger.debug(f"Could not clear GPU cache: {e}")

        # Force garbage collection
        gc.collect() 