````markdown
# BYOD Strategy Backtesting — Merged Architecture & Implementation Plan
## Combined Technical Architecture and Implementation Roadmap

---

This document merges the high-level architecture from `Architecture.md` with practical implementation decisions, tuned defaults, and operational guidance from `Implementation_plan_other project.md`. The goal is to keep the original architecture's structure while adding concrete, measurable implementation items and defaults that have been benchmarked and validated.

---

## 1. System Overview (merged)

### Architecture Philosophy (keeps original principles + added constraints)
- Offline-first design: full feature set available without network access
- Monolithic desktop application packaged with an embedded Python runtime for heavy data work
- Data sovereignty and local-first storage (separate market and user DBs preferred)
- Simplicity and reliability first; add advanced features behind opt-in toggles

### High-Level Architecture (same layered model)
```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Main Process                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Data Manager  │  │ Strategy Engine │  │  Results Engine ││
│  │                 │  │                 │  │                 ││
│  │ • CSV / Parquet │  │ • Graph → Comp. │  │ • Charting      ││
│  │   / XLSX import │  │ • Backtesting   │  │ • Metrics       ││
│  │ • Validation    │  │ • Indicators    │  │ • Export        ││
│  │ • SQLite / DuckDB opt. │                 │                 ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                     Electron IPC Layer                     │
├─────────────────────────────────────────────────────────────┤
│                   Python Backend Service (bridge)          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Data Engine   │  │ Backtest Engine │  │  Analytics      ││
│  │  (parquet/python)│  │ (vectorized)    │  │  (metrics,MC)   ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                        SQLite Databases                    │
│  (market_data.db)  (user_data.db)  (optional: duckdb fast-path)
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Key Implementation Decisions / Tuned Defaults (actionable)

These defaults were derived from benchmark runs and pragmatic tradeoffs. Commit them to `benchmarks/defaults.json` and reference in CI and README.

- csv.parser: "native-split" (fallback: "csv-parser")
- sqlite.batchSize: 10000
- sqlite.pragmas: { "journal_mode": "WAL", "synchronous": "NORMAL", "cache_size": 10000 }
- workerPool.size: max(1, cpuCores - 1)
- python.pool.defaultSize: max(1, cpuCores - 1) (persistent pool recommended)
- parquet.batchSize (python/pyarrow): 8192 (tunable)
- default storage: separate `market_data.db` and `user_data.db` to reduce contention

Decision highlights:
- Keep DuckDB as an optional fast-path (do not enable by default). Add a migration plan to flip on per-install if benchmarks justify it.
- Python bridge: prefer persistent worker pool for warm runs and concurrency; allow isolated per-job spawn mode for easier debugging.

---

## 3. Data Import Engine (incorporated improvements)

Overview:
- Use a parent-driven, worker-thread CSV pipeline for high-throughput imports, with a single serialized SQLite writer in main thread.
- Provide a parser factory that returns async iterators for CSV / XLSX / Parquet. Parquet should use a Python/pyarrow hybrid path when available and fall back to Node-based readers otherwise.

Frontend contract (IPC):
```typescript
// preview and import API surface
async function importData(filePath: string, symbol?: string, mapping?: any): Promise<ImportResult>
```

Backend behavior:
- Chunking strategy: calculate byte-range chunks aligned to newline boundaries, hand chunks to worker pool
- Workers parse, validate, normalize and return batches (worker batch default: 1,000 rows)
- Main thread batch writer flushes at 5,000–10,000 rows or 500ms (whichever first) using transactions
- Validation rules: required OHLC columns, numeric checks, High>=Low invariants, non-negative volume

Parquet/XLSX handling:
- Parquet: prefer `electron/python/parquet_reader.py` using `pyarrow.iter_batches(batch_size=8192)` and emit JSON batches to Node. If Python unavailable, `parquetjs-lite` fallback.
- XLSX: streaming Node parser with sheet selection and header normalization.

Progress & cancellation:
- Provide real-time progress updates (rows processed, rows/sec) via IPC. Support AbortSignal for graceful cancellation and mark `data_uploads` record as cancelled.

---

## 4. Strategy Builder & Compiler (practical additions)

Keep the visual graph-based builder but add a formal compilation step and validations before running heavy backtests:

- Graph → compiled strategy JSON (topo-sorted execution order)
- Parameter validator (range checks, sensible defaults)
- Quick-test mode: run strategy on a small sample range (smoke test) before queuing full backtest

Supported nodes & indicators: align with pandas-ta initially (SMA, EMA, RSI, MACD, Bollinger, ATR, OBV) and expand later.

---

## 5. Python Backtesting Engine (pragmatic guidance)

Core:
- Vectorized indicator calculations in NumPy/Pandas
- Signal generation via compiled strategy JSON
- Execution simulator with market/limit/stop, slippage, commission
- Equity curve, trade logging, and performance metrics

Operational considerations:
- Expose progress stages from Python (load → indicators → signals → simulate → metrics) and stream to UI to estimate time remaining
- Persist partial results in database periodically to allow recovery on crashes

---

## 6. Results & Analytics (merged)

Keep charting and metrics from `Architecture.md`, add:
- Monte Carlo module (optional phase 2)
- Walk-forward optimization reports and WFO visualizations in Phase 2
- Export: PDF (electron/puppeteer) and standalone HTML dashboard

---

## 7. Database Schema & Migration

Adopt the existing schema ideas and add migration and backup guidance:

- Separate `market_data.db` (OHLCV, symbols, data_uploads) and `user_data.db` (strategies, backtests, trades, settings)
- Track applied migrations with a `migrations` table (id, checksum, applied_at)
- Use a migration-runner to apply idempotent SQL files on startup

---

## 8. Backup, Recovery & Data Quality (actionable items to adopt)

Backup & recovery (adopted from Implementation plan):
- Auto-backups with configurable retention (default: daily, keep 30)
- Integrity verification of backups and a restore workflow
- Database integrity check on startup and automatic WAL recovery when safe

Data quality features to incorporate:
- Corporate actions processor (stock splits, dividends) as a Phase 1.2.5 objective
- Gap detection, outlier detection (Z-score, IQR), timezone normalization
- Symbol mapping / historical ticker normalization

---

## 9. Security Hardening (must-have additions)

Incorporate these Electron best-practices immediately:
- contextIsolation: true, nodeIntegration: false, sandbox: true
- Expose a minimal, validated IPC surface via `preload` with a channel whitelist
- Content Security Policy headers in production builds
- Restrict filesystem access to vetted internal handlers only

---

## 10. Testing, CI and Benchmarks

- Unit tests: frontend (Jest/RTL), backend (pytest), Node workers (Jest)
- Integration tests: Python bridge smoke tests and import + backtest e2e
- CI: add a fast smoke step for Parquet that optionally installs Python + pyarrow in a conditional job
- Benchmarks artifacts: `benchmarks/report.md` and `benchmarks/defaults.json` (commit these)

---

## 11. Development Timeline (condensed and actionable)

Phase 0 (Week 0): Benchmark & validate parser, sqlite batch sizes, python warm-start behavior — commit `benchmarks/defaults.json`.

Phase 1 (Weeks 1-8): Shell, SQLite schemas & migrations, parent-driven CSV worker pipeline, parser factory (CSV/XLSX/Parquet), Python bridge scaffold, backup & security hardening.

Phase 2 (Weeks 9-20): Strategy builder, backtesting engine feature-complete, indicators, result dashboards, and Phase 2 advanced features (multi-TF, WFO, portfolio, Monte Carlo) prioritized after core stability and tests.

---

## 12. Actionable To-Dos (what to commit next)

1. Add `benchmarks/defaults.json` (tuned defaults above).
2. Add parser factory and Parquet Python reader shim if not present (files: `electron/services/parsers/*`, `electron/python/parquet_reader.py`).
3. Implement parent-driven CSV chunker + worker-pool if missing and ensure a single main-thread batch writer.
4. Add migration-runner and initial SQL migrations for market & user DBs and commit `electron/database/migrations/001_initial.sql`.
5. Commit Electron security hardening changes to `electron/main.*` and `preload.*` and expose minimal IPC API.
6. Add backup-manager and recovery-manager (or adopt existing implementations) and wire into startup checks.
7. Add CI smoke tests for parser/import and optional Python-backed Parquet tests.

---

## 13. Verification & Next Steps

- The next practical step is to commit `benchmarks/defaults.json` and update README notes to reference the tuned defaults.
- Then add or validate the parser factory and the parent-driven CSV worker pipeline in the codebase; run import smoke tests (use `sample_ohlc_data.csv` and `large_sample.csv`) and measure throughput against the targets.

Completion summary: This merged plan keeps the original architecture structure while adding measured defaults, concrete implementation choices (worker-thread CSV pipeline, Parquet Python hybrid), and operational features (backups, security, migrations) that should be adopted into the current project.

---

This file was generated by merging `Architecture.md` with `Implementation_plan_other project.md` and extracting the immediately actionable and high-value items for incorporation.
````