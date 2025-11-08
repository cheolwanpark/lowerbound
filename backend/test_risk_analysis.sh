#!/bin/bash
#
# test_risk_analysis.sh - Risk Analysis Endpoint Test Script
#
# Tests the /analysis/risk-profile endpoint with various portfolio configurations
# Usage: ./test_risk_analysis.sh
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"

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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
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
    print_info "jq is available - will parse JSON responses"
else
    print_warn "jq not found - JSON parsing will be limited"
fi

# ==================== Precondition Checks ====================

print_header "Precondition Checks"

# Wait for API health endpoint
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

# ==================== Test 1: Spot-only Portfolio ====================

print_header "Test 1: Spot-only Portfolio"

SPOT_ONLY_REQUEST='{
  "positions": [
    {
      "asset": "BTC",
      "quantity": 2.0,
      "position_type": "spot",
      "entry_price": 45000.0,
      "leverage": 1.0
    },
    {
      "asset": "ETH",
      "quantity": 10.0,
      "position_type": "spot",
      "entry_price": 2500.0,
      "leverage": 1.0
    }
  ],
  "lookback_days": 30
}'

echo "Sending request for spot-only portfolio..."
RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/analysis/risk-profile" \
    -H "Content-Type: application/json" \
    -d "$SPOT_ONLY_REQUEST" 2>&1)

if [ $? -ne 0 ]; then
    print_fail "Spot-only portfolio request failed"
    echo "Response: $RESPONSE"
else
    if echo "$RESPONSE" | grep -q "current_portfolio_value"; then
        print_pass "Spot-only portfolio: Response received"

        if [ "$HAS_JQ" = true ]; then
            PORTFOLIO_VALUE=$(echo "$RESPONSE" | jq -r '.current_portfolio_value')
            VAR_95=$(echo "$RESPONSE" | jq -r '.risk_metrics.var_95_1day')
            SHARPE=$(echo "$RESPONSE" | jq -r '.risk_metrics.sharpe_ratio')
            LENDING_METRICS=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics')

            print_info "Portfolio value: \$$PORTFOLIO_VALUE"
            print_info "VaR 95% (1-day): \$$VAR_95"
            print_info "Sharpe ratio: $SHARPE"

            if [ "$LENDING_METRICS" = "null" ]; then
                print_pass "Lending metrics correctly null for spot-only portfolio"
            else
                print_fail "Lending metrics should be null for spot-only portfolio"
            fi
        fi
    else
        print_fail "Spot-only portfolio: Invalid response"
        echo "Response: $RESPONSE"
    fi
fi

# ==================== Test 2: Mixed Portfolio (Spot + Futures) ====================

print_header "Test 2: Mixed Portfolio (Spot + Futures)"

MIXED_REQUEST='{
  "positions": [
    {
      "asset": "BTC",
      "quantity": 1.0,
      "position_type": "spot",
      "entry_price": 50000.0,
      "leverage": 1.0
    },
    {
      "asset": "ETH",
      "quantity": 5.0,
      "position_type": "futures_long",
      "entry_price": 2800.0,
      "leverage": 3.0
    },
    {
      "asset": "BTC",
      "quantity": 0.5,
      "position_type": "futures_short",
      "entry_price": 51000.0,
      "leverage": 2.0
    }
  ],
  "lookback_days": 30
}'

echo "Sending request for mixed portfolio..."
RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/analysis/risk-profile" \
    -H "Content-Type: application/json" \
    -d "$MIXED_REQUEST" 2>&1)

if [ $? -ne 0 ]; then
    print_fail "Mixed portfolio request failed"
    echo "Response: $RESPONSE"
else
    if echo "$RESPONSE" | grep -q "current_portfolio_value"; then
        print_pass "Mixed portfolio: Response received"

        if [ "$HAS_JQ" = true ]; then
            PORTFOLIO_VALUE=$(echo "$RESPONSE" | jq -r '.current_portfolio_value')
            DELTA=$(echo "$RESPONSE" | jq -r '.risk_metrics.delta_exposure')
            VOLATILITY=$(echo "$RESPONSE" | jq -r '.risk_metrics.portfolio_volatility_annual')

            print_info "Portfolio value: \$$PORTFOLIO_VALUE"
            print_info "Delta exposure: $DELTA"
            print_info "Annual volatility: $VOLATILITY"
        fi
    else
        print_fail "Mixed portfolio: Invalid response"
        echo "Response: $RESPONSE"
    fi
fi

# ==================== Test 3: Lending-only Portfolio ====================

print_header "Test 3: Lending-only Portfolio"

LENDING_ONLY_REQUEST='{
  "positions": [
    {
      "asset": "WETH",
      "quantity": 10.0,
      "position_type": "lending_supply",
      "entry_timestamp": "2024-01-01T00:00:00Z",
      "leverage": 1.0
    },
    {
      "asset": "USDC",
      "quantity": 5000.0,
      "position_type": "lending_borrow",
      "entry_timestamp": "2024-01-01T00:00:00Z",
      "borrow_type": "variable",
      "leverage": 1.0
    }
  ],
  "lookback_days": 30
}'

echo "Sending request for lending-only portfolio..."
RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/analysis/risk-profile" \
    -H "Content-Type: application/json" \
    -d "$LENDING_ONLY_REQUEST" 2>&1)

if [ $? -ne 0 ]; then
    print_fail "Lending-only portfolio request failed"
    echo "Response: $RESPONSE"
else
    if echo "$RESPONSE" | grep -q "current_portfolio_value"; then
        print_pass "Lending-only portfolio: Response received"

        if [ "$HAS_JQ" = true ]; then
            PORTFOLIO_VALUE=$(echo "$RESPONSE" | jq -r '.current_portfolio_value')
            LENDING_METRICS=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics')

            print_info "Portfolio value: \$$PORTFOLIO_VALUE"

            if [ "$LENDING_METRICS" != "null" ]; then
                print_pass "Lending metrics present for lending portfolio"

                LTV=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics.ltv_ratio')
                HEALTH_FACTOR=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics.health_factor')
                NET_APY=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics.net_apy')

                print_info "LTV: $LTV"
                print_info "Health Factor: $HEALTH_FACTOR"
                print_info "Net APY: $NET_APY%"
            else
                print_fail "Lending metrics missing for lending portfolio"
            fi
        fi
    else
        print_fail "Lending-only portfolio: Invalid response"
        echo "Response: $RESPONSE"
    fi
fi

# ==================== Test 4: Combined Portfolio (Spot + Futures + Lending) ====================

print_header "Test 4: Combined Portfolio (Spot + Futures + Lending)"

COMBINED_REQUEST='{
  "positions": [
    {
      "asset": "BTC",
      "quantity": 1.5,
      "position_type": "spot",
      "entry_price": 48000.0,
      "leverage": 1.0
    },
    {
      "asset": "ETH",
      "quantity": 8.0,
      "position_type": "futures_long",
      "entry_price": 2700.0,
      "leverage": 2.0
    },
    {
      "asset": "WETH",
      "quantity": 15.0,
      "position_type": "lending_supply",
      "entry_timestamp": "2024-01-15T00:00:00Z",
      "leverage": 1.0
    },
    {
      "asset": "USDC",
      "quantity": 8000.0,
      "position_type": "lending_borrow",
      "entry_timestamp": "2024-01-15T00:00:00Z",
      "borrow_type": "variable",
      "leverage": 1.0
    }
  ],
  "lookback_days": 30
}'

echo "Sending request for combined portfolio..."
RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/analysis/risk-profile" \
    -H "Content-Type: application/json" \
    -d "$COMBINED_REQUEST" 2>&1)

if [ $? -ne 0 ]; then
    print_fail "Combined portfolio request failed"
    echo "Response: $RESPONSE"
else
    if echo "$RESPONSE" | grep -q "current_portfolio_value"; then
        print_pass "Combined portfolio: Response received"

        if [ "$HAS_JQ" = true ]; then
            PORTFOLIO_VALUE=$(echo "$RESPONSE" | jq -r '.current_portfolio_value')
            LENDING_METRICS=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics')
            SCENARIOS_COUNT=$(echo "$RESPONSE" | jq -r '.scenarios | length')

            print_info "Portfolio value: \$$PORTFOLIO_VALUE"
            print_info "Scenarios analyzed: $SCENARIOS_COUNT"

            if [ "$LENDING_METRICS" != "null" ]; then
                print_pass "Lending metrics present in combined portfolio"

                LTV=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics.ltv_ratio')
                HEALTH_FACTOR=$(echo "$RESPONSE" | jq -r '.risk_metrics.lending_metrics.health_factor')

                print_info "LTV: $LTV"
                print_info "Health Factor: $HEALTH_FACTOR"
            else
                print_fail "Lending metrics missing in combined portfolio"
            fi
        fi
    else
        print_fail "Combined portfolio: Invalid response"
        echo "Response: $RESPONSE"
    fi
fi

# ==================== Test 5: Error Handling - Invalid Position Type ====================

print_header "Test 5: Error Handling - Invalid Position Type"

INVALID_REQUEST='{
  "positions": [
    {
      "asset": "BTC",
      "quantity": 1.0,
      "position_type": "invalid_type",
      "entry_price": 50000.0,
      "leverage": 1.0
    }
  ],
  "lookback_days": 30
}'

echo "Sending request with invalid position type..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/api/v1/analysis/risk-profile" \
    -H "Content-Type: application/json" \
    -d "$INVALID_REQUEST")

if [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "400" ]; then
    print_pass "Invalid position type rejected with HTTP $HTTP_CODE"
else
    print_fail "Expected HTTP 422/400, got $HTTP_CODE"
fi

# ==================== Test 6: Error Handling - Missing Required Fields ====================

print_header "Test 6: Error Handling - Missing Required Fields"

MISSING_FIELDS_REQUEST='{
  "positions": [
    {
      "asset": "WETH",
      "quantity": 10.0,
      "position_type": "lending_supply",
      "leverage": 1.0
    }
  ],
  "lookback_days": 30
}'

echo "Sending lending position without entry_timestamp..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/api/v1/analysis/risk-profile" \
    -H "Content-Type: application/json" \
    -d "$MISSING_FIELDS_REQUEST")

if [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "400" ]; then
    print_pass "Missing entry_timestamp rejected with HTTP $HTTP_CODE"
else
    print_fail "Expected HTTP 422/400, got $HTTP_CODE"
fi

# ==================== Test 7: Sensitivity Analysis ====================

print_header "Test 7: Sensitivity Analysis Validation"

SIMPLE_REQUEST='{
  "positions": [
    {
      "asset": "BTC",
      "quantity": 1.0,
      "position_type": "spot",
      "entry_price": 50000.0,
      "leverage": 1.0
    }
  ],
  "lookback_days": 30
}'

echo "Sending request to check sensitivity analysis..."
RESPONSE=$(curl -sf -X POST "$API_URL/api/v1/analysis/risk-profile" \
    -H "Content-Type: application/json" \
    -d "$SIMPLE_REQUEST" 2>&1)

if [ $? -ne 0 ]; then
    print_fail "Sensitivity analysis test failed"
else
    if echo "$RESPONSE" | grep -q "sensitivity_analysis"; then
        print_pass "Sensitivity analysis present in response"

        if [ "$HAS_JQ" = true ]; then
            SENS_COUNT=$(echo "$RESPONSE" | jq -r '.sensitivity_analysis | length')
            print_info "Sensitivity table entries: $SENS_COUNT"

            if [ "$SENS_COUNT" -gt 0 ]; then
                print_pass "Sensitivity table contains $SENS_COUNT entries"
            else
                print_fail "Sensitivity table is empty"
            fi
        fi
    else
        print_fail "Sensitivity analysis missing from response"
    fi
fi

# ==================== Test 8: Scenario Analysis ====================

print_header "Test 8: Scenario Analysis Validation"

echo "Checking scenario analysis in previous response..."
if echo "$RESPONSE" | grep -q "scenarios"; then
    print_pass "Scenario analysis present in response"

    if [ "$HAS_JQ" = true ]; then
        SCENARIOS=$(echo "$RESPONSE" | jq -r '.scenarios | length')
        print_info "Scenarios analyzed: $SCENARIOS"

        if [ "$SCENARIOS" -gt 0 ]; then
            print_pass "Scenarios contain $SCENARIOS entries"

            # Check if scenarios have expected fields
            FIRST_SCENARIO_NAME=$(echo "$RESPONSE" | jq -r '.scenarios[0].name')
            print_info "First scenario: $FIRST_SCENARIO_NAME"
        else
            print_fail "Scenarios list is empty"
        fi
    fi
else
    print_fail "Scenario analysis missing from response"
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
