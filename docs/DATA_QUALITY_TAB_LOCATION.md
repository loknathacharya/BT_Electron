# Data Management Navigation Structure

## Visual Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│  BYOD Strategy Backtesting                                      │
├─────────────────────────────────────────────────────────────────┤
│  [Data Management] [Scanner] [Backtest] [Portfolio] [etc...]    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                  ┌────────────────────┐
                  │ Data Management    │
                  │ (ViewResults.tsx)  │
                  └────────────────────┘
                            ↓
        ┌───────────────────────────────────────────┐
        │ Sub-Tabs within Data Management:          │
        ├───────────────────────────────────────────┤
        │ • 📦 Browse Datasets                      │
        │ • 📊 Data View                            │
        │ • 📊 Analysis                             │
        │ • ✓ Data Quality  ← NEW LOCATION         │
        └───────────────────────────────────────────┘
```

## Navigation Flow

### Old Structure (Before)
```
Top Navigation Bar
├── Data Management
│   ├── Browse Datasets
│   ├── Data View
│   └── Analysis
├── Data Analysis ← Separate Top-Level Item
├── Scanner
├── Backtest
├── Portfolio
├── Walk-Forward
└── Backup & Recovery
```

### New Structure (After)
```
Top Navigation Bar
├── Data Management
│   ├── Browse Datasets
│   ├── Data View
│   ├── Analysis
│   └── Data Quality ← Moved Here
├── Scanner
├── Backtest
├── Portfolio
├── Walk-Forward
└── Backup & Recovery
```

## Component Architecture

```
App.tsx
├── Navigation
│   └── navItems = [Data Management, Scanner, Backtest, ...]
└── Routes
    └── "/" → ViewResults.tsx
        ├── selectedMetric = 'browse-datasets' | 'data-view' | 'results-analysis' | 'data-quality'
        ├── Browse Datasets View
        ├── Data View Section
        │   ├── Symbol Selection
        │   ├── Candlestick Chart
        │   └── Data Table
        ├── Analysis Section
        │   ├── Price Movement Analysis
        │   └── Charts & Visualizations
        └── Data Quality Section ← NEW
            └── DataAnalysis.tsx
                ├── Summary Cards
                └── Sortable Table
                    ├── Symbol
                    ├── Start Date
                    ├── End Date
                    ├── Coverage %
                    ├── Quality Score
                    ├── Rating
                    ├── Gaps
                    └── Status
```

## Features Available in Data Quality Tab

The Data Quality tab now provides:

1. **Summary Cards**
   - Total Symbols
   - Total Records
   - Average Quality Score
   - Symbols with Gaps

2. **Sortable Data Table**
   - Click any column header to sort
   - Columns: Symbol, Start Date, End Date, Total Records, Data Points, Coverage %, Quality Score, Rating, Gaps, Status
   - Color-coded quality ratings:
     - 🟢 Green: ≥95% quality
     - 🟡 Yellow: ≥70% quality
     - 🟠 Orange: ≥50% quality
     - 🔴 Red: <50% quality

3. **Details on Click**
   - Click any row to expand and see detailed analysis
   - View missing periods and alternative symbols

4. **Refresh Functionality**
   - Refresh button to re-analyze all symbols
   - Automatic analysis after import

## Routing Changes

| Endpoint | Component | Status |
|----------|-----------|--------|
| `/` | ViewResults (Data Management) | ✅ Active |
| `/data-analysis` | ❌ Removed | Route removed, redirects to "/" |
| `/#/data-quality` | DataAnalysis (sub-tab) | ✅ New location |

## User Access Path

**Old Path:** Click "Data Analysis" in top navigation

**New Path:** 
1. Click "Data Management" in top navigation
2. Click "✓ Data Quality" tab button within Data Management

## Implementation Details

### Files Modified
- `src/App.tsx` - Removed DataAnalysis import and route
- `src/components/ViewResults.tsx` - Added DataAnalysis sub-tab

### Files Unchanged
- `src/components/DataAnalysis.tsx` - Works identically, just repositioned
- `backend/data_quality_analyzer.py` - No changes
- `src/components/ImportData.tsx` - Data quality summary still shown on import

## Benefits

✅ **Better UX Organization** - All data management features grouped together
✅ **Improved Discoverability** - Data quality tools visible alongside other data features
✅ **Cleaner Navigation** - Fewer top-level items, easier to navigate
✅ **Logical Grouping** - Data import, browse, view, and analyze all in one section
✅ **No Functionality Loss** - All data quality features work exactly as before

## Validation Checklist

- ✅ Data Quality tab appears in Data Management
- ✅ Tab can be clicked to show DataAnalysis component
- ✅ All quality metrics display correctly
- ✅ Table sorting works
- ✅ Quality summary cards show correct data
- ✅ Automatic analysis after import still works
- ✅ No errors in console
- ✅ TypeScript compilation passes
- ✅ Old `/data-analysis` route redirects to home
