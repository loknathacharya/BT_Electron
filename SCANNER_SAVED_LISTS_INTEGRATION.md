# Scanner Tab - Saved Symbol Lists Integration

## Overview
Integrated saved symbol lists into the Scanner tab's universe selector, allowing users to run scans against predefined symbol lists instead of manually typing them.

## Implementation Details

### Backend Changes (backend/main.py)
**Added Handler:** `get-all-datasets`
- Location: Line ~2293
- Purpose: Retrieves all available datasets from the market database
- Calls existing DatabaseService method: `get_all_datasets()`
- Returns: Dictionary with `success: true` and `datasets` array containing all datasets with their metadata

### Electron Bridge Changes (electron/main.ts)
**Added Handler:** `get-all-datasets`
- Location: Line ~815
- Purpose: Routes get-all-datasets requests from frontend to Python backend
- Includes error handling and logging
- Returns dataset information to Scanner component

### Preload Context Changes (electron/preload.ts)
**Updated validChannels:** Added `'get-all-datasets'` to whitelist
- Location: Line ~33 (in datasets section)
- Allows frontend to invoke the new IPC channel

### Frontend Changes (src/components/Scanner.tsx)

#### State Management
Added three new state variables:
- `selectedDataset`: Currently selected dataset name (string or null)
- `selectedSavedList`: Currently selected symbol list name (string)
- `datasets`: Array of available datasets (with metadata)
- `datasetsLoading`: Boolean flag for loading state

#### Universe Mode Support
Enhanced universeMode to support three modes:
1. **'ALL'**: Scans all available symbols (existing)
2. **'LIST'**: Scans manually entered comma-separated symbols (existing)
3. **'SAVED_LIST'**: Scans symbols from a selected saved list (NEW)

#### DSL Key Calculation
Updated `dslKey` useMemo to handle SAVED_LIST mode:
```typescript
if (universeMode === 'SAVED_LIST' && selectedSavedList) {
  const list = symbolLists.find(l => l.name === selectedSavedList);
  uni = list ? list.symbols : 'ALL';
}
```

#### Scanner Spec Logic
Updated `scannerSpec` useMemo to route to saved list symbols when SAVED_LIST mode is selected:
```typescript
} else if (universeMode === 'SAVED_LIST' && selectedSavedList && selectedDataset) {
  const list = symbolLists.find(l => l.name === selectedSavedList);
  uni = list ? list.symbols : [];
}
```

#### UI Components
**Universe Dropdown:** Added "Saved list" option when symbol lists are available
**Dataset Selector:** Shows when SAVED_LIST mode is selected
- Displays all available datasets
- Disables when loading
- Resets saved list selection when dataset changes

**Saved Symbol List Dropdown:** Shows when dataset is selected
- Populated via `useSymbolLists` hook
- Displays symbol count for each list
- Shows list description if available
- Disables when no dataset selected or lists are loading

#### Data Fetching
Updated useEffect to fetch datasets on component mount:
```typescript
useEffect(() => {
  const fetchDatasets = async () => {
    setDatasetsLoading(true);
    try {
      const result = await window.electronAPI.invoke('get-all-datasets', {});
      if (!result.error) {
        setDatasets(result.datasets || []);
      }
    } catch (err) {
      console.error('Error fetching datasets:', err);
    } finally {
      setDatasetsLoading(false);
    }
  };
  fetchDatasets();
}, []);
```

## User Workflow

1. **Select Universe Mode:** User clicks "Saved list" option in Universe dropdown
2. **Select Dataset:** User selects a dataset from the dataset selector
3. **Select Symbol List:** User selects a saved symbol list from the available lists
4. **Run Scan:** User configures scan parameters and runs scan
5. **Execution:** Scanner executes against symbols in the selected list

## Data Flow

```
Scanner Component
  ↓
  └─→ Fetch datasets on mount (get-all-datasets)
  └─→ User selects SAVED_LIST mode
  └─→ User selects dataset
  └─→ useSymbolLists hook fetches symbol lists for dataset
  └─→ User selects symbol list
  └─→ scannerSpec retrieves symbols from selected list
  └─→ Run scan with selected symbols
  └─→ Backend receives symbols and executes scan
```

## Integration Points

### useSymbolLists Hook
- Automatically fetches symbol lists when `selectedDataset` changes
- Returns: `symbolLists` array and `loading` state
- Used to populate the saved symbol list dropdown

### Dataset Selection
- Changes reset the selected saved list to empty
- Prevents invalid state where dataset and list don't match

### Symbol Retrieval
- Symbols are retrieved from the saved list object
- Applied to the universeMode='SAVED_LIST' branch in scannerSpec

## Testing Checklist

- [ ] Datasets load correctly on Scanner component mount
- [ ] Dataset dropdown shows all available datasets
- [ ] Selecting a dataset fetches its associated symbol lists
- [ ] Symbol list dropdown shows correct lists for selected dataset
- [ ] Scan executes with correct symbols from selected list
- [ ] Symbol count displays correctly in dropdown
- [ ] List description shows in UI when available
- [ ] Changing dataset resets symbol list selection
- [ ] Error handling works for network/backend failures

## Files Modified

1. **backend/main.py** - Added get-all-datasets handler
2. **electron/main.ts** - Added get-all-datasets IPC handler
3. **electron/preload.ts** - Added get-all-datasets to whitelist
4. **src/components/Scanner.tsx** - Integrated saved symbol lists UI and logic

## Build Status

✅ TypeScript compilation successful
✅ Vite build successful
✅ No errors or warnings related to these changes

## Dependencies

- `useSymbolLists` hook (existing, already imported)
- `window.electronAPI.invoke` for IPC communication
- Existing dataset and symbol list backend services

## Future Enhancements

- Add ability to create new symbol lists directly from Scanner
- Add quick filters/search for dataset and list selection
- Add symbol list preview tooltip on hover
- Add "Recent symbol lists" quick access
- Integrate similar functionality into Backtest, Portfolio, Walkforward tabs
