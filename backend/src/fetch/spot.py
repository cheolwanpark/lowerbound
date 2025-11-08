"""OHLCV data fetcher for SPOT assets with gap detection."""

from datetime import datetime, timedelta, timezone

from loguru import logger

from src.config import settings
from src.database import (
    detect_gaps,
    get_earliest_timestamp,
    get_latest_timestamp,
    upsert_ohlcv_batch,
)
from src.fetch.binance_client import BinanceClient


class SpotFetcher:
    """Fetcher for SPOT asset OHLCV data."""

    def __init__(self, binance_client: BinanceClient):
        """
        Initialize SPOT fetcher.

        Args:
            binance_client: Configured BinanceClient instance
        """
        self.client = binance_client
        self.interval = "12h"

    def _asset_to_symbol(self, asset: str) -> str:
        """
        Convert asset name to Binance SPOT symbol.

        Args:
            asset: Asset name (e.g., 'BTC')

        Returns:
            Binance symbol (e.g., 'BTCUSDT')
        """
        return f"{asset.upper()}USDT"

    async def fetch_and_store_range(
        self, asset: str, start_time: datetime, end_time: datetime
    ) -> int:
        """
        Fetch OHLCV data for a specific time range and store to database.

        Args:
            asset: Asset symbol (e.g., 'BTC')
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)

        Returns:
            Number of candles stored
        """
        symbol = self._asset_to_symbol(asset)

        try:
            # Fetch klines with pagination
            klines = await self.client.get_klines_paginated(
                symbol=symbol,
                interval=self.interval,
                start_time=start_time,
                end_time=end_time,
            )

            if not klines:
                logger.warning(
                    f"No data returned for {asset} from {start_time} to {end_time}"
                )
                return 0

            # Convert to OHLCV dictionaries
            candles = [kline.to_ohlcv() for kline in klines]

            # Store to database with upsert
            stored_count = await upsert_ohlcv_batch(asset, candles)

            logger.info(
                f"Fetched and stored {stored_count} candles for {asset} "
                f"({start_time.date()} to {end_time.date()})"
            )

            return stored_count

        except Exception as e:
            logger.error(f"Error fetching {asset} from {start_time} to {end_time}: {e}")
            raise

    async def fetch_latest(self, asset: str) -> int:
        """
        Fetch the latest OHLCV data (catch-up from last stored timestamp to now).

        This is used by the scheduler to keep data up-to-date.

        Args:
            asset: Asset symbol

        Returns:
            Number of new candles stored
        """
        latest = await get_latest_timestamp(asset)

        if latest is None:
            logger.info(f"No existing data for {asset}. Use backfill instead.")
            return 0

        # Calculate expected next candle time (latest + 12h)
        interval_delta = timedelta(hours=12)
        expected_next = latest + interval_delta

        # Current time
        now = datetime.now(timezone.utc)

        # If expected_next is in the future, nothing to fetch
        if expected_next > now:
            logger.debug(f"No new data available for {asset} (next expected: {expected_next})")
            return 0

        logger.info(f"Catching up {asset} from {expected_next} to {now}")

        return await self.fetch_and_store_range(
            asset=asset, start_time=expected_next, end_time=now
        )

    async def fill_gaps(self, asset: str) -> int:
        """
        Detect and fill missing candles (gaps) in the data.

        Args:
            asset: Asset symbol

        Returns:
            Total number of candles filled
        """
        gaps = await detect_gaps(asset, interval_hours=12)

        if not gaps:
            logger.info(f"No gaps detected for {asset}")
            return 0

        logger.info(f"Detected {len(gaps)} gap(s) for {asset}")

        total_filled = 0

        for gap_start, gap_end in gaps:
            logger.info(f"Filling gap for {asset}: {gap_start} to {gap_end}")

            try:
                filled = await self.fetch_and_store_range(
                    asset=asset, start_time=gap_start, end_time=gap_end
                )
                total_filled += filled

            except Exception as e:
                logger.error(f"Error filling gap for {asset} ({gap_start} to {gap_end}): {e}")
                # Continue with next gap instead of failing completely
                continue

        logger.info(f"Filled {total_filled} candles across {len(gaps)} gap(s) for {asset}")
        return total_filled

    async def fetch_all_latest(self) -> dict[str, int]:
        """
        Fetch latest data for all tracked assets.

        Returns:
            Dictionary mapping asset -> number of new candles
        """
        results = {}

        for asset in settings.assets_list:
            try:
                count = await self.fetch_latest(asset)
                results[asset] = count
            except Exception as e:
                logger.error(f"Failed to fetch latest for {asset}: {e}")
                results[asset] = 0

        return results

    async def fill_all_gaps(self) -> dict[str, int]:
        """
        Fill gaps for all tracked assets.

        Returns:
            Dictionary mapping asset -> number of filled candles
        """
        results = {}

        for asset in settings.assets_list:
            try:
                count = await self.fill_gaps(asset)
                results[asset] = count
            except Exception as e:
                logger.error(f"Failed to fill gaps for {asset}: {e}")
                results[asset] = 0

        return results


async def create_spot_fetcher() -> SpotFetcher:
    """
    Factory function to create a SpotFetcher instance.

    Returns:
        Configured SpotFetcher
    """
    client = BinanceClient()
    return SpotFetcher(binance_client=client)
