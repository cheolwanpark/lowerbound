"""
Dune Analytics API client for fetching lending market data.

This module provides a wrapper around the official dune-client package
to fetch lending market data from Dune Analytics query 3328916.
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from dune_client.client import DuneClient as OfficialDuneClient
from dune_client.query import QueryBase
from loguru import logger

from src.config import settings
from src.models import DuneLendingData


class DuneClient:
    """
    Dune Analytics API client wrapper.

    Handles rate limiting, error handling, and data transformation
    for lending market data from Dune Analytics.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize Dune client.

        Args:
            api_key: Dune Analytics API key. If None, loads from config/environment.
        """
        if api_key:
            self.client = OfficialDuneClient(api_key=api_key)
        else:
            # Load from pydantic settings
            if settings.dune_api_key:
                self.client = OfficialDuneClient(api_key=settings.dune_api_key.get_secret_value())
            else:
                # Fallback to environment variable
                self.client = OfficialDuneClient.from_env()

        self.last_request_time = 0
        self.min_request_interval = 65  # Free tier: ~1 req/min, use 65s to be safe

        logger.info("Dune Analytics client initialized")

    async def _rate_limit(self):
        """
        Apply rate limiting to avoid hitting API limits.

        Free tier allows ~1 request per minute.
        Waits if necessary to maintain the rate limit.
        """
        now = asyncio.get_event_loop().time()
        time_since_last_request = now - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.1f}s")
            await asyncio.sleep(sleep_time)

        self.last_request_time = asyncio.get_event_loop().time()

    async def get_lending_data(
        self, max_age_hours: int = 24, max_retries: int = 3
    ) -> list[DuneLendingData]:
        """
        Fetch lending market data from Dune Analytics by executing the query.

        Args:
            max_age_hours: Unused parameter (kept for API compatibility).
            max_retries: Maximum number of retry attempts on failure.

        Returns:
            List of DuneLendingData objects containing lending market data.

        Raises:
            Exception: If all retry attempts fail.
        """
        query_id = settings.dune_lending_query_id

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Executing Dune query {query_id} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                # Apply rate limiting
                await self._rate_limit()

                # Create query object and execute it
                query = QueryBase(
                    name="Lending Data Query",
                    query_id=query_id,
                )

                # Execute query (runs in thread pool to avoid blocking)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.client.run_query(query)
                )

                if not result or not result.result:
                    logger.warning(f"Dune query {query_id} returned no results")
                    return []

                rows = result.result.rows
                logger.info(f"Received {len(rows)} rows from Dune query {query_id}")

                # Parse rows into DuneLendingData objects
                lending_data = []
                for row in rows:
                    try:
                        # Convert row dict to DuneLendingData
                        # Dune returns data as dict with column names as keys
                        data = DuneLendingData(
                            dt=row["dt"],
                            symbol=row["symbol"],
                            reserve=row["reserve"],
                            avg_stableBorrowRate=Decimal(str(row["avg_stableBorrowRate"])),
                            avg_variableBorrowRate=Decimal(str(row["avg_variableBorrowRate"])),
                            avg_supplyRate=Decimal(str(row["avg_supplyRate"])),
                            avg_liquidityIndex=Decimal(str(row["avg_liquidityIndex"])),
                            avg_variableBorrowIndex=Decimal(str(row["avg_variableBorrowIndex"])),
                        )
                        lending_data.append(data)
                    except (KeyError, ValueError, TypeError) as e:
                        logger.error(f"Failed to parse row: {row}. Error: {e}")
                        continue

                logger.info(f"Successfully parsed {len(lending_data)} lending data points")
                return lending_data

            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")

                if attempt < max_retries - 1:
                    # Exponential backoff: 5s, 10s, 20s
                    sleep_time = 5 * (2**attempt)
                    logger.info(f"Retrying in {sleep_time}s...")
                    await asyncio.sleep(sleep_time)
                else:
                    logger.error(f"All {max_retries} attempts failed for Dune query {query_id}")
                    raise

        return []

    async def get_lending_data_for_asset(
        self, asset: str, max_age_hours: int = 24
    ) -> list[DuneLendingData]:
        """
        Fetch lending data for a specific asset.

        Note: Dune query 3328916 returns data for ALL assets.
        This method fetches everything and filters client-side.

        Args:
            asset: Asset symbol (e.g., DAI, USDC, WETH)
            max_age_hours: Maximum age of cached results

        Returns:
            List of DuneLendingData objects filtered for the asset.
        """
        all_data = await self.get_lending_data(max_age_hours=max_age_hours)

        # Filter for the specific asset
        filtered_data = [d for d in all_data if d.symbol.upper() == asset.upper()]

        logger.info(f"Filtered {len(filtered_data)} data points for asset {asset}")
        return filtered_data

    async def validate_connection(self) -> bool:
        """
        Validate that the Dune API connection is working.

        Returns:
            True if connection is valid, False otherwise.
        """
        try:
            logger.info("Validating Dune Analytics connection...")

            # Try to fetch data with a very old max_age to use cached results
            data = await self.get_lending_data(max_age_hours=8760)  # 1 year

            if data:
                logger.info("Dune Analytics connection validated successfully")
                return True
            else:
                logger.warning("Dune Analytics connection returned no data")
                return False

        except Exception as e:
            logger.error(f"Dune Analytics connection validation failed: {e}")
            return False
