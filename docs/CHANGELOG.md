# Changelog

All notable changes to the Ultimate Vocal Remover PySide6 Edition project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Latest] - 2025-01-05

### Separation Logic Modularization 📁

#### Major Architecture Improvement
- **REFACTORED**: Split monolithic `separate_logic.py` (2172 lines) into 5 logical modules
- **IMPROVED**: Better separation of concerns with focused, maintainable components
- **ORGANIZED**: Each separator architecture now has its own dedicated module
- **ENHANCED**: Cleaner codebase structure for easier development and debugging

#### New Modular Structure
```
src/uvr_pyside6_ui/core/
├── separate_logic_base.py     # Common utilities and base SeparatorAttributesLogic class
├── separate_vr_logic.py       # VR architecture separation implementation
├── separate_mdx_logic.py      # MDX-Net ONNX model implementation  
├── separate_mdxc_logic.py     # MDX-C checkpoint model implementation
└── separate_demucs_logic.py   # Demucs v1/v2/v3/v4 implementation
```

#### Backward Compatibility Maintained
- **PRESERVED**: All existing functionality remains intact
- **CREATED**: Compatibility namespace for seamless test integration
- **UPDATED**: 467 tests successfully adapted to new module structure
- **ENSURED**: Zero breaking changes for end users

#### Enhanced Development Experience
- **FOCUSED**: Each module contains architecture-specific logic only
- **MAINTAINABLE**: Easier to locate, understand, and modify separation algorithms
- **SCALABLE**: New separator architectures can be easily added as separate modules
- **DEBUGGABLE**: Cleaner stack traces and more targeted error handling

#### Quality Assurance
- **TESTS**: Updated all test imports and mocking to use new module paths
- **COVERAGE**: Maintained test coverage at 61% with all 467 tests passing
- **COMPATIBILITY**: Processing worker imports correctly updated
- **VERIFIED**: All separation functionality working perfectly across all architectures

### Modern Download Center Redesign

#### Complete Interface Overhaul
- **REDESIGNED**: Modern, clean download center with intuitive 2-dropdown interface
- **IMPROVED**: Replaced radio buttons with cleaner architecture + model selection dropdowns
- **ENHANCED**: Professional styling with modern color scheme and rounded corners
- **ORGANIZED**: Grouped sections with QGroupBox containers for better visual hierarchy

#### Smart Model Filtering
- **NEW**: Downloaded models are automatically filtered out from available options
- **INTELLIGENT**: Real-time model list updates after successful downloads
- **EFFICIENT**: No duplicate downloads - only shows models that aren't already installed
- **ACCURATE**: Architecture-specific filtering for VR, MDX-Net, and Demucs models

#### Enhanced Download Experience
- **IMPROVED**: Better progress visualization with modern styling
- **ENHANCED**: Clear status messages with emoji indicators (✅/❌)
- **PROFESSIONAL**: Gradient progress bars with proper percentage display
- **RESPONSIVE**: Real-time updates during download process

#### User Interface Improvements
- **MODERN**: Clean, contemporary design language throughout
- **INTUITIVE**: Two-dropdown selection (Architecture → Model) for better UX
- **ACCESSIBLE**: Clear visual feedback and status indicators
- **CONSISTENT**: Unified button styling with hover effects
- **SPACIOUS**: Better spacing and padding for improved readability

#### Technical Enhancements
- **FIXED**: Model type mapping between UI and internal adapter types
- **IMPROVED**: Error handling with user-friendly messages
- **ENHANCED**: Automatic list refresh after successful downloads
- **OPTIMIZED**: Better performance with smart filtering logic

### Previous Settings Dialog Fixes

#### Settings Guide Tab Fixes
- **FIXED**: Settings Guide dropdown now matches original UVR exactly with correct advanced menu options:
  - "Advanced VR Options", "Advanced MDX-Net Options", "Advanced Demucs Options"
  - "Ensemble Customization Options", "Audio Alignment Tool" 
  - "Open Information Guide", "Open Error Log"
- **IMPROVED**: Advanced settings selection now properly emits signals to open separate windows (placeholder implementation)
- **ENHANCED**: Better UVR-consistent styling for all settings guide components

#### Download Progress Improvements
- **FIXED**: Download progress now updates in real-time during model downloads
- **IMPROVED**: Progress display shows:
  - Progress info: "Downloading ModelName..."
  - Progress percentage: "45%" 
  - Visual progress bar with modern styling
- **ENHANCED**: Proper success/error handling with emoji indicators (✅/❌)
- **ADDED**: Auto-reset of progress display after completion/error

#### Technical Improvements
- **FIXED**: Missing `download_target_info` parameter in download method calls
- **IMPROVED**: Better error handling and logging for download operations
- **ENHANCED**: Proper signal connections between presenter and view
- **ADDED**: Status message system for user feedback

#### Cross-Platform Compatibility
- **MAINTAINED**: All macOS Qt layer-backing compatibility
- **PRESERVED**: Icon loading with graceful fallbacks
- **ENSURED**: Consistent behavior across platforms

### Previous Entries

## [2025-01-04] - Progress Bar and Settings Implementation

### Fixed
- Progress bar styling issues causing visibility problems during processing
- Missing QTimer import in settings dialog presenter
- Font warnings about missing "Courier" font - implemented proper fallback chain
- NSOpenPanel method identifier warnings on macOS

### Added  
- Initial 3-tab settings structure: Settings Guide, Additional Settings, Download Center
- Cross-platform progress bar improvements
- Enhanced font loading with family detection
- macOS-specific Qt attributes to prevent NSOpenPanel warnings

### Changed
- Reverted excessive progress bar styling to maintain visibility
- Updated font fallback chain in QSS to eliminate Courier warnings
- Improved signal flow for download progress updates

### Tests
- Updated test_application_startup.py to verify new 3-tab structure
- All critical startup tests passing (13/13)
- Settings load/save functionality verified

## [Previous] - Initial Setup and Core Features

### Added
- Complete PySide6/Qt-based UVR interface
- Core audio processing functionality  
- Model downloading and management
- Ensemble processing capabilities
- Cross-platform compatibility (Windows, macOS, Linux)

### Features
- Real-time audio processing with progress tracking
- Multiple AI model support (VR, MDX-Net, Demucs)
- Batch processing capabilities
- Comprehensive settings management
- Resource management with QRC system
- Modern Qt styling and theming

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
- **Enhanced Settings System**: Complete 3-tab settings dialog matching original UVR structure
- **Authentic Settings Interface**: Radio button model selection with proper progress tracking  
- **Professional UI Components**: QGroupBox organization, proper spacing, comprehensive functionality
- **Cross-Platform Compatibility**: macOS NSOpenPanel fixes and font improvements
- **Enhanced Download Center**: Modern model download interface with real-time progress

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
- **QRC Resource Loading**: Protected critical imports from removal by formatting tools
- **Progress Bar Issues**: Reverted styling changes, fixed signal connections and visibility
- **Font Warnings**: Eliminated problematic Courier font references with better fallbacks
- **Download Progress**: Fixed info label, percentage label, and progress bar updates for all models
- **Settings Structure**: Corrected to match original UVR 3-tab layout (Settings Guide, Additional Settings, Download Center)
- **macOS Compatibility**: Resolved NSOpenPanel warnings and native dialog behavior
- **Settings Persistence**: All settings now properly save and restore across sessions

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

## [0.2.0] - 2025-01-04

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
- **Enhanced Settings System**: Complete settings dialog with audio format, processing options, and UI configuration
- **Progress Bar Visibility Fixes**: Improved styling, forced updates, and visibility assurance
- **Comprehensive Testing**: New critical tests for progress bars and settings functionality

### Fixed
- QRC resource loading errors (Century Gothic and Montserrat fonts)
- Style.qss and progress_bars.qss stylesheet loading issues
- Import optimization preventing resources_rc module removal
- **Progress bar visibility during model processing**
- **Settings persistence and loading across all new configuration options**

### Removed
- **Redundant Documentation**: Consolidated project_status_summary.md into technical.md and README.md 