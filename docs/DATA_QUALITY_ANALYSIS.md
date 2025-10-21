# Data Quality Analysis Feature

## Overview
Comprehensive data quality analysis system that automatically runs after data import and provides detailed insights into data coverage, completeness, and integrity.

## Features

### 1. **Automatic Analysis After Import**
- Runs automatically when data is imported
- No additional clicks needed - results appear in import summary
- Analyzes single symbol or multiple symbols

### 2. **Data Quality Metrics**

#### Basic Information
- **Start Date**: Earliest timestamp in the dataset
- **End Date**: Latest timestamp in the dataset
- **Total Records**: Complete row count
- **Unique Dates**: Number of distinct dates with data
- **Days Span**: Calendar days between start and end
- **Data Coverage %**: (Unique Dates / Days Span) * 100

#### Quality Scores
- **Completeness Score**: Measures missing values in OHLCV fields (0-100%)
- **Integrity Score**: Detects logical errors (high < low, close outside range) (0-100%)
- **Overall Score**: Average of completeness and integrity scores
- **Quality Rating**: Excellent (95+), Good (85+), Fair (70+), Poor (<70)

#### Data Errors Detected
- Null/zero values in Open, High, Low, Close, Volume
- High < Low inversions
- Close prices outside High-Low range

### 3. **Missing Period Detection**

Identifies gaps in data larger than 5 days:
- Gap start and end dates
- Gap duration in days
- Last date before gap
- First date after gap
- Displayed visually in analysis

**Why 5 days?**
- Accounts for weekends and public holidays
- Typical trading is Mon-Fri (5 business days)
- Gaps > 5 days indicate possible data source issues

### 4. **Alternative Symbol Discovery**

For each missing period, the system:
1. Identifies other symbols that have data during that gap
2. Shows available records for each alternative
3. Displays coverage dates for each alternative
4. Suggests up to 5 best alternatives per gap

**Use Case**: When your primary symbol has gaps, check if related symbols are available for correlated analysis

### 5. **Data Analysis Page**

New dedicated page showing comprehensive analysis of all symbols:
- Sortable table with all key metrics
- Start/End date columns (no OHLCV details)
- Data coverage percentage
- Quality rating with color coding
- Missing gaps count
- Overall status indicator

**Navigation**: Data Management → Data Analysis (new tab)

## Data Structure

### Backend Analysis Result
```python
{
    'symbol': 'AAPL',
    'basic_info': {
        'start_date': '2023-01-01',
        'end_date': '2024-10-21',
        'total_records': 450,
        'unique_dates': 440,
        'days_span': 655
    },
    'quality_metrics': {
        'completeness_score': 95.5,
        'integrity_score': 98.2,
        'null_fields': {
            'open': 5, 'high': 2, 'low': 1, 'close': 0, 'volume': 10
        },
        'data_errors': {
            'high_low_reversed': 0,
            'close_outside_range': 1
        }
    },
    'missing_periods': [
        {
            'gap_start_date': '2023-06-15',
            'gap_end_date': '2023-06-25',
            'gap_days': 10,
            'date_before': '2023-06-14',
            'date_after': '2023-06-26'
        }
    ],
    'comparable_symbols': {
        'status': 'Found alternatives for 1/1 gaps',
        'comparable_gaps': [
            {
                'gap_period': {...},
                'alternative_symbols': [
                    {
                        'symbol': 'SPY',
                        'records_available': 10,
                        'coverage_start': '2023-06-15',
                        'coverage_end': '2023-06-25'
                    }
                ]
            }
        ]
    },
    'summary': {
        'overall_score': 96.85,
        'quality_rating': 'Excellent',
        'status': '✓',
        'data_coverage': '440 / 655 days',
        'coverage_percentage': 67.2,
        'missing_gaps_count': 1,
        'recommendation': '✓ Data quality is acceptable for backtesting'
    }
}
```

## UI Components

### Import Summary Display
Shows data quality immediately after import:
- Data Coverage section (start/end dates, record counts)
- Quality Metrics (scores with percentages)
- Missing Periods (if any gaps detected)
- Alternative Symbols (suggestions for gaps)
- Recommendation text

### Data Analysis Page
Comprehensive dashboard showing:
- Summary cards: Total symbols, total records, avg quality, gaps found
- Sortable data table with all metrics
- Color-coded ratings (green=good, yellow=warning, red=poor)
- Click any symbol for detailed analysis
- Refresh button to re-run analysis

## Workflow

### After Data Import
1. User imports data file
2. Data is validated and inserted into database
3. **Automatic**: Data quality analyzer runs
4. Results displayed in import success panel
5. User can review issues immediately

### On Data Analysis Page
1. User clicks "Data Analysis" tab
2. System fetches and analyzes all symbols
3. Results displayed in sortable table
4. User can click any symbol for detailed breakdown
5. Identifies all symbols with data issues
6. Shows alternative symbols for gaps

## Technical Implementation

### Files Added/Modified

1. **backend/data_quality_analyzer.py** (NEW)
   - `DataQualityAnalyzer` class
   - `analyze_symbol()`: Single symbol analysis
   - `analyze_all_symbols()`: Batch analysis
   - Missing period detection
   - Alternative symbol discovery
   - Quality scoring algorithms

2. **backend/main.py** (MODIFIED)
   - Import: `DataQualityAnalyzer`
   - Added `analyze-data-quality` handler
   - Integrated into import workflow

3. **src/components/ImportData.tsx** (MODIFIED)
   - Added data quality summary panel
   - Displays after successful import
   - Shows all metrics and recommendations

4. **src/components/DataAnalysis.tsx** (NEW)
   - Comprehensive analysis dashboard
   - Sortable table with all symbols
   - Summary statistics cards
   - Color-coded quality indicators

5. **src/App.tsx** (MODIFIED)
   - Added `/data-analysis` route
   - Added "Data Analysis" nav tab
   - Imported `DataAnalysis` component

### Database Queries
Uses existing `price_data` table:
- `MIN/MAX(timestamp)`: Date range
- `COUNT(DISTINCT DATE(...))`: Unique dates
- Null count aggregation
- Data validation checks

## Recommendations

### Data Quality Thresholds
- **Excellent**: Score ≥ 95%
- **Good**: Score ≥ 85%
- **Fair**: Score ≥ 70%
- **Poor**: Score < 70%

### When to Use Alternative Symbols
- Coverage < 80% indicates significant gaps
- Use alternatives for correlation/hedge analysis
- Don't use different symbols for primary trading strategy

### Addressing Data Issues

**High null counts:**
- Re-import with correct column mapping
- Check data source for availability

**High integrity errors:**
- Validate data source
- Check for data corruption
- Consider alternative source

**Large gaps (> 5 days):**
- Verify symbol trading status
- Check for halts or delisting
- Consider alternative symbols

## API Reference

### Backend Handler
```
Action: 'analyze-data-quality'
Request:
{
    'data': {
        'symbols': ['AAPL', 'MSFT']  // optional, all if omitted
    }
}
Response:
{
    'success': true,
    'results': [analysis1, analysis2, ...],
    'requestId': '...'
}
```

### React Hook Usage
```typescript
const result = await window.electronAPI.invoke('analyze-data-quality', {
    symbols: ['AAPL']  // optional
});
```

## Performance Considerations

- Analysis is efficient for large datasets
- Typical 100k records: < 1 second per symbol
- Batch processing of multiple symbols
- Results cached during session

## Future Enhancements

- Trend analysis for data quality over time
- Automated alerts for data degradation
- Export analysis reports (PDF/CSV)
- Custom gap threshold configuration
- Integration with portfolio backtesting
- Predictive analysis of future data quality
