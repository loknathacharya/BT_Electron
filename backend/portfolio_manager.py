"""
Phase 8: Portfolio Management
Multi-symbol backtests, portfolio allocation, rebalancing, and correlation analysis.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import copy


def calculate_portfolio_weights(
    allocation_mode: str,
    symbols: List[str],
    custom_weights: Optional[Dict[str, float]] = None,
    equal_weight: bool = True
) -> Dict[str, float]:
    """Calculate portfolio weights for each symbol.
    
    Args:
        allocation_mode: 'equal', 'custom', 'risk_parity', 'market_cap'
        symbols: List of symbols
        custom_weights: Dict of symbol -> weight (for custom mode)
        equal_weight: If True, use equal weighting (for equal mode)
    
    Returns:
        Dict of symbol -> weight (sum = 1.0)
    """
    n = len(symbols)
    if n == 0:
        return {}
    
    if allocation_mode == 'equal':
        weight = 1.0 / n
        return {symbol: weight for symbol in symbols}
    
    elif allocation_mode == 'custom' and custom_weights:
        # Check if all symbols have custom weights
        all_symbols_present = all(s in custom_weights for s in symbols)
        if not all_symbols_present:
            # Fall back to equal weights if custom weights incomplete
            weight = 1.0 / n
            return {symbol: weight for symbol in symbols}
        
        # Normalize custom weights to sum to 1
        total = sum(custom_weights.get(s, 0) for s in symbols)
        if total == 0:
            return calculate_portfolio_weights('equal', symbols)
        return {s: custom_weights.get(s, 0) / total for s in symbols}
    
    elif allocation_mode == 'risk_parity':
        # Equal risk contribution (simplified: equal weights as placeholder)
        # Full implementation would need volatility estimates
        weight = 1.0 / n
        return {symbol: weight for symbol in symbols}
    
    else:
        # Default to equal weight
        weight = 1.0 / n
        return {symbol: weight for symbol in symbols}


def calculate_correlation_matrix(returns_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate correlation matrix of returns.
    
    Args:
        returns_df: DataFrame with symbols as columns, returns as values
    
    Returns:
        Correlation matrix DataFrame
    """
    if returns_df.empty:
        return pd.DataFrame()
    
    return returns_df.corr()


def calculate_diversification_ratio(
    weights: Dict[str, float],
    returns_df: pd.DataFrame
) -> float:
    """Calculate portfolio diversification ratio.
    
    DR = (weighted avg volatility) / (portfolio volatility)
    Higher is better (more diversified)
    
    Args:
        weights: Symbol weights
        returns_df: Returns for each symbol
    
    Returns:
        Diversification ratio
    """
    if returns_df.empty or not weights:
        return 1.0
    
    # Calculate individual volatilities
    vols = returns_df.std()
    
    # Weighted average volatility
    weighted_vol = sum(weights.get(sym, 0) * vols.get(sym, 0) for sym in weights.keys())
    
    # Portfolio volatility
    # Convert weights to array in same order as returns_df columns
    weight_array = np.array([weights.get(col, 0) for col in returns_df.columns])
    cov_matrix = returns_df.cov()
    portfolio_var = np.dot(weight_array, np.dot(cov_matrix, weight_array))
    portfolio_vol = np.sqrt(portfolio_var)
    
    if portfolio_vol == 0:
        return 1.0
    
    return weighted_vol / portfolio_vol


def build_portfolio_equity_curve(
    symbol_trades: Dict[str, List[Dict[str, Any]]],
    weights: Dict[str, float],
    initial_capital: float,
    index: pd.DatetimeIndex
) -> Tuple[List[int], List[float], Dict[str, List[float]]]:
    """Build combined portfolio equity curve from individual symbol trades.
    
    Args:
        symbol_trades: Dict of symbol -> list of trades
        weights: Portfolio weights for each symbol
        initial_capital: Starting capital
        index: Common date index for alignment
    
    Returns:
        (timestamps, portfolio_equity, symbol_equities)
        symbol_equities is dict of symbol -> equity curve list
    """
    if not symbol_trades or not weights:
        idx_seconds = (index.view('int64') // 10**9).astype(int).tolist()
        return (idx_seconds, [initial_capital] * len(index), {})
    
    # Allocate capital to each symbol
    allocated_capital = {
        symbol: initial_capital * weights.get(symbol, 0)
        for symbol in symbol_trades.keys()
    }
    
    # Build individual equity curves
    symbol_equities = {}
    idx_seconds = (index.view('int64') // 10**9).astype(int).tolist()
    
    for symbol, trades in symbol_trades.items():
        capital = allocated_capital.get(symbol, 0)
        
        # Map exit date to cumulative PnL
        pnl_by_date: Dict[str, float] = {}
        for trade in trades:
            exit_date = trade.get('exit_date', '')
            entry_price = float(trade.get('entry_price', 0))
            exit_price = float(trade.get('exit_price', 0))
            shares = float(trade.get('shares', 0))
            direction = trade.get('direction', 'long')
            
            # Calculate PnL
            if direction == 'long':
                pnl = (exit_price - entry_price) * shares
            else:  # short
                pnl = (entry_price - exit_price) * shares
            
            pnl_by_date[exit_date] = pnl_by_date.get(exit_date, 0.0) + pnl
        
        # Build equity curve aligned with index
        equity = []
        current = float(capital)
        cumulative_pnl = 0.0
        
        for ts in index:
            date_str = ts.strftime('%Y-%m-%d')
            # Add any PnL that occurred on this date
            pnl_today = pnl_by_date.get(date_str, 0.0)
            cumulative_pnl += pnl_today
            equity.append(capital + cumulative_pnl)
        
        symbol_equities[symbol] = equity
    
    # Combine into portfolio equity
    portfolio_equity = []
    for i in range(len(index)):
        total = sum(symbol_equities[sym][i] for sym in symbol_equities.keys())
        portfolio_equity.append(total)
    
    return (idx_seconds, portfolio_equity, symbol_equities)


def calculate_portfolio_metrics(
    portfolio_equity: List[float],
    symbol_trades: Dict[str, List[Dict[str, Any]]],
    initial_capital: float,
    index: pd.DatetimeIndex,
    timeframe: str = '1D'
) -> Dict[str, Any]:
    """Calculate portfolio-level metrics.
    
    Args:
        portfolio_equity: Portfolio equity curve
        symbol_trades: Dict of symbol -> trades
        initial_capital: Starting capital
        index: Date index
        timeframe: Timeframe for annualization
    
    Returns:
        Dict with portfolio metrics
    """
    if not portfolio_equity:
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'total_trades': 0,
            'avg_trades_per_symbol': 0.0
        }
    
    # Portfolio returns
    final_equity = portfolio_equity[-1]
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0 if initial_capital else 0.0
    
    # Annualization factor
    tf = (timeframe or '1D').upper()
    periods_per_year = 252 if tf == '1D' else (24*252 if tf == '1H' else (6.5*60/15*252 if tf == '15M' else (6.5*60/5*252)))
    periods_per_year = float(periods_per_year) if periods_per_year else 252.0
    
    # Daily returns
    returns = []
    for i in range(1, len(portfolio_equity)):
        prev = portfolio_equity[i-1]
        curr = portfolio_equity[i]
        r = (curr - prev) / prev if prev else 0.0
        returns.append(r)
    
    # Annualized return
    if len(portfolio_equity) > 1 and initial_capital:
        per_period = (final_equity / initial_capital) ** (periods_per_year / max(1.0, float(len(portfolio_equity)))) - 1.0
        annualized_return_pct = per_period * 100.0
    else:
        annualized_return_pct = 0.0
    
    # Volatility (annualized)
    if len(returns) >= 2:
        vol = float(pd.Series(returns).std(ddof=1)) * np.sqrt(periods_per_year) * 100.0
    else:
        vol = 0.0
    
    # Sharpe ratio
    if len(returns) >= 2 and vol > 0:
        mean_r = float(pd.Series(returns).mean())
        std_r = float(pd.Series(returns).std(ddof=1))
        sharpe = (mean_r / std_r) * np.sqrt(periods_per_year) if std_r != 0 else 0.0
    else:
        sharpe = 0.0
    
    # Max drawdown
    dd = 0.0
    max_dd = 0.0
    peak = -float('inf')
    for eq in portfolio_equity:
        if eq > peak:
            peak = eq
            dd = 0.0
        else:
            dd = (eq - peak) / peak if peak > 0 else 0.0
            if dd < max_dd:
                max_dd = dd
    max_drawdown_pct = max_dd * 100.0
    
    # Trade counts
    total_trades = sum(len(trades) for trades in symbol_trades.values())
    avg_trades_per_symbol = total_trades / len(symbol_trades) if symbol_trades else 0.0
    
    return {
        'totalReturn': round(total_return_pct / 100.0, 6),  # Return as decimal
        'annualizedReturn': round(annualized_return_pct / 100.0, 6),
        'volatility': round(vol / 100.0, 6),
        'sharpeRatio': round(float(sharpe), 6),
        'maxDrawdown': round(max_drawdown_pct / 100.0, 6),
        'totalTrades': int(total_trades),
        'winRate': 0.0,  # TODO: Calculate from trades
        'profitFactor': 0.0,  # TODO: Calculate from trades
        'avgTradesPerSymbol': round(avg_trades_per_symbol, 2),
        'symbolsCount': len(symbol_trades)
    }


def rebalance_portfolio(
    current_positions: Dict[str, float],
    target_weights: Dict[str, float],
    current_prices: Dict[str, float],
    rebalance_threshold: float = 0.05
) -> Dict[str, Any]:
    """Determine rebalancing trades to align with target weights.
    
    Args:
        current_positions: Dict of symbol -> current value in dollars
        target_weights: Dict of symbol -> target weight (0-1)
        current_prices: Dict of symbol -> current price per share
        rebalance_threshold: Minimum deviation to trigger rebalance (default 5%)
    
    Returns:
        Dict with rebalancing actions needed per symbol
    """
    # Calculate total equity
    total_equity = sum(current_positions.values())
    
    if total_equity == 0:
        return {}
    
    # Calculate current weights
    current_weights = {
        symbol: value / total_equity
        for symbol, value in current_positions.items()
    }
    
    # Calculate target values and trades needed
    rebalance_trades = {}
    for symbol in target_weights.keys():
        current_value = current_positions.get(symbol, 0)
        target_value = total_equity * target_weights.get(symbol, 0)
        delta_value = target_value - current_value
        
        # Check if deviation exceeds threshold
        current_weight = current_weights.get(symbol, 0)
        target_weight = target_weights.get(symbol, 0)
        deviation = abs(current_weight - target_weight)
        
        if deviation > rebalance_threshold:
            price = current_prices.get(symbol, 1)
            shares = delta_value / price if price > 0 else 0
            
            rebalance_trades[symbol] = {
                'action': 'buy' if shares > 0 else 'sell',
                'shares': abs(shares),
                'value': abs(delta_value),
                'deviation': deviation
            }
    
    return rebalance_trades


def calculate_symbol_correlation(
    symbol_a_trades: List[Dict[str, Any]],
    symbol_b_trades: List[Dict[str, Any]],
    index: pd.DatetimeIndex
) -> float:
    """Calculate correlation between two symbols based on their returns.
    
    Args:
        symbol_a_trades: Trades for symbol A
        symbol_b_trades: Trades for symbol B
        index: Common date index
    
    Returns:
        Correlation coefficient (-1 to 1)
    """
    # Build returns series for each symbol
    def build_returns(trades):
        # Calculate PnL for each trade
        returns_data = []
        for trade in trades:
            entry_price = float(trade.get('entry_price', 100))
            exit_price = float(trade.get('exit_price', 100))
            direction = trade.get('direction', 'long')
            
            if direction == 'long':
                ret = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
            else:  # short
                ret = (entry_price - exit_price) / entry_price if entry_price > 0 else 0
            
            returns_data.append(ret)
        
        return returns_data
    
    returns_a = build_returns(symbol_a_trades)
    returns_b = build_returns(symbol_b_trades)
    
    # Need at least 2 points for correlation
    if len(returns_a) < 2 or len(returns_b) < 2:
        return 0.0
    
    # Pad shorter list with zeros to match lengths
    max_len = max(len(returns_a), len(returns_b))
    while len(returns_a) < max_len:
        returns_a.append(0.0)
    while len(returns_b) < max_len:
        returns_b.append(0.0)
    
    # Calculate correlation
    if len(returns_a) >= 2 and len(returns_b) >= 2:
        corr = np.corrcoef(returns_a, returns_b)[0, 1]
        return float(corr) if not np.isnan(corr) else 0.0
    
    return 0.0


def build_correlation_matrix_from_trades(
    symbol_trades: Dict[str, List[Dict[str, Any]]],
    index: pd.DatetimeIndex
) -> pd.DataFrame:
    """Build correlation matrix from symbol trades.
    
    Args:
        symbol_trades: Dict of symbol -> trades
        index: Common date index
    
    Returns:
        Correlation matrix DataFrame
    """
    symbols = list(symbol_trades.keys())
    n = len(symbols)
    
    if n == 0:
        return pd.DataFrame()
    
    # Initialize correlation matrix
    corr_matrix = np.eye(n)
    
    # Calculate pairwise correlations
    for i in range(n):
        for j in range(i + 1, n):
            corr = calculate_symbol_correlation(
                symbol_trades[symbols[i]],
                symbol_trades[symbols[j]],
                index
            )
            corr_matrix[i, j] = corr
            corr_matrix[j, i] = corr
    
    # Create DataFrame
    df = pd.DataFrame(corr_matrix, index=symbols, columns=symbols)
    return df


def aggregate_trades_by_symbol(
    symbol_trades: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, Any]]:
    """Aggregate trade statistics by symbol.
    
    Args:
        symbol_trades: Dict of symbol -> list of trades
    
    Returns:
        Dict of symbol -> aggregated stats
    """
    aggregated = {}
    
    for symbol, trades in symbol_trades.items():
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        
        aggregated[symbol] = {
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0.0
        }
    
    return aggregated
