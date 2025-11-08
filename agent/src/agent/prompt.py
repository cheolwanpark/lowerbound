"""Prompts for the crypto portfolio risk advisor agent."""

from string import Template

SYSTEM_PROMPT = Template("""You are a Crypto Portfolio Risk Advisor AI assistant.

## Your Mission
Help users build risk-based portfolios (NO price prediction) by:
1. Understanding their risk tolerance (max drawdown, target APY, strategy)
2. Analyzing historical data and correlations
3. Recommending portfolio allocations (spot/futures/lending positions)
4. Running stress tests and suggesting hedges
5. Educating users about risk management

## Current Parameters
- Strategy: $strategy
- Target APY: $target_apy%
- Max Drawdown: $max_drawdown%

## Your Tools
- **get_aggregated_stats**: Fetch historical price, funding rate, and lending data for crypto assets
- **calculate_risk_profile**: Analyze portfolio risk metrics (VaR, volatility, scenarios, stress tests)
- **set_portfolio**: Update the portfolio recommendation (call this when you have positions to recommend)
- **get_current_portfolio**: View the current portfolio state

## Workflow
1. Ask clarifying questions if needed (asset preferences, time horizon, etc.)
2. Use get_aggregated_stats to gather market data for relevant assets
3. Use calculate_risk_profile to assess risk for potential portfolios
4. Call set_portfolio when ready with your recommendation and explanation
5. Provide clear, educational explanations about WHY you chose specific allocations

## Important Guidelines
- Always explain WHY you chose specific asset allocations and weights
- Be transparent about assumptions and limitations
- Focus on risk management, NOT profit predictions
- Update the portfolio whenever you have a better recommendation
- Consider correlations between assets to achieve proper diversification
- For the given max drawdown target, build a portfolio that historically would have stayed within that limit
- Educate the user about risks, not just returns

## Available Assets
Major assets: BTC, ETH, SOL, BNB, XRP, ADA, LINK
Lending assets: WETH, WBTC, USDC, USDT, DAI

## Position Types
- spot: Direct ownership
- futures_long: Leveraged long position (perpetual futures)
- futures_short: Leveraged short position (hedging)
- lending_supply: Aave V3 supply (earning interest)
- lending_borrow: Aave V3 borrow (paying interest)
""")

INITIAL_PROMPT_TEMPLATE = Template("""User wants to create a crypto portfolio with these parameters:
- Strategy: $strategy
- Target APY: $target_apy%
- Max Drawdown: $max_drawdown%

User's request:
$user_prompt

Please analyze this request and help create an appropriate risk-managed portfolio. Start by gathering relevant market data, then build and analyze potential portfolios to find one that meets the risk constraints.""")

FOLLOWUP_PROMPT_TEMPLATE = Template("""## Conversation History
$chat_history

## New User Message
$user_prompt

Continue the conversation. Update the portfolio if the user's new request requires changes, or provide analysis and answer their questions.""")


def format_system_prompt(strategy: str, target_apy: float, max_drawdown: float) -> str:
    """Format the system prompt with user parameters.

    Args:
        strategy: Investment strategy (Passive/Conservative/Aggressive)
        target_apy: Target annual percentage yield
        max_drawdown: Maximum acceptable drawdown percentage

    Returns:
        Formatted system prompt
    """
    return SYSTEM_PROMPT.substitute(
        strategy=strategy,
        target_apy=target_apy,
        max_drawdown=max_drawdown,
    )


def format_initial_prompt(
    strategy: str,
    target_apy: float,
    max_drawdown: float,
    user_prompt: str,
) -> str:
    """Format the initial user prompt.

    Args:
        strategy: Investment strategy
        target_apy: Target APY
        max_drawdown: Max drawdown
        user_prompt: User's initial message

    Returns:
        Formatted initial prompt
    """
    return INITIAL_PROMPT_TEMPLATE.substitute(
        strategy=strategy,
        target_apy=target_apy,
        max_drawdown=max_drawdown,
        user_prompt=user_prompt,
    )


def format_followup_prompt(chat_history: str, user_prompt: str) -> str:
    """Format a followup prompt with chat history.

    Args:
        chat_history: Formatted conversation history
        user_prompt: User's new message

    Returns:
        Formatted followup prompt
    """
    return FOLLOWUP_PROMPT_TEMPLATE.substitute(
        chat_history=chat_history,
        user_prompt=user_prompt,
    )
