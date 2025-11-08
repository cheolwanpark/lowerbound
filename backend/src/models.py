"""Pydantic models for API requests/responses and data validation."""

from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator


class OHLCVCandle(BaseModel):
    """OHLCV candlestick data."""

    timestamp: datetime = Field(description="Candle open time (UTC)")
    open: Decimal = Field(description="Open price")
    high: Decimal = Field(description="High price")
    low: Decimal = Field(description="Low price")
    close: Decimal = Field(description="Close price")
    volume: Decimal = Field(description="Trading volume (base asset)")
    filled: bool = Field(default=False, description="Whether this candle was forward-filled")


class OHLCVResponse(BaseModel):
    """Response for OHLCV data queries."""

    asset: str = Field(description="Asset symbol (e.g., BTC)")
    interval: str = Field(description="Candle interval (e.g., 12h)")
    data: list[OHLCVCandle] = Field(description="List of OHLCV candles")
    count: int = Field(description="Number of candles returned")


class BinanceKline(BaseModel):
    """Binance kline (candlestick) response validation."""

    open_time: int = Field(description="Kline open time (milliseconds)")
    open: str = Field(description="Open price")
    high: str = Field(description="High price")
    low: str = Field(description="Low price")
    close: str = Field(description="Close price")
    volume: str = Field(description="Volume")
    close_time: int = Field(description="Kline close time (milliseconds)")
    quote_asset_volume: str = Field(description="Quote asset volume")
    number_of_trades: int = Field(description="Number of trades")
    taker_buy_base_asset_volume: str = Field(description="Taker buy base asset volume")
    taker_buy_quote_asset_volume: str = Field(description="Taker buy quote asset volume")
    ignore: str = Field(description="Unused field")

    @classmethod
    def from_list(cls, data: list) -> "BinanceKline":
        """Parse Binance API array response into typed model."""
        if len(data) < 12:
            raise ValueError(f"Invalid kline data: expected 12 fields, got {len(data)}")

        return cls(
            open_time=data[0],
            open=data[1],
            high=data[2],
            low=data[3],
            close=data[4],
            volume=data[5],
            close_time=data[6],
            quote_asset_volume=data[7],
            number_of_trades=data[8],
            taker_buy_base_asset_volume=data[9],
            taker_buy_quote_asset_volume=data[10],
            ignore=data[11],
        )

    def to_ohlcv(self) -> dict:
        """Convert to OHLCV dictionary for database insertion."""
        return {
            "timestamp": datetime.fromtimestamp(self.open_time / 1000, tz=timezone.utc),
            "open": Decimal(self.open),
            "high": Decimal(self.high),
            "low": Decimal(self.low),
            "close": Decimal(self.close),
            "volume": Decimal(self.volume),
        }


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status (healthy/unhealthy)")
    database: str = Field(description="Database connection status")
    scheduler: str | None = Field(default=None, description="Scheduler status (if applicable)")
    timestamp: datetime = Field(description="Health check timestamp")


class FetchTriggerRequest(BaseModel):
    """Manual fetch trigger request."""

    assets: list[str] | None = Field(
        default=None, description="List of assets to fetch (None = all tracked assets)"
    )
    start_date: datetime | None = Field(default=None, description="Start date for fetching")
    end_date: datetime | None = Field(default=None, description="End date for fetching")

    @field_validator("assets")
    @classmethod
    def normalize_assets(cls, v: list[str] | None) -> list[str] | None:
        """Normalize asset symbols to uppercase."""
        if v is None:
            return None
        return [asset.strip().upper() for asset in v]


class FetchTriggerResponse(BaseModel):
    """Manual fetch trigger response."""

    job_id: str = Field(description="Job identifier for tracking")
    message: str = Field(description="Status message")
    assets: list[str] = Field(description="Assets to be fetched")


class AssetCoverage(BaseModel):
    """Data coverage information for an asset."""

    asset: str = Field(description="Asset symbol")
    earliest_timestamp: datetime | None = Field(description="Earliest available data point")
    latest_timestamp: datetime | None = Field(description="Latest available data point")
    total_candles: int = Field(description="Total number of candles stored")
    backfill_completed: bool = Field(description="Whether initial backfill is completed")


class AssetCoverageResponse(BaseModel):
    """Response for asset coverage query."""

    assets: list[AssetCoverage] = Field(description="Coverage info for all tracked assets")


# ==================== Futures Models ====================


class BinanceFundingRate(BaseModel):
    """Binance funding rate response validation."""

    model_config = {"populate_by_name": True}

    symbol: str = Field(description="Trading pair symbol (e.g., BTCUSDT)")
    funding_rate: str = Field(alias="fundingRate", description="Funding rate")
    funding_time: int = Field(alias="fundingTime", description="Funding time (milliseconds)")
    mark_price: str | None = Field(default=None, alias="markPrice", description="Mark price at funding time")

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": datetime.fromtimestamp(self.funding_time / 1000, tz=timezone.utc),
            "funding_rate": Decimal(self.funding_rate),
            "mark_price": Decimal(self.mark_price) if self.mark_price else None,
        }


class BinanceMarkPriceKline(BaseModel):
    """Binance mark price kline response validation."""

    open_time: int = Field(description="Kline open time (milliseconds)")
    open: str = Field(description="Open mark price")
    high: str = Field(description="High mark price")
    low: str = Field(description="Low mark price")
    close: str = Field(description="Close mark price")
    # Binance mark price klines return empty strings for fields 5-11
    ignore_5: str = Field(default="")
    close_time: int = Field(description="Kline close time (milliseconds)")
    ignore_7: str = Field(default="")
    ignore_8: str = Field(default="")
    ignore_9: str = Field(default="")
    ignore_10: str = Field(default="")
    ignore_11: str = Field(default="")

    @classmethod
    def from_list(cls, data: list) -> "BinanceMarkPriceKline":
        """Parse Binance API array response into typed model."""
        if len(data) < 12:
            raise ValueError(f"Invalid mark price kline data: expected 12 fields, got {len(data)}")

        return cls(
            open_time=data[0],
            open=data[1],
            high=data[2],
            low=data[3],
            close=data[4],
            ignore_5=str(data[5]),
            close_time=data[6],
            ignore_7=str(data[7]),
            ignore_8=str(data[8]),
            ignore_9=str(data[9]),
            ignore_10=str(data[10]),
            ignore_11=str(data[11]),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": datetime.fromtimestamp(self.open_time / 1000, tz=timezone.utc),
            "open": Decimal(self.open),
            "high": Decimal(self.high),
            "low": Decimal(self.low),
            "close": Decimal(self.close),
        }


class BinanceIndexPriceKline(BaseModel):
    """Binance index price kline response validation."""

    open_time: int = Field(description="Kline open time (milliseconds)")
    open: str = Field(description="Open index price")
    high: str = Field(description="High index price")
    low: str = Field(description="Low index price")
    close: str = Field(description="Close index price")
    ignore_5: str = Field(default="")
    close_time: int = Field(description="Kline close time (milliseconds)")
    ignore_7: str = Field(default="")
    ignore_8: str = Field(default="")
    ignore_9: str = Field(default="")
    ignore_10: str = Field(default="")
    ignore_11: str = Field(default="")

    @classmethod
    def from_list(cls, data: list) -> "BinanceIndexPriceKline":
        """Parse Binance API array response into typed model."""
        if len(data) < 12:
            raise ValueError(f"Invalid index price kline data: expected 12 fields, got {len(data)}")

        return cls(
            open_time=data[0],
            open=data[1],
            high=data[2],
            low=data[3],
            close=data[4],
            ignore_5=str(data[5]),
            close_time=data[6],
            ignore_7=str(data[7]),
            ignore_8=str(data[8]),
            ignore_9=str(data[9]),
            ignore_10=str(data[10]),
            ignore_11=str(data[11]),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": datetime.fromtimestamp(self.open_time / 1000, tz=timezone.utc),
            "open": Decimal(self.open),
            "high": Decimal(self.high),
            "low": Decimal(self.low),
            "close": Decimal(self.close),
        }


class BinanceOpenInterest(BaseModel):
    """Binance open interest response validation."""

    model_config = {"populate_by_name": True}

    symbol: str = Field(description="Trading pair symbol")
    sum_open_interest: str = Field(alias="sumOpenInterest", description="Total open interest")
    sum_open_interest_value: str = Field(alias="sumOpenInterestValue", description="Total open interest value in USD")
    timestamp: int = Field(description="Data timestamp (milliseconds)")

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp / 1000, tz=timezone.utc),
            "open_interest": Decimal(self.sum_open_interest),
        }


# ==================== Futures API Response Models ====================


class FundingRateDataPoint(BaseModel):
    """Funding rate data point for API responses."""

    timestamp: datetime = Field(description="Funding time (UTC)")
    funding_rate: Decimal = Field(description="Funding rate")
    mark_price: Decimal | None = Field(default=None, description="Mark price at funding time")


class FundingRateResponse(BaseModel):
    """Response for funding rate queries."""

    asset: str = Field(description="Asset symbol (e.g., BTC)")
    interval: str = Field(description="Interval (e.g., 8h)")
    data: list[FundingRateDataPoint] = Field(description="List of funding rate data points")
    count: int = Field(description="Number of data points returned")


class MarkPriceCandle(BaseModel):
    """Mark price OHLCV candle for API responses."""

    timestamp: datetime = Field(description="Candle open time (UTC)")
    open: Decimal = Field(description="Open mark price")
    high: Decimal = Field(description="High mark price")
    low: Decimal = Field(description="Low mark price")
    close: Decimal = Field(description="Close mark price")


class MarkPriceResponse(BaseModel):
    """Response for mark price kline queries."""

    asset: str = Field(description="Asset symbol (e.g., BTC)")
    interval: str = Field(description="Candle interval (e.g., 8h)")
    data: list[MarkPriceCandle] = Field(description="List of mark price candles")
    count: int = Field(description="Number of candles returned")


class IndexPriceCandle(BaseModel):
    """Index price OHLCV candle for API responses."""

    timestamp: datetime = Field(description="Candle open time (UTC)")
    open: Decimal = Field(description="Open index price")
    high: Decimal = Field(description="High index price")
    low: Decimal = Field(description="Low index price")
    close: Decimal = Field(description="Close index price")


class IndexPriceResponse(BaseModel):
    """Response for index price kline queries."""

    asset: str = Field(description="Asset symbol (e.g., BTC)")
    interval: str = Field(description="Candle interval (e.g., 8h)")
    data: list[IndexPriceCandle] = Field(description="List of index price candles")
    count: int = Field(description="Number of candles returned")


class OpenInterestDataPoint(BaseModel):
    """Open interest data point for API responses."""

    timestamp: datetime = Field(description="Data timestamp (UTC)")
    open_interest: Decimal = Field(description="Total open interest")


class OpenInterestResponse(BaseModel):
    """Response for open interest queries."""

    asset: str = Field(description="Asset symbol (e.g., BTC)")
    data: list[OpenInterestDataPoint] = Field(description="List of open interest data points")
    count: int = Field(description="Number of data points returned")


class FuturesAssetCoverage(BaseModel):
    """Futures data coverage information for an asset."""

    asset: str = Field(description="Asset symbol")
    funding_rate_count: int = Field(description="Total funding rate data points")
    funding_rate_earliest: datetime | None = Field(description="Earliest funding rate timestamp")
    funding_rate_latest: datetime | None = Field(description="Latest funding rate timestamp")
    mark_klines_count: int = Field(description="Total mark price klines")
    mark_klines_earliest: datetime | None = Field(description="Earliest mark kline timestamp")
    mark_klines_latest: datetime | None = Field(description="Latest mark kline timestamp")
    index_klines_count: int = Field(description="Total index price klines")
    index_klines_earliest: datetime | None = Field(description="Earliest index kline timestamp")
    index_klines_latest: datetime | None = Field(description="Latest index kline timestamp")
    open_interest_count: int = Field(description="Total open interest data points")
    open_interest_earliest: datetime | None = Field(description="Earliest open interest timestamp")
    open_interest_latest: datetime | None = Field(description="Latest open interest timestamp")


class FuturesAssetCoverageResponse(BaseModel):
    """Response for futures asset coverage query."""

    assets: list[FuturesAssetCoverage] = Field(description="Coverage info for all tracked futures assets")


# ==================== Lending (Dune Analytics) Models ====================


def decimal_to_ray(value: Decimal) -> str:
    """
    Convert decimal rate to RAY format (10^27 precision).

    Dune returns rates as decimals (e.g., 0.052 = 5.2%).
    We store them in RAY format for precision.

    Args:
        value: Decimal rate (e.g., 0.052 for 5.2% APY)

    Returns:
        String representation of RAY value (e.g., "52000000000000000000000000")
    """
    ray_value = value * Decimal(10**27)
    return str(int(ray_value))


class DuneLendingData(BaseModel):
    """
    Raw lending data from Dune Analytics query.

    Query ID: 3328916
    Returns aggregated lending market data with rates and indices.
    """

    model_config = {"populate_by_name": True}

    dt: datetime = Field(description="Date/time of the data point")
    symbol: str = Field(description="Asset symbol (e.g., DAI, USDC)")
    reserve: str = Field(description="Reserve contract address (Ethereum address)")
    avg_stableBorrowRate: Decimal = Field(description="Average stable borrow rate (decimal, e.g., 0.052 = 5.2%)")
    avg_variableBorrowRate: Decimal = Field(description="Average variable borrow rate (decimal)")
    avg_supplyRate: Decimal = Field(description="Average supply rate (decimal)")
    avg_liquidityIndex: Decimal = Field(description="Average liquidity index")
    avg_variableBorrowIndex: Decimal = Field(description="Average variable borrow index")

    def to_dict(self) -> dict:
        """
        Convert to dictionary for database insertion.

        Transforms Dune decimal rates to RAY format (10^27 precision).
        Ensures timestamp is timezone-aware (UTC).

        Returns:
            Dict with all lending data fields ready for database
        """
        # Ensure timestamp is timezone-aware
        timestamp = self.dt
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return {
            "timestamp": timestamp,
            "asset": self.symbol,
            "reserve_address": self.reserve,
            "supply_rate_ray": decimal_to_ray(self.avg_supplyRate),
            "variable_borrow_rate_ray": decimal_to_ray(self.avg_variableBorrowRate),
            "stable_borrow_rate_ray": decimal_to_ray(self.avg_stableBorrowRate),
            "liquidity_index": decimal_to_ray(self.avg_liquidityIndex),
            "variable_borrow_index": decimal_to_ray(self.avg_variableBorrowIndex),
        }


def convert_ray_to_apy(ray_rate: str | Decimal) -> float:
    """
    Convert Aave RAY rate to APY percentage.

    Aave rates are expressed in RAY units (10^27) as APR with per-second compounding.
    Formula: APY = (1 + APR/secondsPerYear)^secondsPerYear - 1

    Args:
        ray_rate: Rate in RAY units (string or Decimal)

    Returns:
        APY as percentage (e.g., 5.23 for 5.23%)
    """
    SECONDS_PER_YEAR = 31536000  # 365.25 days * 24 * 60 * 60

    # Convert RAY to APR decimal
    ray = Decimal(ray_rate)
    apr_decimal = ray / Decimal(10**27)

    # Convert APR to APY with per-second compounding
    # APY = (1 + APR/secondsPerYear)^secondsPerYear - 1
    try:
        # Use float for the power operation (Decimal doesn't support ** with large exponents)
        apr_float = float(apr_decimal)
        apy_decimal = (1 + apr_float / SECONDS_PER_YEAR) ** SECONDS_PER_YEAR - 1
    except OverflowError:
        # For extremely high rates, cap at 1000000% APY
        logger.warning(f"APR rate overflow: {apr_decimal}, capping at 1000000% APY")
        return 1000000.0

    # Convert to percentage
    return apy_decimal * 100


class LendingDataPoint(BaseModel):
    """Lending data point for API responses."""

    timestamp: datetime = Field(description="Data point timestamp (UTC)")
    reserve_address: str = Field(description="Reserve contract address")
    supply_rate_ray: str = Field(description="Supply APR in RAY units (10^27 precision)")
    supply_apy_percent: float = Field(description="Supply APY as percentage (e.g., 5.23 = 5.23%)")
    variable_borrow_rate_ray: str = Field(description="Variable borrow APR in RAY units")
    variable_borrow_apy_percent: float = Field(description="Variable borrow APY as percentage")
    stable_borrow_rate_ray: str = Field(description="Stable borrow APR in RAY units")
    stable_borrow_apy_percent: float = Field(description="Stable borrow APY as percentage")
    liquidity_index: str = Field(description="Liquidity index in RAY units")
    variable_borrow_index: str = Field(description="Variable borrow index in RAY units")


class LendingResponse(BaseModel):
    """Response for lending data queries."""

    asset: str = Field(description="Asset symbol (e.g., WETH, USDC)")
    data: list[LendingDataPoint] = Field(description="List of lending data points")
    count: int = Field(description="Number of data points returned")


class LendingAssetCoverage(BaseModel):
    """Lending data coverage information for an asset."""

    asset: str = Field(description="Asset symbol")
    earliest_timestamp: datetime | None = Field(description="Earliest available data point")
    latest_timestamp: datetime | None = Field(description="Latest available data point")
    total_events: int = Field(description="Total number of events stored")
    backfill_completed: bool = Field(description="Whether initial backfill is completed")


class LendingAssetCoverageResponse(BaseModel):
    """Response for lending asset coverage query."""

    assets: list[LendingAssetCoverage] = Field(description="Coverage info for all tracked lending assets")


# ==================== Risk Profile Analysis Models ====================


class PositionInput(BaseModel):
    """Portfolio position input for risk analysis."""

    asset: str = Field(description="Asset symbol (e.g., BTC, ETH)")
    quantity: float = Field(gt=0, description="Position size (must be positive)")
    position_type: str = Field(
        description="Position type: spot, futures_long, futures_short, lending_supply, lending_borrow"
    )
    entry_price: float = Field(default=0.0, ge=0, description="Entry price in USD (required for spot/futures, ignored for lending)")
    leverage: float = Field(default=1.0, gt=0, le=125, description="Leverage (1-125x, for futures only)")

    # Lending-specific fields
    entry_timestamp: datetime | None = Field(
        default=None,
        description="When lending position opened (required for lending positions)",
    )
    entry_index: str | None = Field(
        default=None,
        description="Liquidity/borrow index at entry (optional - will be looked up if not provided)",
    )
    borrow_type: str | None = Field(
        default=None,
        description="Borrow rate type: 'variable' or 'stable' (required for lending_borrow)",
    )

    @field_validator("asset")
    @classmethod
    def normalize_asset(cls, v: str) -> str:
        """Normalize asset symbol to uppercase."""
        return v.strip().upper()

    @field_validator("position_type")
    @classmethod
    def validate_position_type(cls, v: str) -> str:
        """Validate position type."""
        valid_types = ["spot", "futures_long", "futures_short", "lending_supply", "lending_borrow"]
        if v not in valid_types:
            raise ValueError(f"position_type must be one of {valid_types}")
        return v

    @model_validator(mode="after")
    def validate_lending_fields(self) -> "PositionInput":
        """Validate lending-specific fields are provided."""
        if self.position_type in ["lending_supply", "lending_borrow"]:
            if self.entry_timestamp is None:
                raise ValueError(f"entry_timestamp required for {self.position_type} positions")
            if self.position_type == "lending_borrow" and self.borrow_type is None:
                raise ValueError("borrow_type ('variable' or 'stable') required for lending_borrow positions")
            if self.borrow_type and self.borrow_type not in ["variable", "stable"]:
                raise ValueError("borrow_type must be 'variable' or 'stable'")
        return self


class RiskProfileRequest(BaseModel):
    """Request for portfolio risk profile calculation."""

    positions: list[PositionInput] = Field(
        min_length=1, max_length=20, description="Portfolio positions (1-20 positions)"
    )
    lookback_days: int = Field(
        default=30, ge=7, le=180, description="Historical data lookback period (7-180 days)"
    )


class SensitivityRow(BaseModel):
    """Portfolio sensitivity to price changes."""

    price_change_pct: float = Field(description="Price change percentage (e.g., -30, -25, ..., 30)")
    portfolio_value: float = Field(description="Portfolio value at this price level")
    pnl: float = Field(description="Profit/Loss relative to current value")
    return_pct: float = Field(description="Return percentage")


class LendingMetrics(BaseModel):
    """Account-level lending risk metrics (Aave protocol)."""

    total_supplied_value: float = Field(description="Total value of all supply positions (USD)")
    total_borrowed_value: float = Field(description="Total value of all borrow positions (USD, absolute)")
    net_lending_value: float = Field(description="Net lending value: supplied - borrowed (USD)")

    # Account-level risk metrics
    current_ltv: float = Field(description="Current loan-to-value ratio (0-1, borrowed/supplied)")
    health_factor: float = Field(
        description="Aave health factor: (collateral × liq_threshold) / borrowed. >1 = safe, <1 = liquidation"
    )
    max_safe_borrow: float = Field(
        description="Maximum additional borrowing before hitting max LTV (USD)"
    )

    # Yield metrics
    net_apy: float = Field(description="Net APY: (supply_yield - borrow_cost) / net_value")
    weighted_supply_apy: float = Field(description="Weighted average supply APY across all supply positions")
    weighted_borrow_apy: float = Field(description="Weighted average borrow APY across all borrow positions")

    # Data quality indicators
    data_timestamp: datetime = Field(description="Timestamp of latest lending data used")
    data_age_hours: float = Field(description="Hours since latest data (staleness indicator)")
    data_warning: str | None = Field(
        default=None,
        description="Warning if data is stale (>48h) or other data quality issues",
    )


class RiskMetrics(BaseModel):
    """Comprehensive risk metrics for the portfolio."""

    lookback_days_used: int = Field(description="Actual days of data used for calculations")
    portfolio_variance: float = Field(description="Portfolio variance (daily)")
    portfolio_volatility_annual: float = Field(description="Annualized portfolio volatility")
    var_95_1day: float = Field(description="1-day Value at Risk at 95% confidence (negative = loss)")
    var_99_1day: float = Field(description="1-day Value at Risk at 99% confidence (negative = loss)")
    cvar_95: float = Field(description="Conditional VaR (Expected Shortfall) at 95%")
    sharpe_ratio: float = Field(description="Sharpe ratio (annualized)")
    max_drawdown: float = Field(description="Maximum drawdown (negative decimal, e.g., -0.25 = 25%)")
    delta_exposure: float = Field(description="Total delta exposure (market directional risk)")
    correlation_matrix: dict[str, dict[str, float]] = Field(
        description="Asset correlation matrix"
    )

    # Lending-specific metrics (None if no lending positions in portfolio)
    lending_metrics: LendingMetrics | None = Field(
        default=None,
        description="Lending risk metrics (only present if portfolio contains lending positions)",
    )


class ScenarioResult(BaseModel):
    """Scenario analysis result."""

    name: str = Field(description="Scenario name")
    description: str = Field(description="Scenario description")
    portfolio_value: float = Field(description="Portfolio value under this scenario")
    pnl: float = Field(description="Profit/Loss relative to current value")
    return_pct: float = Field(description="Return percentage")


class RiskProfileResponse(BaseModel):
    """Response for portfolio risk profile calculation."""

    current_portfolio_value: float = Field(description="Current total portfolio value in USD")
    data_availability_warning: str | None = Field(
        default=None,
        description="Warning message if data availability is limited or has gaps",
    )
    sensitivity_analysis: list[SensitivityRow] = Field(
        description="Portfolio value sensitivity to price changes (-30% to +30%)"
    )
    risk_metrics: RiskMetrics = Field(description="Comprehensive risk metrics")
    scenarios: list[ScenarioResult] = Field(
        description="Predefined scenario analysis results (bull/bear markets, etc.)"
    )


# ==================== Aggregated Statistics Models ====================


class AggregatedSpotStats(BaseModel):
    """Aggregated spot market statistics."""

    current_price: float = Field(description="Current spot price")
    min_price: float = Field(description="Minimum price over period")
    max_price: float = Field(description="Maximum price over period")
    mean_price: float = Field(description="Mean price over period")
    total_return_pct: float = Field(description="Total return percentage over period")
    volatility_pct: float = Field(description="Annualized volatility percentage")
    sharpe_ratio: float = Field(description="Annualized Sharpe ratio")
    max_drawdown_pct: float = Field(description="Maximum drawdown percentage (negative)")


class AggregatedFuturesStats(BaseModel):
    """Aggregated futures market statistics."""

    current_funding_rate_pct: float = Field(description="Current 8h funding rate percentage")
    mean_funding_rate_pct: float = Field(description="Mean funding rate over period")
    cumulative_funding_cost_pct: float = Field(
        description="Cumulative funding cost over period (sum of all rates)"
    )
    current_basis_premium_pct: float | None = Field(
        default=None, description="Current basis premium (mark - spot) / spot * 100"
    )
    mean_basis_premium_pct: float | None = Field(
        default=None, description="Mean basis premium over period"
    )
    current_open_interest: float | None = Field(
        default=None, description="Current open interest in USD"
    )
    open_interest_change_pct: float | None = Field(
        default=None, description="Open interest change percentage over period"
    )


class AggregatedLendingStats(BaseModel):
    """Aggregated lending market statistics."""

    current_supply_apy_pct: float = Field(description="Current supply APY percentage")
    mean_supply_apy_pct: float = Field(description="Mean supply APY over period")
    min_supply_apy_pct: float = Field(description="Minimum supply APY over period")
    max_supply_apy_pct: float = Field(description="Maximum supply APY over period")
    current_variable_borrow_apy_pct: float = Field(description="Current variable borrow APY percentage")
    mean_variable_borrow_apy_pct: float = Field(description="Mean variable borrow APY over period")
    spread_pct: float = Field(description="Current spread (borrow - supply) percentage")


class AggregatedStatsResponse(BaseModel):
    """Response for single-asset aggregated statistics."""

    asset: str = Field(description="Asset symbol (e.g., BTC)")
    query: dict = Field(description="Query parameters used (start, end, period_days)")
    spot: AggregatedSpotStats | None = Field(
        default=None, description="Spot market statistics (null if unavailable)"
    )
    futures: AggregatedFuturesStats | None = Field(
        default=None, description="Futures market statistics (null if unavailable)"
    )
    lending: AggregatedLendingStats | None = Field(
        default=None, description="Lending market statistics (null if unavailable)"
    )
    timestamp: datetime = Field(description="Response generation timestamp (UTC)")


class MultiAssetAggregatedStatsResponse(BaseModel):
    """Response for multi-asset aggregated statistics."""

    query: dict = Field(description="Query parameters used (assets, start, end, period_days)")
    data: dict[str, dict] = Field(
        description="Per-asset statistics: {asset: {spot, futures, lending}}"
    )
    correlations: dict[str, dict[str, float]] | None = Field(
        default=None, description="Cross-asset correlation matrix (null if unavailable)"
    )
    timestamp: datetime = Field(description="Response generation timestamp (UTC)")
