import pandas as pd
from backend.trade_simulator import simulate_long_only


def make_df(prices):
    # prices: list of dicts with open, high, low, close
    ts = pd.date_range('2023-01-01', periods=len(prices), freq='D')
    df = pd.DataFrame(prices)
    df['timestamp'] = ts.view('int64') // 10**9
    df.index = ts
    return df[['open', 'high', 'low', 'close']]


def test_simulate_long_only_take_profit():
    # Construct a simple series where TP is hit on the second bar after entry
    df = make_df([
        {'open': 100, 'high': 102, 'low': 99, 'close': 101},  # signal bar
        {'open': 101, 'high': 111.2, 'low': 100, 'close': 110},  # fill at 101, TP 10% -> 111.1, hit on this bar
        {'open': 112, 'high': 115, 'low': 110, 'close': 114},
    ])
    # Entry timestamp is the first bar; fill occurs at next bar open (bar 1)
    entry_ts = int(df.index[0].timestamp())
    trades = simulate_long_only(
        df,
        'TEST',
        [entry_ts],
        {
            'initial_capital': 10000,
            'position_size_mode': 'percent_capital',
            'position_size_value': 100,
            'take_profit_percent': 10,  # 10%
            'stop_loss_percent': 0,
            'commission_per_trade': 0.0,
        }
    )
    assert len(trades) == 1
    tr = trades[0]
    assert tr['entry_price'] == 101
    # TP at 101 * 1.10 = 111.1 should exit on bar 1 at price 111.1
    expected_tp = 101 * 1.10
    assert abs(tr['exit_price'] - expected_tp) < 1e-6, f"Expected exit_price ~{expected_tp}, got {tr['exit_price']}"
    assert tr['exit_reason'] in ('take_profit', 'stop_loss_and_take_profit')


def test_simulate_long_only_stop_loss_and_commission():
    # Construct bars where SL is triggered on the first bar after entry; include commission
    df = make_df([
        {'open': 200, 'high': 205, 'low': 198, 'close': 204},  # signal
        {'open': 204, 'high': 205, 'low': 180, 'close': 190},   # fill at 204, SL 5% -> 193.8, hit
        {'open': 192, 'high': 195, 'low': 185, 'close': 190},
    ])
    entry_ts = int(df.index[0].timestamp())
    trades = simulate_long_only(
        df,
        'TEST',
        [entry_ts],
        {
            'initial_capital': 10000,
            'position_size_mode': 'percent_capital',
            'position_size_value': 100,
            'take_profit_percent': 0,
            'stop_loss_percent': 5,   # 5%
            'commission_per_trade': 0.001,  # 0.1%
        }
    )
    assert len(trades) == 1
    tr = trades[0]
    assert tr['entry_price'] == 204
    # SL at 193.8 should execute
    assert abs(tr['exit_price'] - 193.8) < 1e-8
    # Commission should be charged on entry and exit (percent of notional)
    notional_entry = tr['entry_price'] * tr['quantity']
    notional_exit = tr['exit_price'] * tr['quantity']
    expected_comm = 0.001 * notional_entry + 0.001 * notional_exit
    assert abs(tr['commission'] - expected_comm) < 1e-6
