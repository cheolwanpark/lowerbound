"""Lending data fetcher using Dune Analytics."""

from datetime import datetime, timezone

from loguru import logger

from src.config import settings
from src.database import upsert_lending_batch
from src.fetch.dune_client import DuneClient

# Validation constants for RAY format values
MAX_RATE_RAY = int(2e27)  # 200% APY maximum
MIN_INDEX_RAY = int(1e27)  # Liquidity indices start at 1.0 in RAY
MAX_INDEX_RAY = int(1e30)  # Upper bound for indices


class LendingFetcher:
    """Fetcher for lending market data from Dune Analytics."""

    def __init__(self, dune_client: DuneClient):
        """
        Initialize lending fetcher.

        Args:
            dune_client: Configured DuneClient instance
        """
        self.client = dune_client

    def _validate_lending_data(self, data_dict: dict) -> bool:
        """
        Validate lending data before database insertion.

        Args:
            data_dict: Data dictionary from DuneLendingData.to_dict()

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check timestamp is not in future
            if data_dict["timestamp"] > datetime.now(timezone.utc):
                logger.warning(f"Future timestamp detected: {data_dict['timestamp']}")
                return False

            # Check reserve address format (basic Ethereum address validation)
            reserve = data_dict.get("reserve_address", "")
            if not reserve.startswith("0x") or len(reserve) != 42:
                logger.warning(f"Invalid reserve address format: {reserve}")
                return False

            # Check RAY rates are positive and within reasonable range (0 to 200% APY)
            for rate_field in [
                "supply_rate_ray",
                "variable_borrow_rate_ray",
                "stable_borrow_rate_ray",
            ]:
                rate_str = data_dict.get(rate_field, "0")
                rate_int = int(rate_str)
                if rate_int < 0 or rate_int > MAX_RATE_RAY:
                    logger.warning(
                        f"Rate {rate_field} out of range (0-200% APY): {rate_int}"
                    )
                    return False

            # Check indices are within reasonable range
            for index_field in ["liquidity_index", "variable_borrow_index"]:
                index_str = data_dict.get(index_field, "0")
                index_int = int(index_str)
                if index_int < MIN_INDEX_RAY or index_int > MAX_INDEX_RAY:
                    logger.warning(f"Index {index_field} out of range: {index_int}")
                    return False

            return True

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Validation error: {e}")
            return False

    async def fetch_dune_lending(self, max_age_hours: int = 24) -> dict[str, int]:
        """
        Fetch lending market data from Dune Analytics.

        Unlike the previous event-based Aave fetching, Dune provides
        pre-aggregated data snapshots (typically daily).

        Args:
            max_age_hours: Maximum age of cached Dune results (hours)

        Returns:
            Dict mapping asset to number of data points stored
        """
        try:
            logger.info(f"Fetching lending data from Dune (max_age={max_age_hours}h)")

            # Fetch all lending data from Dune
            lending_data_list = await self.client.get_lending_data(max_age_hours=max_age_hours)

            if not lending_data_list:
                logger.warning("No lending data returned from Dune")
                return {}

            # Group data by asset
            data_by_asset: dict[str, list[dict]] = {}

            for lending_data in lending_data_list:
                asset = lending_data.symbol
                data_dict = lending_data.to_dict()

                # Validate data
                if not self._validate_lending_data(data_dict):
                    logger.warning(f"Skipping invalid data for {asset}: {data_dict}")
                    continue

                if asset not in data_by_asset:
                    data_by_asset[asset] = []

                data_by_asset[asset].append(data_dict)

            # Store data for each asset
            results = {}

            for asset, data_list in data_by_asset.items():
                try:
                    logger.info(f"Storing {len(data_list)} data points for {asset}")

                    # Batch upsert to database
                    stored_count = await upsert_lending_batch(asset, data_list)
                    results[asset] = stored_count

                    logger.info(f"Stored {stored_count} data points for {asset}")

                except Exception as e:
                    logger.error(f"Failed to store lending data for {asset}: {e}")
                    results[asset] = 0

            total = sum(results.values())
            logger.info(
                f"Dune fetch complete: {total} total data points across {len(results)} assets"
            )

            return results

        except Exception as e:
            logger.error(f"Error fetching lending data from Dune: {e}")
            raise

    async def fetch_for_asset(self, asset: str, max_age_hours: int = 24) -> int:
        """
        Fetch lending data for a specific asset from Dune.

        Note: Dune query returns data for ALL assets, so this fetches all data
        but only stores/counts the specified asset.

        Args:
            asset: Asset symbol (e.g., 'DAI', 'USDC', 'WETH')
            max_age_hours: Maximum age of cached Dune results

        Returns:
            Number of data points stored for the asset
        """
        results = await self.fetch_dune_lending(max_age_hours=max_age_hours)
        return results.get(asset.upper(), 0)

    async def fetch_all_assets(self, max_age_hours: int = 24) -> dict[str, int]:
        """
        Fetch lending data for all tracked assets.

        Args:
            max_age_hours: Maximum age of cached Dune results

        Returns:
            Dict mapping asset to number of data points stored
        """
        # For Dune, we fetch all assets in one query
        # This is more efficient than fetching per asset
        return await self.fetch_dune_lending(max_age_hours=max_age_hours)


async def create_lending_fetcher() -> LendingFetcher:
    """
    Factory function to create LendingFetcher with initialized client.

    Returns:
        Configured LendingFetcher instance with Dune client
    """
    dune_client = DuneClient()  # Loads API key from environment
    return LendingFetcher(dune_client)
