# Phase 2 Components - Quick Reference Guide

## Configuration Components

### 1. PositionSizingSelector
**Purpose:** Allow users to select and configure position sizing method  
**File:** `src/components/PortfolioBacktest/PositionSizingSelector.tsx`

**Props:**
```typescript
interface PositionSizingSelectorProps {
  config: PositionSizingConfig;
  onChange: (config: PositionSizingConfig) => void;
  showAdvanced?: boolean;
}
```

**Methods Supported:**
- `equal_weight` - 2% of portfolio per position
- `fixed_amount` - Same dollar amount per trade
- `percent_risk` - Risk % based on stop-loss
- `volatility_target` - Size by instrument volatility
- `atr_based` - Size by Average True Range
- `kelly_criterion` - Optimal mathematical sizing

**Example Usage:**
```tsx
<PositionSizingSelector
  config={positionSizingConfig}
  onChange={setPositionSizingConfig}
/>
```

---

### 2. SignalTypeSelector
**Purpose:** Toggle between long and short signals  
**File:** `src/components/PortfolioBacktest/SignalTypeSelector.tsx`

**Props:**
```typescript
interface SignalTypeSelectorProps {
  signalType: 'long' | 'short';
  onChange: (type: 'long' | 'short') => void;
}
```

**Signal Types:**
- `long` - Buy and profit from price increase
- `short` - Sell and profit from price decrease

**Example Usage:**
```tsx
<SignalTypeSelector
  signalType={signalType}
  onChange={setSignalType}
/>
```

---

### 3. RiskManagementControls
**Purpose:** Configure risk management parameters  
**File:** `src/components/PortfolioBacktest/RiskManagementControls.tsx`

**Props:**
```typescript
interface RiskManagementControlsProps {
  config: RiskManagementConfig;
  onChange: (config: RiskManagementConfig) => void;
}
```

**Controls:**
- Stop-loss percentage
- Take-profit percentage
- Maximum holding period (days)
- Allow leverage toggle
- One trade per instrument option

**Example Usage:**
```tsx
<RiskManagementControls
  config={riskManagementConfig}
  onChange={setRiskManagementConfig}
/>
```

---

## Analytics Components

### 4. TradeAnalyticsDashboard
**Purpose:** Display comprehensive trade analysis with 4 charts  
**File:** `src/components/TradeAnalytics/TradeAnalyticsDashboard.tsx`

**Props:**
```typescript
interface TradeAnalyticsDashboardProps {
  analytics: TradeAnalytics;
  trades: Trade[];
}
```

**Charts Included:**
1. Exit Reason Pie Chart
2. Holding Period Histogram
3. P&L Distribution
4. P&L Over Time Scatter Plot

**Example Usage:**
```tsx
<TradeAnalyticsDashboard
  analytics={results.tradeAnalytics}
  trades={allTrades}
/>
```

---

### 5. MonteCarloSimulation
**Purpose:** Run and visualize Monte Carlo simulations  
**File:** `src/components/MonteCarloSimulation/MonteCarloSimulation.tsx`

**Props:**
```typescript
interface MonteCarloSimulationProps {
  trades: any[];
  initialCapital: number;
  onRunSimulation: (numSims: number, numTrades: number) => Promise<MonteCarloResults>;
}
```

**Features:**
- Adjustable number of simulations (100-10000)
- Adjustable number of trades (min-max)
- Distribution histogram with percentile lines
- Statistics panel (mean, median, std dev, percentiles)
- Risk assessment gauge
- Probability metrics

**Example Usage:**
```tsx
<MonteCarloSimulation
  trades={tradesList}
  initialCapital={10000}
  onRunSimulation={async (nSims, nTrades) => {
    const response = await window.electronAPI.invoke('run-monte-carlo', {
      trade_returns,
      n_simulations: nSims,
      n_trades: nTrades
    });
    return response;
  }}
/>
```

---

### 6. LeverageAnalysis
**Purpose:** Analyze leverage usage and its impact on performance  
**File:** `src/components/LeverageAnalysis/LeverageAnalysis.tsx`

**Props:**
```typescript
interface LeverageAnalysisProps {
  metrics: LeverageMetrics;
  leverageTimeline: Array<{date: string; leverage: number}>;
  leverageVsPerformance: Array<{leverage: number; pnlPct: number; symbol: string}>;
}
```

**Features:**
- Leverage metrics cards (avg, max, high trades count)
- Leverage distribution bar chart
- Leverage vs performance scatter plot
- Leverage timeline line chart
- Risk assessment with color-coded warnings

**Example Usage:**
```tsx
<LeverageAnalysis
  metrics={results.leverageMetrics}
  leverageTimeline={results.leverageTimeline}
  leverageVsPerformance={results.leverageVsPerformance}
/>
```

---

### 7. InvestedCapital
**Purpose:** Track and visualize capital allocation over time  
**File:** `src/components/InvestedCapital/InvestedCapital.tsx`

**Props:**
```typescript
interface InvestedCapitalProps {
  timeline: InvestedCapitalPoint[];
  initialCapital: number;
}
```

**Features:**
- Summary cards (initial, avg, peak, current)
- Stacked area chart (invested vs available)
- Utilization percentage timeline
- Capital allocation breakdown table
- Insights panel with recommendations

**Example Usage:**
```tsx
<InvestedCapital
  timeline={results.investedCapitalTimeline}
  initialCapital={backtestConfig.initial_capital}
/>
```

---

## Integration in PortfolioBacktest

### State Management
```typescript
// Configuration states
const [positionSizingConfig, setPositionSizingConfig] = useState({...});
const [signalType, setSignalType] = useState('long');
const [riskManagementConfig, setRiskManagementConfig] = useState({...});
const [activeResultsTab, setActiveResultsTab] = useState('overview');
```

### IPC Call Updated
```typescript
const payload = {
  scannerSpec,
  symbols,
  backtestConfig,
  portfolioConfig,
  positionSizingConfig,        // NEW
  signalType,                   // NEW
  riskManagementConfig          // NEW
};
const response = await window.electronAPI.invoke('run-portfolio-backtest', payload);
```

### Results Tab Structure
```typescript
<div className="results-tabs">
  <button onClick={() => setActiveResultsTab('overview')}>Overview</button>
  <button onClick={() => setActiveResultsTab('invested')}>Invested Capital</button>
  <button onClick={() => setActiveResultsTab('trades')}>Trades</button>
  <button onClick={() => setActiveResultsTab('analytics')}>Analytics</button>
  <button onClick={() => setActiveResultsTab('monte-carlo')}>Monte Carlo</button>
  <button onClick={() => setActiveResultsTab('leverage')}>Leverage</button>
</div>
```

---

## Data Types Reference

### PositionSizingConfig
```typescript
interface PositionSizingConfig {
  method: PositionSizingMethod;
  riskPerTrade?: number;        // For percent_risk (%)
  fixedAmount?: number;          // For fixed_amount ($)
  volatilityTarget?: number;     // For volatility_target
  atrMultiplier?: number;        // For atr_based
  kellyWinRate?: number;         // For kelly_criterion (%)
  kellyAvgWin?: number;          // For kelly_criterion (%)
  kellyAvgLoss?: number;         // For kelly_criterion (%)
}
```

### RiskManagementConfig
```typescript
interface RiskManagementConfig {
  allowLeverage: boolean;
  oneTradePerInstrument: boolean;
  stopLossPct: number | null;
  takeProfitPct: number | null;
  holdingPeriodDays: number | null;
  trailingStopPct?: number | null;
  maxDrawdownLimit?: number | null;
}
```

### TradeAnalytics
```typescript
interface TradeAnalytics {
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  averageWin: number;
  averageLoss: number;
  maxDrawdown: number;
  maxConsecutiveWins: number;
  maxConsecutiveLosses: number;
  exitReasons: Record<ExitReason, number>;
  holdingPeriods: number[];
  plDistribution: number[];
  plTimeline: Array<{...}>;
}
```

### MonteCarloResults
```typescript
interface MonteCarloResults {
  simulations: number[];
  percentile5: number;
  percentile50: number;
  percentile95: number;
  mean: number;
  std: number;
  probabilityProfit: number;
  probabilityLoss10: number;
  error?: string;
}
```

### LeverageMetrics
```typescript
interface LeverageMetrics {
  averageLeverage: number;
  maxLeverage: number;
  leverageDistribution: Record<string, number>;
  highLeverageTrades: number;
  leverageRiskScore: number;
}
```

### InvestedCapitalPoint
```typescript
interface InvestedCapitalPoint {
  date: string;
  investedValue: number;
  availableCash: number;
  totalValue: number;
  utilizationPct: number;
}
```

---

## Styling & CSS

### Color Scheme
- **Positive (Profit):** `#28a745` (Green)
- **Negative (Loss):** `#dc3545` (Red)
- **Neutral:** `#007bff` (Blue)
- **Warning:** `#ffc107` (Orange)
- **Background:** `#f8f9fa` (Light Gray)
- **Text:** `#1a1a2e` (Dark)
- **Border:** `#dee2e6` (Medium Gray)

### Responsive Breakpoints
- **Desktop:** > 1200px (Full layout)
- **Tablet:** 768px - 1200px (2-column grid)
- **Mobile:** < 768px (Stacked, single column)

### CSS Modules Used
- `PositionSizingSelector.css`
- `SignalTypeSelector.css`
- `RiskManagementControls.css`
- `TradeAnalyticsDashboard.css`
- `MonteCarloSimulation.css`
- `LeverageAnalysis.css`
- `InvestedCapital.css`

---

## Common Issues & Solutions

### Issue: Monte Carlo simulation shows "Insufficient Data"
**Solution:** Requires at least 10 trades. Run a backtest with more trades first.

### Issue: Charts not rendering
**Solution:** Check that the required data fields exist in the results object. Each component expects specific properties.

### Issue: Leverage tab shows "undefined"
**Solution:** Backend needs to return `leverageMetrics` object. Check that position_sizing is enabled.

### Issue: Invested Capital showing $0
**Solution:** Timeline data needs to be properly populated. Verify `investedCapitalTimeline` is included in results.

---

## Testing Checklist

- [ ] PositionSizingSelector renders all 6 methods
- [ ] Switching methods updates parameter inputs dynamically
- [ ] Kelly Criterion shows warning message
- [ ] SignalTypeSelector toggles long/short correctly
- [ ] RiskManagementControls updates state on input change
- [ ] TradeAnalyticsDashboard renders 4 charts without errors
- [ ] Monte Carlo runs simulation and shows results
- [ ] Leverage Analysis displays all 4 charts
- [ ] Invested Capital shows timeline and table
- [ ] Tab navigation switches between all 6 tabs
- [ ] IPC payload includes all new parameters
- [ ] Mobile responsive on screens < 768px
- [ ] No console errors in DevTools
- [ ] All TypeScript types compile without errors

---

## Performance Notes

- **Charts:** Each chart uses Recharts for efficient SVG rendering
- **Histograms:** Data binned to 30 bins for performance
- **State Updates:** All state changes are localized to components
- **Lazy Loading:** Analytics tab components only render when active
- **Memory:** No memory leaks with proper cleanup in useEffect hooks

---

## Next Steps

1. **Backend Integration** - Ensure Python backend returns all new fields
2. **End-to-End Testing** - Test with real backtest data
3. **User Feedback** - Gather feedback on UI/UX
4. **Phase 3** - Implement Parameter Optimization (optional)
5. **Production Release** - Deploy Phase 2 to users

