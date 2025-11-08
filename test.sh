#!/bin/bash
#
# test.sh - Comprehensive Test Suite Runner
#
# Runs all test scripts in sequence and reports overall results
# Usage: ./test.sh
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Test scripts to run
TEST_SCRIPTS=(
    "test_fetch.sh"
    "test_aggregated_stats.sh"
    "test_risk_analysis.sh"
)

# Results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

print_banner() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  Crypto Portfolio - Test Suite Runner${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

print_test_header() {
    echo ""
    echo -e "${BLUE}========================================"
    echo -e "Running: $1"
    echo -e "========================================${NC}"
    echo ""
}

print_test_result() {
    local test_name=$1
    local exit_code=$2

    ((TOTAL_TESTS++))

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ $test_name PASSED${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}❌ $test_name FAILED${NC}"
        ((FAILED_TESTS++))
    fi
}

print_summary() {
    echo ""
    echo -e "${CYAN}========================================"
    echo -e "Overall Test Summary"
    echo -e "========================================${NC}"
    echo ""
    echo -e "Total test suites: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL TEST SUITES PASSED! 🎉${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}⚠️  SOME TEST SUITES FAILED ⚠️${NC}"
        echo ""
        return 1
    fi
}

# ==================== Main Execution ====================

print_banner

# Check if scripts exist and are executable
for script in "${TEST_SCRIPTS[@]}"; do
    if [ ! -f "$SCRIPT_DIR/$script" ]; then
        echo -e "${RED}Error: Test script '$script' not found${NC}"
        exit 1
    fi

    if [ ! -x "$SCRIPT_DIR/$script" ]; then
        echo "Making $script executable..."
        chmod +x "$SCRIPT_DIR/$script"
    fi
done

# Run each test script
for script in "${TEST_SCRIPTS[@]}"; do
    print_test_header "$script"

    # Run the test script and capture exit code
    "$SCRIPT_DIR/$script"
    EXIT_CODE=$?

    # Record result
    print_test_result "$script" $EXIT_CODE

    # Add separator between tests
    echo ""
    echo -e "${CYAN}----------------------------------------${NC}"
done

# Print overall summary
print_summary
SUMMARY_EXIT_CODE=$?

exit $SUMMARY_EXIT_CODE
