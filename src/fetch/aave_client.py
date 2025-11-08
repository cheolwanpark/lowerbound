"""Aave GraphQL client for fetching lending data from The Graph."""

import asyncio
import time
from datetime import datetime, timezone

import httpx
from loguru import logger

from src.config import settings
from src.models import AaveReserveData


class RateLimiter:
    """Rate limiter for The Graph API requests."""

    def __init__(self, requests_per_minute: int = 100, request_delay_ms: int = 200):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            request_delay_ms: Minimum delay between requests in milliseconds
        """
        self.requests_per_minute = requests_per_minute
        self.request_delay_sec = request_delay_ms / 1000.0
        self.semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self.last_request_time: float | None = None
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request can be made within rate limits."""
        await self.semaphore.acquire()

        async with self.lock:
            if self.last_request_time is not None:
                elapsed = time.time() - self.last_request_time
                wait_time = self.request_delay_sec - elapsed
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self.last_request_time = time.time()

    def release(self) -> None:
        """Release the semaphore after request completes."""
        self.semaphore.release()


class AaveClient:
    """
    Async HTTP client for Aave V3 GraphQL API (The Graph).

    Handles rate limiting, retries, and error handling for GraphQL queries.
    """

    def __init__(self, graphql_url: str | None = None):
        """
        Initialize Aave GraphQL client.

        Args:
            graphql_url: GraphQL endpoint URL (defaults to config)
        """
        self.graphql_url = graphql_url or settings.aave_v3_graphql_url
        self.rate_limiter = RateLimiter(requests_per_minute=100, request_delay_ms=200)
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"Initialized Aave GraphQL client: {self.graphql_url}")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Aave GraphQL client closed")

    async def _execute_query(self, query: str, variables: dict | None = None, max_retries: int = 3) -> dict:
        """
        Execute a GraphQL query with retry logic.

        Args:
            query: GraphQL query string
            variables: Query variables
            max_retries: Maximum number of retry attempts

        Returns:
            GraphQL response data

        Raises:
            httpx.HTTPError: If all retries fail
            ValueError: If GraphQL returns errors
        """
        last_exception = None

        for attempt in range(max_retries):
            await self.rate_limiter.acquire()

            try:
                payload = {"query": query}
                if variables:
                    payload["variables"] = variables

                response = await self.client.post(self.graphql_url, json=payload)
                response.raise_for_status()

                data = response.json()

                # Check for GraphQL errors (can occur with 200 OK)
                if "errors" in data:
                    error_msg = "; ".join([err.get("message", str(err)) for err in data["errors"]])
                    raise ValueError(f"GraphQL errors: {error_msg}")

                return data.get("data", {})

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.warning(f"HTTP error on attempt {attempt + 1}/{max_retries}: {e.response.status_code}")

                if e.response.status_code == 429:
                    # Rate limited, wait longer
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    logger.info(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                elif e.response.status_code >= 500:
                    # Server error, exponential backoff
                    wait_time = 2**attempt
                    logger.info(f"Server error, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Client error (4xx), don't retry
                    break

            except (httpx.RequestError, ValueError) as e:
                last_exception = e
                logger.warning(f"Request error on attempt {attempt + 1}/{max_retries}: {e}")

                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                break

            finally:
                self.rate_limiter.release()

        # All retries exhausted
        logger.error(f"All {max_retries} retries failed for Aave GraphQL query")
        if last_exception:
            raise last_exception
        raise RuntimeError("GraphQL query failed with unknown error")

    async def query_reserve_events(
        self, symbol: str, after_timestamp: int | None = None, limit: int = 1000
    ) -> list[AaveReserveData]:
        """
        Query reserve parameter history events for an asset.

        Fetches event-based data from Aave Subgraph in chronological order.

        Args:
            symbol: Reserve symbol (e.g., 'WETH', 'USDC')
            after_timestamp: Fetch events after this Unix timestamp (optional)
            limit: Maximum number of events to return (max 1000)

        Returns:
            List of AaveReserveData objects in chronological order

        Raises:
            ValueError: If symbol contains invalid characters
        """
        # Sanitize symbol to prevent GraphQL injection
        # Only allow alphanumeric uppercase characters (valid Aave symbols)
        import re

        if not re.match(r"^[A-Z0-9]{1,20}$", symbol):
            raise ValueError(
                f"Invalid symbol: {symbol}. Must be 1-20 uppercase alphanumeric characters."
            )

        # Build GraphQL query
        where_clause = f'reserve_: {{symbol: "{symbol}"}}'
        if after_timestamp is not None:
            # Validate timestamp is a positive integer
            if not isinstance(after_timestamp, int) or after_timestamp < 0:
                raise ValueError(f"Invalid timestamp: {after_timestamp}")
            where_clause = f'reserve_: {{symbol: "{symbol}"}}, timestamp_gt: {after_timestamp}'

        query = """
        query($limit: Int!, $whereClause: String!) {
          reserveParamsHistoryItems(
            where: $whereClause
            orderBy: timestamp
            orderDirection: asc
            first: $limit
          ) {
            timestamp
            liquidityRate
            variableBorrowRate
            stableBorrowRate
            totalLiquidity
            availableLiquidity
            totalCurrentVariableDebt
            utilizationRate
            priceInEth
          }
        }
        """

        # Note: The Graph doesn't support dynamic where clauses via variables,
        # so we build the query directly
        query = f"""
        {{
          reserveParamsHistoryItems(
            where: {{{where_clause}}}
            orderBy: timestamp
            orderDirection: asc
            first: {limit}
          ) {{
            timestamp
            liquidityRate
            variableBorrowRate
            stableBorrowRate
            totalLiquidity
            availableLiquidity
            totalCurrentVariableDebt
            totalPrincipalStableDebt
            utilizationRate
            priceInEth
          }}
        }}
        """

        logger.debug(f"Querying Aave events for {symbol} (after={after_timestamp}, limit={limit})")

        data = await self._execute_query(query)
        items = data.get("reserveParamsHistoryItems", [])

        logger.info(f"Fetched {len(items)} events for {symbol}")

        # Parse into AaveReserveData models
        return [AaveReserveData(**item) for item in items]

    async def query_current_reserves(self, symbols: list[str]) -> dict[str, AaveReserveData]:
        """
        Query current state for multiple reserves.

        Args:
            symbols: List of reserve symbols (e.g., ['WETH', 'USDC'])

        Returns:
            Dict mapping symbol to current AaveReserveData
        """
        if not symbols:
            return {}

        # Build symbol filter for GraphQL
        symbols_filter = ", ".join([f'"{s}"' for s in symbols])

        query = f"""
        {{
          reserves(where: {{symbol_in: [{symbols_filter}]}}) {{
            symbol
            liquidityRate
            variableBorrowRate
            stableBorrowRate
            totalLiquidity
            availableLiquidity
            totalCurrentVariableDebt
            totalPrincipalStableDebt
            utilizationRate
            price {{
              priceInEth
            }}
          }}
        }}
        """

        logger.debug(f"Querying current reserves for {len(symbols)} assets")

        data = await self._execute_query(query)
        reserves = data.get("reserves", [])

        logger.info(f"Fetched current state for {len(reserves)} reserves")

        # Convert to AaveReserveData format (use current time as timestamp)
        result = {}
        current_time = int(datetime.now(timezone.utc).timestamp())

        for reserve in reserves:
            symbol = reserve["symbol"]
            # Extract price from nested structure
            price_eth = reserve.get("price", {}).get("priceInEth")

            # Build AaveReserveData
            reserve_data = AaveReserveData(
                timestamp=current_time,
                liquidityRate=reserve["liquidityRate"],
                variableBorrowRate=reserve["variableBorrowRate"],
                stableBorrowRate=reserve["stableBorrowRate"],
                totalLiquidity=reserve["totalLiquidity"],
                availableLiquidity=reserve["availableLiquidity"],
                totalCurrentVariableDebt=reserve["totalCurrentVariableDebt"],
                utilizationRate=reserve["utilizationRate"],
                priceInEth=price_eth,
            )
            result[symbol] = reserve_data

        return result

    async def verify_connectivity(self) -> bool:
        """
        Test connectivity to Aave GraphQL endpoint.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Simple query to test connection
            query = """
            {
              reserves(first: 1) {
                symbol
              }
            }
            """

            data = await self._execute_query(query)
            reserves = data.get("reserves", [])

            if reserves:
                logger.info(f"Aave GraphQL connectivity verified (found reserve: {reserves[0]['symbol']})")
                return True
            else:
                logger.warning("Aave GraphQL connectivity test returned no reserves")
                return False

        except Exception as e:
            logger.error(f"Aave GraphQL connectivity test failed: {e}")
            return False


async def create_aave_client() -> AaveClient:
    """
    Factory function to create and verify Aave client.

    Returns:
        Initialized AaveClient instance

    Raises:
        RuntimeError: If connectivity test fails
    """
    client = AaveClient()

    # Verify connectivity
    is_connected = await client.verify_connectivity()
    if not is_connected:
        await client.close()
        raise RuntimeError("Failed to connect to Aave GraphQL API")

    return client
