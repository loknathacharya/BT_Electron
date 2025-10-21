# Symbol List Integration Guide

This guide shows how to integrate the Symbol List selector into Scanner, Backtest, Portfolio, and Walk-Forward tabs.

## Quick Integration Pattern

### Step 1: Import Dependencies

```typescript
import SymbolListSelector from './SymbolListSelector';
import { useState, useEffect } from 'react';
```

### Step 2: Add State Variables

```typescript
const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
const [selectedSymbolList, setSelectedSymbolList] = useState<string | null>(null);
const [filterSymbols, setFilterSymbols] = useState<string[]>([]);
```

### Step 3: Add SymbolListSelector Component

```tsx
<div className="controls-section">
  <h4>Data Source</h4>
  
  {/* Dataset Selector - You probably already have this */}
  <div className="form-group">
    <label>Dataset:</label>
    <select 
      value={selectedDataset || ''} 
      onChange={(e) => setSelectedDataset(e.target.value)}
    >
      <option value="">-- Select Dataset --</option>
      {datasets.map(ds => (
        <option key={ds.name} value={ds.name}>{ds.name}</option>
      ))}
    </select>
  </div>

  {/* NEW: Symbol List Selector */}
  <SymbolListSelector
    datasetName={selectedDataset}
    selectedList={selectedSymbolList}
    onListSelect={(listName, symbols) => {
      setSelectedSymbolList(listName);
      setFilterSymbols(symbols);
    }}
    label="Symbol Filter"
    showAllOption={true}
  />
</div>
```

### Step 4: Use the Selected Symbols

The `filterSymbols` array will contain:
- Empty array `[]` when "All Symbols" is selected
- Array of symbols `['AAPL', 'GOOGL', ...]` when a list is selected

**Example usage in Scanner:**

```typescript
const runScan = async () => {
  const payload = {
    dataset_name: selectedDataset,
    universe: filterSymbols.length > 0 ? filterSymbols : 'ALL',
    scan_spec: scanSpec,
    // ... other scan parameters
  };

  const result = await window.electronAPI.invoke('run-scan', payload);
  // Process results...
};
```

**Example usage in Backtest:**

```typescript
const runBacktest = async () => {
  // If symbol list is selected, run backtest for each symbol
  const symbolsToTest = filterSymbols.length > 0 
    ? filterSymbols 
    : await getAllSymbolsFromDataset(selectedDataset);

  for (const symbol of symbolsToTest) {
    const result = await window.electronAPI.invoke('run-backtest', {
      dataset_name: selectedDataset,
      symbol: symbol,
      strategy: selectedStrategy,
      // ... other parameters
    });
    // Process results...
  }
};
```

**Example usage in Portfolio:**

```typescript
const runPortfolioBacktest = async () => {
  const payload = {
    dataset_name: selectedDataset,
    symbols: filterSymbols.length > 0 ? filterSymbols : 'ALL',
    strategy: selectedStrategy,
    // ... other portfolio parameters
  };

  const result = await window.electronAPI.invoke('run-portfolio-backtest', payload);
  // Process results...
};
```

---

## Component-Specific Integration Examples

### Scanner Integration

File: `src/components/Scanner.tsx`

```typescript
// Add near top of component
const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
const [selectedSymbolList, setSelectedSymbolList] = useState<string | null>(null);
const [filterSymbols, setFilterSymbols] = useState<string[]>([]);

// In the JSX, add before or after timeframe selection
<div className="form-group">
  <label>Dataset:</label>
  <select 
    value={selectedDataset || ''} 
    onChange={(e) => setSelectedDataset(e.target.value)}
  >
    <option value="">Select Dataset</option>
    {/* Load datasets from API */}
  </select>
</div>

<SymbolListSelector
  datasetName={selectedDataset}
  selectedList={selectedSymbolList}
  onListSelect={(listName, symbols) => {
    setSelectedSymbolList(listName);
    setFilterSymbols(symbols);
  }}
  label="Symbol List"
  showAllOption={true}
/>

// In handleRunScan function:
const handleRunScan = async () => {
  const payload = {
    dataset_name: selectedDataset,
    universe: filterSymbols.length > 0 ? filterSymbols : 'ALL',
    scan_spec: buildScanSpec(),
    timeframe: timeframe
  };

  const result = await window.electronAPI.invoke('run-scan', payload);
  // ... handle results
};
```

### Backtest Engine Integration

File: `src/components/BacktestEngine.tsx`

```typescript
// Add state
const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
const [selectedSymbolList, setSelectedSymbolList] = useState<string | null>(null);
const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);

// In JSX:
<div className="backtest-settings">
  <h3>Data Selection</h3>
  
  {/* Dataset selector */}
  <div className="form-group">
    <label>Dataset:</label>
    <select onChange={(e) => setSelectedDataset(e.target.value)}>
      {/* ... options */}
    </select>
  </div>

  {/* Symbol List selector */}
  <SymbolListSelector
    datasetName={selectedDataset}
    selectedList={selectedSymbolList}
    onListSelect={(listName, symbols) => {
      setSelectedSymbolList(listName);
      setSelectedSymbols(symbols);
    }}
    showAllOption={true}
  />
</div>

// When running backtest:
const runBacktest = async () => {
  // Get symbols to test
  const symbolsToTest = selectedSymbols.length > 0 
    ? selectedSymbols 
    : await fetchAllSymbolsFromDataset(selectedDataset);

  // Run backtest for each symbol
  const results = [];
  for (const symbol of symbolsToTest) {
    const result = await window.electronAPI.invoke('run-backtest', {
      dataset_name: selectedDataset,
      symbol: symbol,
      strategy: strategySpec
    });
    results.push(result);
  }

  setBacktestResults(results);
};
```

### Portfolio Backtest Integration

File: `src/components/PortfolioBacktest.tsx`

```typescript
// Add state
const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
const [selectedSymbolList, setSelectedSymbolList] = useState<string | null>(null);
const [portfolioSymbols, setPortfolioSymbols] = useState<string[]>([]);

// In JSX:
<div className="portfolio-setup">
  <h3>Portfolio Configuration</h3>
  
  <SymbolListSelector
    datasetName={selectedDataset}
    selectedList={selectedSymbolList}
    onListSelect={(listName, symbols) => {
      setSelectedSymbolList(listName);
      setPortfolioSymbols(symbols);
    }}
    label="Portfolio Symbols"
    showAllOption={false}  // Require specific selection
  />
</div>

// When running portfolio backtest:
const runPortfolioBacktest = async () => {
  if (portfolioSymbols.length === 0) {
    alert('Please select a symbol list for the portfolio');
    return;
  }

  const result = await window.electronAPI.invoke('run-portfolio-backtest', {
    dataset_name: selectedDataset,
    symbols: portfolioSymbols,
    initial_capital: initialCapital,
    rebalance_frequency: rebalanceFreq,
    // ... other portfolio parameters
  });

  setPortfolioResults(result);
};
```

### Walk-Forward Analysis Integration

File: `src/components/WalkForwardAnalysis.tsx`

```typescript
// Add state
const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
const [selectedSymbolList, setSelectedSymbolList] = useState<string | null>(null);
const [optimizationSymbols, setOptimizationSymbols] = useState<string[]>([]);

// In JSX:
<div className="walk-forward-setup">
  <h3>Optimization Setup</h3>
  
  <SymbolListSelector
    datasetName={selectedDataset}
    selectedList={selectedSymbolList}
    onListSelect={(listName, symbols) => {
      setSelectedSymbolList(listName);
      setOptimizationSymbols(symbols);
    }}
    label="Symbols to Optimize"
    showAllOption={true}
  />
</div>

// When running walk-forward:
const runWalkForward = async () => {
  const result = await window.electronAPI.invoke('run-walk-forward', {
    dataset_name: selectedDataset,
    symbols: optimizationSymbols.length > 0 ? optimizationSymbols : 'ALL',
    in_sample_period: inSamplePeriod,
    out_sample_period: outSamplePeriod,
    // ... other parameters
  });

  setWalkForwardResults(result);
};
```

---

## Best Practices

### 1. Always Check Dataset Selection

```typescript
if (!selectedDataset) {
  alert('Please select a dataset first');
  return;
}
```

### 2. Handle "All Symbols" vs Specific List

```typescript
const symbolsToUse = filterSymbols.length > 0 ? filterSymbols : 'ALL';
```

### 3. Provide User Feedback

```typescript
if (selectedSymbolList) {
  console.log(`Using symbol list: ${selectedSymbolList} with ${filterSymbols.length} symbols`);
}
```

### 4. Disable Actions When No Dataset

```typescript
<button 
  onClick={runScan}
  disabled={!selectedDataset}
>
  Run Scan
</button>
```

### 5. Show Symbol Count

```typescript
{selectedSymbolList && filterSymbols.length > 0 && (
  <div className="info">
    Testing {filterSymbols.length} symbols from "{selectedSymbolList}"
  </div>
)}
```

---

## Common Patterns

### Pattern 1: Dataset + Symbol List + Action

```tsx
<div className="controls">
  <DatasetSelector 
    value={selectedDataset}
    onChange={setSelectedDataset}
  />
  
  <SymbolListSelector
    datasetName={selectedDataset}
    selectedList={selectedSymbolList}
    onListSelect={(name, symbols) => {
      setSelectedSymbolList(name);
      setSymbols(symbols);
    }}
  />
  
  <button 
    onClick={handleAction}
    disabled={!selectedDataset}
  >
    Run Action
  </button>
</div>
```

### Pattern 2: Symbol List with Preview

```tsx
<div>
  <SymbolListSelector
    datasetName={selectedDataset}
    selectedList={selectedSymbolList}
    onListSelect={(name, symbols) => {
      setSelectedSymbolList(name);
      setSymbols(symbols);
    }}
  />
  
  {symbols.length > 0 && (
    <div className="symbol-preview">
      <strong>Selected Symbols ({symbols.length}):</strong>
      <div className="symbol-chips">
        {symbols.slice(0, 10).map(sym => (
          <span key={sym} className="chip">{sym}</span>
        ))}
        {symbols.length > 10 && <span>+{symbols.length - 10} more</span>}
      </div>
    </div>
  )}
</div>
```

### Pattern 3: Multi-Selection Support

```tsx
// For advanced use cases where you want multiple lists
const [selectedLists, setSelectedLists] = useState<string[]>([]);
const [combinedSymbols, setCombinedSymbols] = useState<string[]>([]);

// Combine symbols from multiple lists
useEffect(() => {
  const allSymbols = selectedLists.flatMap(listName => {
    return getSymbolsByListName(listName);
  });
  const uniqueSymbols = [...new Set(allSymbols)];
  setCombinedSymbols(uniqueSymbols);
}, [selectedLists]);
```

---

## Testing Your Integration

### Checklist

- [ ] Symbol list selector appears in your tab
- [ ] Selector is disabled when no dataset selected
- [ ] Selector loads lists when dataset is selected
- [ ] "All Symbols" option works
- [ ] Selecting a list populates the symbols array
- [ ] Your action uses the selected symbols correctly
- [ ] Error handling works (no dataset, no list, etc.)
- [ ] UI feedback shows selected list and symbol count

### Test Scenarios

1. **No dataset selected** - Selector should be disabled
2. **Dataset with no lists** - Shows "No lists" message
3. **Dataset with lists** - All lists appear in dropdown
4. **Select "All Symbols"** - Symbols array is empty
5. **Select specific list** - Symbols array populated
6. **Run action with list** - Verifies symbols are used
7. **Switch datasets** - Lists update correctly

---

## Troubleshooting

**Problem:** SymbolListSelector not showing
- Check import path
- Verify component is rendered inside your JSX
- Check if datasetName prop is passed

**Problem:** No lists appear in dropdown
- Verify dataset is selected
- Check if lists exist for that dataset in DB
- Open console and look for errors

**Problem:** Symbols array is empty when list selected
- Check onListSelect callback is set correctly
- Verify state update is happening
- Console.log the symbols parameter in onListSelect

**Problem:** Action not using selected symbols
- Ensure you're reading from the correct state variable
- Check if you're handling the "All Symbols" case
- Verify the API call includes the symbols

---

## Example: Complete Scanner Integration

Here's a complete example showing full integration:

```typescript
import React, { useState, useEffect } from 'react';
import SymbolListSelector from './SymbolListSelector';

const Scanner: React.FC = () => {
  // State
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [selectedSymbolList, setSelectedSymbolList] = useState<string | null>(null);
  const [filterSymbols, setFilterSymbols] = useState<string[]>([]);
  const [scanResults, setScanResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch datasets on mount
  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    const result = await window.electronAPI.invoke('get-datasets', {});
    if (!result.error) {
      setDatasets(result.datasets || []);
    }
  };

  const runScan = async () => {
    if (!selectedDataset) {
      alert('Please select a dataset');
      return;
    }

    setLoading(true);

    try {
      const result = await window.electronAPI.invoke('run-scan', {
        dataset_name: selectedDataset,
        universe: filterSymbols.length > 0 ? filterSymbols : 'ALL',
        scan_spec: {
          // Your scan specification
        }
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setScanResults(result.results || []);
    } catch (err) {
      console.error('Scan error:', err);
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="scanner">
      <h2>Scanner</h2>

      <div className="scanner-controls">
        {/* Dataset Selection */}
        <div className="form-group">
          <label>Dataset:</label>
          <select
            value={selectedDataset || ''}
            onChange={(e) => setSelectedDataset(e.target.value)}
          >
            <option value="">-- Select Dataset --</option>
            {datasets.map(ds => (
              <option key={ds.name} value={ds.name}>{ds.name}</option>
            ))}
          </select>
        </div>

        {/* Symbol List Selection */}
        <SymbolListSelector
          datasetName={selectedDataset}
          selectedList={selectedSymbolList}
          onListSelect={(listName, symbols) => {
            setSelectedSymbolList(listName);
            setFilterSymbols(symbols);
          }}
          label="Symbol Filter"
          showAllOption={true}
        />

        {/* Info Display */}
        {selectedSymbolList && filterSymbols.length > 0 && (
          <div className="info-box">
            Using symbol list "{selectedSymbolList}" with {filterSymbols.length} symbols
          </div>
        )}

        {/* Run Button */}
        <button
          onClick={runScan}
          disabled={!selectedDataset || loading}
          className="btn btn-primary"
        >
          {loading ? 'Scanning...' : 'Run Scan'}
        </button>
      </div>

      {/* Results */}
      {scanResults.length > 0 && (
        <div className="results">
          <h3>Scan Results ({scanResults.length})</h3>
          {/* Display results */}
        </div>
      )}
    </div>
  );
};

export default Scanner;
```

This integration is now ready to use!
