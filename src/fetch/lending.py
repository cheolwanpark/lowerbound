"""Lending data fetcher for Aave protocol with event-based storage."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from loguru import logger

from src.config import settings
from src.database import (
    get_earliest_lending_timestamp,
    get_latest_lending_timestamp,
    get_ohlcv_data,
    upsert_lending_batch,
)
from src.fetch.aave_client import AaveClient


class LendingFetcher:
    """Fetcher for Aave lending data (event-based)."""

    def __init__(self, aave_client: AaveClient):
        """
        Initialize lending fetcher.

        Args:
            aave_client: Configured AaveClient instance
        """
        self.client = aave_client

    async def _get_eth_usd_price(self) -> Decimal | None:
        """
        Get current ETH/USD price from spot OHLCV data.

        Returns:
            ETH/USDT price as Decimal (approximation of USD), or None if not available

        Note:
            Uses ETH/USDT pair from spot data. USDT aims for 1:1 USD peg but
            may deviate slightly. For historical events, this returns the CURRENT
            ETH price, not the price at the event timestamp.
        """
        try:
            # Query latest ETH price from spot data
            # NOTE: get_ohlcv_data() sorts ASC, so we need to get the latest ourselves
            from src.database import get_latest_timestamp

            latest_ts = await get_latest_timestamp("ETH")
            if not latest_ts:
                logger.warning("No ETH spot data available for price calculation")
                return None

            # Query data at latest timestamp
            eth_data = await get_ohlcv_data(
                asset="ETH", start_time=latest_ts, limit=1
            )

            if eth_data and len(eth_data) > 0:
                latest = eth_data[0]
                # Use close price
                eth_price = Decimal(str(latest["close"]))
                logger.debug(f"Fetched ETH/USDT price: {eth_price}")
                return eth_price
            else:
                logger.warning("No ETH spot data available for price calculation")
                return None

        except Exception as e:
            logger.warning(f"Failed to fetch ETH/USD price: {e}")
            return None

    async def fetch_new_events(self, asset: str) -> int:
        """
        Fetch new lending events since last stored timestamp.

        This is the event-driven equivalent of fetch_latest() for spot data.
        Instead of fetching fixed intervals, we query for new events that
        occurred since our last data point.

        Args:
            asset: Asset symbol (e.g., 'WETH', 'USDC')

        Returns:
            Number of new events stored
        """
        try:
            # Get latest stored timestamp
            latest_timestamp = await get_latest_lending_timestamp(asset)

            if latest_timestamp:
                # Fetch events after latest timestamp
                after_unix = int(latest_timestamp.timestamp())
                logger.info(
                    f"Fetching new {asset} lending events after {latest_timestamp.isoformat()}"
                )
            else:
                # No data yet, this will be handled by backfill
                logger.info(f"No existing data for {asset}, use backfill for initial data")
                return 0

            # Query Aave for new events
            events = await self.client.query_reserve_events(
                symbol=asset, after_timestamp=after_unix, limit=1000
            )

            if not events:
                logger.info(f"No new events for {asset}")
                return 0

            # Get ETH/USD price for price_usd calculation
            eth_usd_price = await self._get_eth_usd_price()

            # Convert to database format
            event_dicts = [event.to_dict(eth_usd_price=eth_usd_price) for event in events]

            # Store to database
            stored_count = await upsert_lending_batch(asset, event_dicts)

            logger.info(f"Stored {stored_count} new lending events for {asset}")

            return stored_count

        except Exception as e:
            logger.error(f"Error fetching new events for {asset}: {e}")
            raise

    async def fetch_all_new_events(self) -> dict[str, int]:
        """
        Fetch new events for all tracked lending assets.

        Isolates errors per asset to prevent one failure from blocking others.

        Returns:
            Dict mapping asset to number of events fetched
        """
        results = {}

        for asset in settings.lending_assets_list:
            try:
                count = await self.fetch_new_events(asset)
                results[asset] = count
            except Exception as e:
                logger.error(f"Failed to fetch new events for {asset}: {e}")
                results[asset] = 0

        total = sum(results.values())
        logger.info(
            f"Fetch new events complete: {total} total events across {len(results)} assets"
        )

        return results

    async def backfill_events(
        self, asset: str, start_date: datetime, end_date: datetime
    ) -> int:
        """
        Backfill historical lending events for a time range.

        Unlike spot data which has fixed intervals, Aave events are irregular.
        We fetch all events in the range and store them as-is.

        Args:
            asset: Asset symbol (e.g., 'WETH', 'USDC')
            start_date: Start datetime (inclusive)
            end_date: End datetime (inclusive)

        Returns:
            Total number of events stored
        """
        try:
            logger.info(
                f"Backfilling {asset} lending events from {start_date.date()} to {end_date.date()}"
            )

            # Get ETH/USD price for price_usd calculation
            eth_usd_price = await self._get_eth_usd_price()

            total_stored = 0
            current_after = int(start_date.timestamp())
            end_unix = int(end_date.timestamp())

            # Pagination loop (The Graph limits to 1000 items per query)
            while current_after < end_unix:
                events = await self.client.query_reserve_events(
                    symbol=asset, after_timestamp=current_after, limit=1000
                )

                if not events:
                    # No more events
                    break

                # Filter events within end_date
                events_in_range = [
                    event for event in events if event.timestamp <= end_unix
                ]

                if not events_in_range:
                    break

                # Convert to database format
                event_dicts = [
                    event.to_dict(eth_usd_price=eth_usd_price) for event in events_in_range
                ]

                # Store to database
                stored_count = await upsert_lending_batch(asset, event_dicts)
                total_stored += stored_count

                logger.info(
                    f"Stored {stored_count} events for {asset} (total: {total_stored})"
                )

                # Update pagination cursor
                if len(events) < 1000:
                    # Last page
                    break
                else:
                    # Move to next page (after last event timestamp)
                    current_after = events[-1].timestamp

            logger.info(
                f"Backfill complete for {asset}: {total_stored} events stored"
            )

            return total_stored

        except Exception as e:
            logger.error(f"Error backfilling {asset} from {start_date} to {end_date}: {e}")
            raise


async def create_lending_fetcher() -> LendingFetcher:
    """
    Factory function to create LendingFetcher with initialized client.

    Returns:
        Configured LendingFetcher instance
    """
    from src.fetch.aave_client import create_aave_client

    aave_client = await create_aave_client()
    return LendingFetcher(aave_client)
