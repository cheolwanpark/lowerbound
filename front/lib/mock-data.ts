import { GraphChunk, TableChunk } from '@/types'

/**
 * Generates mock crypto price data for graphs
 */
export function generateMockGraphData(): GraphChunk['data'] {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
  const values = [42000, 45000, 43000, 48000, 51000, 49000]

  return {
    labels: months,
    values: values
  }
}

/**
 * Generates mock portfolio holdings data for tables
 */
export function generateMockTableData(): TableChunk['data'] {
  return {
    headers: ['Asset', 'Amount', 'Value', 'Change'],
    rows: [
      ['BTC', '2.5', '$122,500', '+5.2%'],
      ['ETH', '15.0', '$45,000', '+3.8%'],
      ['SOL', '100', '$12,000', '-1.5%'],
      ['USDT', '50,000', '$50,000', '0.0%']
    ]
  }
}

/**
 * Generates mock streaming response text chunks
 */
export function generateMockTextChunks(): string[] {
  return [
    'Analyzing your portfolio...',
    '\n\nBased on current market conditions, ',
    'here is your portfolio performance:\n\n',
    'Your total portfolio value is $229,500 ',
    'with an overall gain of +4.2% this month. ',
    '\n\nHere\'s the price trend for BTC:\n\n',
    // Graph will be inserted here
    '\n\nYour current holdings:\n\n',
    // Table will be inserted here
    '\n\nRecommendation: ',
    'Your portfolio shows strong performance. ',
    'Consider rebalancing to maintain your target allocations.'
  ]
}
