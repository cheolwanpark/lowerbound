"""Portfolio position valuation logic."""

from typing import Any


def calculate_spot_value(quantity: float, current_price: float) -> float:
    """
    Calculate the value of a spot position.

    Args:
        quantity: Number of units held
        current_price: Current market price

    Returns:
        Total value in USD
    """
    return quantity * current_price


def calculate_futures_long_value(
    quantity: float, entry_price: float, current_price: float, leverage: float
) -> float:
    """
    Calculate the value of a futures long position.

    Formula:
        Margin = (quantity × entry_price) / leverage
        PnL = (current_price - entry_price) × quantity
        Value = Margin + PnL

    Args:
        quantity: Number of contracts
        entry_price: Entry price of the position
        current_price: Current futures mark price
        leverage: Position leverage (only affects margin, not PnL)

    Returns:
        Total position value (margin + unrealized PnL)
    """
    margin = (quantity * entry_price) / leverage
    pnl = (current_price - entry_price) * quantity  # Leverage does NOT multiply PnL
    return margin + pnl


def calculate_futures_short_value(
    quantity: float, entry_price: float, current_price: float, leverage: float
) -> float:
    """
    Calculate the value of a futures short position.

    Formula:
        Margin = (quantity × entry_price) / leverage
        PnL = (entry_price - current_price) × quantity
        Value = Margin + PnL

    Args:
        quantity: Number of contracts
        entry_price: Entry price of the position
        current_price: Current futures mark price
        leverage: Position leverage (only affects margin, not PnL)

    Returns:
        Total position value (margin + unrealized PnL)
    """
    margin = (quantity * entry_price) / leverage
    pnl = (entry_price - current_price) * quantity  # Leverage does NOT multiply PnL
    return margin + pnl


def calculate_position_value(
    position: dict[str, Any],
    current_prices: dict[tuple[str, str] | str, float],
    current_indices: dict[str, dict[str, float]] | None = None,
) -> float:
    """
    Calculate the value of a single position.

    Args:
        position: Dict with keys: asset, quantity, position_type, leverage, entry_price
        current_prices: Dict mapping (asset, position_type) tuple or asset string to current price
        current_indices: Dict mapping asset to {liquidity_index, variable_borrow_index} (for lending)

    Returns:
        Position value in USD
    """
    asset = position["asset"]
    quantity = position["quantity"]
    position_type = position["position_type"]
    entry_price = position.get("entry_price", 0.0)
    leverage = position.get("leverage", 1.0)

    # Handle lending positions
    if position_type in ["lending_supply", "lending_borrow"]:
        if current_indices is None:
            raise ValueError("Lending positions require current_indices parameter")

        indices = current_indices.get(asset, {})
        entry_index = position.get("entry_index")
        if entry_index is None:
            raise ValueError(f"Position missing entry_index for {position_type}")

        # Convert entry_index from string to float
        entry_index = float(entry_index)

        if position_type == "lending_supply":
            current_index = indices.get("liquidity_index")
            if current_index is None:
                raise ValueError(f"No liquidity_index available for {asset}")
            return calculate_lending_supply_value(quantity, entry_index, current_index)

        else:  # lending_borrow
            current_index = indices.get("variable_borrow_index")
            if current_index is None:
                raise ValueError(f"No variable_borrow_index available for {asset}")
            borrow_type = position.get("borrow_type", "variable")
            return calculate_lending_borrow_value(quantity, entry_index, current_index, borrow_type)

    # Handle spot/futures positions (existing logic)
    # Try composite key first (asset, position_type), fallback to asset string
    price_key = (asset, position_type)
    current_price = current_prices.get(price_key)
    if current_price is None:
        # Fallback to simple asset key for backwards compatibility
        current_price = current_prices.get(asset)

    if current_price is None:
        raise ValueError(f"No current price available for {asset} ({position_type})")

    if position_type == "spot":
        return calculate_spot_value(quantity, current_price)
    elif position_type == "futures_long":
        return calculate_futures_long_value(quantity, entry_price, current_price, leverage)
    elif position_type == "futures_short":
        return calculate_futures_short_value(quantity, entry_price, current_price, leverage)
    else:
        raise ValueError(f"Unknown position type: {position_type}")


def calculate_portfolio_value(
    positions: list[dict[str, Any]],
    current_prices: dict[str, float],
    current_indices: dict[str, dict[str, float]] | None = None,
) -> float:
    """
    Calculate total portfolio value across all positions.

    Args:
        positions: List of position dicts
        current_prices: Dict mapping asset to current price
        current_indices: Dict mapping asset to indices (for lending positions)

    Returns:
        Total portfolio value in USD
    """
    total_value = 0.0
    for position in positions:
        total_value += calculate_position_value(position, current_prices, current_indices)
    return total_value


def apply_price_shock(
    base_prices: dict[str, float], shock_pct: float
) -> dict[str, float]:
    """
    Apply a percentage price shock to all assets.

    Args:
        base_prices: Dict mapping asset to base price
        shock_pct: Percentage change (e.g., 0.10 for +10%, -0.20 for -20%)

    Returns:
        Dict mapping asset to shocked price
    """
    return {asset: price * (1 + shock_pct) for asset, price in base_prices.items()}


def calculate_delta_exposure(positions: list[dict[str, Any]]) -> float:
    """
    Calculate total delta exposure (market directional risk).

    Delta represents notional exposure to price movements.
    Leverage affects margin requirements but NOT directional exposure.

    Formula:
        Delta = Σ(spot quantities) + Σ(futures_long quantities) - Σ(futures_short quantities)

    Args:
        positions: List of position dicts

    Returns:
        Total delta exposure (positive = net long, negative = net short)
    """
    delta = 0.0

    for position in positions:
        quantity = position["quantity"]
        position_type = position["position_type"]

        if position_type == "spot":
            delta += quantity
        elif position_type == "futures_long":
            delta += quantity  # Leverage does NOT affect delta
        elif position_type == "futures_short":
            delta -= quantity  # Leverage does NOT affect delta

    return delta


def calculate_sensitivity_table(
    positions: list[dict[str, Any]],
    base_prices: dict[str, float],
    shock_range: list[float],
    current_indices: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, float]]:
    """
    Calculate portfolio sensitivity to price shocks.

    Args:
        positions: List of position dicts
        base_prices: Dict mapping asset to base (current) price
        shock_range: List of shock percentages (e.g., [-0.30, -0.25, ..., 0.30])
        current_indices: Optional dict of current lending indices for lending positions

    Returns:
        List of dicts with keys: price_change_pct, portfolio_value, pnl, return_pct
    """
    base_value = calculate_portfolio_value(positions, base_prices, current_indices)
    sensitivity_table = []

    for shock_pct in shock_range:
        # Only apply price shocks if there are prices to shock
        # Lending-only portfolios have no price sensitivity
        if base_prices:
            shocked_prices = apply_price_shock(base_prices, shock_pct)
            shocked_value = calculate_portfolio_value(positions, shocked_prices, current_indices)
        else:
            # No prices to shock (lending-only portfolio)
            shocked_value = base_value

        pnl = shocked_value - base_value
        return_pct = pnl / base_value if base_value != 0 else 0.0

        sensitivity_table.append(
            {
                "price_change_pct": shock_pct * 100,  # Convert to percentage
                "portfolio_value": shocked_value,
                "pnl": pnl,
                "return_pct": return_pct * 100,  # Convert to percentage
            }
        )

    return sensitivity_table


# ==================== Lending Position Valuation ====================


def calculate_lending_supply_value(
    initial_amount: float, entry_index: float, current_index: float
) -> float:
    """
    Calculate current value of lending supply position with accrued interest.

    Uses Aave liquidity index to calculate value with accrued supply interest.

    Formula: value = initial_amount × (current_index / entry_index)

    Example:
        Supplied 10 WETH when index was 1.05, now index is 1.10
        Value = 10 × (1.10 / 1.05) = 10.476 WETH

    Args:
        initial_amount: Initial supply amount
        entry_index: Liquidity index when position was opened
        current_index: Current liquidity index

    Returns:
        Current position value with accrued interest
    """
    if entry_index <= 0:
        raise ValueError("entry_index must be positive")
    if current_index <= 0:
        raise ValueError("current_index must be positive")

    return initial_amount * (current_index / entry_index)


def calculate_lending_borrow_value(
    initial_amount: float, entry_index: float, current_index: float, borrow_type: str
) -> float:
    """
    Calculate current debt of lending borrow position with accrued interest.

    Uses Aave borrow index to calculate debt with accrued borrow interest.

    Formula:
        For variable borrows: debt = initial_amount × (current_index / entry_index)
        For stable borrows: Similar calculation with stable borrow index

    Args:
        initial_amount: Initial borrow amount
        entry_index: Borrow index when position was opened
        current_index: Current borrow index
        borrow_type: "variable" or "stable"

    Returns:
        Current debt (NEGATIVE value representing debt)
    """
    if entry_index <= 0:
        raise ValueError("entry_index must be positive")
    if current_index <= 0:
        raise ValueError("current_index must be positive")

    if borrow_type == "variable":
        debt = initial_amount * (current_index / entry_index)
    elif borrow_type == "stable":
        # Stable borrows track interest differently
        # For simplicity, approximate using same formula
        # TODO: Implement proper stable rate tracking if needed
        debt = initial_amount * (current_index / entry_index)
    else:
        raise ValueError(f"Invalid borrow_type: {borrow_type} (must be 'variable' or 'stable')")

    return -float(debt)  # Negative = debt


def calculate_account_ltv(total_borrowed: float, total_collateral: float) -> float:
    """
    Calculate account-level loan-to-value ratio.

    LTV = Total Borrowed / Total Collateral

    Args:
        total_borrowed: Total borrowed amount (USD)
        total_collateral: Total collateral (supply) amount (USD)

    Returns:
        LTV ratio (0.0 to 1.0+)
        Returns 0.0 if no collateral (avoid division by zero)
    """
    if total_collateral <= 0:
        return 0.0
    return total_borrowed / total_collateral


def calculate_health_factor(
    positions: list[dict[str, Any]],
    total_borrowed: float,
    liquidation_thresholds: dict[str, float],
) -> float:
    """
    Calculate Aave health factor (ACCOUNT-LEVEL metric).

    Health Factor = Σ(collateral_value × liquidation_threshold) / total_borrowed

    Interpretation:
        HF > 2.0: Safe
        1.0 < HF < 2.0: Moderate risk
        HF < 1.0: Liquidation occurs
        HF = inf: No debt (infinite health)

    Args:
        positions: ALL supply positions in portfolio
        total_borrowed: Total borrowed amount (USD)
        liquidation_thresholds: Dict mapping asset to liquidation threshold (0-1)

    Returns:
        Health factor (>1 = safe, <1 = liquidation risk)
    """
    if total_borrowed <= 0:
        return float("inf")  # No debt = infinite health

    weighted_collateral = 0.0
    for pos in positions:
        if pos.get("position_type") != "lending_supply":
            continue

        asset = pos["asset"]
        value = pos.get("value", 0)
        # Use asset-specific liquidation threshold, default to 0.50 if unknown
        liq_threshold = liquidation_thresholds.get(asset, 0.50)

        weighted_collateral += value * liq_threshold

    if weighted_collateral <= 0:
        return 0.0  # No collateral = zero health

    return weighted_collateral / total_borrowed
