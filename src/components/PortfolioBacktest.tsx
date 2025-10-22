import React, { useState, useEffect } from 'react';
import './PortfolioBacktest.css';
import {
  PortfolioEquityCurve,
  AllocationPieChart,
  CorrelationHeatmap,
  DiversificationMetrics
} from './PortfolioCharts';
import { RebalancingTimeline } from './RebalancingTimeline';
import { PositionSizingSelector } from './PortfolioBacktest/PositionSizingSelector';
import { SignalTypeSelector } from './PortfolioBacktest/SignalTypeSelector';
import { RiskManagementControls } from './PortfolioBacktest/RiskManagementControls';
import { MetricsLegend } from './PortfolioBacktest/MetricsLegend';
import { QuickStatsHeader } from './PortfolioBacktest/QuickStatsHeader';
import { TabSuggestions } from './PortfolioBacktest/TabSuggestions';
import { TradeAnalyticsDashboard } from './TradeAnalytics/TradeAnalyticsDashboard';
import { MonteCarloSimulation } from './MonteCarloSimulation/MonteCarloSimulation';
import { LeverageAnalysis } from './LeverageAnalysis/LeverageAnalysis';
import { InvestedCapital } from './InvestedCapital/InvestedCapital';
import { ParameterOptimization } from './ParameterOptimization/ParameterOptimization';
import {
  PositionSizingMethod,
  RiskManagementConfig,
  TradeAnalytics,
  LeverageMetrics,
  InvestedCapitalPoint
} from '../types/portfolio';
import SymbolListSelector from './SymbolListSelector';

interface PortfolioBacktestProps {
  scannerSpec: any;
}

interface BacktestConfig {
  initial_capital: number;
  position_size_pct: number;
  commission: number;
  slippage: number;
}

interface PortfolioConfig {
  allocationMode: 'equal' | 'custom';
  customWeights: Record<string, number>;
}

interface PortfolioMetrics {
  totalReturn: number;
  annualizedReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  volatility: number;
  winRate: number;
  profitFactor: number;
  totalTrades: number;
}

interface SymbolMetrics {
  [symbol: string]: PortfolioMetrics;
}

interface EquityCurve {
  timestamps: number[];
  equity: number[];
}

interface PortfolioResults {
  portfolioMetrics: PortfolioMetrics;
  symbolMetrics: SymbolMetrics;
  weights: Record<string, number>;
  portfolioEquityCurve: EquityCurve;
  symbolEquityCurves: Record<string, EquityCurve>;
  symbolTrades: Record<string, any[]>;
  correlationMatrix: Record<string, Record<string, number>>;
  diversificationRatio: number;
  stats: {
    timeMs: number;
    symbolsCount: number;
    totalTrades: number;
  };
  // Phase 2 additions
  investedCapitalTimeline?: InvestedCapitalPoint[];
  tradeAnalytics?: TradeAnalytics;
  leverageMetrics?: LeverageMetrics;
  leverageTimeline?: Array<{ date: string; leverage: number }>;
  leverageVsPerformance?: Array<{ leverage: number; pnlPct: number; symbol: string }>;
}

const PortfolioBacktest: React.FC<PortfolioBacktestProps> = ({ scannerSpec }) => {
  // Symbol List Integration State
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [selectedSymbolList, setSelectedSymbolList] = useState<string | null>(null);
  const [portfolioSymbols, setPortfolioSymbols] = useState<string[]>([]);
  const [useSymbolList, setUseSymbolList] = useState(false);

  const [symbols, setSymbols] = useState<string[]>(['']);
  const [backtestConfig, setBacktestConfig] = useState<BacktestConfig>({
    initial_capital: 10000,
    position_size_pct: 10,
    commission: 0.001,
    slippage: 0.001,
  });
  const [portfolioConfig, setPortfolioConfig] = useState<PortfolioConfig>({
    allocationMode: 'equal',
    customWeights: {},
  });
  const [rebalanceFrequency, setRebalanceFrequency] = useState<'monthly' | 'quarterly' | 'yearly'>('quarterly');
  const [rebalanceThreshold, setRebalanceThreshold] = useState<number>(0.05);
  const [results, setResults] = useState<PortfolioResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Phase 2: Advanced Features State
  const [positionSizingConfig, setPositionSizingConfig] = useState({
    method: 'equal_weight' as PositionSizingMethod,
    riskPerTrade: 2.0,
    fixedAmount: 10000,
    volatilityTarget: 0.15,
    atrMultiplier: 1.0,
    kellyWinRate: 55,
    kellyAvgWin: 8,
    kellyAvgLoss: -4,
  } as any);

  const [signalType, setSignalType] = useState<'long' | 'short'>('long');

  const [riskManagementConfig, setRiskManagementConfig] = useState<RiskManagementConfig>({
    allowLeverage: false,
    oneTradePerInstrument: false,
    stopLossPct: null,
    takeProfitPct: null,
    holdingPeriodDays: null,
  });

  const [activeResultsTab, setActiveResultsTab] = useState<'overview' | 'invested' | 'trades' | 'analytics' | 'monte-carlo' | 'leverage' | 'optimization'>('overview');

  // Load datasets on component mount
  useEffect(() => {
    const loadDatasets = async () => {
      try {
        const result = await window.electronAPI.invoke('get-all-datasets', {});
        if (!result.error && result.datasets) {
          setDatasets(result.datasets);
          // Auto-select first dataset if available
          if (result.datasets.length > 0) {
            setSelectedDataset(result.datasets[0].name);
          }
        }
      } catch (error) {
        console.error('Failed to load datasets:', error);
      }
    };

    loadDatasets();
  }, []);

  const addSymbol = () => {
    setSymbols([...symbols, '']);
  };

  const removeSymbol = (index: number) => {
    const newSymbols = symbols.filter((_, i) => i !== index);
    setSymbols(newSymbols);
    
    // Also remove from custom weights if present
    const symbol = symbols[index];
    if (symbol && portfolioConfig.customWeights[symbol]) {
      const newWeights = { ...portfolioConfig.customWeights };
      delete newWeights[symbol];
      setPortfolioConfig({ ...portfolioConfig, customWeights: newWeights });
    }
  };

  const updateSymbol = (index: number, value: string) => {
    const newSymbols = [...symbols];
    const oldSymbol = newSymbols[index];
    newSymbols[index] = value.trim().toUpperCase();
    setSymbols(newSymbols);
    
    // Update custom weights if renaming
    if (portfolioConfig.allocationMode === 'custom' && oldSymbol && oldSymbol !== newSymbols[index]) {
      if (portfolioConfig.customWeights[oldSymbol]) {
        const newWeights = { ...portfolioConfig.customWeights };
        newWeights[newSymbols[index]] = newWeights[oldSymbol];
        delete newWeights[oldSymbol];
        setPortfolioConfig({ ...portfolioConfig, customWeights: newWeights });
      }
    }
  };

  const updateCustomWeight = (symbol: string, weight: number) => {
    setPortfolioConfig({
      ...portfolioConfig,
      customWeights: {
        ...portfolioConfig.customWeights,
        [symbol]: weight,
      },
    });
  };

  const normalizeWeights = () => {
    const validSymbols = symbols.filter(s => s.trim());
    const total = validSymbols.reduce((sum, symbol) => {
      return sum + (portfolioConfig.customWeights[symbol] || 0);
    }, 0);
    
    if (total > 0) {
      const newWeights: Record<string, number> = {};
      validSymbols.forEach(symbol => {
        const weight = portfolioConfig.customWeights[symbol] || 0;
        newWeights[symbol] = weight / total;
      });
      setPortfolioConfig({ ...portfolioConfig, customWeights: newWeights });
    }
  };

  const runPortfolioBacktest = async () => {
    let validSymbols: string[];

    if (useSymbolList) {
      if (!selectedDataset) {
        setError('Please select a dataset');
        return;
      }

      if (!selectedSymbolList) {
        setError('Please select a symbol list');
        return;
      }

      validSymbols = portfolioSymbols;
    } else {
      validSymbols = symbols.filter(s => s.trim());
    }

    if (validSymbols.length === 0) {
      setError('Please add at least one symbol or select a symbol list');
      return;
    }

    // Validate custom weights if in custom mode
    if (portfolioConfig.allocationMode === 'custom') {
      const totalWeight = validSymbols.reduce((sum, symbol) => {
        return sum + (portfolioConfig.customWeights[symbol] || 0);
      }, 0);
      
      if (Math.abs(totalWeight - 1.0) > 0.01) {
        setError('Custom weights must sum to 1.0 (use Normalize button)');
        return;
      }
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const payload = {
        scannerSpec,
        symbols: validSymbols,
        backtestConfig,
        portfolioConfig,
        positionSizingConfig,
        signalType,
        riskManagementConfig,
        dataset_name: selectedDataset, // Include dataset for symbol list context
      };
      const response = await window.electronAPI.invoke('run-portfolio-backtest', payload);

      if (response.error) {
        // Provide more helpful error messages
        let errorMsg = response.error;
        if (errorMsg.includes('No successful backtests')) {
          errorMsg += '\n\nMake sure you have imported price data for these symbols via the "Import Data" page.';
        }
        setError(errorMsg);
      } else {
        setResults(response as PortfolioResults);
      }
    } catch (err: any) {
      setError(err.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Helper function to transform EquityCurve to chart format
  const transformEquityCurve = (curve: EquityCurve) => {
    if (!curve || !curve.timestamps || !curve.equity) return [];
    return curve.timestamps.map((timestamp, idx) => ({
      timestamp: new Date(timestamp).toISOString(),
      value: curve.equity[idx]
    }));
  };

  // Helper function to calculate average correlation
  const calculateAvgCorrelation = (correlationMatrix: Record<string, Record<string, number>>) => {
    const symbols = Object.keys(correlationMatrix);
    if (symbols.length < 2) return 0;
    
    let sum = 0;
    let count = 0;
    
    for (let i = 0; i < symbols.length; i++) {
      for (let j = i + 1; j < symbols.length; j++) {
        const corr = correlationMatrix[symbols[i]]?.[symbols[j]];
        if (corr !== undefined && !isNaN(corr)) {
          sum += corr;
          count++;
        }
      }
    }
    
    return count > 0 ? sum / count : 0;
  };

  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatNumber = (value: number | undefined, decimals = 2) => {
    if (value === undefined || value === null) return 'N/A';
    return value.toFixed(decimals);
  };

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return `$${value.toFixed(2)}`;
  };

  return (
    <div className="portfolio-backtest">
      <h2>Portfolio Backtest</h2>

      {/* Data Source Selection */}
      <div className="config-section">
        <h3>Data Source</h3>

        {/* Dataset Selection */}
        <div className="form-group">
          <label>Dataset:</label>
          <select
            value={selectedDataset || ''}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="dataset-select"
          >
            <option value="">-- Select Dataset --</option>
            {datasets.map(dataset => (
              <option key={dataset.name} value={dataset.name}>
                {dataset.name} ({dataset.symbol_count} symbols)
              </option>
            ))}
          </select>
        </div>

        {/* Symbol List Selection */}
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={useSymbolList}
              onChange={(e) => {
                setUseSymbolList(e.target.checked);
                if (!e.target.checked) {
                  setSelectedSymbolList(null);
                  setPortfolioSymbols([]);
                }
              }}
            />
            Use Symbol List
          </label>
        </div>

        {useSymbolList && (
          <SymbolListSelector
            datasetName={selectedDataset}
            selectedList={selectedSymbolList}
            onListSelect={(listName, symbols) => {
              setSelectedSymbolList(listName);
              setPortfolioSymbols(symbols);
            }}
            label="Portfolio Symbols"
            showAllOption={true}
          />
        )}

        {/* Show selected symbols info */}
        {useSymbolList && selectedSymbolList && portfolioSymbols.length > 0 && (
          <div className="info-box">
            Using symbol list "{selectedSymbolList}" with {portfolioSymbols.length} symbols
          </div>
        )}
      </div>

      {/* Symbol Selection (when not using symbol list) */}
      {!useSymbolList && (
        <div className="config-section">
          <h3>Symbols</h3>
        <div className="symbols-list">
          {symbols.map((symbol, index) => (
            <div key={index} className="symbol-row">
              <input
                type="text"
                value={symbol}
                onChange={(e) => updateSymbol(index, e.target.value)}
                placeholder="Enter symbol (e.g., AAPL)"
                className="symbol-input"
              />
              {symbols.length > 1 && (
                <button
                  onClick={() => removeSymbol(index)}
                  className="btn-remove"
                  title="Remove symbol"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
        <button onClick={addSymbol} className="btn-add">
          + Add Symbol
        </button>
        </div>
      )}

      {/* Allocation Configuration */}
      <div className="config-section">
        <h3>Allocation</h3>
        <div className="allocation-mode">
          <label>
            <input
              type="radio"
              value="equal"
              checked={portfolioConfig.allocationMode === 'equal'}
              onChange={(e) => setPortfolioConfig({ ...portfolioConfig, allocationMode: 'equal' })}
            />
            Equal Weight
          </label>
          <label>
            <input
              type="radio"
              value="custom"
              checked={portfolioConfig.allocationMode === 'custom'}
              onChange={(e) => setPortfolioConfig({ ...portfolioConfig, allocationMode: 'custom' })}
            />
            Custom Weights
          </label>
        </div>

        {portfolioConfig.allocationMode === 'custom' && (
          <div className="custom-weights">
            {symbols.filter(s => s.trim()).map((symbol) => (
              <div key={symbol} className="weight-row">
                <label>{symbol}:</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={portfolioConfig.customWeights[symbol] || 0}
                  onChange={(e) => updateCustomWeight(symbol, parseFloat(e.target.value) || 0)}
                  className="weight-input"
                />
              </div>
            ))}
            <button onClick={normalizeWeights} className="btn-normalize">
              Normalize Weights
            </button>
          </div>
        )}
      </div>

      {/* Backtest Configuration */}
      <div className="config-section">
        <h3>Backtest Settings</h3>
        <div className="backtest-config">
          <div className="config-row">
            <label>Initial Capital:</label>
            <input
              type="number"
              value={backtestConfig.initial_capital}
              onChange={(e) => setBacktestConfig({ ...backtestConfig, initial_capital: parseFloat(e.target.value) })}
              min="1000"
              step="1000"
            />
          </div>
          <div className="config-row">
            <label>Position Size (%):</label>
            <input
              type="number"
              value={backtestConfig.position_size_pct}
              onChange={(e) => setBacktestConfig({ ...backtestConfig, position_size_pct: parseFloat(e.target.value) })}
              min="1"
              max="100"
              step="1"
            />
          </div>
          <div className="config-row">
            <label>Commission (%):</label>
            <input
              type="number"
              value={backtestConfig.commission * 100}
              onChange={(e) => setBacktestConfig({ ...backtestConfig, commission: parseFloat(e.target.value) / 100 })}
              min="0"
              max="10"
              step="0.01"
            />
          </div>
          <div className="config-row">
            <label>Slippage (%):</label>
            <input
              type="number"
              value={backtestConfig.slippage * 100}
              onChange={(e) => setBacktestConfig({ ...backtestConfig, slippage: parseFloat(e.target.value) / 100 })}
              min="0"
              max="10"
              step="0.01"
            />
          </div>
        </div>
      </div>

      {/* Rebalancing Configuration */}
      <div className="config-section">
        <h3>Rebalancing Settings</h3>
        <div className="backtest-config">
          <div className="config-row">
            <label>Rebalance Frequency:</label>
            <select
              value={rebalanceFrequency}
              onChange={(e) => setRebalanceFrequency(e.target.value as 'monthly' | 'quarterly' | 'yearly')}
            >
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="yearly">Yearly</option>
            </select>
          </div>
          <div className="config-row">
            <label>Rebalance Threshold (%):</label>
            <input
              type="number"
              value={rebalanceThreshold * 100}
              onChange={(e) => setRebalanceThreshold(parseFloat(e.target.value) / 100)}
              min="0"
              max="50"
              step="0.5"
            />
          </div>
        </div>
      </div>

      {/* Phase 2: Position Sizing */}
      <div className="config-section">
        <PositionSizingSelector
          config={positionSizingConfig}
          onChange={setPositionSizingConfig}
        />
      </div>

      {/* Phase 2: Signal Type Selection */}
      <div className="config-section">
        <SignalTypeSelector
          signalType={signalType}
          onChange={setSignalType}
        />
      </div>

      {/* Phase 2: Risk Management */}
      <div className="config-section">
        <RiskManagementControls
          config={riskManagementConfig}
          onChange={setRiskManagementConfig}
        />
      </div>

      {/* Run Button */}
      <div className="actions">
        <button
          onClick={runPortfolioBacktest}
          disabled={loading ||
            (useSymbolList && (!selectedDataset || !selectedSymbolList)) ||
            (!useSymbolList && symbols.filter(s => s.trim()).length === 0)}
          className="btn-run"
        >
          {loading ? 'Running...' : 'Run Portfolio Backtest'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results Display */}
      {results && (
        <div className="results-section">
          <h3>Portfolio Results</h3>
          
          {/* Results Navigation Tabs */}
          <div className="results-tabs">
            <button 
              className={`tab-button ${activeResultsTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveResultsTab('overview')}
            >
              📊 Overview
            </button>
            <button 
              className={`tab-button ${activeResultsTab === 'invested' ? 'active' : ''}`}
              onClick={() => setActiveResultsTab('invested')}
            >
              💰 Invested Capital
            </button>
            <button 
              className={`tab-button ${activeResultsTab === 'trades' ? 'active' : ''}`}
              onClick={() => setActiveResultsTab('trades')}
            >
              📋 Trades
            </button>
            <button 
              className={`tab-button ${activeResultsTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveResultsTab('analytics')}
            >
              📊 Analytics
            </button>
            <button 
              className={`tab-button ${activeResultsTab === 'monte-carlo' ? 'active' : ''}`}
              onClick={() => setActiveResultsTab('monte-carlo')}
            >
              🎲 Monte Carlo
            </button>
            <button 
              className={`tab-button ${activeResultsTab === 'leverage' ? 'active' : ''}`}
              onClick={() => setActiveResultsTab('leverage')}
            >
              ⚡ Leverage
            </button>
            <button 
              className={`tab-button ${activeResultsTab === 'optimization' ? 'active' : ''}`}
              onClick={() => setActiveResultsTab('optimization')}
            >
              🔍 Optimization
            </button>
          </div>

          {/* Tab Content */}
          <div className="tab-content">
            {/* Overview Tab */}
            {activeResultsTab === 'overview' && (
              <>
          <div style={{display: 'flex', gap: '16px', marginBottom: '16px', alignItems: 'center'}}>
            <h3 style={{margin: 0}}>Portfolio Overview</h3>
            <MetricsLegend />
          </div>

          <QuickStatsHeader
            totalReturn={results.portfolioMetrics.totalReturn}
            sharpeRatio={results.portfolioMetrics.sharpeRatio}
            maxDrawdown={results.portfolioMetrics.maxDrawdown}
            totalTrades={results.portfolioMetrics.totalTrades}
            winRate={results.portfolioMetrics.winRate}
          />

          <TabSuggestions 
            currentTab="overview"
            onTabChange={(tab) => setActiveResultsTab(tab as any)}
            hasLeverageData={!!results.leverageMetrics}
          />

          {/* Portfolio-Level Metrics */}
          <div className="metrics-card">
            <h4>Portfolio Metrics</h4>
            <div className="metrics-grid">
              <div className="metric">
                <span className="metric-label">Total Return:</span>
                <span className="metric-value">{formatPercent(results.portfolioMetrics.totalReturn)}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Sharpe Ratio:</span>
                <span className="metric-value">{formatNumber(results.portfolioMetrics.sharpeRatio)}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Max Drawdown:</span>
                <span className="metric-value">{formatPercent(results.portfolioMetrics.maxDrawdown)}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Volatility:</span>
                <span className="metric-value">{formatPercent(results.portfolioMetrics.volatility)}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Total Trades:</span>
                <span className="metric-value">{results.portfolioMetrics.totalTrades}</span>
              </div>
            </div>
          </div>

          {/* Visualization Charts */}
          <div className="charts-section">
            {/* Equity Curve Chart */}
            {results.portfolioEquityCurve && results.portfolioEquityCurve.timestamps && results.portfolioEquityCurve.timestamps.length > 0 && (
              <PortfolioEquityCurve
                portfolioEquityCurve={transformEquityCurve(results.portfolioEquityCurve)}
                symbolEquityCurves={
                  Object.fromEntries(
                    Object.entries(results.symbolEquityCurves).map(([symbol, curve]) => [
                      symbol,
                      transformEquityCurve(curve)
                    ])
                  )
                }
                symbols={symbols.filter(s => s.trim())}
              />
            )}

            {/* Row with Pie Chart and Diversification Metrics */}
            <div className="charts-row">
              {/* Allocation Pie Chart */}
              {results.weights && Object.keys(results.weights).length > 0 && (
                <AllocationPieChart weights={results.weights} />
              )}

              {/* Diversification Metrics */}
              {results.correlationMatrix && (
                <DiversificationMetrics
                  diversificationRatio={results.diversificationRatio}
                  symbolCount={Object.keys(results.weights).length}
                  avgCorrelation={calculateAvgCorrelation(results.correlationMatrix)}
                />
              )}
            </div>

            {/* Correlation Heatmap */}
            {results.correlationMatrix && Object.keys(results.correlationMatrix).length > 0 && (
              <CorrelationHeatmap correlationMatrix={results.correlationMatrix} />
            )}

            {/* Rebalancing Timeline */}
            {results.portfolioEquityCurve && results.symbolEquityCurves && (
              <RebalancingTimeline
                symbols={symbols.filter(s => s.trim())}
                initialWeights={results.weights}
                equityCurve={results.portfolioEquityCurve}
                symbolEquities={Object.fromEntries(
                  Object.entries(results.symbolEquityCurves).map(([symbol, curve]) => [
                    symbol,
                    curve.equity
                  ])
                )}
                rebalanceFrequency={rebalanceFrequency}
                rebalanceThreshold={rebalanceThreshold}
              />
            )}
          </div>

          {/* Per-Symbol Metrics */}
          <div className="symbol-metrics-card">
            <h4>Individual Symbol Performance</h4>
            <div className="symbol-metrics-table">
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Total Return</th>
                    <th>Sharpe</th>
                    <th>Max DD</th>
                    <th>Trades</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(results.symbolMetrics).map(([symbol, metrics]) => (
                    <tr key={symbol}>
                      <td><strong>{symbol}</strong></td>
                      <td className={metrics.totalReturn >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(metrics.totalReturn)}
                      </td>
                      <td>{formatNumber(metrics.sharpeRatio)}</td>
                      <td className="negative">{formatPercent(metrics.maxDrawdown)}</td>
                      <td>{metrics.totalTrades}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Stats Footer */}
          <div className="stats-footer">
            <span>Completed in {results.stats.timeMs}ms</span>
            <span>{results.stats.symbolsCount} symbols</span>
            <span>{results.stats.totalTrades} total trades</span>
          </div>
              </>
            )}

            {/* Invested Capital Tab */}
            {activeResultsTab === 'invested' && results.investedCapitalTimeline && (
              <>
                <TabSuggestions 
                  currentTab="invested"
                  onTabChange={(tab) => setActiveResultsTab(tab as any)}
                  hasLeverageData={!!results.leverageMetrics}
                />
                <InvestedCapital
                  timeline={results.investedCapitalTimeline}
                  initialCapital={backtestConfig.initial_capital}
                />
              </>
            )}

            {/* Trades Tab */}
            {activeResultsTab === 'trades' && (
              <>
                <TabSuggestions 
                  currentTab="trades"
                  onTabChange={(tab) => setActiveResultsTab(tab as any)}
                  hasLeverageData={!!results.leverageMetrics}
                />
                <div className="trades-section">
                  <h4>Trade Log</h4>
                <div className="trades-table-wrapper">
                  <table className="trades-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Entry Date</th>
                        <th>Exit Date</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>Shares</th>
                        <th>P&L ($)</th>
                        <th>P&L (%)</th>
                        <th>Days Held</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(results.symbolTrades).flatMap(([symbol, trades]) =>
                        trades.map((trade: any, idx: number) => (
                          <tr key={`${symbol}-${idx}`}>
                            <td><strong>{symbol}</strong></td>
                            <td>{new Date(trade.entry_date).toLocaleDateString()}</td>
                            <td>{new Date(trade.exit_date).toLocaleDateString()}</td>
                            <td>${trade.entry_price.toFixed(2)}</td>
                            <td>${trade.exit_price.toFixed(2)}</td>
                            <td>{trade.shares}</td>
                            <td className={trade.pl >= 0 ? 'positive' : 'negative'}>
                              ${trade.pl.toFixed(2)}
                            </td>
                            <td className={trade.pl_pct >= 0 ? 'positive' : 'negative'}>
                              {(trade.pl_pct * 100).toFixed(2)}%
                            </td>
                            <td>{Math.floor((new Date(trade.exit_date).getTime() - new Date(trade.entry_date).getTime()) / (1000 * 60 * 60 * 24))}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              </>
            )}

            {/* Trade Analytics Tab */}
            {activeResultsTab === 'analytics' && results.tradeAnalytics && (
              <>
                <TabSuggestions 
                  currentTab="analytics"
                  onTabChange={(tab) => setActiveResultsTab(tab as any)}
                  hasLeverageData={!!results.leverageMetrics}
                />
                <TradeAnalyticsDashboard
                  analytics={results.tradeAnalytics}
                  trades={Object.values(results.symbolTrades).flat()}
                />
              </>
            )}

            {/* Monte Carlo Tab */}
            {activeResultsTab === 'monte-carlo' && (
              <>
                <TabSuggestions 
                  currentTab="monte-carlo"
                  onTabChange={(tab) => setActiveResultsTab(tab as any)}
                  hasLeverageData={!!results.leverageMetrics}
                />
                <MonteCarloSimulation
                  trades={Object.values(results.symbolTrades).flat()}
                  initialCapital={backtestConfig.initial_capital}
                  onRunSimulation={async (numSims, numTrades) => {
                    const response = await window.electronAPI.invoke('run-monte-carlo', {
                      trade_returns: Object.values(results.symbolTrades).flat().map((t: any) => t.pl_pct),
                      n_simulations: numSims,
                      n_trades: numTrades
                    });
                    return response;
                  }}
                />
              </>
            )}

            {/* Leverage Analysis Tab */}
            {activeResultsTab === 'leverage' && results.leverageMetrics && (
              <>
                <TabSuggestions 
                  currentTab="leverage"
                  onTabChange={(tab) => setActiveResultsTab(tab as any)}
                  hasLeverageData={!!results.leverageMetrics}
                />
                <LeverageAnalysis
                  metrics={results.leverageMetrics}
                  leverageTimeline={results.leverageTimeline || []}
                  leverageVsPerformance={results.leverageVsPerformance || []}
                />
              </>
            )}

            {/* Parameter Optimization Tab */}
            {activeResultsTab === 'optimization' && (
              <>
                <TabSuggestions 
                  currentTab="optimization"
                  onTabChange={(tab) => setActiveResultsTab(tab as any)}
                  hasLeverageData={!!results.leverageMetrics}
                />
                <ParameterOptimization
                  scannerSpec={scannerSpec}
                  symbols={symbols.filter(s => s.trim())}
                  baseConfig={backtestConfig}
                  onOptimizationComplete={(results) => {
                    console.log('Optimization complete:', results);
                  }}
                />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioBacktest;
