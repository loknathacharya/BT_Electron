# Signal Generation & Backtesting – Quick Reference
**Updated Oct 19, 2025**

---

## What Changed

| Aspect | Before | After |
|--------|--------|-------|
| **Approach** | Build new signal generator from scratch | Reuse existing `eval_filter_series()` from scanner |
| **Total effort** | ~90 hours | ~58–78 hours |
| **Timeline** | 7–9 weeks | 5–6 weeks |
| **Complexity** | High (new DSL parser, cache, indicators) | Low (thin wrapper, reuse proven code) |
| **Risk of drift** | High (two evaluators) | None (one source of truth) |
| **Initial scope** | All features (long/short, pyramiding, etc.) | Long-only, core metrics only |

---

## Key Simplifications

### 1. Signal Generation
- **Old**: New class with indicator computation and caching → **30 hours**
- **New**: Wrapper calling `eval_filter_series(...)` → **10–15 hours**

### 2. Simulator
- **Old**: Support short, pyramiding, trailing stops from day 1 → **25 hours**
- **New**: Long-only, next-bar-open fills, SL/TP basic rules → **12–18 hours**

### 3. Metrics
- **Old**: All metrics (Sortino, Calmar, recovery factor, etc.) → **15 hours**
- **New**: Core metrics (win rate, Sharpe, max DD) → **8–10 hours**

### 4. Database
- **Old**: New tables + migrations → **5 hours**
- **New**: Reuse existing + add `equity_curve` → **2 hours**

---

## Revised Architecture

```
User → Electron UI (BacktestBuilder.tsx)
        ↓
Electron Main (ipcMain.handle('run-backtest'))
        ↓
Python Backend:
  1. Fetch OHLCV (fetch_ohlcv_data)
  2. Generate signals (eval_filter_series from scanner)
  3. Simulate trades (TradeSimulator - long-only)
  4. Calculate metrics (BacktestAnalytics)
  5. Return JSON
        ↓
User sees: Metrics card, trades table, equity curve
```

**No new DSL parser. No duplicate cache. Reuse everything from scanner.**

---

## API Contract (One IPC Action)

**Backend**: `'run-backtest'`

**Input**: 
- `scanner_spec` (same JSON AST as `run-scan`)
- `symbol`, `timeframe`, `start_date`, `end_date`
- `backtest_config` (capital, commission, position_size_mode, SL%, TP%)

**Output**: 
- `metrics` (win_rate, sharpe, max_drawdown, total_return, etc.)
- `trades` (array with entry/exit prices, PnL, duration)
- `equity_curve` (timestamps + equity values)
- `stats` (execution time, bars processed, warnings)

---

## Implementation Phases

| Phase | What | When | Effort |
|-------|------|------|--------|
| 5A | Reuse scanner evaluator for signals | Week 1 | 10–15 hrs |
| 5B | Build minimal long-only simulator | Week 1–2 | 12–18 hrs |
| 5C | Calculate core metrics | Week 2 | 8–10 hrs |
| 5D | Orchestrate backend workflow | Week 2–3 | 6–8 hrs |
| 5E | Build UI (form + results) | Week 3 | 10–12 hrs |
| 5F | Comprehensive testing | Week 3–4 | 12–15 hrs |

**Total**: 5–6 weeks for full Phase 5 core functionality.

---

## Fill Rules (No Lookahead Bias)

- **Entry signal on bar i** → Fill at bar i+1 open
- **Exit signal on bar i** → Fill at bar i+1 open
- **SL/TP triggered** → Fill at worst price within intrabar (high/low)
- **Gap crosses SL** → Fill at open if gap crosses but bar low < SL < open
- **Indicator warmup** → Skip first N bars where indicators are NaN

---

## Testing Checklist

- [ ] SMA(50) > SMA(200) crossover generates correct signal mask
- [ ] Single long trade enters and exits correctly
- [ ] SL fills at correct price (including gap handling)
- [ ] TP fills before SL when both triggered
- [ ] Commission deducted from net PnL
- [ ] Warmup bars skipped (no signals in first 200 bars for SMA(200))
- [ ] Win rate = (winning trades / total) * 100
- [ ] Sharpe ratio formula correct
- [ ] Equity curve cumulative sum validated
- [ ] E2E backtest on 50-bar sample returns expected metrics

---

## Decisions Made

1. **Reuse vectorized evaluator** ✓
2. **Long-only first** ✓
3. **Next-bar-open fills** ✓
4. **Reuse existing DB tables** ✓
5. **Core metrics only** ✓
6. **Single orchestrated action** ✓

---

## Next Steps (Immediate)

1. **Backend**: Add `'run-backtest'` action to `backend/main.py` (Phase 5A).
2. **Electron**: Add `ipcMain.handle('run-backtest', ...)` to `electron/main.ts`.
3. **Tests**: Unit test for signal mask validation.
4. **Database**: Finalize schema (reuse + `equity_curve` table).
5. **UI**: Stub `BacktestBuilder.tsx` form.

**Ready to start implementation immediately.**

---

## Questions?

See detailed plan: `docs/SIGNAL_BACKTEST_UPDATED_PLAN.md`  
Original plan with pseudo-code: `docs/signal-generation-backtest-integration-plan.md` (sections 1–8)
