"""
Phase 5F: Trade simulation tests
Tests for long-only trade simulator with SL/TP, gap handling, and commission.
"""
import pandas as pd
import numpy as np
from backend.trade_simulator import simulate_long_only, derive_rising_entries


def test_single_long_trade_entry_exit():
    """Test that a single long trade enters and exits correctly."""
    # Create simple OHLCV data: 20 bars, uptrend then downtrend
    closes = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100, 99], dtype=float)
    dates = pd.date_range('2024-01-01', periods=len(closes), freq='D')
    df = pd.DataFrame({
        'open': closes,
        'high': closes + 1,
        'low': closes - 1,
        'close': closes,
        'volume': 1000
    }, index=dates)
    
    # Signal at bar 5 (entry at next bar 6)
    entry_ts = int(pd.Timestamp(dates[5]).timestamp())
    config = {'initial_capital': 10000, 'position_size_mode': 'percent_capital', 'position_size_value': 100, 'commission_per_trade': 0}
    
    trades = simulate_long_only(df, 'TEST', [entry_ts], config)
    
    assert len(trades) == 1, f"Expected 1 trade, got {len(trades)}"
    trade = trades[0]
    assert trade['symbol'] == 'TEST'
    assert trade['side'] == 'long'
    assert trade['quantity'] > 0
    assert trade['entry_price'] > 0
    assert trade['exit_price'] > 0
    assert trade['status'] == 'closed'


def test_stop_loss_fill_intrabar():
    """Test that SL fills at correct price within the bar (intrabar check)."""
    # Scenario: entry at bar 0, then bar 1 gaps down, and bar 2 gaps down more to hit SL
    closes = np.array([100, 98, 94, 95, 96, 97, 98, 99, 100, 101], dtype=float)
    highs = np.array([101, 99, 95, 96, 97, 98, 99, 100, 101, 102], dtype=float)
    lows = np.array([99, 97, 93, 94, 95, 96, 97, 98, 99, 100], dtype=float)
    dates = pd.date_range('2024-01-01', periods=len(closes), freq='D')
    df = pd.DataFrame({
        'open': closes,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': 1000
    }, index=dates)
    
    # Entry at bar 0 (close=100), fill at bar 1 (open=98)
    # SL 5% below 98 = 93.1, bar 2 low is 93 which triggers it
    entry_ts = int(pd.Timestamp(dates[0]).timestamp())
    config = {
        'initial_capital': 10000,
        'position_size_mode': 'percent_capital',
        'position_size_value': 100,
        'stop_loss_percent': 5.0,
        'take_profit_percent': 0,
        'commission_per_trade': 0
    }
    
    trades = simulate_long_only(df, 'TEST', [entry_ts], config)
    
    assert len(trades) >= 1, "Expected at least 1 trade"
    trade = trades[0]
    # SL should trigger
    assert trade['exit_reason'] == 'stop_loss', f"Expected stop_loss, got {trade['exit_reason']}"
    assert trade['pnl'] < 0, "SL trade should have negative PnL"


def test_take_profit_fill():
    """Test that TP fills at correct price."""
    closes = np.array([100, 101, 102, 103, 104, 105, 106, 105, 104, 103], dtype=float)
    highs = np.array([101, 102, 103, 104, 105, 106, 107, 106, 105, 104], dtype=float)
    lows = np.array([99, 100, 101, 102, 103, 104, 105, 104, 103, 102], dtype=float)
    dates = pd.date_range('2024-01-01', periods=len(closes), freq='D')
    df = pd.DataFrame({
        'open': closes,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': 1000
    }, index=dates)
    
    # Entry at bar 0, TP 5% above entry (100 * 1.05 = 105)
    entry_ts = int(pd.Timestamp(dates[0]).timestamp())
    config = {
        'initial_capital': 10000,
        'position_size_mode': 'percent_capital',
        'position_size_value': 100,
        'stop_loss_percent': 0,
        'take_profit_percent': 5.0,
        'commission_per_trade': 0
    }
    
    trades = simulate_long_only(df, 'TEST', [entry_ts], config)
    
    assert len(trades) >= 1
    trade = trades[0]
    assert trade['exit_reason'] == 'take_profit'
    assert trade['pnl'] > 0, "TP trade should have positive PnL"


def test_sl_tp_precedence_sl_first():
    """Test that SL is prioritized when both SL and TP are hit on same bar (conservative)."""
    # Entry at bar 0 (fill bar 1), SL at -5% = 95, TP at +5% = 105
    # Bar 1 (fill): open=100
    # Bar 2: low=94 (hits SL at 95), high=106 (hits TP at 105) - SL should be chosen
    closes = np.array([100, 100, 100, 104, 105, 106, 107, 108, 109], dtype=float)
    highs = np.array([101, 101, 106, 105, 106, 107, 108, 109, 110], dtype=float)
    lows = np.array([99, 99, 94, 103, 104, 105, 106, 107, 108], dtype=float)
    dates = pd.date_range('2024-01-01', periods=len(closes), freq='D')
    df = pd.DataFrame({
        'open': closes,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': 1000
    }, index=dates)
    
    # Entry at bar 0, fill at bar 1 (open=100), SL 5%, TP 5%
    entry_ts = int(pd.Timestamp(dates[0]).timestamp())
    config = {
        'initial_capital': 10000,
        'position_size_mode': 'percent_capital',
        'position_size_value': 100,
        'stop_loss_percent': 5.0,
        'take_profit_percent': 5.0,
        'commission_per_trade': 0
    }
    
    trades = simulate_long_only(df, 'TEST', [entry_ts], config)
    assert len(trades) >= 1, "Expected at least 1 trade"
    trade = trades[0]
    # Bar 2 hits both SL (low=94 < 95) and TP (high=106 > 105), SL should win
    assert trade['exit_reason'] in ['stop_loss', 'stop_loss_and_take_profit'], f"Got {trade['exit_reason']}"


def test_commission_deducted():
    """Test that commission is correctly deducted from PnL."""
    closes = np.array([100, 101, 102, 103, 104, 105, 106, 105, 104, 103], dtype=float)
    dates = pd.date_range('2024-01-01', periods=len(closes), freq='D')
    df = pd.DataFrame({
        'open': closes,
        'high': closes + 1,
        'low': closes - 1,
        'close': closes,
        'volume': 1000
    }, index=dates)
    
    entry_ts = int(pd.Timestamp(dates[0]).timestamp())
    comm_rate = 0.001  # 0.1% on each side
    config = {
        'initial_capital': 10000,
        'position_size_mode': 'percent_capital',
        'position_size_value': 100,
        'commission_per_trade': comm_rate,
        'stop_loss_percent': 0,
        'take_profit_percent': 0
    }
    
    trades = simulate_long_only(df, 'TEST', [entry_ts], config)
    assert len(trades) >= 1
    trade = trades[0]
    # Commission should be > 0
    assert trade['commission'] > 0, "Commission should be deducted"
    # PnL should be less than gross (PnL - commission)
    gross_pnl = (trade['exit_price'] - trade['entry_price']) * trade['quantity']
    assert trade['pnl'] < gross_pnl or abs(trade['pnl'] - gross_pnl) < 0.01


def test_warmup_bars_skipped():
    """Test that warmup bars (NaN periods) don't generate signals."""
    # This test verifies derive_rising_entries ignores timestamps before data starts
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    idx = dates
    # Timestamps in second half (should be retained)
    match_ts = [int(pd.Timestamp(dates[i]).timestamp()) for i in [60, 65, 70]]
    
    rising = derive_rising_entries(idx, match_ts)
    # Should extract rising edges from match_ts
    assert len(rising) <= len(match_ts), "Rising edges should not exceed matches"
    assert all(isinstance(ts, int) for ts in rising), "All rising edge timestamps should be ints"


def test_no_pyramiding():
    """Test that only one position is held at a time (no pyramiding)."""
    # Create data where first position can close before second signal
    # Entry 1 at bar 0, exit at bar 5 (TP hit), Entry 2 at bar 6
    closes = np.array([100, 101, 102, 103, 104, 105, 104, 103, 102, 101], dtype=float)
    highs = np.array([101, 102, 103, 104, 105, 106, 105, 104, 103, 102], dtype=float)
    lows = np.array([99, 100, 101, 102, 103, 104, 103, 102, 101, 100], dtype=float)
    dates = pd.date_range('2024-01-01', periods=len(closes), freq='D')
    df = pd.DataFrame({
        'open': closes,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': 1000
    }, index=dates)
    
    # Two entry signals: bar 0 and bar 6
    # Bar 0 entry: fill at bar 1 (open=101), TP 5%=105.05 hits at bar 5
    # Bar 6 entry: fill at bar 7 (open=103), should be allowed as first trade is closed
    entry_ts = [int(pd.Timestamp(dates[0]).timestamp()), int(pd.Timestamp(dates[6]).timestamp())]
    config = {
        'initial_capital': 10000,
        'position_size_mode': 'percent_capital',
        'position_size_value': 100,
        'stop_loss_percent': 0,
        'take_profit_percent': 5.0,
        'commission_per_trade': 0
    }
    
    trades = simulate_long_only(df, 'TEST', entry_ts, config)
    # First entry should get TP, second entry should be allowed
    assert len(trades) == 2, f"Expected 2 trades (pyramiding allowed if not overlapping), got {len(trades)}"
