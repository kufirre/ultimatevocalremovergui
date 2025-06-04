#!/bin/bash
# Code formatting script for UVR PySide6 project
# This script automatically formats code to maintain consistent style

set -e  # Exit on any error

echo "🎨 Starting code formatting..."

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Make sure you have the dev dependencies installed."
fi

# Format Python code with black
echo "📝 Running black formatter..."
python -m black src/ tests/ --line-length=88

# Sort and organize imports with ruff (replacing isort to avoid conflicts)
echo "📋 Fixing imports with ruff..."
python -m ruff check src/ tests/ --fix --select I

# Format additional files if they exist
echo "📄 Formatting standalone files..."
if [ -f "setup.py" ]; then
    python -m black setup.py --line-length=88
fi

if [ -f "conftest.py" ]; then
    python -m black conftest.py --line-length=88
fi

echo "✅ Code formatting completed!"
echo "📊 Summary:"
echo "   - Black: Python code formatted to 88 character line length"
echo "   - Ruff: Imports sorted and organized"
echo "   - Target: Python 3.8+ compatibility" 