"""Backfill manager for Binance futures historical data."""

from datetime import datetime, timedelta, timezone

from loguru import logger

from src.config import settings
from src.database import (
    get_earliest_futures_timestamp,
    get_latest_futures_timestamp,
    is_futures_backfill_completed,
    update_futures_backfill_state,
)
from src.fetch.futures import FuturesFetcher


class FuturesBackfillManager:
    """Manager for idempotent backfill of futures historical data."""

    def __init__(self, fetcher: FuturesFetcher):
        """Initialize backfill manager with a futures fetcher."""
        self.fetcher = fetcher
        logger.info("FuturesBackfillManager initialized")

    async def backfill_funding_rates(
        self, asset: str, target_days: int = 730, force: bool = False
    ) -> dict:
        """
        Backfill funding rate history for an asset.

        Args:
            asset: Asset symbol (e.g., 'BTC')
            target_days: Days of history to backfill (default 2 years)
            force: Force re-backfill even if already completed

        Returns:
            Dict with backfill results
        """
        metric_type = "funding_rate"

        # Check if already completed
        if not force and await is_futures_backfill_completed(asset, metric_type):
            logger.info(f"Funding rate backfill already completed for {asset} (use force=True to re-run)")
            return {"status": "skipped", "reason": "already_completed", "records_stored": 0}

        logger.info(f"Starting funding rate backfill for {asset} (target: {target_days} days)")

        now = datetime.now(timezone.utc)
        target_start = now - timedelta(days=target_days)

        # Check existing data
        earliest = await get_earliest_futures_timestamp(asset, metric_type)
        latest = await get_latest_futures_timestamp(asset, metric_type)

        if earliest and earliest <= target_start:
            logger.info(f"Funding rates for {asset} already cover target period")
            # Just fill gaps and mark complete
            await self.fetcher.fill_funding_rate_gaps(asset)
            await update_futures_backfill_state(asset, metric_type, True, latest)
            return {"status": "completed", "reason": "already_sufficient", "records_stored": 0}

        # Determine fetch range
        if earliest:
            # Backfill before earliest existing data
            fetch_start = target_start
            fetch_end = earliest - timedelta(hours=settings.futures_funding_interval_hours)
            logger.info(f"Backfilling {asset} funding rates from {fetch_start} to {fetch_end}")
        else:
            # No existing data, fetch full range
            fetch_start = target_start
            fetch_end = now
            logger.info(f"Initial backfill for {asset} funding rates from {fetch_start} to {fetch_end}")

        try:
            # Fetch historical data
            count = await self.fetcher.fetch_and_store_funding_rates(asset, fetch_start, fetch_end)

            # Fill any gaps
            gap_count = await self.fetcher.fill_funding_rate_gaps(asset)

            # Mark as completed
            await update_futures_backfill_state(asset, metric_type, True, fetch_end)

            logger.info(f"Funding rate backfill completed for {asset}: {count} records, {gap_count} gap fills")
            return {
                "status": "success",
                "records_stored": count,
                "gaps_filled": gap_count,
            }

        except Exception as e:
            logger.error(f"Funding rate backfill failed for {asset}: {e}")
            return {"status": "failed", "error": str(e), "records_stored": 0}

    async def backfill_mark_klines(
        self, asset: str, target_days: int = 730, force: bool = False
    ) -> dict:
        """Backfill mark price klines for an asset."""
        metric_type = "mark_klines"

        if not force and await is_futures_backfill_completed(asset, metric_type):
            logger.info(f"Mark price klines backfill already completed for {asset}")
            return {"status": "skipped", "reason": "already_completed", "records_stored": 0}

        logger.info(f"Starting mark price klines backfill for {asset} (target: {target_days} days)")

        now = datetime.now(timezone.utc)
        target_start = now - timedelta(days=target_days)

        earliest = await get_earliest_futures_timestamp(asset, metric_type)
        latest = await get_latest_futures_timestamp(asset, metric_type)

        if earliest and earliest <= target_start:
            logger.info(f"Mark price klines for {asset} already cover target period")
            await self.fetcher.fill_mark_klines_gaps(asset)
            await update_futures_backfill_state(asset, metric_type, True, latest)
            return {"status": "completed", "reason": "already_sufficient", "records_stored": 0}

        # Parse interval
        interval_str = settings.futures_klines_interval
        interval_hours = int(interval_str.rstrip('h'))

        if earliest:
            fetch_start = target_start
            fetch_end = earliest - timedelta(hours=interval_hours)
            logger.info(f"Backfilling {asset} mark price klines from {fetch_start} to {fetch_end}")
        else:
            fetch_start = target_start
            fetch_end = now
            logger.info(f"Initial backfill for {asset} mark price klines from {fetch_start} to {fetch_end}")

        try:
            count = await self.fetcher.fetch_and_store_mark_klines(asset, fetch_start, fetch_end)
            gap_count = await self.fetcher.fill_mark_klines_gaps(asset)
            await update_futures_backfill_state(asset, metric_type, True, fetch_end)

            logger.info(f"Mark price klines backfill completed for {asset}: {count} records, {gap_count} gap fills")
            return {
                "status": "success",
                "records_stored": count,
                "gaps_filled": gap_count,
            }

        except Exception as e:
            logger.error(f"Mark price klines backfill failed for {asset}: {e}")
            return {"status": "failed", "error": str(e), "records_stored": 0}

    async def backfill_index_klines(
        self, asset: str, target_days: int = 730, force: bool = False
    ) -> dict:
        """Backfill index price klines for an asset."""
        metric_type = "index_klines"

        if not force and await is_futures_backfill_completed(asset, metric_type):
            logger.info(f"Index price klines backfill already completed for {asset}")
            return {"status": "skipped", "reason": "already_completed", "records_stored": 0}

        logger.info(f"Starting index price klines backfill for {asset} (target: {target_days} days)")

        now = datetime.now(timezone.utc)
        target_start = now - timedelta(days=target_days)

        earliest = await get_earliest_futures_timestamp(asset, metric_type)
        latest = await get_latest_futures_timestamp(asset, metric_type)

        if earliest and earliest <= target_start:
            logger.info(f"Index price klines for {asset} already cover target period")
            await self.fetcher.fill_index_klines_gaps(asset)
            await update_futures_backfill_state(asset, metric_type, True, latest)
            return {"status": "completed", "reason": "already_sufficient", "records_stored": 0}

        interval_str = settings.futures_klines_interval
        interval_hours = int(interval_str.rstrip('h'))

        if earliest:
            fetch_start = target_start
            fetch_end = earliest - timedelta(hours=interval_hours)
            logger.info(f"Backfilling {asset} index price klines from {fetch_start} to {fetch_end}")
        else:
            fetch_start = target_start
            fetch_end = now
            logger.info(f"Initial backfill for {asset} index price klines from {fetch_start} to {fetch_end}")

        try:
            count = await self.fetcher.fetch_and_store_index_klines(asset, fetch_start, fetch_end)
            gap_count = await self.fetcher.fill_index_klines_gaps(asset)
            await update_futures_backfill_state(asset, metric_type, True, fetch_end)

            logger.info(f"Index price klines backfill completed for {asset}: {count} records, {gap_count} gap fills")
            return {
                "status": "success",
                "records_stored": count,
                "gaps_filled": gap_count,
            }

        except Exception as e:
            logger.error(f"Index price klines backfill failed for {asset}: {e}")
            return {"status": "failed", "error": str(e), "records_stored": 0}

    async def backfill_open_interest(
        self, asset: str, target_days: int = 30, force: bool = False
    ) -> dict:
        """
        Backfill open interest history for an asset.

        Note: Binance only provides ~30 days of open interest history.
        """
        metric_type = "open_interest"

        if not force and await is_futures_backfill_completed(asset, metric_type):
            logger.info(f"Open interest backfill already completed for {asset}")
            return {"status": "skipped", "reason": "already_completed", "records_stored": 0}

        logger.info(f"Starting open interest backfill for {asset} (target: {target_days} days, limited by Binance)")

        now = datetime.now(timezone.utc)
        # Binance limits open interest history to ~30 days
        target_start = now - timedelta(days=min(target_days, 30))

        earliest = await get_earliest_futures_timestamp(asset, metric_type)
        latest = await get_latest_futures_timestamp(asset, metric_type)

        if earliest and earliest <= target_start:
            logger.info(f"Open interest for {asset} already covers available period")
            await update_futures_backfill_state(asset, metric_type, True, latest)
            return {"status": "completed", "reason": "already_sufficient", "records_stored": 0}

        if earliest:
            fetch_start = target_start
            fetch_end = earliest - timedelta(minutes=5)  # 5m is typical OI interval
            logger.info(f"Backfilling {asset} open interest from {fetch_start} to {fetch_end}")
        else:
            fetch_start = target_start
            fetch_end = now
            logger.info(f"Initial backfill for {asset} open interest from {fetch_start} to {fetch_end}")

        try:
            count = await self.fetcher.fetch_and_store_open_interest(asset, fetch_start, fetch_end, period="5m")
            await update_futures_backfill_state(asset, metric_type, True, fetch_end)

            logger.info(f"Open interest backfill completed for {asset}: {count} records")
            return {
                "status": "success",
                "records_stored": count,
                "gaps_filled": 0,  # Don't fill gaps for OI due to limited history
            }

        except Exception as e:
            logger.error(f"Open interest backfill failed for {asset}: {e}")
            return {"status": "failed", "error": str(e), "records_stored": 0}

    async def backfill_asset_all_metrics(
        self, asset: str, force: bool = False
    ) -> dict[str, dict]:
        """
        Backfill all futures metrics for a single asset.

        Returns results for each metric type with error isolation.
        """
        logger.info(f"Starting full futures backfill for {asset}")

        results = {}

        # Backfill funding rates (2 years)
        results["funding_rate"] = await self.backfill_funding_rates(
            asset, target_days=730, force=force
        )

        # Backfill mark price klines (2 years)
        results["mark_klines"] = await self.backfill_mark_klines(
            asset, target_days=730, force=force
        )

        # Backfill index price klines (2 years)
        results["index_klines"] = await self.backfill_index_klines(
            asset, target_days=730, force=force
        )

        # Backfill open interest (30 days - Binance limit)
        results["open_interest"] = await self.backfill_open_interest(
            asset, target_days=30, force=force
        )

        # Log summary
        total_records = sum(r.get("records_stored", 0) for r in results.values())
        logger.info(f"Full futures backfill completed for {asset}: {total_records} total records")

        return results

    async def backfill_all_assets(self, force: bool = False) -> dict[str, dict]:
        """
        Backfill all futures metrics for all tracked assets.

        Returns results per asset with error isolation.
        """
        logger.info(f"Starting futures backfill for all assets: {settings.futures_assets_list}")

        results = {}

        for asset in settings.futures_assets_list:
            try:
                results[asset] = await self.backfill_asset_all_metrics(asset, force=force)
            except Exception as e:
                logger.error(f"Backfill failed for {asset}: {e}")
                results[asset] = {
                    "status": "failed",
                    "error": str(e),
                }

        # Log overall summary
        total_assets = len(results)
        successful = sum(1 for r in results.values() if all(
            metric.get("status") in ["success", "skipped", "completed"]
            for metric in r.values() if isinstance(metric, dict)
        ))

        logger.info(f"Futures backfill summary: {successful}/{total_assets} assets completed successfully")

        return results


# ==================== Entry Point ====================


async def run_futures_backfill(force: bool = False) -> None:
    """
    Run futures backfill as a standalone script.

    Args:
        force: Force re-backfill even if already completed
    """
    from src.database import init_pool, init_futures_schemas
    from src.fetch.futures import create_futures_fetcher

    logger.info("Initializing futures backfill...")

    # Initialize database
    await init_pool()
    await init_futures_schemas()

    # Create fetcher and backfill manager
    fetcher = await create_futures_fetcher()
    manager = FuturesBackfillManager(fetcher)

    # Run backfill
    results = await manager.backfill_all_assets(force=force)

    # Print summary
    logger.info("=" * 80)
    logger.info("FUTURES BACKFILL COMPLETE")
    logger.info("=" * 80)

    for asset, asset_results in results.items():
        logger.info(f"\n{asset}:")
        if isinstance(asset_results, dict):
            for metric, metric_results in asset_results.items():
                if isinstance(metric_results, dict):
                    status = metric_results.get("status", "unknown")
                    records = metric_results.get("records_stored", 0)
                    logger.info(f"  {metric}: {status} ({records} records)")

    logger.info("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_futures_backfill())
