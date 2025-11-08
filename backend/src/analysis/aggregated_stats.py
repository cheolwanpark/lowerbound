"""Aggregated statistics calculations for API endpoints.

This module provides pre-calculated statistics for spot, futures, and lending data
to reduce token usage for AI agents by 80-85%.
"""

import numpy as np
import pandas as pd
from loguru import logger

from src.analysis.metrics import (
    calculate_correlation_matrix,
    calculate_max_drawdown,
    calculate_returns,
    calculate_sharpe_ratio,
    calculate_volatility,
)
from src.config import settings
from src.models import convert_ray_to_apy


def calculate_spot_stats(ohlcv_data: list[dict]) -> dict | None:
    """
    Calculate aggregated spot market statistics.

    Args:
        ohlcv_data: List of OHLCV dicts with keys: timestamp, open, high, low, close, volume

    Returns:
        Dict with price and returns metrics, or None if insufficient data

    Metrics returned:
        - price: current, min, max, mean
        - returns: total_return_pct, volatility_pct, sharpe_ratio, max_drawdown_pct
    """
    if not ohlcv_data or len(ohlcv_data) < 2:
        logger.debug("Insufficient spot data for stats calculation (need >= 2 points)")
        return None

    try:
        # Extract price data
        prices = np.array([float(row["close"]) for row in ohlcv_data])

        # Price statistics
        current_price = float(prices[-1])
        min_price = float(np.min(prices))
        max_price = float(np.max(prices))
        mean_price = float(np.mean(prices))

        # Calculate returns
        returns = calculate_returns(prices)

        if len(returns) == 0:
            logger.warning("Could not calculate returns from spot data")
            return None

        # Total return (first to last price)
        total_return_pct = float(((prices[-1] / prices[0]) - 1) * 100)

        # Volatility (annualized)
        volatility_pct = calculate_volatility(returns, annualize=True, periods_per_year=365) * 100

        # Sharpe ratio (annualized)
        sharpe_ratio = calculate_sharpe_ratio(
            returns, risk_free_rate=settings.RISK_FREE_RATE, periods_per_year=365
        )

        # Max drawdown
        max_drawdown_pct = calculate_max_drawdown(prices) * 100

        return {
            "current_price": current_price,
            "min_price": min_price,
            "max_price": max_price,
            "mean_price": mean_price,
            "total_return_pct": total_return_pct,
            "volatility_pct": volatility_pct,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown_pct": max_drawdown_pct,
        }

    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Error calculating spot stats: {e}", exc_info=True)
        return None


def calculate_futures_stats(
    funding_data: list[dict],
    mark_data: list[dict] | None,
    oi_data: list[dict] | None,
    spot_price: float | None,
) -> dict | None:
    """
    Calculate aggregated futures market statistics.

    Args:
        funding_data: List of funding rate dicts with keys: timestamp, funding_rate, mark_price
        mark_data: List of mark price klines (for basis calculation)
        oi_data: List of open interest dicts with keys: timestamp, open_interest
        spot_price: Current spot price (for basis calculation)

    Returns:
        Dict with funding, basis, and OI metrics, or None if no funding data

    Metrics returned:
        - current_funding_rate_pct
        - mean_funding_rate_pct
        - cumulative_funding_cost_pct
        - current_basis_premium_pct (None if mark_data/spot_price unavailable)
        - mean_basis_premium_pct (None if mark_data/spot_price unavailable)
        - current_open_interest (None if oi_data unavailable)
        - open_interest_change_pct (None if oi_data unavailable)
    """
    if not funding_data:
        logger.debug("No funding data available")
        return None

    try:
        # Funding rate statistics
        funding_rates = np.array([float(row["funding_rate"]) for row in funding_data])

        current_funding_rate_pct = float(funding_rates[-1] * 100)
        mean_funding_rate_pct = float(np.mean(funding_rates) * 100)

        # Cumulative funding cost (sum of all funding rates over period)
        # Note: This is the total cost for holding a perpetual position
        cumulative_funding_cost_pct = float(np.sum(funding_rates) * 100)

        # Basis statistics (requires mark price and spot price)
        current_basis_premium_pct = None
        mean_basis_premium_pct = None

        if mark_data and spot_price and spot_price > 0:
            try:
                # Calculate basis premium: (mark_price - spot_price) / spot_price
                mark_prices = np.array([float(row["close"]) for row in mark_data])

                if len(mark_prices) > 0:
                    current_mark_price = mark_prices[-1]
                    current_basis_premium_pct = float(
                        ((current_mark_price - spot_price) / spot_price) * 100
                    )

                    # Mean basis premium over period
                    basis_premiums = (mark_prices - spot_price) / spot_price
                    mean_basis_premium_pct = float(np.mean(basis_premiums) * 100)

            except (ValueError, KeyError, IndexError) as e:
                logger.warning(f"Could not calculate basis statistics: {e}")

        # Open interest statistics
        current_open_interest = None
        open_interest_change_pct = None

        if oi_data and len(oi_data) >= 2:
            try:
                oi_values = np.array([float(row["open_interest"]) for row in oi_data])
                current_open_interest = float(oi_values[-1])

                # Calculate change from first to last
                if oi_values[0] > 0:
                    open_interest_change_pct = float(
                        ((oi_values[-1] / oi_values[0]) - 1) * 100
                    )

            except (ValueError, KeyError, IndexError) as e:
                logger.warning(f"Could not calculate OI statistics: {e}")

        return {
            "current_funding_rate_pct": current_funding_rate_pct,
            "mean_funding_rate_pct": mean_funding_rate_pct,
            "cumulative_funding_cost_pct": cumulative_funding_cost_pct,
            "current_basis_premium_pct": current_basis_premium_pct,
            "mean_basis_premium_pct": mean_basis_premium_pct,
            "current_open_interest": current_open_interest,
            "open_interest_change_pct": open_interest_change_pct,
        }

    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Error calculating futures stats: {e}", exc_info=True)
        return None


def calculate_lending_stats(lending_data: list[dict]) -> dict | None:
    """
    Calculate aggregated lending market statistics.

    Args:
        lending_data: List of lending dicts with keys: timestamp, supply_rate_ray,
                     variable_borrow_rate_ray, stable_borrow_rate_ray

    Returns:
        Dict with supply/borrow APY metrics, or None if no data

    Metrics returned:
        - current_supply_apy_pct
        - mean_supply_apy_pct
        - min_supply_apy_pct
        - max_supply_apy_pct
        - current_variable_borrow_apy_pct
        - mean_variable_borrow_apy_pct
        - spread_pct (borrow - supply)
    """
    if not lending_data:
        logger.debug("No lending data available")
        return None

    try:
        # Convert RAY rates to APY percentages
        supply_apys = []
        borrow_apys = []

        for row in lending_data:
            try:
                supply_apy = convert_ray_to_apy(row["supply_rate_ray"])
                borrow_apy = convert_ray_to_apy(row["variable_borrow_rate_ray"])

                supply_apys.append(supply_apy)
                borrow_apys.append(borrow_apy)

            except (ValueError, KeyError, ArithmeticError) as e:
                logger.warning(f"Skipping row due to conversion error: {e}")
                continue

        if not supply_apys or not borrow_apys:
            logger.warning("No valid lending data after conversion")
            return None

        # Supply statistics
        current_supply_apy_pct = float(supply_apys[-1])
        mean_supply_apy_pct = float(np.mean(supply_apys))
        min_supply_apy_pct = float(np.min(supply_apys))
        max_supply_apy_pct = float(np.max(supply_apys))

        # Borrow statistics
        current_variable_borrow_apy_pct = float(borrow_apys[-1])
        mean_variable_borrow_apy_pct = float(np.mean(borrow_apys))

        # Spread (borrow - supply)
        spread_pct = current_variable_borrow_apy_pct - current_supply_apy_pct

        return {
            "current_supply_apy_pct": current_supply_apy_pct,
            "mean_supply_apy_pct": mean_supply_apy_pct,
            "min_supply_apy_pct": min_supply_apy_pct,
            "max_supply_apy_pct": max_supply_apy_pct,
            "current_variable_borrow_apy_pct": current_variable_borrow_apy_pct,
            "mean_variable_borrow_apy_pct": mean_variable_borrow_apy_pct,
            "spread_pct": spread_pct,
        }

    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Error calculating lending stats: {e}", exc_info=True)
        return None


def calculate_cross_asset_correlations(
    multi_asset_ohlcv: dict[str, list[dict]]
) -> dict[str, dict[str, float]] | None:
    """
    Calculate correlation matrix for multiple assets.

    Time-aligns data by timestamp (inner join), drops non-overlapping periods.

    Args:
        multi_asset_ohlcv: Dict mapping asset symbol to OHLCV data list

    Returns:
        Correlation matrix as nested dict {asset1: {asset2: correlation}},
        or None if <2 assets or insufficient overlapping data

    Example:
        {
            "BTC": {"BTC": 1.0, "ETH": 0.85, "SOL": 0.72},
            "ETH": {"BTC": 0.85, "ETH": 1.0, "SOL": 0.78},
            "SOL": {"BTC": 0.72, "ETH": 0.78, "SOL": 1.0}
        }
    """
    if not multi_asset_ohlcv or len(multi_asset_ohlcv) < 2:
        logger.debug("Need at least 2 assets for correlation calculation")
        return None

    try:
        # Convert to DataFrames with timestamp index
        asset_dataframes = {}

        for asset, ohlcv_data in multi_asset_ohlcv.items():
            if not ohlcv_data or len(ohlcv_data) < 2:
                logger.debug(f"Skipping {asset}: insufficient data")
                continue

            df = pd.DataFrame(ohlcv_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["close"] = df["close"].astype(float)
            df = df.set_index("timestamp")

            asset_dataframes[asset] = df[["close"]].rename(columns={"close": asset})

        if len(asset_dataframes) < 2:
            logger.debug("Insufficient assets with valid data for correlation")
            return None

        # Align timestamps (inner join - only overlapping periods)
        aligned_df = pd.concat(asset_dataframes.values(), axis=1, join="inner")

        if len(aligned_df) < 2:
            logger.warning("Insufficient overlapping data points for correlation")
            return None

        # Calculate returns for each asset
        multi_asset_returns = {}
        for asset in aligned_df.columns:
            prices = aligned_df[asset].values
            returns = calculate_returns(prices)

            if len(returns) > 0:
                multi_asset_returns[asset] = returns

        if len(multi_asset_returns) < 2:
            logger.warning("Could not calculate returns for correlation")
            return None

        # Calculate correlation matrix
        correlation_matrix = calculate_correlation_matrix(multi_asset_returns)

        logger.info(
            f"Calculated correlation matrix for {len(correlation_matrix)} assets "
            f"with {len(aligned_df)} overlapping data points"
        )

        return correlation_matrix

    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Error calculating cross-asset correlations: {e}", exc_info=True)
        return None
