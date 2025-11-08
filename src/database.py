"""Database connection pool and operations using asyncpg."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncIterator

import asyncpg
from loguru import logger

from src.config import settings

# Global connection pool
_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    """Initialize the database connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    logger.info(f"Initializing database connection pool: {settings.database_url_str}")
    _pool = await asyncpg.create_pool(
        settings.database_url_str,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )
    logger.info("Database connection pool initialized")
    return _pool


async def close_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing database connection pool")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


def get_pool() -> asyncpg.Pool:
    """Get the global connection pool (must be initialized first)."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncIterator[asyncpg.Connection]:
    """Get a database connection from the pool."""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


async def init_schema() -> None:
    """Initialize database schema (tables and indexes)."""
    logger.info("Initializing database schema")

    create_spot_ohlcv_table = """
    CREATE TABLE IF NOT EXISTS spot_ohlcv (
        id SERIAL PRIMARY KEY,
        asset VARCHAR(20) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        open NUMERIC(20, 8) NOT NULL,
        high NUMERIC(20, 8) NOT NULL,
        low NUMERIC(20, 8) NOT NULL,
        close NUMERIC(20, 8) NOT NULL,
        volume NUMERIC(30, 8) NOT NULL,
        UNIQUE(asset, timestamp)
    );
    """

    create_spot_ohlcv_index = """
    CREATE INDEX IF NOT EXISTS idx_asset_timestamp
    ON spot_ohlcv(asset, timestamp DESC);
    """

    create_backfill_state_table = """
    CREATE TABLE IF NOT EXISTS backfill_state (
        asset VARCHAR(20) PRIMARY KEY,
        completed BOOLEAN DEFAULT FALSE,
        last_fetched_timestamp TIMESTAMPTZ,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """

    async with get_connection() as conn:
        await conn.execute(create_spot_ohlcv_table)
        await conn.execute(create_spot_ohlcv_index)
        await conn.execute(create_backfill_state_table)

    # Initialize futures and lending schemas
    await init_futures_schemas()
    await init_lending_schemas()

    logger.info("Database schema initialized successfully")


async def health_check() -> bool:
    """Check database connection health."""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# ==================== CRUD Operations ====================


async def upsert_ohlcv_batch(asset: str, candles: list[dict]) -> int:
    """
    Insert or update OHLCV candles for an asset using efficient batch operations.

    Args:
        asset: Asset symbol (e.g., 'BTC')
        candles: List of dicts with keys: timestamp, open, high, low, close, volume

    Returns:
        Number of rows inserted/updated
    """
    if not candles:
        return 0

    query = """
    INSERT INTO spot_ohlcv (asset, timestamp, open, high, low, close, volume)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (asset, timestamp)
    DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume
    """

    # Prepare batch data
    batch_data = [
        (
            asset,
            candle["timestamp"],
            candle["open"],
            candle["high"],
            candle["low"],
            candle["close"],
            candle["volume"],
        )
        for candle in candles
    ]

    async with get_connection() as conn:
        async with conn.transaction():
            try:
                # Use executemany for batch insert
                await conn.executemany(query, batch_data)
                return len(candles)

            except Exception as e:
                logger.error(f"Batch upsert failed for {asset}: {e}")
                raise


async def get_ohlcv_data(
    asset: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    Retrieve OHLCV data for an asset.

    Args:
        asset: Asset symbol
        start_time: Start timestamp (inclusive)
        end_time: End timestamp (inclusive)
        limit: Maximum number of rows to return

    Returns:
        List of dicts with OHLCV data
    """
    query_parts = ["SELECT timestamp, open, high, low, close, volume FROM spot_ohlcv WHERE asset = $1"]
    params = [asset]
    param_idx = 2

    if start_time:
        query_parts.append(f"AND timestamp >= ${param_idx}")
        params.append(start_time)
        param_idx += 1

    if end_time:
        query_parts.append(f"AND timestamp <= ${param_idx}")
        params.append(end_time)
        param_idx += 1

    query_parts.append("ORDER BY timestamp ASC")

    if limit:
        query_parts.append(f"LIMIT ${param_idx}")
        params.append(limit)

    query = " ".join(query_parts)

    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def get_latest_timestamp(asset: str) -> datetime | None:
    """Get the latest (most recent) timestamp for an asset."""
    query = "SELECT MAX(timestamp) FROM spot_ohlcv WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result


async def get_earliest_timestamp(asset: str) -> datetime | None:
    """Get the earliest (oldest) timestamp for an asset."""
    query = "SELECT MIN(timestamp) FROM spot_ohlcv WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result


async def get_candle_count(asset: str) -> int:
    """Get the total number of candles for an asset."""
    query = "SELECT COUNT(*) FROM spot_ohlcv WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result or 0


async def detect_gaps(asset: str, interval_hours: int = 12) -> list[tuple[datetime, datetime]]:
    """
    Detect missing candles (gaps) in the data for an asset.

    Args:
        asset: Asset symbol
        interval_hours: Expected interval between candles (default 12h)

    Returns:
        List of (gap_start, gap_end) tuples representing missing data ranges
    """
    earliest = await get_earliest_timestamp(asset)
    latest = await get_latest_timestamp(asset)

    if earliest is None or latest is None:
        return []

    # Generate expected timestamp series
    interval_delta = timedelta(hours=interval_hours)
    expected_timestamps = []
    current = earliest
    while current <= latest:
        expected_timestamps.append(current)
        current += interval_delta

    # Query actual timestamps
    query = "SELECT timestamp FROM spot_ohlcv WHERE asset = $1 ORDER BY timestamp ASC"
    async with get_connection() as conn:
        rows = await conn.fetch(query, asset)
        actual_timestamps = {row["timestamp"] for row in rows}

    # Find missing timestamps
    missing = [ts for ts in expected_timestamps if ts not in actual_timestamps]

    if not missing:
        return []

    # Group consecutive missing timestamps into ranges
    gaps = []
    gap_start = missing[0]
    gap_end = missing[0]

    for i in range(1, len(missing)):
        if missing[i] - gap_end == interval_delta:
            # Consecutive gap, extend current range
            gap_end = missing[i]
        else:
            # Non-consecutive, finalize current gap and start new one
            gaps.append((gap_start, gap_end))
            gap_start = missing[i]
            gap_end = missing[i]

    # Add the final gap
    gaps.append((gap_start, gap_end))

    return gaps


# ==================== Backfill State Management ====================


async def get_backfill_state(asset: str) -> dict | None:
    """Get backfill state for an asset."""
    query = "SELECT * FROM backfill_state WHERE asset = $1"
    async with get_connection() as conn:
        row = await conn.fetchrow(query, asset)
        return dict(row) if row else None


async def update_backfill_state(
    asset: str, completed: bool, last_fetched_timestamp: datetime | None = None
) -> None:
    """Update or insert backfill state for an asset."""
    query = """
    INSERT INTO backfill_state (asset, completed, last_fetched_timestamp, updated_at)
    VALUES ($1, $2, $3, NOW())
    ON CONFLICT (asset)
    DO UPDATE SET
        completed = EXCLUDED.completed,
        last_fetched_timestamp = EXCLUDED.last_fetched_timestamp,
        updated_at = NOW()
    """
    async with get_connection() as conn:
        await conn.execute(query, asset, completed, last_fetched_timestamp)


async def is_backfill_completed(asset: str) -> bool:
    """Check if initial backfill is completed for an asset."""
    state = await get_backfill_state(asset)
    return state is not None and state.get("completed", False)


# ==================== Futures Schema Initialization ====================


async def init_futures_schemas() -> None:
    """Initialize all futures-related database schemas."""
    logger.info("Initializing futures database schemas")

    # Funding rates table
    create_funding_rates_table = """
    CREATE TABLE IF NOT EXISTS futures_funding_rates (
        id SERIAL PRIMARY KEY,
        asset VARCHAR(20) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        funding_rate NUMERIC(20, 8) NOT NULL,
        mark_price NUMERIC(20, 8),
        UNIQUE(asset, timestamp)
    );
    """

    create_funding_rates_index = """
    CREATE INDEX IF NOT EXISTS idx_funding_rates
    ON futures_funding_rates(asset, timestamp DESC);
    """

    # Mark price klines table
    create_mark_klines_table = """
    CREATE TABLE IF NOT EXISTS futures_mark_price_klines (
        id SERIAL PRIMARY KEY,
        asset VARCHAR(20) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        open NUMERIC(20, 8) NOT NULL,
        high NUMERIC(20, 8) NOT NULL,
        low NUMERIC(20, 8) NOT NULL,
        close NUMERIC(20, 8) NOT NULL,
        UNIQUE(asset, timestamp)
    );
    """

    create_mark_klines_index = """
    CREATE INDEX IF NOT EXISTS idx_mark_klines
    ON futures_mark_price_klines(asset, timestamp DESC);
    """

    # Index price klines table
    create_index_klines_table = """
    CREATE TABLE IF NOT EXISTS futures_index_price_klines (
        id SERIAL PRIMARY KEY,
        asset VARCHAR(20) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        open NUMERIC(20, 8) NOT NULL,
        high NUMERIC(20, 8) NOT NULL,
        low NUMERIC(20, 8) NOT NULL,
        close NUMERIC(20, 8) NOT NULL,
        UNIQUE(asset, timestamp)
    );
    """

    create_index_klines_index = """
    CREATE INDEX IF NOT EXISTS idx_index_klines
    ON futures_index_price_klines(asset, timestamp DESC);
    """

    # Open interest table
    create_open_interest_table = """
    CREATE TABLE IF NOT EXISTS futures_open_interest (
        id SERIAL PRIMARY KEY,
        asset VARCHAR(20) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        open_interest NUMERIC(30, 8) NOT NULL,
        UNIQUE(asset, timestamp)
    );
    """

    create_open_interest_index = """
    CREATE INDEX IF NOT EXISTS idx_open_interest
    ON futures_open_interest(asset, timestamp DESC);
    """

    # Futures backfill state table
    create_futures_backfill_table = """
    CREATE TABLE IF NOT EXISTS futures_backfill_state (
        asset VARCHAR(20) NOT NULL,
        metric_type VARCHAR(50) NOT NULL,
        completed BOOLEAN DEFAULT FALSE,
        last_fetched_timestamp TIMESTAMPTZ,
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY(asset, metric_type)
    );
    """

    async with get_connection() as conn:
        # Funding rates
        await conn.execute(create_funding_rates_table)
        await conn.execute(create_funding_rates_index)

        # Mark price klines
        await conn.execute(create_mark_klines_table)
        await conn.execute(create_mark_klines_index)

        # Index price klines
        await conn.execute(create_index_klines_table)
        await conn.execute(create_index_klines_index)

        # Open interest
        await conn.execute(create_open_interest_table)
        await conn.execute(create_open_interest_index)

        # Backfill state
        await conn.execute(create_futures_backfill_table)

    logger.info("Futures database schemas initialized successfully")


# ==================== Futures CRUD Operations ====================


async def upsert_funding_rates_batch(asset: str, rates: list[dict]) -> int:
    """Insert or update funding rates in batch."""
    if not rates:
        return 0

    query = """
    INSERT INTO futures_funding_rates (asset, timestamp, funding_rate, mark_price)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (asset, timestamp)
    DO UPDATE SET
        funding_rate = EXCLUDED.funding_rate,
        mark_price = EXCLUDED.mark_price
    """

    batch_data = [
        (asset, rate["timestamp"], rate["funding_rate"], rate.get("mark_price"))
        for rate in rates
    ]

    async with get_connection() as conn:
        async with conn.transaction():
            await conn.executemany(query, batch_data)
            return len(rates)


async def upsert_mark_klines_batch(asset: str, candles: list[dict]) -> int:
    """Insert or update mark price klines in batch."""
    if not candles:
        return 0

    query = """
    INSERT INTO futures_mark_price_klines (asset, timestamp, open, high, low, close)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (asset, timestamp)
    DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close
    """

    batch_data = [
        (asset, c["timestamp"], c["open"], c["high"], c["low"], c["close"])
        for c in candles
    ]

    async with get_connection() as conn:
        async with conn.transaction():
            await conn.executemany(query, batch_data)
            return len(candles)


async def upsert_index_klines_batch(asset: str, candles: list[dict]) -> int:
    """Insert or update index price klines in batch."""
    if not candles:
        return 0

    query = """
    INSERT INTO futures_index_price_klines (asset, timestamp, open, high, low, close)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (asset, timestamp)
    DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close
    """

    batch_data = [
        (asset, c["timestamp"], c["open"], c["high"], c["low"], c["close"])
        for c in candles
    ]

    async with get_connection() as conn:
        async with conn.transaction():
            await conn.executemany(query, batch_data)
            return len(candles)


async def upsert_open_interest_batch(asset: str, data_points: list[dict]) -> int:
    """Insert or update open interest data in batch."""
    if not data_points:
        return 0

    query = """
    INSERT INTO futures_open_interest (asset, timestamp, open_interest)
    VALUES ($1, $2, $3)
    ON CONFLICT (asset, timestamp)
    DO UPDATE SET
        open_interest = EXCLUDED.open_interest
    """

    batch_data = [
        (asset, dp["timestamp"], dp["open_interest"])
        for dp in data_points
    ]

    async with get_connection() as conn:
        async with conn.transaction():
            await conn.executemany(query, batch_data)
            return len(data_points)


async def get_funding_rates(
    asset: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Retrieve funding rate data for an asset."""
    query_parts = ["SELECT timestamp, funding_rate, mark_price FROM futures_funding_rates WHERE asset = $1"]
    params = [asset]
    param_idx = 2

    if start_time:
        query_parts.append(f"AND timestamp >= ${param_idx}")
        params.append(start_time)
        param_idx += 1

    if end_time:
        query_parts.append(f"AND timestamp <= ${param_idx}")
        params.append(end_time)
        param_idx += 1

    query_parts.append("ORDER BY timestamp ASC")

    if limit:
        query_parts.append(f"LIMIT ${param_idx}")
        params.append(limit)

    query = " ".join(query_parts)

    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def get_mark_klines(
    asset: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Retrieve mark price klines for an asset."""
    query_parts = ["SELECT timestamp, open, high, low, close FROM futures_mark_price_klines WHERE asset = $1"]
    params = [asset]
    param_idx = 2

    if start_time:
        query_parts.append(f"AND timestamp >= ${param_idx}")
        params.append(start_time)
        param_idx += 1

    if end_time:
        query_parts.append(f"AND timestamp <= ${param_idx}")
        params.append(end_time)
        param_idx += 1

    query_parts.append("ORDER BY timestamp ASC")

    if limit:
        query_parts.append(f"LIMIT ${param_idx}")
        params.append(limit)

    query = " ".join(query_parts)

    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def get_index_klines(
    asset: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Retrieve index price klines for an asset."""
    query_parts = ["SELECT timestamp, open, high, low, close FROM futures_index_price_klines WHERE asset = $1"]
    params = [asset]
    param_idx = 2

    if start_time:
        query_parts.append(f"AND timestamp >= ${param_idx}")
        params.append(start_time)
        param_idx += 1

    if end_time:
        query_parts.append(f"AND timestamp <= ${param_idx}")
        params.append(end_time)
        param_idx += 1

    query_parts.append("ORDER BY timestamp ASC")

    if limit:
        query_parts.append(f"LIMIT ${param_idx}")
        params.append(limit)

    query = " ".join(query_parts)

    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def get_open_interest(
    asset: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Retrieve open interest data for an asset."""
    query_parts = ["SELECT timestamp, open_interest FROM futures_open_interest WHERE asset = $1"]
    params = [asset]
    param_idx = 2

    if start_time:
        query_parts.append(f"AND timestamp >= ${param_idx}")
        params.append(start_time)
        param_idx += 1

    if end_time:
        query_parts.append(f"AND timestamp <= ${param_idx}")
        params.append(end_time)
        param_idx += 1

    query_parts.append("ORDER BY timestamp ASC")

    if limit:
        query_parts.append(f"LIMIT ${param_idx}")
        params.append(limit)

    query = " ".join(query_parts)

    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def get_latest_futures_timestamp(asset: str, metric_type: str) -> datetime | None:
    """Get the latest timestamp for a futures metric type."""
    table_map = {
        "funding_rate": "futures_funding_rates",
        "mark_klines": "futures_mark_price_klines",
        "index_klines": "futures_index_price_klines",
        "open_interest": "futures_open_interest",
    }

    table_name = table_map.get(metric_type)
    if not table_name:
        raise ValueError(f"Invalid metric_type: {metric_type}")

    query = f"SELECT MAX(timestamp) FROM {table_name} WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result


async def get_earliest_futures_timestamp(asset: str, metric_type: str) -> datetime | None:
    """Get the earliest timestamp for a futures metric type."""
    table_map = {
        "funding_rate": "futures_funding_rates",
        "mark_klines": "futures_mark_price_klines",
        "index_klines": "futures_index_price_klines",
        "open_interest": "futures_open_interest",
    }

    table_name = table_map.get(metric_type)
    if not table_name:
        raise ValueError(f"Invalid metric_type: {metric_type}")

    query = f"SELECT MIN(timestamp) FROM {table_name} WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result


async def get_futures_data_count(asset: str, metric_type: str) -> int:
    """Get the total count of data points for a futures metric type."""
    table_map = {
        "funding_rate": "futures_funding_rates",
        "mark_klines": "futures_mark_price_klines",
        "index_klines": "futures_index_price_klines",
        "open_interest": "futures_open_interest",
    }

    table_name = table_map.get(metric_type)
    if not table_name:
        raise ValueError(f"Invalid metric_type: {metric_type}")

    query = f"SELECT COUNT(*) FROM {table_name} WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result or 0


async def detect_futures_gaps(asset: str, metric_type: str, interval_hours: int) -> list[tuple[datetime, datetime]]:
    """Detect gaps in futures data for a specific metric type."""
    earliest = await get_earliest_futures_timestamp(asset, metric_type)
    latest = await get_latest_futures_timestamp(asset, metric_type)

    if earliest is None or latest is None:
        return []

    # Generate expected timestamps
    interval_delta = timedelta(hours=interval_hours)
    expected_timestamps = []
    current = earliest
    while current <= latest:
        expected_timestamps.append(current)
        current += interval_delta

    # Query actual timestamps
    table_map = {
        "funding_rate": "futures_funding_rates",
        "mark_klines": "futures_mark_price_klines",
        "index_klines": "futures_index_price_klines",
        "open_interest": "futures_open_interest",
    }

    table_name = table_map.get(metric_type)
    if not table_name:
        raise ValueError(f"Invalid metric_type: {metric_type}")

    query = f"SELECT timestamp FROM {table_name} WHERE asset = $1 ORDER BY timestamp ASC"
    async with get_connection() as conn:
        rows = await conn.fetch(query, asset)
        actual_timestamps = {row["timestamp"] for row in rows}

    # Find missing timestamps
    missing = [ts for ts in expected_timestamps if ts not in actual_timestamps]

    if not missing:
        return []

    # Group consecutive missing timestamps into ranges
    gaps = []
    gap_start = missing[0]
    gap_end = missing[0]

    for i in range(1, len(missing)):
        if missing[i] - gap_end == interval_delta:
            gap_end = missing[i]
        else:
            gaps.append((gap_start, gap_end))
            gap_start = missing[i]
            gap_end = missing[i]

    gaps.append((gap_start, gap_end))
    return gaps


# ==================== Futures Backfill State Management ====================


async def get_futures_backfill_state(asset: str, metric_type: str) -> dict | None:
    """Get backfill state for a futures metric."""
    query = "SELECT * FROM futures_backfill_state WHERE asset = $1 AND metric_type = $2"
    async with get_connection() as conn:
        row = await conn.fetchrow(query, asset, metric_type)
        return dict(row) if row else None


async def update_futures_backfill_state(
    asset: str,
    metric_type: str,
    completed: bool,
    last_fetched_timestamp: datetime | None = None,
) -> None:
    """Update or insert backfill state for a futures metric."""
    query = """
    INSERT INTO futures_backfill_state (asset, metric_type, completed, last_fetched_timestamp, updated_at)
    VALUES ($1, $2, $3, $4, NOW())
    ON CONFLICT (asset, metric_type)
    DO UPDATE SET
        completed = EXCLUDED.completed,
        last_fetched_timestamp = EXCLUDED.last_fetched_timestamp,
        updated_at = NOW()
    """
    async with get_connection() as conn:
        await conn.execute(query, asset, metric_type, completed, last_fetched_timestamp)


async def is_futures_backfill_completed(asset: str, metric_type: str) -> bool:
    """Check if backfill is completed for a futures metric."""
    state = await get_futures_backfill_state(asset, metric_type)
    return state is not None and state.get("completed", False)


# ==================== Lending Schema Initialization ====================


async def init_lending_schemas() -> None:
    """Initialize all lending-related database schemas."""
    logger.info("Initializing lending database schemas")

    # Lendings table (event-based data from Aave)
    create_lendings_table = """
    CREATE TABLE IF NOT EXISTS lendings (
        id SERIAL PRIMARY KEY,
        asset VARCHAR(20) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        supply_rate_ray NUMERIC(80, 27) NOT NULL,
        variable_borrow_rate_ray NUMERIC(80, 27) NOT NULL,
        stable_borrow_rate_ray NUMERIC(80, 27) NOT NULL,
        total_supplied NUMERIC(30, 8) NOT NULL,
        available_liquidity NUMERIC(30, 8) NOT NULL,
        total_borrowed NUMERIC(30, 8) NOT NULL,
        utilization_rate NUMERIC(10, 8) NOT NULL,
        price_eth NUMERIC(20, 8),
        price_usd NUMERIC(20, 8),
        UNIQUE(asset, timestamp)
    );
    """

    create_lendings_index = """
    CREATE INDEX IF NOT EXISTS idx_lendings_asset_timestamp
    ON lendings(asset, timestamp DESC);
    """

    # Lending backfill state table
    create_lending_backfill_table = """
    CREATE TABLE IF NOT EXISTS lending_backfill_state (
        asset VARCHAR(20) PRIMARY KEY,
        completed BOOLEAN DEFAULT FALSE,
        last_fetched_timestamp TIMESTAMPTZ,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """

    async with get_connection() as conn:
        await conn.execute(create_lendings_table)
        await conn.execute(create_lendings_index)
        await conn.execute(create_lending_backfill_table)

    logger.info("Lending database schemas initialized successfully")


# ==================== Lending Data Validation ====================


def validate_lending_data(data: dict) -> bool:
    """
    Validate lending data for sanity checks.

    Args:
        data: Dict with lending data fields

    Returns:
        True if valid, False otherwise

    Raises:
        ValueError: If validation fails with details
    """
    try:
        # Rates must be non-negative
        if float(data["supply_rate_ray"]) < 0:
            raise ValueError("Supply rate cannot be negative")
        if float(data["variable_borrow_rate_ray"]) < 0:
            raise ValueError("Variable borrow rate cannot be negative")
        if float(data["stable_borrow_rate_ray"]) < 0:
            raise ValueError("Stable borrow rate cannot be negative")

        # Utilization rate must be between 0 and 1
        util_rate = float(data["utilization_rate"])
        if not 0 <= util_rate <= 1:
            raise ValueError(f"Utilization rate must be 0-1, got {util_rate}")

        # Total borrowed cannot exceed total supplied
        total_supplied = float(data["total_supplied"])
        total_borrowed = float(data["total_borrowed"])
        # Use relative tolerance (0.01% of supply)
        tolerance = max(total_supplied * 0.0001, 0.01)  # At least 0.01 for small pools
        if total_borrowed > total_supplied + tolerance:
            raise ValueError(f"Total borrowed ({total_borrowed}) exceeds total supplied ({total_supplied})")

        # Amounts must be non-negative
        if total_supplied < 0:
            raise ValueError("Total supplied cannot be negative")
        if total_borrowed < 0:
            raise ValueError("Total borrowed cannot be negative")
        if float(data["available_liquidity"]) < 0:
            raise ValueError("Available liquidity cannot be negative")

        return True
    except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"Lending data validation failed: {e}")
        raise


# ==================== Lending CRUD Operations ====================


async def upsert_lending_batch(asset: str, events: list[dict]) -> int:
    """
    Insert or update lending events for an asset using efficient batch operations.

    Args:
        asset: Asset symbol (e.g., 'WETH', 'WBTC', 'USDC')
        events: List of dicts with lending data fields

    Returns:
        Number of rows inserted/updated
    """
    if not events:
        return 0

    # Validate all events before inserting
    for event in events:
        validate_lending_data(event)

    query = """
    INSERT INTO lendings (
        asset, timestamp, supply_rate_ray, variable_borrow_rate_ray, stable_borrow_rate_ray,
        total_supplied, available_liquidity, total_borrowed, utilization_rate,
        price_eth, price_usd
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    ON CONFLICT (asset, timestamp)
    DO UPDATE SET
        supply_rate_ray = EXCLUDED.supply_rate_ray,
        variable_borrow_rate_ray = EXCLUDED.variable_borrow_rate_ray,
        stable_borrow_rate_ray = EXCLUDED.stable_borrow_rate_ray,
        total_supplied = EXCLUDED.total_supplied,
        available_liquidity = EXCLUDED.available_liquidity,
        total_borrowed = EXCLUDED.total_borrowed,
        utilization_rate = EXCLUDED.utilization_rate,
        price_eth = EXCLUDED.price_eth,
        price_usd = EXCLUDED.price_usd
    """

    # Prepare batch data
    batch_data = [
        (
            asset,
            event["timestamp"],
            event["supply_rate_ray"],
            event["variable_borrow_rate_ray"],
            event["stable_borrow_rate_ray"],
            event["total_supplied"],
            event["available_liquidity"],
            event["total_borrowed"],
            event["utilization_rate"],
            event.get("price_eth"),
            event.get("price_usd"),
        )
        for event in events
    ]

    async with get_connection() as conn:
        async with conn.transaction():
            try:
                await conn.executemany(query, batch_data)
                return len(events)
            except Exception as e:
                logger.error(f"Batch upsert failed for lending data {asset}: {e}")
                raise


async def get_lending_data(
    asset: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    Retrieve lending data for an asset.

    Args:
        asset: Asset symbol
        start_time: Start timestamp (inclusive)
        end_time: End timestamp (inclusive)
        limit: Maximum number of rows to return

    Returns:
        List of dicts with lending data (all fields including RAY rates)
    """
    query_parts = [
        """SELECT timestamp, supply_rate_ray, variable_borrow_rate_ray, stable_borrow_rate_ray,
        total_supplied, available_liquidity, total_borrowed, utilization_rate,
        price_eth, price_usd
        FROM lendings WHERE asset = $1"""
    ]
    params = [asset]
    param_idx = 2

    if start_time:
        query_parts.append(f"AND timestamp >= ${param_idx}")
        params.append(start_time)
        param_idx += 1

    if end_time:
        query_parts.append(f"AND timestamp <= ${param_idx}")
        params.append(end_time)
        param_idx += 1

    query_parts.append("ORDER BY timestamp ASC")

    if limit:
        query_parts.append(f"LIMIT ${param_idx}")
        params.append(limit)

    query = " ".join(query_parts)

    async with get_connection() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def get_latest_lending_timestamp(asset: str) -> datetime | None:
    """Get the latest (most recent) timestamp for lending data for an asset."""
    query = "SELECT MAX(timestamp) FROM lendings WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result


async def get_earliest_lending_timestamp(asset: str) -> datetime | None:
    """Get the earliest (oldest) timestamp for lending data for an asset."""
    query = "SELECT MIN(timestamp) FROM lendings WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result


async def get_lending_event_count(asset: str) -> int:
    """Get the total number of lending events for an asset."""
    query = "SELECT COUNT(*) FROM lendings WHERE asset = $1"
    async with get_connection() as conn:
        result = await conn.fetchval(query, asset)
        return result or 0


# ==================== Lending Backfill State Management ====================


async def get_lending_backfill_state(asset: str) -> dict | None:
    """Get backfill state for a lending asset."""
    query = "SELECT * FROM lending_backfill_state WHERE asset = $1"
    async with get_connection() as conn:
        row = await conn.fetchrow(query, asset)
        return dict(row) if row else None


async def update_lending_backfill_state(
    asset: str, completed: bool, last_fetched_timestamp: datetime | None = None
) -> None:
    """Update or insert backfill state for a lending asset."""
    query = """
    INSERT INTO lending_backfill_state (asset, completed, last_fetched_timestamp, updated_at)
    VALUES ($1, $2, $3, NOW())
    ON CONFLICT (asset)
    DO UPDATE SET
        completed = EXCLUDED.completed,
        last_fetched_timestamp = EXCLUDED.last_fetched_timestamp,
        updated_at = NOW()
    """
    async with get_connection() as conn:
        await conn.execute(query, asset, completed, last_fetched_timestamp)


async def is_lending_backfill_completed(asset: str) -> bool:
    """Check if initial backfill is completed for a lending asset."""
    state = await get_lending_backfill_state(asset)
    return state is not None and state.get("completed", False)
