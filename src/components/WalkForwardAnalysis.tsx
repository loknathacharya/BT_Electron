import React, { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, BarChart, Bar
} from 'recharts';
import './WalkForwardAnalysis.css';

interface WalkForwardAnalysisProps {
  scannerSpec: any;
}

interface WalkForwardConfig {
  startDate: string;
  endDate: string;
  inSampleDays: number;
  outSampleDays: number;
  stepDays: number;
}

interface WindowResult {
  windowIndex: number;
  inSample: {
    startDate: string;
    endDate: string;
    metrics: any;
    trades: number;
  };
  outSample: {
    startDate: string;
    endDate: string;
    metrics: any;
    trades: number;
  };
}

interface WalkForwardResults {
  symbol: string;
  windows: WindowResult[];
  summary: {
    totalWindows: number;
    inSample: {
      avgReturn: number;
      avgSharpe: number;
      winRate: number;
    };
    outSample: {
      avgReturn: number;
      avgSharpe: number;
      winRate: number;
    };
  };
  stats: {
    timeMs: number;
  };
}

export const WalkForwardAnalysis: React.FC<WalkForwardAnalysisProps> = ({ scannerSpec }) => {
  const [symbol, setSymbol] = useState('');
  const [config, setConfig] = useState<WalkForwardConfig>({
    startDate: '2020-01-01',
    endDate: '2023-12-31',
    inSampleDays: 180,
    outSampleDays: 60,
    stepDays: 30
  });
  const [backtestConfig, setBacktestConfig] = useState({
    initialCapital: 10000,
    positionSize: 10,
    commission: 0.1,
    slippage: 0.1
  });
  const [results, setResults] = useState<WalkForwardResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runWalkForward = async () => {
    if (!symbol.trim()) {
      setError('Please enter a symbol');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      // Use provided scannerSpec or create a default RSI strategy if empty
      let effectiveScannerSpec = scannerSpec;
      
      if (!scannerSpec || Object.keys(scannerSpec).length === 0) {
        // Default Moving Average Crossover strategy: Buy when SMA(10) > SMA(30), Sell when SMA(10) < SMA(30)
        effectiveScannerSpec = {
          timeframe: '1D',
          conditions: {
            entry: {
              operator: 'AND',
              conditions: [
                {
                  type: 'cross',
                  indicator1: 'sma',
                  params1: { period: 10 },
                  indicator2: 'sma',
                  params2: { period: 30 },
                  direction: 'above'
                }
              ]
            },
            exit: {
              operator: 'AND',
              conditions: [
                {
                  type: 'cross',
                  indicator1: 'sma',
                  params1: { period: 10 },
                  indicator2: 'sma',
                  params2: { period: 30 },
                  direction: 'below'
                }
              ]
            }
          }
        };
        console.log('Using default SMA crossover strategy for walk-forward analysis');
      }

      const response = await window.electronAPI.invoke('run-walk-forward', {
        scannerSpec: effectiveScannerSpec,
        symbol: symbol.trim().toUpperCase(),
        backtestConfig: {
          initial_capital: backtestConfig.initialCapital,
          position_size_pct: backtestConfig.positionSize,
          commission: backtestConfig.commission / 100,
          slippage: backtestConfig.slippage / 100
        },
        walkForwardConfig: config
      });

      if (response.error) {
        setError(response.error);
      } else {
        setResults(response as WalkForwardResults);
      }
    } catch (err: any) {
      setError(err.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null || isNaN(value)) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatNumber = (value: number | undefined, decimals = 2) => {
    if (value === undefined || value === null || isNaN(value)) return 'N/A';
    return value.toFixed(decimals);
  };

  // Prepare chart data
  const prepareChartData = () => {
    if (!results) return [];
    
    return results.windows.map(window => ({
      window: `W${window.windowIndex + 1}`,
      inSampleReturn: (window.inSample.metrics.totalReturn || 0) * 100,
      outSampleReturn: (window.outSample.metrics.totalReturn || 0) * 100,
      inSampleSharpe: window.inSample.metrics.sharpeRatio || 0,
      outSampleSharpe: window.outSample.metrics.sharpeRatio || 0
    }));
  };

  return (
    <div className="walk-forward-analysis">
      <h2>Walk-Forward Analysis</h2>
      <p className="description">
        Test strategy robustness by running multiple in-sample (training) and out-of-sample (testing) periods.
        <br />
        <strong>Default Strategy:</strong> SMA Crossover - Buy when SMA(10) crosses above SMA(30), Sell when crosses below
      </p>

      {/* Configuration */}
      <div className="config-section">
        <h3>Configuration</h3>
        
        <div className="form-row">
          <div className="form-group">
            <label>Symbol:</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g., RELIANCE"
              className="input-field"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Start Date:</label>
            <input
              type="date"
              value={config.startDate}
              onChange={(e) => setConfig({...config, startDate: e.target.value})}
              className="input-field"
            />
          </div>
          <div className="form-group">
            <label>End Date:</label>
            <input
              type="date"
              value={config.endDate}
              onChange={(e) => setConfig({...config, endDate: e.target.value})}
              className="input-field"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>In-Sample Days (Training):</label>
            <input
              type="number"
              value={config.inSampleDays}
              onChange={(e) => setConfig({...config, inSampleDays: parseInt(e.target.value)})}
              min="30"
              max="730"
              className="input-field"
            />
          </div>
          <div className="form-group">
            <label>Out-of-Sample Days (Testing):</label>
            <input
              type="number"
              value={config.outSampleDays}
              onChange={(e) => setConfig({...config, outSampleDays: parseInt(e.target.value)})}
              min="30"
              max="365"
              className="input-field"
            />
          </div>
          <div className="form-group">
            <label>Step Days (Window Advance):</label>
            <input
              type="number"
              value={config.stepDays}
              onChange={(e) => setConfig({...config, stepDays: parseInt(e.target.value)})}
              min="1"
              max="180"
              className="input-field"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Initial Capital ($):</label>
            <input
              type="number"
              value={backtestConfig.initialCapital}
              onChange={(e) => setBacktestConfig({...backtestConfig, initialCapital: parseInt(e.target.value)})}
              min="1000"
              className="input-field"
            />
          </div>
          <div className="form-group">
            <label>Position Size (%):</label>
            <input
              type="number"
              value={backtestConfig.positionSize}
              onChange={(e) => setBacktestConfig({...backtestConfig, positionSize: parseFloat(e.target.value)})}
              min="1"
              max="100"
              step="0.1"
              className="input-field"
            />
          </div>
          <div className="form-group">
            <label>Commission (%):</label>
            <input
              type="number"
              value={backtestConfig.commission}
              onChange={(e) => setBacktestConfig({...backtestConfig, commission: parseFloat(e.target.value)})}
              min="0"
              max="5"
              step="0.01"
              className="input-field"
            />
          </div>
          <div className="form-group">
            <label>Slippage (%):</label>
            <input
              type="number"
              value={backtestConfig.slippage}
              onChange={(e) => setBacktestConfig({...backtestConfig, slippage: parseFloat(e.target.value)})}
              min="0"
              max="5"
              step="0.01"
              className="input-field"
            />
          </div>
        </div>

        <button
          onClick={runWalkForward}
          disabled={loading || !symbol.trim()}
          className="btn-primary"
        >
          {loading ? 'Running Walk-Forward Analysis...' : 'Run Walk-Forward Analysis'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="results-section">
          <h3>Walk-Forward Results for {results.symbol}</h3>
          
          {/* Summary Statistics */}
          <div className="summary-cards">
            <div className="summary-card in-sample">
              <h4>In-Sample (Training)</h4>
              <div className="metrics">
                <div className="metric">
                  <span className="label">Avg Return:</span>
                  <span className="value">{formatPercent(results.summary.inSample.avgReturn)}</span>
                </div>
                <div className="metric">
                  <span className="label">Avg Sharpe:</span>
                  <span className="value">{formatNumber(results.summary.inSample.avgSharpe)}</span>
                </div>
                <div className="metric">
                  <span className="label">Win Rate:</span>
                  <span className="value">{formatPercent(results.summary.inSample.winRate)}</span>
                </div>
              </div>
            </div>

            <div className="summary-card out-sample">
              <h4>Out-of-Sample (Testing)</h4>
              <div className="metrics">
                <div className="metric">
                  <span className="label">Avg Return:</span>
                  <span className="value">{formatPercent(results.summary.outSample.avgReturn)}</span>
                </div>
                <div className="metric">
                  <span className="label">Avg Sharpe:</span>
                  <span className="value">{formatNumber(results.summary.outSample.avgSharpe)}</span>
                </div>
                <div className="metric">
                  <span className="label">Win Rate:</span>
                  <span className="value">{formatPercent(results.summary.outSample.winRate)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Performance Degradation Analysis */}
          <div className="degradation-analysis">
            <h4>Performance Degradation</h4>
            <div className="degradation-metrics">
              <div className="degradation-metric">
                <span className="label">Return Degradation:</span>
                <span className={`value ${
                  results.summary.outSample.avgReturn < results.summary.inSample.avgReturn * 0.7 ? 'bad' : 
                  results.summary.outSample.avgReturn < results.summary.inSample.avgReturn * 0.9 ? 'warning' : 'good'
                }`}>
                  {formatPercent(
                    (results.summary.outSample.avgReturn - results.summary.inSample.avgReturn) / 
                    (results.summary.inSample.avgReturn || 1)
                  )}
                </span>
              </div>
              <div className="degradation-metric">
                <span className="label">Sharpe Degradation:</span>
                <span className={`value ${
                  results.summary.outSample.avgSharpe < results.summary.inSample.avgSharpe * 0.7 ? 'bad' : 
                  results.summary.outSample.avgSharpe < results.summary.inSample.avgSharpe * 0.9 ? 'warning' : 'good'
                }`}>
                  {formatPercent(
                    (results.summary.outSample.avgSharpe - results.summary.inSample.avgSharpe) / 
                    (results.summary.inSample.avgSharpe || 1)
                  )}
                </span>
              </div>
            </div>
            <p className="hint">
              {results.summary.outSample.avgReturn >= results.summary.inSample.avgReturn * 0.9 
                ? '✓ Strategy shows good stability (low degradation)'
                : results.summary.outSample.avgReturn >= results.summary.inSample.avgReturn * 0.7
                ? '⚠ Moderate degradation - strategy may be overfitted'
                : '⚠ High degradation - strategy likely overfitted to in-sample data'}
            </p>
          </div>

          {/* Returns Chart */}
          <div className="chart-container">
            <h4>Returns by Window</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={prepareChartData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="window" />
                <YAxis label={{ value: 'Return (%)', angle: -90, position: 'insideLeft' }} />
                <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
                <Legend />
                <Bar dataKey="inSampleReturn" fill="#8884d8" name="In-Sample" />
                <Bar dataKey="outSampleReturn" fill="#82ca9d" name="Out-of-Sample" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Sharpe Ratio Chart */}
          <div className="chart-container">
            <h4>Sharpe Ratio by Window</h4>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={prepareChartData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="window" />
                <YAxis label={{ value: 'Sharpe Ratio', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="inSampleSharpe" stroke="#8884d8" name="In-Sample" strokeWidth={2} />
                <Line type="monotone" dataKey="outSampleSharpe" stroke="#82ca9d" name="Out-of-Sample" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Window Details Table */}
          <div className="window-details">
            <h4>Window Details</h4>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Window</th>
                    <th colSpan={3}>In-Sample (Training)</th>
                    <th colSpan={3}>Out-of-Sample (Testing)</th>
                  </tr>
                  <tr>
                    <th></th>
                    <th>Period</th>
                    <th>Return</th>
                    <th>Sharpe</th>
                    <th>Period</th>
                    <th>Return</th>
                    <th>Sharpe</th>
                  </tr>
                </thead>
                <tbody>
                  {results.windows.map(window => (
                    <tr key={window.windowIndex}>
                      <td><strong>W{window.windowIndex + 1}</strong></td>
                      <td className="date-range">
                        {window.inSample.startDate} to {window.inSample.endDate}
                      </td>
                      <td className={window.inSample.metrics.totalReturn >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(window.inSample.metrics.totalReturn)}
                      </td>
                      <td>{formatNumber(window.inSample.metrics.sharpeRatio)}</td>
                      <td className="date-range">
                        {window.outSample.startDate} to {window.outSample.endDate}
                      </td>
                      <td className={window.outSample.metrics.totalReturn >= 0 ? 'positive' : 'negative'}>
                        {formatPercent(window.outSample.metrics.totalReturn)}
                      </td>
                      <td>{formatNumber(window.outSample.metrics.sharpeRatio)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Stats */}
          <div className="stats-footer">
            <span>{results.summary.totalWindows} windows analyzed</span>
            <span>Completed in {results.stats.timeMs}ms</span>
          </div>
        </div>
      )}
    </div>
  );
};
