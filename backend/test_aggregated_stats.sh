#!/bin/bash
#
# test_aggregated_stats.sh - Aggregated Statistics API Test Script
#
# Tests aggregated statistics endpoints and validates response structure
# Usage: ./test_aggregated_stats.sh
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"

# Test date range (adjust based on available data)
START_DATE="2025-01-01T00:00:00Z"
END_DATE="2025-02-01T00:00:00Z"

# Counters
PASS=0
FAIL=0
WARN=0

# Helper functions
print_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

print_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

print_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARN++))
}

print_header() {
    echo ""
    echo "=================================================="
    echo "$1"
    echo "=================================================="
}

# Check if jq is available
HAS_JQ=false
if command -v jq &> /dev/null; then
    HAS_JQ=true
fi

# ==================== Precondition Checks ====================

print_header "Precondition Checks"

# Check API health
echo "Waiting for API to be ready..."
for i in {1..30}; do
    if curl -sf "$API_URL/api/v1/health" > /dev/null 2>&1; then
        print_pass "API is responding on $API_URL"
        break
    fi
    if [ $i -eq 30 ]; then
        print_fail "API not responding after 30 attempts"
        exit 1
    fi
    sleep 1
done

# ==================== Single Asset Endpoint Tests ====================

print_header "Single Asset Endpoint Tests"

# Test 1: BTC with all data types
echo ""
echo "Test 1: BTC with all data types (spot, futures, lending)"
BTC_ALL_RESPONSE=$(curl -sf "$API_URL/api/v1/aggregated-stats/BTC?start=$START_DATE&end=$END_DATE" || echo "")
if [ -z "$BTC_ALL_RESPONSE" ]; then
    print_fail "BTC endpoint failed (empty response)"
elif echo "$BTC_ALL_RESPONSE" | grep -q "asset"; then
    print_pass "BTC endpoint responding"

    # Validate response structure
    if echo "$BTC_ALL_RESPONSE" | grep -q "query"; then
        print_pass "Response contains 'query' field"
    else
        print_fail "Response missing 'query' field"
    fi

    if echo "$BTC_ALL_RESPONSE" | grep -q "timestamp"; then
        print_pass "Response contains 'timestamp' field"
    else
        print_fail "Response missing 'timestamp' field"
    fi

    # Check if spot stats are present (BTC should have spot data)
    if echo "$BTC_ALL_RESPONSE" | grep -q "current_price"; then
        print_pass "Response contains spot statistics"
    else
        print_warn "Response missing spot statistics (may be expected if no data)"
    fi
else
    print_fail "BTC endpoint returned unexpected data"
fi

# Test 2: ETH with spot only
echo ""
echo "Test 2: ETH with spot data type only"
ETH_SPOT_RESPONSE=$(curl -sf "$API_URL/api/v1/aggregated-stats/ETH?start=$START_DATE&end=$END_DATE&data_types=spot" || echo "")
if [ -z "$ETH_SPOT_RESPONSE" ]; then
    print_fail "ETH spot-only endpoint failed"
elif echo "$ETH_SPOT_RESPONSE" | grep -q "asset"; then
    print_pass "ETH spot-only endpoint responding"

    # Check that futures and lending are null or absent
    if echo "$ETH_SPOT_RESPONSE" | grep -q '"futures":null' || ! echo "$ETH_SPOT_RESPONSE" | grep -q '"futures"'; then
        print_pass "Futures correctly null when not requested"
    else
        print_warn "Futures data present when only spot requested"
    fi
else
    print_fail "ETH spot-only endpoint returned unexpected data"
fi

# Test 3: WETH with lending data (if available)
echo ""
echo "Test 3: WETH/ETH with lending data type"
LENDING_RESPONSE=$(curl -sf "$API_URL/api/v1/aggregated-stats/ETH?start=$START_DATE&end=$END_DATE&data_types=lending" || echo "")
if [ -z "$LENDING_RESPONSE" ]; then
    print_fail "Lending endpoint failed"
elif echo "$LENDING_RESPONSE" | grep -q "asset"; then
    print_pass "Lending endpoint responding"

    # Check for lending-specific fields (may be null if no data)
    if echo "$LENDING_RESPONSE" | grep -q "supply_apy_percent\|lending"; then
        print_pass "Response contains lending-related fields"
    else
        print_warn "Response missing lending fields (may be expected if no data)"
    fi
else
    print_fail "Lending endpoint returned unexpected data"
fi

# Test 4: Check JSON structure with jq (if available)
if [ "$HAS_JQ" = true ]; then
    echo ""
    echo "Test 4: JSON structure validation with jq"

    # Validate BTC response is valid JSON
    if echo "$BTC_ALL_RESPONSE" | jq empty 2>/dev/null; then
        print_pass "BTC response is valid JSON"

        # Check specific fields
        ASSET=$(echo "$BTC_ALL_RESPONSE" | jq -r '.asset' 2>/dev/null)
        if [ "$ASSET" = "BTC" ]; then
            print_pass "Asset field correctly set to 'BTC'"
        else
            print_fail "Asset field incorrect: $ASSET"
        fi

        # Check query.period_days
        PERIOD_DAYS=$(echo "$BTC_ALL_RESPONSE" | jq -r '.query.period_days' 2>/dev/null)
        if [ -n "$PERIOD_DAYS" ] && [ "$PERIOD_DAYS" != "null" ]; then
            print_pass "Query period_days field present: $PERIOD_DAYS days"
        else
            print_fail "Query period_days field missing or null"
        fi
    else
        print_fail "BTC response is not valid JSON"
    fi
else
    print_warn "jq not available, skipping JSON structure validation"
fi

# ==================== Multi-Asset Endpoint Tests ====================

print_header "Multi-Asset Endpoint Tests"

# Test 5: Multi-asset with BTC, ETH, SOL
echo ""
echo "Test 5: Multi-asset (BTC,ETH,SOL) with all data types"
MULTI_RESPONSE=$(curl -sf "$API_URL/api/v1/aggregated-stats/multi?assets=BTC,ETH,SOL&start=$START_DATE&end=$END_DATE" || echo "")
if [ -z "$MULTI_RESPONSE" ]; then
    print_fail "Multi-asset endpoint failed"
elif echo "$MULTI_RESPONSE" | grep -q "data"; then
    print_pass "Multi-asset endpoint responding"

    # Check for data field
    if echo "$MULTI_RESPONSE" | grep -q '"data"'; then
        print_pass "Response contains 'data' field"
    else
        print_fail "Response missing 'data' field"
    fi

    # Check for query field with assets list
    if echo "$MULTI_RESPONSE" | grep -q "assets"; then
        print_pass "Response contains 'assets' in query"
    else
        print_fail "Response missing 'assets' field"
    fi

    # Check for correlations field (may be null if insufficient data)
    if echo "$MULTI_RESPONSE" | grep -q "correlations"; then
        print_pass "Response contains 'correlations' field"
    else
        print_warn "Response missing 'correlations' field"
    fi
else
    print_fail "Multi-asset endpoint returned unexpected data"
fi

# Test 6: Multi-asset correlation matrix validation (if jq available)
if [ "$HAS_JQ" = true ]; then
    echo ""
    echo "Test 6: Correlation matrix structure validation"

    CORRELATIONS=$(echo "$MULTI_RESPONSE" | jq -r '.correlations' 2>/dev/null)
    if [ "$CORRELATIONS" != "null" ] && [ -n "$CORRELATIONS" ]; then
        print_pass "Correlations present in multi-asset response"

        # Check if BTC correlation exists
        BTC_BTC_CORR=$(echo "$MULTI_RESPONSE" | jq -r '.correlations.BTC.BTC' 2>/dev/null)
        if [ "$BTC_BTC_CORR" = "1" ] || [ "$BTC_BTC_CORR" = "1.0" ]; then
            print_pass "BTC self-correlation is 1.0 (correct)"
        else
            print_warn "BTC self-correlation: $BTC_BTC_CORR (expected 1.0)"
        fi
    else
        print_warn "Correlations null (may be expected if insufficient overlapping data)"
    fi
fi

# Test 7: Two-asset minimum for correlations
echo ""
echo "Test 7: Two-asset request (BTC,ETH)"
TWO_ASSET_RESPONSE=$(curl -sf "$API_URL/api/v1/aggregated-stats/multi?assets=BTC,ETH&start=$START_DATE&end=$END_DATE&data_types=spot" || echo "")
if [ -z "$TWO_ASSET_RESPONSE" ]; then
    print_fail "Two-asset endpoint failed"
elif echo "$TWO_ASSET_RESPONSE" | grep -q "data"; then
    print_pass "Two-asset endpoint responding"
else
    print_fail "Two-asset endpoint returned unexpected data"
fi

# ==================== Error Handling Tests ====================

print_header "Error Handling Tests"

# Test 8: Invalid asset (404 expected)
echo ""
echo "Test 8: Invalid asset (INVALID_ASSET)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/aggregated-stats/INVALID_ASSET?start=$START_DATE&end=$END_DATE")
if [ "$HTTP_CODE" = "404" ]; then
    print_pass "Invalid asset returns 404"
else
    print_fail "Invalid asset returned $HTTP_CODE (expected 404)"
fi

# Test 9: Date range too large (400 expected)
echo ""
echo "Test 9: Date range > 90 days (400 expected)"
LONG_END_DATE="2025-05-01T00:00:00Z"  # 4 months from start
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/aggregated-stats/BTC?start=$START_DATE&end=$LONG_END_DATE")
if [ "$HTTP_CODE" = "400" ]; then
    print_pass "Date range >90 days returns 400"
else
    print_fail "Long date range returned $HTTP_CODE (expected 400)"
fi

# Test 10: Too many assets (400 expected)
echo ""
echo "Test 10: >10 assets (400 expected)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/aggregated-stats/multi?assets=BTC,ETH,SOL,BNB,XRP,ADA,LINK,DOGE,AVAX,MATIC,ATOM&start=$START_DATE&end=$END_DATE")
if [ "$HTTP_CODE" = "400" ]; then
    print_pass "Too many assets (>10) returns 400"
else
    print_fail "Too many assets returned $HTTP_CODE (expected 400)"
fi

# Test 11: Invalid data type (400 expected)
echo ""
echo "Test 11: Invalid data_types parameter"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/aggregated-stats/BTC?start=$START_DATE&end=$END_DATE&data_types=invalid_type")
if [ "$HTTP_CODE" = "400" ]; then
    print_pass "Invalid data_types returns 400"
else
    print_fail "Invalid data_types returned $HTTP_CODE (expected 400)"
fi

# Test 12: End before start (400 expected)
echo ""
echo "Test 12: End date before start date (400 expected)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/aggregated-stats/BTC?start=$END_DATE&end=$START_DATE")
if [ "$HTTP_CODE" = "400" ]; then
    print_pass "End before start returns 400"
else
    print_fail "End before start returned $HTTP_CODE (expected 400)"
fi

# ==================== Response Field Validation ====================

if [ "$HAS_JQ" = true ]; then
    print_header "Response Field Validation"

    # Test 13: Numeric field types
    echo ""
    echo "Test 13: Numeric field validation"

    # Check spot fields are numbers (if present)
    CURRENT_PRICE=$(echo "$BTC_ALL_RESPONSE" | jq -r '.spot.current_price' 2>/dev/null)
    if [ "$CURRENT_PRICE" != "null" ] && [ -n "$CURRENT_PRICE" ]; then
        if [[ "$CURRENT_PRICE" =~ ^[0-9.]+$ ]]; then
            print_pass "current_price is numeric: $CURRENT_PRICE"
        else
            print_fail "current_price is not numeric: $CURRENT_PRICE"
        fi
    else
        print_warn "current_price not present (may be expected if no spot data)"
    fi

    # Test 14: Null handling for missing data types
    echo ""
    echo "Test 14: Null handling for unavailable data"

    # BTC typically doesn't have native lending, should be null
    BTC_LENDING=$(echo "$BTC_ALL_RESPONSE" | jq -r '.lending' 2>/dev/null)
    if [ "$BTC_LENDING" = "null" ]; then
        print_pass "Lending correctly null for BTC (no native lending)"
    else
        print_warn "Lending not null for BTC (may have WBTC mapping)"
    fi
fi

# ==================== Summary ====================

print_header "Test Summary"

echo ""
echo "Results:"
echo "--------"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${YELLOW}Warnings: $WARN${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}❌ Tests FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests PASSED${NC}"
    if [ $WARN -gt 0 ]; then
        echo -e "${YELLOW}(with $WARN warning(s))${NC}"
    fi
    exit 0
fi
