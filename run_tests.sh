#!/bin/bash

# Test runner script for UVR PySide6 application
# 
# This script provides various options for running tests including:
# - Unit tests only
# - Integration tests only  
# - All tests
# - Coverage reports
# - Specific test categories

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emoji support detection
if command -v printf >/dev/null 2>&1; then
    SUCCESS_ICON="✅"
    FAILURE_ICON="❌"
    WARNING_ICON="⚠️"
    CELEBRATE_ICON="🎉"
    REPORT_ICON="📊"
else
    SUCCESS_ICON="[OK]"
    FAILURE_ICON="[FAIL]"
    WARNING_ICON="[WARN]"
    CELEBRATE_ICON="[SUCCESS]"
    REPORT_ICON="[REPORT]"
fi

# Function to print colored output
print_header() {
    echo
    printf "${BLUE}%s${NC}\n" "$(printf '=%.0s' {1..60})"
    if [ -n "$1" ]; then
        printf "${BLUE}Running: %s${NC}\n" "$1"
    fi
    printf "${BLUE}Command: %s${NC}\n" "$2"
    printf "${BLUE}%s${NC}\n" "$(printf '=%.0s' {1..60})"
}

print_success() {
    printf "\n${GREEN}%s %s${NC}\n" "$SUCCESS_ICON" "$1"
}

print_error() {
    printf "\n${RED}%s %s${NC}\n" "$FAILURE_ICON" "$1"
}

print_warning() {
    printf "\n${YELLOW}%s %s${NC}\n" "$WARNING_ICON" "$1"
}

# Function to run commands with error handling
run_command() {
    local description="$1"
    shift
    local cmd=("$@")
    
    print_header "$description" "${cmd[*]}"
    
    if "${cmd[@]}"; then
        print_success "${description:-Command} completed successfully!"
        return 0
    else
        local exit_code=$?
        print_error "${description:-Command} failed with exit code $exit_code"
        return $exit_code
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python and pytest availability
check_dependencies() {
    if ! command_exists python3; then
        print_error "Python 3 is required but not found"
        exit 1
    fi
    
    if ! python3 -m pytest --version >/dev/null 2>&1; then
        print_warning "pytest not found. Installing test dependencies..."
        install_test_dependencies
    fi
}

# Install test dependencies
install_test_dependencies() {
    print_header "Installing test dependencies"
    if [ -f "requirements-test.txt" ]; then
        run_command "Installing test dependencies" python3 -m pip install -r requirements-test.txt
    else
        print_error "requirements-test.txt not found"
        return 1
    fi
}

# Run unit tests only
run_unit_tests() {
    local verbose=""
    local coverage=""
    
    [ "$VERBOSE" = "true" ] && verbose="-v"
    [ "$COVERAGE" = "true" ] && coverage="--cov=src/uvr_pyside6_ui --cov-report=term-missing"
    
    run_command "Unit Tests" python3 -m pytest tests/unit/ -m unit $verbose $coverage
}

# Run integration tests only
run_integration_tests() {
    local verbose=""
    [ "$VERBOSE" = "true" ] && verbose="-v"
    
    run_command "Integration Tests" python3 -m pytest tests/ -m integration $verbose
}

# Run all tests
run_all_tests() {
    local verbose=""
    local coverage=""
    
    [ "$VERBOSE" = "true" ] && verbose="-v"
    
    if [ "$COVERAGE" = "true" ]; then
        coverage="--cov=src/uvr_pyside6_ui --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml"
    fi
    
    run_command "All Tests" python3 -m pytest tests/ $verbose $coverage
}

# Run tests for specific category
run_specific_category() {
    local category="$1"
    local verbose=""
    [ "$VERBOSE" = "true" ] && verbose="-v"
    
    run_command "Tests for category: $category" python3 -m pytest tests/ -m "$category" $verbose
}

# Run fast tests (exclude slow tests)
run_fast_tests() {
    local verbose=""
    [ "$VERBOSE" = "true" ] && verbose="-v"
    
    run_command "Fast Tests (excluding slow tests)" python3 -m pytest tests/ -m "not slow" $verbose
}

# Run ensemble-specific tests
run_ensemble_tests() {
    local verbose=""
    [ "$VERBOSE" = "true" ] && verbose="-v"
    
    run_command "Ensemble Tests" python3 -m pytest tests/ -m ensemble $verbose
}

# Run edge case tests
run_edge_case_tests() {
    local verbose=""
    [ "$VERBOSE" = "true" ] && verbose="-v"
    
    run_command "Edge Case Tests" python3 -m pytest tests/ -m edge_case $verbose
}

# Run code linting checks
run_linting() {
    print_header "Running code quality checks"
    
    if command_exists flake8; then
        if python3 -m flake8 src/ --max-line-length=120 --ignore=E203,W503; then
            print_success "Flake8 linting passed!"
            return 0
        else
            print_error "Flake8 linting failed"
            return 1
        fi
    else
        print_warning "Flake8 not found. Install with: pip install flake8"
        return 0  # Don't fail if flake8 is not installed
    fi
}

# Generate detailed coverage report
generate_coverage_report() {
    local cmd=(
        python3 -m pytest tests/
        --cov=src/uvr_pyside6_ui
        --cov-report=html:htmlcov
        --cov-report=xml
        --cov-report=term-missing
        --cov-fail-under=80
    )
    
    if run_command "Coverage Report Generation" "${cmd[@]}"; then
        echo
        printf "${GREEN}%s Coverage reports generated:${NC}\n" "$REPORT_ICON"
        echo "  - HTML report: htmlcov/index.html"
        echo "  - XML report: coverage.xml"
        echo "  - Terminal report shown above"
        return 0
    else
        return 1
    fi
}

# Show help
show_help() {
    cat << EOF
Test runner for UVR PySide6 application

Usage: $0 [OPTIONS]

Test Types:
  --all                 Run all tests
  --unit                Run unit tests only
  --integration         Run integration tests only
  --fast                Run fast tests only (exclude slow)
  --ensemble            Run ensemble tests only
  --edge-cases          Run edge case tests only
  --category CATEGORY   Run tests for specific category

Options:
  --verbose, -v         Verbose output
  --coverage, -c        Generate coverage report
  --install-deps        Install test dependencies
  --lint                Run code linting
  --coverage-only       Generate coverage report only
  --help, -h            Show this help message

Examples:
  $0 --all --coverage          # Run all tests with coverage
  $0 --unit --verbose          # Run unit tests with verbose output
  $0 --category ensemble       # Run ensemble-specific tests
  $0 --fast                    # Run only fast tests
  $0 --install-deps            # Install test dependencies
  $0 --lint                    # Run code linting
  $0 --coverage-only           # Generate coverage report only

EOF
}

# Main function
main() {
    # Default values
    local test_type=""
    local category=""
    VERBOSE="false"
    COVERAGE="false"
    local install_deps="false"
    local run_lint="false"
    local coverage_only="false"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                test_type="all"
                shift
                ;;
            --unit)
                test_type="unit"
                shift
                ;;
            --integration)
                test_type="integration"
                shift
                ;;
            --fast)
                test_type="fast"
                shift
                ;;
            --ensemble)
                test_type="ensemble"
                shift
                ;;
            --edge-cases)
                test_type="edge_cases"
                shift
                ;;
            --category)
                test_type="category"
                category="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE="true"
                shift
                ;;
            --coverage|-c)
                COVERAGE="true"
                shift
                ;;
            --install-deps)
                install_deps="true"
                shift
                ;;
            --lint)
                run_lint="true"
                shift
                ;;
            --coverage-only)
                coverage_only="true"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # If no arguments provided, show help
    if [ $# -eq 0 ] && [ "$test_type" = "" ] && [ "$install_deps" = "false" ] && [ "$run_lint" = "false" ] && [ "$coverage_only" = "false" ]; then
        show_help
        exit 0
    fi
    
    local success=true
    
    # Check dependencies
    check_dependencies
    
    # Install dependencies if requested
    if [ "$install_deps" = "true" ]; then
        if ! install_test_dependencies; then
            success=false
        fi
    fi
    
    # Run linting if requested
    if [ "$run_lint" = "true" ]; then
        if ! run_linting; then
            success=false
        fi
    fi
    
    # Generate coverage report only
    if [ "$coverage_only" = "true" ]; then
        if ! generate_coverage_report; then
            success=false
        fi
        exit $?
    fi
    
    # Run tests based on type
    case "$test_type" in
        "all")
            if ! run_all_tests; then
                success=false
            fi
            ;;
        "unit")
            if ! run_unit_tests; then
                success=false
            fi
            ;;
        "integration")
            if ! run_integration_tests; then
                success=false
            fi
            ;;
        "fast")
            if ! run_fast_tests; then
                success=false
            fi
            ;;
        "ensemble")
            if ! run_ensemble_tests; then
                success=false
            fi
            ;;
        "edge_cases")
            if ! run_edge_case_tests; then
                success=false
            fi
            ;;
        "category")
            if [ -z "$category" ]; then
                print_error "Category name required with --category option"
                exit 1
            fi
            if ! run_specific_category "$category"; then
                success=false
            fi
            ;;
    esac
    
    # Print summary
    echo
    printf "${BLUE}%s${NC}\n" "$(printf '=%.0s' {1..60})"
    if [ "$success" = "true" ]; then
        printf "${GREEN}%s All operations completed successfully!${NC}\n" "$CELEBRATE_ICON"
    else
        printf "${RED}%s Some operations failed. Check the output above.${NC}\n" "$FAILURE_ICON"
        exit 1
    fi
    printf "${BLUE}%s${NC}\n" "$(printf '=%.0s' {1..60})"
}

# Run main function with all arguments
main "$@" 