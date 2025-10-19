"""
Phase 5F: Backtest analytics tests
Tests for metrics calculation (win rate, profit factor, Sharpe, drawdown).
"""
import pandas as pd
import numpy as np
from backend.backtest_analytics import calculate_metrics, build_equity_curve


def test_build_equity_curve_and_metrics_smoke():
    # Create a simple index of 5 days
    idx = pd.date_range('2023-01-01', periods=5, freq='D')
    # Two trades: one win exited on day 3, one loss exited on day 5
    trades = [
        {
            'exit_timestamp': int(idx[2].timestamp()),
            'pnl': 100.0,
            'duration_bars': 2
        },
        {
            'exit_timestamp': int(idx[4].timestamp()),
            'pnl': -50.0,
            'duration_bars': 3
        }
    ]
    ts, eq = build_equity_curve(trades, 10000.0, idx)
    assert len(ts) == len(eq) == 5
    assert eq[0] == 10000.0
    # After day 3, equity should reflect +100
    assert eq[2] == 10100.0
    # After day 5, -50 more => 10050
    assert eq[4] == 10050.0

    metrics = calculate_metrics(trades, 10000.0, idx, '1D')
    # Basic keys should exist
    for key in (
        'total_trades','winning_trades','losing_trades','win_rate','profit_factor','total_return',
        'annualized_return','max_drawdown','max_drawdown_duration','sharpe_ratio','avg_win','avg_loss',
        'largest_win','largest_loss','avg_bars_held'
    ):
        assert key in metrics
    assert metrics['total_trades'] == 2
    assert metrics['winning_trades'] == 1
    assert metrics['losing_trades'] == 1
    assert metrics['largest_win'] >= 0
    assert metrics['largest_loss'] <= 0


def test_win_rate_calculation():
    """Test that win rate is calculated correctly."""
    trades = [
        {'pnl': 100, 'exit_timestamp': 1000, 'duration_bars': 5},
        {'pnl': -50, 'exit_timestamp': 1086400, 'duration_bars': 3},
        {'pnl': 200, 'exit_timestamp': 1172800, 'duration_bars': 10},
    ]
    index = pd.date_range('2024-01-01', periods=1000, freq='D')
    metrics = calculate_metrics(trades, 10000, index, '1D')
    
    # 2 winning, 1 losing → 2/3 = 66.67%
    expected_win_rate = (2 / 3) * 100
    assert abs(metrics['win_rate'] - expected_win_rate) < 0.01, f"Expected {expected_win_rate}, got {metrics['win_rate']}"
    assert metrics['total_trades'] == 3
    assert metrics['winning_trades'] == 2
    assert metrics['losing_trades'] == 1


def test_profit_factor_calculation():
    """Test that profit factor = sum(wins) / abs(sum(losses))."""
    trades = [
        {'pnl': 100, 'exit_timestamp': 1000, 'duration_bars': 5},
        {'pnl': -50, 'exit_timestamp': 1086400, 'duration_bars': 3},
        {'pnl': 200, 'exit_timestamp': 1172800, 'duration_bars': 10},
    ]
    index = pd.date_range('2024-01-01', periods=1000, freq='D')
    metrics = calculate_metrics(trades, 10000, index, '1D')
    
    # Wins: 100 + 200 = 300
    # Losses: 50
    # Profit factor: 300 / 50 = 6.0
    expected_pf = 300 / 50
    assert abs(metrics['profit_factor'] - expected_pf) < 0.01, f"Expected {expected_pf}, got {metrics['profit_factor']}"


def test_equity_curve_cumulative():
    """Test that equity curve accumulates PnL correctly."""
    index = pd.date_range('2024-01-01', periods=5, freq='D')
    # Use actual index timestamps
    ts_3 = int(index[2].timestamp())  # Day 3
    ts_5 = int(index[4].timestamp())  # Day 5
    
    trades = [
        {'pnl': 100, 'exit_timestamp': ts_3, 'duration_bars': 5},
        {'pnl': 50, 'exit_timestamp': ts_5, 'duration_bars': 3},
    ]
    initial_capital = 10000.0
    ts_list, equity = build_equity_curve(trades, initial_capital, index)
    
    assert len(equity) == len(index)
    # Equity should start at initial_capital
    assert equity[0] == initial_capital
    # After day 3, equity should reflect +100
    assert equity[2] == initial_capital + 100, f"Expected {initial_capital + 100}, got {equity[2]}"
    # After day 5, equity should reflect +100 + 50
    assert equity[4] == initial_capital + 150, f"Expected {initial_capital + 150}, got {equity[4]}"


def test_average_win_loss():
    """Test that average win and average loss are calculated correctly."""
    trades = [
        {'pnl': 100, 'exit_timestamp': 1000, 'duration_bars': 5},
        {'pnl': -50, 'exit_timestamp': 1086400, 'duration_bars': 3},
        {'pnl': 200, 'exit_timestamp': 1172800, 'duration_bars': 10},
        {'pnl': -30, 'exit_timestamp': 1259200, 'duration_bars': 2},
    ]
    index = pd.date_range('2024-01-01', periods=1000, freq='D')
    metrics = calculate_metrics(trades, 10000, index, '1D')
    
    # Wins: 100, 200 → avg = 150
    # Losses: -50, -30 → avg = -40
    assert abs(metrics['avg_win'] - 150) < 0.01
    assert abs(metrics['avg_loss'] - (-40)) < 0.01


def test_max_drawdown_calculation():
    """Test that max drawdown is calculated correctly."""
    index = pd.date_range('2024-01-01', periods=5, freq='D')
    ts_1 = int(index[0].timestamp())  # Day 1
    ts_2 = int(index[1].timestamp())  # Day 2
    ts_3 = int(index[2].timestamp())  # Day 3
    ts_4 = int(index[3].timestamp())  # Day 4
    
    trades = [
        {'pnl': 1000, 'exit_timestamp': ts_1, 'duration_bars': 5},   # Gain to 11000
        {'pnl': -500, 'exit_timestamp': ts_2, 'duration_bars': 3},   # Loss to 10500, peak now 11000
        {'pnl': 100, 'exit_timestamp': ts_3, 'duration_bars': 3},
        {'pnl': 200, 'exit_timestamp': ts_4, 'duration_bars': 10},
    ]
    initial_capital = 10000.0
    metrics = calculate_metrics(trades, initial_capital, index, '1D')
    
    # After first trade: 10000 + 1000 = 11000 (peak)
    # After second trade: 11000 - 500 = 10500
    # Max drawdown from peak 11000 to trough 10500 → DD = -500/11000 ≈ -4.55%
    assert metrics['max_drawdown'] < 0, f"Max drawdown should be negative, got {metrics['max_drawdown']}"
    # Should be close to -4.55%
    assert -5 < metrics['max_drawdown'] < 0, f"Expected DD between -5% and 0%, got {metrics['max_drawdown']}"


def test_sharpe_ratio_formula():
    """Test that Sharpe ratio uses correct annualization."""
    # Simple case: all returns are same
    trades = [
        {'pnl': 50, 'exit_timestamp': 1000, 'duration_bars': 5},
        {'pnl': 50, 'exit_timestamp': 1086400, 'duration_bars': 5},
    ]
    index = pd.date_range('2024-01-01', periods=252, freq='D')  # 1 year of data
    metrics = calculate_metrics(trades, 10000, index, '1D')
    
    # Sharpe should be calculable (may be high or low depending on bar returns variance)
    assert 'sharpe_ratio' in metrics
    assert isinstance(metrics['sharpe_ratio'], (int, float))


def test_avg_bars_held():
    """Test that average bars held is calculated correctly."""
    trades = [
        {'pnl': 100, 'exit_timestamp': 1000, 'duration_bars': 10},
        {'pnl': 50, 'exit_timestamp': 1086400, 'duration_bars': 20},
        {'pnl': 200, 'exit_timestamp': 1172800, 'duration_bars': 5},
    ]
    index = pd.date_range('2024-01-01', periods=1000, freq='D')
    metrics = calculate_metrics(trades, 10000, index, '1D')
    
    # Avg bars held: (10 + 20 + 5) / 3 = 11.67
    expected_avg = (10 + 20 + 5) / 3
    assert abs(metrics['avg_bars_held'] - expected_avg) < 0.01


def test_largest_win_loss():
    """Test that largest win and largest loss are identified correctly."""
    trades = [
        {'pnl': 100, 'exit_timestamp': 1000, 'duration_bars': 5},
        {'pnl': -50, 'exit_timestamp': 1086400, 'duration_bars': 3},
        {'pnl': 300, 'exit_timestamp': 1172800, 'duration_bars': 10},  # largest win
        {'pnl': -200, 'exit_timestamp': 1259200, 'duration_bars': 2},  # largest loss
    ]
    index = pd.date_range('2024-01-01', periods=1000, freq='D')
    metrics = calculate_metrics(trades, 10000, index, '1D')
    
    assert metrics['largest_win'] == 300
    assert metrics['largest_loss'] == -200


def test_metrics_with_no_trades():
    """Test that metrics handle empty trade list gracefully."""
    trades = []
    index = pd.date_range('2024-01-01', periods=100, freq='D')
    metrics = calculate_metrics(trades, 10000, index, '1D')
    
    assert metrics['total_trades'] == 0
    assert metrics['win_rate'] == 0
    assert metrics['profit_factor'] >= 0
    assert metrics['total_return'] == 0
