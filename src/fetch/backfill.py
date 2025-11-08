"""Idempotent backfill script for initial historical data fetch."""

from datetime import datetime, timedelta, timezone

from loguru import logger

from src.config import settings
from src.database import (
    get_earliest_timestamp,
    get_latest_timestamp,
    is_backfill_completed,
    update_backfill_state,
)
from src.fetch.spot import SpotFetcher


class BackfillManager:
    """Manager for idempotent backfill operations."""

    def __init__(self, fetcher: SpotFetcher):
        """
        Initialize backfill manager.

        Args:
            fetcher: SpotFetcher instance
        """
        self.fetcher = fetcher
        self.target_days = settings.initial_backfill_days
        self.min_days = settings.min_backfill_days

    async def backfill_asset(self, asset: str, force: bool = False) -> dict:
        """
        Perform idempotent backfill for a single asset.

        This method:
        1. Checks if backfill is already completed (skip if True, unless force=True)
        2. Determines the date range to fetch based on existing data
        3. Fetches historical data in chunks
        4. Marks backfill as completed

        Args:
            asset: Asset symbol (e.g., 'BTC')
            force: Force backfill even if already completed

        Returns:
            Dict with backfill statistics
        """
        logger.info(f"Starting backfill for {asset} (target: {self.target_days} days)")

        # Check if already completed
        if not force and await is_backfill_completed(asset):
            logger.info(f"Backfill already completed for {asset}, skipping")
            return {"asset": asset, "status": "skipped", "candles_fetched": 0, "already_completed": True}

        # Calculate target date range
        now = datetime.now(timezone.utc)
        target_start = now - timedelta(days=self.target_days)

        # Check existing data
        earliest_existing = await get_earliest_timestamp(asset)
        latest_existing = await get_latest_timestamp(asset)

        if earliest_existing and latest_existing:
            logger.info(
                f"{asset} has existing data from {earliest_existing} to {latest_existing}"
            )

            # If we already have data covering the target range, just fill gaps
            if earliest_existing <= target_start:
                logger.info(
                    f"{asset} already has sufficient historical data. Filling any gaps..."
                )
                filled = await self.fetcher.fill_gaps(asset)
                await update_backfill_state(asset, completed=True, last_fetched_timestamp=latest_existing)
                return {
                    "asset": asset,
                    "status": "completed",
                    "candles_fetched": filled,
                    "gaps_filled": True,
                }

            # Fetch missing historical data before earliest existing
            fetch_start = target_start
            fetch_end = earliest_existing - timedelta(hours=12)  # One interval before existing

        else:
            # No existing data, fetch full range
            fetch_start = target_start
            fetch_end = now
            logger.info(f"No existing data for {asset}. Fetching full {self.target_days} days")

        # Perform backfill
        try:
            total_fetched = await self.fetcher.fetch_and_store_range(
                asset=asset,
                start_time=fetch_start,
                end_time=fetch_end,
            )

            # Also catch up to present if we had existing data
            if latest_existing:
                catch_up_start = latest_existing + timedelta(hours=12)
                if catch_up_start < now:
                    logger.info(f"Catching up {asset} from {catch_up_start} to {now}")
                    catch_up_count = await self.fetcher.fetch_and_store_range(
                        asset=asset,
                        start_time=catch_up_start,
                        end_time=now,
                    )
                    total_fetched += catch_up_count

            # Fill any gaps that might exist
            logger.info(f"Checking for gaps in {asset} data...")
            gaps_filled = await self.fetcher.fill_gaps(asset)
            total_fetched += gaps_filled

            # Get final timestamp
            final_latest = await get_latest_timestamp(asset)

            # Mark backfill as completed
            await update_backfill_state(
                asset=asset,
                completed=True,
                last_fetched_timestamp=final_latest,
            )

            logger.info(f"Backfill completed for {asset}: {total_fetched} total candles fetched")

            return {
                "asset": asset,
                "status": "completed",
                "candles_fetched": total_fetched,
                "gaps_filled": gaps_filled > 0,
                "final_latest": final_latest,
            }

        except Exception as e:
            logger.error(f"Backfill failed for {asset}: {e}")

            # Mark as incomplete (but update progress if any data was fetched)
            current_latest = await get_latest_timestamp(asset)
            await update_backfill_state(
                asset=asset,
                completed=False,
                last_fetched_timestamp=current_latest,
            )

            return {
                "asset": asset,
                "status": "failed",
                "error": str(e),
                "candles_fetched": 0,
            }

    async def backfill_all(self, force: bool = False) -> dict[str, dict]:
        """
        Perform backfill for all tracked assets.

        Args:
            force: Force backfill even if already completed

        Returns:
            Dictionary mapping asset -> backfill results
        """
        logger.info(f"Starting backfill for {len(settings.assets_list)} assets")

        results = {}

        for asset in settings.assets_list:
            try:
                result = await self.backfill_asset(asset, force=force)
                results[asset] = result

            except Exception as e:
                logger.error(f"Unexpected error during backfill for {asset}: {e}")
                results[asset] = {
                    "asset": asset,
                    "status": "error",
                    "error": str(e),
                }

        # Summary
        completed = sum(1 for r in results.values() if r.get("status") == "completed")
        failed = sum(1 for r in results.values() if r.get("status") in ["failed", "error"])
        skipped = sum(1 for r in results.values() if r.get("status") == "skipped")

        logger.info(
            f"Backfill summary: {completed} completed, {failed} failed, {skipped} skipped"
        )

        return results


async def run_backfill(force: bool = False) -> None:
    """
    Main entry point for running backfill.

    Args:
        force: Force backfill even if already completed
    """
    from src.database import close_pool, init_pool, init_schema
    from src.fetch.spot import create_spot_fetcher

    logger.info("Initializing database connection for backfill")
    await init_pool()
    await init_schema()

    try:
        logger.info("Creating SPOT fetcher")
        fetcher = await create_spot_fetcher()

        logger.info("Starting backfill process")
        manager = BackfillManager(fetcher)
        results = await manager.backfill_all(force=force)

        # Log results
        for asset, result in results.items():
            status = result.get("status")
            if status == "completed":
                logger.info(f"✓ {asset}: {result.get('candles_fetched', 0)} candles")
            elif status == "skipped":
                logger.info(f"- {asset}: skipped (already completed)")
            else:
                logger.error(f"✗ {asset}: {result.get('error', 'unknown error')}")

    finally:
        if fetcher and fetcher.client:
            await fetcher.client.close()
        await close_pool()
        logger.info("Backfill process completed")


if __name__ == "__main__":
    import asyncio
    import sys

    # Parse command line arguments
    force = "--force" in sys.argv

    # Run backfill
    asyncio.run(run_backfill(force=force))
