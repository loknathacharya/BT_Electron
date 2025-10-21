# Quick Start: Using Saved Symbol Lists in Scanner

## Step-by-Step User Guide

### Prerequisites
- Symbol lists already created in Data Management → Symbol Lists tab
- Datasets already uploaded in Data Management tab

### Running a Scan with Saved Symbol List

1. **Navigate to Scanner Tab**
   - Click "Scanner" in the main navigation

2. **Set Universe Mode to "Saved list"**
   - In the Universe section, select "Saved list" from the dropdown
   - Two new dropdowns will appear:
     - Dataset selector
     - Saved Symbol List selector

3. **Select Dataset**
   - Click the "Dataset" dropdown
   - Choose the dataset that contains your symbol list
   - The list will load the available symbol lists for that dataset

4. **Select Symbol List**
   - Click the "Saved Symbol List" dropdown
   - Choose from the available lists
   - Each list shows the number of symbols in parentheses
   - If available, the list description appears below

5. **Configure Scan Parameters**
   - Set timeframe (1D, 1h, 15m, 5m)
   - Configure filter rules using Scanner Builder or DSL
   - Adjust advanced options (max symbols, date range, etc.)

6. **Run Scan**
   - Click "Run Scan" button
   - Scanner will execute against all symbols in the selected list
   - Results will appear below

## Features

### Dataset Selector
- Auto-populated with all available datasets
- Appears only when "Saved list" universe mode is selected
- Clicking the dataset resets the symbol list selection

### Saved Symbol List Dropdown
- Shows all symbol lists for the selected dataset
- Displays symbol count for each list (e.g., "Portfolio (25 symbols)")
- Shows list description if provided
- Enables only after selecting a dataset

### Error Handling
- Dataset dropdown disabled while loading
- Symbol list dropdown disabled while:
  - No dataset is selected
  - Lists are still loading
- Graceful error messages if backend request fails

## Integration with Other Features

### With Scanner Builder
- Use "Saved list" mode with Scanner Builder for visual rule creation
- All builder features work normally with saved lists

### With DSL Mode
- Use "Saved list" with DSL for text-based rule definition
- Universe specification automatically uses selected list symbols

### Export Results
- Results from saved list scans can be exported like any other scan
- Symbol column shows which symbols were included in scan

## Troubleshooting

### Datasets Not Appearing
- Check if datasets are properly loaded in Data Management
- Refresh browser to reload datasets
- Look in browser console for error messages

### Symbol Lists Not Appearing
- Verify dataset is selected (dropdown must have a value)
- Check that symbol lists exist for the selected dataset
- Create symbol lists in Data Management → Symbol Lists tab

### Scan Fails with Symbol List
- Verify selected symbol list has valid symbols for the dataset
- Check that price data exists for symbols in the list
- Review error message in results section

## Related Documentation

- **Creating Symbol Lists:** See Data Management section
- **Scanner Basics:** See Scanner tab documentation
- **Symbol List API:** See developer documentation for integration

## Developer Notes

### IPC Channels Used
- `get-all-datasets` - Fetches all available datasets
- `get-symbol-lists` - Fetches symbol lists for dataset (from useSymbolLists hook)
- `run-scan` - Executes scan with selected symbols

### Component Flow
```
Scanner Component
├─ Datasets fetched on mount
├─ User selects SAVED_LIST mode
├─ Datasets dropdown populated
├─ User selects dataset
├─ useSymbolLists hook fetches lists
├─ Symbol lists dropdown populated
├─ User selects list
└─ Scan executes with list symbols
```

### State Management
- `selectedDataset` - Currently selected dataset name
- `selectedSavedList` - Currently selected list name
- `datasets` - Array of available datasets
- `symbolLists` - Array of lists for selected dataset (from hook)

## Keyboard Shortcuts
- None currently implemented, but can be added

## Accessibility
- Dropdowns are properly labeled
- Disabled state indicated visually
- Keyboard navigable
- Error messages clear and descriptive
