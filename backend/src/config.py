"""Configuration management using Pydantic Settings."""

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql://crypto:password@localhost:5432/portfolio",
        description="PostgreSQL connection string",
    )

    # Binance API
    binance_api_base_url: str = Field(
        default="https://api.binance.com",
        description="Binance API base URL",
    )
    binance_futures_api_base_url: str = Field(
        default="https://fapi.binance.com",
        description="Binance Futures API base URL",
    )
    binance_rate_limit_requests_per_minute: int = Field(
        default=2440,
        description="Rate limit for Binance API",
    )
    binance_request_delay_ms: int = Field(
        default=100,
        description="Delay between requests in milliseconds",
    )

    # Scheduler
    fetch_interval_hours: int = Field(
        default=12,
        description="Interval between scheduled fetches in hours",
    )
    initial_backfill_days: int = Field(
        default=730,
        description="Days to backfill on initial run (2 years = 730)",
    )
    min_backfill_days: int = Field(
        default=90,
        description="Minimum days to fetch if full backfill unavailable",
    )

    # Security
    api_key: str = Field(
        default="change-this-in-production",
        description="API key for protected endpoints",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # Assets
    tracked_assets: str = Field(
        default="BTC,ETH,SOL,BNB,XRP,ADA,LINK",
        description="Comma-separated list of assets to track for spot markets",
    )
    tracked_futures_assets: str = Field(
        default="BTC,ETH,SOL,BNB,XRP,ADA,LINK",
        description="Comma-separated list of assets to track for futures markets",
    )

    # Futures specific settings
    futures_funding_interval_hours: int = Field(
        default=8,
        description="Funding rate interval in hours (Binance perpetuals use 8h)",
    )
    futures_klines_interval: str = Field(
        default="8h",
        description="Interval for mark/index price klines (e.g., 1h, 4h, 8h, 1d)",
    )
    futures_oi_period: str = Field(
        default="5m",
        description="Period for open interest data (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d)",
    )

    # Lending (Dune Analytics) specific settings
    tracked_lending_assets: str = Field(
        default="WETH,WBTC,USDC,USDT,DAI",
        description="Comma-separated list of lending assets to track",
    )
    lending_fetch_interval_hours: int = Field(
        default=24,
        description="Interval between lending data fetches in hours (Dune query provides daily snapshots)",
    )
    initial_lending_backfill_days: int = Field(
        default=730,
        description="Days to backfill for lending data on initial setup",
    )
    dune_api_key: SecretStr | None = Field(
        default=None,
        description="Dune Analytics API key for data fetching",
    )
    dune_lending_query_id: int = Field(
        default=3328916,
        description="Dune Analytics query ID for lending market data",
    )

    # Risk Analysis settings
    RISK_ANALYSIS_DEFAULT_LOOKBACK_DAYS: int = Field(
        default=30,
        description="Default historical data lookback period for risk analysis (days)",
    )
    RISK_ANALYSIS_MAX_LOOKBACK_DAYS: int = Field(
        default=180,
        description="Maximum allowed lookback period for risk analysis (days)",
    )
    FUNDING_RATE_LOOKBACK_DAYS: int = Field(
        default=30,
        description="Funding rate data availability limit (hard constraint)",
    )

    # Position limits
    MAX_PORTFOLIO_POSITIONS: int = Field(
        default=20,
        description="Maximum number of positions allowed in a portfolio",
    )
    MAX_LEVERAGE_LIMIT: float = Field(
        default=125.0,
        description="Maximum leverage allowed for futures positions",
    )

    # Risk calculation parameters
    SENSITIVITY_RANGE: list[int] = Field(
        default=[-30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30],
        description="Price shock range for sensitivity analysis (percentages)",
    )
    VAR_CONFIDENCE_LEVELS: list[float] = Field(
        default=[0.95, 0.99],
        description="Confidence levels for VaR calculations",
    )
    RISK_FREE_RATE: float = Field(
        default=0.0,
        description="Annual risk-free rate for Sharpe ratio (0.0 = 0%)",
    )

    # Query optimization
    QUERY_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Maximum time allowed for database queries in risk analysis",
    )

    # Aave V3 Lending Protocol Parameters (Ethereum Mainnet)
    # Source: Aave V3 Risk Parameters (hardcoded, accurate as of 2025)
    AAVE_LIQUIDATION_THRESHOLDS: dict[str, float] = Field(
        default={
            "WETH": 0.825,  # 82.5% liquidation threshold
            "WBTC": 0.750,  # 75%
            "USDC": 0.870,  # 87%
            "USDT": 0.870,  # 87%
            "DAI": 0.800,   # 80%
        },
        description="Liquidation thresholds per asset (LTV at which liquidation occurs)",
    )

    AAVE_MAX_LTV: dict[str, float] = Field(
        default={
            "WETH": 0.800,  # 80% maximum LTV
            "WBTC": 0.700,  # 70%
            "USDC": 0.850,  # 85%
            "USDT": 0.850,  # 85%
            "DAI": 0.750,   # 75%
        },
        description="Maximum LTV allowed for borrowing per asset",
    )

    AAVE_LIQUIDATION_BONUS: float = Field(
        default=0.05,
        description="Liquidation bonus percentage (5% = 0.05)",
    )

    # Lending data staleness validation
    LENDING_DATA_MAX_AGE_HOURS: int = Field(
        default=48,
        description="Maximum age of lending data before warning (hours)",
    )

    @property
    def assets_list(self) -> list[str]:
        """Parse tracked assets into a list."""
        return [asset.strip().upper() for asset in self.tracked_assets.split(",")]

    @property
    def futures_assets_list(self) -> list[str]:
        """Parse tracked futures assets into a list."""
        return [asset.strip().upper() for asset in self.tracked_futures_assets.split(",")]

    @property
    def lending_assets_list(self) -> list[str]:
        """Parse tracked lending assets into a list."""
        return [asset.strip().upper() for asset in self.tracked_lending_assets.split(",")]

    @property
    def lending_asset_symbol_map(self) -> dict[str, str]:
        """
        Map common asset symbols to Aave reserve symbols.

        Allows API users to query with 'BTC' or 'ETH' and automatically
        map to 'WBTC' or 'WETH' for Aave reserves.
        """
        return {
            "BTC": "WBTC",
            "ETH": "WETH",
            "WBTC": "WBTC",
            "WETH": "WETH",
            "USDC": "USDC",
            "USDT": "USDT",
            "DAI": "DAI",
        }

    @property
    def database_url_str(self) -> str:
        """Get database URL as string."""
        return str(self.database_url)


# Global settings instance
settings = Settings()


def get_config() -> Settings:
    """Get the global settings instance."""
    return settings
