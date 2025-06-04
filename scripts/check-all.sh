#!/bin/bash
# Comprehensive quality check script for UVR PySide6 project
# This script runs the complete development quality pipeline

set -e  # Exit on any error

echo "🏆 Running comprehensive quality checks for UVR PySide6..."
echo "============================================================="

# Initialize error tracking
TOTAL_ERRORS=0
declare -a FAILED_STEPS=()

# Function to track failures
track_failure() {
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
    FAILED_STEPS+=("$1")
}

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Not in a virtual environment."
    echo "    Make sure you have the dev dependencies installed: pip install -e \".[dev]\""
    echo ""
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Step 1: Check dependencies
echo "📦 Step 1: Installing/checking dependencies..."
if command -v python &> /dev/null && command -v pip &> /dev/null; then
    echo "✅ All required dependencies available"
else
    echo "❌ Missing required dependencies (python/pip)"
    track_failure "Dependencies"
fi

# Step 2: Code formatting
echo ""
echo "🎨 Step 2: Code formatting check..."
if bash "$SCRIPT_DIR/format.sh"; then
    echo "✅ Formatting completed successfully"
else
    echo "❌ Formatting failed"
    track_failure "Formatting"
fi

# Step 3: Critical tests (NEW - run before linting to catch import issues)
echo ""
echo "🚨 Step 3: Critical functionality tests..."
if python -m pytest tests/unit/core/test_application_startup.py -m critical -v --tb=short; then
    echo "✅ Critical tests passed"
else
    echo "❌ Critical tests failed - Core functionality broken!"
    track_failure "Critical Tests"
fi

# Step 4: Linting and code quality
echo ""
echo "🔍 Step 4: Code linting and quality checks..."
if bash "$SCRIPT_DIR/lint.sh"; then
    echo "✅ Linting passed successfully"
else
    echo "❌ Linting found issues"
    track_failure "Linting"
fi

# Step 5: Full test suite
echo ""
echo "🧪 Step 5: Running test suite..."
if ./run_tests.sh --all; then
    echo "✅ All tests passed successfully"
else
    echo "❌ Tests failed"
    track_failure "Tests"
fi

# Step 6: Coverage report (only for src/)
echo ""
echo "📊 Step 6: Generating coverage report..."
if python -m pytest --cov=uvr_pyside6_ui --cov-report=html:htmlcov --cov-report=xml --cov-report=term-missing tests/ --tb=short; then
    echo "✅ Coverage report generated in htmlcov/"
else
    echo "❌ Coverage generation failed"
    track_failure "Coverage"
fi

# Summary
echo ""
echo "🏁 Quality Check Summary:"
echo "========================="

if [ $TOTAL_ERRORS -eq 0 ]; then
    echo "🎉 ALL QUALITY CHECKS PASSED!"
    echo ""
    echo "✅ Code formatting: PASSED"
    echo "✅ Critical tests: PASSED"
    echo "✅ Linting & style: PASSED"
    echo "✅ Type checking: PASSED"
    echo "✅ Test suite: PASSED"
    echo "✅ Coverage report: GENERATED"
    echo ""
    echo "🚀 Your code is ready for commit and deployment!"
    echo ""
    echo "📋 Focus areas (src/ and tests/ only):"
    echo "   - All legacy files (UVR.py, separate.py) excluded from checks"
    echo "   - Modern PySide6 codebase maintains high quality standards"
    echo "   - Critical functionality protected against regressions"
    exit 0
else
    echo "❌ SOME QUALITY CHECKS FAILED"
    echo ""
    echo "Failed steps:"
    for step in "${FAILED_STEPS[@]}"; do
        echo "  ❌ $step"
    done
    echo ""
    echo "🔧 Please review and fix the issues above before committing."
    echo "💡 You can run individual scripts to focus on specific issues:"
    echo "   - ./scripts/format.sh  (fix formatting)"
    echo "   - ./scripts/lint.sh    (check linting)"
    echo "   - ./run_tests.sh       (run tests only)"
    echo "   - pytest -m critical   (run critical tests only)"
    echo ""
    echo "📋 Note: Quality checks focus on src/ and tests/ directories only"
    exit 1
fi 