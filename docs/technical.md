# Technical Documentation

## Architecture Overview

### 🎯 System Architecture Diagrams

This section provides visual representations of the system architecture to complement the technical descriptions below.

#### Overall System Architecture
![System Architecture](images/diagrams/01_system_architecture.png)

The application follows a **layered architecture** with clear separation between the application layer, UI layer (MVP pattern), core business logic, and external dependencies.

#### MVP Pattern Implementation  
![MVP Pattern](images/diagrams/02_mvp_pattern.png)

The UI layer implements the **Model-View-Presenter (MVP)** pattern for maintainable, testable code with clean separation of concerns.

#### Core Processing Pipeline
![Processing Pipeline](images/diagrams/03_processing_pipeline.png)

Audio processing follows a **robust, threaded pipeline** from user interaction through settings validation, thread creation, model loading, audio processing, and result handling.

#### Model Management System
![Model Management](images/diagrams/04_model_management.png)

Sophisticated **model lifecycle management** with dynamic loading, smart caching, download management, version handling, and resource optimization.

#### Audio Processing Components
![Audio Processing](images/diagrams/05_audio_processing.png)  

**Multi-architecture audio separation** pipeline supporting VR Architecture, MDX-Net, Demucs, and Ensemble modes with optimized inference.

#### Signal/Slot Communication
![Signal-Slot Communication](images/diagrams/06_signal_slot.png)

**Event-driven architecture** using Qt's signal/slot mechanism for loose coupling, type safety, thread safety, and extensibility.

> 📋 **For detailed UML documentation**: See [Architecture Diagrams](architecture_diagrams.md)
> 
> 🎨 **To generate/modify diagrams**: See [Diagram Generation Guide](diagram_generation_guide.md)
> 
> 🌐 **Online diagram editor**: Use [Mermaid Live Editor](https://mermaid.live/) with diagram code from architecture_diagrams.md

### Core Components
- **PySide6 GUI**: Modern Qt-based user interface with professional resource management
- **PyTorch Backend**: Deep learning framework for model inference with GPU acceleration
- **Multi-model Support**: VR, MDX-Net, and Demucs architectures with automatic V3/V4 handling
- **Threaded Processing**: Non-blocking audio processing with comprehensive progress feedback
- **Quality Assurance**: Enterprise-grade testing and automated regression prevention

### Key Modules

#### Core Processing Engine
- **`uvr_core_adapter.py`**: Main coordinator class managing model discovery and processing
- **`model_data.py`**: Model configuration and metadata management with V3/V4 detection
- **Separation Logic Modules** (Modularized for better maintainability):
  - **`separate_logic_base.py`**: Common helper functions and base SeparatorAttributesLogic class
  - **`separate_vr_logic.py`**: VR architecture audio separation implementation  
  - **`separate_mdx_logic.py`**: MDX-Net architecture implementation with ONNX support
  - **`separate_mdxc_logic.py`**: MDX-C architecture implementation for checkpoint models
  - **`separate_demucs_logic.py`**: Demucs architecture implementation (v1/v2/v3/v4 support)
- **`processing_worker.py`**: Threaded processing with progress tracking and error handling
- **`model_downloader.py`**: Automated model downloading with intelligent directory placement

#### User Interface
- **`main_window_view.py`**: Main application window with PySide6 components
- **`main.py`**: Application entry point with QRC resource management
- **`resources_rc.py`**: Compiled Qt resources (fonts, stylesheets, icons)
- **UI Presenters**: MVP pattern implementation for clean separation of concerns

#### Configuration & Utilities
- **`app_constants.py`**: Centralized configuration with comprehensive constants
- **`logger_utils.py`**: Professional logging system with configurable levels
- **`download_worker.py`**: Background download management with progress tracking

## Testing Infrastructure

### Current Test Coverage
- **341+ total tests** across 12 test modules
- **57% code coverage** (significantly exceeds 15% minimum requirement)
- **100% test success rate** after comprehensive bug fixes
- **Critical functionality protection** with automated regression prevention

### Enhanced Test Organization
```
tests/unit/core/
├── test_app_constants.py                    # Configuration constants (45 tests)
├── test_application_startup.py             # Critical functionality (6 tests) 🆕
├── test_model_data.py                       # Model configuration (50 tests)
├── test_separate_logic.py                   # Separation algorithms (44 tests)
├── test_processing_worker.py                # Threaded processing (31 tests)
├── test_uvr_core_adapter.py                # Main coordinator (64 tests)
├── test_model_downloader.py                 # Download management (18 tests)
├── test_download_worker.py                  # Download threads (23 tests)
├── test_logger_utils.py                     # Logging system (29 tests)
├── test_demucs_v3_v4_directory_placement.py # V3/V4 handling (24 tests)
└── test_demucs_secondary_stem_fix.py        # Bug fix verification (16 tests)
```

### Critical Functionality Protection System 🆕

The project now includes a **Critical Functionality Protection System** that prevents regressions through automated testing:

#### Protected Functionality
- ✅ **QRC Resource Loading**: Fonts, stylesheets, and UI assets
- ✅ **Core Module Imports**: Essential dependencies and module structure
- ✅ **Application Startup**: Initialization sequence and component creation
- ✅ **Model Loading Pipeline**: Download, detection, and inference preparation
- ✅ **UI Component Creation**: Main window and critical interface elements

#### Protection Mechanisms
```bash
# Critical tests (run before every commit)
pytest tests/unit/core/test_application_startup.py -m critical

# Pre-commit verification (blocks breaking commits)
./scripts/pre-commit-checks.sh

# Complete quality pipeline
./scripts/check-all.sh
```

### Test Execution Methods

```bash
# Complete test suite
./run_tests.sh --all

# Test categories
pytest -m unit           # Unit tests (fast execution)
pytest -m integration    # Integration tests
pytest -m critical       # Critical functionality tests 🆕
pytest -m edge_case      # Edge cases and error conditions

# Coverage reporting
pytest tests/ --cov=uvr_pyside6_ui --cov-report=html --cov-report=xml

# Specific functionality
pytest tests/unit/core/test_application_startup.py -v  # Critical tests
pytest tests/unit/core/test_separate_logic.py -v       # Core algorithms
pytest tests/unit/core/test_demucs_v3_v4_directory_placement.py -v  # V3/V4 handling
```

## Recent Major Improvements

### QRC Resource Management Fix 🔧
- **Issue**: Resource loading warnings due to missing `resources_rc` import
- **Root Cause**: Import optimization tools removing "unused" critical imports
- **Solution**: Protected import with `# noqa: F401` and systematic resource verification
- **Impact**: Eliminated all QRC resource warnings; fonts and stylesheets load perfectly
- **Tests**: 6 comprehensive tests ensure resource loading never breaks again

### Demucs V3/V4 Directory Management 🚀
- **Enhancement**: Intelligent automatic placement of V3/V4 models in `v3_v4_repo` subdirectory
- **Detection Logic**: Analyzes model names and file extensions (.yaml triggers V3/V4 placement)
- **Directory Structure**: 
  ```
  models/Demucs_Models/
  ├── v1_v2_models.th          # Legacy models in root
  └── v3_v4_repo/              # V3/V4 models auto-organized
      ├── htdemucs_v4.yaml     # V4 models
      └── mdx_extra_v3.yaml    # V3 models
  ```
- **Tests**: 24 comprehensive tests covering all placement scenarios

### Separation Logic Modularization 📁
- **Architecture**: Split monolithic 2172-line `separate_logic.py` into 5 logical modules
- **Modular Structure**: 
  ```
  src/uvr_pyside6_ui/core/
  ├── separate_logic_base.py     # Common utilities and base class (helper functions)
  ├── separate_vr_logic.py       # VR architecture implementation
  ├── separate_mdx_logic.py      # MDX-Net ONNX implementation  
  ├── separate_mdxc_logic.py     # MDX-C checkpoint implementation
  └── separate_demucs_logic.py   # Demucs v1/v2/v3/v4 implementation
  ```
- **Maintainability**: Better separation of concerns, improved code organization
- **Backward Compatibility**: Preserved all functionality with compatibility namespace
- **Test Coverage**: Updated 467 tests to work with new modular structure
- **Benefits**: Easier debugging, focused development, cleaner architecture

### Critical Bug Fixes Resolved

#### AC.NO_STEM Attribution Error (Fixed) ✅
- **Issue**: `AttributeError: module 'app_constants' has no attribute 'NO_STEM'`
- **Impact**: Application crashed during single-instrument Demucs separation
- **Root Cause**: Reference to non-existent constant in secondary stem logic
- **Fix**: Changed `md.secondary_stem != ac.NO_STEM` to `not md.secondary_stem.startswith("No ")`
- **Verification**: 16 regression tests ensure this specific crash never recurs

#### Version Detection Logic (Enhanced) 🔧
- **Issue**: Models like "v3 | mdx_extra" incorrectly detected as V4
- **Root Cause**: Version detection only executed when model files existed locally
- **Solution**: Moved detection logic to `__post_init__()` to ensure consistent execution
- **Result**: Accurate V1/V2/V3/V4 detection regardless of file presence
- **Coverage**: Comprehensive version detection tests for all edge cases

## Quality Assurance Infrastructure

### Automated Quality Pipeline

The project maintains enterprise-grade code quality through a multi-layered approach:

#### Layer 1: Code Formatting & Organization
```bash
# Automated formatting pipeline
./scripts/format.sh
```
- **Black**: Code formatting with 88-character line length
- **Ruff**: Import organization and auto-fixable linting
- **Consistency**: Ensures uniform code style across the entire codebase

#### Layer 2: Comprehensive Linting
```bash
# Multi-tool linting pipeline
./scripts/lint.sh
```
- **Ruff**: Fast Python linting (replaces flake8, pycodestyle, pyflakes)
- **MyPy**: Static type checking (disabled for legacy compatibility)
- **Bandit**: Security vulnerability scanning with project-specific rules
- **Flake8**: Additional style validation with reasonable exceptions

#### Layer 3: Critical Functionality Verification 🆕
```bash
# Pre-commit protection
./scripts/pre-commit-checks.sh
```
- **Critical Tests**: Essential functionality verification
- **Import Smoke Tests**: Core module import verification
- **Fast Linting**: Immediate feedback on code quality issues
- **Commit Blocking**: Prevents broken code from entering the repository

#### Layer 4: Complete Quality Assurance
```bash
# Comprehensive quality pipeline
./scripts/check-all.sh
```
- **Full Test Suite**: All 341+ tests with coverage reporting
- **Quality Metrics**: Code coverage, security analysis, and performance monitoring
- **Integration Verification**: End-to-end functionality testing

### Quality Standards & Metrics

#### Code Quality Standards
- **Line Length**: 88 characters maximum (Black standard)
- **Import Organization**: Grouped and sorted by Ruff/isort
- **Type Coverage**: Progressive improvement with MyPy
- **Security**: Zero high-confidence Bandit issues
- **Test Coverage**: Minimum 15% (currently 57%)

#### Tool Configuration (pyproject.toml)
```toml
[tool.ruff]
target-version = "py38"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "S3"]  # Essential rules only
ignore = ["E402", "F841", "E501"]   # Reasonable exceptions

[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310', 'py311', 'py312']

[tool.pytest.ini_options]
markers = [
    "critical: Critical tests that must pass for basic functionality",
    # ... other markers
]
```

### Development Workflow Integration

#### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
- repo: local
  hooks:
  - id: black
  - id: ruff
  - id: ruff-format  
  - id: mypy
  - id: bandit
  - id: critical-tests  # Ensures core functionality always works
```

#### Makefile Shortcuts
```makefile
# Quality assurance targets
make format          # Format code with Black + Ruff
make lint           # Run all linting tools
make test-critical  # Run critical functionality tests
make pre-commit     # Pre-commit verification
make check-all      # Complete quality pipeline
```

## Dependencies & Installation

### Core Runtime Dependencies
- **PySide6**: Qt-based GUI framework (6.4.0+)
- **PyTorch**: ML model inference (1.13.0+) with CUDA/MPS support
- **Audio Processing**: librosa, soundfile, scipy for audio manipulation
- **Model Support**: onnxruntime, onnx2pytorch for various model formats
- **Configuration**: omegaconf, pyyaml, ml-collections for model configs

### Development Dependencies
```bash
# Testing framework
pytest>=7.4.0, pytest-qt>=4.4.0, pytest-cov>=4.1.0

# Quality assurance tools
black>=23.0.0, ruff>=0.1.0, mypy>=1.5.0, bandit>=1.7.0

# Pre-commit integration
pre-commit>=3.0.0
```

### Installation Options
```bash
# Basic installation
pip install -e .

# Development with quality tools
pip install -e ".[dev]"

# GPU acceleration support
pip install -e ".[gpu]"

# Complete development setup
pip install -e ".[dev,gpu]" && pre-commit install
```

## Performance & Optimization

### Memory Management
- **Configurable segment sizes**: 256/512/1024 for different VRAM capacities
- **Progressive loading**: Handles large audio files without memory overflow
- **Automatic cleanup**: Proper disposal of temporary audio arrays
- **Low memory mode**: `UVR_LOW_MEMORY=1` for resource-constrained systems

### GPU Acceleration Support
- **CUDA**: Nvidia GPU support with automatic detection
- **MPS**: Apple Silicon acceleration (M1/M2/M3 Macs)
- **Fallback**: Automatic CPU processing when GPU unavailable
- **Memory monitoring**: Intelligent VRAM usage optimization

### Threading Architecture
- **Main UI Thread**: Remains responsive during all operations
- **Background Workers**: Model downloading, loading, and processing
- **Progress Signals**: Real-time feedback for all long-running operations
- **Clean Shutdown**: Proper thread cleanup and resource management

## Environment Configuration

### Environment Variables
```bash
# Debug and logging
UVR_DEBUG=1                    # Enable debug logging
UVR_LOG_LEVEL=INFO            # Set log level

# Path configuration  
UVR_MODEL_DIR=/path/to/models  # Custom model directory
UVR_CACHE_DIR=/path/to/cache   # Custom cache directory

# Performance tuning
UVR_NO_GPU=1                   # Force CPU processing
UVR_LOW_MEMORY=1               # Memory optimization mode
UVR_DEFAULT_SEGMENT_SIZE=256   # Default segment size

# GPU configuration
CUDA_VISIBLE_DEVICES=0         # Specific GPU selection
PYTORCH_ENABLE_MPS_FALLBACK=1  # MPS fallback (macOS)
```

### Configuration Files
- **Settings**: Platform-specific user preference storage
  - Windows: `%APPDATA%/UVR-PySide6/settings.json`
  - macOS: `~/Library/Application Support/UVR-PySide6/settings.json`
  - Linux: `~/.config/UVR-PySide6/settings.json`

## Development Guidelines

### Code Standards
- **Type Hints**: Required for all public functions and methods
- **Docstrings**: Google-style documentation for all public APIs
- **Error Handling**: Comprehensive exception handling with user-friendly messages
- **Logging**: Structured logging throughout the application
- **Testing**: Unit tests required for all new functionality

### Contribution Workflow
1. **Setup**: Clone repository and install with `pip install -e ".[dev]"`
2. **Pre-commit**: Install hooks with `pre-commit install`
3. **Development**: Make changes with appropriate tests
4. **Quality**: Run `make check-all` before committing
5. **Commit**: Pre-commit hooks automatically verify quality
6. **Review**: Submit PR with comprehensive description

### Quality Gates
- ✅ **Critical Tests**: Must pass (blocks commits if failing)
- ✅ **Linting**: No critical issues from Ruff
- ✅ **Formatting**: 100% Black compliance
- ✅ **Security**: No high-confidence Bandit issues
- ✅ **Type Safety**: Progressive MyPy improvement

## Monitoring & Debugging

### Logging System
```python
# Professional logging throughout the application
from uvr_pyside6_ui.core.logger_utils import get_logger

logger = get_logger("module_name")
logger.info("Operation completed successfully")
logger.error("Error details", exc_info=True)
```

### Debug Mode
```bash
# Enable comprehensive debug logging
export UVR_DEBUG=1
uvr-gui 2>&1 | tee debug.log

# Application performance monitoring
export UVR_PROFILE=1  # Performance profiling (if implemented)
```

### Error Tracking
- **Structured Logging**: Consistent log format across all modules
- **Exception Handling**: Comprehensive error capture with context
- **User Feedback**: Clear error messages for end-user troubleshooting
- **Debug Information**: Detailed technical information for developers

## Security Considerations

### Input Validation
- **File Path Sanitization**: Prevents directory traversal attacks
- **Audio File Validation**: Checks file integrity before processing
- **Model URL Verification**: Validates download sources
- **Configuration Validation**: Ensures safe configuration values

### Dependency Security
- **Bandit Scanning**: Automated security vulnerability detection
- **Dependency Updates**: Regular updates for security patches
- **Minimal Privileges**: Application runs with minimal required permissions
- **Safe Defaults**: Secure default configuration values

## Future Development

### Planned Enhancements
- **Real-time Processing**: Live audio separation capabilities
- **Performance Optimization**: Further memory and speed improvements
- **Additional Models**: Support for emerging separation architectures
- **Advanced UI**: Spectrogram visualization and audio editing features
- **Cloud Integration**: Optional cloud-based model inference

### Technical Debt
- **Legacy Code**: Gradual modernization of inherited components
- **Type Coverage**: Progressive improvement of type annotations
- **Test Coverage**: Expansion to achieve >80% coverage target
- **Documentation**: Continuous improvement of technical documentation 

## Recent Improvements ✨

### **Enhanced Settings System** (January 2025)
- **Corrected 3-Tab Structure**: Now properly matches original UVR structure
  - **Settings Guide Tab**: General menu selection, help hints, app updates, settings management
  - **Additional Settings Tab**: Audio format (WAV/MP3), processing options, GPU settings, sample mode
  - **Download Center Tab**: Model selection with radio buttons, real-time progress tracking
- **Authentic UVR Interface**: Radio button model selection (VR Arch, MDX-Net, Demucs) with dropdowns
- **Fixed Download Progress**: Separate info label, percentage label, and progress bar updates
- **Professional UI Components**: QGroupBox organization, proper spacing, comprehensive functionality
- **Persistent Configuration**: All settings properly save and restore across sessions

### **Progress Bar & Download Fixes** (January 2025)
- **Reverted Progress Bar Styling**: Simplified to original working styling
- **Enhanced Download Progress**: Fixed signal connections and progress visibility
- **UI Update Mechanisms**: Improved progress percentage and status message display
- **Download Center Integration**: Modern download interface with real-time progress tracking

### **Cross-Platform Compatibility** (January 2025)
- **macOS Compatibility Fixes**: Resolved NSOpenPanel warnings and font issues
- **Font System Improvements**: Better font loading with proper fallbacks
- **High DPI Support**: Enhanced scaling for modern displays
- **Native Dialog Integration**: Proper macOS native dialog behavior

### **Font & Styling Enhancements** (January 2025)
- **Eliminated Font Warnings**: Replaced problematic Courier font references
- **Better Font Fallbacks**: Comprehensive font family chain for cross-platform compatibility
- **Modern Font Loading**: Dynamic font family detection and application
- **Enhanced QSS Styling**: Improved widget-specific styling with better organization

## Architecture Overview 🏛️ 