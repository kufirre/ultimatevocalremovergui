# Makefile for UVR PySide6 project
# Provides convenient shortcuts for common development tasks

.PHONY: help install install-dev format lint test test-fast check-all clean setup-hooks

# Default target
help:
	@echo "UVR PySide6 Development Makefile"
	@echo "================================"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install the package"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  format       - Format code with Black and isort"
	@echo "  lint         - Run linting and quality checks"
	@echo "  test         - Run the full test suite"
	@echo "  test-fast    - Run fast tests only"
	@echo "  check-all    - Run complete quality pipeline"
	@echo "  setup-hooks  - Install pre-commit hooks"
	@echo "  clean        - Clean up generated files"
	@echo ""
	@echo "Example usage:"
	@echo "  make install-dev  # Set up development environment"
	@echo "  make check-all    # Run all quality checks"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Code quality targets
format:
	@echo "🎨 Formatting code..."
	./scripts/format.sh

lint:
	@echo "🔍 Running linting checks..."
	./scripts/lint.sh

# Testing targets  
test:
	@echo "🧪 Running full test suite..."
	./run_tests.sh

test-fast:
	@echo "⚡ Running fast tests..."
	python -m pytest tests/unit/core/test_app_constants.py tests/unit/core/test_logger_utils.py -v

# Comprehensive quality check
check-all:
	@echo "🏆 Running comprehensive quality checks..."
	./scripts/check-all.sh

# Development setup
setup-hooks:
	@echo "🔧 Setting up pre-commit hooks..."
	pre-commit install
	@echo "✅ Pre-commit hooks installed"

# Cleanup targets
clean:
	@echo "🧹 Cleaning up generated files..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "✅ Cleanup completed"

# Development workflow targets
dev-setup: install-dev setup-hooks
	@echo "🚀 Development environment setup complete!"
	@echo "💡 Run 'make check-all' to verify everything works"

quick-check: format lint test-fast
	@echo "⚡ Quick quality check completed!"

# CI/CD simulation
ci: check-all
	@echo "🎯 CI pipeline simulation completed!" 