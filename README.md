# Ultimate Vocal Remover GUI - PySide6 Edition

<img src="gui_data/img/pyside6-port.png" />

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Qt Framework](https://img.shields.io/badge/Qt-PySide6-green)](https://pyside.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-341%20passing-green)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-57%25-yellow)](htmlcov/index.html)
[![Quality](https://img.shields.io/badge/code%20quality-excellent-brightgreen)](scripts/)

## About

A **professional, modern rewrite** of the Ultimate Vocal Remover GUI using **PySide6** and **PyTorch**. This application provides **state-of-the-art audio source separation** with a beautiful, responsive Qt-based interface, enterprise-grade code quality, and comprehensive testing.

> 🔥 **Latest Update**: Added critical functionality protection system that prevents regressions through automated testing and quality assurance.

### ✨ Key Features

- 🎵 **Advanced AI Models**: VR, MDX-Net, and Demucs architectures for superior separation quality
- 🖥️ **Modern Interface**: Professional PySide6/Qt GUI with custom styling and resource management
- ⚡ **GPU Acceleration**: CUDA support for Nvidia GPUs and MPS for Apple Silicon
- 🧵 **Threaded Processing**: Non-blocking UI with real-time progress feedback
- 📦 **Smart Model Management**: Automatic model downloading, organization, V3/V4 handling, and VIP premium model access
- 🔒 **VIP Premium Models**: Access to exclusive high-quality models with code-based authentication
- 🔧 **Highly Configurable**: Extensive settings for fine-tuning separation quality
- 🧪 **Enterprise Quality**: 341+ tests with 57% coverage and automated quality assurance
- 🛡️ **Regression Protection**: Critical functionality tests prevent breaking changes

### 🔍 Quick Architecture Tour

Want to understand how this application works? Start here:

1. **📊 View Architecture**: Scroll down to the [🏗️ Architecture](#🏗️-architecture) section for visual system overview
2. **🎮 Interactive Diagrams**: Open `scripts/diagram_generator.html` in your browser for interactive exploration
3. **📋 Detailed Documentation**: Check out `docs/architecture_diagrams.md` for complete UML specifications
4. **🔧 Technical Deep Dive**: See `docs/technical.md` for implementation details

### 🎶 Supported Separation Types

- **Vocal Isolation**: Remove or isolate vocals from music tracks
- **Instrumental Extraction**: Extract clean backing tracks without vocals  
- **Multi-stem Separation**: Separate drums, bass, vocals, and other instruments
- **Custom Ensembles**: Combine multiple models for enhanced separation quality
- **Format Support**: WAV, FLAC, MP3, and more with high-quality output

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/kufirre/ultimatevocalremovergui.git
cd ultimatevocalremovergui

# Create virtual environment (recommended)
python -m venv uvr-env
source uvr-env/bin/activate  # On Windows: uvr-env\Scripts\activate

# Install the application
pip install -e ".[dev]"  # With development tools
# OR
pip install -e .         # Basic installation
```

### 2. Launch the Application

```bash
# Using the installed command
uvr-gui

# OR using Python directly
python -m uvr_pyside6_ui.main

# OR using the legacy entry point
python UVR.py
```

### 3. Basic Workflow

1. **📁 Select Audio File**: Click the input file browser to choose your audio
2. **🤖 Choose Model**: Select a separation model from the dropdown
3. **⚙️ Configure Settings**: Adjust segment size, overlap, and other parameters
4. **▶️ Start Processing**: Click "Start Processing" to begin separation
5. **📊 Monitor Progress**: Watch real-time progress in the status bar
6. **📂 Get Results**: Find separated stems in the output directory

## 📋 System Requirements

### Minimum Requirements
- **Python**: 3.8+ (3.10+ recommended)
- **OS**: Windows 10+, macOS 11+, or modern Linux
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 5GB+ for models and processing cache
- **Network**: Internet connection for model downloads

### GPU Acceleration (Optional but Recommended)
- **Nvidia**: GTX 1060 6GB minimum, RTX series recommended (8GB+ VRAM)
- **Apple Silicon**: M1/M2/M3 Macs with automatic MPS acceleration
- **AMD**: Limited support (CPU fallback recommended)

## 🔧 Installation Options

### Option 1: Development Installation (Recommended)

Perfect for users who want the latest features and developers:

```bash
# Clone and setup
git clone https://github.com/kufirre/ultimatevocalremovergui.git
cd ultimatevocalremovergui

# Virtual environment (highly recommended)
python -m venv uvr-env

# Activate virtual environment
# Windows:
uvr-env\Scripts\activate
# macOS/Linux:
source uvr-env/bin/activate

# Install with development tools
pip install -e ".[dev]"

# Set up pre-commit hooks (optional)
pre-commit install
```

### Option 2: Direct Installation

For users who want a simple pip install:

```bash
# Basic installation
pip install git+https://github.com/kufirre/ultimatevocalremovergui.git

# With GPU support
pip install "git+https://github.com/kufirre/ultimatevocalremovergui.git[gpu]"

# With development tools
pip install "git+https://github.com/kufirre/ultimatevocalremovergui.git[dev]"
```

### Option 3: Platform-Specific Setup

#### Windows Setup
```bash
# Install Visual C++ Build Tools (if needed)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Install Python dependencies
pip install -e ".[dev,gpu]"

# Add Windows Defender exclusions for model downloads (optional)
```

#### macOS Setup
```bash
# Install Xcode command line tools
xcode-select --install

# Install the application (MPS acceleration automatic on Apple Silicon)
pip install -e ".[dev]"
```

#### Linux (Ubuntu/Debian) Setup
```bash
# Install system dependencies
sudo apt update
sudo apt install python3-dev python3-venv ffmpeg qt6-base-dev

# Install the application
pip install -e ".[dev]"
```

## 🎛️ Usage Guide

### Starting the Application

The application can be launched in several ways:

```bash
# Method 1: Using the installed command (recommended)
uvr-gui

# Method 2: Using Python module directly
python -m uvr_pyside6_ui.main

# Method 3: Using the legacy entry point
python UVR.py

# Method 4: From source directory
cd src && python -m uvr_pyside6_ui.main
```

### Interface Overview

The PySide6 interface consists of several key sections:

1. **File Input/Output Section**: Select source audio and output directory
2. **Model Selection**: Choose from VR, MDX-Net, or Demucs models
3. **Processing Settings**: Configure separation parameters
4. **Advanced Settings**: Fine-tune model-specific parameters
5. **Processing Control**: Start/stop processing with progress monitoring

### Step-by-Step Separation Workflow

#### 1. File Selection
- Click **"Select Audio File"** to choose your input audio
- Supported formats: WAV, FLAC, MP3, M4A, OGG, and more
- File size: No strict limit, but 16GB+ files may require additional RAM

#### 2. Model Selection
Choose the appropriate model based on your needs:

- **VR (Vocal Remover) Models**: Best for vocal/instrumental separation
  - `UVR-MDX-NET-Vocal_FT`: High-quality vocal extraction
  - `UVR-MDX-NET-Inst_3`: Excellent instrumental extraction
  
- **MDX-Net Models**: Balanced quality and speed
  - `UVR_MDXNET_KARA_2`: Karaoke-focused separation
  - `UVR-MDX-NET-Inst_Main`: General-purpose instrumental
  
- **Demucs Models**: Best for multi-stem separation
  - `htdemucs`: 4-stem separation (vocals, drums, bass, other)
  - `htdemucs_ft`: Fine-tuned version with better quality

#### 3. Output Configuration
- **Output Directory**: Choose where separated files will be saved
- **Output Format**: Select WAV (highest quality) or FLAC (compressed lossless)
- **Sample Rate**: Typically 44.1kHz (CD quality) or 48kHz (professional)

#### 4. Processing Settings

**Segment Size**: 
- **256**: Fastest, uses less VRAM (4GB+ GPUs)
- **512**: Balanced speed and quality (6GB+ GPUs) 
- **1024**: Best quality, requires more VRAM (8GB+ GPUs)

**Overlap**:
- **0.25**: Faster processing, slight quality reduction
- **0.5**: Balanced (recommended)
- **0.75**: Slower but highest quality

#### 5. Advanced Settings (Model-Specific)

**VR Models**:
- **Window Size**: 1024 (default) or 512 for speed
- **Aggression Setting**: 5-20 (higher = more aggressive separation)
- **Post-Processing**: Enable for cleaner output

**MDX-Net Models**:
- **Overlap**: 0.25-0.75 (affects quality vs speed)
- **Segment Size**: 256-1024 (affects VRAM usage)

**Demucs Models**:
- **Shifts**: 0-10 (more shifts = better quality, slower processing)
- **Split**: Enables processing of extra-long files
- **Overlap**: 0.25-0.5 for optimal quality

### 📂 Model Management

Models are automatically managed by the application:

#### Automatic Downloads
- First-time model use triggers automatic download
- Progress shown with download status and speed
- Models cached locally for future use

#### Model Organization
```
models/
├── VR_Models/           # VR architecture models
├── MDX_Net_Models/      # MDX-Net models  
├── Demucs_Models/       # Demucs v1/v2 models
│   └── v3_v4_repo/      # Demucs v3/v4 models (auto-organized)
└── Ensemble_Models/     # Custom ensemble configurations
```

#### Model Directories
- **VR Models**: `.pth` files for vocal removal models
- **MDX-Net Models**: `.onnx` files for balanced separation
- **Demucs Models**: Automatically organized by version
  - V1/V2: Main Demucs directory
  - V3/V4: `v3_v4_repo/` subdirectory (automatically detected)

#### 🔒 VIP Premium Models

The application supports exclusive **VIP premium models** with enhanced separation quality and advanced features.

**How VIP Access Works**:
1. **Secure Authentication**: VIP models use cryptographic verification with access codes
2. **Enhanced Catalog**: VIP users get access to additional premium models not available publicly
3. **Automatic Integration**: VIP models seamlessly integrate with the standard interface
4. **Backward Compatibility**: Standard functionality remains unchanged for non-VIP users

**VIP Model Types**:
- **🔒 VIP VR Premium**: Ultra-high-quality vocal removal models
- **🔒 VIP MDX Premium**: Advanced separation models with superior algorithms  
- **🔒 VIP MDX23C**: Next-generation MDX23C models with cutting-edge architecture
- **🔒 VIP Demucs**: Enhanced multi-stem separation models

**Accessing VIP Models**:
1. Open the **Download Center** in the application
2. Click the **"Get VIP Access"** button
3. Enter your VIP access code when prompted
4. VIP models will be automatically added to your catalog
5. Download and use VIP models just like standard models

**VIP Features**:
- ✨ **Premium Quality**: Access to the highest-quality separation models available
- 🔒 **Secure Access**: Cryptographically protected model access with tamper-resistant verification
- 🎯 **Specialized Models**: Task-specific models optimized for particular use cases
- 🔄 **Automatic Updates**: VIP catalog automatically refreshes with new premium models
- 💎 **Exclusive Content**: Early access to experimental and cutting-edge models
- 🛡️ **Quality Guarantee**: VIP models undergo extensive testing and quality assurance

**Technical Details**:
- VIP verification uses AES encryption with PBKDF2 key derivation
- Model authenticity verified through cryptographic signatures
- No personal information collected during VIP verification
- VIP access stored locally and persists across application restarts

### ⚙️ Configuration Options

#### Application Settings

Settings are automatically saved to platform-specific locations:

- **Windows**: `%APPDATA%/UVR-PySide6/settings.json`
- **macOS**: `~/Library/Application Support/UVR-PySide6/settings.json`  
- **Linux**: `~/.config/UVR-PySide6/settings.json`

#### Environment Variables

Customize behavior with environment variables:

```bash
# Enable debug logging
export UVR_DEBUG=1

# Custom model directory
export UVR_MODEL_DIR="/path/to/models"

# Custom cache directory  
export UVR_CACHE_DIR="/path/to/cache"

# Force CPU-only processing
export UVR_NO_GPU=1

# Custom log level
export UVR_LOG_LEVEL=INFO
```

#### Advanced Configuration

**Memory Optimization**:
```bash
# Reduce memory usage for large files
export UVR_LOW_MEMORY=1

# Custom segment size for memory-constrained systems
export UVR_DEFAULT_SEGMENT_SIZE=256
```

**GPU Configuration**:
```bash
# Force specific CUDA device
export CUDA_VISIBLE_DEVICES=0

# MPS optimization (macOS)
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

## 🧪 Quality Assurance

This project maintains enterprise-grade code quality through comprehensive automated testing and quality assurance.

### Testing Infrastructure

- **341+ Tests**: Comprehensive test coverage across all components
- **57% Code Coverage**: Well above industry standards
- **100% Critical Path Coverage**: All essential functionality tested
- **Automated Regression Prevention**: Critical tests prevent breaking changes

#### Test Categories

```bash
# Run all tests
./run_tests.sh --all

# Run by category
pytest -m unit        # Unit tests (fast)
pytest -m integration # Integration tests  
pytest -m critical    # Critical functionality tests
pytest -m edge_case   # Edge cases and error conditions

# Run specific test suites
pytest tests/unit/core/test_application_startup.py -v
pytest tests/unit/core/test_separate_logic.py -v
```

### Quality Assurance Tools

The project uses a comprehensive suite of automated tools:

#### Code Quality Scripts

```bash
# Format code (Black + import sorting)
./scripts/format.sh

# Run linting and quality checks
./scripts/lint.sh

# Run comprehensive quality pipeline
./scripts/check-all.sh

# Pre-commit checks (before committing changes)
./scripts/pre-commit-checks.sh
```

#### Quality Tools

- **Black**: Code formatting with 88-character line length
- **Ruff**: Fast Python linting (replaces flake8, pycodestyle)
- **MyPy**: Static type checking for type safety
- **Bandit**: Security vulnerability scanning
- **isort**: Import statement organization
- **Pre-commit**: Automated quality checks before commits

#### Makefile Shortcuts

```bash
# Setup development environment
make install-dev

# Quality assurance
make format          # Format code
make lint           # Run linting
make test           # Run tests
make test-critical  # Run critical tests only
make pre-commit     # Pre-commit checks
make check-all      # Complete quality pipeline

# Cleanup
make clean          # Remove generated files
```

### Critical Functionality Protection

The application includes a **Critical Functionality Protection System** that prevents regressions:

#### What It Protects
- ✅ QRC resource loading (fonts, stylesheets)
- ✅ Core module imports and dependencies
- ✅ Application startup and initialization
- ✅ Essential UI component creation
- ✅ Model loading and inference paths

#### How It Works
1. **Critical Tests**: Run before every commit and during CI
2. **Pre-commit Hooks**: Block commits that break essential functionality
3. **Automated Detection**: Immediate feedback when core features break
4. **Regression Prevention**: Comprehensive test coverage for all fixes

#### Running Critical Tests
```bash
# Quick critical functionality check
make test-critical

# Pre-commit verification
make pre-commit

# Complete quality assurance
make check-all
```

## 🏗️ Architecture

This application follows modern software engineering principles with a clean, modular architecture designed for maintainability, testability, and extensibility.

### 🎯 System Overview

![System Architecture](docs/images/diagrams/01_system_architecture.png)

The UVR PySide6 application is built with a **layered architecture** that separates concerns and enables maintainable, scalable code:

- 🖥️ **Application Layer**: Entry points and main application bootstrap
- 🎨 **UI Layer**: PySide6-based interface using MVP (Model-View-Presenter) pattern
- 🧠 **Core Business Logic**: Audio processing, model management, and orchestration
- 🔧 **External Dependencies**: Qt Framework, ML libraries, and system resources

### 🎭 MVP Pattern Implementation

![MVP Pattern](docs/images/diagrams/02_mvp_pattern.png)

The UI follows the **Model-View-Presenter (MVP)** pattern for clean separation of concerns:

- **Views**: PySide6 widgets handling UI rendering and user input
- **Presenters**: Business logic coordinators managing data flow between views and core
- **Core Adapter**: Central hub connecting UI layer to business logic

**Benefits**:
- ✅ **Testability**: Presenters can be unit tested without GUI components
- ✅ **Maintainability**: Clear separation between UI and business logic
- ✅ **Flexibility**: Easy to modify UI without affecting core functionality
- ✅ **Reusability**: Core logic can be reused across different UIs

### 🔄 Processing Pipeline

![Processing Pipeline](docs/images/diagrams/03_processing_pipeline.png)

The audio processing follows a **robust, threaded pipeline**:

1. **User Interaction**: UI captures user settings and file selections
2. **Settings Validation**: Presenters validate and prepare processing parameters
3. **Thread Creation**: Core adapter creates isolated processing threads
4. **Model Loading**: Dynamic model loading with validation and caching
5. **Audio Processing**: ML inference with progress reporting
6. **Result Handling**: Output generation and UI state management

**Key Features**:
- 🧵 **Non-blocking UI**: Processing runs in separate threads
- 📊 **Real-time Progress**: Granular progress updates with cancellation support  
- 🛡️ **Error Handling**: Comprehensive error recovery and user feedback
- 🚀 **Performance**: Optimized memory usage and GPU acceleration

### 🤖 Model Management System

![Model Management](docs/images/diagrams/04_model_management.png)

Sophisticated model lifecycle management:

- **Dynamic Loading**: Models loaded on-demand with automatic dependency resolution
- **Smart Caching**: Intelligent caching with validation and invalidation
- **Download Management**: Robust download system with progress tracking and resumption
- **Version Handling**: Automatic detection and organization of model versions
- **Resource Optimization**: Memory-efficient loading and cleanup

### 🎵 Audio Processing Components

![Audio Processing](docs/images/diagrams/05_audio_processing.png)

Multi-architecture audio separation pipeline:

- **Input Validation**: Format detection, conversion, and quality validation
- **Separation Logic**: Support for VR Architecture, MDX-Net, Demucs, and Ensemble modes
- **Model Processing**: Optimized inference with GPU acceleration and memory management
- **Output Generation**: High-quality stem generation with configurable formats

### 🔗 Signal/Slot Communication

![Signal-Slot Communication](docs/images/diagrams/06_signal_slot.png)

Event-driven architecture using Qt's signal/slot mechanism:

- **Loose Coupling**: Components communicate through signals without direct dependencies
- **Type Safety**: Compile-time type checking for signal/slot connections
- **Thread Safety**: Safe communication between UI and worker threads
- **Extensibility**: Easy to add new events and handlers

### 📊 Code Organization

```
src/uvr_pyside6_ui/
├── main.py                    # Application entry point
├── gui/                       # UI components
│   ├── views/                 # PySide6 view components
│   └── presenters/            # MVP presenter layer
├── core/                      # Business logic
│   ├── separate_logic.py      # Audio separation algorithms
│   ├── model_data.py          # Model management
│   └── processing/            # Processing pipeline
├── lib_v5/                    # Legacy compatibility layer
└── resources/                 # UI resources (QRC)
```

### 🧪 Testing Architecture

The application includes comprehensive testing at multiple levels:

- **Unit Tests**: Individual component testing with mocking
- **Integration Tests**: Component interaction and data flow testing
- **Critical Path Tests**: Essential functionality regression prevention
- **UI Tests**: Automated UI interaction testing
- **Performance Tests**: Memory usage and processing speed validation

### 🔒 Error Handling Strategy

**Defensive Programming Approach**:
- ✅ **Input Validation**: All user inputs validated at entry points
- ✅ **Resource Management**: Automatic cleanup with context managers
- ✅ **Graceful Degradation**: Fallback options when components fail
- ✅ **User Communication**: Clear error messages with actionable solutions
- ✅ **Logging**: Comprehensive logging for debugging and monitoring

### 🚀 Performance Optimizations

**Memory Management**:
- Smart model caching with LRU eviction
- Chunked processing for large audio files
- Automatic garbage collection optimization
- Memory-mapped file I/O for large datasets

**GPU Acceleration**:
- CUDA support for Nvidia GPUs with automatic device selection
- MPS support for Apple Silicon with fallback detection
- Memory pool management for efficient GPU memory usage
- Asynchronous GPU operations with CPU overlap

**I/O Optimization**:
- Asynchronous file operations
- Parallel model downloading
- Efficient audio format conversion
- Smart caching with filesystem monitoring

### 🔮 Future Architecture Improvements

**Planned Enhancements**:
- 🔌 **Plugin System**: Extensible architecture for third-party models
- 🌐 **Cloud Integration**: Optional cloud-based processing for limited hardware
- 📱 **Mobile Support**: Qt for Python mobile deployment
- 🤖 **AI Assistant**: Intelligent model recommendation system
- 📊 **Analytics**: Optional usage analytics and performance monitoring

### 📚 Architecture Documentation

For detailed architecture information, see:
- 📋 **[Architecture Diagrams](docs/architecture_diagrams.md)**: Complete UML documentation
- 🔧 **[Technical Documentation](docs/technical.md)**: Implementation details
- 🛣️ **[Development Roadmap](docs/development_roadmap.md)**: Future architecture plans
- 🎨 **[Diagram Generation Guide](docs/diagram_generation_guide.md)**: How to generate/modify diagrams

> 🌐 **Interactive Diagrams**: Open `scripts/diagram_generator.html` in your browser for an interactive diagram viewer with real-time rendering and download capabilities.

## 🚀 Performance Optimization

### Memory Optimization

**For Limited RAM (8GB or less)**:
```bash
# Reduce segment size
# In UI: Set segment size to 256
# Or via environment:
export UVR_DEFAULT_SEGMENT_SIZE=256

# Enable low memory mode
export UVR_LOW_MEMORY=1
```

**For Large Files (1GB+ audio)**:
- Use **segment size 512** or **1024** for better quality
- Ensure **16GB+ RAM** for comfortable processing
- Close other applications during processing

### GPU Acceleration

**Nvidia GPUs**:
```bash
# Verify CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# Monitor GPU usage during processing
nvidia-smi -l 1
```

**Apple Silicon (M1/M2/M3)**:
```bash
# Verify MPS availability
python -c "import torch; print(torch.backends.mps.is_available())"

# MPS is automatically enabled on compatible Macs
```

**Performance Tips**:
- **8GB+ VRAM**: Use segment size 1024 for best quality
- **4-6GB VRAM**: Use segment size 512 for balanced performance
- **<4GB VRAM**: Use segment size 256 or CPU processing

### Storage Performance

- **Use SSD storage** for model directory and temp files
- **Network storage**: May slow down model loading significantly
- **Free space**: Ensure 10GB+ available for temporary files

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### Application Won't Start

**"Qt platform plugin error" (Linux)**:
```bash
# Install Qt platform dependencies
sudo apt install qt6-base-dev qt6-tools-dev qt6-image-formats-plugins

# Alternative: Set Qt platform
export QT_QPA_PLATFORM=xcb
```

**"Module not found" errors**:
```