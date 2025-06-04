#!/bin/bash
# Linting script for UVR PySide6 project
# This script runs comprehensive code quality checks

set -e  # Exit on any error

echo "🔍 Starting code linting and quality checks..."

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Make sure you have the dev dependencies installed."
fi

# Initialize error counter
ERRORS=0

# Run ruff for linting and style checks
echo "🚀 Running ruff linter..."
if python -m ruff check src/ tests/ --fix; then
    echo "✅ Ruff checks passed"
else
    echo "❌ Ruff found issues"
    ((ERRORS++))
fi

# Run mypy for type checking
echo "🔍 Running mypy type checker..."
if python -m mypy src/ --ignore-missing-imports --show-error-codes --pretty; then
    echo "✅ MyPy type checks passed"
else
    echo "⚠️  MyPy found type issues (not failing the build)"
    # Don't increment errors for mypy as it may have many warnings initially
fi

# Check for potential security issues with bandit
echo "🔒 Running bandit security check..."
if python -m bandit -r src/ -f json -o bandit-report.json -ll; then
    echo "✅ Bandit security checks passed"
    rm -f bandit-report.json
else
    echo "⚠️  Bandit found potential security issues"
    if [ -f "bandit-report.json" ]; then
        echo "📄 Security report saved as bandit-report.json"
    fi
    # Don't fail on bandit issues, just warn
fi

# Check for common Python issues with flake8 (if available)
echo "📋 Running additional style checks..."
if command -v flake8 &> /dev/null; then
    if python -m flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503; then
        echo "✅ Flake8 style checks passed"
    else
        echo "⚠️  Flake8 found style issues"
        ((ERRORS++))
    fi
else
    echo "ℹ️  Flake8 not installed, skipping additional style checks"
fi

# Check imports with isort (dry-run)
echo "📦 Checking import organization..."
if python -m isort src/ tests/ --check-only --profile black; then
    echo "✅ Import organization is correct"
else
    echo "❌ Imports need reorganization (run ./scripts/format.sh)"
    ((ERRORS++))
fi

# Check formatting with black (dry-run)
echo "🎨 Checking code formatting..."
if python -m black src/ tests/ --check --line-length 88; then
    echo "✅ Code formatting is correct"
else
    echo "❌ Code needs formatting (run ./scripts/format.sh)"
    ((ERRORS++))
fi

# Summary
echo ""
echo "📊 Linting Summary:"
echo "==================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ All critical checks passed!"
    echo "🎉 Code quality looks good!"
    exit 0
else
    echo "❌ Found $ERRORS critical issue(s)"
    echo "🔧 Please fix the issues above before committing"
    exit 1
fi 