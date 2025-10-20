"""
Phase 8 Tests: Portfolio Management

Tests for multi-symbol backtests, portfolio allocation strategies,
correlation analysis, and diversification metrics.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# Test Portfolio Weight Calculations
def test_equal_weight_allocation():
    """Test equal weight allocation across symbols"""
    from backend.portfolio_manager import calculate_portfolio_weights  # type: ignore
    
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    weights = calculate_portfolio_weights('equal', symbols)
    
    assert len(weights) == 3
    assert all(abs(weights[s] - 1/3) < 1e-6 for s in symbols)
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_custom_weight_allocation():
    """Test custom weight allocation"""
    from backend.portfolio_manager import calculate_portfolio_weights  # type: ignore
    
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    custom_weights = {
        'AAPL': 0.5,
        'MSFT': 0.3,
        'GOOGL': 0.2
    }
    
    weights = calculate_portfolio_weights('custom', symbols, custom_weights)
    
    assert weights['AAPL'] == 0.5
    assert weights['MSFT'] == 0.3
    assert weights['GOOGL'] == 0.2
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_missing_custom_weights_defaults_to_equal():
    """Test that missing custom weights defaults to equal allocation"""
    from backend.portfolio_manager import calculate_portfolio_weights  # type: ignore
    
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    custom_weights = {'AAPL': 0.5}  # Missing MSFT and GOOGL
    
    weights = calculate_portfolio_weights('custom', symbols, custom_weights)
    
    # Should fall back to equal weights when custom weights incomplete
    assert all(abs(weights[s] - 1/3) < 1e-6 for s in symbols)


# Test Correlation Matrix Calculation
def test_correlation_matrix_from_trades():
    """Test correlation matrix calculation from trade returns"""
    from backend.portfolio_manager import build_correlation_matrix_from_trades  # type: ignore
    
    # Create sample trades with correlated returns
    index = pd.date_range('2023-01-01', periods=10, freq='D')
    
    # AAPL and MSFT highly correlated (both go up)
    aapl_trades = [
        {'entry_date': index[i].strftime('%Y-%m-%d'), 'exit_date': index[i+1].strftime('%Y-%m-%d'),
         'entry_price': 100, 'exit_price': 100 + i, 'shares': 10, 'direction': 'long'}
        for i in range(5)
    ]
    
    msft_trades = [
        {'entry_date': index[i].strftime('%Y-%m-%d'), 'exit_date': index[i+1].strftime('%Y-%m-%d'),
         'entry_price': 200, 'exit_price': 200 + i*2, 'shares': 5, 'direction': 'long'}
        for i in range(5)
    ]
    
    # GOOGL negatively correlated (goes down)
    googl_trades = [
        {'entry_date': index[i].strftime('%Y-%m-%d'), 'exit_date': index[i+1].strftime('%Y-%m-%d'),
         'entry_price': 150, 'exit_price': 150 - i, 'shares': 8, 'direction': 'long'}
        for i in range(5)
    ]
    
    symbol_trades = {
        'AAPL': aapl_trades,
        'MSFT': msft_trades,
        'GOOGL': googl_trades
    }
    
    corr_matrix = build_correlation_matrix_from_trades(symbol_trades, index)
    
    # Check diagonal is 1.0 (symbol correlated with itself)
    assert abs(corr_matrix.loc['AAPL', 'AAPL'] - 1.0) < 1e-6
    assert abs(corr_matrix.loc['MSFT', 'MSFT'] - 1.0) < 1e-6
    
    # AAPL and MSFT should be positively correlated
    assert corr_matrix.loc['AAPL', 'MSFT'] > 0.5
    
    # GOOGL should be negatively correlated with AAPL
    assert corr_matrix.loc['AAPL', 'GOOGL'] < -0.5


def test_correlation_matrix_single_symbol():
    """Test correlation matrix with single symbol"""
    from backend.portfolio_manager import build_correlation_matrix_from_trades  # type: ignore
    
    index = pd.date_range('2023-01-01', periods=5, freq='D')
    trades = [
        {'entry_date': index[i].strftime('%Y-%m-%d'), 'exit_date': index[i+1].strftime('%Y-%m-%d'),
         'entry_price': 100, 'exit_price': 105, 'shares': 10, 'direction': 'long'}
        for i in range(3)
    ]
    
    symbol_trades = {'AAPL': trades}
    corr_matrix = build_correlation_matrix_from_trades(symbol_trades, index)
    
    assert len(corr_matrix) == 1
    assert corr_matrix.loc['AAPL', 'AAPL'] == 1.0


# Test Portfolio Equity Curve Construction
def test_build_portfolio_equity_curve():
    """Test building combined portfolio equity curve"""
    from backend.portfolio_manager import build_portfolio_equity_curve  # type: ignore
    
    index = pd.date_range('2023-01-01', periods=10, freq='D')
    
    # Symbol 1: Gains 10% over period
    trades_1 = [
        {'entry_date': index[0].strftime('%Y-%m-%d'), 'exit_date': index[5].strftime('%Y-%m-%d'),
         'entry_price': 100, 'exit_price': 110, 'shares': 10, 'direction': 'long'}
    ]
    
    # Symbol 2: Loses 5% over period
    trades_2 = [
        {'entry_date': index[0].strftime('%Y-%m-%d'), 'exit_date': index[5].strftime('%Y-%m-%d'),
         'entry_price': 200, 'exit_price': 190, 'shares': 5, 'direction': 'long'}
    ]
    
    symbol_trades = {'SYM1': trades_1, 'SYM2': trades_2}
    weights = {'SYM1': 0.5, 'SYM2': 0.5}  # Equal weight
    initial_capital = 10000
    
    timestamps, portfolio_equity, symbol_equities = build_portfolio_equity_curve(
        symbol_trades, weights, initial_capital, index
    )
    
    assert len(timestamps) == len(index)
    assert len(portfolio_equity) == len(index)
    assert 'SYM1' in symbol_equities
    assert 'SYM2' in symbol_equities
    
    # Portfolio should be between the two symbols
    assert portfolio_equity[0] == initial_capital
    # SYM1 allocated 5000, trade gains (110-100)*10 = 100
    # SYM2 allocated 5000, trade loses (190-200)*5 = -50
    # Net change: +50, so final = 10050
    final_equity = portfolio_equity[-1]
    assert 10040 < final_equity < 10060  # Allow for some calculation variance


def test_portfolio_equity_with_no_trades():
    """Test portfolio equity curve when no trades occur"""
    from backend.portfolio_manager import build_portfolio_equity_curve  # type: ignore
    
    index = pd.date_range('2023-01-01', periods=5, freq='D')
    symbol_trades = {'AAPL': [], 'MSFT': []}  # No trades
    weights = {'AAPL': 0.5, 'MSFT': 0.5}
    initial_capital = 10000
    
    timestamps, portfolio_equity, symbol_equities = build_portfolio_equity_curve(
        symbol_trades, weights, initial_capital, index
    )
    
    # Should return flat equity curve at initial capital
    assert all(eq == initial_capital for eq in portfolio_equity)
    assert all(eq == initial_capital * 0.5 for eq in symbol_equities['AAPL'])


# Test Portfolio Metrics Calculation
def test_calculate_portfolio_metrics():
    """Test calculation of portfolio-level metrics"""
    from backend.portfolio_manager import calculate_portfolio_metrics  # type: ignore
    
    index = pd.date_range('2023-01-01', periods=252, freq='D')  # 1 year
    
    # Create equity curve with some gains
    portfolio_equity = [10000 * (1 + 0.001 * i) for i in range(252)]  # ~25% annual return
    
    # Create some sample trades
    trades_1 = [
        {'entry_date': index[i*10].strftime('%Y-%m-%d'), 'exit_date': index[i*10+5].strftime('%Y-%m-%d'),
         'entry_price': 100, 'exit_price': 105, 'shares': 10, 'direction': 'long'}
        for i in range(10)
    ]
    
    trades_2 = [
        {'entry_date': index[i*10+1].strftime('%Y-%m-%d'), 'exit_date': index[i*10+6].strftime('%Y-%m-%d'),
         'entry_price': 200, 'exit_price': 202, 'shares': 5, 'direction': 'long'}
        for i in range(10)
    ]
    
    symbol_trades = {'AAPL': trades_1, 'MSFT': trades_2}
    initial_capital = 10000
    
    metrics = calculate_portfolio_metrics(portfolio_equity, symbol_trades, initial_capital, index, '1D')
    
    assert 'totalReturn' in metrics
    assert 'annualizedReturn' in metrics
    assert 'sharpeRatio' in metrics
    assert 'maxDrawdown' in metrics
    assert 'volatility' in metrics
    assert 'totalTrades' in metrics
    
    # Check reasonable values
    assert metrics['totalReturn'] > 0  # Made gains
    assert 0 < metrics['annualizedReturn'] < 1  # Between 0% and 100%
    assert metrics['totalTrades'] == 20  # 10 + 10


def test_portfolio_metrics_with_drawdown():
    """Test portfolio metrics calculation with drawdown scenario"""
    from backend.portfolio_manager import calculate_portfolio_metrics  # type: ignore
    
    index = pd.date_range('2023-01-01', periods=10, freq='D')
    
    # Equity curve: gain then lose (creates drawdown)
    portfolio_equity = [10000, 11000, 12000, 11000, 10500, 10000, 10200, 10500, 11000, 11500]
    
    symbol_trades = {'AAPL': []}
    initial_capital = 10000
    
    metrics = calculate_portfolio_metrics(portfolio_equity, symbol_trades, initial_capital, index, '1D')
    
    # Should detect drawdown from peak (12000) to trough (10000)
    assert metrics['maxDrawdown'] < 0  # Drawdown is negative
    expected_dd = (10000 - 12000) / 12000
    assert abs(metrics['maxDrawdown'] - expected_dd) < 0.01


# Test Diversification Ratio
def test_calculate_diversification_ratio():
    """Test diversification ratio calculation"""
    from backend.portfolio_manager import calculate_diversification_ratio  # type: ignore
    
    # Create uncorrelated returns for perfect diversification
    np.random.seed(42)
    returns_data = {
        'AAPL': np.random.randn(100) * 0.02,
        'MSFT': np.random.randn(100) * 0.02,
        'GOOGL': np.random.randn(100) * 0.02
    }
    returns_df = pd.DataFrame(returns_data)
    
    weights = {'AAPL': 1/3, 'MSFT': 1/3, 'GOOGL': 1/3}
    
    div_ratio = calculate_diversification_ratio(weights, returns_df)
    
    # For uncorrelated assets, diversification ratio should be > 1
    # Perfect diversification would be sqrt(N) for equal weights
    assert div_ratio > 1.0
    # With 3 uncorrelated assets, should be close to sqrt(3) = 1.73
    assert 1.2 < div_ratio < 2.0


def test_diversification_ratio_single_asset():
    """Test diversification ratio with single asset (should be 1.0)"""
    from backend.portfolio_manager import calculate_diversification_ratio  # type: ignore
    
    returns_data = {'AAPL': np.random.randn(100) * 0.02}
    returns_df = pd.DataFrame(returns_data)
    
    weights = {'AAPL': 1.0}
    
    div_ratio = calculate_diversification_ratio(weights, returns_df)
    
    # Single asset has no diversification benefit
    assert abs(div_ratio - 1.0) < 0.01


def test_diversification_ratio_highly_correlated():
    """Test diversification ratio with highly correlated assets"""
    from backend.portfolio_manager import calculate_diversification_ratio  # type: ignore
    
    # Create highly correlated returns (same random series with noise)
    np.random.seed(42)
    base_returns = np.random.randn(100) * 0.02
    
    returns_data = {
        'AAPL': base_returns + np.random.randn(100) * 0.001,
        'MSFT': base_returns + np.random.randn(100) * 0.001,
        'GOOGL': base_returns + np.random.randn(100) * 0.001
    }
    returns_df = pd.DataFrame(returns_data)
    
    weights = {'AAPL': 1/3, 'MSFT': 1/3, 'GOOGL': 1/3}
    
    div_ratio = calculate_diversification_ratio(weights, returns_df)
    
    # Highly correlated assets provide little diversification
    assert 1.0 < div_ratio < 1.3


# Test Rebalancing Logic
def test_rebalance_portfolio():
    """Test portfolio rebalancing calculation"""
    from backend.portfolio_manager import rebalance_portfolio  # type: ignore
    
    # Current allocation after drift
    current_values = {'AAPL': 6000, 'MSFT': 3000, 'GOOGL': 1000}  # Total 10000
    
    # Target weights
    target_weights = {'AAPL': 0.5, 'MSFT': 0.3, 'GOOGL': 0.2}
    
    # Current prices
    current_prices = {'AAPL': 150, 'MSFT': 300, 'GOOGL': 100}
    
    rebalance_trades = rebalance_portfolio(current_values, target_weights, current_prices)
    
    # AAPL should sell (6000 -> 5000)
    assert 'AAPL' in rebalance_trades
    assert rebalance_trades['AAPL']['action'] == 'sell'
    assert rebalance_trades['AAPL']['shares'] > 0
    
    # MSFT should stay the same (3000 target)
    # GOOGL should buy (1000 -> 2000)
    assert 'GOOGL' in rebalance_trades
    assert rebalance_trades['GOOGL']['action'] == 'buy'


def test_rebalance_no_action_needed():
    """Test rebalancing when portfolio is already balanced"""
    from backend.portfolio_manager import rebalance_portfolio  # type: ignore
    
    # Already at target weights
    current_values = {'AAPL': 5000, 'MSFT': 3000, 'GOOGL': 2000}
    target_weights = {'AAPL': 0.5, 'MSFT': 0.3, 'GOOGL': 0.2}
    current_prices = {'AAPL': 150, 'MSFT': 300, 'GOOGL': 100}
    
    rebalance_trades = rebalance_portfolio(current_values, target_weights, current_prices, rebalance_threshold=0.01)
    
    # No rebalancing needed
    assert len(rebalance_trades) == 0


# Test Aggregate Trades by Symbol
def test_aggregate_trades_by_symbol():
    """Test aggregating trades grouped by symbol"""
    from backend.portfolio_manager import aggregate_trades_by_symbol  # type: ignore
    
    index = pd.date_range('2023-01-01', periods=5, freq='D')
    
    trades_1 = [
        {'entry_date': index[0].strftime('%Y-%m-%d'), 'exit_date': index[1].strftime('%Y-%m-%d'),
         'entry_price': 100, 'exit_price': 105, 'shares': 10, 'direction': 'long', 'pnl': 50}
    ]
    
    trades_2 = [
        {'entry_date': index[0].strftime('%Y-%m-%d'), 'exit_date': index[1].strftime('%Y-%m-%d'),
         'entry_price': 200, 'exit_price': 195, 'shares': 5, 'direction': 'long', 'pnl': -25}
    ]
    
    symbol_trades = {'AAPL': trades_1, 'MSFT': trades_2}
    
    aggregated = aggregate_trades_by_symbol(symbol_trades)
    
    assert 'AAPL' in aggregated
    assert 'MSFT' in aggregated
    assert aggregated['AAPL']['total_trades'] == 1
    assert aggregated['AAPL']['total_pnl'] == 50
    assert aggregated['MSFT']['total_pnl'] == -25


# Test Integration: Full Portfolio Backtest Flow
def test_portfolio_backtest_integration():
    """Integration test for full portfolio backtest workflow"""
    from backend.portfolio_manager import (  # type: ignore
        calculate_portfolio_weights,
        build_portfolio_equity_curve,
        calculate_portfolio_metrics,
        build_correlation_matrix_from_trades
    )
    
    # Setup
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    index = pd.date_range('2023-01-01', periods=50, freq='D')
    initial_capital = 10000
    
    # Create sample trades for each symbol
    symbol_trades = {}
    for i, symbol in enumerate(symbols):
        trades = [
            {'entry_date': index[j*5].strftime('%Y-%m-%d'), 'exit_date': index[j*5+3].strftime('%Y-%m-%d'),
             'entry_price': 100 + i*50, 'exit_price': 105 + i*50, 'shares': 10, 'direction': 'long'}
            for j in range(5)
        ]
        symbol_trades[symbol] = trades
    
    # Calculate weights
    weights = calculate_portfolio_weights('equal', symbols)
    
    # Build equity curve
    timestamps, portfolio_equity, symbol_equities = build_portfolio_equity_curve(
        symbol_trades, weights, initial_capital, index
    )
    
    # Calculate metrics
    metrics = calculate_portfolio_metrics(portfolio_equity, symbol_trades, initial_capital, index, '1D')
    
    # Build correlation matrix
    corr_matrix = build_correlation_matrix_from_trades(symbol_trades, index)
    
    # Assertions
    assert len(timestamps) > 0
    assert len(portfolio_equity) == len(timestamps)
    assert len(symbol_equities) == 3
    assert 'totalReturn' in metrics
    assert not corr_matrix.empty
    assert len(corr_matrix) == 3
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_portfolio_backtest_with_unequal_weights():
    """Integration test with custom unequal weights"""
    from backend.portfolio_manager import (  # type: ignore
        calculate_portfolio_weights,
        build_portfolio_equity_curve
    )
    
    symbols = ['AAPL', 'MSFT']
    index = pd.date_range('2023-01-01', periods=10, freq='D')
    
    # AAPL gains 20%, MSFT gains 10%
    trades_aapl = [
        {'entry_date': index[0].strftime('%Y-%m-%d'), 'exit_date': index[5].strftime('%Y-%m-%d'),
         'entry_price': 100, 'exit_price': 120, 'shares': 10, 'direction': 'long'}
    ]
    
    trades_msft = [
        {'entry_date': index[0].strftime('%Y-%m-%d'), 'exit_date': index[5].strftime('%Y-%m-%d'),
         'entry_price': 200, 'exit_price': 220, 'shares': 5, 'direction': 'long'}
    ]
    
    symbol_trades = {'AAPL': trades_aapl, 'MSFT': trades_msft}
    
    # 70% AAPL, 30% MSFT
    weights = calculate_portfolio_weights('custom', symbols, {'AAPL': 0.7, 'MSFT': 0.3})
    initial_capital = 10000
    
    timestamps, portfolio_equity, symbol_equities = build_portfolio_equity_curve(
        symbol_trades, weights, initial_capital, index
    )
    
    # Verify allocation
    # AAPL gets 7000, trade gains (120-100)*10 = 200
    # MSFT gets 3000, trade gains (220-200)*5 = 100
    # Total gain = 300, final = 10300
    final_equity = portfolio_equity[-1]
    assert 10250 < final_equity < 10350


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
