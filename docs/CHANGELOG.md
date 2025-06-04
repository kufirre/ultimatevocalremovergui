# Changelog

All notable changes to the Ultimate Vocal Remover PySide6 Edition project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Critical Functionality Protection System
- Comprehensive quality assurance pipeline
- Pre-commit hooks for automated quality checks
- Enterprise-grade testing infrastructure with 341+ tests
- Advanced QRC resource management
- Automated V3/V4 model directory management
- Professional development workflow with Makefile shortcuts
- **Visual Architecture Documentation**: Complete UML diagrams with PNG/SVG generation
- **Architecture Diagrams**: 6 comprehensive UML diagrams showing system structure
- **Diagram Generation Tools**: Automated script and HTML generator for creating diagrams
- **Enhanced README**: Visual architecture section with embedded diagram images

### Changed
- Enhanced test coverage from 33% to 57%
- Improved Demucs version detection logic
- Updated all documentation for comprehensive user guidance
- Modernized development tooling and quality standards

### Fixed
- **Critical Bug**: QRC resource loading warnings (fonts, stylesheets)
- **Critical Bug**: `ac.NO_STEM` AttributeError in Demucs separation
- **Enhancement**: Demucs V3/V4 model placement accuracy
- **Enhancement**: Version detection for models with complex names

### Security
- Added Bandit security scanning with project-specific rules
- Implemented input validation and sanitization
- Enhanced dependency security monitoring

## [0.1.0] - 2024-12-04

### Added
- Initial PySide6 rewrite of Ultimate Vocal Remover GUI
- Modern Qt-based interface replacing tkinter
- PyTorch backend with GPU acceleration support
- Multi-model support (VR, MDX-Net, Demucs)
- Threaded processing with progress feedback
- Automatic model downloading and management
- Comprehensive test suite with pytest and pytest-qt
- Professional logging system
- Cross-platform compatibility (Windows, macOS, Linux)

### Technical Highlights
- **PySide6 Integration**: Complete migration from tkinter to modern Qt framework
- **Performance**: GPU acceleration with CUDA and MPS support
- **Architecture**: Clean MVP pattern with separation of concerns
- **Testing**: Professional pytest configuration with Qt integration
- **Documentation**: Comprehensive technical and user documentation

### Dependencies
- PySide6 6.4.0+ for modern Qt GUI
- PyTorch 1.13.0+ for ML model inference
- librosa, soundfile for audio processing
- onnxruntime for ONNX model support
- pytest ecosystem for comprehensive testing

---

## Development Notes

### Quality Assurance Milestones
- **December 2024**: Implemented Critical Functionality Protection System
- **December 2024**: Achieved 57% test coverage (341+ tests)
- **December 2024**: Resolved all critical QRC resource loading issues
- **December 2024**: Enhanced Demucs V3/V4 handling with comprehensive testing

### Breaking Changes
None. The application maintains compatibility with original UVR workflows while providing enhanced functionality and reliability.

### Migration Guide
For users upgrading from tkinter UVR:
1. Install with `pip install -e ".[dev]"`
2. Launch with `uvr-gui` command
3. All existing models and settings are automatically migrated
4. Enjoy improved performance and modern interface

### Contributors
- **[Kufirre Ebong](https://github.com/kufirre)** - PySide6 rewrite, quality assurance, and modernization
- **[Anjok07](https://github.com/anjok07)** - Original UVR development and architecture
- **[aufr33](https://github.com/aufr33)** - Core UVR development contributions

### Acknowledgments
Special thanks to the entire UVR community for testing, feedback, and continuous support during the PySide6 transition. 