#!/bin/bash
# Code formatting script for UVR PySide6 project
# This script formats Python code using black and isort

set -e  # Exit on any error

echo "🎨 Starting code formatting..."

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Make sure you have the dev dependencies installed."
fi

# Format with black
echo "📝 Running black formatter..."
python -m black src/ tests/ --line-length 88 --target-version py38 --verbose

# Sort imports with isort (compatible with black)
echo "📋 Sorting imports with isort..."
python -m isort src/ tests/ --profile black --line-length 88 --multi-line 3 --trailing-comma --force-grid-wrap 0 --combine-as --src src

# Optional: Format any standalone Python files
if [ -f "UVR.py" ]; then
    echo "📄 Formatting standalone files..."
    python -m black UVR.py --line-length 88 --target-version py38
    python -m isort UVR.py --profile black
fi

if [ -f "separate.py" ]; then
    python -m black separate.py --line-length 88 --target-version py38
    python -m isort separate.py --profile black
fi

echo "✅ Code formatting completed!"
echo "📊 Summary:"
echo "   - Black: Python code formatted to 88 character line length"
echo "   - isort: Imports sorted and organized"
echo "   - Target: Python 3.8+ compatibility" 