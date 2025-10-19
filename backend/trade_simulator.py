from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


@dataclass
class Trade:
    trade_id: str
    symbol: str
    entry_timestamp: int
    entry_price: float
    exit_timestamp: int
    exit_price: float
    quantity: float
    side: str
    pnl: float
    pnl_percent: float
    commission: float
    status: str
    exit_reason: str
    duration_bars: int


def derive_rising_entries(index: pd.DatetimeIndex, match_timestamps: List[int]) -> List[int]:
    """Given a series index and a list of match timestamps (epoch seconds) that may include
    consecutive True bars, return only rising-edge entries (True following a False).

    Returns a list of epoch seconds corresponding to rising edges present in the index.
    """
    if index.empty or not match_timestamps:
        return []
    # Build a boolean mask aligned to the index
    idx_seconds = (index.view('int64') // 10**9).astype(np.int64)
    ts_set = set(int(ts) for ts in match_timestamps if isinstance(ts, (int, float)))
    mask = pd.Series([int(ts) in ts_set for ts in idx_seconds.tolist()], index=index)
    rising = mask & (~mask.shift(1).fillna(False))
    # rising index values are pandas Timestamps already; convert to epoch seconds reliably
    rising_ts = [int(pd.Timestamp(ts).value // 10**9) for ts, v in rising.items() if bool(v)]
    return rising_ts


def simulate_long_only(
    df: pd.DataFrame,
    symbol: str,
    entry_timestamps: List[int],
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Simulate long-only trades using next-bar-open fills and SL/TP exits.

    Assumptions:
    - Single position at a time (no pyramiding)
    - Entry on signal bar i → fill at bar i+1 open
    - SL/TP are checked intrabar starting from the fill bar
    - If both SL and TP touched on the same bar, prefer SL (conservative)
    - Commission is percent of notional per side (applied on both entry and exit)
    - Position sizing: percent of current capital; defaults to 100% if not provided
    """
    if df.empty or not entry_timestamps:
        return []

    cfg = config or {}
    init_capital = float(cfg.get('initial_capital', 10000.0))
    comm_rate = float(cfg.get('commission_per_trade', 0.0))  # e.g., 0.001 = 0.1%
    pos_mode = str(cfg.get('position_size_mode', 'percent_capital')).lower()
    pos_val = float(cfg.get('position_size_value', 100.0))  # percent
    sl_pct = float(cfg.get('stop_loss_percent', 0.0)) / 100.0
    tp_pct = float(cfg.get('take_profit_percent', 0.0)) / 100.0

    index = df.index
    # Map epoch seconds to index position for quick lookups
    idx_seconds = (index.view('int64') // 10**9).astype(np.int64)
    sec_to_pos = {int(s): i for i, s in enumerate(idx_seconds.tolist())}

    capital = init_capital
    in_position = False
    entry_pos = -1
    entry_price = 0.0
    quantity = 0.0
    trades: List[Dict[str, Any]] = []

    # Iterate over signals sorted by time; if already in a position, ignore until exit
    for ts in sorted(set(int(t) for t in entry_timestamps)):
        if ts not in sec_to_pos:
            continue
        sig_pos = sec_to_pos[ts]
        # Compute fill position: next bar
        fill_pos = sig_pos + 1
        if fill_pos >= len(index):
            # No next bar to fill
            continue
        fill_open = float(df.iloc[fill_pos]['open']) if 'open' in df.columns else float(df.iloc[fill_pos]['close'])

        if in_position:
            # Skip additional entries until position is closed
            continue

        # Position sizing
        if pos_mode == 'percent_capital':
            alloc = max(0.0, capital * (pos_val / 100.0))
        else:
            alloc = max(0.0, capital)  # default
        if fill_open <= 0:
            continue
        qty = np.floor(alloc / fill_open)
        if qty <= 0:
            continue

        # Enter position
        in_position = True
        entry_pos = fill_pos
        entry_price = fill_open
        quantity = float(qty)

        stop_price = entry_price * (1.0 - sl_pct) if sl_pct > 0 else None
        take_price = entry_price * (1.0 + tp_pct) if tp_pct > 0 else None

        # Walk forward to find exit
        exit_pos = -1
        exit_price = float(df.iloc[-1]['close'])  # default to last close if never hit SL/TP
        exit_reason = 'end_of_series'
        for j in range(entry_pos, len(index)):
            bar_open = float(df.iloc[j]['open']) if 'open' in df.columns else float(df.iloc[j]['close'])
            bar_high = float(df.iloc[j]['high']) if 'high' in df.columns else bar_open
            bar_low = float(df.iloc[j]['low']) if 'low' in df.columns else bar_open

            hit_sl = False
            hit_tp = False
            if stop_price is not None:
                hit_sl = bar_low <= stop_price
            if take_price is not None:
                hit_tp = bar_high >= take_price

            if hit_sl and hit_tp:
                # Conservative: assume SL first
                exit_pos = j
                exit_price = stop_price if stop_price is not None else bar_open
                exit_reason = 'stop_loss_and_take_profit'  # logged as SL precedence
                break
            elif hit_sl:
                exit_pos = j
                exit_price = stop_price if stop_price is not None else bar_open
                exit_reason = 'stop_loss'
                break
            elif hit_tp:
                exit_pos = j
                exit_price = take_price if take_price is not None else bar_open
                exit_reason = 'take_profit'
                break

        if exit_pos == -1:
            exit_pos = len(index) - 1

        # Compute PnL and commission
        notional_entry = entry_price * quantity
        notional_exit = exit_price * quantity
        commission = comm_rate * notional_entry + comm_rate * notional_exit if comm_rate > 0 else 0.0
        pnl_gross = (exit_price - entry_price) * quantity
        pnl_net = pnl_gross - commission
        pnl_pct = (pnl_net / notional_entry) * 100.0 if notional_entry > 0 else 0.0

        # Update capital for next trade
        capital += pnl_net

        trade = Trade(
            trade_id=f"{symbol}_{int(pd.Timestamp(index[entry_pos]).timestamp())}",
            symbol=symbol,
            entry_timestamp=int(pd.Timestamp(index[entry_pos]).timestamp()),
            entry_price=float(entry_price),
            exit_timestamp=int(pd.Timestamp(index[exit_pos]).timestamp()),
            exit_price=float(exit_price),
            quantity=float(quantity),
            side='long',
            pnl=float(round(pnl_net, 6)),
            pnl_percent=float(round(pnl_pct, 6)),
            commission=float(round(commission, 6)),
            status='closed',
            exit_reason=exit_reason,
            duration_bars=int(exit_pos - entry_pos + 1)
        ).__dict__

        trades.append(trade)

        # Reset position state
        in_position = False
        entry_pos = -1
        entry_price = 0.0
        quantity = 0.0

    return trades
