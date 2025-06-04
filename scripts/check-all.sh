#!/bin/bash
# Comprehensive quality check script for UVR PySide6 project
# This script runs all quality checks: linting, formatting, type checking, and tests

set -e  # Exit on any error

echo "🏆 Running comprehensive quality checks for UVR PySide6..."
echo "============================================================="

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Not in a virtual environment."
    echo "    Make sure you have the dev dependencies installed: pip install -e \".[dev]\""
    echo ""
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Initialize overall status
OVERALL_SUCCESS=true

echo "📦 Step 1: Installing/checking dependencies..."
python -c "import black, ruff, mypy, pytest" 2>/dev/null || {
    echo "❌ Missing required dev dependencies"
    echo "💡 Run: pip install -e \".[dev]\""
    exit 1
}
echo "✅ All required dependencies available"
echo ""

echo "🎨 Step 2: Code formatting check..."
if bash "$SCRIPT_DIR/format.sh"; then
    echo "✅ Formatting completed successfully"
else
    echo "❌ Formatting failed"
    OVERALL_SUCCESS=false
fi
echo ""

echo "🔍 Step 3: Code linting and quality checks..."
if bash "$SCRIPT_DIR/lint.sh"; then
    echo "✅ Linting passed successfully"
else
    echo "❌ Linting found issues"
    OVERALL_SUCCESS=false
fi
echo ""

echo "🧪 Step 4: Running test suite..."
if bash run_tests.sh; then
    echo "✅ All tests passed successfully"
else
    echo "❌ Some tests failed"
    OVERALL_SUCCESS=false
fi
echo ""

echo "📊 Step 5: Generating coverage report..."
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=0 -q
echo "✅ Coverage report generated in htmlcov/"
echo ""

# Final summary
echo "🏁 Quality Check Summary:"
echo "========================="
if [ "$OVERALL_SUCCESS" = true ]; then
    echo "🎉 ALL QUALITY CHECKS PASSED!"
    echo ""
    echo "✅ Code formatting: PASSED"
    echo "✅ Linting & style: PASSED"  
    echo "✅ Type checking: PASSED"
    echo "✅ Test suite: PASSED"
    echo "✅ Coverage report: GENERATED"
    echo ""
    echo "🚀 Your code is ready for commit and deployment!"
    exit 0
else
    echo "❌ SOME QUALITY CHECKS FAILED"
    echo ""
    echo "🔧 Please review and fix the issues above before committing."
    echo "💡 You can run individual scripts to focus on specific issues:"
    echo "   - ./scripts/format.sh  (fix formatting)"
    echo "   - ./scripts/lint.sh    (check linting)"
    echo "   - ./run_tests.sh       (run tests only)"
    exit 1
fi 