# Technical Documentation

## Testing Infrastructure

### Overview
The project now has a comprehensive testing suite covering all core modules with:
- **245 total tests** across 6 core modules
- **237 passing, 8 failing** (97% success rate) 
- Professional pytest configuration with markers and coverage reporting
- Proper PySide6/Qt integration with signal testing

### Test Coverage by Module

#### Core Module Tests (244 tests)
1. **test_app_constants.py** (45 tests) - ✅ All passing
   - Tests for all model type keys, subdirectories, online catalog mappings
   - DummyModelParameters class with JSON file handling and parameter structure validation
   - Constant consistency checks and stem mappings
   - Audio format, processing method, and configuration constant verification

2. **test_logger_utils.py** (29 tests) - ✅ All passing  
   - UVRLogger class configuration, level management, and logger creation
   - Environment variable handling and console output control
   - Integration tests for logging workflows and caching behavior
   - Logger name handling and format validation

3. **test_model_downloader.py** (26 tests) - ✅ 25 passing, 1 failing
   - Online catalog fetching with caching mechanisms and network error fallbacks
   - Model file downloads with progress tracking and cleanup on errors
   - Special handling for Demucs v3/v4 models and config files
   - Integration tests for complete download workflows

4. **test_download_worker.py** (23 tests) - ✅ All passing
   - DownloadWorker Qt-based class for threaded downloads
   - DownloadManager for coordinating multiple downloads
   - Qt signal handling and threading behavior testing
   - Progress callbacks and error management

5. **test_uvr_core_adapter.py** (47 tests) - ✅ 40 passing, 7 failing
   - UVRCoreAdapter main coordinator class testing
   - Model directory detection and scanning functionality
   - Online catalog integration and downloadable model filtering
   - Processing coordination and Qt signal management
   - Integration tests for complete workflows

6. **test_separate_logic.py** (12 tests) - ✅ All passing
   - Structural tests for ML separation logic without requiring actual models
   - Mock-based testing for separator classes (VR, MDX, Demucs)
   - Audio format compatibility and workflow structure validation

7. **test_model_data.py** (24 tests) - ✅ All passing
   - ModelData class initialization and configuration
   - Settings dictionary conversion and validation
   - Ensemble model creation and management
   - Processing method verification

8. **test_processing_worker.py** (39 tests) - ✅ All passing
   - ProcessingWorker and ProcessingThread classes
   - Ensemble processing and audio combination algorithms
   - Progress tracking and error handling
   - Threading behavior and signal management

### Test Infrastructure Components

#### Configuration Files
- **pyproject.toml**: Professional structure with comprehensive dependencies
  - Core dependencies (uvr-pyside6-ui, PySide6, torch, torchaudio, etc.)
  - Audio processing (librosa, soundfile, scipy)
  - ML/AI (onnxruntime, huggingface-hub, diffq)
  - Testing framework (pytest, pytest-qt, pytest-cov)
  - Code quality tools (flake8, mypy, black)

- **pytest.ini**: Comprehensive test configuration
  - Test markers for categorization (unit, integration, download, worker, adapter)
  - Coverage reporting (HTML, XML, terminal) with 15% threshold
  - Asyncio settings for PySide6 compatibility
  - Timeout configurations and warning filters

#### Key Testing Patterns
1. **Qt Signal Testing**: Using QSignalSpy with proper `.at()` method for signal verification
2. **Threading Mocks**: Proper mocking of QThread to avoid segmentation faults
3. **Fixture Management**: Temporary directories and file cleanup
4. **Mock Strategies**: Comprehensive mocking for external dependencies
5. **Integration Testing**: End-to-end workflow verification

### Resolved Issues

#### PySide6/Qt Compatibility Issues (Fixed)
- ✅ **QSignalSpy subscripting**: Changed from `spy[index]` to `spy.at(index)`
- ✅ **QThread mocking**: Used proper Mock objects instead of real threads in tests
- ✅ **moveToThread compatibility**: Added proper patching to avoid Qt type checking
- ✅ **Signal counting**: Used `spy.count()` instead of `len(spy)`

#### Test Logic Issues (Fixed)
- ✅ **JSON parameter structure**: Fixed numeric key serialization in DummyModelParameters tests
- ✅ **Path handling**: Corrected directory detection fallback logic
- ✅ **Mock patching**: Fixed instance vs class attribute mocking issues

### Remaining Issues (8 failing tests)

#### 1. Model Downloader (1 failure)
- **Issue**: Demucs v3/v4 special path handling test expects 'v3_v4_repo' in path
- **Root Cause**: Test assumption about directory structure doesn't match implementation
- **Priority**: Low - edge case in Demucs model handling

#### 2. UVR Core Adapter (7 failures)
- **Mock attribute issues**: `download_manager` attribute mocking problems
- **Directory scanning**: Model name mapping logic not working as expected in tests
- **Processing thread mocking**: Mock objects missing required signal attributes
- **Integration workflow**: End-to-end model scanning pipeline issues

#### Common Root Causes
1. **Mock configuration**: Some tests need more sophisticated mocking strategies
2. **Business logic assumptions**: Tests make assumptions about internal implementation details
3. **Qt integration complexity**: Some Qt-specific behaviors are difficult to mock properly

### Test Execution Commands

```bash
# Run all tests
python -m pytest tests/unit/core/ -v

# Run specific module tests
python -m pytest tests/unit/core/test_app_constants.py -v

# Run with coverage (disable 15% threshold for development)
python -m pytest tests/unit/core/ -v --cov=src --cov-report=html --cov-fail-under=0

# Run only failing tests
python -m pytest tests/unit/core/ --lf -v

# Run tests by marker
python -m pytest tests/unit/core/ -m "unit" -v
python -m pytest tests/unit/core/ -m "integration" -v
```

### Development Workflow

1. **Individual Module Development**: Focus on single module test suites
2. **Integration Testing**: Run cross-module integration tests
3. **Coverage Analysis**: Use HTML coverage reports to identify untested code
4. **Regression Testing**: Use `--lf` flag to quickly re-run failing tests
5. **Performance Testing**: Monitor test execution time for large suites

### Future Enhancements

1. **Property-Based Testing**: Add hypothesis for more robust test cases
2. **Performance Benchmarks**: Add timing tests for audio processing
3. **Mock Audio Data**: Create realistic test fixtures for audio processing
4. **CI/CD Integration**: Set up automated testing pipeline
5. **Documentation Tests**: Add docstring example testing

## Dependencies and Package Management

### Core Dependencies
- **Python 3.12+**: Required for modern typing features
- **PySide6**: Qt-based GUI framework
- **PyTorch**: Deep learning framework for model inference
- **librosa**: Audio analysis and processing
- **onnxruntime**: ONNX model inference engine

### Development Dependencies
- **pytest ecosystem**: Testing framework with Qt support
- **coverage tools**: Code coverage analysis
- **code quality**: Linting and formatting tools
- **type checking**: mypy for static type analysis

### Installation
```bash
# Production installation
pip install -e .

# Development installation with testing tools
pip install -e ".[dev]"
```

The testing infrastructure provides a solid foundation for maintaining code quality and ensuring reliability as the project continues to grow. 