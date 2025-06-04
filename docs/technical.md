# Technical Documentation

## Architecture Overview

### Core Components
- **PySide6 GUI**: Modern Qt-based user interface replacing tkinter
- **PyTorch Backend**: Deep learning framework for model inference
- **Multi-model Support**: VR, MDX-Net, and Demucs architectures
- **Threaded Processing**: Non-blocking audio processing with progress feedback

### Key Modules
- `uvr_core_adapter.py`: Main coordinator class managing model discovery and processing
- `model_data.py`: Model configuration and metadata management
- `separate_logic.py`: Core audio separation algorithms for each model type
- `processing_worker.py`: Threaded processing with progress tracking
- `model_downloader.py`: Automated model downloading and management

## Testing Infrastructure

### Test Coverage
- **335+ total tests** across 11 test modules
- **32.96% code coverage** (exceeds 15% minimum requirement)
- **100% test success rate** after bug fixes
- Professional pytest configuration with Qt integration

### Test Organization
```
tests/unit/core/
├── test_app_constants.py       # Configuration constants (45 tests)
├── test_model_data.py         # Model configuration (24 tests)  
├── test_separate_logic.py     # Separation algorithms (12 tests)
├── test_processing_worker.py  # Threaded processing (39 tests)
├── test_uvr_core_adapter.py  # Main coordinator (47 tests)
├── test_model_downloader.py   # Download management (26 tests)
├── test_download_worker.py    # Download threads (23 tests)
├── test_logger_utils.py       # Logging system (29 tests)
├── test_demucs_v3_v4_directory_placement.py  # V3/V4 handling (24 tests)
└── test_demucs_secondary_stem_fix.py         # Bug fix verification (16 tests)
```

### Running Tests
```bash
# All tests
python -m pytest tests/unit/core/ -v

# With coverage
python -m pytest tests/unit/core/ -v --cov=src --cov-report=html

# Specific test suite  
python -m pytest tests/unit/core/test_separate_logic.py -v

# Using convenience script
./run_tests.sh
```

## Recent Bug Fixes

### Critical ac.NO_STEM Bug (Fixed)
- **Issue**: `AttributeError: module 'app_constants' has no attribute 'NO_STEM'`
- **Impact**: Crashed single instrument Demucs separation
- **Fix**: Changed `md.secondary_stem != ac.NO_STEM` to `not md.secondary_stem.startswith("No ")`
- **Tests**: 16 comprehensive tests ensure regression prevention

### Demucs Version Detection (Fixed)
- **Issue**: Models like "v3 | mdx_extra" incorrectly detected as V4
- **Root Cause**: Version detection only ran when model files existed
- **Fix**: Moved detection logic to `__post_init__()` to always run
- **Result**: Proper V1/V2/V3/V4 detection regardless of file existence

### V3/V4 Directory Placement (Enhanced)
- **Enhancement**: Automatic placement of V3/V4 models in `v3_v4_repo` subdirectory
- **Logic**: Detects v3/v4 in model name or .yaml extension
- **Tests**: 24 tests covering directory creation, file placement, and path resolution

## Dependencies

### Core Runtime
- **PySide6**: Qt-based GUI framework
- **PyTorch**: ML model inference
- **librosa**: Audio analysis and processing
- **onnxruntime**: ONNX model support
- **soundfile**: Audio I/O operations

### Development Tools
- **pytest**: Testing framework with Qt support
- **pytest-cov**: Code coverage analysis
- **black/ruff**: Code formatting and linting
- **mypy**: Static type checking

### Installation
```bash
# Production
pip install -e .

# Development with testing tools
pip install -e ".[dev]"

# GPU acceleration (optional)
pip install -e ".[gpu]"
```

## Performance Considerations

### Memory Management
- Configurable segment/window sizes to prevent OOM errors
- Automatic cleanup of temporary audio data
- Progressive loading for large audio files

### GPU Acceleration
- CUDA support for Nvidia GPUs (8GB+ VRAM recommended)
- MPS support for Apple Silicon Macs
- Automatic fallback to CPU processing

### Threading Architecture
- Main UI thread remains responsive during processing
- Background worker threads for model loading and separation
- Progress signals for real-time feedback

## Development Guidelines

### Code Quality
- Type hints throughout codebase
- Comprehensive error handling with user-friendly messages
- Consistent logging for debugging and monitoring
- Modular architecture for easy testing and maintenance

### Testing Standards
- Unit tests for all core functionality
- Integration tests for end-to-end workflows
- Mock-based testing to avoid heavy model dependencies
- Qt signal testing for UI interactions
- Regression tests for all critical bug fixes

### Configuration
- All model paths and settings configurable
- Persistent user preferences
- Environment-specific settings support
- Comprehensive logging configuration 