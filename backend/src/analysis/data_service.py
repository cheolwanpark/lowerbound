"""Data fetching and time series alignment for risk analysis."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from loguru import logger

from src import database


async def fetch_portfolio_data(
    assets: list[str], lookback_days: int
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame], int]:
    """
    Fetch historical spot, futures, and lending data for multiple assets concurrently.

    Args:
        assets: List of asset symbols (e.g., ['BTC', 'ETH'])
        lookback_days: Number of days to look back

    Returns:
        Tuple of (spot_data_dict, futures_data_dict, lending_data_dict, actual_days_available)
        - spot_data_dict: {asset: DataFrame with columns [timestamp, close]}
        - futures_data_dict: {asset: DataFrame with columns [timestamp, mark_price, funding_rate]}
        - lending_data_dict: {asset: DataFrame with lending rates and indices}
        - actual_days_available: Minimum days available across all assets
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=lookback_days)

    logger.info(f"Fetching {lookback_days} days of data for assets: {assets}")
    logger.info(f"Date range: {start_time} to {end_time}")

    # Fetch spot data for all assets concurrently
    spot_tasks = [
        database.get_ohlcv_data(asset, start_time, end_time) for asset in assets
    ]
    spot_results = await asyncio.gather(*spot_tasks, return_exceptions=True)

    # Fetch futures data (mark prices and funding rates) concurrently
    mark_price_tasks = [
        database.get_mark_klines(asset, start_time, end_time) for asset in assets
    ]
    funding_rate_tasks = [
        database.get_funding_rates(asset, start_time, end_time) for asset in assets
    ]

    # Fetch lending data concurrently
    lending_tasks = [
        database.get_lending_data(asset, start_time, end_time) for asset in assets
    ]

    mark_price_results, funding_rate_results, lending_results = await asyncio.gather(
        asyncio.gather(*mark_price_tasks, return_exceptions=True),
        asyncio.gather(*funding_rate_tasks, return_exceptions=True),
        asyncio.gather(*lending_tasks, return_exceptions=True),
    )

    # Process spot data
    spot_data_dict = {}
    for asset, result in zip(assets, spot_results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch spot data for {asset}: {result}")
            continue

        if not result:
            logger.warning(f"No spot data available for {asset}")
            continue

        df = pd.DataFrame(result)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        # Convert Decimal to float, coerce errors to NaN
        df["close"] = pd.to_numeric(df["close"], errors='coerce')
        # Drop rows with NaN prices (invalid data)
        df = df.dropna(subset=["close"])
        df = df[["timestamp", "close"]].sort_values("timestamp")
        spot_data_dict[asset] = df
        logger.info(f"Fetched {len(df)} spot candles for {asset}")

    # Process futures data
    futures_data_dict = {}
    for asset, mark_result, funding_result in zip(
        assets, mark_price_results, funding_rate_results
    ):
        if isinstance(mark_result, Exception) or isinstance(funding_result, Exception):
            logger.warning(
                f"Failed to fetch futures data for {asset}: mark={mark_result}, funding={funding_result}"
            )
            continue

        if not mark_result:
            logger.warning(f"No mark price data available for {asset}")
            continue

        # Process mark prices
        mark_df = pd.DataFrame(mark_result)
        mark_df["timestamp"] = pd.to_datetime(mark_df["timestamp"])
        # Convert Decimal to float, coerce errors to NaN
        mark_df["close"] = pd.to_numeric(mark_df["close"], errors='coerce')
        # Drop rows with NaN prices (invalid data)
        mark_df = mark_df.dropna(subset=["close"])
        mark_df = mark_df[["timestamp", "close"]].rename(columns={"close": "mark_price"})

        # Process funding rates
        funding_df = pd.DataFrame(funding_result) if funding_result else pd.DataFrame()
        if not funding_df.empty:
            funding_df["timestamp"] = pd.to_datetime(funding_df["timestamp"])
            # Convert Decimal to float and fill NULL values with 0.0 (neutral funding rate)
            funding_df["funding_rate"] = pd.to_numeric(funding_df["funding_rate"], errors='coerce').fillna(0.0)
            funding_df = funding_df[["timestamp", "funding_rate"]]

            # Merge mark prices and funding rates
            futures_df = pd.merge(mark_df, funding_df, on="timestamp", how="left")
            # Fill any remaining NaN funding rates with 0.0
            futures_df["funding_rate"] = futures_df["funding_rate"].fillna(0.0)
        else:
            futures_df = mark_df
            futures_df["funding_rate"] = 0.0  # Default to 0 if no funding data

        futures_df = futures_df.sort_values("timestamp")
        futures_data_dict[asset] = futures_df
        logger.info(
            f"Fetched {len(mark_df)} mark prices and {len(funding_df)} funding rates for {asset}"
        )

    # Process lending data
    lending_data_dict = {}
    for asset, result in zip(assets, lending_results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch lending data for {asset}: {result}")
            continue

        if not result:
            logger.debug(f"No lending data available for {asset}")
            continue

        df = pd.DataFrame(result)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        # Keep relevant lending columns: supply_rate_ray, variable_borrow_rate_ray,
        # stable_borrow_rate_ray, liquidity_index, variable_borrow_index
        required_cols = ["timestamp"]
        optional_cols = [
            "supply_rate_ray",
            "variable_borrow_rate_ray",
            "stable_borrow_rate_ray",
            "liquidity_index",
            "variable_borrow_index",
        ]
        available_cols = [col for col in optional_cols if col in df.columns]

        # Convert Decimal columns to float, coerce errors to NaN, fill with 0
        for col in available_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        df = df[required_cols + available_cols].sort_values("timestamp")
        lending_data_dict[asset] = df
        logger.info(f"Fetched {len(df)} lending data points for {asset}")

    # Calculate actual days available (minimum across all assets)
    min_days = lookback_days
    if spot_data_dict:
        for asset, df in spot_data_dict.items():
            days_available = (df["timestamp"].max() - df["timestamp"].min()).days
            min_days = min(min_days, days_available)

    logger.info(f"Actual data availability: {min_days} days")

    return spot_data_dict, futures_data_dict, lending_data_dict, min_days


def resample_to_daily(
    spot_data: dict[str, pd.DataFrame],
    futures_data: dict[str, pd.DataFrame],
    lending_data: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """
    Resample 12h spot OHLCV, 8h futures data, and lending data to daily (24h) intervals.

    Args:
        spot_data: Dict of {asset: DataFrame with 12h interval data}
        futures_data: Dict of {asset: DataFrame with 8h interval data}
        lending_data: Dict of {asset: DataFrame with lending data}

    Returns:
        Tuple of (daily_spot_data, daily_futures_data, daily_lending_data)
    """
    logger.info("Resampling data to daily intervals")

    daily_spot = {}
    for asset, df in spot_data.items():
        if df.empty:
            continue

        # Resample to daily, taking the last close price of each day
        df_copy = df.copy()
        df_copy.set_index("timestamp", inplace=True)
        daily = df_copy.resample("D")["close"].last()
        daily = daily.dropna()

        daily_df = pd.DataFrame({"timestamp": daily.index, "close": daily.values})
        daily_spot[asset] = daily_df
        logger.debug(
            f"Resampled {asset} spot: {len(df)} -> {len(daily_df)} daily candles"
        )

    daily_futures = {}
    for asset, df in futures_data.items():
        if df.empty:
            continue

        df_copy = df.copy()
        df_copy.set_index("timestamp", inplace=True)

        # Resample mark price (take last of day)
        daily_mark = df_copy.resample("D")["mark_price"].last()

        # Resample funding rate (take mean of day, as it's a rate)
        daily_funding = df_copy.resample("D")["funding_rate"].mean()

        daily_df = pd.DataFrame(
            {
                "timestamp": daily_mark.index,
                "mark_price": daily_mark.values,
                "funding_rate": daily_funding.values,
            }
        )
        daily_df = daily_df.dropna()
        daily_futures[asset] = daily_df
        logger.debug(
            f"Resampled {asset} futures: {len(df)} -> {len(daily_df)} daily data points"
        )

    # Resample lending data
    daily_lending = {}
    for asset, df in lending_data.items():
        if df.empty:
            continue

        df_copy = df.copy()
        df_copy.set_index("timestamp", inplace=True)

        # Resample lending metrics (take last value of each day for indices and rates)
        daily_data = {}
        for col in df_copy.columns:
            daily_data[col] = df_copy.resample("D")[col].last()

        # Create DataFrame
        daily_df = pd.DataFrame(daily_data)
        daily_df["timestamp"] = daily_df.index
        daily_df = daily_df.dropna(how="all", subset=[c for c in daily_df.columns if c != "timestamp"])
        daily_df = daily_df.reset_index(drop=True)

        if not daily_df.empty:
            daily_lending[asset] = daily_df
            logger.debug(
                f"Resampled {asset} lending: {len(df)} -> {len(daily_df)} daily data points"
            )

    return daily_spot, daily_futures, daily_lending


def align_time_series(
    spot_data: dict[str, pd.DataFrame],
    futures_data: dict[str, pd.DataFrame],
    lending_data: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, list[str]]:
    """
    Align spot, futures, and lending time series to common timestamps with forward-fill.

    Args:
        spot_data: Dict of {asset: DataFrame with daily spot prices}
        futures_data: Dict of {asset: DataFrame with daily futures data}
        lending_data: Dict of {asset: DataFrame with daily lending data}

    Returns:
        Tuple of (aligned_df, warnings)
        - aligned_df: Multi-column DataFrame with columns: timestamp, {asset}_spot, {asset}_futures_mark,
                      {asset}_funding, {asset}_liquidity_index, {asset}_variable_borrow_index, etc.
        - warnings: List of warning messages about data gaps
    """
    logger.info("Aligning time series across assets")

    warnings = []

    # Combine all timestamps from all assets
    all_timestamps = set()
    for df in spot_data.values():
        all_timestamps.update(df["timestamp"])
    for df in futures_data.values():
        all_timestamps.update(df["timestamp"])
    for df in lending_data.values():
        all_timestamps.update(df["timestamp"])

    if not all_timestamps:
        raise ValueError("No data available for any asset")

    # Create a date range from min to max timestamp
    min_ts = min(all_timestamps)
    max_ts = max(all_timestamps)
    date_range = pd.date_range(start=min_ts, end=max_ts, freq="D")

    # Build aligned DataFrame
    aligned = pd.DataFrame({"timestamp": date_range})

    # Add spot prices
    for asset, df in spot_data.items():
        aligned = pd.merge(aligned, df, on="timestamp", how="left", suffixes=("", "_dup"))
        aligned = aligned.rename(columns={"close": f"{asset}_spot"})

        # Forward-fill gaps
        aligned[f"{asset}_spot"] = aligned[f"{asset}_spot"].ffill()

        # Check for remaining NaN (gaps at the start)
        if aligned[f"{asset}_spot"].isna().any():
            na_count = aligned[f"{asset}_spot"].isna().sum()
            warnings.append(
                f"{asset} spot: {na_count} missing values at the beginning (no forward-fill source)"
            )
            # Backward fill for start gaps
            aligned[f"{asset}_spot"] = aligned[f"{asset}_spot"].bfill()

    # Add futures data
    for asset, df in futures_data.items():
        # Add mark price
        mark_df = df[["timestamp", "mark_price"]].rename(
            columns={"mark_price": f"{asset}_futures_mark"}
        )
        aligned = pd.merge(aligned, mark_df, on="timestamp", how="left")
        aligned[f"{asset}_futures_mark"] = aligned[f"{asset}_futures_mark"].ffill()

        # Add funding rate
        funding_df = df[["timestamp", "funding_rate"]].rename(
            columns={"funding_rate": f"{asset}_funding"}
        )
        aligned = pd.merge(aligned, funding_df, on="timestamp", how="left")
        aligned[f"{asset}_funding"] = aligned[f"{asset}_funding"].ffill()

        # Check for gaps
        if aligned[f"{asset}_futures_mark"].isna().any():
            na_count = aligned[f"{asset}_futures_mark"].isna().sum()
            warnings.append(f"{asset} futures: {na_count} missing mark prices")
            aligned[f"{asset}_futures_mark"] = aligned[f"{asset}_futures_mark"].bfill()

        if aligned[f"{asset}_funding"].isna().any():
            na_count = aligned[f"{asset}_funding"].isna().sum()
            warnings.append(f"{asset} funding: {na_count} missing funding rates")
            # Fill missing funding rates with 0 (neutral)
            aligned[f"{asset}_funding"] = aligned[f"{asset}_funding"].fillna(0.0)

    # Add lending data
    for asset, df in lending_data.items():
        # Add liquidity index (for supply positions)
        if "liquidity_index" in df.columns:
            index_df = df[["timestamp", "liquidity_index"]].rename(
                columns={"liquidity_index": f"{asset}_liquidity_index"}
            )
            aligned = pd.merge(aligned, index_df, on="timestamp", how="left")
            aligned[f"{asset}_liquidity_index"] = aligned[f"{asset}_liquidity_index"].ffill()

            if aligned[f"{asset}_liquidity_index"].isna().any():
                na_count = aligned[f"{asset}_liquidity_index"].isna().sum()
                warnings.append(f"{asset} lending: {na_count} missing liquidity indices")
                aligned[f"{asset}_liquidity_index"] = aligned[f"{asset}_liquidity_index"].bfill()

        # Add variable borrow index (for borrow positions)
        if "variable_borrow_index" in df.columns:
            borrow_index_df = df[["timestamp", "variable_borrow_index"]].rename(
                columns={"variable_borrow_index": f"{asset}_variable_borrow_index"}
            )
            aligned = pd.merge(aligned, borrow_index_df, on="timestamp", how="left")
            aligned[f"{asset}_variable_borrow_index"] = aligned[
                f"{asset}_variable_borrow_index"
            ].ffill()

            if aligned[f"{asset}_variable_borrow_index"].isna().any():
                na_count = aligned[f"{asset}_variable_borrow_index"].isna().sum()
                warnings.append(f"{asset} lending: {na_count} missing variable borrow indices")
                aligned[f"{asset}_variable_borrow_index"] = aligned[
                    f"{asset}_variable_borrow_index"
                ].bfill()

        # Add supply rate (for APY calculations)
        if "supply_rate_ray" in df.columns:
            supply_rate_df = df[["timestamp", "supply_rate_ray"]].rename(
                columns={"supply_rate_ray": f"{asset}_supply_rate"}
            )
            aligned = pd.merge(aligned, supply_rate_df, on="timestamp", how="left")
            aligned[f"{asset}_supply_rate"] = aligned[f"{asset}_supply_rate"].ffill()

            if aligned[f"{asset}_supply_rate"].isna().any():
                aligned[f"{asset}_supply_rate"] = aligned[f"{asset}_supply_rate"].fillna(0.0)

        # Add variable borrow rate
        if "variable_borrow_rate_ray" in df.columns:
            var_borrow_rate_df = df[["timestamp", "variable_borrow_rate_ray"]].rename(
                columns={"variable_borrow_rate_ray": f"{asset}_variable_borrow_rate"}
            )
            aligned = pd.merge(aligned, var_borrow_rate_df, on="timestamp", how="left")
            aligned[f"{asset}_variable_borrow_rate"] = aligned[
                f"{asset}_variable_borrow_rate"
            ].ffill()

            if aligned[f"{asset}_variable_borrow_rate"].isna().any():
                aligned[f"{asset}_variable_borrow_rate"] = aligned[
                    f"{asset}_variable_borrow_rate"
                ].fillna(0.0)

        # Add stable borrow rate
        if "stable_borrow_rate_ray" in df.columns:
            stable_borrow_rate_df = df[["timestamp", "stable_borrow_rate_ray"]].rename(
                columns={"stable_borrow_rate_ray": f"{asset}_stable_borrow_rate"}
            )
            aligned = pd.merge(aligned, stable_borrow_rate_df, on="timestamp", how="left")
            aligned[f"{asset}_stable_borrow_rate"] = aligned[
                f"{asset}_stable_borrow_rate"
            ].ffill()

            if aligned[f"{asset}_stable_borrow_rate"].isna().any():
                aligned[f"{asset}_stable_borrow_rate"] = aligned[
                    f"{asset}_stable_borrow_rate"
                ].fillna(0.0)

    logger.info(f"Aligned data: {len(aligned)} daily data points")
    if warnings:
        for warning in warnings:
            logger.warning(f"Data gap: {warning}")

    return aligned, warnings
