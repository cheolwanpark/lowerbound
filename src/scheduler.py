"""Scheduler service for periodic OHLCV data fetching."""

import asyncio
import signal
import sys
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from src.config import settings
from src.database import close_pool, init_pool, init_schema, init_futures_schemas, init_lending_schemas
from src.fetch.spot import SpotFetcher, create_spot_fetcher
from src.fetch.futures import FuturesFetcher, create_futures_fetcher
from src.fetch.lending import LendingFetcher, create_lending_fetcher


class SchedulerService:
    """Scheduler service for periodic data fetching."""

    def __init__(self):
        """Initialize scheduler service."""
        self.scheduler = AsyncIOScheduler()
        self.fetcher: SpotFetcher | None = None
        self.futures_fetcher: FuturesFetcher | None = None
        self.lending_fetcher: LendingFetcher | None = None
        self.running = False

    async def initialize(self) -> None:
        """Initialize database and fetcher."""
        logger.info("Initializing scheduler service")

        # Initialize database
        await init_pool()
        await init_schema()
        await init_futures_schemas()
        await init_lending_schemas()

        # Create fetchers
        self.fetcher = await create_spot_fetcher()
        self.futures_fetcher = await create_futures_fetcher()

        # Create lending fetcher with error handling
        try:
            self.lending_fetcher = await create_lending_fetcher()
            logger.info("Lending fetcher initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize lending fetcher: {e}")
            logger.warning("Lending data fetching will be disabled")
            self.lending_fetcher = None

        logger.info("Scheduler service initialized")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up scheduler service")

        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

        if self.fetcher and self.fetcher.client:
            await self.fetcher.client.close()

        if self.futures_fetcher and self.futures_fetcher.client:
            await self.futures_fetcher.client.close()

        if self.lending_fetcher and self.lending_fetcher.client:
            await self.lending_fetcher.client.close()

        await close_pool()

        logger.info("Scheduler service cleaned up")

    async def fetch_job(self) -> None:
        """
        Scheduled job to fetch latest OHLCV data.

        This job:
        1. Fetches latest data for all assets (catch-up logic)
        2. Fills any detected gaps
        """
        logger.info("=" * 60)
        logger.info(f"Starting scheduled fetch job at {datetime.now(timezone.utc)}")
        logger.info("=" * 60)

        try:
            # Fetch latest data for all assets
            logger.info("Fetching latest data for all assets...")
            latest_results = await self.fetcher.fetch_all_latest()

            for asset, count in latest_results.items():
                if count > 0:
                    logger.info(f"  {asset}: {count} new candles")
                else:
                    logger.debug(f"  {asset}: no new data")

            total_new = sum(latest_results.values())
            logger.info(f"Total new candles fetched: {total_new}")

            # Fill any gaps
            logger.info("Checking for gaps...")
            gap_results = await self.fetcher.fill_all_gaps()

            total_filled = sum(gap_results.values())
            if total_filled > 0:
                logger.info(f"Total gaps filled: {total_filled}")
                for asset, count in gap_results.items():
                    if count > 0:
                        logger.info(f"  {asset}: {count} gaps filled")
            else:
                logger.info("No gaps detected")

            logger.info("=" * 60)
            logger.info(f"Scheduled fetch job completed successfully")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error in scheduled fetch job: {e}", exc_info=True)

    async def futures_fetch_job(self) -> None:
        """
        Scheduled job to fetch latest futures data.

        This job:
        1. Fetches latest data for all futures assets (catch-up logic)
        2. Fills any detected gaps
        """
        logger.info("=" * 60)
        logger.info(f"Starting scheduled futures fetch job at {datetime.now(timezone.utc)}")
        logger.info("=" * 60)

        try:
            # Fetch latest data for all futures assets
            logger.info("Fetching latest futures data for all assets...")
            latest_results = await self.futures_fetcher.fetch_all_assets_latest()

            for asset, metrics in latest_results.items():
                total_count = sum(metrics.values())
                if total_count > 0:
                    logger.info(f"  {asset}: {total_count} new records ({metrics})")
                else:
                    logger.debug(f"  {asset}: no new data")

            total_new = sum(sum(m.values()) for m in latest_results.values())
            logger.info(f"Total new futures records fetched: {total_new}")

            # Fill any gaps
            logger.info("Checking for futures gaps...")
            gap_results = await self.futures_fetcher.fill_all_assets_gaps()

            total_filled = sum(sum(m.values()) for m in gap_results.values())
            if total_filled > 0:
                logger.info(f"Total futures gaps filled: {total_filled}")
                for asset, metrics in gap_results.items():
                    metric_total = sum(metrics.values())
                    if metric_total > 0:
                        logger.info(f"  {asset}: {metric_total} gaps filled ({metrics})")
            else:
                logger.info("No futures gaps detected")

            logger.info("=" * 60)
            logger.info(f"Scheduled futures fetch job completed successfully")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error in scheduled futures fetch job: {e}", exc_info=True)

    async def lending_fetch_job(self) -> None:
        """
        Scheduled job to fetch latest lending data from Aave.

        This job:
        1. Fetches new events for all lending assets since last fetch
        """
        logger.info("=" * 60)
        logger.info(f"Starting scheduled lending fetch job at {datetime.now(timezone.utc)}")
        logger.info("=" * 60)

        try:
            if not self.lending_fetcher:
                logger.error("Lending fetcher not initialized, skipping job")
                return

            # Fetch new events for all assets
            logger.info("Fetching new lending events for all assets...")
            results = await self.lending_fetcher.fetch_all_new_events()

            for asset, count in results.items():
                if count > 0:
                    logger.info(f"  {asset}: {count} new events")
                else:
                    logger.debug(f"  {asset}: no new events")

            total_new = sum(results.values())
            logger.info(f"Total new lending events fetched: {total_new}")

            logger.info("=" * 60)
            logger.info(f"Scheduled lending fetch job completed successfully")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error in scheduled lending fetch job: {e}", exc_info=True)
            # Don't raise - let scheduler continue

    def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        logger.info(f"Starting scheduler with {settings.fetch_interval_hours}h interval for spot, {settings.futures_funding_interval_hours}h for futures")

        # Add periodic spot fetch job
        self.scheduler.add_job(
            self.fetch_job,
            trigger=IntervalTrigger(hours=settings.fetch_interval_hours),
            id="fetch_ohlcv",
            name="Fetch OHLCV data for all assets",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Add periodic futures fetch job
        self.scheduler.add_job(
            self.futures_fetch_job,
            trigger=IntervalTrigger(hours=settings.futures_funding_interval_hours),
            id="fetch_futures",
            name="Fetch futures data for all assets",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Add periodic lending fetch job (if initialized)
        if self.lending_fetcher:
            self.scheduler.add_job(
                self.lending_fetch_job,
                trigger=IntervalTrigger(hours=settings.lending_fetch_interval_hours),
                id="fetch_lending",
                name="Fetch Aave lending data for all assets",
                replace_existing=True,
                max_instances=1,  # Prevent overlapping runs
            )
            logger.info(f"Lending fetch job added with {settings.lending_fetch_interval_hours}h interval")
        else:
            logger.warning("Lending fetcher not available, lending job not scheduled")

        # Start the scheduler
        self.scheduler.start()
        self.running = True

        logger.info("Scheduler started successfully")
        logger.info(f"Next spot run: {self.scheduler.get_job('fetch_ohlcv').next_run_time}")
        logger.info(f"Next futures run: {self.scheduler.get_job('fetch_futures').next_run_time}")
        if self.lending_fetcher:
            logger.info(f"Next lending run: {self.scheduler.get_job('fetch_lending').next_run_time}")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            return

        logger.info("Stopping scheduler")
        self.scheduler.shutdown(wait=True)
        self.running = False
        logger.info("Scheduler stopped")


async def run_scheduler() -> None:
    """
    Main entry point for running the scheduler service.

    This function:
    1. Initializes the service
    2. Optionally runs initial backfill
    3. Starts the scheduler
    4. Runs indefinitely until interrupted
    """
    service = SchedulerService()
    shutdown_event = asyncio.Event()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize
        await service.initialize()

        # Run initial backfill if enabled
        if settings.initial_backfill_days > 0:
            logger.info("Running initial spot backfill (if needed)...")
            from src.fetch.backfill import BackfillManager

            backfill_manager = BackfillManager(service.fetcher)
            await backfill_manager.backfill_all(force=False)
            logger.info("Initial spot backfill completed")

            logger.info("Running initial futures backfill (if needed)...")
            from src.fetch.futures_backfill import FuturesBackfillManager

            futures_backfill_manager = FuturesBackfillManager(service.futures_fetcher)
            await futures_backfill_manager.backfill_all_assets(force=False)
            logger.info("Initial futures backfill completed")

        # Start scheduler
        service.start()

        # Run immediate fetch jobs on startup
        logger.info("Running immediate spot fetch on startup...")
        await service.fetch_job()

        logger.info("Running immediate futures fetch on startup...")
        await service.futures_fetch_job()

        # Keep running until shutdown signal
        logger.info("Scheduler is now running. Press Ctrl+C to stop.")
        await shutdown_event.wait()

        # Shutdown
        logger.info("Shutting down scheduler service...")
        service.stop()

    except Exception as e:
        logger.error(f"Fatal error in scheduler service: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await service.cleanup()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
    )

    # Run scheduler
    asyncio.run(run_scheduler())
