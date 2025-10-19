from __future__ import annotations

from typing import List, Dict, Any, Tuple
import math
import pandas as pd


def build_equity_curve(trades: List[Dict[str, Any]], initial_capital: float, index: pd.DatetimeIndex) -> Tuple[list[int], list[float]]:
    """Build a simple equity curve over the provided index.

    Approach: step-wise equity that changes only on exit bars (closed trades). For days without exits,
    equity remains unchanged. This is a conservative Phase 5C implementation that avoids MTM for open trades.
    """
    if initial_capital is None or math.isnan(initial_capital):
        initial_capital = 0.0
    if index is None or len(index) == 0:
        return ([], [])

    # Map exit_timestamp to cumulative PnL at that timestamp (sum if multiple trades exit on same bar)
    pnl_by_ts: Dict[int, float] = {}
    for tr in trades or []:
        ts_exit = int(tr.get('exit_timestamp', 0) or 0)
        pnl = float(tr.get('pnl', 0.0) or 0.0)
        pnl_by_ts[ts_exit] = pnl_by_ts.get(ts_exit, 0.0) + pnl

    equity = []
    current = float(initial_capital)
    # Convert index to epoch seconds
    idx_seconds = (index.view('int64') // 10**9).astype(int).tolist()
    for ts in idx_seconds:
        delta = pnl_by_ts.get(int(ts), 0.0)
        current += float(delta)
        equity.append(current)

    return (idx_seconds, equity)


def _safe_ratio(num: float, den: float) -> float:
    den_safe = den if abs(den) > 1e-12 else (1e-12 if den >= 0 else -1e-12)
    return num / den_safe


def calculate_metrics(trades: List[Dict[str, Any]], initial_capital: float, index: pd.DatetimeIndex, timeframe: str = '1D') -> Dict[str, Any]:
    """Compute core metrics from trade list and equity curve.

    Returns a dict with the fields outlined in the plan: totals, win rate, profit factor, returns, drawdown, Sharpe, etc.
    """
    trades = trades or []
    n = len(trades)
    wins = [t for t in trades if float(t.get('pnl', 0.0)) > 0]
    losses = [t for t in trades if float(t.get('pnl', 0.0)) < 0]
    win_sum = sum(float(t.get('pnl', 0.0)) for t in wins)
    loss_sum = sum(float(t.get('pnl', 0.0)) for t in losses)
    winning_trades = len(wins)
    losing_trades = len(losses)
    win_rate = (winning_trades / n) * 100.0 if n > 0 else 0.0
    profit_factor = _safe_ratio(win_sum, abs(loss_sum)) if losing_trades > 0 else (_safe_ratio(win_sum, 1.0))

    # Equity curve
    ts_list, equity = build_equity_curve(trades, initial_capital, index)
    final_equity = equity[-1] if equity else float(initial_capital)
    total_return_pct = _safe_ratio((final_equity - initial_capital), initial_capital) * 100.0 if initial_capital else 0.0

    # Annualization factors (rough)
    tf = (timeframe or '1D').upper()
    periods_per_year = 252 if tf == '1D' else (24*252 if tf == '1H' else (6.5*60/15*252 if tf == '15M' else (6.5*60/5*252)))
    periods_per_year = float(periods_per_year) if periods_per_year else 252.0

    # Daily (or bar) returns from equity curve
    returns = []
    for i in range(1, len(equity)):
        prev = equity[i-1]
        curr = equity[i]
        r = _safe_ratio((curr - prev), prev) if prev else 0.0
        returns.append(r)

    # Annualized return using geometric approximation if we have multiple bars
    if len(equity) > 1 and initial_capital:
        per_period = (final_equity / initial_capital) ** (periods_per_year / max(1.0, float(len(equity)))) - 1.0
        annualized_return_pct = per_period * 100.0
    else:
        annualized_return_pct = 0.0

    # Sharpe (risk-free assumed 0 for Phase 5C). Use bar returns; annualize by sqrt(periods_per_year)
    if len(returns) >= 2:
        mean_r = float(pd.Series(returns).mean())
        std_r = float(pd.Series(returns).std(ddof=1))
        sharpe = _safe_ratio(mean_r, std_r) * math.sqrt(periods_per_year) if std_r != 0 else 0.0
    else:
        sharpe = 0.0

    # Drawdown metrics
    dd = 0.0
    max_dd = 0.0
    max_dd_duration = 0
    peak = -float('inf')
    duration = 0
    for eq in equity:
        if eq > peak:
            peak = eq
            dd = 0.0
            duration = 0
        else:
            dd = (eq - peak) / peak if peak > 0 else 0.0
            duration += 1
            if dd < max_dd:
                max_dd = dd
                max_dd_duration = duration
    # Convert to percent
    max_drawdown_pct = max_dd * 100.0

    # Win/loss stats
    avg_win = (win_sum / winning_trades) if winning_trades > 0 else 0.0
    avg_loss = (loss_sum / losing_trades) if losing_trades > 0 else 0.0
    largest_win = max((float(t.get('pnl', 0.0)) for t in trades), default=0.0)
    largest_loss = min((float(t.get('pnl', 0.0)) for t in trades), default=0.0)
    avg_bars_held = float(pd.Series([int(t.get('duration_bars', 0) or 0) for t in trades]).mean()) if trades else 0.0

    return {
        'total_trades': n,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 4),
        'profit_factor': round(float(profit_factor), 6),
        'total_return': round(total_return_pct, 6),
        'annualized_return': round(annualized_return_pct, 6),
        'max_drawdown': round(max_drawdown_pct, 6),
        'max_drawdown_duration': int(max_dd_duration),
        'sharpe_ratio': round(float(sharpe), 6),
        'avg_win': round(float(avg_win), 6),
        'avg_loss': round(float(avg_loss), 6),
        'largest_win': round(float(largest_win), 6),
        'largest_loss': round(float(largest_loss), 6),
        'avg_bars_held': round(float(avg_bars_held), 6)
    }
