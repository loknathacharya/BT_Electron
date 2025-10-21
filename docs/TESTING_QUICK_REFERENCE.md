# Phase 2 Testing Quick Reference Card

## 🎯 What to Test

### Test 1: Component Rendering
```
Objective: Verify all new components display correctly
Steps:
1. Open the application
2. Click "Run Portfolio Backtest"
3. Verify configuration sections appear:
   - ✓ Position Sizing Selector
   - ✓ Signal Type Selector  
   - ✓ Risk Management Controls
4. Click each dropdown/selector
5. Verify UI updates without errors

Expected: All selectors render with proper styling
```

### Test 2: Configuration Changes
```
Objective: Verify state management works
Steps:
1. Select different position sizing methods
   - Equal Weight
   - Fixed Amount
   - Percent Risk
   - Volatility Target
   - ATR Based
   - Kelly Criterion
2. For each method, verify:
   - ✓ Parameters update
   - ✓ Descriptions change
   - ✓ No console errors
3. Toggle Long/Short signals
4. Adjust risk management settings

Expected: All changes reflected in state without errors
```

### Test 3: Backtest Execution
```
Objective: Verify IPC communication
Steps:
1. Configure backtest settings:
   - Choose symbols (AAPL, MSFT, etc.)
   - Set date range
   - Select scanner
2. Set phase 2 configurations:
   - Position sizing method
   - Signal type
   - Risk parameters
3. Click "Run Portfolio Backtest"
4. Wait for execution

Expected: 
- ✓ Progress indicator shows
- ✓ No errors in console
- ✓ Results load in < 30 seconds
```

### Test 4: Results Tab - Overview
```
Objective: Verify portfolio metrics
Steps:
1. Run a backtest (see Test 3)
2. Confirm you're on "Overview" tab
3. Verify these elements display:
   - Total trades count
   - Win rate percentage
   - Profit/loss in dollars
   - Monthly returns chart
   - Trade log table
   - Summary statistics

Expected: All metrics visible and correctly formatted
```

### Test 5: Results Tab - Invested Capital
```
Objective: Verify capital tracking
Steps:
1. Results loaded (see Test 3)
2. Click "📊 Invested Capital" tab
3. Verify these elements:
   - Summary cards (Initial, Avg, Peak, Current)
   - Stacked area chart showing capital allocation
   - Capital utilization percentage over time
   - Capital allocation breakdown table
   - Insights panel with recommendations

Expected: Chart renders smoothly with proper data
```

### Test 6: Results Tab - Trades
```
Objective: Verify trade log display
Steps:
1. Results loaded
2. Click "📝 Trades" tab
3. Verify trade log table shows:
   - Trade number
   - Symbol
   - Entry/Exit dates
   - Entry/Exit prices
   - P&L in dollars
   - P&L percentage
   - Exit reason
   - Holding period

Expected: All trade data displayed in sortable table
```

### Test 7: Results Tab - Analytics
```
Objective: Verify trade analytics visualizations
Steps:
1. Results loaded
2. Click "📊 Analytics" tab
3. Verify 4 charts render:
   - Exit Reason Pie Chart (take profit, stop loss, etc.)
   - Holding Period Histogram (days distribution)
   - P&L Distribution (histogram with green/red bars)
   - P&L Over Time Scatter (colored by profit/loss)
4. Hover over charts for tooltips
5. Verify statistics panel shows:
   - Win rate, Profit factor
   - Avg win/loss
   - Consecutive wins/losses

Expected: All 4 charts render with proper colors
```

### Test 8: Results Tab - Monte Carlo
```
Objective: Verify Monte Carlo simulation
Steps:
1. Results loaded with trades
2. Click "🎲 Monte Carlo" tab
3. Adjust simulation parameters:
   - Number of simulations (100-10000)
   - Number of trades (min-max available)
4. Click "Run Simulation"
5. Wait for calculation
6. Verify results display:
   - Distribution histogram
   - Percentile lines (5th, 50th, 95th)
   - Statistics: mean, median, std dev
   - Risk gauge
   - Probability metrics

Expected: Simulation completes and visualizes distribution
```

### Test 9: Results Tab - Leverage
```
Objective: Verify leverage analysis
Steps:
1. Results loaded
2. Click "⚖️ Leverage" tab
3. Verify these elements:
   - Leverage metrics cards (avg, max, high trades)
   - Distribution bar chart
   - Leverage vs performance scatter
   - Leverage timeline line chart
   - Risk assessment panel with color coding

Expected: All leverage visualizations display correctly
```

### Test 10: Tab Switching
```
Objective: Verify smooth tab navigation
Steps:
1. Results loaded
2. Rapidly click between tabs:
   - Overview → Analytics → Monte Carlo → Leverage
3. Verify no content overlap
4. Check console for errors
5. Verify tab buttons highlight correctly

Expected: Tabs switch smoothly without visual glitches
```

---

## 🔍 What to Look For (Common Issues)

### Visual Issues
- [ ] Tabs not highlighting when selected
- [ ] Charts rendering partially (cut off)
- [ ] Text overlapping
- [ ] Colors not showing correctly
- [ ] Responsive design broken on narrow screens

### Data Issues
- [ ] Empty charts (no data)
- [ ] NaN values showing
- [ ] Dates formatted incorrectly
- [ ] Numbers with wrong precision
- [ ] Missing trade symbols

### Performance Issues
- [ ] Slow tab switching (>1 second)
- [ ] Chart lag when scrolling
- [ ] Monte Carlo taking >10 seconds
- [ ] Memory usage increasing
- [ ] Unresponsive UI

### Console Errors
- [ ] Red error messages
- [ ] Yellow warnings
- [ ] Undefined variables
- [ ] Component prop warnings
- [ ] IPC communication errors

---

## ✅ Success Criteria

### Must Pass
- ✅ All 6 tabs render without JavaScript errors
- ✅ Data flows correctly through all components
- ✅ No NaN, null, or undefined values visible
- ✅ Charts render with proper colors
- ✅ IPC communication completes successfully
- ✅ State management works correctly
- ✅ Responsive design works on mobile

### Should Pass
- ✅ Performance acceptable (<2 seconds per operation)
- ✅ Responsive design looks good on all sizes
- ✅ Color contrast meets accessibility standards
- ✅ All tooltips work on hover

### Nice to Have
- ✅ Smooth animations on chart renders
- ✅ Loading indicators during long operations
- ✅ Export data functionality
- ✅ Keyboard shortcuts for tab switching

---

## 📊 Test Data Recommendations

### Small Dataset (Quick Testing)
```python
symbols = ['AAPL', 'MSFT']
start_date = '2024-01-01'
end_date = '2024-03-31'
```

### Medium Dataset (Full Testing)
```python
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
start_date = '2024-01-01'
end_date = '2024-06-30'
```

### Large Dataset (Stress Testing)
```python
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TESLA', 'FB', 'NFLX']
start_date = '2023-01-01'
end_date = '2024-09-30'
```

---

## 🐛 Known Limitations (Expected Behavior)

1. **Bundle Size Warning**
   - Main JS is 774KB (>500KB is warned)
   - This is normal for a full-featured app
   - Will optimize in Phase 2.1

2. **Monte Carlo Requires Trades**
   - Needs minimum 10 trades
   - Empty portfolio won't simulate
   - This is by design

3. **Leverage Tab Optional**
   - Only shows if leverage used in backtest
   - Empty if no leveraged positions
   - This is expected

4. **Invested Capital Tab Optional**
   - Only shows if data provided by backend
   - Backend must include investedCapitalTimeline
   - Check backend integration

---

## 🚀 Testing Checklist

- [ ] Component rendering test passed
- [ ] Configuration changes test passed
- [ ] Backtest execution test passed
- [ ] Overview tab test passed
- [ ] Invested Capital tab test passed
- [ ] Trades tab test passed
- [ ] Analytics tab test passed
- [ ] Monte Carlo tab test passed
- [ ] Leverage tab test passed
- [ ] Tab switching test passed
- [ ] No visual issues observed
- [ ] No data issues observed
- [ ] No performance issues observed
- [ ] No console errors
- [ ] Responsive design working
- [ ] Accessibility acceptable

---

## 📞 Support

If issues arise:

1. **Check Console** (F12 → Console tab)
   - Look for red error messages
   - Copy exact error text
   - Note which tab triggered it

2. **Reload Application**
   - Hard refresh (Ctrl+Shift+R)
   - Clear browser cache
   - Restart Electron app

3. **Check Backend**
   - Verify Python backend running
   - Check for import errors
   - Verify data files accessible

4. **Review Logs**
   - Check electron logs
   - Check Python console output
   - Check IPC messages in DevTools

---

**Status:** Phase 2 Ready for Testing  
**Date:** October 20, 2025  
**Version:** 1.0.0
