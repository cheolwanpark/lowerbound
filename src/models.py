"""Pydantic models for API requests/responses and data validation."""

from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger
from pydantic import BaseModel, Field, field_validator


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


# ==================== Lending (Aave) Models ====================


class AaveReserveData(BaseModel):
    """
    Aave reserve data from GraphQL API.

    Models the event-based data from Aave Subgraph reserveParamsHistoryItems.
    """

    model_config = {"populate_by_name": True}

    timestamp: int = Field(description="Event timestamp (Unix seconds)")
    liquidity_rate: str = Field(alias="liquidityRate", description="Supply APR in RAY units (10^27)")
    variable_borrow_rate: str = Field(
        alias="variableBorrowRate", description="Variable borrow APR in RAY units (10^27)"
    )
    stable_borrow_rate: str = Field(alias="stableBorrowRate", description="Stable borrow APR in RAY units (10^27)")
    total_liquidity: str = Field(alias="totalLiquidity", description="Total supplied liquidity")
    available_liquidity: str = Field(alias="availableLiquidity", description="Available liquidity to borrow")
    total_variable_debt: str = Field(alias="totalCurrentVariableDebt", description="Total variable rate debt")
    total_stable_debt: str = Field(alias="totalPrincipalStableDebt", description="Total stable rate debt")
    utilization_rate: str = Field(alias="utilizationRate", description="Utilization rate (decimal)")
    price_in_eth: str | None = Field(default=None, alias="priceInEth", description="Asset price in ETH")

    def to_dict(self, eth_usd_price: Decimal | None = None) -> dict:
        """
        Convert to dictionary for database insertion.

        Args:
            eth_usd_price: Current ETH/USD price for computing price_usd

        Returns:
            Dict with all lending data fields
        """
        # Calculate price_usd if we have both price_eth and eth_usd_price
        price_eth_decimal = Decimal(self.price_in_eth) if self.price_in_eth else None
        price_usd = None
        if price_eth_decimal and eth_usd_price:
            price_usd = price_eth_decimal * eth_usd_price

        # Calculate total_borrowed = variable debt + stable debt
        total_borrowed = Decimal(self.total_variable_debt) + Decimal(self.total_stable_debt)

        return {
            "timestamp": datetime.fromtimestamp(self.timestamp, tz=timezone.utc),
            "supply_rate_ray": self.liquidity_rate,  # Keep as string for NUMERIC(78,27)
            "variable_borrow_rate_ray": self.variable_borrow_rate,
            "stable_borrow_rate_ray": self.stable_borrow_rate,
            "total_supplied": Decimal(self.total_liquidity),
            "available_liquidity": Decimal(self.available_liquidity),
            "total_borrowed": total_borrowed,
            "utilization_rate": Decimal(self.utilization_rate),
            "price_eth": price_eth_decimal,
            "price_usd": price_usd,
        }


def convert_ray_to_apy(ray_rate: str | Decimal) -> float:
    """
    Convert Aave RAY rate to APY percentage.

    Aave rates are expressed in RAY units (10^27) as APR with continuous compounding.
    Formula: APY = e^APR - 1

    Args:
        ray_rate: Rate in RAY units (string or Decimal)

    Returns:
        APY as percentage (e.g., 5.23 for 5.23%)
    """
    import math

    # Convert RAY to APR decimal
    ray = Decimal(ray_rate)
    apr_decimal = ray / Decimal(10**27)

    # Convert APR to APY with continuous compounding
    # APY = e^APR - 1
    try:
        apy_decimal = Decimal(math.exp(float(apr_decimal))) - Decimal(1)
    except OverflowError:
        # For extremely high rates, cap at 1000000% APY
        logger.warning(f"APR rate overflow: {apr_decimal}, capping at 1000000% APY")
        return 1000000.0

    # Convert to percentage
    return float(apy_decimal * 100)


class LendingDataPoint(BaseModel):
    """Lending data point for API responses."""

    timestamp: datetime = Field(description="Event timestamp (UTC)")
    supply_rate_ray: str = Field(description="Supply APR in RAY units (10^27 precision)")
    supply_apy_percent: float = Field(description="Supply APY as percentage (e.g., 5.23 = 5.23%)")
    variable_borrow_rate_ray: str = Field(description="Variable borrow APR in RAY units")
    variable_borrow_apy_percent: float = Field(description="Variable borrow APY as percentage")
    stable_borrow_rate_ray: str = Field(description="Stable borrow APR in RAY units")
    stable_borrow_apy_percent: float = Field(description="Stable borrow APY as percentage")
    total_supplied: Decimal = Field(description="Total supplied liquidity")
    available_liquidity: Decimal = Field(description="Available liquidity to borrow")
    total_borrowed: Decimal = Field(description="Total borrowed amount")
    utilization_rate: Decimal = Field(description="Utilization rate (0.0 to 1.0)")
    price_eth: Decimal | None = Field(default=None, description="Asset price in ETH")
    price_usd: Decimal | None = Field(default=None, description="Asset price in USD")


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
