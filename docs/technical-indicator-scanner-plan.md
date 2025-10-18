# Technical Indicator Scanner — Implementation Plan (Chartink parity, indicators only)

Date: 2025-10-18
Owner: BYOD Backtesting (Electron + Python)
Scope: Technical indicator scanning (ignore fundamentals/alerts for now)

## Goal
Build a flexible, fast technical scanner inspired by Chartink’s Scanner User Guide, focusing on:
- Filters built from stock attributes and indicators
- Offsets (lookback indexing) and multiple timeframes
- Arithmetic/comparison/crossover ops
- Grouping (AND/OR) with nested sub-filters
- Functional filters (MIN/MAX over period)
- Backtest-like query against local OHLCV DB

## Terminology
- Candle: OHLCV row for a symbol/timeframe
- Offset: [k] means k-th candle from the session start for intraday or simply historical lookback in EOD; also support relative [-n] lookback
- Period: number of bars over which indicators or min/max are computed
- Measure: attribute or indicator output used by a function

## What Chartink supports (indicator-related)
- Components: stock attributes (open/high/low/close/volume), number constants, indicators (SMA/EMA/RSI/MACD/ADX/Bollinger/etc.), offsets
- Operations: arithmetic (+ - * /), comparison (< <= > >= == !=), crossover/crossunder
- Grouping: multiple filters, sub-filters (AND/OR nesting)
- Functional filters: Max(period, measure), Min(period, measure)
- Examples: RSI cross zones, gap up/down (% comparisons with prior close), SMA crossovers, 52-week high via Max(252, High)

We target these for v1.

## Non-goals (deferred)
- Fundamentals
- Alerts/notifications & Atlas dashboards
- Watchlists/segments beyond our DB
- Proprietary/time-and-sales or option-oi derived filters
- Custom-rendered charts inside scanner (we’ll reuse existing charts for preview later)

---

## Architecture overview
- Renderer (React): Visual filter builder (no-code), plus an “advanced” text DSL editor for power users
- Main (Electron): routes scanner requests to Python
- Backend (Python): Parser + AST + query planner + indicator engine + execution (SQLite)
- Storage: existing market_data.db; indicators computed on-the-fly with caching

### Data flow
1) User defines scan (UI builder or DSL)
2) Renderer sends a JSON scanner spec to Electron main → Python backend
3) Backend parses/validates, plans execution (symbols universe, timeframe, required columns, windows), computes indicators, evaluates filter expressions across bars per symbol
4) Returns matching symbols (optionally last matched bar timestamp, sample values per filter)

---

## DSL (text) — minimal v1
- Literals: numbers (123, 1.5), strings for timeframe/symbol if needed
- Attributes: open, high, low, close, volume
- Offsets:
  - Lookback index: [-n] attr (n > 0) e.g., [-1] close
  - Candle ordinal of the day/session: [=k] 5min close (defer full session-aware semantics; v1 interpret [=k] as k-th bar from series start or from trading-day partition if timeframe intraday and session boundaries are known)
- Indicators: SMA(close, 20), EMA(close, 9), RSI(close, 14), MACD(close, 12, 26, 9), ADX(14), BollingerMiddle(close, 20, 2), BollingerUpper(close, 20, 2), BollingerLower(close, 20, 2), VWAP (daily-only v1), ATR(14)
- Functions: MAX(n, measure), MIN(n, measure)
- Ops: + - * /, < <= > >= == !=, CROSSES_ABOVE(a, b), CROSSES_BELOW(a, b)
- Grouping via parentheses; AND/OR/NOT keywords

Example:
- close > 500
- SMA(close, 50) CROSSES_ABOVE SMA(close, 200)
- RSI(close, 14) > 70 AND volume > 2 * SMA(volume, 20)
- MAX(252, high) == high
- [ -1 ] close * 1.03 < open  // gap-up 3%

JSON AST equivalent will be used by the engine (renderer will generate it; DSL is optional but nice to have).

---

## UI (builder) — v1
- Add filter row
  - Component selector: Attribute | Indicator | Function (MIN/MAX)
  - If Indicator: dropdown (SMA/EMA/RSI/MACD/ADX/BB/ATR/VWAP), then parameter editors
  - Operation selector: comparison/crossover or arithmetic chain
  - Right-hand operand: attribute/indicator/function or number constant
  - Offset: dropdown for [-n] and [=k] with numeric input
- Add AND/OR group (sub-filter). Nesting allowed.
- Timeframe selector: Daily (v1) + prepare stubs for Intraday (5m/15m/1h)
- Universe selector: All symbols (from DB) or subset via multi-select (phase 2)
- Run scan button → results table with symbol, last date, matched explanation (optional per-row tooltip)

---

## Backend (Python) — components
1) Parser
   - For v1 we can start with JSON spec only (UI builder emits JSON). Add DSL parser later.
   - JSON grammar (draft):
     {
       "timeframe": "1D",
       "universe": "ALL" | ["AAPL", "MSFT"],
       "filters": [ FilterNode ]
     }

     FilterNode can be:
     - { "op": "group", "logic": "AND"|"OR", "children": [FilterNode, ...] }
     - { "op": "not", "child": FilterNode }
     - Comparison/Crossover:
       {
         "op": "compare"|"crossover",
         "cmp": "<"|"<="|">"|">="|"=="|"!=", // only for compare
         "type": "CROSSES_ABOVE"|"CROSSES_BELOW", // only for crossover
         "left": MeasureNode,
         "right": MeasureNode
       }
     - Arithmetic chain (optional v1):
       { "op": "arith", "expr": [MeasureNode, "+"|"-"|"*"|"/", MeasureNode, ...] }

     MeasureNode can be:
     - { "type": "attr", "name": "close"|"open"|"high"|"low"|"volume", "offset": {"kind": "lookback", "bars": 1} | {"kind":"ordinal","n":2} | null }
     - { "type": "indicator", "name": "SMA"|"EMA"|"RSI"|"MACD"|"ADX"|"BB_UPPER"|"BB_MIDDLE"|"BB_LOWER"|"ATR"|"VWAP", "params": { ... }, "offset": ... }
     - { "type": "func", "name": "MAX"|"MIN", "period": n, "measure": MeasureNode }
     - { "type": "const", "value": number }

2) Indicator engine
   - Use pandas/ta-lib-like computations via pandas + numpy (avoid external TA libs initially)
   - Implement: SMA, EMA, RSI, MACD (line/signal/hist), ADX (di+/di- optional), BB (upper/middle/lower), ATR, VWAP (daily)
   - All indicators computed per symbol over the needed window. Cache per request by (symbol, timeframe, required_series_signature)

3) Query planner
   - Derive required series windows:
     - From indicators and MIN/MAX lookbacks, compute needed lookback bars (e.g., EMA 200 requires >= 200 + safety margin, MACD 26/9 requires ~ 26+9 + safety, RSI n requires n+1, ADX 14 requires ~ (14*2) etc.)
     - From crossovers, need at least 2 bars to detect edge
   - Fetch OHLCV for all symbols in universe for the timeframe with required bars
   - Compute indicators, then evaluate filters row-wise per bar. For v1, return matches on the latest bar only (like “latest close”). Phase 2: allow historical matches window/backtest.

4) Evaluator
   - Comparison: evaluate left,right series at aligned index, pick last bar (or all bars if backtest mode)
   - Crossover: detect when left[t-1] <= right[t-1] and left[t] > right[t] (or inverse for below)
   - Arithmetic expr: evaluate vectorized
   - Group logic: apply AND/OR across predicates

5) Output
   - { results: [ { symbol, timestamp, sample: { metricName:value, ... } } ], stats: { scannedSymbols, timeMs } }

---

## IPC additions
Electron main to Python backend (existing JSON request/response):
- Action: "run-scan"
  - payload: scannerSpec JSON (see above), options: { latestOnly: true, limit: 5000 }
- Response: { results, error? }

Renderer will add a minimal “Build Strategy → Scanner” tab to create filters and run.

---

## Phased delivery

Phase 0 — groundwork (1–2 days)
- Backend: module skeletons (parser from JSON, indicator registry, evaluator)
- Electron main: add run-scan IPC
- Renderer: simple dev page to submit a hard-coded JSON scannerSpec and show results

Phase 1 — Core comparisons and indicators (3–5 days)
- Indicators: SMA, EMA, RSI, MACD (line/signal), ATR, BB (upper/mid/lower), ADX (main), VWAP (daily)
- Attributes: open/high/low/close/volume
- Offsets: simple lookback [-n]
- Ops: arithmetic, comparison, crossovers
- Functions: MAX/MIN(period, measure)
- Latest-bar evaluation per symbol
- Tests: unit tests for indicator outputs and basic scans

Phase 2 — UI builder + grouping (3–4 days)
- React components for:
  - Add filter rows, pick component type & parameters
  - Choose operators and right-hand side
  - Grouping (AND/OR), nested with simple UI
  - Timeframe selector (Daily, stub others)
- Serialize to JSON AST; send to backend; render results table

Phase 3 — Multiple timeframes and offsets (2–3 days)
- Support [=k] ordinal within daily (acts like fixed index from series start or trading-day partition in intraday later)
- Add 5m/15m/1h timeframe at storage level if data is available; otherwise resample daily-only and keep API stable
- Cross-timeframe requests: evaluate each timeframe per condition independently, AND/OR them

Phase 4 — Performance & UX polish (2–4 days)
- Symbol batching, parallel compute per symbol
- Memoize per-request series
- Add “explain” tooltips showing evaluated values on last bar for each filter
- Pagination/limit controls; result sorting

Backlog (nice-to-have)
- DSL text parser
- Backtest mode returning historical matches over a date range
- Saved scans (CRUD) in user DB
- Watchlists/universe subsets

---

## Contract (backend API)
Input:
- action: "run-scan"
- payload: scannerSpec JSON (see above)
- options.latestOnly: boolean (default true)

Success output:
- results: [ { symbol: string, timestamp: number, values?: Record<string, number> } ]
- stats: { scannedSymbols: number, timeMs: number }

Errors:
- { error: "ParseError|ValidationError|ExecutionError", details }

---

## Edge cases
- Missing data for symbol/timeframe: skip symbol, record warning
- Insufficient history for indicator period: return no-match for symbol
- Division by zero in arithmetic: guard with NaN and treat as false
- Crossover on flat series: require strict inequality changes
- Floating precision: use np.isclose for equality compares with epsilon

---

## Minimal test plan
- Indicators: compare against known small vectors for SMA/EMA/RSI/MACD/ATR/BB/ADX
- Comparisons: open > close, etc.
- Crossovers: construct synthetic series to validate above/below
- MIN/MAX: detect 52-week extremes with controlled data
- Combined filter: RSI>70 AND close>MAX(20, high)-epsilon
- Performance: 100 symbols x 5k bars within acceptable time (<2s local, synthetic)

---

## Implementation notes
- Python: pandas, numpy only; keep engine pure and deterministic
- We already have SQLite OHLCV; add simple timeframe adapter if we later store intraday
- Renderer state: store scannerSpec in React state; reuse existing IPC wiring
- Security: no remote code execution — strict parsing of JSON AST, no eval

---

## Milestone acceptance (v1)
- Run a scan equivalent to examples:
  - RSI(14) > 70
  - SMA(50) crosses above SMA(200)
  - Gap up > 3% vs previous close
  - 52-week high using MAX(252, high) == high
- Show results table with symbol and last timestamp; returns within a couple seconds on local DB

