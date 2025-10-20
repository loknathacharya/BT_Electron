# Testing Guide - Post-Consolidation

**Date**: October 20, 2025  
**Purpose**: Manual testing checklist for the completed consolidation

---

## Quick Start Test (5 minutes)

### 1. Check Navigation Bar
- [ ] Navigate to app home
- [ ] Verify 8 tabs display: Import Data, Scanner, Data Management, Backtest, Backtest Dev, Portfolio, Walk-Forward, Backup & Recovery
- [ ] Click each tab - verify page loads without errors

### 2. Test Production Backtest Mode
- [ ] Click "Backtest" tab
- [ ] Verify DSL input field is visible with default value: `SMA(close, 50) CROSSES_ABOVE SMA(close, 200)`
- [ ] Click "Run Backtest" button
- [ ] Verify backtest runs and results display
- [ ] No errors in console

### 3. Test Development Backtest Mode
- [ ] Click "Backtest Dev" tab
- [ ] Verify DSL input field is NOT visible (hidden)
- [ ] Verify results show detailed inline display (metrics, trades table)
- [ ] Click "Run Backtest" button
- [ ] Verify backtest runs with hardcoded spec
- [ ] No errors in console

---

## Comprehensive Testing Guide

### Section 1: Navigation (10 minutes)

#### Navigation Bar Display:
- [ ] 8 tabs visible (not 10)
- [ ] Tab labels correct:
  - [ ] Import Data
  - [ ] Scanner
  - [ ] Data Management (NOT "Results & Analysis")
  - [ ] Backtest
  - [ ] Backtest Dev
  - [ ] Portfolio
  - [ ] Walk-Forward
  - [ ] Backup & Recovery
- [ ] Active tab highlighted
- [ ] No visual glitches

#### Route Navigation:
- [ ] Click each tab in sequence - all load without errors
- [ ] Tab switching is smooth
- [ ] No console errors on tab changes
- [ ] Browser back button works correctly

#### Invalid Routes:
- [ ] Navigate to `/invalid-route` → redirects to home
- [ ] Navigate to `/strategy` (removed) → redirects to home
- [ ] Navigate to `/results` (removed) → redirects to home

---

### Section 2: Production Backtest Mode (15 minutes)

#### UI Elements:
- [ ] DSL input field visible and labeled "DSL"
- [ ] DSL textarea shows default: `SMA(close, 50) CROSSES_ABOVE SMA(close, 200)`
- [ ] Symbol field shows "TEST"
- [ ] Timeframe dropdown shows "1D"
- [ ] Mode dropdown defaults to "simulate"
- [ ] Date fields empty
- [ ] "Run Backtest" button visible and clickable

#### Configuration Section (appears when mode='simulate'):
- [ ] Configuration section appears when mode is "simulate"
- [ ] 6 config fields visible:
  - [ ] Initial Capital (default: 10000)
  - [ ] Position Size Mode (default: percent_capital)
  - [ ] Position Size Value (default: 100)
  - [ ] Stop Loss (default: 0)
  - [ ] Take Profit (default: 0)
  - [ ] Commission (default: 0)
- [ ] All fields editable

#### Running Backtest:
- [ ] Enter valid DSL: `SMA(close, 50) CROSSES_ABOVE SMA(close, 200)`
- [ ] Select symbol: TEST
- [ ] Select timeframe: 1D
- [ ] Click "Run Backtest"
- [ ] Loading indicator appears
- [ ] Results render successfully
- [ ] Results show BacktestResults component (professional formatting)

#### Validation:
- [ ] Clear DSL field and click Run → Error message: "DSL must not be empty"
- [ ] Enter very long DSL (>5000 chars) → Error: "DSL is too long"
- [ ] Clear symbol field → Error: "Symbol is required"
- [ ] Set From date > To date → Error: "From date must be..."
- [ ] Validation error box displays with red background
- [ ] "Run Backtest" button disabled when errors present

---

### Section 3: Development Backtest Mode (15 minutes)

#### UI Elements - DSL Hidden:
- [ ] Navigate to "Backtest Dev" tab
- [ ] DSL input field NOT visible
- [ ] Symbol field visible showing "TEST"
- [ ] Timeframe dropdown visible showing "1D"
- [ ] Mode dropdown defaults to "signals"
- [ ] Date fields visible and empty
- [ ] "Run Backtest" button visible

#### Configuration Section:
- [ ] Configuration section appears when mode='simulate'
- [ ] Default values pre-filled (different from production):
  - [ ] Stop Loss: 5 (not 0)
  - [ ] Take Profit: 10 (not 0)
  - [ ] Commission: 0.001 (not 0)
- [ ] Fields editable

#### Running Backtest - Signals Mode:
- [ ] Verify mode defaults to "signals"
- [ ] Click "Run Backtest"
- [ ] Results display inline (not BacktestResults component)
- [ ] Results show:
  - [ ] Signals section with count
  - [ ] Metrics section with key-value pairs
- [ ] No validation errors even with empty/default values

#### Running Backtest - Simulate Mode:
- [ ] Change mode to "simulate"
- [ ] Config section reappears with pre-filled values
- [ ] Click "Run Backtest"
- [ ] Results display inline detailed format
- [ ] Results include:
  - [ ] Metrics section
  - [ ] Trades table (scrollable if many trades)
    - [ ] Columns: Entry, Exit, Qty, Entry, Exit, PNL, PNL%, Reason
  - [ ] Equity curve preview (raw data display)

#### No Validation in Dev Mode:
- [ ] Clear symbol field → Still runs (no validation error)
- [ ] Leave all fields empty except symbol → Still runs
- [ ] Very long DSL-like text in symbol → Still runs
- [ ] No validation error box displayed

---

### Section 4: Feature Comparison (10 minutes)

#### Both Modes Share:
- [ ] Symbol selection
- [ ] Timeframe selection  
- [ ] Mode toggle (signals/simulate)
- [ ] Date range selection
- [ ] Configuration parameters
- [ ] Run backtest API call
- [ ] Error handling
- [ ] Loading states
- [ ] Console no errors

#### Production Only:
- [ ] DSL input field
- [ ] DSL parsing (parse-dsl API call)
- [ ] Validation logic
- [ ] Validation error display
- [ ] BacktestResults component

#### Development Only:
- [ ] Hardcoded sample spec (no input)
- [ ] Skipped validation
- [ ] Inline detailed results
- [ ] Trades table
- [ ] Raw metrics display

---

### Section 5: Data Management Tab (5 minutes)

#### After Consolidation:
- [ ] "Data Management" tab visible (NOT "Results & Analysis")
- [ ] Clicking it loads data browsing interface
- [ ] Shows same ViewResults component functionality
- [ ] All data browsing features work

#### Verify Removed:
- [ ] "Results & Analysis" tab NOT in navigation
- [ ] Trying to navigate to `/results` redirects to home
- [ ] No 404 errors

---

### Section 6: Error Scenarios (10 minutes)

#### Production Backtest Errors:
- [ ] Invalid DSL → Shows error message
- [ ] Symbol too long → Handles gracefully
- [ ] No backtest data → Shows appropriate error
- [ ] Network error → Shows "Failed to run backtest"

#### Development Backtest Errors:
- [ ] Invalid symbol → Still attempts to run (no validation)
- [ ] API error → Shows error message
- [ ] Network error → Shows "Failed to run backtest"

#### Navigation Errors:
- [ ] Invalid routes redirect properly
- [ ] Component switching doesn't break state
- [ ] Refresh on any tab works

---

### Section 7: Performance (5 minutes)

#### Load Times:
- [ ] App home loads in < 2 seconds
- [ ] Each tab loads in < 1 second
- [ ] Backtest runs in reasonable time (< 30 seconds for typical data)

#### No Console Errors:
- [ ] Open browser DevTools Console
- [ ] No red error messages
- [ ] No TypeScript compile errors
- [ ] No import/module resolution errors
- [ ] Only informational logs (if any)

#### Memory:
- [ ] Tab switching doesn't leak memory
- [ ] No performance degradation after multiple backtests
- [ ] Browser responsive

---

## Sign-Off Checklist

### Quick Test (5 min): 
- [ ] All 8 tabs present
- [ ] Backtest tab shows DSL input
- [ ] Backtest Dev tab hides DSL input
- [ ] Both run successfully
- [ ] No console errors

### Full Test (60 min):
- [ ] All sections above completed
- [ ] All checkboxes checked
- [ ] No unexpected errors
- [ ] User experience improved
- [ ] Ready to commit

---

## Known Limitations (None at this time)

Currently, no known issues or limitations. All consolidation complete.

---

## Rollback Procedure (if needed)

If critical issues found:

1. Stop the app
2. Copy from `.archive/`:
   - `cp .archive/BacktestBuilder.tsx.bak src/components/BacktestBuilder.tsx`
   - `cp .archive/BacktestDev.tsx.bak src/components/BacktestDev.tsx`
3. Revert App.tsx from git or restore previous version
4. Delete BacktestEngine.tsx
5. Restart app
6. Estimated time: < 5 minutes

---

## Success Criteria

✅ **TEST SUCCESSFUL IF:**
1. All 8 navigation tabs work
2. Production backtest shows DSL input and validation
3. Dev backtest hides DSL input and skips validation
4. Both backtests produce results
5. No console errors anywhere
6. No compilation errors
7. Removed tabs don't appear
8. Invalid routes redirect properly
9. Performance is acceptable
10. User experience feels improved

---

## Testing Environment

- **Browser**: Chrome/Firefox/Edge (latest)
- **Node Version**: v18+
- **React Version**: 18.2.0
- **TypeScript**: 4.9.3+
- **App Status**: Development build (npm run dev)

---

## Contact/Issues

If you find any issues during testing:
1. Note the exact steps to reproduce
2. Check console for errors
3. Check browser DevTools
4. Document browser/OS version
5. Report with screenshots if possible

---

*Testing Guide Created: October 20, 2025*  
*Last Updated: October 20, 2025*  
*Status: Ready for User Testing*
