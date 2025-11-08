"""Main risk profile calculation orchestration."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from decimal import Decimal
from loguru import logger

from src.analysis import data_service, metrics, scenarios, valuation
from src.config import settings


async def calculate_risk_profile(request_data: dict) -> dict:
    """
    Calculate comprehensive risk profile for a portfolio.

    Args:
        request_data: Dict with keys:
            - positions: List of position dicts
            - lookback_days: Number of days to look back (default: 30)

    Returns:
        Dict with risk profile data including:
            - current_portfolio_value
            - data_availability_warning
            - sensitivity_analysis
            - risk_metrics
            - scenarios
    """
    positions = request_data["positions"]
    lookback_days = request_data.get("lookback_days", 30)

    logger.info(f"Calculating risk profile for {len(positions)} positions")

    # Detect if portfolio has lending positions
    has_lending = any(
        p["position_type"] in ["lending_supply", "lending_borrow"] for p in positions
    )

    # Validate positions
    _validate_positions(positions)

    # Extract unique assets from positions
    assets = list(set(pos["asset"] for pos in positions))
    logger.info(f"Unique assets in portfolio: {assets}")

    # Step 1: Fetch historical data for all assets
    spot_data, futures_data, lending_data, actual_days = await data_service.fetch_portfolio_data(
        assets, lookback_days
    )

    # Check data availability
    data_warning = None
    if actual_days < 30:
        data_warning = f"Warning: Only {actual_days} days of data available (recommended: 30+). Risk metrics may be unreliable."
        logger.warning(data_warning)

    # Step 2: Resample to daily intervals
    daily_spot, daily_futures, daily_lending = data_service.resample_to_daily(
        spot_data, futures_data, lending_data
    )

    # Step 3: Align time series
    aligned_data, alignment_warnings = data_service.align_time_series(
        daily_spot, daily_futures, daily_lending
    )

    if alignment_warnings:
        warning_msg = "; ".join(alignment_warnings)
        if data_warning:
            data_warning += f" | {warning_msg}"
        else:
            data_warning = warning_msg

    logger.info(f"Aligned data shape: {aligned_data.shape}")

    # Step 3.5: Auto-lookup entry_index for lending positions if not provided
    if has_lending:
        for pos in positions:
            if pos["position_type"] in ["lending_supply", "lending_borrow"]:
                # Validate required fields
                if "entry_timestamp" not in pos:
                    raise ValueError(
                        f"Lending position for {pos['asset']} missing required field: entry_timestamp"
                    )

                if pos["position_type"] == "lending_borrow" and "borrow_type" not in pos:
                    raise ValueError(
                        f"Lending borrow position for {pos['asset']} missing required field: borrow_type"
                    )

                # Auto-lookup entry_index if not provided
                if not pos.get("entry_index"):
                    entry_timestamp = pd.to_datetime(pos["entry_timestamp"])
                    if entry_timestamp.tzinfo is None:
                        entry_timestamp = entry_timestamp.replace(tzinfo=timezone.utc)

                    index_type = (
                        "liquidity"
                        if pos["position_type"] == "lending_supply"
                        else "variable_borrow"
                    )
                    entry_index = _lookup_entry_index(
                        pos["asset"], entry_timestamp, aligned_data, index_type
                    )
                    pos["entry_index"] = str(entry_index)
                    logger.info(
                        f"Auto-looked up entry_index for {pos['asset']} {pos['position_type']}: {entry_index}"
                    )

    # Step 4: Get current prices (most recent in aligned data)
    current_prices = _extract_current_prices(aligned_data, positions)
    logger.info(f"Current prices: {current_prices}")

    # Step 4.5: Extract current indices for lending positions
    current_indices = {}
    if has_lending:
        current_indices = _extract_current_indices(aligned_data, positions)
        logger.info(f"Current lending indices: {current_indices}")

    # Step 5: Calculate current portfolio value
    current_value = valuation.calculate_portfolio_value(
        positions, current_prices, current_indices if has_lending else None
    )
    logger.info(f"Current portfolio value: ${current_value:,.2f}")

    # Step 6: Calculate historical portfolio values and returns
    portfolio_values, portfolio_returns = _calculate_historical_portfolio_series(
        positions, aligned_data
    )

    logger.info(
        f"Historical portfolio: {len(portfolio_values)} values, {len(portfolio_returns)} returns"
    )

    # Step 7: Calculate sensitivity table
    sensitivity_range = [x / 100 for x in settings.SENSITIVITY_RANGE]  # Convert to decimals
    sensitivity_table = valuation.calculate_sensitivity_table(
        positions, current_prices, sensitivity_range, current_indices if has_lending else None
    )

    # Step 8: Calculate risk metrics
    risk_metrics_data = _calculate_risk_metrics(
        portfolio_returns,
        portfolio_values,
        current_value,
        actual_days,
        positions,
        aligned_data,
    )

    # Step 8.5: Calculate lending metrics if applicable
    if has_lending:
        # Extract current rates from aligned data
        current_rates = _extract_current_rates(aligned_data, positions)

        # Calculate position values for lending metrics
        positions_with_values = []
        for pos in positions:
            pos_copy = pos.copy()
            pos_value = valuation.calculate_position_value(
                pos, current_prices, current_indices if has_lending else None
            )
            pos_copy["value"] = pos_value
            positions_with_values.append(pos_copy)

        # Calculate lending metrics
        lending_metrics = _calculate_lending_metrics(
            positions_with_values, aligned_data, current_rates
        )
        risk_metrics_data["lending_metrics"] = lending_metrics
    else:
        risk_metrics_data["lending_metrics"] = None

    # Step 9: Calculate delta exposure
    delta_exposure = valuation.calculate_delta_exposure(positions)
    risk_metrics_data["delta_exposure"] = delta_exposure
    logger.info(f"Delta exposure: {delta_exposure:.4f}")

    # Step 10: Run scenario analysis
    scenario_results = scenarios.run_all_scenarios(
        positions, current_prices, current_indices if has_lending else None
    )

    # Step 11: Construct response
    response = {
        "current_portfolio_value": current_value,
        "data_availability_warning": data_warning,
        "sensitivity_analysis": sensitivity_table,
        "risk_metrics": risk_metrics_data,
        "scenarios": scenario_results,
    }

    logger.info("Risk profile calculation completed successfully")
    return response


def _validate_positions(positions: list[dict]) -> None:
    """Validate position data."""
    if not positions:
        raise ValueError("Portfolio must contain at least one position")

    if len(positions) > 20:
        raise ValueError("Maximum 20 positions allowed")

    valid_types = [
        "spot",
        "futures_long",
        "futures_short",
        "lending_supply",
        "lending_borrow",
    ]

    for i, pos in enumerate(positions):
        # Check position type first to determine required fields
        if "position_type" not in pos:
            raise ValueError(f"Position {i} missing required field: position_type")

        if pos["position_type"] not in valid_types:
            raise ValueError(
                f"Position {i} has invalid position_type: {pos['position_type']}"
            )

        # Basic required fields for all positions
        if "asset" not in pos:
            raise ValueError(f"Position {i} missing required field: asset")
        if "quantity" not in pos:
            raise ValueError(f"Position {i} missing required field: quantity")

        # Lending positions have different requirements
        if pos["position_type"] in ["lending_supply", "lending_borrow"]:
            # Lending positions don't require entry_price, but require entry_timestamp
            if "entry_timestamp" not in pos:
                raise ValueError(
                    f"Lending position {i} missing required field: entry_timestamp"
                )
            if pos["position_type"] == "lending_borrow" and "borrow_type" not in pos:
                raise ValueError(
                    f"Lending borrow position {i} missing required field: borrow_type"
                )
        else:
            # Spot and futures positions require entry_price
            if "entry_price" not in pos:
                raise ValueError(f"Position {i} missing required field: entry_price")

            if pos["entry_price"] <= 0:
                raise ValueError(
                    f"Position {i} has invalid entry_price: {pos['entry_price']}"
                )

        if pos["quantity"] <= 0:
            raise ValueError(f"Position {i} has invalid quantity: {pos['quantity']}")

        leverage = pos.get("leverage", 1.0)
        if leverage <= 0 or leverage > 125:
            raise ValueError(
                f"Position {i} has invalid leverage: {leverage} (must be 0 < leverage <= 125)"
            )


def _extract_current_prices(
    aligned_data: pd.DataFrame, positions: list[dict]
) -> dict[tuple[str, str], float]:
    """
    Extract current prices for each position from aligned data.

    Returns:
        Dict with (asset, position_type) tuple keys to handle same asset with different instruments
    """
    current_prices = {}
    latest_row = aligned_data.iloc[-1]

    for pos in positions:
        asset = pos["asset"]
        position_type = pos["position_type"]

        # Skip lending positions - they don't use prices, they use indices
        if position_type in ["lending_supply", "lending_borrow"]:
            continue

        # Use composite key to differentiate spot vs futures for same asset
        price_key = (asset, position_type)

        if position_type == "spot":
            # Use spot price
            col_name = f"{asset}_spot"
            if col_name in aligned_data.columns:
                current_prices[price_key] = float(latest_row[col_name])
            else:
                raise ValueError(f"No spot data available for asset: {asset}")
        else:
            # Use futures mark price (both long and short use same mark price)
            col_name = f"{asset}_futures_mark"
            if col_name in aligned_data.columns:
                current_prices[price_key] = float(latest_row[col_name])
            else:
                raise ValueError(f"No futures data available for asset: {asset}")

    return current_prices


def _calculate_historical_portfolio_series(
    positions: list[dict], aligned_data: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate historical portfolio values and returns.

    Returns:
        Tuple of (portfolio_values, portfolio_returns)
    """
    portfolio_values = []

    # Check if we have lending positions
    has_lending = any(
        p["position_type"] in ["lending_supply", "lending_borrow"] for p in positions
    )

    for _, row in aligned_data.iterrows():
        # Build price dict for this date using composite keys
        prices = {}
        for pos in positions:
            asset = pos["asset"]
            position_type = pos["position_type"]

            # Skip lending positions - they don't use prices
            if position_type in ["lending_supply", "lending_borrow"]:
                continue

            price_key = (asset, position_type)

            if position_type == "spot":
                col_name = f"{asset}_spot"
            else:
                col_name = f"{asset}_futures_mark"

            if col_name in aligned_data.columns:
                prices[price_key] = float(row[col_name])

        # Build indices dict for this date if we have lending positions
        indices = {}
        if has_lending:
            for pos in positions:
                if pos["position_type"] in ["lending_supply", "lending_borrow"]:
                    asset = pos["asset"]
                    if asset not in indices:
                        indices[asset] = {}

                    # Get liquidity index
                    liquidity_col = f"{asset}_liquidity_index"
                    if liquidity_col in aligned_data.columns:
                        indices[asset]["liquidity_index"] = float(row[liquidity_col])

                    # Get variable borrow index
                    borrow_col = f"{asset}_variable_borrow_index"
                    if borrow_col in aligned_data.columns:
                        indices[asset]["variable_borrow_index"] = float(row[borrow_col])

        # Calculate portfolio value for this date
        value = valuation.calculate_portfolio_value(
            positions, prices, indices if has_lending else None
        )
        portfolio_values.append(value)

    portfolio_values = np.array(portfolio_values)
    portfolio_returns = metrics.calculate_returns(portfolio_values)

    return portfolio_values, portfolio_returns


def _calculate_risk_metrics(
    portfolio_returns: np.ndarray,
    portfolio_values: np.ndarray,
    current_value: float,
    actual_days: int,
    positions: list[dict],
    aligned_data: pd.DataFrame,
) -> dict:
    """Calculate all risk metrics."""
    from src.config import settings

    # Volatility
    volatility = metrics.calculate_volatility(
        portfolio_returns, annualize=True, periods_per_year=365
    )

    # VaR at multiple confidence levels
    var_95 = metrics.calculate_var_historical(portfolio_returns, 0.95, current_value)
    var_99 = metrics.calculate_var_historical(portfolio_returns, 0.99, current_value)

    # CVaR (use VaR 95% threshold)
    var_95_threshold = np.quantile(portfolio_returns, 0.05) if len(portfolio_returns) > 0 else 0
    cvar_95 = metrics.calculate_cvar(portfolio_returns, var_95_threshold, current_value)

    # Sharpe ratio
    sharpe = metrics.calculate_sharpe_ratio(
        portfolio_returns,
        risk_free_rate=settings.RISK_FREE_RATE,
        periods_per_year=365,
    )

    # Max drawdown
    max_dd = metrics.calculate_max_drawdown(portfolio_values)

    # Calculate correlation matrix
    asset_returns = _calculate_asset_returns(positions, aligned_data)
    corr_matrix = metrics.calculate_correlation_matrix(asset_returns)

    # Portfolio variance
    # First, calculate position values at current prices
    current_prices = _extract_current_prices(aligned_data, positions)

    # Check if we have lending positions
    has_lending = any(
        p["position_type"] in ["lending_supply", "lending_borrow"] for p in positions
    )

    # Extract current indices if needed
    current_indices = None
    if has_lending:
        current_indices = _extract_current_indices(aligned_data, positions)

    positions_with_values = []
    for pos in positions:
        pos_copy = pos.copy()
        pos_value = valuation.calculate_position_value(pos, current_prices, current_indices)
        pos_copy["value"] = pos_value
        positions_with_values.append(pos_copy)

    portfolio_variance = metrics.calculate_portfolio_variance(
        positions_with_values, asset_returns, corr_matrix
    )

    return {
        "lookback_days_used": actual_days,
        "portfolio_variance": portfolio_variance,
        "portfolio_volatility_annual": volatility,
        "var_95_1day": var_95,
        "var_99_1day": var_99,
        "cvar_95": cvar_95,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "correlation_matrix": corr_matrix,
    }


def _calculate_asset_returns(
    positions: list[dict], aligned_data: pd.DataFrame
) -> dict[str, np.ndarray]:
    """Calculate returns for each asset in the portfolio."""
    asset_returns = {}
    unique_assets = list(set(pos["asset"] for pos in positions))

    for asset in unique_assets:
        # Try spot first, then futures
        if f"{asset}_spot" in aligned_data.columns:
            prices = aligned_data[f"{asset}_spot"].values
        elif f"{asset}_futures_mark" in aligned_data.columns:
            prices = aligned_data[f"{asset}_futures_mark"].values
        else:
            continue

        returns = metrics.calculate_returns(prices)
        asset_returns[asset] = returns

    return asset_returns


def _validate_lending_data_freshness(
    latest_timestamp: datetime, max_age_hours: int
) -> tuple[float, str | None]:
    """
    Validate lending data isn't too stale.

    Args:
        latest_timestamp: Most recent timestamp from lending data
        max_age_hours: Maximum acceptable age in hours

    Returns:
        Tuple of (age_hours, warning_message)
        warning_message is None if data is fresh enough
    """
    now = datetime.now(timezone.utc)

    # Ensure latest_timestamp is timezone-aware
    if latest_timestamp.tzinfo is None:
        latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)

    age = now - latest_timestamp
    age_hours = age.total_seconds() / 3600

    if age_hours > max_age_hours:
        warning = f"Lending data is {age_hours:.1f}h old (max: {max_age_hours}h). Metrics may be stale."
        logger.warning(warning)
        return age_hours, warning

    return age_hours, None


def _lookup_entry_index(
    asset: str,
    entry_timestamp: datetime,
    aligned_data: pd.DataFrame,
    index_type: str,  # "liquidity" or "variable_borrow"
) -> float:
    """
    Look up historical index closest to entry_timestamp.

    Handles positions older than available data by using earliest available index.

    Args:
        asset: Asset symbol (e.g., "WETH")
        entry_timestamp: When the position was entered
        aligned_data: Aligned DataFrame with index columns
        index_type: "liquidity" for supply, "variable_borrow" for borrows

    Returns:
        Index value at entry (or earliest available)
    """
    col_name = f"{asset}_{index_type}_index"

    if col_name not in aligned_data.columns:
        raise ValueError(f"No {index_type} index data available for {asset}")

    # Ensure entry_timestamp is timezone-aware
    if entry_timestamp.tzinfo is None:
        entry_timestamp = entry_timestamp.replace(tzinfo=timezone.utc)

    # Find the row closest to entry_timestamp
    aligned_data_copy = aligned_data.copy()
    aligned_data_copy["timestamp"] = pd.to_datetime(aligned_data_copy["timestamp"])

    # Make timestamps timezone-aware if they aren't
    if aligned_data_copy["timestamp"].dt.tz is None:
        aligned_data_copy["timestamp"] = aligned_data_copy["timestamp"].dt.tz_localize(timezone.utc)

    # Check if entry_timestamp is before all available data
    earliest_timestamp = aligned_data_copy["timestamp"].min()
    if entry_timestamp < earliest_timestamp:
        logger.warning(
            f"Entry timestamp {entry_timestamp} predates available data ({earliest_timestamp}). "
            f"Using earliest available {index_type} index for {asset}."
        )
        return float(aligned_data_copy.iloc[0][col_name])

    # Find closest timestamp
    time_diff = abs(aligned_data_copy["timestamp"] - entry_timestamp)
    closest_idx = time_diff.argmin()
    entry_index = float(aligned_data_copy.iloc[closest_idx][col_name])

    logger.debug(
        f"Looked up {asset} {index_type} index at {entry_timestamp}: {entry_index}"
    )

    return entry_index


def _extract_current_indices(
    aligned_data: pd.DataFrame, positions: list[dict]
) -> dict[str, dict[str, float]]:
    """
    Extract current lending indices for each asset.

    Args:
        aligned_data: Aligned DataFrame with index columns
        positions: List of positions to extract indices for

    Returns:
        Dict of {asset: {liquidity_index: float, variable_borrow_index: float}}
    """
    current_indices = {}
    latest_row = aligned_data.iloc[-1]

    # Get unique assets from lending positions
    lending_assets = set()
    for pos in positions:
        if pos["position_type"] in ["lending_supply", "lending_borrow"]:
            lending_assets.add(pos["asset"])

    for asset in lending_assets:
        indices = {}

        # Extract liquidity index (for supply positions)
        liquidity_col = f"{asset}_liquidity_index"
        if liquidity_col in aligned_data.columns:
            indices["liquidity_index"] = float(latest_row[liquidity_col])

        # Extract variable borrow index (for borrow positions)
        borrow_col = f"{asset}_variable_borrow_index"
        if borrow_col in aligned_data.columns:
            indices["variable_borrow_index"] = float(latest_row[borrow_col])

        if indices:
            current_indices[asset] = indices

    return current_indices


def _extract_current_rates(
    aligned_data: pd.DataFrame, positions: list[dict]
) -> dict[str, dict[str, float]]:
    """
    Extract current lending rates for each asset.

    Args:
        aligned_data: Aligned DataFrame with rate columns
        positions: List of positions to extract rates for

    Returns:
        Dict of {asset: {supply_rate: float (RAY), variable_borrow_rate: float (RAY), stable_borrow_rate: float (RAY)}}
    """
    current_rates = {}
    latest_row = aligned_data.iloc[-1]

    # Get unique assets from lending positions
    lending_assets = set()
    for pos in positions:
        if pos["position_type"] in ["lending_supply", "lending_borrow"]:
            lending_assets.add(pos["asset"])

    for asset in lending_assets:
        rates = {}

        # Extract supply rate
        supply_col = f"{asset}_supply_rate"
        if supply_col in aligned_data.columns:
            rates["supply_rate"] = float(latest_row[supply_col])

        # Extract variable borrow rate
        var_borrow_col = f"{asset}_variable_borrow_rate"
        if var_borrow_col in aligned_data.columns:
            rates["variable_borrow_rate"] = float(latest_row[var_borrow_col])

        # Extract stable borrow rate
        stable_borrow_col = f"{asset}_stable_borrow_rate"
        if stable_borrow_col in aligned_data.columns:
            rates["stable_borrow_rate"] = float(latest_row[stable_borrow_col])

        if rates:
            current_rates[asset] = rates

    return current_rates


def _calculate_lending_metrics(
    positions: list[dict],
    aligned_data: pd.DataFrame,
    current_rates: dict[str, dict[str, float]],
) -> dict:
    """
    Calculate ACCOUNT-LEVEL lending metrics.

    Args:
        positions: List of all positions (with calculated values)
        aligned_data: Aligned DataFrame with lending data
        current_rates: Dict of {asset: {supply_rate: float, variable_borrow_rate: float, stable_borrow_rate: float}}

    Returns:
        Dict matching LendingMetrics model structure
    """
    # Separate supply and borrow positions
    supply_positions = [p for p in positions if p["position_type"] == "lending_supply"]
    borrow_positions = [p for p in positions if p["position_type"] == "lending_borrow"]

    if not supply_positions and not borrow_positions:
        raise ValueError("No lending positions found")

    # Calculate total collateral and total debt values
    total_collateral_value = sum(p.get("value", 0.0) for p in supply_positions)
    total_debt_value = sum(abs(p.get("value", 0.0)) for p in borrow_positions)

    # Calculate LTV
    ltv = valuation.calculate_account_ltv(total_debt_value, total_collateral_value)

    # Calculate health factor
    # Get liquidation thresholds from settings
    liquidation_thresholds = settings.AAVE_LIQUIDATION_THRESHOLDS
    health_factor = valuation.calculate_health_factor(
        supply_positions, total_debt_value, liquidation_thresholds
    )

    # Calculate net APY
    net_apy, weighted_supply_apy, weighted_borrow_apy = metrics.calculate_net_apy(
        supply_positions, borrow_positions, current_rates
    )

    # Calculate additional metrics
    net_lending_value = total_collateral_value - total_debt_value

    # Calculate max safe borrow (based on max LTV)
    # Get max LTV from settings (use weighted average of collateral assets)
    max_ltv_values = settings.AAVE_MAX_LTV
    weighted_max_ltv = 0.0
    if total_collateral_value > 0:
        for pos in supply_positions:
            asset = pos["asset"]
            value = pos.get("value", 0.0)
            max_ltv = max_ltv_values.get(asset, 0.75)  # Default to 75% if unknown
            weighted_max_ltv += (value / total_collateral_value) * max_ltv

    max_safe_borrow = (total_collateral_value * weighted_max_ltv) - total_debt_value

    # Validate data freshness
    latest_timestamp = pd.to_datetime(aligned_data.iloc[-1]["timestamp"])
    if latest_timestamp.tzinfo is None:
        latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)

    max_age_hours = settings.LENDING_DATA_MAX_AGE_HOURS
    age_hours, freshness_warning = _validate_lending_data_freshness(
        latest_timestamp, max_age_hours
    )

    return {
        "total_supplied_value": total_collateral_value,
        "total_borrowed_value": total_debt_value,
        "net_lending_value": net_lending_value,
        "current_ltv": ltv,
        "health_factor": health_factor,
        "max_safe_borrow": max(0.0, max_safe_borrow),  # Can't be negative
        "net_apy": net_apy,
        "weighted_supply_apy": weighted_supply_apy,
        "weighted_borrow_apy": weighted_borrow_apy,
        "data_timestamp": latest_timestamp,
        "data_age_hours": age_hours,
        "data_warning": freshness_warning,
    }
