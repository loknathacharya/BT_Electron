# Portfolio Backtest Enhancement Plan
## Migrating Features from Streamlit to Electron App

**Created:** 2025-10-20  
**Project:** BT_Electron - BYOD Strategy Backtesting  
**Goal:** Bring advanced portfolio backtesting features from the Streamlit version to the current Electron app

---

## 📋 Executive Summary

This plan outlines how to enhance the current **PortfolioBacktest** component in the Electron app to match the feature-rich **Backtestengine_streamlit.py** implementation. The Streamlit version includes advanced position sizing, signal type support (long/short), Monte Carlo analysis, leverage metrics, and comprehensive visualizations that are currently missing from the Electron version.

**Current State:**
- ✅ Basic portfolio backtesting with multiple symbols
- ✅ Equal weight and custom allocation
- ✅ Simple metrics (return, Sharpe, drawdown)
- ✅ Basic equity curve and correlation heatmap

**Target State:**
- 🎯 Advanced position sizing methods (6 types)
- 🎯 Long/Short signal support
- 🎯 Comprehensive trade analytics
- 🎯 Monte Carlo simulation
- 🎯 Leverage metrics and analysis
- 🎯 Parameter optimization
- 🎯 Enhanced visualizations
- 🎯 Invested capital tracking

---

## 🎯 Feature Gap Analysis

### **Missing Features from Streamlit Version:**

#### **1. Position Sizing Methods (HIGH PRIORITY)**
**Current:** Only basic percentage allocation  
**Target:** 6 sophisticated methods

| Method | Description | Use Case | Priority |
|--------|-------------|----------|----------|
| **Equal Weight** | 2% of portfolio per position | Simple, diversified | P0 |
| **Fixed Amount** | Same dollar amount per trade | Testing, stable capital | P0 |
| **Percent Risk** | Risk fixed % based on stop-loss | Risk-conscious trading | P1 |
| **Volatility Target** | Size by instrument volatility | Professional portfolios | P1 |
| **ATR-based** | Size by Average True Range | Trend-following | P2 |
| **Kelly Criterion** | Optimal mathematical sizing | Experienced traders | P2 |

**Backend Integration Required:**
```python
def calculate_position_size(
    sizing_method: str,
    entry_price: float,
    portfolio_value: float,
    volatility: Optional[float] = None,
    atr: Optional[float] = None,
    risk_per_trade: float = 2.0,
    # ... additional parameters
) -> float:
    # Returns number of shares to trade
```

---

#### **2. Signal Type Support (HIGH PRIORITY)**
**Current:** Assumes long-only signals  
**Target:** Explicit long/short toggle with proper P&L calculation

**Features:**
- 📈 **Long Signals:** Buy at signal, profit when price rises
  - Stop loss: Below entry price
  - Take profit: Above entry price
  - P&L = (exit_price - entry_price) × shares

- 📉 **Short Signals:** Sell at signal, profit when price falls
  - Stop loss: Above entry price
  - Take profit: Below entry price
  - P&L = (entry_price - exit_price) × shares

**UI Changes:**
```tsx
<div className="signal-type-selector">
  <label>
    <input type="radio" value="long" checked={signalType === 'long'} />
    📈 Long Signals (Buy & Hold)
  </label>
  <label>
    <input type="radio" value="short" checked={signalType === 'short'} />
    📉 Short Signals (Sell & Cover)
  </label>
</div>
```

---

#### **3. Trade Analytics Dashboard (MEDIUM PRIORITY)**

**Missing Visualizations:**

| Chart Type | Purpose | Priority |
|------------|---------|----------|
| **Exit Reason Pie Chart** | Shows distribution of stop-loss/take-profit/time exits | P0 |
| **Holding Period Distribution** | Histogram of days held per trade | P0 |
| **P&L Distribution** | Histogram of profit/loss percentages | P0 |
| **P&L Over Time Scatter** | Trade performance timeline | P1 |
| **Position Size Distribution** | Shows capital allocation patterns | P1 |
| **Position Size Timeline** | Capital usage over time | P2 |

**Implementation:**
- Use existing Plotly.js (already in dependencies)
- Create new component: `TradeAnalyticsDashboard.tsx`
- Add to Portfolio Backtest results tabs

---

#### **4. Monte Carlo Simulation (MEDIUM PRIORITY)**

**Purpose:** Forecast future performance based on historical trade returns

**Features:**
- Run N simulations (100-2000)
- Simulate M future trades (10-200)
- Display distribution of potential outcomes
- Calculate confidence intervals (5th, 50th, 95th percentile)

**UI:**
```tsx
<div className="monte-carlo-section">
  <h4>🎲 Monte Carlo Analysis</h4>
  <label>Number of Simulations: 
    <input type="range" min="100" max="2000" value={nSims} />
  </label>
  <label>Future Trades to Simulate: 
    <input type="range" min="10" max="200" value={nTrades} />
  </label>
  <button onClick={runMonteCarlo}>Run Simulation</button>
  
  {/* Results: Histogram + confidence intervals */}
  <MonteCarloChart data={mcResults} />
</div>
```

**Backend Function:**
```python
def run_monte_carlo_simulation(
    trade_returns: List[float],
    n_simulations: int = 1000,
    n_future_trades: int = 50
) -> Dict[str, Any]:
    # Returns distribution, percentiles, risk metrics
```

---

#### **5. Leverage Metrics (MEDIUM PRIORITY)**

**Purpose:** Track and analyze capital utilization and risk

**Key Metrics:**
- Average leverage used
- Maximum leverage reached
- Leverage risk score (% of high-leverage trades)
- Leverage-performance correlation
- Leverage distribution (≤1x, 1-2x, 2-3x, >3x)

**Visualizations:**
- Leverage distribution bar chart
- Leverage vs performance scatter plot
- Leverage usage timeline
- Leverage risk dashboard (4-panel)

**Backend Calculation:**
```python
def calculate_leverage_metrics(
    trade_log: pd.DataFrame,
    initial_capital: float
) -> Dict[str, Any]:
    # Leverage = Position Value / Available Capital
    # Returns comprehensive leverage analysis
```

---

#### **6. Parameter Optimization (LOW PRIORITY)**

**Current:** Single backtest with fixed parameters  
**Target:** Grid search across parameter space

**Parameters to Optimize:**
- Holding period (5-100 days)
- Stop loss (1-50%)
- Take profit (5-100%)
- Position sizing method
- Rebalancing frequency

**Features:**
- Parallel processing (multiprocessing)
- Progress tracking
- Interactive heatmaps (2D/3D)
- Export results to CSV
- Best strategy identification

**UI Flow:**
1. User defines parameter ranges
2. System calculates total combinations (e.g., 1000)
3. Runs backtests in parallel
4. Displays top 20 results
5. Shows heatmaps for key metrics

---

#### **7. Invested Capital Tracking (HIGH PRIORITY)**

**Current:** No visibility into capital deployment  
**Target:** Real-time tracking of invested vs available capital

**Purpose:**
- Show how much capital is actively deployed in trades
- Identify periods of over/under-utilization
- Enable no-leverage mode validation

**Visualization:**
```
Portfolio Value: $100,000
├── Invested Capital: $85,000 (85%)
│   ├── Symbol A: $25,000
│   ├── Symbol B: $30,000
│   └── Symbol C: $30,000
└── Available Cash: $15,000 (15%)
```

**Chart:** Line chart showing invested value over time

**Backend Function:**
```python
def calculate_invested_value_over_time(
    trade_log: pd.DataFrame
) -> pd.DataFrame:
    # Returns DataFrame with Date and Invested Value columns
```

---

#### **8. Enhanced Risk Management (MEDIUM PRIORITY)**

**Features:**

| Feature | Description | Backend Required |
|---------|-------------|------------------|
| **One Trade Per Instrument** | Prevent multiple concurrent positions | ✅ Already exists |
| **Leverage Control** | Enable/disable leverage | ✅ Already exists |
| **Stop Loss** | Automatic exit on drawdown | ✅ Needs enhancement |
| **Take Profit** | Automatic exit on gains | ✅ Needs enhancement |
| **Trailing Stop** | Dynamic stop-loss adjustment | ❌ New feature |
| **Max Drawdown Limit** | Stop trading after X% loss | ❌ New feature |

**UI for Leverage Control:**
```tsx
<label>
  <input 
    type="checkbox" 
    checked={allowLeverage}
    onChange={(e) => setAllowLeverage(e.target.checked)}
  />
  Allow Leverage (positions can exceed portfolio value)
</label>
{!allowLeverage && (
  <p className="info">
    ℹ️ Total position value cannot exceed portfolio value
  </p>
)}
```

---

## 🏗️ Implementation Architecture

### **Phase 1: Backend Enhancement (Python)**

#### **1.1 Position Sizing Module**
**File:** `backend/position_sizing.py` (new)

```python
from enum import Enum
from typing import Optional, Dict, Any
import numpy as np

class PositionSizingMethod(Enum):
    EQUAL_WEIGHT = "equal_weight"
    FIXED_AMOUNT = "fixed_amount"
    PERCENT_RISK = "percent_risk"
    VOLATILITY_TARGET = "volatility_target"
    ATR_BASED = "atr_based"
    KELLY_CRITERION = "kelly_criterion"

class PositionSizer:
    def __init__(self, method: PositionSizingMethod, **params):
        self.method = method
        self.params = params
    
    def calculate_shares(
        self,
        entry_price: float,
        portfolio_value: float,
        open_positions_value: float = 0,
        allow_leverage: bool = False,
        **kwargs
    ) -> int:
        """
        Calculate number of shares to trade.
        Returns 0 if insufficient capital.
        """
        # Method-specific logic...
        # Apply leverage constraints
        # Return integer shares
        pass
    
    def calculate_volatility(self, price_data: np.ndarray) -> float:
        """Calculate rolling volatility for vol targeting"""
        pass
    
    def calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> float:
        """Calculate Average True Range"""
        pass
```

**Integration with existing backend:**
```python
# In portfolio_manager.py
from position_sizing import PositionSizer, PositionSizingMethod

# During backtest execution:
sizer = PositionSizer(
    method=PositionSizingMethod[config['sizing_method'].upper()],
    risk_per_trade=config.get('risk_per_trade', 2.0),
    fixed_amount=config.get('fixed_amount', 10000),
    # ... other params
)

shares = sizer.calculate_shares(
    entry_price=entry_price,
    portfolio_value=current_portfolio_value,
    open_positions_value=total_open_positions,
    allow_leverage=config.get('allow_leverage', False)
)
```

---

#### **1.2 Trade Analytics Module**
**File:** `backend/trade_analytics.py` (new)

```python
from typing import Dict, Any, List
import pandas as pd
import numpy as np

class TradeAnalyzer:
    def __init__(self, trade_log: pd.DataFrame):
        self.trades = trade_log
    
    def calculate_performance_metrics(self, initial_capital: float) -> Dict[str, Any]:
        """Enhanced metrics including leverage analysis"""
        return {
            "totalReturn": self._calculate_total_return(initial_capital),
            "winRate": self._calculate_win_rate(),
            "profitFactor": self._calculate_profit_factor(),
            "averageWin": self._calculate_avg_win(),
            "averageLoss": self._calculate_avg_loss(),
            "maxDrawdown": self._calculate_max_drawdown(),
            "sharpeRatio": self._calculate_sharpe(),
            "leverageMetrics": self._calculate_leverage_metrics(initial_capital),
            "exitReasons": self._analyze_exit_reasons(),
            "holdingPeriods": self._analyze_holding_periods(),
            "plDistribution": self._analyze_pl_distribution(),
        }
    
    def run_monte_carlo(
        self, 
        n_simulations: int = 1000, 
        n_trades: int = 50
    ) -> Dict[str, Any]:
        """Monte Carlo simulation for future performance"""
        returns = self.trades['Profit/Loss (%)'] / 100
        simulations = []
        
        for _ in range(n_simulations):
            sim_returns = np.random.choice(returns, n_trades, replace=True)
            final_return = np.prod(1 + sim_returns) - 1
            simulations.append(final_return * 100)
        
        return {
            "simulations": simulations,
            "percentile_5": np.percentile(simulations, 5),
            "percentile_50": np.percentile(simulations, 50),
            "percentile_95": np.percentile(simulations, 95),
            "mean": np.mean(simulations),
            "std": np.std(simulations),
        }
    
    def calculate_invested_value_timeline(self) -> pd.DataFrame:
        """Track invested capital over time"""
        # Implementation from Streamlit version
        pass
    
    def _calculate_leverage_metrics(self, initial_capital: float) -> Dict[str, Any]:
        """Comprehensive leverage analysis"""
        # Calculate leverage for each trade
        # Analyze distribution, correlation with performance
        # Return leverage risk score
        pass
```

---

#### **1.3 IPC Handler Updates**
**File:** `electron/main.ts`

```typescript
// Add new IPC handlers
ipcMain.handle('run-portfolio-backtest', async (event, payload) => {
  const {
    scannerSpec,
    symbols,
    backtestConfig,
    portfolioConfig,
    positionSizingConfig,  // NEW
    signalType,            // NEW
    riskManagementConfig   // NEW
  } = payload;
  
  // Enhanced Python call with new parameters
  const result = await pythonBackend.invoke('run_portfolio_backtest', {
    ...payload,
    position_sizing: positionSizingConfig,
    signal_type: signalType,
    risk_management: riskManagementConfig
  });
  
  return result;
});

// New handler for Monte Carlo
ipcMain.handle('run-monte-carlo', async (event, payload) => {
  const { tradeReturns, nSimulations, nTrades } = payload;
  return await pythonBackend.invoke('monte_carlo_simulation', payload);
});

// New handler for parameter optimization
ipcMain.handle('run-parameter-optimization', async (event, payload) => {
  // Stream progress updates to renderer
  const progressCallback = (progress: number) => {
    event.sender.send('optimization-progress', progress);
  };
  
  return await pythonBackend.invoke('optimize_parameters', {
    ...payload,
    progress_callback: progressCallback
  });
});
```

---

### **Phase 2: Frontend Enhancement (React/TypeScript)**

#### **2.1 Component Structure**

```
src/components/
├── PortfolioBacktest.tsx (ENHANCED)
│   ├── Position Sizing Configuration
│   ├── Signal Type Selection
│   ├── Risk Management Settings
│   └── Results Display
│
├── TradeAnalytics/ (NEW FOLDER)
│   ├── TradeAnalyticsDashboard.tsx
│   ├── ExitReasonChart.tsx
│   ├── HoldingPeriodHistogram.tsx
│   ├── PLDistributionChart.tsx
│   ├── PLTimelineScatter.tsx
│   └── PositionSizingCharts.tsx
│
├── MonteCarloSimulation/ (NEW FOLDER)
│   ├── MonteCarloRunner.tsx
│   ├── MonteCarloHistogram.tsx
│   └── MonteCarloStats.tsx
│
├── LeverageAnalysis/ (NEW FOLDER)
│   ├── LeverageMetrics.tsx
│   ├── LeverageDistribution.tsx
│   ├── LeverageVsPerformance.tsx
│   └── LeverageTimeline.tsx
│
├── ParameterOptimization/ (NEW FOLDER)
│   ├── OptimizationRunner.tsx
│   ├── ParameterRanges.tsx
│   ├── OptimizationHeatmaps.tsx
│   └── BestStrategiesTable.tsx
│
└── InvestedCapital/ (NEW FOLDER)
    ├── InvestedValueChart.tsx
    └── CapitalAllocationTable.tsx
```

---

#### **2.2 Enhanced PortfolioBacktest.tsx**

**New State Variables:**
```tsx
const [positionSizingConfig, setPositionSizingConfig] = useState({
  method: 'equal_weight' as PositionSizingMethod,
  riskPerTrade: 2.0,
  fixedAmount: 10000,
  volatilityTarget: 0.15,
  kellyWinRate: 55,
  kellyAvgWin: 8,
  kellyAvgLoss: -4,
});

const [signalType, setSignalType] = useState<'long' | 'short'>('long');

const [riskManagementConfig, setRiskManagementConfig] = useState({
  allowLeverage: false,
  oneTradePerInstrument: false,
  stopLoss: 5.0,
  takeProfit: null as number | null,
  trailingStop: null as number | null,
});

const [showMonteCarlo, setShowMonteCarlo] = useState(false);
const [showLeverageAnalysis, setShowLeverageAnalysis] = useState(false);
```

**New UI Sections:**

1. **Position Sizing Selector:**
```tsx
<div className="position-sizing-section">
  <h3>💰 Position Sizing Method</h3>
  <select 
    value={positionSizingConfig.method}
    onChange={(e) => setPositionSizingConfig({
      ...positionSizingConfig, 
      method: e.target.value as PositionSizingMethod
    })}
  >
    <option value="equal_weight">Equal Weight (2% per position)</option>
    <option value="fixed_amount">Fixed Dollar Amount</option>
    <option value="percent_risk">Percent Risk (Risk-based)</option>
    <option value="volatility_target">Volatility Targeting</option>
    <option value="atr_based">ATR-based Sizing</option>
    <option value="kelly_criterion">Kelly Criterion</option>
  </select>
  
  {/* Conditional parameter inputs based on method */}
  {positionSizingConfig.method === 'fixed_amount' && (
    <label>
      Fixed Amount ($):
      <input 
        type="number" 
        value={positionSizingConfig.fixedAmount}
        onChange={(e) => setPositionSizingConfig({
          ...positionSizingConfig,
          fixedAmount: parseFloat(e.target.value)
        })}
      />
    </label>
  )}
  
  {/* Similar conditional inputs for other methods */}
</div>
```

2. **Signal Type Selector:**
```tsx
<div className="signal-type-section">
  <h3>📊 Signal Type</h3>
  <div className="signal-type-buttons">
    <button 
      className={signalType === 'long' ? 'active long' : 'inactive'}
      onClick={() => setSignalType('long')}
    >
      📈 Long Signals
      <span className="hint">Buy & profit from price increase</span>
    </button>
    <button 
      className={signalType === 'short' ? 'active short' : 'inactive'}
      onClick={() => setSignalType('short')}
    >
      📉 Short Signals
      <span className="hint">Sell & profit from price decrease</span>
    </button>
  </div>
</div>
```

3. **Enhanced Results Tabs:**
```tsx
{results && (
  <Tabs>
    <Tab label="📈 Equity Curve">
      <PortfolioEquityCurve {...results} />
    </Tab>
    
    <Tab label="📊 Invested Capital">
      <InvestedValueChart data={results.investedValueTimeline} />
    </Tab>
    
    <Tab label="📋 Trade Log">
      <TradeLogTable trades={results.trades} />
    </Tab>
    
    <Tab label="📊 Trade Analytics">
      <TradeAnalyticsDashboard 
        exitReasons={results.exitReasons}
        holdingPeriods={results.holdingPeriods}
        plDistribution={results.plDistribution}
        plTimeline={results.trades}
      />
    </Tab>
    
    <Tab label="🎲 Monte Carlo">
      <MonteCarloSimulation 
        tradeReturns={results.trades.map(t => t.returnPct)}
      />
    </Tab>
    
    <Tab label="⚖️ Leverage">
      <LeverageAnalysis 
        metrics={results.leverageMetrics}
        trades={results.trades}
      />
    </Tab>
    
    <Tab label="🔍 Optimization">
      <ParameterOptimization 
        symbols={symbols}
        scannerSpec={scannerSpec}
      />
    </Tab>
  </Tabs>
)}
```

---

#### **2.3 New Component: TradeAnalyticsDashboard.tsx**

```tsx
import React from 'react';
import Plot from 'react-plotly.js';

interface TradeAnalyticsDashboardProps {
  exitReasons: Record<string, number>;
  holdingPeriods: number[];
  plDistribution: number[];
  plTimeline: Array<{date: string; pl: number; reason: string}>;
}

export const TradeAnalyticsDashboard: React.FC<TradeAnalyticsDashboardProps> = ({
  exitReasons,
  holdingPeriods,
  plDistribution,
  plTimeline
}) => {
  return (
    <div className="trade-analytics-dashboard">
      <div className="analytics-grid">
        {/* Exit Reason Pie Chart */}
        <Plot
          data={[{
            type: 'pie',
            labels: Object.keys(exitReasons),
            values: Object.values(exitReasons),
            marker: {
              colors: ['#28a745', '#dc3545', '#ffc107']
            }
          }]}
          layout={{
            title: 'Trade Exit Reasons',
            height: 400
          }}
        />
        
        {/* Holding Period Histogram */}
        <Plot
          data={[{
            type: 'histogram',
            x: holdingPeriods,
            nbinsx: 20,
            marker: { color: '#1f77b4' }
          }]}
          layout={{
            title: 'Holding Period Distribution',
            xaxis: { title: 'Days Held' },
            yaxis: { title: 'Frequency' },
            height: 400
          }}
        />
        
        {/* P&L Distribution */}
        <Plot
          data={[{
            type: 'histogram',
            x: plDistribution,
            nbinsx: 25,
            marker: { 
              color: plDistribution,
              colorscale: 'RdYlGn',
              cmin: -10,
              cmax: 10
            }
          }]}
          layout={{
            title: 'P&L Distribution (%)',
            xaxis: { title: 'Profit/Loss (%)' },
            yaxis: { title: 'Frequency' },
            height: 400,
            shapes: [{
              type: 'line',
              x0: 0,
              x1: 0,
              y0: 0,
              y1: 1,
              yref: 'paper',
              line: { color: 'red', dash: 'dash' }
            }]
          }}
        />
        
        {/* P&L Over Time Scatter */}
        <Plot
          data={[{
            type: 'scatter',
            mode: 'markers',
            x: plTimeline.map(t => t.date),
            y: plTimeline.map(t => t.pl),
            marker: {
              size: 8,
              color: plTimeline.map(t => t.pl),
              colorscale: 'RdYlGn',
              showscale: true
            },
            text: plTimeline.map(t => `${t.reason}: ${t.pl.toFixed(2)}%`),
            hovertemplate: '%{text}<br>Date: %{x}<extra></extra>'
          }]}
          layout={{
            title: 'P&L Over Time',
            xaxis: { title: 'Date' },
            yaxis: { title: 'Profit/Loss (%)' },
            height: 400,
            shapes: [{
              type: 'line',
              x0: plTimeline[0].date,
              x1: plTimeline[plTimeline.length - 1].date,
              y0: 0,
              y1: 0,
              line: { color: 'red', dash: 'dash' }
            }]
          }}
        />
      </div>
    </div>
  );
};
```

---

#### **2.4 New Component: MonteCarloSimulation.tsx**

```tsx
import React, { useState } from 'react';
import Plot from 'react-plotly.js';

interface MonteCarloSimulationProps {
  tradeReturns: number[];
}

export const MonteCarloSimulation: React.FC<MonteCarloSimulationProps> = ({
  tradeReturns
}) => {
  const [nSimulations, setNSimulations] = useState(1000);
  const [nTrades, setNTrades] = useState(50);
  const [results, setResults] = useState<any>(null);
  const [running, setRunning] = useState(false);
  
  const runSimulation = async () => {
    setRunning(true);
    try {
      const result = await window.electronAPI.invoke('run-monte-carlo', {
        tradeReturns,
        nSimulations,
        nTrades
      });
      setResults(result);
    } catch (error) {
      console.error('Monte Carlo simulation failed:', error);
    } finally {
      setRunning(false);
    }
  };
  
  return (
    <div className="monte-carlo-simulation">
      <h3>🎲 Monte Carlo Analysis</h3>
      
      {/* Controls */}
      <div className="mc-controls">
        <label>
          Number of Simulations:
          <input 
            type="range" 
            min="100" 
            max="2000" 
            step="100"
            value={nSimulations}
            onChange={(e) => setNSimulations(parseInt(e.target.value))}
          />
          <span>{nSimulations}</span>
        </label>
        
        <label>
          Future Trades to Simulate:
          <input 
            type="range" 
            min="10" 
            max="200" 
            step="10"
            value={nTrades}
            onChange={(e) => setNTrades(parseInt(e.target.value))}
          />
          <span>{nTrades}</span>
        </label>
        
        <button 
          onClick={runSimulation}
          disabled={running || tradeReturns.length < 10}
        >
          {running ? 'Running...' : 'Run Simulation'}
        </button>
      </div>
      
      {/* Results */}
      {results && (
        <>
          {/* Histogram */}
          <Plot
            data={[{
              type: 'histogram',
              x: results.simulations,
              nbinsx: 50,
              marker: { color: '#1f77b4' }
            }]}
            layout={{
              title: `Distribution of ${nTrades} Future Trades (${nSimulations} simulations)`,
              xaxis: { title: 'Total Return (%)' },
              yaxis: { title: 'Frequency' },
              height: 500,
              shapes: [
                // Percentile lines
                { type: 'line', x0: results.percentile_5, x1: results.percentile_5, y0: 0, y1: 1, yref: 'paper', line: { color: 'red', dash: 'dash' } },
                { type: 'line', x0: results.percentile_50, x1: results.percentile_50, y0: 0, y1: 1, yref: 'paper', line: { color: 'green', dash: 'solid' } },
                { type: 'line', x0: results.percentile_95, x1: results.percentile_95, y0: 0, y1: 1, yref: 'paper', line: { color: 'orange', dash: 'dash' } },
              ]
            }}
          />
          
          {/* Statistics */}
          <div className="mc-stats">
            <div className="mc-stat">
              <span className="label">5th Percentile (Worst Case):</span>
              <span className="value negative">{results.percentile_5.toFixed(2)}%</span>
            </div>
            <div className="mc-stat">
              <span className="label">Median (50th Percentile):</span>
              <span className="value">{results.percentile_50.toFixed(2)}%</span>
            </div>
            <div className="mc-stat">
              <span className="label">95th Percentile (Best Case):</span>
              <span className="value positive">{results.percentile_95.toFixed(2)}%</span>
            </div>
            <div className="mc-stat">
              <span className="label">Mean:</span>
              <span className="value">{results.mean.toFixed(2)}%</span>
            </div>
            <div className="mc-stat">
              <span className="label">Standard Deviation:</span>
              <span className="value">{results.std.toFixed(2)}%</span>
            </div>
          </div>
          
          {/* Risk Assessment */}
          <div className="risk-assessment">
            <h4>Risk Assessment</h4>
            <p>
              Based on {nSimulations.toLocaleString()} simulations of {nTrades} trades:
            </p>
            <ul>
              <li>95% chance of return between <strong>{results.percentile_5.toFixed(2)}%</strong> and <strong>{results.percentile_95.toFixed(2)}%</strong></li>
              <li>Probability of positive return: <strong>{(results.simulations.filter((r: number) => r > 0).length / results.simulations.length * 100).toFixed(1)}%</strong></li>
              <li>Probability of >10% loss: <strong>{(results.simulations.filter((r: number) => r < -10).length / results.simulations.length * 100).toFixed(1)}%</strong></li>
            </ul>
          </div>
        </>
      )}
      
      {tradeReturns.length < 10 && (
        <p className="warning">
          ⚠️ Need at least 10 trades to run Monte Carlo simulation
        </p>
      )}
    </div>
  );
};
```

---

## 📊 Implementation Roadmap

### **Phase 1: Foundation (Week 1-2)**
**Goal:** Core backend enhancements

| Task | Effort | Priority | Dependencies |
|------|--------|----------|--------------|
| Create `position_sizing.py` module | 2 days | P0 | None |
| Implement 6 position sizing methods | 2 days | P0 | position_sizing.py |
| Add signal type support (long/short) | 1 day | P0 | None |
| Update `portfolio_manager.py` integration | 1 day | P0 | position_sizing.py |
| Add unit tests for position sizing | 1 day | P0 | position_sizing.py |
| Create `trade_analytics.py` module | 2 days | P1 | None |
| Implement invested capital tracking | 1 day | P1 | trade_analytics.py |

**Deliverables:**
- ✅ Working position sizing module
- ✅ Long/short signal support
- ✅ Updated backend tests

---

### **Phase 2: Enhanced UI (Week 3-4)**
**Goal:** Frontend components for new features

| Task | Effort | Priority | Dependencies |
|------|--------|----------|--------------|
| Add position sizing UI to PortfolioBacktest | 1 day | P0 | Phase 1 |
| Add signal type selector | 0.5 days | P0 | Phase 1 |
| Create `TradeAnalyticsDashboard.tsx` | 2 days | P1 | Phase 1 |
| Implement exit reason pie chart | 0.5 days | P1 | TradeAnalyticsDashboard |
| Implement holding period histogram | 0.5 days | P1 | TradeAnalyticsDashboard |
| Implement P&L distribution chart | 0.5 days | P1 | TradeAnalyticsDashboard |
| Implement P&L timeline scatter | 0.5 days | P1 | TradeAnalyticsDashboard |
| Create `InvestedValueChart.tsx` | 1 day | P1 | Phase 1 |
| Update results tabs structure | 1 day | P1 | All charts |

**Deliverables:**
- ✅ Position sizing configuration in UI
- ✅ Signal type selector
- ✅ Trade analytics dashboard with 4 charts
- ✅ Invested capital visualization

---

### **Phase 3: Advanced Analytics (Week 5)**
**Goal:** Monte Carlo and leverage analysis

| Task | Effort | Priority | Dependencies |
|------|--------|----------|--------------|
| Implement Monte Carlo backend | 1 day | P1 | trade_analytics.py |
| Create `MonteCarloSimulation.tsx` | 1.5 days | P1 | MC backend |
| Implement leverage metrics backend | 1 day | P1 | trade_analytics.py |
| Create `LeverageAnalysis.tsx` components | 2 days | P2 | Leverage backend |
| Add leverage distribution chart | 0.5 days | P2 | LeverageAnalysis |
| Add leverage vs performance scatter | 0.5 days | P2 | LeverageAnalysis |
| Add leverage timeline chart | 0.5 days | P2 | LeverageAnalysis |

**Deliverables:**
- ✅ Working Monte Carlo simulation
- ✅ Comprehensive leverage analysis
- ✅ Interactive visualizations

---

### **Phase 4: Optimization (Week 6 - Optional)**
**Goal:** Parameter optimization grid search

| Task | Effort | Priority | Dependencies |
|------|--------|----------|--------------|
| Implement parameter optimization backend | 2 days | P2 | All Phase 1 |
| Add progress streaming via IPC | 1 day | P2 | Optimization backend |
| Create `ParameterOptimization.tsx` | 2 days | P2 | Optimization backend |
| Implement 2D heatmaps | 1 day | P2 | ParameterOptimization |
| Implement 3D scatter plots | 1 day | P2 | ParameterOptimization |
| Add best strategies table | 0.5 days | P2 | ParameterOptimization |

**Deliverables:**
- ✅ Full parameter optimization suite
- ✅ Interactive heatmaps and 3D plots
- ✅ Export optimization results

---

## 🎨 UI/UX Mockups

### **Position Sizing Configuration**
```
┌─────────────────────────────────────────────────────────────┐
│ 💰 Position Sizing Method                                   │
├─────────────────────────────────────────────────────────────┤
│ Method: [Equal Weight (2% per position) ▼]                  │
│                                                              │
│ ℹ️ Info: Allocates exactly 2% of current portfolio value    │
│   to each trade. Simple and ensures diversification.        │
│                                                              │
│ [Show Advanced Options ▶]                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Method: [Kelly Criterion ▼]                                 │
│                                                              │
│ Expected Win Rate: [────●────] 55%                          │
│ Average Win:       [──●──────] 8%                           │
│ Average Loss:      [────●────] -4%                          │
│                                                              │
│ ⚠️ Kelly sizing can be aggressive. Consider fractional     │
│   Kelly (multiplying by 0.25-0.5) for safer sizing.        │
└─────────────────────────────────────────────────────────────┘
```

### **Signal Type Selector**
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Signal Type                                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │  📈 Long Signals    │  │  📉 Short Signals   │          │
│  │  ─────────────────  │  │  ─────────────────  │          │
│  │  • Buy at signal    │  │  • Sell at signal   │          │
│  │  • Profit from ↑    │  │  • Profit from ↓    │          │
│  │  • Stop below entry │  │  • Stop above entry │          │
│  └─────────────────────┘  └─────────────────────┘          │
│         [SELECTED]                  [ ]                      │
└─────────────────────────────────────────────────────────────┘
```

### **Trade Analytics Dashboard**
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Trade Analytics                                           │
├──────────────────────────┬──────────────────────────────────┤
│  Exit Reason Distribution │  Holding Period Distribution    │
│  ┌────────────────────┐  │  ┌────────────────────┐         │
│  │   🥧 PIE CHART     │  │  │   📊 HISTOGRAM     │         │
│  │ • Take Profit: 35% │  │  │                    │         │
│  │ • Stop Loss: 25%   │  │  │  ▄▅▆▇█▇▆▅▄▃▂▁     │         │
│  │ • Time Exit: 40%   │  │  │ 5  10  15  20  25  │         │
│  └────────────────────┘  │  └────────────────────┘         │
├──────────────────────────┼──────────────────────────────────┤
│  P&L Distribution (%)     │  P&L Over Time                  │
│  ┌────────────────────┐  │  ┌────────────────────┐         │
│  │   📊 HISTOGRAM     │  │  │   📈 SCATTER       │         │
│  │        █           │  │  │   • • ••  •••      │         │
│  │      ▆▇█▇▆         │  │  │  •     •   • •     │         │
│  │   ▂▄▅─────▅▄▃▂▁    │  │  │ ──────────────     │         │
│  │ -10  0  +10  +20   │  │  │   Date Timeline    │         │
│  └────────────────────┘  │  └────────────────────┘         │
└──────────────────────────┴──────────────────────────────────┘
```

### **Monte Carlo Results**
```
┌─────────────────────────────────────────────────────────────┐
│ 🎲 Monte Carlo Simulation Results                           │
├─────────────────────────────────────────────────────────────┤
│  Distribution of 50 Future Trades (1000 simulations)        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              📊 HISTOGRAM                             │  │
│  │                   ▁▃▅▇█▇▅▃▁                           │  │
│  │                 ▂▄▆███████▆▄▂                         │  │
│  │        ▁▂▃▅▇███████████████████▇▅▃▂▁                 │  │
│  │  ────┼─────────┼─────────┼─────────┼────            │  │
│  │     5%        50%       95%                           │  │
│  │   -8.2%     +12.5%    +35.8%                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  📊 Statistics:                                             │
│  • Median: +12.5%                                           │
│  • Mean: +13.2%                                             │
│  • Std Dev: 15.4%                                           │
│                                                              │
│  ⚖️ Risk Assessment:                                        │
│  • 95% chance: between -8.2% and +35.8%                    │
│  • Probability of profit: 78.3%                             │
│  • Probability of >10% loss: 12.5%                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Technical Considerations

### **1. Performance Optimization**

**Problem:** Processing large portfolios (50+ symbols) with complex position sizing can be slow.

**Solutions:**

1. **Vectorization (Numba):**
   - Already used in Streamlit version
   - Port vectorized functions to current backend
   - Use `@jit(nopython=True)` decorator for hot loops

2. **Multiprocessing:**
   - Parameter optimization runs in parallel
   - Use Python `multiprocessing.Pool`
   - Stream progress updates via IPC

3. **Caching:**
   - Cache OHLC data in memory
   - Cache calculated indicators (volatility, ATR)
   - Invalidate cache on data updates

**Implementation:**
```python
from functools import lru_cache
import multiprocessing as mp

@lru_cache(maxsize=128)
def get_volatility(symbol: str, date: str) -> float:
    """Cached volatility calculation"""
    pass

def parallel_backtest(params_list: List[Dict]) -> List[Dict]:
    """Run backtests in parallel"""
    with mp.Pool(processes=mp.cpu_count() - 1) as pool:
        results = pool.map(run_single_backtest, params_list)
    return results
```

---

### **2. Data Consistency**

**Problem:** Long/short signals have different P&L calculations and exit logic.

**Solution:** Create unified trade execution engine:

```python
class TradeExecutor:
    def __init__(self, signal_type: str):
        self.signal_type = signal_type
        self.multiplier = 1 if signal_type == 'long' else -1
    
    def check_stop_loss(self, entry_price: float, current_price: float, stop_pct: float) -> bool:
        if self.signal_type == 'long':
            stop_price = entry_price * (1 - stop_pct / 100)
            return current_price <= stop_price
        else:  # short
            stop_price = entry_price * (1 + stop_pct / 100)
            return current_price >= stop_price
    
    def check_take_profit(self, entry_price: float, current_price: float, tp_pct: float) -> bool:
        if self.signal_type == 'long':
            tp_price = entry_price * (1 + tp_pct / 100)
            return current_price >= tp_price
        else:  # short
            tp_price = entry_price * (1 - tp_pct / 100)
            return current_price <= tp_price
    
    def calculate_pl(self, entry_price: float, exit_price: float, shares: int) -> float:
        return (exit_price - entry_price) * shares * self.multiplier
```

---

### **3. Memory Management**

**Problem:** Storing all trades and equity curves for 50 symbols can use 100+ MB of memory.

**Solutions:**

1. **Streaming Results:**
   - Don't keep all trades in memory
   - Stream to disk or database
   - Load on-demand for visualization

2. **Compression:**
   - Compress equity curves (downsample)
   - Store only essential trade fields
   - Use efficient data structures (NumPy arrays)

3. **Pagination:**
   - Load trade log in chunks
   - Implement virtual scrolling in UI
   - Lazy-load charts on tab activation

---

### **4. Error Handling**

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| **Insufficient Data** | Symbol missing OHLC data | Skip symbol, warn user |
| **Division by Zero** | Zero volatility/ATR | Use default fallback values |
| **Memory Error** | Too many simulations | Limit max simulations, use streaming |
| **Timeout** | Long-running optimization | Add progress callback, allow cancel |
| **Invalid Weights** | Custom weights don't sum to 1.0 | Normalize automatically, warn user |

**Implementation:**
```python
try:
    result = run_backtest(...)
except InsufficientDataError as e:
    logger.warning(f"Skipping {symbol}: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise BacktestError(f"Backtest failed: {e}")
```

---

## 📈 Success Metrics

### **Feature Completion Checklist**

| Feature | Backend | Frontend | Tests | Docs | Status |
|---------|---------|----------|-------|------|--------|
| **Position Sizing** |  |  |  |  | 🔲 |
| - Equal Weight | ✅ | 🔲 | 🔲 | 🔲 | Partial |
| - Fixed Amount | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| - Percent Risk | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| - Volatility Target | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| - ATR-based | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| - Kelly Criterion | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| **Signal Type** | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| **Trade Analytics** | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| **Monte Carlo** | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| **Leverage Analysis** | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| **Invested Capital** | 🔲 | 🔲 | 🔲 | 🔲 | TODO |
| **Parameter Optimization** | 🔲 | 🔲 | 🔲 | 🔲 | TODO |

---

### **Performance Benchmarks**

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Single backtest (10 symbols) | < 2s | TBD | 🔲 |
| Single backtest (50 symbols) | < 10s | TBD | 🔲 |
| Parameter optimization (100 combos) | < 30s | TBD | 🔲 |
| Monte Carlo (1000 sims) | < 3s | TBD | 🔲 |
| Trade log load (1000 trades) | < 500ms | TBD | 🔲 |

---

### **User Acceptance Criteria**

**✅ Feature is complete when:**

1. **Position Sizing:**
   - [ ] User can select from 6 methods via dropdown
   - [ ] Method-specific parameters show/hide dynamically
   - [ ] Backend correctly calculates shares for each method
   - [ ] Results show average position size and distribution
   - [ ] Unit tests cover all 6 methods with edge cases

2. **Signal Type:**
   - [ ] User can toggle between long/short with clear visual indicator
   - [ ] Stop-loss logic reverses correctly for shorts
   - [ ] P&L calculation matches signal type
   - [ ] Results show signal type in trade log
   - [ ] Backend validates signal type consistency

3. **Trade Analytics:**
   - [ ] 4 charts render without errors
   - [ ] Charts update when filters change
   - [ ] Hover tooltips show detailed info
   - [ ] Export to CSV/PNG works
   - [ ] Charts are responsive on different screen sizes

4. **Monte Carlo:**
   - [ ] Simulation completes in < 5 seconds
   - [ ] Histogram shows percentile lines
   - [ ] Statistics calculate correctly
   - [ ] User can adjust simulation parameters
   - [ ] Warning shows if insufficient trades

5. **Leverage Analysis:**
   - [ ] All 4 visualizations render
   - [ ] Metrics calculate correctly
   - [ ] Color coding indicates risk levels
   - [ ] Export functionality works
   - [ ] No-leverage mode prevents overleveraging

6. **Overall:**
   - [ ] No console errors during normal operation
   - [ ] Loading states prevent UI freezing
   - [ ] Error messages are user-friendly
   - [ ] All features documented in user guide
   - [ ] Code review passed

---

## 📚 Documentation Requirements

### **User Documentation**

1. **Position Sizing Guide** (`docs/POSITION_SIZING_GUIDE.md`)
   - Explanation of each method
   - When to use which method
   - Parameter recommendations
   - Examples with screenshots

2. **Signal Type Guide** (`docs/SIGNAL_TYPE_GUIDE.md`)
   - Long vs short signals explained
   - Exit logic differences
   - P&L calculation examples
   - Common pitfalls

3. **Trade Analytics Tutorial** (`docs/TRADE_ANALYTICS_TUTORIAL.md`)
   - How to interpret each chart
   - Filter and export options
   - Best practices for analysis

4. **Monte Carlo Guide** (`docs/MONTE_CARLO_GUIDE.md`)
   - What is Monte Carlo simulation
   - How to interpret results
   - Risk assessment methodology
   - Limitations and assumptions

---

### **Developer Documentation**

1. **Position Sizing Architecture** (`docs/dev/POSITION_SIZING_ARCHITECTURE.md`)
   - Module structure
   - Class hierarchy
   - Integration points
   - Testing strategy

2. **IPC Protocol** (`docs/dev/IPC_PROTOCOL_UPDATES.md`)
   - New IPC handlers
   - Payload schemas
   - Error handling
   - Progress streaming

3. **Backend API** (`docs/dev/BACKEND_API.md`)
   - New Python functions
   - Type signatures
   - Return formats
   - Error codes

---

## 🚀 Next Steps

### **Immediate Actions (This Week)**

1. **Review and Approve Plan:**
   - [ ] Review this document with stakeholders
   - [ ] Prioritize features (confirm P0, P1, P2)
   - [ ] Adjust timeline if needed
   - [ ] Get sign-off to proceed

2. **Set Up Development Environment:**
   - [ ] Create feature branch: `feature/portfolio-backtest-enhancements`
   - [ ] Set up Python virtual environment
   - [ ] Install any new dependencies (numba, etc.)
   - [ ] Create initial directory structure

3. **Start Phase 1 (Backend Foundation):**
   - [ ] Create `backend/position_sizing.py`
   - [ ] Implement `PositionSizer` class skeleton
   - [ ] Write unit tests for equal weight (baseline)
   - [ ] Integrate with `portfolio_manager.py`
   - [ ] Test end-to-end with existing UI

---

### **Weekly Milestones**

**Week 1-2:** Phase 1 complete
- ✅ Position sizing backend working
- ✅ Signal type support added
- ✅ Unit tests passing
- ✅ Basic integration tested

**Week 3-4:** Phase 2 complete
- ✅ Position sizing UI complete
- ✅ Signal type selector in UI
- ✅ Trade analytics dashboard with 4 charts
- ✅ Invested capital chart

**Week 5:** Phase 3 complete
- ✅ Monte Carlo simulation working
- ✅ Leverage analysis complete
- ✅ All visualizations polished

**Week 6 (Optional):** Phase 4 complete
- ✅ Parameter optimization working
- ✅ Interactive heatmaps
- ✅ Export functionality

---

## 🎯 Conclusion

This plan provides a comprehensive roadmap to bring the advanced features from the Streamlit version into the Electron app's Portfolio Backtest component. The phased approach ensures:

1. **Incremental Delivery:** Each phase delivers working features
2. **Risk Mitigation:** Core features (P0) implemented first
3. **Quality Assurance:** Tests and documentation alongside code
4. **User-Centric:** UI/UX carefully designed for clarity
5. **Performance:** Optimizations considered from the start

**Estimated Total Effort:** 4-6 weeks (depending on optional Phase 4)

**Key Success Factors:**
- Clear communication with stakeholders
- Regular testing and feedback
- Comprehensive documentation
- Performance monitoring
- User acceptance testing

---

**Ready to proceed with Phase 1?** Let's start building! 🚀

