# Cross-Timeframe Query Support

## Overview

The scanner now supports mixing different timeframes in a single scan. You can compare daily data with hourly indicators, or use any combination of supported timeframes.

## Supported Timeframes

- **1D** - Daily data
- **1H** (or **1HOUR**) - Hourly data
- **15M** - 15-minute data  
- **5M** - 5-minute data

## Implementation

### Per-Node Timeframe Property

Any measure node in the scanner AST can now include an optional `timeframe` property:

```json
{
  "type": "attr",
  "name": "close",
  "timeframe": "1h"
}
```

### Cross-Timeframe Evaluation

When `eval_measure` encounters a node with a different timeframe than the main scan timeframe, it:

1. Fetches OHLCV data for that specific timeframe
2. Evaluates the measure against the cross-timeframe data
3. Returns the result aligned with the original dataframe's index

### Example Scans

#### Daily vs Hourly SMA

Compare daily close price with hourly 20-period SMA:

```json
{
  "timeframe": "1D",
  "symbols": ["AAPL", "MSFT"],
  "filters": [
    {
      "op": "compare",
      "cmp": ">",
      "left": {
        "type": "attr",
        "name": "close",
        "timeframe": "1D"
      },
      "right": {
        "type": "indicator",
        "name": "SMA",
        "timeframe": "1h",
        "params": {
          "src": {"type": "attr", "name": "close"},
          "period": 20
        }
      }
    }
  ]
}
```

#### Multi-Timeframe Trend Check

Check if both daily and hourly are above their respective SMAs:

```json
{
  "timeframe": "1D",
  "symbols": ["SPY"],
  "filters": [
    {
      "op": "logical",
      "logic": "AND",
      "children": [
        {
          "op": "compare",
          "cmp": ">",
          "left": {"type": "attr", "name": "close", "timeframe": "1D"},
          "right": {
            "type": "indicator",
            "name": "SMA",
            "timeframe": "1D",
            "params": {"period": 50}
          }
        },
        {
          "op": "compare",
          "cmp": ">",
          "left": {"type": "attr", "name": "close", "timeframe": "1h"},
          "right": {
            "type": "indicator",
            "name": "SMA",
            "timeframe": "1h",
            "params": {"period": 20}
          }
        }
      ]
    }
  ]
}
```

## Technical Details

### Database Schema

- **Daily data**: Stored in `price_data` table
- **Intraday data**: Stored in `ohlcv_intraday` table with `timeframe` column

### Function Signatures

```python
def eval_measure(node, df: pd.DataFrame, symbol: str = '', main_timeframe: str = '') -> pd.Series:
    """
    Evaluate a measure node, potentially fetching cross-timeframe data
    
    Args:
        node: Measure AST node (can include 'timeframe' property)
        df: Main scan dataframe
        symbol: Symbol being evaluated
        main_timeframe: Main scan timeframe (e.g., '1D')
    
    Returns:
        pd.Series: Evaluated measure values
    """
```

```python
def eval_filter(node, df: pd.DataFrame, symbol: str = '', 
                explain_values: dict | None = None, 
                main_timeframe: str = '1D') -> bool:
    """
    Evaluate a filter node with cross-timeframe support
    
    Args:
        node: Filter AST node
        df: Main scan dataframe
        symbol: Symbol being evaluated
        explain_values: Optional dict to collect explain values
        main_timeframe: Main scan timeframe (e.g., '1D')
    
    Returns:
        bool: Filter evaluation result
    """
```

### Recursive Call Propagation

The `main_timeframe` parameter is propagated through all recursive calls:

- `eval_measure` → `eval_measure` (for indicators, functions, nested measures)
- `eval_filter` → `eval_measure` (for compare, crossover operations)
- `eval_filter` → `eval_filter` (for logical AND/OR/NOT operations)

### Optimization

When a node's timeframe matches the main scan timeframe, no additional data fetching occurs - the original dataframe is used directly.

## Performance Considerations

- **Thread Safety**: Each parallel worker thread gets its own database connection via `conn_override` parameter
- **Caching**: Indicator results are still cached per-symbol to avoid redundant calculations
- **Data Alignment**: Cross-timeframe data is automatically aligned to the main dataframe's datetime index

## Testing

The feature is tested via:
- Existing Phase 3 test suite (no regressions)
- Manual testing with real market data
- Integration testing with parallel processing

## Next Steps

Potential enhancements:
- Add alignment options (forward-fill, backward-fill, interpolate)
- Support custom timeframe aggregations
- Add cross-timeframe pattern detection
- Optimize data fetching with bulk queries
