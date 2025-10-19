# Signal Generation & Backtesting Engine – Updated Plan
## Incorporating Reviewer Recommendations (Oct 19, 2025)

**Document Version**: 2.0 (Revised)  
**Date**: October 19, 2025  
**Status**: Phase 5A–5D Implemented (signals, simulator, analytics, orchestration); Phase 5E–5F in progress  
**Priority**: Phase 5 - Core Feature Implementation  

---

## Executive Summary (Revised)

Based on comprehensive review of the existing scanner implementation in `backend/main.py`, the plan has been significantly streamlined:

- **Reuse existing vectorized evaluator** (`eval_filter_series`, `eval_measure`) instead of re-implementing.
- **Eliminate duplication** of DSL parsing and indicator caching.
- **Focus on integration** rather than large new subsystems.
- **Reduce complexity by 40%**: From ~90 hours to ~58–78 hours for core functionality.
- **Deliver faster**: 5–6 weeks for full Phase 5A–5F vs. original 7–9 weeks.

This approach keeps behavior consistent across "scan" and "backtest," minimizes rework, and enables rapid iteration toward full-featured simulation and analytics.

---

## Key Architectural Changes

### 1. Reuse Existing Vectorized Engine

**Before (Planned):**
- New `SignalGenerator` class with duplicate indicator computation, caching, and DSL evaluation.
- Risk of drift between scanner and backtest semantics.
- ~30 hours implementing indicator math and caching.

**After (Revised):**
- `SignalGenerator` becomes a thin wrapper calling existing `eval_filter_series(...)` and `fetch_ohlcv_data(...)` from `run-scan`.
- One source of truth for DSL semantics and indicator math.
- Reuse memoization and cross-timeframe handling already proven in scanner.
- ~8–10 hours integrating via existing helpers.

### 2. Signal Generation = Series Masking

Instead of explicit `Signal` objects, work directly with pandas Series returned by `eval_filter_series(...)`:

```python
# Example: entry signal mask
entry_mask = eval_filter_series(entry_dsl_spec, df, symbol, timeframe)  
# Result: pd.Series([False, False, True, True, False, ...])

# Convert True indices to timestamps and prices
entry_indices = entry_mask[entry_mask].index  # DatetimeIndex of signal bars
entry_prices = df.loc[entry_indices, 'close']  # Prices at signal bars
```

**Benefit**: Leverage vectorization; no row-by-row iteration.

### 3. Trade Simulator – Long-Only First

Start with a minimal simulator that handles:
- **Fill logic**: Entry on bar `i` → fill at next-bar-open (configurable).
- **SL/TP intrabar**: Check high/low on the bar when entry happens; apply SL/TP logic.
- **Gap handling**: If gap crosses SL, fill at worst executable price.
- **Indicator warmup**: Skip first N bars where indicators are NaN.
- **Long-only trades**: Short and pyramiding come in Phase 6.

**Avoid**:
- Trailing stops (Phase 6).
- Complex position management (Phase 6).
- Shorting logic (Phase 6).

### 4. Analytics – Core Metrics Only

Phase 5C focuses on essential metrics:
- Total trades, win rate, profit factor
- Total return, annualized return
- Max drawdown, drawdown duration
- Sharpe ratio
- Average win/loss, largest win/loss
- Average bars held

**Defer** (Phase 6):
- Sortino, Calmar, recovery factor
- Monte Carlo analysis
- Trade clustering and distribution analysis

### 5. Database Schema – Reuse Existing Tables

**Option A (Preferred)**:
- Reuse existing `backtest_results` and `trades` tables (already in user DB).
- Add `equity_curve` table for daily equity snapshots (for charting).
- Add columns as needed (e.g., `scanner_spec_json`, `backtest_config_json`).

**Option B**:
- Introduce new tables: `backtest_runs`, `backtest_trades`, `equity_curve`.
- Migrate existing `backtest_results` callers if they exist.

**Decision**: Use Option A for continuity; add `equity_curve` table.

### 6. IPC Contract – Stable and Simple

**Backend action**: `'run-backtest'`

**Input**:
```json
{
  "scanner_spec": { /* JSON AST (same as run-scan) */ },
  "symbol": "RELIANCE",
  "timeframe": "1D",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "backtest_config": {
    "initial_capital": 10000,
    "commission_per_trade": 0.001,
    "position_size_mode": "percent_capital",
    "position_size_value": 2,
    "stop_loss_percent": 2,
    "take_profit_percent": 5
  }
}
```

**Output**:
```json
{
  "metrics": {
    "total_trades": 15,
    "winning_trades": 9,
    "losing_trades": 6,
    "win_rate": 60.0,
    "profit_factor": 1.8,
    "total_return": 12.5,
    "annualized_return": 6.2,
    "max_drawdown": -8.3,
    "max_drawdown_duration": 45,
    "sharpe_ratio": 0.75,
    "avg_win": 150.0,
    "avg_loss": -75.0,
    "largest_win": 500.0,
    "largest_loss": -200.0,
    "avg_bars_held": 22
  },
  "trades": [
    {
      "trade_id": "RELIANCE_1234",
      "symbol": "RELIANCE",
      "entry_timestamp": 1672531200,
      "entry_price": 2500.0,
      "exit_timestamp": 1672790400,
      "exit_price": 2550.0,
      "quantity": 4.0,
      "side": "long",
      "pnl": 200.0,
      "pnl_percent": 2.0,
      "commission": 50.0,
      "status": "closed",
      "exit_reason": "exit_signal",
      "duration_bars": 10
    }
    /* ... more trades ... */
  ],
  "equity_curve": {
    "timestamps": [1672531200, 1672617600, ...],
    "equity": [10000.0, 10050.0, 10120.0, ...]
  },
  "stats": {
    "timeMs": 342,
    "scannedBars": 252,
    "warnings": []
  },
  "requestId": "req-123"
}
```

---

## Implementation Roadmap (Revised)

### Phase 5A: Signal Generation via existing evaluator (Completed)

**Goals**:
- Reuse `eval_filter_series(...)` to generate entry/exit boolean masks.
- No new cache; leverage existing indicator memoization.

**Deliverables**:
1. Backend: Add `'run-backtest'` action in `backend/main.py`.
   - Reuse: `fetch_ohlcv_data(...)`, `eval_filter_series(...)` from scanner.
   - Accept: `scanner_spec`, `symbol`, `timeframe`, `start_date`, `end_date`, `backtest_config`.
   - Output: Entry/exit mask indices and prices.

2. Electron/Main: Add `ipcMain.handle('run-backtest', ...)` forwarding to Python.

3. Preload: Already whitelists `run-backtest`; no changes needed.

**Acceptance Criteria**:
- Entry mask generated for SMA(50) > SMA(200) on sample data.
- Timestamps and prices extracted correctly.
- Reuse of existing evaluator verified (no duplicate code).

---

### Phase 5B: Trade Simulator (Completed)

**Goals**:
- Accept signal masks from 5A.
- Simulate fills at next-bar-open (no lookahead bias).
- Apply SL/TP with documented precedence.
- Long-only trades only.

**Key design choices**:
- **Fill semantics**: Signal on bar `i` → fill at bar `i+1` open.
- **Intrabar SL/TP**: Check high/low on entry bar; apply rules on same bar.
- **Gap handling**: Long SL below gap → fill at open if low < SL < open.
- **Indicator warmup**: Skip leading bars where indicators are NaN.
- **Commission**: Fixed per trade or percent-of-notional.

**Deliverables**:
1. Backend: Minimal `TradeSimulator` class.
   - Method: `simulate(entry_mask: Series, exit_mask: Optional[Series], price_data: DataFrame, config: dict) -> List[Trade]`.
   - No trailing stops, shorting, or pyramiding.

2. Database: Finalize schema (reuse `backtest_results`/`trades` or add `backtest_runs`/`backtest_trades`).

**Acceptance Criteria**:
- Single long trade enters and exits correctly.
- SL/TP fills at correct prices.
- Commission applied correctly.
- Gap crossing SL fills at worst price within bar.
- Warmup bars skipped (no signals on first 200 bars for SMA(200)).

---

### Phase 5C: Analytics (Completed)

**Goals**:
- Calculate core metrics from trade list.
- Build daily equity curve (cumulative P&L + MTM).
- Compute Sharpe ratio and drawdown.

**Deliverables**:
1. Backend: `BacktestAnalytics.calculate_metrics(trades, initial_capital, price_data) -> dict`.
   - Return: All metrics from IPC contract above.

**Acceptance Criteria**:
- Win rate = (winning trades / total trades) * 100.
- Profit factor = sum(winning PnL) / abs(sum(losing PnL)).
- Equity curve cumulative correctly.
- Sharpe = (annualized_return - risk_free_rate) / volatility.
- Max drawdown calculated correctly.

---

### Phase 5D: Backend Orchestration (Completed)

**Goals**:
- Combine 5A, 5B, 5C into single `'run-backtest'` action.
- Return stable JSON response.

**Deliverables**:
1. Backend handler in `backend/main.py`:
   ```python
   elif action == 'run-backtest':
       # 1. Fetch OHLCV via fetch_ohlcv_data(...)
       # 2. Generate entry/exit masks via eval_filter_series(...)
       # 3. Run simulator -> trades list
       # 4. Calculate metrics
       # 5. Store in user_data.db (optional)
       # 6. Return { metrics, trades, equity_curve, stats, requestId }
   ```

   Note: The current implementation also includes a `signals` section under the top-level response for convenience in the UI/dev harness:
   - signals: { symbol, timeframe, priceField, entries: [{ timestamp, price }], count, seriesLength }

**Acceptance Criteria**:
- Full backtest workflow completes end-to-end. ✅
- JSON response matches contract. ✅
- Errors handled gracefully (return error in response). ✅

---

### Phase 5E: UI – Builder + Results (1 week, 10–12 hours)

**Goals**:
- Simple config form for backtest parameters.
- Results display: metrics card + trades table.
- Use `window.electronAPI.invoke(...)` to match preload API.

**Deliverables**:
1. `src/components/BacktestBuilder.tsx`:
   - Form for: initial_capital, commission, position_size_mode, position_size_value, SL%, TP%.
   - Run backtest button.
   - Display results via `BacktestResults` component.

2. `src/components/BacktestResults.tsx`:
   - Metrics summary card (key stats).
   - Trades table (entry/exit dates, prices, PnL, %return).
   - Optional: inline equity curve chart or link to chart viewer.

**Acceptance Criteria**:
- Form inputs validated (e.g., capital > 0).
- Results render correctly.
- Uses `window.electronAPI.invoke('run-backtest', payload)`.
- Responsive layout on desktop and tablet.

---

### Phase 5F: Testing (1.5 weeks, 12–15 hours)

**Goals**:
- Unit tests for signal masks, stops, warmup.
- Integration tests for end-to-end backtest.
- Edge cases: gaps, identical series (no false crosses), NaN handling.

**Deliverables**:
1. `tests/test_signal_generation.py`:
   - SMA(50) > SMA(200) crossover produces expected mask positions.
   - Indicator NaN handling (first N bars).
   - Identical series do not falsely cross.

2. `tests/test_trade_simulation.py`:
   - Single long trade enters and exits.
   - SL fills at correct price (intrabar and gap).
   - TP fills before SL.
   - Commission deducted correctly.
   - Warmup bars skipped.

3. `tests/test_backtest_analytics.py`:
   - Win rate, profit factor calculated correctly.
   - Sharpe ratio formula correct.
   - Equity curve cumulative sum.
   - Drawdown calculation.

4. `tests/test_backtest_integration.py`:
   - End-to-end backtest on small dataset (50 bars, 1 symbol).
   - Trades count matches expected.
   - Metrics within expected range.

**Acceptance Criteria**:
- All tests pass.
- Coverage > 80% for core modules.
- Edge cases documented and handled.

---

### Phase 6: Parameter Optimization (Deferred, 2–3 weeks, 20–25 hours)

**Goals**:
- Grid search over DSL variable ranges.
- Report best parameters by Sharpe ratio.
- Walk-forward testing.

**Effort**: Deferred after Phases 5A–5F are complete and tested.

---

## Revised Timeline

| Phase | Name | Duration | Effort | Status |
|-------|------|----------|--------|--------|
| 5A | Signal generation (reuse evaluator) | 1 week | 10–15 hrs | Completed |
| 5B | Trade simulator (long-only, next-open) | 1.5 weeks | 12–18 hrs | Completed |
| 5C | Analytics (core metrics) | 1 week | 8–10 hrs | Completed |
| 5D | Backend orchestration | 3–4 days | 6–8 hrs | In Progress |
| 5E | UI (builder + results) | 1 week | 10–12 hrs | Ready |
| 5F | Testing | 1.5 weeks | 12–15 hrs | Ready |
| 6 | Parameter optimization | 2–3 weeks | 20–25 hrs | Deferred |

**Total (Phases 5A–5F)**: ~5–6 weeks, ~58–78 hours.  
**Reduction vs. original plan**: 40% fewer hours, 30% faster delivery.

---

## Key Decisions Made

1. **Reuse vectorized evaluator**: No duplicate DSL parser or cache. One source of truth.
2. **Long-only first**: Reduces complexity. Short and pyramiding come in Phase 6.
3. **Next-bar-open fills**: Configurable but default avoids lookahead. Clear gap and intrabar rules.
4. **Existing tables preferred**: Reuse `backtest_results`/`trades`. Add `equity_curve` table for charting.
5. **Core metrics only**: Total return, win rate, max DD, Sharpe. Sortino, Calmar in Phase 6.
6. **Progress events optional**: Return full response; emit progress on `backtest-progress` channel for UX.

---

## Immediate Next Steps

### Week 1:

1. **Backend (5A)**: Implement `'run-backtest'` action using existing evaluator helpers.
   - Reuse `fetch_ohlcv_data(...)`, `eval_filter_series(...)`.
   - Accept scanner_spec, extract entry/exit masks.
   - Return signal indices and prices.

2. **Tests (5F prep)**: Write unit tests for signal mask validation.
   - Test SMA crossover on synthetic data.
   - Verify NaN handling in warmup period.

3. **Database**: Finalize schema decision (Option A: reuse + add `equity_curve`).
   - Add migrations if needed.

4. **Electron (5A)**: Add `ipcMain.handle('run-backtest', ...)` forwarding to Python.

### Week 2:

5. **Backend (5B)**: Implement minimal `TradeSimulator`.
   - Accept entry/exit masks, simulate long-only trades.
   - Test SL/TP fills, gap handling, commission.

6. **Backend (5C)**: Implement `BacktestAnalytics`.
   - Calculate metrics, build equity curve.

7. **UI (5E prep)**: Stub `BacktestBuilder.tsx` form.

### Week 3:

8. **Backend (5D)**: Orchestrate full backtest workflow.
   - Chain 5A → 5B → 5C.
   - Return stable JSON response.

9. **UI (5E)**: Build `BacktestResults.tsx` display.
   - Metrics card, trades table, optional equity chart link.

10. **Tests (5F)**: Complete end-to-end integration test.
    - Validate full workflow on sample data.

---

## Success Criteria for Phase 5

- [ ] Backtest runs end-to-end on single symbol.
- [ ] Entry and exit signals generated correctly from scanner DSL.
- [ ] SL/TP fills at correct prices (intrabar, gap-aware).
- [ ] Metrics calculated accurately (win rate, Sharpe, drawdown).
- [ ] UI displays results (metrics, trades, optional chart link).
- [ ] All tests pass (coverage > 80%).
- [ ] No duplicate code from scanner (vectorized evaluator reused).
- [ ] No lookahead bias (next-bar-open fills, warmup skipped).

---

## Future Roadmap (Phases 6–8)

### Phase 6: Enhancements
- Short trades and pyramiding.
- Trailing stops.
- Additional metrics (Sortino, Calmar, recovery factor).
- Parameter optimization (grid/random search).

### Phase 7: Real-Time Integration (Not to be included in this project)
- Live signal generation (streaming market data).
- Paper trading simulation.

### Phase 8: Portfolio Management
- Multi-symbol backtests.
- Portfolio allocation and rebalancing.
- Cross-symbol correlation analysis.

---

## Conclusion

By reusing the existing vectorized evaluator, the signal generation and backtesting integration becomes a straightforward orchestration task, reducing effort by 40% and delivery time by 30%. The revised plan prioritizes clarity, correctness (no lookahead bias), and rapid iteration toward a full-featured simulation platform.

**Ready to implement immediately after this review.**
