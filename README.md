# Ultimate Vocal Remover GUI - PySide6 Edition

<img src="gui_data/img/pyside6-port.png" />

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Qt Framework](https://img.shields.io/badge/Qt-PySide6-green)](https://pyside.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-335%20passing-green)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-33%25-yellow)](htmlcov/index.html)

## About

A modern, professional rewrite of the Ultimate Vocal Remover GUI using **PySide6** and **PyTorch**. This application provides state-of-the-art audio source separation capabilities with a beautiful, responsive Qt-based interface.

### Key Features

- 🎵 **Advanced AI Models**: VR, MDX-Net, and Demucs architectures for superior separation quality
- 🖥️ **Modern Interface**: Professional PySide6/Qt GUI replacing the original tkinter interface  
- ⚡ **GPU Acceleration**: CUDA support for Nvidia GPUs and MPS for Apple Silicon
- 🧵 **Threaded Processing**: Non-blocking UI with real-time progress feedback
- 📦 **Auto Model Management**: Automatic model downloading and organization
- 🔧 **Configurable**: Extensive settings for fine-tuning separation quality
- 🧪 **Well Tested**: 335+ tests with 33% code coverage ensuring reliability

### Supported Separation Types

- **Vocal Isolation**: Remove or isolate vocals from music
- **Instrumental Extraction**: Extract backing tracks without vocals  
- **Stem Separation**: Separate drums, bass, vocals, and other instruments
- **Custom Ensembles**: Combine multiple models for enhanced quality

## Requirements

### System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows 10+, macOS 11+, or modern Linux
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 5GB+ for models and processing cache

### GPU Requirements (Optional)

- **Nvidia**: GTX 1060 6GB minimum, RTX series recommended (8GB+ VRAM)
- **Apple Silicon**: M1/M2 Macs with MPS acceleration
- **AMD**: Limited support (CPU fallback recommended)

## Installation

### Method 1: Development Installation (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kufirre/ultimatevocalremovergui.git
   cd ultimatevocalremovergui
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv uvr-env
   
   # Windows
   uvr-env\Scripts\activate
   
   # macOS/Linux  
   source uvr-env/bin/activate
   ```

3. **Install the application**:
   ```bash
   # Basic installation
   pip install -e .
   
   # With development tools
   pip install -e ".[dev]"
   
   # With GPU acceleration (Nvidia)
   pip install -e ".[gpu]"
   ```

### Method 2: Direct Installation

```bash
# Install directly from repository
pip install git+https://github.com/kufirre/ultimatevocalremovergui.git

# Or with extras
pip install "git+https://github.com/kufirre/ultimatevocalremovergui.git[dev,gpu]"
```

### Platform-Specific Notes

#### Windows
- Ensure you have Visual Studio Build Tools installed for PyTorch
- Windows Defender may need exclusions for model downloads

#### macOS
- Xcode command line tools required: `xcode-select --install`
- For Apple Silicon, MPS acceleration is automatically enabled

#### Linux (Ubuntu/Debian)
```bash
# Install system dependencies
sudo apt update
sudo apt install python3-dev python3-tk ffmpeg

# Then follow standard installation
```

## Usage

### Starting the Application

#### Using the installed command:
```bash
uvr-gui
```

#### Using Python directly:
```bash
python -m uvr_pyside6_ui.main
```

#### Using the legacy entry point:
```bash
python UVR.py
```

### Basic Workflow

1. **Launch the application** using one of the methods above
2. **Select your audio file** using the file browser
3. **Choose a separation model** from the dropdown menu
4. **Configure settings** (segment size, overlap, etc.) if needed
5. **Click "Start Processing"** to begin separation
6. **Monitor progress** in real-time via the progress bar
7. **Find output files** in the specified output directory

### Model Management

Models are automatically downloaded when first selected. The application will:
- Fetch the latest model catalog from online sources
- Download models to appropriate directories (`models/VR_Models/`, `models/MDX_Net_Models/`, etc.)
- Organize Demucs v3/v4 models in the `v3_v4_repo` subdirectory
- Cache model metadata for faster subsequent loads

## Testing

This project includes a comprehensive testing suite with 335+ tests covering all core functionality.

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ -v --cov=src --cov-report=html

# Run specific test modules
python -m pytest tests/unit/core/test_separate_logic.py -v

# Run tests by category
python -m pytest tests/ -m "unit" -v
python -m pytest tests/ -m "integration" -v

# Using the convenience script
./run_tests.sh
```

## Code Quality

This project maintains high code quality through automated formatting, linting, and type checking.

### Available Scripts

```bash
# Format code (black + isort)
./scripts/format.sh

# Run linting and quality checks  
./scripts/lint.sh

# Run all quality checks (format + lint + tests)
./scripts/check-all.sh
```

### Code Standards

- **Formatting**: Black with 88-character line length
- **Import Sorting**: isort configured for Black compatibility
- **Linting**: Ruff for fast Python linting
- **Type Checking**: MyPy for static type analysis
- **Security**: Bandit for security vulnerability scanning
- **Pre-commit Hooks**: Automated quality checks before commits

### Setting Up Pre-commit Hooks

```bash
# Install pre-commit hooks (runs checks before each commit)
pre-commit install

# Run pre-commit on all files manually
pre-commit run --all-files

# Update pre-commit hook versions
pre-commit autoupdate
```

### Quality Check Details

- **Black**: Formats Python code to ensure consistent style
- **isort**: Organizes and sorts import statements
- **Ruff**: Fast linter that replaces flake8, pycodestyle, and more
- **MyPy**: Static type checker to catch type-related bugs
- **Bandit**: Scans for common security issues
- **Pytest**: Runs the comprehensive test suite with coverage

## Development

### Setting Up Development Environment

1. **Clone and install in development mode**:
   ```bash
   git clone https://github.com/kufirre/ultimatevocalremovergui.git
   cd ultimatevocalremovergui
   pip install -e ".[dev]"
   ```

2. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

3. **Run tests to verify setup**:
   ```bash
   ./run_tests.sh
   ```

4. **Set up code quality tools**:
   ```bash
   # Install pre-commit hooks
   pre-commit install
   
   # Run initial quality checks
   ./scripts/check-all.sh
   ```

### Project Structure

```
ultimatevocalremovergui/
├── src/uvr_pyside6_ui/       # Main application package
│   ├── core/                 # Core processing logic
│   ├── gui/                  # PySide6 UI components  
│   └── main.py              # Application entry point
├── tests/                    # Comprehensive test suite
├── scripts/                  # Quality assurance scripts
│   ├── format.sh            # Code formatting
│   ├── lint.sh              # Linting and quality checks
│   └── check-all.sh         # Complete quality pipeline
├── models/                   # Downloaded AI models
├── docs/                     # Documentation
├── demucs/                   # Demucs model code
├── lib_v5/                   # Legacy VR model code
├── pyproject.toml           # Project configuration
├── pytest.ini              # Test configuration
└── .pre-commit-config.yaml  # Pre-commit hooks
```

### Code Quality

The project maintains high code quality through:

- **Automated Formatting**: Black + isort for consistent code style
- **Comprehensive Linting**: Ruff + MyPy + Bandit for quality and security
- **Testing**: 335+ tests with pytest and pytest-qt
- **Coverage**: HTML coverage reports for monitoring test effectiveness
- **Pre-commit Hooks**: Automated quality checks prevent bad commits
- **Documentation**: Comprehensive docstrings and comments

### Development Workflow

1. **Make your changes** with appropriate tests
2. **Run quality checks**: `./scripts/check-all.sh`
3. **Fix any issues** identified by the quality tools
4. **Commit your changes** (pre-commit hooks will run automatically)
5. **Push to your branch** and open a Pull Request

### Contributing

1. **Fork the repository** on GitHub
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow the development workflow above**
4. **Ensure all quality checks pass**: `./scripts/check-all.sh`
5. **Open a Pull Request** with a clear description

### Bug Reports

When reporting bugs, please include:
- **Operating system and version**
- **Python version and installation method**
- **Complete error messages and stack traces**
- **Steps to reproduce the issue**
- **Audio file characteristics (if relevant)**

## Configuration

### Settings File

User preferences are automatically saved to:
- **Windows**: `%APPDATA%/UVR-PySide6/settings.json`
- **macOS**: `~/Library/Application Support/UVR-PySide6/settings.json`
- **Linux**: `~/.config/UVR-PySide6/settings.json`

### Environment Variables

- `UVR_DEBUG=1`: Enable debug logging
- `UVR_MODEL_DIR`: Custom model directory path
- `UVR_CACHE_DIR`: Custom cache directory path
- `UVR_NO_GPU=1`: Force CPU-only processing

## Performance Tips

### Memory Optimization
- Reduce **Segment Size** if you encounter out-of-memory errors
- Close other applications during processing
- Use 64-bit Python for large audio files

### GPU Acceleration  
- Ensure CUDA drivers are up to date for Nvidia GPUs
- Monitor GPU memory usage during processing
- Consider upgrading to 8GB+ VRAM for large models

### Processing Speed
- Use SSD storage for faster model loading
- Enable GPU acceleration when available
- Process multiple files in batches for efficiency

## Troubleshooting

### Common Issues

**"Model failed to load"**
- Check internet connection for automatic downloads
- Verify sufficient disk space (5GB+ recommended)
- Try manually downloading the model from the online catalog

**"CUDA out of memory"**
- Reduce segment size in advanced settings
- Close other GPU-intensive applications
- Switch to CPU processing if necessary

**"Qt platform plugin error"** (Linux)
```bash
# Install Qt platform dependencies
sudo apt install qt6-base-dev qt6-tools-dev
```

**Audio playback issues**
- Install system audio codecs (FFmpeg)
- Check output directory permissions
- Verify input file format compatibility

### Getting Help

- **GitHub Issues**: [Report bugs and request features](https://github.com/kufirre/ultimatevocalremovergui/issues)
- **Original UVR**: [Community support](https://github.com/Anjok07/ultimatevocalremovergui)
- **Documentation**: Check the `docs/` directory for technical details

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### Third-Party Components

- **Original UVR**: Based on [Ultimate Vocal Remover GUI](https://github.com/Anjok07/ultimatevocalremovergui) by Anjok07
- **PySide6**: Qt for Python interface framework
- **PyTorch**: Deep learning framework for model inference
- **Model Architectures**: VR (tsurumeso), MDX-Net (Kuielab), Demucs (Facebook Research)

## Credits

### Core Developers
- **[Kufirre Ebong](https://github.com/kufirre)** - PySide6 rewrite and modernization
- **[Anjok07](https://github.com/anjok07)** - Original UVR development and model training
- **[aufr33](https://github.com/aufr33)** - Original UVR core development

### Model Contributions
- **[ZFTurbo](https://github.com/ZFTurbo)** - MDX23C model training
- **[tsurumeso](https://github.com/tsurumeso)** - VR Architecture development
- **[Kuielab & Woosung Choi](https://github.com/kuielab)** - MDX-Net development
- **[Facebook Research](https://github.com/facebookresearch/demucs)** - Demucs development

### Design & Community
- **[Bas Curtiz](https://www.youtube.com/user/bascurtiz)** - Official UVR branding and design
- **[DilanBoskan](https://github.com/DilanBoskan)** - Early project contributions
- **The UVR Community** - Testing, feedback, and continuous support

## Acknowledgments

This project builds upon the incredible work of the original Ultimate Vocal Remover team and the broader audio source separation research community. Special thanks to all contributors who have made this advanced audio processing technology accessible to everyone.
