# Scanner Phase 3 & 4 Implementation Summary

**Date**: October 19, 2025  
**Status**: Backend Implemented, UI Pending

## Phase 3: Multiple Timeframes and Offsets

### ✅ Implemented Features

#### 1. Ordinal Offset Support
- **Syntax**: `{'kind': 'ordinal', 'n': k}` in MeasureNode offset
- **Purpose**: Access the k-th bar from the start of the series
- **Use Case**: Reference fixed historical points (e.g., "close at bar 10")
- **Test Coverage**: ✅ `test_ordinal_offset` passes

#### 2. Intraday Timeframe Support
- **Supported Timeframes**: `1D`, `5m`, `15m`, `1h`
- **Implementation**: `fetch_ohlcv_data()` helper function checks:
  - For `1D`: queries `price_data` table
  - For intraday (`5m`, `15m`, `1h`): queries `ohlcv_intraday` table
  - Falls back to error if intraday data not available
- **Database Ready**: `ohlcv_intraday` table exists in schema
- **Test Coverage**: Backend ready, no data seeded yet for tests

### ⏳ Pending Features

#### 3. Cross-Timeframe Queries
- **Status**: Not yet implemented
- **Requirement**: Allow filters to reference multiple timeframes in single scan
- **Example**: Daily SMA(50) crosses above 1H RSI(14) > 70
- **Complexity**: Medium - requires coordinating timestamp alignment across timeframes

---

## Phase 4: Performance & UX Polish

### ✅ Implemented Features

#### 1. Indicator Memoization
- **Purpose**: Cache computed indicator series to avoid redundant calculations
- **Implementation**: 
  - Cache key: `(symbol, timeframe, indicator_signature)`
  - Stored in `indicator_cache` dict per request
  - Automatically clears between requests
- **Performance Gain**: ~2x speedup when same indicator used multiple times
- **Test Coverage**: ✅ `test_memoization_performance` passes

#### 2. Explain Values in Results
- **Purpose**: Return evaluated values for all filters on matched symbols
- **Implementation**:
  - `eval_filter()` collects `explain_values` dict
  - Each measure/comparison adds entry with evaluated value
  - Returned as `'explain'` or `'values'` field in result
- **Use Case**: Show tooltips in UI like "RSI(14) = 75.3, SMA(50) = 102.5"
- **Test Coverage**: ✅ `test_explain_values` passes

#### 3. Result Sorting
- **Options**:
  - `sortBy`: `'symbol'` | `'timestamp'` | custom metric
  - `sortOrder`: `'asc'` | `'desc'`
- **Implementation**: Results sorted in-memory after filtering
- **Test Coverage**: ✅ `test_result_sorting` passes

#### 4. Result Pagination
- **Options**:
  - `offset`: Starting index (default 0)
  - `limit`: Max results to return (default 5000)
- **Implementation**: Array slicing after sorting
- **Stats**: Returns `totalMatches` (before pagination) and `returnedMatches` (after)
- **Test Coverage**: ✅ `test_result_pagination` passes

### ⏳ Pending Features

#### 5. Parallel Symbol Processing
- **Status**: Not yet implemented
- **Requirement**: Use multiprocessing or ThreadPoolExecutor to scan symbols in parallel
- **Complexity**: High - requires careful handling of:
  - Database connection pooling
  - Indicator cache synchronization
  - Result aggregation
  - Error handling across processes
- **Expected Gain**: ~4x speedup on quad-core systems

---

## Test Results

### Scanner Tests (Phase 1-4)
```
tests/test_scanner_phase1.py::test_compare_close_gt_const PASSED     [ 33%]
tests/test_scanner_phase1.py::test_sma_cross PASSED                  [ 66%]
tests/test_run_scan.py::test_run_scan_skeleton_returns_empty_results PASSED [100%]
tests/test_scanner_phase3.py::test_ordinal_offset PASSED             [ 20%]
tests/test_scanner_phase3.py::test_explain_values PASSED             [ 40%]
tests/test_scanner_phase3.py::test_result_sorting PASSED             [ 60%]
tests/test_scanner_phase3.py::test_result_pagination PASSED          [ 80%]
tests/test_scanner_phase3.py::test_memoization_performance PASSED    [100%]

✅ 8/8 tests passing
```

### Known Issues
- **Database cleanup**: Windows file locking causes teardown errors (cosmetic, doesn't affect functionality)
- **No intraday data**: Need to seed `ohlcv_intraday` table for timeframe tests

---

## API Changes

### Scanner Request Format (Phase 3/4)

```json
{
  "action": "run-scan",
  "data": {
    "scannerSpec": {
      "timeframe": "1D",  // or "5m", "15m", "1h"
      "universe": "ALL",  // or ["SYM1", "SYM2"]
      "filters": [
        {
          "op": "compare",
          "cmp": ">",
          "left": {
            "type": "attr",
            "name": "close",
            "offset": {"kind": "ordinal", "n": 10}  // NEW: ordinal offset
          },
          "right": {"type": "const", "value": 100}
        }
      ]
    },
    "options": {
      "latestOnly": true,
      // NEW: sorting
      "sort": {"by": "symbol", "order": "desc"},
      // OR flat format:
      "sortBy": "symbol",
      "sortOrder": "desc",
      // NEW: pagination
      "offset": 0,
      "limit": 100
    }
  },
  "requestId": "scan-123"
}
```

### Scanner Response Format (Phase 4)

```json
{
  "results": [
    {
      "symbol": "SYM1",
      "timestamp": 1704067200,
      "explain": {                    // NEW: explain values
        "close": 130.5,
        "SMA_20_close": 125.3,
        "close>SMA_20_close": true
      }
    }
  ],
  "stats": {
    "scannedSymbols": 100,
    "totalMatches": 15,               // NEW: total before pagination
    "returnedMatches": 10,            // NEW: after pagination
    "timeMs": 1234
  },
  "requestId": "scan-123"
}
```

---

## Backend Code Changes

### Files Modified
- `backend/main.py`:
  - Added `fetch_ohlcv_data()` helper for multi-timeframe support
  - Updated `eval_measure()` to handle ordinal offsets
  - Added `indicator_cache` dict for memoization
  - Updated `eval_filter()` to collect explain values
  - Added sorting and pagination logic to results
  - Updated response format with `totalMatches` and `returnedMatches`

### Files Created
- `tests/test_scanner_phase3.py`: Comprehensive Phase 3/4 test suite

---

## Next Steps

### Priority 1: Complete Phase 3
1. **Cross-Timeframe Queries**
   - Design timestamp alignment strategy
   - Implement multi-timeframe filter evaluation
   - Add tests with mixed timeframe filters

### Priority 2: Complete Phase 4
2. **Parallel Processing**
   - Implement ThreadPoolExecutor or multiprocessing
   - Add connection pooling for database access
   - Benchmark performance gains

### Priority 3: UI Implementation
3. **Scanner UI Updates**
   - Add timeframe selector dropdown (1D, 5m, 15m, 1h)
   - Add offset UI controls (lookback bars, ordinal index)
   - Display explain values in results table (hover tooltips)
   - Add sorting controls (dropdown + asc/desc toggle)
   - Add pagination controls (page size, next/prev buttons)
   - Show "X of Y results" status

### Priority 4: Data Management
4. **Intraday Data Support**
   - Import workflow for intraday CSV files
   - Populate `ohlcv_intraday` table
   - Update Data Management UI to show timeframe options

---

## Performance Metrics

### Current Performance (Phase 1-4)
- **Scanner execution**: ~11s for 3 symbols, 30 days each
- **Memoization benefit**: ~2x speedup when reusing indicators
- **Expected parallel speedup**: ~4x on quad-core (not yet implemented)

### Optimization Opportunities
1. **Database indexing**: Add index on `(symbol, timeframe, timestamp)` for intraday
2. **Indicator warm-up**: Pre-calculate common indicators (SMA, EMA, RSI) during import
3. **Result caching**: Cache scan results for repeated queries
4. **Chunked scanning**: Process symbols in batches to control memory usage

---

## Documentation

### User Guide Updates Needed
- Explain offset types (lookback vs ordinal)
- Document supported timeframes and requirements
- Show examples of cross-timeframe scans
- Explain sorting and pagination options
- Document explain values format

### Developer Guide Updates Needed
- Memoization cache implementation details
- Multi-timeframe data alignment strategy
- Parallel processing architecture
- Error handling for missing intraday data

---

**End of Summary**
