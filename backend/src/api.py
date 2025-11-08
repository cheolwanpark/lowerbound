"""FastAPI endpoints for OHLCV data service."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from loguru import logger

from src.config import settings
from src.database import (
    get_candle_count,
    get_earliest_timestamp,
    get_latest_timestamp,
    get_ohlcv_data,
    health_check,
    is_backfill_completed,
    # Futures database functions
    get_funding_rates,
    get_mark_klines,
    get_index_klines,
    get_open_interest,
    get_earliest_futures_timestamp,
    get_latest_futures_timestamp,
    get_futures_data_count,
    is_futures_backfill_completed,
    # Lending database functions
    get_lending_data,
    get_earliest_lending_timestamp,
    get_latest_lending_timestamp,
    get_lending_event_count,
    is_lending_backfill_completed,
)
from src.models import (
    AssetCoverage,
    AssetCoverageResponse,
    FetchTriggerRequest,
    FetchTriggerResponse,
    HealthCheck,
    OHLCVCandle,
    OHLCVResponse,
    # Futures models
    FundingRateDataPoint,
    FundingRateResponse,
    MarkPriceCandle,
    MarkPriceResponse,
    IndexPriceCandle,
    IndexPriceResponse,
    OpenInterestDataPoint,
    OpenInterestResponse,
    FuturesAssetCoverage,
    FuturesAssetCoverageResponse,
    # Lending models
    LendingDataPoint,
    LendingResponse,
    LendingAssetCoverage,
    LendingAssetCoverageResponse,
    convert_ray_to_apy,
    # Risk analysis models
    RiskProfileRequest,
    RiskProfileResponse,
    # Aggregated statistics models
    AggregatedSpotStats,
    AggregatedFuturesStats,
    AggregatedLendingStats,
    AggregatedStatsResponse,
    MultiAssetAggregatedStatsResponse,
)

router = APIRouter()


# ==================== Authentication ====================


def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Verify API key for protected endpoints."""
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# ==================== Public Endpoints ====================


@router.get("/health", response_model=HealthCheck)
async def get_health() -> HealthCheck:
    """
    Health check endpoint.

    Verifies:
    - Service is running
    - Database connection is healthy
    """
    db_healthy = await health_check()

    return HealthCheck(
        status="healthy" if db_healthy else "unhealthy",
        database="connected" if db_healthy else "disconnected",
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/assets", response_model=AssetCoverageResponse)
async def get_assets() -> AssetCoverageResponse:
    """
    Get data coverage information for all tracked assets.

    Returns information about:
    - Earliest and latest timestamps
    - Total number of candles
    - Backfill completion status
    """
    assets = []

    for asset in settings.assets_list:
        earliest = await get_earliest_timestamp(asset)
        latest = await get_latest_timestamp(asset)
        count = await get_candle_count(asset)
        completed = await is_backfill_completed(asset)

        assets.append(
            AssetCoverage(
                asset=asset,
                earliest_timestamp=earliest,
                latest_timestamp=latest,
                total_candles=count,
                backfill_completed=completed,
            )
        )

    return AssetCoverageResponse(assets=assets)


@router.get("/ohlcv/{asset}", response_model=OHLCVResponse)
async def get_ohlcv(
    asset: str,
    start: Annotated[datetime | None, Query(description="Start timestamp (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End timestamp (UTC)")] = None,
    limit: Annotated[int | None, Query(description="Maximum number of candles", ge=1, le=10000)] = None,
    fill: Annotated[bool, Query(description="Forward-fill missing candles")] = False,
) -> OHLCVResponse:
    """
    Retrieve OHLCV data for a specific asset.

    Args:
        asset: Asset symbol (e.g., 'BTC')
        start: Start timestamp (inclusive)
        end: End timestamp (inclusive)
        limit: Maximum number of candles to return
        fill: Whether to forward-fill missing candles

    Returns:
        OHLCV data for the asset

    Raises:
        404: Asset not found or not tracked
    """
    # Validate asset
    asset_upper = asset.upper()
    if asset_upper not in settings.assets_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset}' not found. Tracked assets: {', '.join(settings.assets_list)}",
        )

    # Query database
    data = await get_ohlcv_data(
        asset=asset_upper,
        start_time=start,
        end_time=end,
        limit=limit,
    )

    # Convert to Pydantic models
    candles = [
        OHLCVCandle(
            timestamp=row["timestamp"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            filled=False,
        )
        for row in data
    ]

    # Apply forward-fill if requested
    if fill and candles:
        candles = _forward_fill_candles(candles, interval_hours=12)

    return OHLCVResponse(
        asset=asset_upper,
        interval="12h",
        data=candles,
        count=len(candles),
    )


def _forward_fill_candles(candles: list[OHLCVCandle], interval_hours: int) -> list[OHLCVCandle]:
    """
    Forward-fill missing candles in a time series.

    Args:
        candles: List of existing candles (must be sorted by timestamp)
        interval_hours: Expected interval between candles

    Returns:
        List of candles with gaps filled
    """
    if not candles or len(candles) < 2:
        return candles

    filled_candles = []
    interval_delta = timedelta(hours=interval_hours)

    for i in range(len(candles)):
        filled_candles.append(candles[i])

        # Check if there's a gap before the next candle
        if i < len(candles) - 1:
            current_time = candles[i].timestamp
            next_time = candles[i + 1].timestamp
            expected_next = current_time + interval_delta

            # Fill gaps
            while expected_next < next_time:
                # Use last known close price for all OHLCV values
                last_close = candles[i].close

                filled_candle = OHLCVCandle(
                    timestamp=expected_next,
                    open=last_close,
                    high=last_close,
                    low=last_close,
                    close=last_close,
                    volume=0,  # Zero volume for filled candles
                    filled=True,
                )
                filled_candles.append(filled_candle)
                expected_next += interval_delta

    return filled_candles


# ==================== Protected Endpoints ====================


@router.post("/fetch/trigger", response_model=FetchTriggerResponse)
async def trigger_fetch(
    request: FetchTriggerRequest,
    _: Annotated[None, Depends(verify_api_key)],
) -> FetchTriggerResponse:
    """
    Manually trigger a fetch job for specific assets.

    **Authentication required**: X-API-KEY header

    Args:
        request: Fetch trigger parameters
            - assets: List of assets to fetch (None = all tracked)
            - start_date: Optional start date
            - end_date: Optional end date

    Returns:
        Job identifier and status message

    Raises:
        401: Invalid or missing API key
    """
    # Determine which assets to fetch
    assets_to_fetch = request.assets or settings.assets_list

    # Validate assets
    invalid_assets = [a for a in assets_to_fetch if a not in settings.assets_list]
    if invalid_assets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assets: {', '.join(invalid_assets)}. "
            f"Tracked assets: {', '.join(settings.assets_list)}",
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # TODO: Implement actual async job execution
    # For now, this is a placeholder that would integrate with a job queue
    logger.info(
        f"Manual fetch triggered (job_id={job_id}): assets={assets_to_fetch}, "
        f"start={request.start_date}, end={request.end_date}"
    )

    return FetchTriggerResponse(
        job_id=job_id,
        message=f"Fetch job queued for {len(assets_to_fetch)} asset(s)",
        assets=assets_to_fetch,
    )


@router.get("/fetch/status/{job_id}")
async def get_fetch_status(
    job_id: str,
    _: Annotated[None, Depends(verify_api_key)],
) -> dict:
    """
    Check the status of a manual fetch job.

    **Authentication required**: X-API-KEY header

    Args:
        job_id: Job identifier returned from /fetch/trigger

    Returns:
        Job status information

    Raises:
        401: Invalid or missing API key
        404: Job not found
    """
    # TODO: Implement actual job status tracking
    # This is a placeholder
    logger.info(f"Status check for job {job_id}")

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job status tracking not yet implemented",
    }


# ==================== Futures Endpoints ====================


@router.get("/futures/assets", response_model=FuturesAssetCoverageResponse)
async def get_futures_assets() -> FuturesAssetCoverageResponse:
    """
    Get data coverage information for all tracked futures assets.

    Returns information about each metric type:
    - Funding rates
    - Mark price klines
    - Index price klines
    - Open interest
    """
    assets = []

    for asset in settings.futures_assets_list:
        # Get funding rate coverage
        fr_earliest = await get_earliest_futures_timestamp(asset, "funding_rate")
        fr_latest = await get_latest_futures_timestamp(asset, "funding_rate")
        fr_count = await get_futures_data_count(asset, "funding_rate")

        # Get mark price klines coverage
        mark_earliest = await get_earliest_futures_timestamp(asset, "mark_klines")
        mark_latest = await get_latest_futures_timestamp(asset, "mark_klines")
        mark_count = await get_futures_data_count(asset, "mark_klines")

        # Get index price klines coverage
        index_earliest = await get_earliest_futures_timestamp(asset, "index_klines")
        index_latest = await get_latest_futures_timestamp(asset, "index_klines")
        index_count = await get_futures_data_count(asset, "index_klines")

        # Get open interest coverage
        oi_earliest = await get_earliest_futures_timestamp(asset, "open_interest")
        oi_latest = await get_latest_futures_timestamp(asset, "open_interest")
        oi_count = await get_futures_data_count(asset, "open_interest")

        assets.append(
            FuturesAssetCoverage(
                asset=asset,
                funding_rate_count=fr_count,
                funding_rate_earliest=fr_earliest,
                funding_rate_latest=fr_latest,
                mark_klines_count=mark_count,
                mark_klines_earliest=mark_earliest,
                mark_klines_latest=mark_latest,
                index_klines_count=index_count,
                index_klines_earliest=index_earliest,
                index_klines_latest=index_latest,
                open_interest_count=oi_count,
                open_interest_earliest=oi_earliest,
                open_interest_latest=oi_latest,
            )
        )

    return FuturesAssetCoverageResponse(assets=assets)


@router.get("/futures/funding-rates/{asset}", response_model=FundingRateResponse)
async def get_futures_funding_rates(
    asset: str,
    start: Annotated[datetime | None, Query(description="Start timestamp (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End timestamp (UTC)")] = None,
    limit: Annotated[int | None, Query(description="Max records to return", ge=1, le=10000)] = None,
) -> FundingRateResponse:
    """
    Get funding rate data for a futures asset.

    Args:
        asset: Asset symbol (e.g., BTC)
        start: Start timestamp (inclusive)
        end: End timestamp (inclusive)
        limit: Maximum number of records to return

    Returns:
        Funding rate data

    Raises:
        404: Asset not tracked or no data available
    """
    asset = asset.upper()

    if asset not in settings.futures_assets_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset} not tracked. Tracked assets: {settings.futures_assets_list}",
        )

    data = await get_funding_rates(asset, start, end, limit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No funding rate data found for {asset}",
        )

    # Convert to response model
    data_points = [
        FundingRateDataPoint(
            timestamp=row["timestamp"],
            funding_rate=row["funding_rate"],
            mark_price=row["mark_price"],
        )
        for row in data
    ]

    return FundingRateResponse(
        asset=asset,
        interval=f"{settings.futures_funding_interval_hours}h",
        data=data_points,
        count=len(data_points),
    )


@router.get("/futures/mark-price/{asset}", response_model=MarkPriceResponse)
async def get_futures_mark_price(
    asset: str,
    start: Annotated[datetime | None, Query(description="Start timestamp (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End timestamp (UTC)")] = None,
    limit: Annotated[int | None, Query(description="Max candles to return", ge=1, le=10000)] = None,
) -> MarkPriceResponse:
    """
    Get mark price klines for a futures asset.

    Args:
        asset: Asset symbol (e.g., BTC)
        start: Start timestamp (inclusive)
        end: End timestamp (inclusive)
        limit: Maximum number of candles to return

    Returns:
        Mark price OHLCV data

    Raises:
        404: Asset not tracked or no data available
    """
    asset = asset.upper()

    if asset not in settings.futures_assets_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset} not tracked. Tracked assets: {settings.futures_assets_list}",
        )

    data = await get_mark_klines(asset, start, end, limit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mark price data found for {asset}",
        )

    candles = [
        MarkPriceCandle(
            timestamp=row["timestamp"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
        )
        for row in data
    ]

    return MarkPriceResponse(
        asset=asset,
        interval=settings.futures_klines_interval,
        data=candles,
        count=len(candles),
    )


@router.get("/futures/index-price/{asset}", response_model=IndexPriceResponse)
async def get_futures_index_price(
    asset: str,
    start: Annotated[datetime | None, Query(description="Start timestamp (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End timestamp (UTC)")] = None,
    limit: Annotated[int | None, Query(description="Max candles to return", ge=1, le=10000)] = None,
) -> IndexPriceResponse:
    """
    Get index price klines for a futures asset.

    Args:
        asset: Asset symbol (e.g., BTC)
        start: Start timestamp (inclusive)
        end: End timestamp (inclusive)
        limit: Maximum number of candles to return

    Returns:
        Index price OHLCV data

    Raises:
        404: Asset not tracked or no data available
    """
    asset = asset.upper()

    if asset not in settings.futures_assets_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset} not tracked. Tracked assets: {settings.futures_assets_list}",
        )

    data = await get_index_klines(asset, start, end, limit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No index price data found for {asset}",
        )

    candles = [
        IndexPriceCandle(
            timestamp=row["timestamp"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
        )
        for row in data
    ]

    return IndexPriceResponse(
        asset=asset,
        interval=settings.futures_klines_interval,
        data=candles,
        count=len(candles),
    )


@router.get("/futures/open-interest/{asset}", response_model=OpenInterestResponse)
async def get_futures_open_interest(
    asset: str,
    start: Annotated[datetime | None, Query(description="Start timestamp (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End timestamp (UTC)")] = None,
    limit: Annotated[int | None, Query(description="Max records to return", ge=1, le=10000)] = None,
) -> OpenInterestResponse:
    """
    Get open interest data for a futures asset.

    Note: Binance only provides ~30 days of open interest history.

    Args:
        asset: Asset symbol (e.g., BTC)
        start: Start timestamp (inclusive)
        end: End timestamp (inclusive)
        limit: Maximum number of records to return

    Returns:
        Open interest data

    Raises:
        404: Asset not tracked or no data available
    """
    asset = asset.upper()

    if asset not in settings.futures_assets_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset {asset} not tracked. Tracked assets: {settings.futures_assets_list}",
        )

    data = await get_open_interest(asset, start, end, limit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No open interest data found for {asset}",
        )

    data_points = [
        OpenInterestDataPoint(
            timestamp=row["timestamp"],
            open_interest=row["open_interest"],
        )
        for row in data
    ]

    return OpenInterestResponse(
        asset=asset,
        data=data_points,
        count=len(data_points),
    )


# ==================== Lending Endpoints ====================


@router.get("/lending/assets", response_model=LendingAssetCoverageResponse)
async def get_lending_assets() -> LendingAssetCoverageResponse:
    """
    Get data coverage information for all tracked lending assets.

    Returns information about:
    - Earliest and latest timestamps
    - Total number of events
    - Backfill completion status
    """
    assets = []

    for asset in settings.lending_assets_list:
        earliest = await get_earliest_lending_timestamp(asset)
        latest = await get_latest_lending_timestamp(asset)
        total_events = await get_lending_event_count(asset)
        backfill_completed = await is_lending_backfill_completed(asset)

        assets.append(
            LendingAssetCoverage(
                asset=asset,
                earliest_timestamp=earliest,
                latest_timestamp=latest,
                total_events=total_events,
                backfill_completed=backfill_completed,
            )
        )

    return LendingAssetCoverageResponse(assets=assets)


@router.get("/lending/{asset}", response_model=LendingResponse)
async def get_lending(
    asset: str,
    start: Annotated[datetime | None, Query(description="Start timestamp (UTC)")] = None,
    end: Annotated[datetime | None, Query(description="End timestamp (UTC)")] = None,
    limit: Annotated[
        int | None, Query(description="Maximum number of records to return", ge=1, le=1000)
    ] = 100,
) -> LendingResponse:
    """
    Get lending data for an asset from Dune Analytics.

    Supports asset symbol mapping (e.g., BTC → WBTC, ETH → WETH).

    Returns:
    - Data point timestamps
    - Reserve contract address
    - Supply and borrow rates (both RAY and APY formats)
    - Liquidity and variable borrow indices

    Query Parameters:
    - start: Start timestamp (inclusive)
    - end: End timestamp (inclusive)
    - limit: Max records (1-1000, default 100)
    """
    # Map user input to lending asset symbol (e.g., BTC → WBTC)
    asset_upper = asset.upper()

    # First check if it's already a tracked lending asset (more efficient)
    if asset_upper in settings.lending_assets_list:
        lending_asset = asset_upper
    # Then try symbol mapping (e.g., BTC → WBTC)
    elif asset_upper in settings.lending_asset_symbol_map:
        lending_asset = settings.lending_asset_symbol_map[asset_upper]
    else:
        # Build user-friendly error message showing both mapped and native symbols
        mapped_symbols = [
            f"{k}→{v}" for k, v in settings.lending_asset_symbol_map.items() if k != v
        ]
        available_symbols = ", ".join(mapped_symbols + list(settings.lending_assets_list))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset}' not found. Available: {available_symbols}",
        )

    try:
        # Query lending data from database
        rows = await get_lending_data(
            asset=lending_asset,
            start_time=start,
            end_time=end,
            limit=limit,
        )

        # Convert to API response format with RAY→APY conversion
        data_points = []
        failed_count = 0

        for row in rows:
            try:
                # Convert RAY rates to APY percentages
                supply_apy = convert_ray_to_apy(row["supply_rate_ray"])
                variable_borrow_apy = convert_ray_to_apy(row["variable_borrow_rate_ray"])
                stable_borrow_apy = convert_ray_to_apy(row["stable_borrow_rate_ray"])

                data_point = LendingDataPoint(
                    timestamp=row["timestamp"],
                    reserve_address=row["reserve_address"],
                    supply_rate_ray=str(row["supply_rate_ray"]),
                    supply_apy_percent=supply_apy,
                    variable_borrow_rate_ray=str(row["variable_borrow_rate_ray"]),
                    variable_borrow_apy_percent=variable_borrow_apy,
                    stable_borrow_rate_ray=str(row["stable_borrow_rate_ray"]),
                    stable_borrow_apy_percent=stable_borrow_apy,
                    liquidity_index=str(row["liquidity_index"]),
                    variable_borrow_index=str(row["variable_borrow_index"]),
                )
                data_points.append(data_point)
            except (ValueError, ArithmeticError, KeyError) as e:
                failed_count += 1
                logger.warning(f"Failed to convert lending data row: {e}", exc_info=True)
                # Skip this row but continue processing others
                continue

        # Warn if some conversions failed
        if failed_count > 0:
            logger.warning(f"Skipped {failed_count}/{len(rows)} rows due to conversion errors")

        # Raise error if ALL rows failed conversion (prevents silent empty responses)
        if not data_points and rows:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"All {len(rows)} data points failed conversion",
            )

        return LendingResponse(
            asset=lending_asset,
            data=data_points,
            count=len(data_points),
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error querying lending data for {asset}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query lending data: {str(e)}",
        )


# ==================== Aggregated Statistics Endpoints ====================


@router.get("/aggregated-stats/multi", response_model=MultiAssetAggregatedStatsResponse)
async def get_aggregated_stats_multi(
    assets: Annotated[str, Query(description="Comma-separated asset list (e.g., BTC,ETH,SOL)")],
    start: Annotated[datetime, Query(description="Start timestamp (ISO 8601, UTC)")],
    end: Annotated[datetime, Query(description="End timestamp (ISO 8601, UTC)")],
    data_types: Annotated[
        str, Query(description="Comma-separated data types: spot, futures, lending")
    ] = "spot,futures,lending",
) -> MultiAssetAggregatedStatsResponse:
    """
    Get pre-aggregated statistics for multiple assets with cross-asset correlations.

    Returns calculated metrics from existing database records (no new data fetching).
    Includes correlation matrix for multi-asset portfolio analysis.

    **Query Parameters:**
    - `assets`: Comma-separated asset list (e.g., "BTC,ETH,SOL"), max 10 assets
    - `start`, `end`: ISO 8601 datetime (UTC), max range 90 days
    - `data_types`: Comma-separated list of "spot", "futures", "lending" (optional, default: all)

    **Response:**
    - Per-asset statistics in `data` field: `{asset: {spot, futures, lending}}`
    - Cross-asset correlation matrix in `correlations` field (requires ≥2 assets with spot data)
    - Unavailable data types return `null` per asset

    **Correlation Matrix:**
    - Time-aligned using inner join (only overlapping periods)
    - Calculated from daily returns
    - Returns `null` if insufficient overlapping data

    **Examples:**
    - `/aggregated-stats/multi?assets=BTC,ETH,SOL&start=2025-01-01T00:00:00Z&end=2025-02-01T00:00:00Z`
    - `/aggregated-stats/multi?assets=BTC,ETH&start=2025-01-15T00:00:00Z&end=2025-02-15T00:00:00Z&data_types=spot`
    """
    from src.analysis.aggregated_stats import (
        calculate_cross_asset_correlations,
        calculate_futures_stats,
        calculate_lending_stats,
        calculate_spot_stats,
    )

    # Parse and validate assets
    asset_list = [a.strip().upper() for a in assets.split(",")]
    asset_list = list(dict.fromkeys(asset_list))  # Remove duplicates while preserving order

    if len(asset_list) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many assets requested: {len(asset_list)} (max 10)",
        )

    if len(asset_list) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one asset must be specified",
        )

    # Validate all assets exist
    invalid_assets = [a for a in asset_list if a not in settings.assets_list]
    if invalid_assets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assets not tracked: {', '.join(invalid_assets)}. Available: {', '.join(settings.assets_list)}",
        )

    # Validate date range (max 90 days)
    period_days = (end - start).days
    if period_days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range too large: {period_days} days (max 90 days)",
        )
    if period_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Parse requested data types
    requested_types = {dt.strip().lower() for dt in data_types.split(",")}
    valid_types = {"spot", "futures", "lending"}
    invalid_types = requested_types - valid_types
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data types: {invalid_types}. Valid: {valid_types}",
        )

    # Fetch data and calculate stats for all assets
    multi_asset_data = {}
    multi_asset_ohlcv = {}  # For correlation calculation

    try:
        for asset in asset_list:
            asset_stats = {}

            # Fetch spot data if requested
            if "spot" in requested_types:
                ohlcv_data = await get_ohlcv_data(asset, start, end)
                if ohlcv_data:
                    spot_stats_dict = calculate_spot_stats(ohlcv_data)
                    if spot_stats_dict:
                        asset_stats["spot"] = spot_stats_dict
                        multi_asset_ohlcv[asset] = ohlcv_data  # Save for correlation
                    else:
                        asset_stats["spot"] = None
                else:
                    asset_stats["spot"] = None
            else:
                asset_stats["spot"] = None

            # Fetch futures data if requested
            if "futures" in requested_types and asset in settings.futures_assets_list:
                funding_data = await get_funding_rates(asset, start, end)
                mark_data = await get_mark_klines(asset, start, end)
                oi_data = await get_open_interest(asset, start, end)

                # Get spot price for basis calculation
                if "spot" not in requested_types:
                    ohlcv_data = await get_ohlcv_data(asset, start, end)
                else:
                    ohlcv_data = multi_asset_ohlcv.get(asset)

                spot_price = None
                if ohlcv_data and len(ohlcv_data) > 0:
                    spot_price = float(ohlcv_data[-1]["close"])

                if funding_data:
                    futures_stats_dict = calculate_futures_stats(
                        funding_data, mark_data, oi_data, spot_price
                    )
                    asset_stats["futures"] = futures_stats_dict
                else:
                    asset_stats["futures"] = None
            else:
                asset_stats["futures"] = None

            # Fetch lending data if requested
            if "lending" in requested_types:
                # Map asset symbol to lending asset (e.g., BTC → WBTC)
                lending_asset = None
                if asset in settings.lending_assets_list:
                    lending_asset = asset
                elif asset in settings.lending_asset_symbol_map:
                    lending_asset = settings.lending_asset_symbol_map[asset]

                if lending_asset:
                    lending_data_rows = await get_lending_data(lending_asset, start, end)
                    if lending_data_rows:
                        lending_stats_dict = calculate_lending_stats(lending_data_rows)
                        asset_stats["lending"] = lending_stats_dict
                    else:
                        asset_stats["lending"] = None
                else:
                    asset_stats["lending"] = None
            else:
                asset_stats["lending"] = None

            multi_asset_data[asset] = asset_stats

        # Calculate cross-asset correlations if we have spot data for multiple assets
        correlations = None
        if len(multi_asset_ohlcv) >= 2:
            correlations = calculate_cross_asset_correlations(multi_asset_ohlcv)

        return MultiAssetAggregatedStatsResponse(
            query={
                "assets": asset_list,
                "start": start,
                "end": end,
                "period_days": period_days,
            },
            data=multi_asset_data,
            correlations=correlations,
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating multi-asset aggregated stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate statistics: {str(e)}",
        )


@router.get("/aggregated-stats/{asset}", response_model=AggregatedStatsResponse)
async def get_aggregated_stats_single(
    asset: str,
    start: Annotated[datetime, Query(description="Start timestamp (ISO 8601, UTC)")],
    end: Annotated[datetime, Query(description="End timestamp (ISO 8601, UTC)")],
    data_types: Annotated[
        str, Query(description="Comma-separated data types: spot, futures, lending")
    ] = "spot,futures,lending",
) -> AggregatedStatsResponse:
    """
    Get pre-aggregated statistics for a single asset.

    Returns calculated metrics from existing database records (no new data fetching).
    Designed for AI agents to reduce token usage by 80-85% vs raw time series data.

    **Query Parameters:**
    - `start`, `end`: ISO 8601 datetime (UTC), max range 90 days
    - `data_types`: Comma-separated list of "spot", "futures", "lending" (optional, default: all)

    **Response:**
    - Returns available statistics for requested data types
    - Unavailable data types return `null` (e.g., no lending data for BTC)
    - No errors for missing data - graceful degradation

    **Metrics Returned:**
    - **Spot** (8 metrics): price stats, total return %, volatility %, Sharpe ratio, max drawdown %
    - **Futures** (7 metrics): funding rates, basis premium, open interest change
    - **Lending** (7 metrics): supply/borrow APY stats, spread

    **Examples:**
    - `/aggregated-stats/BTC?start=2025-01-01T00:00:00Z&end=2025-02-01T00:00:00Z`
    - `/aggregated-stats/ETH?start=2025-01-01T00:00:00Z&end=2025-02-01T00:00:00Z&data_types=spot,futures`
    """
    from src.analysis.aggregated_stats import (
        calculate_futures_stats,
        calculate_lending_stats,
        calculate_spot_stats,
    )

    # Validate asset
    asset_upper = asset.upper()
    if asset_upper not in settings.assets_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset}' not tracked. Available: {', '.join(settings.assets_list)}",
        )

    # Validate date range (max 90 days)
    period_days = (end - start).days
    if period_days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range too large: {period_days} days (max 90 days)",
        )
    if period_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Parse requested data types
    requested_types = {dt.strip().lower() for dt in data_types.split(",")}
    valid_types = {"spot", "futures", "lending"}
    invalid_types = requested_types - valid_types
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data types: {invalid_types}. Valid: {valid_types}",
        )

    # Fetch data and calculate stats
    spot_stats = None
    futures_stats = None
    lending_stats = None
    ohlcv_data = None  # Initialize for use in futures basis calculation

    try:
        # Fetch spot data if requested
        if "spot" in requested_types and asset_upper in settings.assets_list:
            ohlcv_data = await get_ohlcv_data(asset_upper, start, end)
            if ohlcv_data:
                spot_stats_dict = calculate_spot_stats(ohlcv_data)
                if spot_stats_dict:
                    spot_stats = AggregatedSpotStats(**spot_stats_dict)

        # Fetch futures data if requested
        if "futures" in requested_types and asset_upper in settings.futures_assets_list:
            funding_data = await get_funding_rates(asset_upper, start, end)
            mark_data = await get_mark_klines(asset_upper, start, end)
            oi_data = await get_open_interest(asset_upper, start, end)

            # Get current spot price for basis calculation
            # Fetch spot data if not already loaded
            if not ohlcv_data:
                ohlcv_data = await get_ohlcv_data(asset_upper, start, end)

            spot_price = None
            if ohlcv_data and len(ohlcv_data) > 0:
                spot_price = float(ohlcv_data[-1]["close"])

            if funding_data:
                futures_stats_dict = calculate_futures_stats(
                    funding_data, mark_data, oi_data, spot_price
                )
                if futures_stats_dict:
                    futures_stats = AggregatedFuturesStats(**futures_stats_dict)

        # Fetch lending data if requested
        if "lending" in requested_types:
            # Map asset symbol to lending asset (e.g., BTC → WBTC)
            lending_asset = None
            if asset_upper in settings.lending_assets_list:
                lending_asset = asset_upper
            elif asset_upper in settings.lending_asset_symbol_map:
                lending_asset = settings.lending_asset_symbol_map[asset_upper]

            if lending_asset:
                lending_data_rows = await get_lending_data(lending_asset, start, end)
                if lending_data_rows:
                    lending_stats_dict = calculate_lending_stats(lending_data_rows)
                    if lending_stats_dict:
                        lending_stats = AggregatedLendingStats(**lending_stats_dict)

        return AggregatedStatsResponse(
            asset=asset_upper,
            query={"start": start, "end": end, "period_days": period_days},
            spot=spot_stats,
            futures=futures_stats,
            lending=lending_stats,
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating aggregated stats for {asset}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate statistics: {str(e)}",
        )


# ==================== Risk Analysis Endpoints ====================


@router.post("/analysis/risk-profile", response_model=RiskProfileResponse)
async def calculate_portfolio_risk_profile(
    request: RiskProfileRequest,
) -> RiskProfileResponse:
    """
    Calculate comprehensive risk profile for a portfolio of spot & futures positions.

    This endpoint performs:
    - Portfolio valuation across different price scenarios (-30% to +30%)
    - Risk metrics calculation (VaR, CVaR, Sharpe ratio, volatility, max drawdown)
    - Delta exposure calculation (market directional risk)
    - Scenario analysis (bull market, bear market, crypto winter, etc.)
    - Asset correlation analysis

    **Methodology:**
    - VaR/CVaR: Historical Simulation method (non-parametric)
    - Time Horizon: 1-day VaR at 95% and 99% confidence levels
    - Data Lookback: Configurable (default 30 days, max 180 days)
    - Time Series: Daily intervals (12h spot OHLCV and 8h futures data resampled to 24h)
    - Risk-Free Rate: 0% (configurable in settings)

    **Limitations:**
    - Funding rate data only available for past 30 days (vs desired 180 days for spot)
    - Assumes basis (futures-spot spread) remains constant during price shocks
    - Forward-fills missing data points (gaps ≤2 days)
    - Portfolio resampled to daily intervals for consistency

    **Example Request:**
    ```json
    {
      "positions": [
        {
          "asset": "BTC",
          "quantity": 1.5,
          "position_type": "spot",
          "entry_price": 45000.0,
          "leverage": 1.0
        },
        {
          "asset": "ETH",
          "quantity": 10.0,
          "position_type": "futures_long",
          "entry_price": 2500.0,
          "leverage": 3.0
        }
      ],
      "lookback_days": 30
    }
    ```

    **Response includes:**
    - Current portfolio value
    - Sensitivity analysis table (price changes from -30% to +30%)
    - Risk metrics (VaR, CVaR, Sharpe, volatility, correlation matrix, delta exposure)
    - Scenario results (8 predefined market scenarios)
    - Data availability warnings (if any)
    """
    from src.analysis.riskprofile import calculate_risk_profile

    try:
        logger.info(
            f"Risk profile calculation requested for {len(request.positions)} positions, "
            f"lookback={request.lookback_days} days"
        )

        # Convert Pydantic model to dict for processing
        request_data = {
            "positions": [pos.model_dump() for pos in request.positions],
            "lookback_days": request.lookback_days,
        }

        # Calculate risk profile
        result = await calculate_risk_profile(request_data)

        logger.info(
            f"Risk profile calculated: portfolio_value=${result['current_portfolio_value']:,.2f}, "
            f"VaR_95=${result['risk_metrics']['var_95_1day']:,.2f}"
        )

        return RiskProfileResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid risk profile request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Risk profile calculation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk calculation failed: {str(e)}",
        )
