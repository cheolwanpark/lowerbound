"""High-level fetcher for Binance Futures data."""

from datetime import datetime, timedelta, timezone

from loguru import logger

from src.config import settings
from src.database import (
    detect_futures_gaps,
    get_latest_futures_timestamp,
    upsert_funding_rates_batch,
    upsert_mark_klines_batch,
    upsert_index_klines_batch,
    upsert_open_interest_batch,
)
from src.fetch.binance_client import BinanceClient


class FuturesFetcher:
    """Fetcher for Binance futures market data."""

    def __init__(self, client: BinanceClient):
        """Initialize the futures fetcher with a Binance client."""
        self.client = client
        logger.info("FuturesFetcher initialized")

    def _asset_to_symbol(self, asset: str) -> str:
        """Convert asset name to Binance futures symbol (e.g., BTC -> BTCUSDT)."""
        return f"{asset.upper()}USDT"

    def _parse_interval_hours(self, interval_str: str) -> int:
        """
        Parse interval string to hours.

        Supports: 1h, 4h, 8h, 1d, etc.
        Returns hours as integer.
        """
        interval_str = interval_str.lower().strip()

        if interval_str.endswith('h'):
            return int(interval_str[:-1])
        elif interval_str.endswith('d'):
            return int(interval_str[:-1]) * 24
        elif interval_str.endswith('m'):
            minutes = int(interval_str[:-1])
            # Round up to nearest hour for gap detection
            return max(1, (minutes + 59) // 60)
        else:
            raise ValueError(f"Unsupported interval format: {interval_str}. Use format like '8h', '1d', '5m'")

    # ==================== Funding Rate Methods ====================

    async def fetch_and_store_funding_rates(
        self, asset: str, start_time: datetime, end_time: datetime
    ) -> int:
        """
        Fetch and store funding rate data for an asset.

        Args:
            asset: Asset symbol (e.g., 'BTC')
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)

        Returns:
            Number of funding rate records stored
        """
        symbol = self._asset_to_symbol(asset)
        logger.info(f"Fetching funding rates for {asset} from {start_time} to {end_time}")

        try:
            # Fetch data with pagination
            funding_rates = await self.client.get_funding_rate_history_paginated(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
            )

            if not funding_rates:
                logger.info(f"No funding rates fetched for {asset}")
                return 0

            # Convert to database format
            rate_dicts = [rate.to_dict() for rate in funding_rates]

            # Store in database
            count = await upsert_funding_rates_batch(asset, rate_dicts)
            logger.info(f"Stored {count} funding rates for {asset}")
            return count

        except Exception as e:
            logger.error(f"Failed to fetch funding rates for {asset}: {e}")
            raise

    async def fetch_latest_funding_rates(self, asset: str) -> int:
        """
        Fetch latest funding rates since last stored data point.

        Uses intelligent catch-up: fetches from (latest + interval) to now.
        """
        latest = await get_latest_futures_timestamp(asset, "funding_rate")
        now = datetime.now(timezone.utc)

        if latest is None:
            logger.info(f"No existing funding rates for {asset}, skipping latest fetch")
            return 0

        # Calculate expected next timestamp (funding rates are every 8 hours)
        interval_hours = settings.futures_funding_interval_hours
        expected_next = latest + timedelta(hours=interval_hours)

        if expected_next > now:
            logger.info(f"No new funding rates to fetch for {asset} (next expected: {expected_next})")
            return 0

        logger.info(f"Catching up funding rates for {asset} from {expected_next} to {now}")
        return await self.fetch_and_store_funding_rates(asset, expected_next, now)

    async def fill_funding_rate_gaps(self, asset: str) -> int:
        """Detect and fill gaps in funding rate data."""
        interval_hours = settings.futures_funding_interval_hours
        gaps = await detect_futures_gaps(asset, "funding_rate", interval_hours)

        if not gaps:
            logger.info(f"No gaps found in funding rates for {asset}")
            return 0

        logger.info(f"Found {len(gaps)} gap(s) in funding rates for {asset}")
        total_filled = 0

        for gap_start, gap_end in gaps:
            try:
                count = await self.fetch_and_store_funding_rates(asset, gap_start, gap_end)
                total_filled += count
            except Exception as e:
                logger.error(f"Failed to fill gap {gap_start} to {gap_end} for {asset}: {e}")
                # Continue with next gap

        logger.info(f"Filled {total_filled} funding rate records across {len(gaps)} gap(s) for {asset}")
        return total_filled

    # ==================== Mark Price Klines Methods ====================

    async def fetch_and_store_mark_klines(
        self, asset: str, start_time: datetime, end_time: datetime
    ) -> int:
        """Fetch and store mark price klines for an asset."""
        symbol = self._asset_to_symbol(asset)
        interval = settings.futures_klines_interval
        logger.info(f"Fetching mark price klines for {asset} ({interval}) from {start_time} to {end_time}")

        try:
            klines = await self.client.get_mark_price_klines_paginated(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
            )

            if not klines:
                logger.info(f"No mark price klines fetched for {asset}")
                return 0

            kline_dicts = [kline.to_dict() for kline in klines]
            count = await upsert_mark_klines_batch(asset, kline_dicts)
            logger.info(f"Stored {count} mark price klines for {asset}")
            return count

        except Exception as e:
            logger.error(f"Failed to fetch mark price klines for {asset}: {e}")
            raise

    async def fetch_latest_mark_klines(self, asset: str) -> int:
        """Fetch latest mark price klines since last stored data point."""
        latest = await get_latest_futures_timestamp(asset, "mark_klines")
        now = datetime.now(timezone.utc)

        if latest is None:
            logger.info(f"No existing mark price klines for {asset}, skipping latest fetch")
            return 0

        # Parse interval using helper
        interval_hours = self._parse_interval_hours(settings.futures_klines_interval)
        expected_next = latest + timedelta(hours=interval_hours)

        if expected_next > now:
            logger.info(f"No new mark price klines to fetch for {asset}")
            return 0

        logger.info(f"Catching up mark price klines for {asset} from {expected_next} to {now}")
        return await self.fetch_and_store_mark_klines(asset, expected_next, now)

    async def fill_mark_klines_gaps(self, asset: str) -> int:
        """Detect and fill gaps in mark price kline data."""
        interval_hours = self._parse_interval_hours(settings.futures_klines_interval)
        gaps = await detect_futures_gaps(asset, "mark_klines", interval_hours)

        if not gaps:
            logger.info(f"No gaps found in mark price klines for {asset}")
            return 0

        logger.info(f"Found {len(gaps)} gap(s) in mark price klines for {asset}")
        total_filled = 0

        for gap_start, gap_end in gaps:
            try:
                count = await self.fetch_and_store_mark_klines(asset, gap_start, gap_end)
                total_filled += count
            except Exception as e:
                logger.error(f"Failed to fill gap {gap_start} to {gap_end} for {asset}: {e}")

        logger.info(f"Filled {total_filled} mark price klines across {len(gaps)} gap(s) for {asset}")
        return total_filled

    # ==================== Index Price Klines Methods ====================

    async def fetch_and_store_index_klines(
        self, asset: str, start_time: datetime, end_time: datetime
    ) -> int:
        """Fetch and store index price klines for an asset."""
        pair = self._asset_to_symbol(asset)  # Index klines use 'pair' parameter
        interval = settings.futures_klines_interval
        logger.info(f"Fetching index price klines for {asset} ({interval}) from {start_time} to {end_time}")

        try:
            klines = await self.client.get_index_price_klines_paginated(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
            )

            if not klines:
                logger.info(f"No index price klines fetched for {asset}")
                return 0

            kline_dicts = [kline.to_dict() for kline in klines]
            count = await upsert_index_klines_batch(asset, kline_dicts)
            logger.info(f"Stored {count} index price klines for {asset}")
            return count

        except Exception as e:
            logger.error(f"Failed to fetch index price klines for {asset}: {e}")
            raise

    async def fetch_latest_index_klines(self, asset: str) -> int:
        """Fetch latest index price klines since last stored data point."""
        latest = await get_latest_futures_timestamp(asset, "index_klines")
        now = datetime.now(timezone.utc)

        if latest is None:
            logger.info(f"No existing index price klines for {asset}, skipping latest fetch")
            return 0

        interval_hours = self._parse_interval_hours(settings.futures_klines_interval)
        expected_next = latest + timedelta(hours=interval_hours)

        if expected_next > now:
            logger.info(f"No new index price klines to fetch for {asset}")
            return 0

        logger.info(f"Catching up index price klines for {asset} from {expected_next} to {now}")
        return await self.fetch_and_store_index_klines(asset, expected_next, now)

    async def fill_index_klines_gaps(self, asset: str) -> int:
        """Detect and fill gaps in index price kline data."""
        interval_hours = self._parse_interval_hours(settings.futures_klines_interval)
        gaps = await detect_futures_gaps(asset, "index_klines", interval_hours)

        if not gaps:
            logger.info(f"No gaps found in index price klines for {asset}")
            return 0

        logger.info(f"Found {len(gaps)} gap(s) in index price klines for {asset}")
        total_filled = 0

        for gap_start, gap_end in gaps:
            try:
                count = await self.fetch_and_store_index_klines(asset, gap_start, gap_end)
                total_filled += count
            except Exception as e:
                logger.error(f"Failed to fill gap {gap_start} to {gap_end} for {asset}: {e}")

        logger.info(f"Filled {total_filled} index price klines across {len(gaps)} gap(s) for {asset}")
        return total_filled

    # ==================== Open Interest Methods ====================

    async def fetch_and_store_open_interest(
        self, asset: str, start_time: datetime, end_time: datetime, period: str | None = None
    ) -> int:
        """
        Fetch and store open interest data for an asset.

        Note: Binance only provides ~30 days of open interest history.
        """
        if period is None:
            period = settings.futures_oi_period

        symbol = self._asset_to_symbol(asset)
        logger.info(f"Fetching open interest for {asset} ({period}) from {start_time} to {end_time}")

        try:
            oi_data = await self.client.get_open_interest_history_paginated(
                symbol=symbol,
                period=period,
                start_time=start_time,
                end_time=end_time,
            )

            if not oi_data:
                logger.info(f"No open interest data fetched for {asset}")
                return 0

            oi_dicts = [oi.to_dict() for oi in oi_data]
            count = await upsert_open_interest_batch(asset, oi_dicts)
            logger.info(f"Stored {count} open interest data points for {asset}")
            return count

        except Exception as e:
            logger.error(f"Failed to fetch open interest for {asset}: {e}")
            raise

    async def fetch_latest_open_interest(self, asset: str, period: str | None = None) -> int:
        """Fetch latest open interest since last stored data point."""
        if period is None:
            period = settings.futures_oi_period

        latest = await get_latest_futures_timestamp(asset, "open_interest")
        now = datetime.now(timezone.utc)

        if latest is None:
            logger.info(f"No existing open interest data for {asset}, skipping latest fetch")
            return 0

        # Parse period to minutes
        period_str = period.lower().strip()
        if period_str.endswith('m'):
            period_minutes = int(period_str[:-1])
        elif period_str.endswith('h'):
            period_minutes = int(period_str[:-1]) * 60
        elif period_str.endswith('d'):
            period_minutes = int(period_str[:-1]) * 1440
        else:
            raise ValueError(f"Unsupported period format: {period}. Use format like '5m', '1h', '1d'")

        expected_next = latest + timedelta(minutes=period_minutes)

        if expected_next > now:
            logger.info(f"No new open interest data to fetch for {asset}")
            return 0

        logger.info(f"Catching up open interest for {asset} from {expected_next} to {now}")
        return await self.fetch_and_store_open_interest(asset, expected_next, now, period)

    # ==================== Aggregated Methods ====================

    async def fetch_all_metrics(
        self, asset: str, start_time: datetime, end_time: datetime
    ) -> dict[str, int]:
        """
        Fetch all futures metrics for an asset with error isolation.

        Returns a dict with counts per metric type.
        """
        results = {
            "funding_rate": 0,
            "mark_klines": 0,
            "index_klines": 0,
            "open_interest": 0,
        }

        # Fetch funding rates
        try:
            results["funding_rate"] = await self.fetch_and_store_funding_rates(
                asset, start_time, end_time
            )
        except Exception as e:
            logger.error(f"Failed to fetch funding rates for {asset}: {e}")

        # Fetch mark price klines
        try:
            results["mark_klines"] = await self.fetch_and_store_mark_klines(
                asset, start_time, end_time
            )
        except Exception as e:
            logger.error(f"Failed to fetch mark price klines for {asset}: {e}")

        # Fetch index price klines
        try:
            results["index_klines"] = await self.fetch_and_store_index_klines(
                asset, start_time, end_time
            )
        except Exception as e:
            logger.error(f"Failed to fetch index price klines for {asset}: {e}")

        # Fetch open interest (limited to 30 days)
        try:
            # Limit open interest to last 30 days even if requested range is larger
            oi_start = max(start_time, datetime.now(timezone.utc) - timedelta(days=30))
            if oi_start < end_time:
                results["open_interest"] = await self.fetch_and_store_open_interest(
                    asset, oi_start, end_time
                )
        except Exception as e:
            logger.error(f"Failed to fetch open interest for {asset}: {e}")

        return results

    async def fetch_latest(self, asset: str) -> dict[str, int]:
        """
        Fetch latest data for all futures metrics with error isolation.

        Returns a dict with counts per metric type.
        """
        results = {
            "funding_rate": 0,
            "mark_klines": 0,
            "index_klines": 0,
            "open_interest": 0,
        }

        try:
            results["funding_rate"] = await self.fetch_latest_funding_rates(asset)
        except Exception as e:
            logger.error(f"Failed to fetch latest funding rates for {asset}: {e}")

        try:
            results["mark_klines"] = await self.fetch_latest_mark_klines(asset)
        except Exception as e:
            logger.error(f"Failed to fetch latest mark price klines for {asset}: {e}")

        try:
            results["index_klines"] = await self.fetch_latest_index_klines(asset)
        except Exception as e:
            logger.error(f"Failed to fetch latest index price klines for {asset}: {e}")

        try:
            results["open_interest"] = await self.fetch_latest_open_interest(asset)
        except Exception as e:
            logger.error(f"Failed to fetch latest open interest for {asset}: {e}")

        return results

    async def fill_all_gaps(self, asset: str) -> dict[str, int]:
        """
        Fill gaps for all futures metrics with error isolation.

        Returns a dict with counts per metric type.
        """
        results = {
            "funding_rate": 0,
            "mark_klines": 0,
            "index_klines": 0,
            "open_interest": 0,
        }

        try:
            results["funding_rate"] = await self.fill_funding_rate_gaps(asset)
        except Exception as e:
            logger.error(f"Failed to fill funding rate gaps for {asset}: {e}")

        try:
            results["mark_klines"] = await self.fill_mark_klines_gaps(asset)
        except Exception as e:
            logger.error(f"Failed to fill mark price kline gaps for {asset}: {e}")

        try:
            results["index_klines"] = await self.fill_index_klines_gaps(asset)
        except Exception as e:
            logger.error(f"Failed to fill index price kline gaps for {asset}: {e}")

        # Note: Skipping open interest gap filling since Binance only keeps 30 days

        return results

    async def fetch_all_assets_latest(self) -> dict[str, dict[str, int]]:
        """Fetch latest data for all tracked futures assets."""
        results = {}

        for asset in settings.futures_assets_list:
            try:
                results[asset] = await self.fetch_latest(asset)
                logger.info(f"Latest fetch complete for {asset}: {results[asset]}")
            except Exception as e:
                logger.error(f"Failed to fetch latest for {asset}: {e}")
                results[asset] = {"funding_rate": 0, "mark_klines": 0, "index_klines": 0, "open_interest": 0}

        return results

    async def fill_all_assets_gaps(self) -> dict[str, dict[str, int]]:
        """Fill gaps for all tracked futures assets."""
        results = {}

        for asset in settings.futures_assets_list:
            try:
                results[asset] = await self.fill_all_gaps(asset)
                logger.info(f"Gap filling complete for {asset}: {results[asset]}")
            except Exception as e:
                logger.error(f"Failed to fill gaps for {asset}: {e}")
                results[asset] = {"funding_rate": 0, "mark_klines": 0, "index_klines": 0, "open_interest": 0}

        return results


# ==================== Factory Function ====================


async def create_futures_fetcher() -> FuturesFetcher:
    """Create a FuturesFetcher instance with an initialized Binance client."""
    client = BinanceClient()
    return FuturesFetcher(client)
