"""Configuration management using Pydantic Settings."""

from pydantic import Field, PostgresDsn
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
        default=5000,
        description="Rate limit for Binance API (safety margin below 6000)",
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

    # Lending (Aave) specific settings
    tracked_lending_assets: str = Field(
        default="WETH,WBTC,USDC,USDT,DAI",
        description="Comma-separated list of Aave assets to track (use Aave native symbols)",
    )
    lending_fetch_interval_hours: int = Field(
        default=8,
        description="Interval between lending data fetches in hours (check for new events)",
    )
    initial_lending_backfill_days: int = Field(
        default=730,
        description="Days to backfill for lending data (limited by Aave V3 launch: Mar 2022)",
    )
    aave_v3_graphql_url: str = Field(
        default="https://api.thegraph.com/subgraphs/name/aave/protocol-v3",
        description="Aave V3 GraphQL API endpoint (The Graph hosted service)",
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
