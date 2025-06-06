#!/bin/bash
# Automatic linting fix script for UVR PySide6 project
# This script automatically fixes as many linting issues as possible

set -e  # Exit on any error

echo "🔧 Auto-fixing linting issues..."
echo "================================"

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Make sure you have the dev dependencies installed."
    echo ""
fi

# Initialize counters
ISSUES_FIXED=0
REMAINING_ISSUES=0

# Function to track fixes
track_fix() {
    ISSUES_FIXED=$((ISSUES_FIXED + 1))
}

# Function to track remaining issues
track_remaining() {
    REMAINING_ISSUES=$((REMAINING_ISSUES + 1))
}

echo "🎯 Step 1: Auto-fixing code formatting..."
echo "----------------------------------------"

# Format Python code with black
echo "📝 Running black formatter..."
if python -m black src/ tests/ --line-length=88; then
    echo "✅ Black formatting applied"
    track_fix
else
    echo "❌ Black formatting failed"
    track_remaining
fi

echo ""
echo "🔍 Step 2: Auto-fixing ruff issues..."
echo "------------------------------------"

# Get initial ruff issue count
echo "📊 Checking current ruff issues..."
RUFF_OUTPUT=$(python -m ruff check src/ tests/ --output-format=concise 2>/dev/null || true)
if [ -z "$RUFF_OUTPUT" ] || echo "$RUFF_OUTPUT" | grep -q "All checks passed!"; then
    INITIAL_RUFF_ISSUES=0
else
    INITIAL_RUFF_ISSUES=$(echo "$RUFF_OUTPUT" | wc -l | tr -d ' ')
fi
echo "Found $INITIAL_RUFF_ISSUES ruff issues"

# Auto-fix ruff issues
echo "🛠️  Auto-fixing ruff issues..."
if python -m ruff check src/ tests/ --fix; then
    echo "✅ Ruff auto-fixes applied"
    track_fix
else
    echo "⚠️  Some ruff issues couldn't be auto-fixed"
    track_remaining
fi

# Check remaining ruff issues
RUFF_OUTPUT_AFTER=$(python -m ruff check src/ tests/ --output-format=concise 2>/dev/null || true)
if [ -z "$RUFF_OUTPUT_AFTER" ] || echo "$RUFF_OUTPUT_AFTER" | grep -q "All checks passed!"; then
    REMAINING_RUFF_ISSUES=0
else
    REMAINING_RUFF_ISSUES=$(echo "$RUFF_OUTPUT_AFTER" | wc -l | tr -d ' ')
fi
FIXED_RUFF_ISSUES=$((INITIAL_RUFF_ISSUES - REMAINING_RUFF_ISSUES))

if [ $FIXED_RUFF_ISSUES -gt 0 ]; then
    echo "🎉 Fixed $FIXED_RUFF_ISSUES ruff issues"
fi

if [ $REMAINING_RUFF_ISSUES -gt 0 ]; then
    echo "⚠️  $REMAINING_RUFF_ISSUES ruff issues still need manual attention"
    track_remaining
fi

echo ""
echo "📋 Step 3: Organizing imports..."
echo "-------------------------------"

# Fix imports with ruff
echo "📦 Sorting imports with ruff..."
if python -m ruff check src/ tests/ --fix --select I,F401; then
    echo "✅ Import organization applied"
    track_fix
else
    echo "⚠️  Some import issues couldn't be auto-fixed"
    track_remaining
fi

echo ""
echo "🔒 Step 4: Security check..."
echo "---------------------------"

# Run bandit for security (informational only)
echo "🛡️  Running security scan..."
if python -m bandit -r src/ -f json -o bandit-report.json -q; then
    echo "✅ No security issues found"
else
    echo "ℹ️  Security report saved as bandit-report.json (review recommended)"
fi

echo ""
echo "🧹 Step 5: Additional cleanup..."
echo "-------------------------------"

# Remove unused imports more aggressively
echo "🗑️  Removing unused imports..."
if command -v autoflake &> /dev/null; then
    if autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive src/ tests/; then
        echo "✅ Unused imports and variables removed"
        track_fix
    else
        echo "⚠️  Some unused imports couldn't be removed automatically"
    fi
else
    echo "ℹ️  autoflake not available (install with: pip install autoflake)"
fi

# Final formatting pass to ensure consistency
echo "🎨 Final formatting pass..."
python -m black src/ tests/ --line-length=88 --quiet

echo ""
echo "🔍 Step 6: Verification..."
echo "------------------------"

# Run a final check to see what's left
echo "📊 Running final linting check..."

# Check ruff
FINAL_RUFF_OUTPUT=$(python -m ruff check src/ tests/ --output-format=concise 2>/dev/null || true)
if [ -z "$FINAL_RUFF_OUTPUT" ] || echo "$FINAL_RUFF_OUTPUT" | grep -q "All checks passed!"; then
    FINAL_RUFF_ISSUES=0
else
    FINAL_RUFF_ISSUES=$(echo "$FINAL_RUFF_OUTPUT" | wc -l | tr -d ' ')
fi

# Check flake8 (less strict for final count)
FINAL_FLAKE8_OUTPUT=$(python -m flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503,E501,E402,E712,F841,F811 2>/dev/null || true)
if [ -z "$FINAL_FLAKE8_OUTPUT" ]; then
    FINAL_FLAKE8_ISSUES=0
else
    FINAL_FLAKE8_ISSUES=$(echo "$FINAL_FLAKE8_OUTPUT" | wc -l | tr -d ' ')
fi

# Check black
BLACK_OUTPUT=$(python -m black --check src/ tests/ --line-length=88 --quiet 2>&1 | grep "would reformat" || true)
if [ -z "$BLACK_OUTPUT" ]; then
    BLACK_ISSUES=0
else
    BLACK_ISSUES=$(echo "$BLACK_OUTPUT" | wc -l | tr -d ' ')
fi

echo ""
echo "🏁 Auto-Fix Summary:"
echo "==================="
echo "🔧 Issues automatically fixed: $ISSUES_FIXED"
echo "⚠️  Issues requiring manual attention: $REMAINING_ISSUES"
echo ""
echo "📊 Remaining issues:"
echo "   - Ruff: $FINAL_RUFF_ISSUES issues"
echo "   - Flake8: $FINAL_FLAKE8_ISSUES issues"
echo "   - Black: $BLACK_ISSUES formatting issues"
echo ""

if [ $FINAL_RUFF_ISSUES -eq 0 ] && [ $FINAL_FLAKE8_ISSUES -eq 0 ] && [ $BLACK_ISSUES -eq 0 ]; then
    echo "🎉 ALL LINTING ISSUES RESOLVED!"
    echo "✅ Code is now ready for commit"
    echo ""
    echo "💡 Next steps:"
    echo "   - Run 'make check-all' to verify everything passes"
    echo "   - Commit your changes"
    exit 0
else
    echo "🔧 SOME ISSUES STILL NEED MANUAL ATTENTION"
    echo ""
    echo "💡 Next steps:"
    echo "   - Review remaining issues with: ./scripts/lint.sh"
    echo "   - Fix any remaining issues manually"
    echo "   - Run 'make check-all' to verify everything passes"
    
    if [ $FINAL_RUFF_ISSUES -gt 0 ]; then
        echo ""
        echo "🔍 View remaining ruff issues:"
        echo "   python -m ruff check src/ tests/"
    fi
    
    if [ $FINAL_FLAKE8_ISSUES -gt 0 ]; then
        echo ""
        echo "📋 View remaining flake8 issues:"
        echo "   python -m flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503,E501,E402,E712,F841,F811"
    fi
    
    exit 1
fi 