#!/usr/bin/env python3
"""
Test script for performance_vs_baseline graph endpoint
"""
import asyncio
from datetime import datetime, timedelta, timezone

async def test_performance_graph():
    from src.analysis.graph import calculate_performance_vs_baseline
    from src.models import PerformanceGraphData, PerformanceDataPoint

    # Test data: simple BTC spot position
    positions = [
        {
            "asset": "BTC",
            "quantity": 1.0,
            "position_type": "spot",
            "entry_price": 90000,
            "leverage": 1.0,
        }
    ]

    # Use a date 30 days ago as initial timestamp
    initial_timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    print(f"Testing performance_vs_baseline calculation...")
    print(f"Initial timestamp: {initial_timestamp}")
    print(f"Positions: {positions}")

    result = await calculate_performance_vs_baseline(
        positions=positions,
        initial_timestamp=initial_timestamp,
        lookback_days=30,
    )

    print(f"\nResult:")
    print(f"  Data points: {len(result['data_points'])}")
    print(f"  Initial value: ${result['initial_value']:,.2f}")
    print(f"  Date range: {result['date_range']['start']} to {result['date_range']['end']}")

    if result['data_points']:
        print(f"\nFirst data point:")
        print(f"  {result['data_points'][0]}")
        print(f"\nLast data point:")
        print(f"  {result['data_points'][-1]}")

        # Validate data structure
        data = PerformanceGraphData(**result)
        print(f"\n✓ Data model validation passed")

        # Check that we have three return percentages
        for point in data.data_points[:3]:
            print(f"\nData point at {point.timestamp}:")
            print(f"  Portfolio: {point.portfolio_return_pct:.2f}%")
            print(f"  BTC: {point.btc_return_pct:.2f}%")
            print(f"  USDT: {point.usdt_return_pct:.2f}%")

    print("\n✓ Test completed successfully!")
    return result

if __name__ == "__main__":
    asyncio.run(test_performance_graph())
