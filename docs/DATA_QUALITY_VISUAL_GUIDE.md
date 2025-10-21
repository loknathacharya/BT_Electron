# Data Quality Analysis - Feature Overview

## 🎯 What You Get

### After Data Import
```
✓ Import Completed Successfully

📊 Dataset: My Trading Data
   Rows Imported: 450 | Rows Skipped: 2 | Time: 2.3s

📊 Data Quality Analysis
   ├─ Data Coverage
   │  ├─ Start Date: 2023-01-01
   │  ├─ End Date: 2024-10-21
   │  ├─ Total Records: 450
   │  └─ Data Points: 440 / 655 days
   │
   ├─ Quality Metrics
   │  ├─ Completeness: 95.5%
   │  ├─ Integrity: 98.2%
   │  └─ Overall Score: 96.85% - EXCELLENT
   │
   ├─ ⚠️ Missing Data Periods (1)
   │  └─ 2023-06-15 to 2023-06-25 (10 days)
   │     Last data: 2023-06-14 | Resume: 2023-06-26
   │
   ├─ ✓ Alternative Symbols Available
   │  └─ Gap: 2023-06-15 to 2023-06-25 (10 days)
   │     • SPY: 10 records available
   │     • IVV: 10 records available
   │     +1 more symbols
   │
   └─ Coverage: 440 / 655 days (67.2%)
      ✓ Data quality is acceptable for backtesting
```

### Data Analysis Page
```
📊 Data Quality Analysis Dashboard

┌─ Summary Cards ─────────────────────────────┐
│ Total Symbols: 5    │ Total Records: 2,250  │
│ Avg Quality: 92%    │ Symbols with Gaps: 2  │
└─────────────────────────────────────────────┘

┌─ Symbol Analysis Table ─────────────────────────────────────────────────┐
│ ⇅ Symbol │ Start Date  │ End Date    │ Records │ Data Pts   │ Coverage │
├──────────┼─────────────┼─────────────┼─────────┼────────────┼──────────┤
│   AAPL   │ 2023-01-01  │ 2024-10-21  │   450   │ 440/655 📊 │ 67% 🟢   │
│   MSFT   │ 2023-03-15  │ 2024-10-21  │   420   │ 410/555 📊 │ 74% 🟢   │
│   GOOGL  │ 2023-01-01  │ 2024-10-18  │   435   │ 425/656 📊 │ 65% 🟡   │
│   AMZN   │ 2023-06-01  │ 2024-10-21  │   360   │ 340/478 📊 │ 71% 🟢   │
│   TSLA   │ 2023-01-01  │ 2024-10-16  │   390   │ 370/655 📊 │ 56% 🟡   │
└──────────┴─────────────┴─────────────┴─────────┴────────────┴──────────┘

│ Quality Score │ Rating    │ Gaps │ Status │
├───────────────┼───────────┼──────┼────────┤
│    96%   🟢    │ Excellent │  0   │  ✓    │
│    94%   🟢    │ Good      │  1   │  ⚠    │
│    89%   🟢    │ Good      │  2   │  ⚠⚠   │
│    92%   🟢    │ Excellent │  0   │  ✓    │
│    78%   🟡    │ Fair      │  3   │  ⚠⚠   │
└───────────────┴───────────┴──────┴────────┘
```

## 📊 Column Descriptions

| Column | Purpose | Format |
|--------|---------|--------|
| **Symbol** | Trading symbol identifier | Text (AAPL, MSFT) |
| **Start Date** | First date in dataset | YYYY-MM-DD |
| **End Date** | Last date in dataset | YYYY-MM-DD |
| **Total Records** | Complete row count | Number |
| **Data Points** | Coverage metric | "X / Y days" |
| **Coverage %** | Data availability percentage | Number with color |
| **Quality Score** | Completeness + Integrity | Percentage with color |
| **Quality Rating** | Human-readable score | Excellent/Good/Fair/Poor |
| **Gaps** | Count of gaps > 5 days | Number |
| **Status** | Quick visual indicator | ✓ ⚠ ⚠⚠ ✗ |

## 🎨 Color Coding Guide

```
Quality/Coverage Indicator Color Meaning
────────────────────────────────────────

🟢 GREEN        95%+ score or 80%+ coverage    EXCELLENT
🟢 GREEN (Alt)  85%+ score or 80%+ coverage    GOOD
🟡 YELLOW       70%+ score or 60%+ coverage    FAIR / WARNING
🟠 ORANGE       50%+ score or 60%+ coverage    POOR / CAUTION
🔴 RED          <50% score or <60% coverage    CRITICAL
```

## 📈 Quality Scoring Explained

### Completeness Score (0-100%)
Measures missing values in OHLCV fields:
```
Completeness = Average of:
├─ % rows with Open price
├─ % rows with High price
├─ % rows with Low price
├─ % rows with Close price
└─ % rows with Volume

Example: 4/5 fields at 100%, 1/5 at 90% = 96% score
```

### Integrity Score (0-100%)
Detects logical data errors:
```
Integrity = Average of:
├─ % rows where High >= Low (valid)
└─ % rows where Close is within High-Low (valid)

Example: 99% valid prices, 1 bad high-low = 99% score
```

### Overall Score
```
Overall = (Completeness + Integrity) / 2

Example: (96% + 99%) / 2 = 97.5% score
```

## 🔍 Missing Period Detection

### What Gets Reported
```
Gap Period: 2023-06-15 to 2023-06-25

Breakdown:
├─ Gap Start Date: 2023-06-15 (first missing day)
├─ Gap End Date: 2023-06-25 (last missing day)
├─ Gap Duration: 10 days
├─ Date Before: 2023-06-14 (last good data)
└─ Date After: 2023-06-26 (first data after gap)
```

### Why 5-Day Threshold?
```
Calendar Gaps:
├─ 1-2 days: Holiday or weekend (common)
├─ 3-4 days: Long weekend (expected)
├─ 5 days: End of week (typical trading week)
├─ 6-10 days: Extended holiday (notable)
└─ 10+ days: Trading halt or exchange closure (critical)

Reporting:
- Gaps ≤ 5 days: Ignored (expected business pattern)
- Gaps > 5 days: Reported (data source issue)
```

## 🔗 Alternative Symbols

### For Each Gap, Find:
1. **Other symbols** in the database
2. **With data** during the gap period
3. **Not the current symbol**
4. **Sorted by** record availability
5. **Limited to** top 5 alternatives

### Use Cases
```
If your primary symbol has a 10-day gap in Jun 2023:
├─ For correlation analysis: Use SPY, IVV, VOO
├─ For hedging: Use sector ETF alternatives
└─ For comparison: Benchmark against similar symbols
```

## 📋 Data Quality Recommendations

```
Your Data Quality Score        Recommendation
─────────────────────────────  ─────────────────────────────
95%+                           ✓ READY - Use for backtesting
85-94%                         ⚠ GOOD - Acceptable, review gaps
70-84%                         ⚠ FAIR - Address data issues
50-69%                         ⚠⚠ POOR - Investigate thoroughly
<50%                           ✗ CRITICAL - Do not use
```

## 🚀 Quick Start

### Step 1: Import Data
1. Click "Data Management" tab
2. Select data file
3. Map columns
4. Click "Import Data"
5. **→ Analysis runs automatically** ✓

### Step 2: Review Quality
- Read quality metrics in success panel
- Note any gaps reported
- Check alternative symbols
- Review recommendation

### Step 3: View Full Analysis
1. Click "Data Analysis" in navigation
2. See all symbols in table
3. Sort by any column
4. Identify issues
5. Click symbol for details

## 🎯 Use Cases

### Data Validation
```
Q: "Is my imported data good?"
A: ✓ Check quality score and rating immediately
```

### Gap Investigation
```
Q: "Why does my symbol have a gap?"
A: ✓ See exact gap dates and alternative symbols available
```

### Symbol Comparison
```
Q: "Which symbol has best coverage?"
A: ✓ Sort by Coverage % in Data Analysis table
```

### Quality Issues
```
Q: "Should I use this symbol?"
A: ✓ Check completeness and integrity scores
   ✓ Read recommendation text
```

### Data Augmentation
```
Q: "What symbol can cover my gaps?"
A: ✓ See alternative symbols with coverage dates
```

## 📊 Key Metrics Summary

```
Basic Information:
├─ Data range: Start Date to End Date
├─ Record count: Total rows imported
├─ Coverage: Unique dates / calendar days
└─ Percentage: (Unique dates / Days) * 100

Quality Metrics:
├─ Completeness: Missing values in OHLCV (0-100%)
├─ Integrity: Logical errors (0-100%)
├─ Overall: Combined score (0-100%)
└─ Rating: Excellent/Good/Fair/Poor

Data Issues:
├─ Missing periods: Gaps > 5 days
├─ Alternative symbols: Available during gaps
├─ Error count: Data validation failures
└─ Recommendations: Actionable guidance
```

---

**Next Steps:**
1. ✅ Import your data
2. ✅ Review quality summary
3. ✅ Visit Data Analysis page
4. ✅ Identify any issues
5. ✅ Use alternatives if needed
6. ✅ Begin backtesting!
