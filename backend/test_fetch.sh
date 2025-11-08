#!/bin/bash
#
# test_fetch.sh - Crypto Portfolio Data Fetching Test Script
#
# Tests API endpoints and database data integrity
# Usage: ./test_fetch.sh
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
DB_CONTAINER="${DB_CONTAINER:-crypto-portfolio-db}"
DB_USER="${DB_USER:-crypto}"
DB_PASS="${DB_PASS:-password}"
DB_NAME="${DB_NAME:-portfolio}"

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

# Check docker
if ! command -v docker &> /dev/null; then
    print_fail "docker not found in PATH"
    exit 1
fi
print_pass "docker is installed"

# Check containers are running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    print_fail "Database container '$DB_CONTAINER' not running"
    exit 1
fi
print_pass "Database container is running"

if ! docker ps | grep -q "crypto-portfolio-api"; then
    print_fail "API container 'crypto-portfolio-api' not running"
    exit 1
fi
print_pass "API container is running"

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

# ==================== API Endpoint Tests ====================

print_header "API Endpoint Tests"

# Test health endpoint
HEALTH_RESPONSE=$(curl -sf "$API_URL/api/v1/health" || echo "")
if [ -z "$HEALTH_RESPONSE" ]; then
    print_fail "Health endpoint returned empty response"
elif echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    print_pass "Health endpoint: status healthy"
else
    print_fail "Health endpoint: status not healthy"
fi

# Test root endpoint
ROOT_RESPONSE=$(curl -sf "$API_URL/" || echo "")
if echo "$ROOT_RESPONSE" | grep -q "Crypto Portfolio"; then
    print_pass "Root endpoint responding"
else
    print_fail "Root endpoint not responding correctly"
fi

# Test assets coverage endpoint
ASSETS_RESPONSE=$(curl -sf "$API_URL/api/v1/assets" || echo "")
if [ -z "$ASSETS_RESPONSE" ]; then
    print_fail "Assets coverage endpoint failed"
elif echo "$ASSETS_RESPONSE" | grep -q "assets"; then
    print_pass "Assets coverage endpoint responding"
else
    print_fail "Assets coverage endpoint returned unexpected data"
fi

# Test OHLCV endpoint (BTC)
OHLCV_RESPONSE=$(curl -sf "$API_URL/api/v1/ohlcv/BTC?limit=5" || echo "")
if [ -z "$OHLCV_RESPONSE" ]; then
    print_fail "OHLCV endpoint (BTC) failed"
elif echo "$OHLCV_RESPONSE" | grep -q "timestamp"; then
    print_pass "OHLCV endpoint (BTC) responding"
else
    print_fail "OHLCV endpoint (BTC) returned unexpected data"
fi

# Test futures coverage endpoint
FUTURES_ASSETS_RESPONSE=$(curl -sf "$API_URL/api/v1/futures/assets" || echo "")
if [ -z "$FUTURES_ASSETS_RESPONSE" ]; then
    print_fail "Futures assets coverage endpoint failed"
elif echo "$FUTURES_ASSETS_RESPONSE" | grep -q "funding_rate_count"; then
    print_pass "Futures assets coverage endpoint responding"
else
    print_fail "Futures assets coverage endpoint returned unexpected data"
fi

# Test futures funding rates endpoint (ETH)
FUNDING_RESPONSE=$(curl -sf "$API_URL/api/v1/futures/funding-rates/ETH?limit=3" || echo "")
if [ -z "$FUNDING_RESPONSE" ]; then
    print_fail "Funding rates endpoint (ETH) failed"
elif echo "$FUNDING_RESPONSE" | grep -q "funding_rate"; then
    print_pass "Funding rates endpoint (ETH) responding"
else
    print_fail "Funding rates endpoint (ETH) returned unexpected data"
fi

# Test lending coverage endpoint
LENDING_ASSETS_RESPONSE=$(curl -sf "$API_URL/api/v1/lending/assets" || echo "")
if [ -z "$LENDING_ASSETS_RESPONSE" ]; then
    print_fail "Lending assets coverage endpoint failed"
elif echo "$LENDING_ASSETS_RESPONSE" | grep -q "total_events"; then
    print_pass "Lending assets coverage endpoint responding"
else
    print_fail "Lending assets coverage endpoint returned unexpected data"
fi

# Test lending endpoint (WETH)
LENDING_RESPONSE=$(curl -sf "$API_URL/api/v1/lending/WETH?limit=2" || echo "")
if [ -z "$LENDING_RESPONSE" ]; then
    print_fail "Lending endpoint (WETH) failed"
elif echo "$LENDING_RESPONSE" | grep -q "supply_apy_percent"; then
    print_pass "Lending endpoint (WETH) responding"
else
    print_fail "Lending endpoint (WETH) returned unexpected data"
fi

# Test lending symbol mapping (BTC -> WBTC)
LENDING_BTC_RESPONSE=$(curl -sf "$API_URL/api/v1/lending/BTC?limit=2" || echo "")
if [ -z "$LENDING_BTC_RESPONSE" ]; then
    print_fail "Lending symbol mapping (BTC→WBTC) failed"
elif echo "$LENDING_BTC_RESPONSE" | grep -q "WBTC"; then
    print_pass "Lending symbol mapping (BTC→WBTC) working"
else
    print_fail "Lending symbol mapping (BTC→WBTC) not working"
fi

# Test error handling (404 for invalid asset)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/v1/ohlcv/INVALID_ASSET?limit=1")
if [ "$HTTP_CODE" = "404" ]; then
    print_pass "Error handling: 404 for invalid asset"
else
    print_fail "Error handling: expected 404, got $HTTP_CODE"
fi

# ==================== Database Checks ====================

print_header "Database Schema Checks"

# Helper function for psql queries
run_query() {
    local result
    result=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "$1" 2>&1)
    if [ $? -ne 0 ]; then
        echo "[QUERY ERROR]" >&2
        return 1
    fi
    echo "$result"
}

# Check all tables exist
EXPECTED_TABLES=("spot_ohlcv" "backfill_state" "futures_funding_rates" "futures_mark_price_klines" "futures_index_price_klines" "futures_open_interest" "futures_backfill_state" "lendings" "lending_backfill_state")
TABLE_COUNT=$(run_query "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND tablename IN ('spot_ohlcv', 'backfill_state', 'futures_funding_rates', 'futures_mark_price_klines', 'futures_index_price_klines', 'futures_open_interest', 'futures_backfill_state', 'lendings', 'lending_backfill_state');")

if [ "$TABLE_COUNT" = "9" ]; then
    print_pass "All 9 expected tables exist"
else
    print_fail "Expected 9 tables, found $TABLE_COUNT"
fi

# ==================== Data Range Verification ====================

print_header "Data Range & Coverage Summary"

echo ""
echo "Spot OHLCV Data:"
echo "----------------"
run_query "
SELECT
    asset,
    COUNT(*) as count,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest
FROM spot_ohlcv
GROUP BY asset
ORDER BY asset
" | while IFS='|' read -r asset count earliest latest; do
    echo "  $asset: $count records | $earliest → $latest"
done

echo ""
echo "Futures Funding Rates (first 3 assets):"
echo "----------------------------------------"
run_query "
SELECT
    asset,
    COUNT(*) as count,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest
FROM futures_funding_rates
GROUP BY asset
ORDER BY asset
LIMIT 3
" | while IFS='|' read -r asset count earliest latest; do
    echo "  $asset: $count records | $earliest → $latest"
done

echo ""
echo "Futures Mark Price Klines (first 3 assets):"
echo "--------------------------------------------"
run_query "
SELECT
    asset,
    COUNT(*) as count,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest
FROM futures_mark_price_klines
GROUP BY asset
ORDER BY asset
LIMIT 3
" | while IFS='|' read -r asset count earliest latest; do
    echo "  $asset: $count records | $earliest → $latest"
done

echo ""
echo "Lending Data:"
echo "-------------"
run_query "
SELECT
    asset,
    COUNT(*) as count,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest
FROM lendings
GROUP BY asset
ORDER BY asset
" | while IFS='|' read -r asset count earliest latest; do
    echo "  $asset: $count records | $earliest → $latest"
done

# ==================== Data Recency Check ====================

print_header "Data Recency Checks"

# Check spot data recency (using SQL for portability)
SPOT_RECENT_COUNT=$(run_query "SELECT COUNT(*) FROM spot_ohlcv WHERE timestamp >= NOW() - INTERVAL '48 hours';")
if [ -n "$SPOT_RECENT_COUNT" ] && [ "$SPOT_RECENT_COUNT" -gt 0 ]; then
    print_pass "Spot OHLCV data is recent (within 48 hours)"
else
    SPOT_LATEST=$(run_query "SELECT MAX(timestamp) FROM spot_ohlcv;")
    if [ -n "$SPOT_LATEST" ]; then
        print_warn "Spot OHLCV latest: $SPOT_LATEST (may be stale)"
    else
        print_fail "No spot OHLCV data found"
    fi
fi

# Check lending data recency
LENDING_RECENT_COUNT=$(run_query "SELECT COUNT(*) FROM lendings WHERE timestamp >= NOW() - INTERVAL '48 hours';")
if [ -n "$LENDING_RECENT_COUNT" ] && [ "$LENDING_RECENT_COUNT" -gt 0 ]; then
    print_pass "Lending data is recent (within 48 hours)"
else
    LENDING_LATEST=$(run_query "SELECT MAX(timestamp) FROM lendings;")
    if [ -n "$LENDING_LATEST" ]; then
        print_warn "Lending data latest: $LENDING_LATEST (may be stale)"
    else
        print_fail "No lending data found"
    fi
fi

# Check backfill state
SPOT_BACKFILL_COMPLETED=$(run_query "SELECT COUNT(*) FROM backfill_state WHERE completed=true;")
FUTURES_BACKFILL_COMPLETED=$(run_query "SELECT COUNT(*) FROM futures_backfill_state WHERE completed=true;")

if [ "$SPOT_BACKFILL_COMPLETED" -gt 0 ]; then
    print_pass "Spot backfill: $SPOT_BACKFILL_COMPLETED asset(s) completed"
else
    print_warn "No spot backfills marked as completed"
fi

if [ "$FUTURES_BACKFILL_COMPLETED" -gt 0 ]; then
    print_pass "Futures backfill: $FUTURES_BACKFILL_COMPLETED metric(s) completed"
else
    print_warn "No futures backfills marked as completed"
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
