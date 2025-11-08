"""Backfill script for lending market data from Dune Analytics."""

from datetime import datetime, timezone

from loguru import logger

from src.config import settings
from src.database import (
    get_earliest_lending_timestamp,
    get_latest_lending_timestamp,
    is_lending_backfill_completed,
    update_lending_backfill_state,
)
from src.fetch.lending import LendingFetcher


class LendingBackfillManager:
    """Manager for lending data backfill operations."""

    def __init__(self, fetcher: LendingFetcher):
        """
        Initialize lending backfill manager.

        Args:
            fetcher: LendingFetcher instance
        """
        self.fetcher = fetcher

    async def backfill_asset(self, asset: str, force: bool = False) -> dict:
        """
        Perform backfill for a single lending asset.

        Note: Unlike spot/futures which fetch historical data in chunks,
        Dune query returns ALL available data at once. This method mainly
        serves to track backfill completion status.

        Args:
            asset: Asset symbol (e.g., 'DAI', 'USDC')
            force: Force backfill even if already completed

        Returns:
            Dict with backfill statistics
        """
        logger.info(f"Starting lending backfill for {asset}")

        # Check if already completed
        if not force and await is_lending_backfill_completed(asset):
            logger.info(f"Backfill already completed for {asset}, skipping")
            return {
                "asset": asset,
                "status": "skipped",
                "data_points_fetched": 0,
                "already_completed": True,
            }

        try:
            # Fetch all available data from Dune
            # Use max_age_hours=8760 (1 year) to prefer cached results if available
            count = await self.fetcher.fetch_for_asset(asset, max_age_hours=8760)

            # Get latest timestamp after fetch
            latest_timestamp = await get_latest_lending_timestamp(asset)

            # Mark backfill as completed
            if latest_timestamp:
                await update_lending_backfill_state(
                    asset, completed=True, last_fetched_timestamp=latest_timestamp
                )

            logger.info(f"Backfill completed for {asset}: {count} data points")

            return {
                "asset": asset,
                "status": "completed",
                "data_points_fetched": count,
                "latest_timestamp": latest_timestamp,
            }

        except Exception as e:
            logger.error(f"Backfill failed for {asset}: {e}")
            return {"asset": asset, "status": "failed", "error": str(e)}

    async def backfill_all_assets(self, force: bool = False) -> dict:
        """
        Perform backfill for all tracked lending assets.

        Args:
            force: Force backfill even if already completed

        Returns:
            Dict with overall backfill statistics
        """
        logger.info(f"Starting backfill for all lending assets (force={force})")

        results = []
        total_fetched = 0

        for asset in settings.lending_assets_list:
            try:
                result = await self.backfill_asset(asset, force=force)
                results.append(result)
                total_fetched += result.get("data_points_fetched", 0)
            except Exception as e:
                logger.error(f"Failed to backfill {asset}: {e}")
                results.append({"asset": asset, "status": "failed", "error": str(e)})

        completed = sum(1 for r in results if r["status"] == "completed")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        failed = sum(1 for r in results if r["status"] == "failed")

        logger.info(
            f"Backfill complete: {completed} completed, {skipped} skipped, "
            f"{failed} failed, {total_fetched} total data points"
        )

        return {
            "total_assets": len(results),
            "completed": completed,
            "skipped": skipped,
            "failed": failed,
            "total_data_points": total_fetched,
            "details": results,
        }


async def create_lending_backfill_manager() -> LendingBackfillManager:
    """
    Factory function to create LendingBackfillManager.

    Returns:
        Configured LendingBackfillManager instance
    """
    from src.fetch.lending import create_lending_fetcher

    fetcher = await create_lending_fetcher()
    return LendingBackfillManager(fetcher)


async def run_lending_backfill(force: bool = False):
    """
    Main entry point for running lending backfill.

    Args:
        force: Force backfill even if already completed
    """
    logger.info("=" * 80)
    logger.info("Starting Lending Data Backfill (Dune Analytics)")
    logger.info("=" * 80)

    manager = await create_lending_backfill_manager()
    results = await manager.backfill_all_assets(force=force)

    logger.info("=" * 80)
    logger.info("Lending Backfill Summary")
    logger.info(f"Total assets: {results['total_assets']}")
    logger.info(f"Completed: {results['completed']}")
    logger.info(f"Skipped: {results['skipped']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Total data points: {results['total_data_points']}")
    logger.info("=" * 80)

    return results
