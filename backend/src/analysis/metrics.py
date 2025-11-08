"""Risk metrics calculations (VaR, CVaR, Sharpe, volatility, etc.)."""

import math

import numpy as np
import pandas as pd
from loguru import logger

from src.models import convert_ray_to_apy


def calculate_returns(price_series: np.ndarray | pd.Series) -> np.ndarray:
    """
    Calculate log returns from a price series.

    Formula: r_t = ln(P_t / P_{t-1})

    Args:
        price_series: Array or Series of prices

    Returns:
        Array of log returns (length = len(price_series) - 1)
    """
    if isinstance(price_series, pd.Series):
        price_series = price_series.values

    if len(price_series) < 2:
        return np.array([])

    # Calculate log returns
    returns = np.log(price_series[1:] / price_series[:-1])

    # Filter out inf and nan values
    returns = returns[np.isfinite(returns)]

    return returns


def calculate_volatility(
    returns: np.ndarray, annualize: bool = True, periods_per_year: int = 365
) -> float:
    """
    Calculate volatility (standard deviation of returns).

    Formula:
        σ = std(returns)
        σ_annual = σ × √periods_per_year

    Args:
        returns: Array of returns
        annualize: Whether to annualize the volatility
        periods_per_year: Number of periods per year (365 for daily data)

    Returns:
        Volatility (annualized if requested)
    """
    if len(returns) == 0:
        return 0.0

    volatility = np.std(returns, ddof=1)

    if annualize:
        volatility *= math.sqrt(periods_per_year)

    return float(volatility)


def calculate_var_historical(
    returns: np.ndarray, confidence_level: float, portfolio_value: float
) -> float:
    """
    Calculate Value at Risk using Historical Simulation method.

    Formula: VaR_α = V₀ × Quantile(returns, 1-α)

    Args:
        returns: Array of historical returns
        confidence_level: Confidence level (e.g., 0.95 for 95%)
        portfolio_value: Current portfolio value

    Returns:
        VaR as a negative value representing potential loss
    """
    if len(returns) == 0:
        return 0.0

    # Calculate the quantile at (1 - confidence_level)
    quantile = np.quantile(returns, 1 - confidence_level)

    # VaR is the potential loss (negative value)
    var = portfolio_value * quantile

    logger.debug(
        f"VaR {confidence_level*100}%: {var:.2f} (quantile: {quantile:.4f}, portfolio: {portfolio_value:.2f})"
    )

    return float(var)


def calculate_cvar(
    returns: np.ndarray, var_threshold: float, portfolio_value: float
) -> float:
    """
    Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

    Formula: CVaR_α = E[Loss | Loss > VaR_α]

    Args:
        returns: Array of historical returns
        var_threshold: VaR threshold (as a return, not dollar value)
        portfolio_value: Current portfolio value

    Returns:
        CVaR as a negative value representing expected loss beyond VaR
    """
    if len(returns) == 0:
        return 0.0

    # Find returns worse than VaR threshold
    tail_returns = returns[returns <= var_threshold]

    if len(tail_returns) == 0:
        # If no returns exceed VaR, return VaR itself
        return portfolio_value * var_threshold

    # Calculate mean of tail returns
    cvar_return = np.mean(tail_returns)
    cvar = portfolio_value * cvar_return

    logger.debug(
        f"CVaR: {cvar:.2f} (mean of {len(tail_returns)} tail returns: {cvar_return:.4f})"
    )

    return float(cvar)


def calculate_sharpe_ratio(
    returns: np.ndarray, risk_free_rate: float = 0.0, periods_per_year: int = 365
) -> float:
    """
    Calculate Sharpe ratio.

    Formula: Sharpe = (E[R_p] - R_f) / σ_p × √periods_per_year

    Args:
        returns: Array of returns
        risk_free_rate: Annual risk-free rate (default: 0.0)
        periods_per_year: Number of periods per year for annualization

    Returns:
        Sharpe ratio (annualized)
    """
    if len(returns) == 0:
        return 0.0

    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)

    if std_return == 0:
        return 0.0

    # Annualize mean and std
    annual_mean = mean_return * periods_per_year
    annual_std = std_return * math.sqrt(periods_per_year)

    # Calculate Sharpe ratio
    sharpe = (annual_mean - risk_free_rate) / annual_std

    logger.debug(
        f"Sharpe: {sharpe:.4f} (mean: {annual_mean:.4f}, std: {annual_std:.4f}, rf: {risk_free_rate:.4f})"
    )

    return float(sharpe)


def calculate_max_drawdown(value_series: np.ndarray | pd.Series) -> float:
    """
    Calculate maximum drawdown (peak-to-trough decline).

    Formula: MDD = max((peak - trough) / peak)

    Args:
        value_series: Array or Series of portfolio values over time

    Returns:
        Maximum drawdown as a negative decimal (e.g., -0.25 for 25% drawdown)
    """
    if isinstance(value_series, pd.Series):
        value_series = value_series.values

    if len(value_series) < 2:
        return 0.0

    # Calculate running maximum (peak)
    running_max = np.maximum.accumulate(value_series)

    # Calculate drawdown at each point
    drawdown = (value_series - running_max) / running_max

    # Maximum drawdown is the most negative value
    max_dd = np.min(drawdown)

    logger.debug(f"Max Drawdown: {max_dd:.4f}")

    return float(max_dd)


def calculate_correlation_matrix(
    multi_asset_returns: dict[str, np.ndarray]
) -> dict[str, dict[str, float]]:
    """
    Calculate correlation matrix for multiple assets.

    Args:
        multi_asset_returns: Dict mapping asset to returns array

    Returns:
        Dict of {asset1: {asset2: correlation_coefficient}}
    """
    if not multi_asset_returns:
        return {}

    # Create DataFrame from returns
    assets = list(multi_asset_returns.keys())
    min_length = min(len(returns) for returns in multi_asset_returns.values())

    # Truncate all return series to same length
    returns_dict = {
        asset: returns[:min_length] for asset, returns in multi_asset_returns.items()
    }

    df = pd.DataFrame(returns_dict)

    # Calculate correlation matrix
    corr_matrix = df.corr()

    # Convert to nested dict
    result = {}
    for asset1 in assets:
        result[asset1] = {}
        for asset2 in assets:
            result[asset1][asset2] = float(corr_matrix.loc[asset1, asset2])

    logger.debug(f"Correlation matrix calculated for {len(assets)} assets")

    return result


def calculate_portfolio_variance(
    positions: list[dict],
    asset_returns: dict[str, np.ndarray],
    correlation_matrix: dict[str, dict[str, float]],
) -> float:
    """
    Calculate portfolio variance using covariance matrix approach.

    Formula: σ_p² = Σᵢⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ

    Args:
        positions: List of position dicts with 'asset' and 'value' keys
        asset_returns: Dict mapping asset to returns array
        correlation_matrix: Correlation matrix from calculate_correlation_matrix()

    Returns:
        Portfolio variance
    """
    if not positions:
        return 0.0

    # Calculate total portfolio value
    total_value = sum(pos.get("value", 0) for pos in positions)
    if total_value == 0:
        return 0.0

    # Calculate weights
    weights = {
        pos["asset"]: pos.get("value", 0) / total_value for pos in positions
    }

    # Calculate asset volatilities
    volatilities = {
        asset: np.std(returns, ddof=1) if len(returns) > 0 else 0.0
        for asset, returns in asset_returns.items()
    }

    # Calculate portfolio variance
    variance = 0.0
    assets = list(weights.keys())

    for i, asset1 in enumerate(assets):
        for j, asset2 in enumerate(assets):
            w1 = weights.get(asset1, 0)
            w2 = weights.get(asset2, 0)
            sigma1 = volatilities.get(asset1, 0)
            sigma2 = volatilities.get(asset2, 0)
            rho = correlation_matrix.get(asset1, {}).get(asset2, 0)

            variance += w1 * w2 * sigma1 * sigma2 * rho

    return float(variance)


def calculate_net_apy(
    supply_positions: list[dict],
    borrow_positions: list[dict],
    current_rates: dict[str, dict[str, float]],
) -> tuple[float, float, float]:
    """
    Calculate net APY and weighted averages for lending positions.

    Args:
        supply_positions: List of supply position dicts with 'asset' and 'value' keys
        borrow_positions: List of borrow position dicts with 'asset', 'value', and 'borrow_type' keys
        current_rates: Dict of {asset: {supply_rate: float (RAY), variable_borrow_rate: float (RAY), stable_borrow_rate: float (RAY)}}

    Returns:
        Tuple of (net_apy, weighted_supply_apy, weighted_borrow_apy)
        All values are in percentage (e.g., 5.25 for 5.25%)
    """
    # Calculate total supply value and weighted supply APY
    total_supply_value = 0.0
    weighted_supply_apy_sum = 0.0

    for pos in supply_positions:
        asset = pos["asset"]
        value = pos.get("value", 0.0)
        total_supply_value += value

        # Get supply rate for this asset
        if asset in current_rates and "supply_rate" in current_rates[asset]:
            supply_rate_ray = current_rates[asset]["supply_rate"]
            supply_apy = convert_ray_to_apy(supply_rate_ray)
            weighted_supply_apy_sum += value * supply_apy
        else:
            logger.warning(f"No supply rate found for asset {asset}, using 0%")

    # Calculate total borrow value and weighted borrow APY
    total_borrow_value = 0.0
    weighted_borrow_apy_sum = 0.0

    for pos in borrow_positions:
        asset = pos["asset"]
        value = abs(pos.get("value", 0.0))  # Borrow value should be positive for calculations
        borrow_type = pos.get("borrow_type", "variable")
        total_borrow_value += value

        # Get borrow rate for this asset
        if asset in current_rates:
            if borrow_type == "stable" and "stable_borrow_rate" in current_rates[asset]:
                borrow_rate_ray = current_rates[asset]["stable_borrow_rate"]
            elif "variable_borrow_rate" in current_rates[asset]:
                borrow_rate_ray = current_rates[asset]["variable_borrow_rate"]
            else:
                logger.warning(f"No {borrow_type} borrow rate found for asset {asset}, using 0%")
                borrow_rate_ray = 0

            borrow_apy = convert_ray_to_apy(borrow_rate_ray)
            weighted_borrow_apy_sum += value * borrow_apy
        else:
            logger.warning(f"No borrow rates found for asset {asset}, using 0%")

    # Calculate weighted averages
    weighted_supply_apy = (
        weighted_supply_apy_sum / total_supply_value if total_supply_value > 0 else 0.0
    )
    weighted_borrow_apy = (
        weighted_borrow_apy_sum / total_borrow_value if total_borrow_value > 0 else 0.0
    )

    # Calculate net APY
    # Net APY = (total_supply_yield - total_borrow_cost) / net_value
    total_supply_yield = weighted_supply_apy_sum
    total_borrow_cost = weighted_borrow_apy_sum
    net_value = total_supply_value - total_borrow_value

    if net_value > 0:
        net_apy = (total_supply_yield - total_borrow_cost) / net_value
    elif net_value < 0:
        # If net value is negative (over-leveraged), net APY is negative
        net_apy = (total_supply_yield - total_borrow_cost) / abs(net_value)
    else:
        # If net value is exactly 0, return 0
        net_apy = 0.0

    logger.debug(
        f"Net APY: {net_apy:.2f}% (supply: {weighted_supply_apy:.2f}%, borrow: {weighted_borrow_apy:.2f}%)"
    )

    return float(net_apy), float(weighted_supply_apy), float(weighted_borrow_apy)
