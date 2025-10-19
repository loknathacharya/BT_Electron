import pandas as pd
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
