"""Scenario analysis definitions and execution."""

from typing import Any

from src.analysis.valuation import apply_price_shock, calculate_portfolio_value

# Predefined scenario definitions
SCENARIOS = {
    "bull_market": {
        "name": "Bull Market (+30%)",
        "description": "All assets increase by 30%",
        "shock_type": "uniform",
        "shock_value": 0.30,
    },
    "bear_market": {
        "name": "Bear Market (-30%)",
        "description": "All assets decrease by 30%",
        "shock_type": "uniform",
        "shock_value": -0.30,
    },
    "crypto_winter": {
        "name": "Crypto Winter (-50%)",
        "description": "Severe bear market with 50% decline across all assets",
        "shock_type": "uniform",
        "shock_value": -0.50,
    },
    "moderate_rally": {
        "name": "Moderate Rally (+15%)",
        "description": "Moderate upward movement of 15%",
        "shock_type": "uniform",
        "shock_value": 0.15,
    },
    "flash_crash": {
        "name": "Flash Crash (-20%)",
        "description": "Sudden sharp decline of 20%",
        "shock_type": "uniform",
        "shock_value": -0.20,
    },
    "btc_dominance": {
        "name": "BTC Dominance",
        "description": "BTC +40%, other assets -10%",
        "shock_type": "asset_specific",
        "shocks": {"BTC": 0.40, "default": -0.10},
    },
    "alt_season": {
        "name": "Alt Season",
        "description": "Altcoins rally: ETH/SOL +50%, BTC +20%",
        "shock_type": "asset_specific",
        "shocks": {"BTC": 0.20, "ETH": 0.50, "SOL": 0.50, "default": 0.35},
    },
    "risk_off": {
        "name": "Risk-Off Environment",
        "description": "Flight to quality: BTC -15%, altcoins -35%",
        "shock_type": "asset_specific",
        "shocks": {"BTC": -0.15, "default": -0.35},
    },
}


def run_scenario(
    positions: list[dict[str, Any]],
    base_prices: dict[str, float],
    scenario_def: dict[str, Any],
    current_indices: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    """
    Run a scenario analysis on the portfolio.

    Args:
        positions: List of position dicts
        base_prices: Dict mapping asset to base (current) price
        scenario_def: Scenario definition dict with keys: name, description, shock_type, shock_value/shocks
        current_indices: Optional dict of current lending indices for lending positions

    Returns:
        Dict with keys: name, description, portfolio_value, pnl, return_pct
    """
    base_value = calculate_portfolio_value(positions, base_prices, current_indices)

    # Only apply shocks if there are prices to shock
    # Lending-only portfolios have no price sensitivity
    if base_prices:
        # Apply scenario shocks
        if scenario_def["shock_type"] == "uniform":
            # Apply uniform shock to all assets
            shocked_prices = apply_price_shock(base_prices, scenario_def["shock_value"])
        elif scenario_def["shock_type"] == "asset_specific":
            # Apply asset-specific shocks
            shocks = scenario_def["shocks"]
            default_shock = shocks.get("default", 0.0)
            shocked_prices = {}
            for asset, price in base_prices.items():
                shock = shocks.get(asset, default_shock)
                shocked_prices[asset] = price * (1 + shock)
        else:
            raise ValueError(f"Unknown shock type: {scenario_def['shock_type']}")

        # Calculate portfolio value under scenario
        scenario_value = calculate_portfolio_value(positions, shocked_prices, current_indices)
    else:
        # No prices to shock (lending-only portfolio) - value remains same
        scenario_value = base_value

    pnl = scenario_value - base_value
    return_pct = (pnl / base_value * 100) if base_value != 0 else 0.0

    return {
        "name": scenario_def["name"],
        "description": scenario_def["description"],
        "portfolio_value": scenario_value,
        "pnl": pnl,
        "return_pct": return_pct,
    }


def run_all_scenarios(
    positions: list[dict[str, Any]],
    base_prices: dict[str, float],
    current_indices: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    """
    Run all predefined scenarios on the portfolio.

    Args:
        positions: List of position dicts
        base_prices: Dict mapping asset to base (current) price
        current_indices: Optional dict of current lending indices for lending positions

    Returns:
        List of scenario result dicts
    """
    results = []
    for scenario_key, scenario_def in SCENARIOS.items():
        result = run_scenario(positions, base_prices, scenario_def, current_indices)
        results.append(result)
    return results


def create_custom_scenario(
    name: str,
    description: str,
    asset_shocks: dict[str, float] | None = None,
    uniform_shock: float | None = None,
) -> dict[str, Any]:
    """
    Create a custom scenario definition.

    Args:
        name: Scenario name
        description: Scenario description
        asset_shocks: Dict mapping asset to shock percentage (e.g., {"BTC": 0.20, "ETH": -0.10})
        uniform_shock: Uniform shock to apply to all assets (if asset_shocks not provided)

    Returns:
        Scenario definition dict
    """
    if asset_shocks is not None:
        return {
            "name": name,
            "description": description,
            "shock_type": "asset_specific",
            "shocks": asset_shocks,
        }
    elif uniform_shock is not None:
        return {
            "name": name,
            "description": description,
            "shock_type": "uniform",
            "shock_value": uniform_shock,
        }
    else:
        raise ValueError("Must provide either asset_shocks or uniform_shock")
