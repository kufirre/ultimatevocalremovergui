#!/bin/bash
# Pre-commit checks for UVR PySide6 project
# This script runs essential checks before allowing commits

set -e

echo "🔒 Running pre-commit checks..."
echo "================================"

# Function to print colored output
print_status() {
    if [ "$2" = "success" ]; then
        echo "✅ $1"
    elif [ "$2" = "error" ]; then
        echo "❌ $1"
    elif [ "$2" = "warning" ]; then
        echo "⚠️  $1"
    else
        echo "ℹ️  $1"
    fi
}

# Track failures
FAILED_CHECKS=0

# Check 1: Critical functionality tests (MANDATORY)
echo ""
echo "🚨 Running critical functionality tests..."
if python -m pytest tests/unit/core/test_application_startup.py -m critical -q --tb=line; then
    print_status "Critical tests passed" "success"
else
    print_status "Critical tests failed - BLOCKING COMMIT" "error"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check 2: Fast linting (MANDATORY) - only src/ and tests/
echo ""
echo "🔍 Running fast linting checks..."
if python -m ruff check src/ tests/ --output-format=concise; then
    print_status "Ruff linting passed" "success"
else
    print_status "Linting issues found - BLOCKING COMMIT" "error"
    echo "💡 Run 'python -m ruff check src/ tests/ --fix' to auto-fix"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check 3: Import organization (MANDATORY) - only src/ and tests/
echo ""
echo "📦 Checking import organization..."
if python -m ruff check src/ tests/ --select I --output-format=concise; then
    print_status "Import organization correct" "success"
else
    print_status "Import issues found - BLOCKING COMMIT" "error"
    echo "💡 Run 'python -m ruff check src/ tests/ --fix --select I' to auto-fix"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Check 4: Code formatting (WARNING ONLY) - only src/ and tests/
echo ""
echo "🎨 Checking code formatting..."
if python -m black --check src/ tests/ --line-length=88 --quiet; then
    print_status "Code formatting correct" "success"
else
    print_status "Code formatting issues found" "warning"
    echo "💡 Run 'make format' or 'python -m black src/ tests/' to fix"
    # Don't increment FAILED_CHECKS - this is just a warning
fi

# Check 5: Quick smoke test for main module import
echo ""
echo "🔥 Running import smoke test..."
if python -c "
import sys
sys.path.insert(0, 'src')
try:
    import uvr_pyside6_ui.resources_rc
    from uvr_pyside6_ui.core import app_constants
    from uvr_pyside6_ui.main import run
    print('✅ Core modules importable')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"; then
    print_status "Core modules import successfully" "success"
else
    print_status "Core module import failed - BLOCKING COMMIT" "error"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# Summary
echo ""
echo "📊 Pre-commit Summary:"
echo "====================="

if [ $FAILED_CHECKS -eq 0 ]; then
    print_status "All mandatory checks passed - COMMIT ALLOWED" "success"
    echo ""
    echo "🚀 Your changes are ready to commit!"
    exit 0
else
    print_status "Some mandatory checks failed - COMMIT BLOCKED" "error"
    echo ""
    echo "❌ Failed checks: $FAILED_CHECKS"
    echo ""
    echo "🔧 Please fix the issues above before committing."
    echo "💡 Quick fixes:"
    echo "   - Run 'make format' for formatting issues"
    echo "   - Run 'make lint' for detailed linting"
    echo "   - Run 'pytest -m critical' for critical tests"
    echo "   - Run 'make check-all' for comprehensive checks"
    exit 1
fi 