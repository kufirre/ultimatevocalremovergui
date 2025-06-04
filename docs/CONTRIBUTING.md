# Contributing to Ultimate Vocal Remover PySide6 Edition

Thank you for your interest in contributing to the Ultimate Vocal Remover PySide6 project! This guide will help you get started with contributing to this enterprise-grade audio separation application.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Quality Standards](#quality-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

This project and everyone participating in it is governed by respect, inclusivity, and collaboration. We are committed to providing a welcoming and inspiring community for all.

### Our Standards

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome newcomers and help them succeed
- **Be collaborative**: Work together to solve problems
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone is learning

## Getting Started

### Prerequisites

- **Python 3.8+** (Python 3.10+ recommended)
- **Git** for version control
- **Basic understanding** of audio processing concepts
- **Familiarity** with PySide6/Qt (helpful but not required)

### Types of Contributions

We welcome contributions in the following areas:

- **Bug fixes**: Resolving issues and improving stability
- **Feature development**: Adding new functionality
- **Testing**: Expanding test coverage and improving test quality
- **Documentation**: Improving user and developer documentation
- **Performance**: Optimizing speed and memory usage
- **UI/UX**: Enhancing the user interface and experience
- **Quality assurance**: Improving code quality and standards

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ultimatevocalremovergui.git
cd ultimatevocalremovergui
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv uvr-dev
source uvr-dev/bin/activate  # On Windows: uvr-dev\Scripts\activate

# Install in development mode with all tools
pip install -e ".[dev]"

# Set up pre-commit hooks (IMPORTANT)
pre-commit install

# Verify setup with critical tests
make test-critical
```

### 3. Verify Installation

```bash
# Run the application to ensure it works
uvr-gui

# Run quality checks to ensure everything is working
make check-all
```

## Development Workflow

### 1. Branch Strategy

```bash
# Create a feature branch
git checkout -b feature/amazing-feature

# Or for bug fixes
git checkout -b fix/issue-description
```

### 2. Development Process

1. **Write tests first** (TDD approach recommended)
2. **Implement your changes** with clear, readable code
3. **Run quality checks** frequently during development
4. **Update documentation** as needed
5. **Test thoroughly** on your local system

### 3. Quality Checks

Run these commands before committing:

```bash
# Format code
make format

# Run linting
make lint

# Run critical tests (MUST PASS)
make test-critical

# Run all tests
make test

# Complete quality pipeline
make check-all
```

### 4. Commit Guidelines

Use clear, descriptive commit messages:

```bash
# Good commit messages
git commit -m "Fix QRC resource loading for custom themes"
git commit -m "Add support for Demucs v5 models"
git commit -m "Improve memory usage in large file processing"

# Include issue numbers when relevant
git commit -m "Fix audio export bug (fixes #123)"
```

## Quality Standards

### Code Quality Requirements

- ✅ **All tests must pass** (especially critical tests)
- ✅ **Code formatting** with Black (88-character lines)
- ✅ **Import organization** with Ruff
- ✅ **No critical linting issues**
- ✅ **Type hints** for all public functions
- ✅ **Docstrings** for all public APIs (Google style)

### Quality Tools

Our automated tools will check your code:

```bash
# Individual tools
black src/ tests/          # Code formatting
ruff check src/ tests/     # Fast linting
mypy src/                  # Type checking (progressive)
bandit -r src/             # Security scanning
pytest tests/              # Test execution
```

### Pre-commit Hooks

Pre-commit hooks automatically run quality checks:

- **Black**: Code formatting
- **Ruff**: Import sorting and linting
- **MyPy**: Type checking
- **Bandit**: Security scanning
- **Critical Tests**: Essential functionality verification

If pre-commit hooks fail, fix the issues before committing.

## Testing Guidelines

### Test Requirements

- **All new features** must include comprehensive tests
- **Bug fixes** must include regression tests
- **Critical functionality** must maintain 100% test coverage
- **UI components** should include Qt signal testing where appropriate

### Test Categories

```bash
# Unit tests (fast, isolated)
pytest -m unit

# Integration tests (component interaction)
pytest -m integration

# Critical tests (essential functionality)
pytest -m critical

# Edge case tests (boundary conditions)
pytest -m edge_case
```

### Writing Tests

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.mark.unit
def test_my_feature():
    """Test my new feature functionality."""
    # Arrange
    input_data = "test_input"
    expected_result = "expected_output"
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == expected_result

@pytest.mark.critical
def test_critical_functionality():
    """Test that critical functionality works correctly."""
    # Critical tests protect against regressions
    # They must always pass and run before every commit
    pass
```

### Test Guidelines

- **Use descriptive test names** that explain what is being tested
- **Follow AAA pattern**: Arrange, Act, Assert
- **Mock external dependencies** (audio files, network calls, etc.)
- **Test edge cases** and error conditions
- **Keep tests focused** on a single behavior

## Documentation

### Documentation Standards

- **User documentation**: Focus on how to use features
- **Developer documentation**: Explain implementation details
- **API documentation**: Comprehensive docstrings for all public APIs
- **Code comments**: Explain complex logic and business rules

### Docstring Format

Use Google-style docstrings:

```python
def process_audio(audio_data: np.ndarray, model_name: str) -> Dict[str, np.ndarray]:
    """Process audio data using the specified model.
    
    Args:
        audio_data: Input audio as numpy array with shape (channels, samples)
        model_name: Name of the separation model to use
        
    Returns:
        Dictionary mapping stem names to separated audio arrays
        
    Raises:
        ModelNotFoundError: If the specified model is not available
        AudioProcessingError: If audio processing fails
        
    Example:
        >>> audio = load_audio("song.wav")
        >>> stems = process_audio(audio, "htdemucs")
        >>> vocals = stems["vocals"]
    """
    pass
```

## Pull Request Process

### Before Submitting

1. **Ensure all quality checks pass**: `make check-all`
2. **Write comprehensive tests** for your changes
3. **Update documentation** as needed
4. **Test on multiple platforms** if possible
5. **Check for breaking changes** and update accordingly

### Pull Request Guidelines

#### Title and Description
- Use clear, descriptive titles
- Include detailed description of changes
- Reference related issues: "Fixes #123" or "Addresses #456"
- Explain the motivation and impact of changes

#### Checklist
```markdown
- [ ] All quality checks pass (`make check-all`)
- [ ] Tests added/updated for new functionality
- [ ] Documentation updated where necessary
- [ ] No breaking changes (or properly documented)
- [ ] Tested on local development environment
- [ ] Pre-commit hooks installed and passing
```

#### Example PR Description
```markdown
## Summary
Fix QRC resource loading warnings by ensuring resources_rc module is properly imported.

## Changes
- Added protected import of resources_rc module in main.py
- Created comprehensive tests for QRC resource loading
- Updated documentation with resource management details

## Testing
- Added 6 new critical tests for resource loading
- All 341+ tests pass
- Verified fonts and stylesheets load correctly
- Tested on macOS and Windows

## Breaking Changes
None. This is a bug fix that improves existing functionality.

Fixes #123
```

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Code review** by maintainers
3. **Testing** on multiple platforms
4. **Documentation review** for accuracy and completeness
5. **Approval** and merge by maintainers

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

```markdown
## Bug Description
A clear and concise description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g., Windows 10, macOS 12.0, Ubuntu 20.04]
- Python version: [e.g., 3.10.0]
- UVR version: [e.g., 0.1.0]
- GPU: [e.g., RTX 3080, Apple M1, CPU only]

## Audio File Details (if relevant)
- Format: [e.g., WAV, MP3, FLAC]
- Duration: [e.g., 3:45]
- Sample rate: [e.g., 44.1kHz]
- File size: [e.g., 45MB]

## Logs
```
Paste relevant log output here (enable debug mode with UVR_DEBUG=1)
```

## Additional Context
Add any other context about the problem here.
```

### Feature Requests

For feature requests, please describe:

- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives considered**: What other approaches were considered?
- **Impact**: How would this benefit users?

## Development Tips

### Performance Considerations

- **Memory usage**: Be mindful of large audio arrays
- **GPU memory**: Consider VRAM limitations
- **Threading**: Use background workers for long operations
- **Caching**: Cache expensive computations appropriately

### UI Development

- **Responsive design**: UI should remain responsive during processing
- **Progress feedback**: Provide clear progress indication
- **Error handling**: Show user-friendly error messages
- **Accessibility**: Consider accessibility in UI design

### Audio Processing

- **Sample rate handling**: Support various sample rates
- **Format support**: Handle different audio formats gracefully
- **Quality preservation**: Maintain audio quality throughout processing
- **Error recovery**: Gracefully handle corrupted or unsupported files

## Getting Help

### Resources

- **Documentation**: Check `docs/` directory for technical details
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Code**: Read existing code for examples and patterns

### Community

- **Be patient**: Maintainers are volunteers
- **Be specific**: Provide detailed information in issues
- **Be helpful**: Help other contributors when possible
- **Be respectful**: Follow the code of conduct

## Recognition

Contributors will be recognized in:
- **README.md**: Major contributors listed in credits
- **CHANGELOG.md**: Contributions documented in releases
- **Git history**: All commits properly attributed

Thank you for contributing to Ultimate Vocal Remover PySide6 Edition! Together, we're building the best audio separation tool available. 🎵 