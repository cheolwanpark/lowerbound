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
    start: datetime | None = Query(None, description="Start timestamp (UTC)"),
    end: datetime | None = Query(None, description="End timestamp (UTC)"),
    limit: int | None = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
) -> LendingResponse:
    """
    Get lending data for an asset.

    Supports asset symbol mapping (e.g., BTC → WBTC, ETH → WETH).

    Returns:
    - Event timestamps
    - Supply and borrow rates (both RAY and APY formats)
    - Liquidity metrics
    - Prices (ETH and USD)

    Query Parameters:
    - start: Start timestamp (inclusive)
    - end: End timestamp (inclusive)
    - limit: Max records (1-1000, default 100)
    """
    # Map user input to Aave symbol (e.g., BTC → WBTC)
    asset_upper = asset.upper()
    symbol_map = settings.lending_asset_symbol_map

    if asset_upper in symbol_map:
        aave_asset = symbol_map[asset_upper]
    else:
        # Check if it's already an Aave symbol
        if asset_upper in settings.lending_assets_list:
            aave_asset = asset_upper
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset '{asset}' not found. Available assets: {', '.join(settings.lending_assets_list)}",
            )

    try:
        # Query lending data from database
        rows = await get_lending_data(
            asset=aave_asset,
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
                    supply_rate_ray=str(row["supply_rate_ray"]),
                    supply_apy_percent=supply_apy,
                    variable_borrow_rate_ray=str(row["variable_borrow_rate_ray"]),
                    variable_borrow_apy_percent=variable_borrow_apy,
                    stable_borrow_rate_ray=str(row["stable_borrow_rate_ray"]),
                    stable_borrow_apy_percent=stable_borrow_apy,
                    total_supplied=row["total_supplied"],
                    available_liquidity=row["available_liquidity"],
                    total_borrowed=row["total_borrowed"],
                    utilization_rate=row["utilization_rate"],
                    price_eth=row["price_eth"],
                    price_usd=row["price_usd"],
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
            asset=aave_asset,
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
