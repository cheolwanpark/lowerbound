"""Shared validation constants and helper functions for portfolio advisory tools."""

import re
from datetime import datetime
from typing import Any, Dict, Optional

# Asset validation constants
VALID_SPOT_FUTURES_ASSETS = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "LINK"}
VALID_LENDING_ASSETS = {"WETH", "WBTC", "USDC", "USDT", "DAI"}
LENDING_SYMBOL_MAPPING = {"BTC": "WBTC", "ETH": "WETH"}

# Position type constants
VALID_POSITION_TYPES = {
    "spot",
    "futures_long",
    "futures_short",
    "lending_supply",
    "lending_borrow"
}

# Validation ranges
MIN_QUANTITY = 0.0  # exclusive
MIN_ENTRY_PRICE = 0.0  # exclusive
MIN_LEVERAGE = 0.0  # exclusive
MAX_LEVERAGE = 125.0
MIN_LOOKBACK_DAYS = 7
MAX_LOOKBACK_DAYS = 180
MIN_POSITIONS = 1
MAX_POSITIONS = 20

# ISO 8601 UTC datetime regex pattern
ISO8601_UTC_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$'
)


def validate_asset(asset: str, data_type: str) -> Optional[str]:
    """Validate asset symbol against available assets.

    Args:
        asset: Asset symbol to validate
        data_type: Type of data ("spot", "futures", or "lending")

    Returns:
        Error message if invalid, None if valid
    """
    asset_upper = asset.upper()

    if data_type in ("spot", "futures"):
        if asset_upper not in VALID_SPOT_FUTURES_ASSETS:
            return (
                f"Invalid asset '{asset}' for {data_type} data. "
                f"Available assets: {', '.join(sorted(VALID_SPOT_FUTURES_ASSETS))}"
            )
    elif data_type == "lending":
        # Check if it's a valid lending asset or can be mapped
        mapped_asset = LENDING_SYMBOL_MAPPING.get(asset_upper, asset_upper)
        if mapped_asset not in VALID_LENDING_ASSETS:
            return (
                f"Invalid asset '{asset}' for lending data. "
                f"Available assets: {', '.join(sorted(VALID_LENDING_ASSETS))} "
                f"(BTC and ETH auto-map to WBTC and WETH)"
            )

    return None


def validate_date_format(date_str: str, field_name: str) -> Optional[str]:
    """Validate ISO 8601 UTC datetime format.

    Args:
        date_str: Date string to validate
        field_name: Name of the field for error message

    Returns:
        Error message if invalid, None if valid
    """
    if not ISO8601_UTC_PATTERN.match(date_str):
        return (
            f"Invalid {field_name} format: '{date_str}'. "
            f"Must be ISO 8601 UTC format (e.g., '2025-01-01T00:00:00Z'). "
            f"Common mistakes: missing 'T' separator, missing 'Z' timezone, "
            f"using space instead of 'T', or omitting time component."
        )

    # Additional validation: try parsing to ensure it's a valid date
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError as e:
        return f"Invalid {field_name}: {str(e)}"

    return None


def validate_date_range(start: str, end: str, max_days: int) -> Optional[str]:
    """Validate date range doesn't exceed maximum.

    Args:
        start: Start date (ISO 8601 UTC)
        end: End date (ISO 8601 UTC)
        max_days: Maximum allowed range in days

    Returns:
        Error message if invalid, None if valid
    """
    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))

        if end_dt <= start_dt:
            return f"end_date must be after start_date (start: {start}, end: {end})"

        delta_days = (end_dt - start_dt).days
        if delta_days > max_days:
            return (
                f"Date range too large: {delta_days} days (max {max_days} days). "
                f"Please reduce the range or split into multiple queries."
            )
    except Exception as e:
        return f"Failed to parse date range: {str(e)}"

    return None


def validate_position(position: Dict[str, Any], index: int) -> Optional[str]:
    """Validate a single position structure and values.

    Args:
        position: Position dictionary to validate
        index: Position index for error messages

    Returns:
        Error message if invalid, None if valid
    """
    # Check required base fields
    if "asset" not in position:
        return f"Position {index}: Missing required field 'asset'"

    if "quantity" not in position:
        return f"Position {index}: Missing required field 'quantity'"

    if "position_type" not in position:
        return f"Position {index}: Missing required field 'position_type'"

    # Validate position_type
    pos_type = position["position_type"]
    if pos_type not in VALID_POSITION_TYPES:
        return (
            f"Position {index}: Invalid position_type '{pos_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_POSITION_TYPES))}. "
            f"Common mistakes: using 'long' instead of 'futures_long', "
            f"'short' instead of 'futures_short'."
        )

    # Validate quantity
    quantity = position.get("quantity", 0)
    if not isinstance(quantity, (int, float)) or quantity <= MIN_QUANTITY:
        return f"Position {index}: quantity must be a positive number (got {quantity})"

    # Validate type-specific required fields
    if pos_type in ("spot", "futures_long", "futures_short"):
        # Spot and futures require entry_price
        if "entry_price" not in position:
            return f"Position {index}: Missing required field 'entry_price' for {pos_type}"

        entry_price = position["entry_price"]
        if not isinstance(entry_price, (int, float)) or entry_price <= MIN_ENTRY_PRICE:
            return f"Position {index}: entry_price must be a positive number (got {entry_price})"

        # Futures require leverage
        if pos_type in ("futures_long", "futures_short"):
            leverage = position.get("leverage", 1.0)
            if not isinstance(leverage, (int, float)) or leverage <= MIN_LEVERAGE or leverage > MAX_LEVERAGE:
                return (
                    f"Position {index}: leverage must be between {MIN_LEVERAGE} (exclusive) "
                    f"and {MAX_LEVERAGE} (got {leverage})"
                )

    elif pos_type in ("lending_supply", "lending_borrow"):
        # Lending requires entry_timestamp
        if "entry_timestamp" not in position:
            return (
                f"Position {index}: Missing required field 'entry_timestamp' for {pos_type}. "
                f"Provide the ISO 8601 UTC timestamp when the position was opened "
                f"(e.g., '2025-01-01T00:00:00Z')"
            )

        # Validate timestamp format
        timestamp = position["entry_timestamp"]
        error = validate_date_format(timestamp, "entry_timestamp")
        if error:
            return f"Position {index}: {error}"

        # Borrow positions need borrow_type
        if pos_type == "lending_borrow" and "borrow_type" not in position:
            return (
                f"Position {index}: Missing required field 'borrow_type' for lending_borrow. "
                f"Must be either 'variable' or 'stable'"
            )

        if pos_type == "lending_borrow":
            borrow_type = position.get("borrow_type")
            if borrow_type not in ("variable", "stable"):
                return (
                    f"Position {index}: borrow_type must be 'variable' or 'stable' "
                    f"(got '{borrow_type}')"
                )

    # Validate asset based on position type
    asset = position["asset"]
    if pos_type in ("spot", "futures_long", "futures_short"):
        error = validate_asset(asset, "spot")  # spot and futures use same asset list
        if error:
            return f"Position {index}: {error}"
    else:  # lending positions
        error = validate_asset(asset, "lending")
        if error:
            return f"Position {index}: {error}"

    return None
