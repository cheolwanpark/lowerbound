#!/usr/bin/env python3
"""
Standalone test script for the portfolio agent implementation.
Tests the agent logic with mocked backend client and verbose mode enabled.

Usage: python test.py
"""

import asyncio
import os
import httpx
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.agent.agent import ChatAgent
from src.models import (
    ChatCreateRequest,
    ChatRecord,
    ChatMessage,
    PortfolioPosition,
)
from src.backend_client import BackendClient
from src.config import Settings
from src.storage.chat_store import ChatStore
from src.storage.redis_client import create_redis_client
from src.wrapper import Agent


def patch_agent_for_verbose():
    """
    Patch the Agent class to enable verbose mode.
    This monkey-patches the Agent.arun method from wrapper.py.
    """
    # Store the original arun method
    original_arun = Agent.arun

    async def verbose_arun(self, prompt: str, *, verbose: bool = True) -> Optional[str]:
        """Wrapper that forces verbose=True"""
        print("\n" + "="*80)
        print("AGENT EXECUTION (VERBOSE MODE ENABLED)")
        print("="*80 + "\n")
        return await original_arun(self, prompt, verbose=True)

    # Replace the method
    Agent.arun = verbose_arun
    print("[INFO] Verbose mode enabled for agent execution\n")


async def test_initial_portfolio_conservative():
    """Test 1: Create an initial portfolio with conservative strategy."""
    print("\n" + "🔵" + "="*78 + "🔵")
    print("TEST 1: Initial Portfolio Creation (Conservative Strategy)")
    print("🔵" + "="*78 + "🔵" + "\n")

    # Setup
    settings = Settings(
        claude_code_oauth_token="test-token-12345",
        backend_api_url="http://localhost:8000",
        backend_api_key="test-api-key",
        redis_url="redis://127.0.0.1:6379/0",
        queue_name="test-queue",
        max_workers=1,
        agent_timeout_seconds=120,
        log_level="INFO",
    )

    # Create Redis client and ChatStore
    redis_client = create_redis_client(settings)
    chat_store = ChatStore(redis_client)

    # Use real backend client with shared HTTP client
    async with httpx.AsyncClient() as http_client:
        backend_client = BackendClient(
            settings.backend_api_url,
            http_client,
            settings.backend_api_key
        )
        agent = ChatAgent(settings, backend_client, chat_store)

        # Test request
        request = ChatCreateRequest(
            user_prompt="Create a conservative portfolio for me with low risk",
            strategy="Conservative",
            target_apy=10.0,
            max_drawdown=15.0,
        )

        try:
            result = await agent.run_initial(
                chat_id="test-chat-001",
                request=request,
                user_prompt=request.user_prompt,
            )

            print("\n" + "─"*80)
            print("TEST RESULT:")
            print("─"*80)
            print(f"Success: {result.success}")
            print(f"Error: {result.error}")
            print(f"\nAgent Messages ({len(result.messages)}):")
            for i, msg in enumerate(result.messages):
                print(f"  [{i+1}] Type: {msg.type}")
                print(f"      Message: {msg.message[:100]}...")
                if msg.reasonings:
                    print(f"      Reasonings: {len(msg.reasonings)} items")

            if result.portfolio:
                print(f"\nPortfolio Positions ({len(result.portfolio)}):")
                for pos in result.portfolio:
                    print(f"  - {pos.asset}: {pos.quantity} @ ${pos.entry_price:.2f} ({pos.position_type})")
            else:
                print("\nNo portfolio returned")

            print("─"*80 + "\n")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}\n")
            import traceback
            traceback.print_exc()


async def test_initial_portfolio_aggressive():
    """Test 2: Create an initial portfolio with aggressive strategy."""
    print("\n" + "🟠" + "="*78 + "🟠")
    print("TEST 2: Initial Portfolio Creation (Aggressive Strategy)")
    print("🟠" + "="*78 + "🟠" + "\n")

    # Setup
    settings = Settings(
        claude_code_oauth_token="test-token-12345",
        backend_api_url="http://localhost:8000",
        backend_api_key="test-api-key",
        redis_url="redis://127.0.0.1:6379/0",
        queue_name="test-queue",
        max_workers=1,
        agent_timeout_seconds=120,
        log_level="INFO",
    )

    # Create Redis client and ChatStore
    redis_client = create_redis_client(settings)
    chat_store = ChatStore(redis_client)

    # Use real backend client with shared HTTP client
    async with httpx.AsyncClient() as http_client:
        backend_client = BackendClient(
            settings.backend_api_url,
            http_client,
            settings.backend_api_key
        )
        agent = ChatAgent(settings, backend_client, chat_store)

        # Test request
        request = ChatCreateRequest(
            user_prompt="I want high returns! Create an aggressive portfolio",
            strategy="Aggressive",
            target_apy=25.0,
            max_drawdown=30.0,
        )

        try:
            result = await agent.run_initial(
                chat_id="test-chat-002",
                request=request,
                user_prompt=request.user_prompt,
            )

            print("\n" + "─"*80)
            print("TEST RESULT:")
            print("─"*80)
            print(f"Success: {result.success}")
            print(f"Error: {result.error}")
            print(f"\nAgent Messages ({len(result.messages)}):")
            for i, msg in enumerate(result.messages):
                print(f"  [{i+1}] Type: {msg.type}")
                print(f"      Message: {msg.message[:100]}...")
                if msg.reasonings:
                    print(f"      Reasonings: {len(msg.reasonings)} items")

            if result.portfolio:
                print(f"\nPortfolio Positions ({len(result.portfolio)}):")
                for pos in result.portfolio:
                    print(f"  - {pos.asset}: {pos.quantity} @ ${pos.entry_price:.2f} ({pos.position_type})")
            else:
                print("\nNo portfolio returned")

            print("─"*80 + "\n")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}\n")
            import traceback
            traceback.print_exc()


async def test_followup_adjustment():
    """Test 3: Follow-up conversation to adjust existing portfolio."""
    print("\n" + "🟢" + "="*78 + "🟢")
    print("TEST 3: Follow-up Portfolio Adjustment")
    print("🟢" + "="*78 + "🟢" + "\n")

    # Setup
    settings = Settings(
        claude_code_oauth_token="test-token-12345",
        backend_api_url="http://localhost:8000",
        backend_api_key="test-api-key",
        redis_url="redis://127.0.0.1:6379/0",
        queue_name="test-queue",
        max_workers=1,
        agent_timeout_seconds=120,
        log_level="INFO",
    )

    # Create Redis client and ChatStore
    redis_client = create_redis_client(settings)
    chat_store = ChatStore(redis_client)

    # Use real backend client with shared HTTP client
    async with httpx.AsyncClient() as http_client:
        backend_client = BackendClient(
            settings.backend_api_url,
            http_client,
            settings.backend_api_key
        )
        agent = ChatAgent(settings, backend_client, chat_store)

        # Create a mock chat record with history
        existing_portfolio = [
            PortfolioPosition(
                asset="BTC",
                quantity=0.4,
                position_type="spot",
                entry_price=50000.0,
            ),
            PortfolioPosition(
                asset="ETH",
                quantity=10.0,
                position_type="spot",
                entry_price=3000.0,
            ),
            PortfolioPosition(
                asset="USDT",
                quantity=15000.0,
                position_type="lending_supply",
                entry_price=1.0,
            ),
        ]

        chat_record = ChatRecord(
            id="test-chat-003",
            status="completed",
            strategy="Conservative",
            target_apy=10.0,
            max_drawdown=15.0,
            portfolio=existing_portfolio,
            messages=[
                ChatMessage(
                    type="user",
                    message="Create a conservative portfolio",
                ),
                ChatMessage(
                    type="agent",
                    message="I've created a conservative portfolio with BTC, ETH, and USDT.",
                ),
            ],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        try:
            result = await agent.run_followup(
                chat_id="test-chat-003",
                chat_record=chat_record,
                user_prompt="I'm concerned about volatility. Can you make it even more conservative?",
            )

            print("\n" + "─"*80)
            print("TEST RESULT:")
            print("─"*80)
            print(f"Success: {result.success}")
            print(f"Error: {result.error}")
            print(f"\nAgent Messages ({len(result.messages)}):")
            for i, msg in enumerate(result.messages):
                print(f"  [{i+1}] Type: {msg.type}")
                print(f"      Message: {msg.message[:100]}...")
                if msg.reasonings:
                    print(f"      Reasonings: {len(msg.reasonings)} items")

            if result.portfolio:
                print(f"\nUpdated Portfolio Positions ({len(result.portfolio)}):")
                for pos in result.portfolio:
                    print(f"  - {pos.asset}: {pos.quantity} @ ${pos.entry_price:.2f} ({pos.position_type})")

                print("\nOriginal Portfolio (for comparison):")
                for pos in existing_portfolio:
                    print(f"  - {pos.asset}: {pos.quantity} @ ${pos.entry_price:.2f} ({pos.position_type})")
            else:
                print("\nNo portfolio changes")

            print("─"*80 + "\n")

        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}\n")
            import traceback
            traceback.print_exc()


async def main():
    """Main test execution."""
    print("\n" + "="*80)
    print("PORTFOLIO AGENT TEST SUITE")
    print("Testing agent implementation with mocked backend client")
    print("="*80)

    # Print loaded environment variables
    print("\nLoaded Environment Variables:")
    print(f"  CLAUDE_CODE_OAUTH_TOKEN: {'✓ Set' if os.getenv('CLAUDE_CODE_OAUTH_TOKEN') else '✗ Not set'}")
    print(f"  BACKEND_API_URL: {os.getenv('BACKEND_API_URL', 'http://localhost:8000 (default)')}")
    print(f"  REDIS_URL: {os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0 (default)')}")
    print(f"  QUEUE_NAME: {os.getenv('QUEUE_NAME', 'chat-agent (default)')}")
    print(f"  AGENT_TIMEOUT_SECONDS: {os.getenv('AGENT_TIMEOUT_SECONDS', '60 (default)')}")
    print(f"  LOG_LEVEL: {os.getenv('LOG_LEVEL', 'INFO (default)')}")
    print("="*80 + "\n")

    # Enable verbose mode
    patch_agent_for_verbose()

    # Run all tests
    await test_initial_portfolio_conservative()
    await asyncio.sleep(1)  # Brief pause between tests

    await test_initial_portfolio_aggressive()
    await asyncio.sleep(1)

    await test_followup_adjustment()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
