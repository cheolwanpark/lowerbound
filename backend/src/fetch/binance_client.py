"""Rate-limited async HTTP client for Binance API."""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from src.config import settings
from src.models import (
    BinanceKline,
    BinanceFundingRate,
    BinanceMarkPriceKline,
    BinanceIndexPriceKline,
    BinanceOpenInterest,
)


class RateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(self, requests_per_minute: int, request_delay_ms: int):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            request_delay_ms: Minimum delay between requests in milliseconds
        """
        self.requests_per_minute = requests_per_minute
        self.request_delay_ms = request_delay_ms
        self.request_delay_sec = request_delay_ms / 1000.0

        # Semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

        # Track last request time for minimum delay
        self.last_request_time: float | None = None
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request can be made within rate limits."""
        await self.semaphore.acquire()

        async with self.lock:
            if self.last_request_time is not None:
                elapsed = asyncio.get_event_loop().time() - self.last_request_time
                wait_time = self.request_delay_sec - elapsed

                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self.last_request_time = asyncio.get_event_loop().time()

    def release(self) -> None:
        """Release the semaphore after request completes."""
        self.semaphore.release()


class BinanceClient:
    """Async HTTP client for Binance API with rate limiting."""

    def __init__(self):
        """Initialize Binance API client."""
        self.base_url = settings.binance_api_base_url
        self.rate_limiter = RateLimiter(
            requests_per_minute=settings.binance_rate_limit_requests_per_minute,
            request_delay_ms=settings.binance_request_delay_ms,
        )
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        logger.info(
            f"Binance client initialized: {self.base_url}, "
            f"rate limit: {settings.binance_rate_limit_requests_per_minute} req/min"
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Binance client closed")

    async def _request_with_retry(
        self, url: str, params: dict[str, Any], max_retries: int = 3
    ) -> Any:
        """
        Make HTTP request with exponential backoff retry.

        Args:
            url: Full URL to request
            params: Query parameters
            max_retries: Maximum number of retry attempts

        Returns:
            JSON response data

        Raises:
            httpx.HTTPStatusError: If all retries fail
        """
        last_exception = None

        for attempt in range(max_retries):
            await self.rate_limiter.acquire()

            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_exception = e

                if e.response.status_code == 429:  # Rate limit exceeded
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Rate limit exceeded. Waiting {retry_after}s before retry..."
                    )
                    await asyncio.sleep(retry_after)
                    # Continue to next attempt (don't release semaphore during backoff)
                    continue

                elif e.response.status_code >= 500:  # Server error
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"Server error {e.response.status_code}. "
                            f"Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                # Client errors (4xx) or final retry - break and raise
                break

            except httpx.RequestError as e:
                last_exception = e

                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Request error: {e}. Retrying in {wait_time}s... "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                # Final attempt failed
                break

            finally:
                self.rate_limiter.release()

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Failed after {max_retries} retries")

    async def get_klines(
        self,
        symbol: str,
        interval: str = "12h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[BinanceKline]:
        """
        Fetch klines (candlestick) data from Binance SPOT API.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '12h')
            start_time: Start time (inclusive)
            end_time: End time (inclusive)
            limit: Number of candles to fetch (max 1000)

        Returns:
            List of validated BinanceKline objects

        Raises:
            httpx.HTTPStatusError: If request fails after retries
            ValueError: If response validation fails
        """
        url = f"{self.base_url}/api/v3/klines"
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),  # Binance max is 1000
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)

        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        logger.debug(f"Fetching klines: {symbol} {interval} (limit={limit})")

        try:
            data = await self._request_with_retry(url, params)

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format: expected list, got {type(data)}")

            # Validate and parse response
            klines = [BinanceKline.from_list(item) for item in data]

            logger.debug(f"Fetched {len(klines)} klines for {symbol}")
            return klines

        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            raise

    async def get_klines_paginated(
        self,
        symbol: str,
        interval: str = "12h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[BinanceKline]:
        """
        Fetch klines with automatic pagination for large date ranges.

        This method handles the 1000 candle limit per request by making
        multiple paginated requests if necessary.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            start_time: Start time (inclusive)
            end_time: End time (inclusive)

        Returns:
            List of all BinanceKline objects in the range
        """
        all_klines: list[BinanceKline] = []
        current_start = start_time

        while True:
            batch = await self.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=current_start,
                end_time=end_time,
                limit=1000,
            )

            if not batch:
                break

            all_klines.extend(batch)

            # Check if we got less than 1000, meaning we reached the end
            if len(batch) < 1000:
                break

            # Update start time for next batch (last candle's close time + 1ms)
            last_close_time_ms = batch[-1].close_time
            current_start = datetime.fromtimestamp((last_close_time_ms + 1) / 1000, tz=timezone.utc)

            # If we've passed the end_time, stop
            if end_time and current_start >= end_time:
                break

        logger.info(
            f"Fetched {len(all_klines)} klines for {symbol} "
            f"from {start_time} to {end_time} (paginated)"
        )
        return all_klines

    # ==================== Futures API Methods ====================

    async def get_funding_rate_history(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[BinanceFundingRate]:
        """
        Fetch historical funding rate data from Binance Futures API.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            start_time: Start time (inclusive)
            end_time: End time (inclusive)
            limit: Number of records to fetch (max 1000)

        Returns:
            List of validated BinanceFundingRate objects
        """
        url = f"{settings.binance_futures_api_base_url}/fapi/v1/fundingRate"
        params: dict[str, Any] = {
            "symbol": symbol,
            "limit": min(limit, 1000),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)

        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        logger.debug(f"Fetching funding rates: {symbol} (limit={limit})")

        try:
            data = await self._request_with_retry(url, params)

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format: expected list, got {type(data)}")

            rates = [BinanceFundingRate(**item) for item in data]
            logger.debug(f"Fetched {len(rates)} funding rates for {symbol}")
            return rates

        except Exception as e:
            logger.error(f"Error fetching funding rates for {symbol}: {e}")
            raise

    async def get_funding_rate_history_paginated(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[BinanceFundingRate]:
        """Fetch funding rate history with automatic pagination."""
        all_rates: list[BinanceFundingRate] = []
        current_start = start_time

        while True:
            batch = await self.get_funding_rate_history(
                symbol=symbol,
                start_time=current_start,
                end_time=end_time,
                limit=1000,
            )

            if not batch:
                break

            all_rates.extend(batch)

            if len(batch) < 1000:
                break

            # Update start time for next batch
            last_funding_time_ms = batch[-1].funding_time
            current_start = datetime.fromtimestamp((last_funding_time_ms + 1) / 1000, tz=timezone.utc)

            if end_time and current_start >= end_time:
                break

        logger.info(
            f"Fetched {len(all_rates)} funding rates for {symbol} "
            f"from {start_time} to {end_time} (paginated)"
        )
        return all_rates

    async def get_mark_price_klines(
        self,
        symbol: str,
        interval: str = "8h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1500,
    ) -> list[BinanceMarkPriceKline]:
        """
        Fetch mark price klines from Binance Futures API.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '8h')
            start_time: Start time (inclusive)
            end_time: End time (inclusive)
            limit: Number of candles to fetch (max 1500)

        Returns:
            List of validated BinanceMarkPriceKline objects
        """
        url = f"{settings.binance_futures_api_base_url}/fapi/v1/markPriceKlines"
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1500),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)

        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        logger.debug(f"Fetching mark price klines: {symbol} {interval} (limit={limit})")

        try:
            data = await self._request_with_retry(url, params)

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format: expected list, got {type(data)}")

            klines = [BinanceMarkPriceKline.from_list(item) for item in data]
            logger.debug(f"Fetched {len(klines)} mark price klines for {symbol}")
            return klines

        except Exception as e:
            logger.error(f"Error fetching mark price klines for {symbol}: {e}")
            raise

    async def get_mark_price_klines_paginated(
        self,
        symbol: str,
        interval: str = "8h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[BinanceMarkPriceKline]:
        """Fetch mark price klines with automatic pagination."""
        all_klines: list[BinanceMarkPriceKline] = []
        current_start = start_time

        while True:
            batch = await self.get_mark_price_klines(
                symbol=symbol,
                interval=interval,
                start_time=current_start,
                end_time=end_time,
                limit=1500,
            )

            if not batch:
                break

            all_klines.extend(batch)

            if len(batch) < 1500:
                break

            last_close_time_ms = batch[-1].close_time
            current_start = datetime.fromtimestamp((last_close_time_ms + 1) / 1000, tz=timezone.utc)

            if end_time and current_start >= end_time:
                break

        logger.info(
            f"Fetched {len(all_klines)} mark price klines for {symbol} "
            f"from {start_time} to {end_time} (paginated)"
        )
        return all_klines

    async def get_index_price_klines(
        self,
        pair: str,
        interval: str = "8h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1500,
    ) -> list[BinanceIndexPriceKline]:
        """
        Fetch index price klines from Binance Futures API.

        Note: This endpoint uses 'pair' parameter instead of 'symbol'.

        Args:
            pair: Trading pair (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '8h')
            start_time: Start time (inclusive)
            end_time: End time (inclusive)
            limit: Number of candles to fetch (max 1500)

        Returns:
            List of validated BinanceIndexPriceKline objects
        """
        url = f"{settings.binance_futures_api_base_url}/fapi/v1/indexPriceKlines"
        params: dict[str, Any] = {
            "pair": pair,  # Note: uses 'pair' not 'symbol'
            "interval": interval,
            "limit": min(limit, 1500),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)

        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        logger.debug(f"Fetching index price klines: {pair} {interval} (limit={limit})")

        try:
            data = await self._request_with_retry(url, params)

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format: expected list, got {type(data)}")

            klines = [BinanceIndexPriceKline.from_list(item) for item in data]
            logger.debug(f"Fetched {len(klines)} index price klines for {pair}")
            return klines

        except Exception as e:
            logger.error(f"Error fetching index price klines for {pair}: {e}")
            raise

    async def get_index_price_klines_paginated(
        self,
        pair: str,
        interval: str = "8h",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[BinanceIndexPriceKline]:
        """Fetch index price klines with automatic pagination."""
        all_klines: list[BinanceIndexPriceKline] = []
        current_start = start_time

        while True:
            batch = await self.get_index_price_klines(
                pair=pair,
                interval=interval,
                start_time=current_start,
                end_time=end_time,
                limit=1500,
            )

            if not batch:
                break

            all_klines.extend(batch)

            if len(batch) < 1500:
                break

            last_close_time_ms = batch[-1].close_time
            current_start = datetime.fromtimestamp((last_close_time_ms + 1) / 1000, tz=timezone.utc)

            if end_time and current_start >= end_time:
                break

        logger.info(
            f"Fetched {len(all_klines)} index price klines for {pair} "
            f"from {start_time} to {end_time} (paginated)"
        )
        return all_klines

    async def get_open_interest_history(
        self,
        symbol: str,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[BinanceOpenInterest]:
        """
        Fetch open interest history from Binance Futures API.

        Note: This endpoint has limited historical data (typically 30 days).

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            period: Data collection period ('5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d')
            start_time: Start time (inclusive)
            end_time: End time (inclusive)
            limit: Number of records to fetch (max 500)

        Returns:
            List of validated BinanceOpenInterest objects
        """
        # Note: Open interest history uses a different base path
        url = f"{settings.binance_futures_api_base_url}/futures/data/openInterestHist"
        params: dict[str, Any] = {
            "symbol": symbol,
            "period": period,
            "limit": min(limit, 500),
        }

        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)

        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        logger.debug(f"Fetching open interest: {symbol} {period} (limit={limit})")

        try:
            data = await self._request_with_retry(url, params)

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format: expected list, got {type(data)}")

            oi_data = [BinanceOpenInterest(**item) for item in data]
            logger.debug(f"Fetched {len(oi_data)} open interest data points for {symbol}")
            return oi_data

        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            raise

    async def get_open_interest_history_paginated(
        self,
        symbol: str,
        period: str = "5m",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[BinanceOpenInterest]:
        """Fetch open interest history with automatic pagination."""
        all_data: list[BinanceOpenInterest] = []
        current_start = start_time

        while True:
            batch = await self.get_open_interest_history(
                symbol=symbol,
                period=period,
                start_time=current_start,
                end_time=end_time,
                limit=500,
            )

            if not batch:
                break

            all_data.extend(batch)

            if len(batch) < 500:
                break

            last_timestamp_ms = batch[-1].timestamp
            current_start = datetime.fromtimestamp((last_timestamp_ms + 1) / 1000, tz=timezone.utc)

            if end_time and current_start >= end_time:
                break

        logger.info(
            f"Fetched {len(all_data)} open interest data points for {symbol} "
            f"from {start_time} to {end_time} (paginated)"
        )
        return all_data
