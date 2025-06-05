# UVR PySide6 Testing Infrastructure

This directory contains comprehensive tests for the UVR PySide6 application, focusing on the `src/` directory components.

## 🧪 Test Structure

```
tests/
├── conftest.py              # Global fixtures and test configuration
├── unit/                    # Unit tests for individual components
│   ├── core/               # Core functionality tests
│   │   ├── test_model_data.py
│   │   ├── test_processing_worker.py
│   │   └── test_uvr_core_adapter.py
│   └── ui/                 # UI component tests
├── integration/            # Integration tests
└── README.md              # This file
```

## 🚀 Quick Start

### Install Test Dependencies

```bash
# Install test dependencies
./run_tests.sh --install-deps

# Or manually
pip install -r requirements-test.txt
```

### Run Tests

```bash
# Run all tests with coverage
./run_tests.sh --all --coverage

# Run unit tests only
./run_tests.sh --unit --verbose

# Run specific test categories
./run_tests.sh --category ensemble
./run_tests.sh --category edge_case

# Run fast tests (exclude slow ones)
./run_tests.sh --fast
```

## 📊 Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests across components
- `@pytest.mark.ui` - UI/GUI tests using pytest-qt
- `@pytest.mark.ensemble` - Ensemble processing tests
- `@pytest.mark.audio` - Audio processing tests
- `@pytest.mark.edge_case` - Edge cases and error conditions
- `@pytest.mark.slow` - Tests that take more than 5 seconds
- `@pytest.mark.mock_audio` - Tests using mocked audio instead of real files
- `@pytest.mark.vip` - VIP download functionality and premium feature tests

## 🛠️ Testing Tools

### Core Testing Framework
- **pytest** - Main testing framework
- **pytest-qt** - PySide6/Qt testing support
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Enhanced mocking capabilities

### PySide6 Testing Features
- **qtbot fixture** - Simulates user interactions with Qt widgets
- **Signal testing** - Wait for Qt signals to be emitted
- **Widget testing** - Test widget behavior and state
- **Headless testing** - Tests run without GUI display

### Audio Testing
- **Mock audio arrays** - Synthetic audio data for testing
- **Audio validation** - Utilities to verify audio array properties
- **Ensemble testing** - Comprehensive ensemble processing tests

## 📝 Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
@pytest.mark.model
class TestMyComponent:
    """Test cases for MyComponent class."""
    
    def test_basic_functionality(self, mock_audio_file):
        """Test basic component functionality."""
        # Test implementation
        pass
    
    @pytest.mark.edge_case
    def test_edge_case(self):
        """Test edge case handling."""
        # Edge case test
        pass
```

### PySide6 Widget Testing

```python
@pytest.mark.ui
def test_widget_interaction(qtbot):
    """Test widget user interactions."""
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    # Simulate user interaction
    qtbot.mouseClick(widget.button, Qt.LeftButton)
    
    # Verify result
    assert widget.label.text() == "Expected Text"
```

### Audio Processing Testing

```python
@pytest.mark.audio
def test_audio_processing(mock_stereo_audio):
    """Test audio processing functionality."""
    processor = AudioProcessor()
    result = processor.process(mock_stereo_audio)
    
    # Validate audio output
    assert_audio_array_valid(result, expected_shape=(2, 1000))
```

### Ensemble Testing

```python
@pytest.mark.ensemble
def test_ensemble_combination(create_mock_ensemble_models):
    """Test ensemble model combination."""
    models = create_mock_ensemble_models()
    ensemble = EnsembleProcessor(models)
    
    # Test ensemble processing
    result = ensemble.process(input_audio)
    assert result is not None
```

### VIP Download Testing

```python
@pytest.mark.vip
@pytest.mark.unit
def test_vip_functionality():
    """Test VIP download and authentication."""
    from uvr_pyside6_ui.ui.settings_dialog_presenter import vip_downloads, NO_CODE
    
    # Test invalid VIP codes
    assert vip_downloads("invalid_code") == NO_CODE
    assert vip_downloads("") == NO_CODE
    assert vip_downloads(None) == NO_CODE
    
    # Test security validation
    malicious_inputs = ["../../../etc/passwd", "'; DROP TABLE models;", ""]
    for bad_input in malicious_inputs:
        assert vip_downloads(bad_input) == NO_CODE

@pytest.mark.vip
@pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="Cryptography library not available")
def test_vip_cryptographic_security():
    """Test VIP cryptographic security measures."""
    from uvr_pyside6_ui.ui.settings_dialog_presenter import VIP_REPO
    import base64
    
    # Verify encrypted data structure
    assert isinstance(VIP_REPO, tuple)
    assert len(VIP_REPO) == 2
    
    # Verify base64 encoding
    decoded = base64.b64decode(VIP_REPO[1])
    assert len(decoded) > 0
```

## 🎯 Test Coverage

The test suite aims for comprehensive coverage of:

### Core Components (Target: 90%+ coverage)
- ✅ **ModelData** - Model configuration and validation
- ✅ **ProcessingWorker** - Audio processing workflow
- ✅ **UVRCoreAdapter** - Core UVR integration
- 🔄 **EnsembleSettings** - Ensemble configuration
- 🔄 **AppConstants** - Application constants

### Edge Cases & Error Handling
- ✅ Invalid input validation
- ✅ File system errors
- ✅ Memory constraints
- ✅ Network failures
- ✅ Malformed data handling

### Audio Processing
- ✅ Different audio formats
- ✅ Various sample rates
- ✅ Mono/stereo handling
- ✅ Empty audio arrays
- ✅ Ensemble combinations

## 🔧 Test Configuration

### pytest.ini Configuration
```ini
[pytest]
qt_api = pyside6
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    ui: UI/GUI tests
    ensemble: Ensemble processing tests
    edge_case: Edge cases and error conditions
```

### Coverage Settings
- **Target Coverage**: 80% minimum
- **Reports**: Terminal, HTML, XML
- **Exclusions**: Test files, migrations, generated code

## 🚨 Continuous Integration

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### CI Pipeline Tests
1. **Linting** - Code quality checks
2. **Unit Tests** - Fast component tests
3. **Integration Tests** - Cross-component tests
4. **Coverage Report** - Ensure coverage targets

## 📋 Test Commands Reference

### Basic Commands
```bash
# Install dependencies
./run_tests.sh --install-deps

# Run all tests
./run_tests.sh --all

# Run with coverage
./run_tests.sh --all --coverage

# Run unit tests only
./run_tests.sh --unit

# Run integration tests
./run_tests.sh --integration
```

### Category-Specific Tests
```bash
# Ensemble tests
./run_tests.sh --ensemble

# Edge case tests
./run_tests.sh --edge-cases

# VIP download functionality tests
./run_tests.sh --category vip

# Fast tests only
./run_tests.sh --fast

# Custom category
./run_tests.sh --category audio
```

### Development Commands
```bash
# Verbose output
./run_tests.sh --unit --verbose

# Code linting
./run_tests.sh --lint

# Coverage report only
./run_tests.sh --coverage-only
```

### Direct pytest Commands
```bash
# Run specific test file
pytest tests/unit/core/test_model_data.py -v

# Run specific test method
pytest tests/unit/core/test_model_data.py::TestModelData::test_creation -v

# Run tests matching pattern
pytest -k "ensemble" -v

# Run with specific markers
pytest -m "unit and not slow" -v
```

## 🐛 Debugging Tests

### Common Issues

1. **Qt Application Errors**
   ```bash
   # Ensure QApplication is properly initialized
   # Use qtbot fixture for Qt tests
   ```

2. **Import Errors**
   ```bash
   # Check PYTHONPATH includes src/
   export PYTHONPATH="${PYTHONPATH}:src"
   ```

3. **Mock Issues**
   ```bash
   # Use proper mock specifications
   mock_obj = Mock(spec=RealClass)
   ```

### Debug Mode
```bash
# Run with debug output
pytest --tb=long --capture=no -v

# Run single test with debugging
pytest tests/unit/core/test_model_data.py::TestModelData::test_creation --pdb
```

## 📈 Best Practices

### Test Organization
- ✅ One test class per component
- ✅ Descriptive test method names
- ✅ Proper test categorization with markers
- ✅ Shared fixtures in conftest.py

### Test Quality
- ✅ Test both success and failure cases
- ✅ Use meaningful assertions
- ✅ Mock external dependencies
- ✅ Test edge cases and boundary conditions

### Performance
- ✅ Use fast tests for development
- ✅ Mark slow tests appropriately
- ✅ Mock expensive operations
- ✅ Parallel test execution when possible

### Maintenance
- ✅ Keep tests simple and focused
- ✅ Update tests when code changes
- ✅ Remove obsolete tests
- ✅ Document complex test scenarios

## 🤝 Contributing

When adding new features:

1. **Write tests first** (TDD approach)
2. **Add appropriate markers** for categorization
3. **Update fixtures** if needed
4. **Maintain coverage** targets
5. **Document complex tests**

### Test Review Checklist
- [ ] Tests cover new functionality
- [ ] Edge cases are tested
- [ ] Appropriate markers are used
- [ ] Coverage targets are met
- [ ] Tests are documented
- [ ] CI pipeline passes

## 📚 Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-qt Documentation](https://pytest-qt.readthedocs.io/)
- [PySide6 Testing Guide](https://doc.qt.io/qtforpython/tutorials/index.html)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

For questions or issues with the testing infrastructure, please check the existing tests for examples or create an issue in the project repository. 