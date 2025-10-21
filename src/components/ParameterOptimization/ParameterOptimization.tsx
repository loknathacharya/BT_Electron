import React, { useState } from 'react';
import {
  BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell
} from 'recharts';
import { OptimizationConfig, OptimizationResult, ParameterRange } from '../../types/portfolio';
import './ParameterOptimization.css';

interface ParameterOptimizationProps {
  scannerSpec: any;
  symbols: string[];
  baseConfig: {
    initial_capital: number;
    position_size_pct: number;
    commission: number;
    slippage: number;
  };
  onOptimizationComplete?: (results: OptimizationResult[]) => void;
}

interface ParameterRangeInput {
  name: string;
  enabled: boolean;
  min: number;
  max: number;
  step: number;
}

interface OptimizationResults {
  topResults: Array<{
    parameters: Record<string, any>;
    metrics: Record<string, number>;
    rank: number;
  }>;
  allResults: Array<{
    parameters: Record<string, any>;
    metrics: Record<string, number>;
  }>;
  stats: {
    count: number;
    min: number;
    max: number;
    mean: number;
    median: number;
    std: number;
  };
  totalCombinations: number;
  successfulRuns: number;
}

export const ParameterOptimization: React.FC<ParameterOptimizationProps> = ({
  scannerSpec,
  symbols,
  baseConfig,
  onOptimizationComplete
}) => {
  // Parameter ranges
  const [holdingPeriod, setHoldingPeriod] = useState<ParameterRangeInput>({
    name: 'holding_period_days',
    enabled: true,
    min: 5,
    max: 50,
    step: 5
  });

  const [stopLoss, setStopLoss] = useState<ParameterRangeInput>({
    name: 'stop_loss_pct',
    enabled: true,
    min: 2,
    max: 10,
    step: 2
  });

  const [takeProfit, setTakeProfit] = useState<ParameterRangeInput>({
    name: 'take_profit_pct',
    enabled: true,
    min: 5,
    max: 20,
    step: 5
  });

  const [positionSize, setPositionSize] = useState<ParameterRangeInput>({
    name: 'position_size_pct',
    enabled: false,
    min: 5,
    max: 20,
    step: 5
  });

  // Optimization state
  const [optimizationMetric, setOptimizationMetric] = useState<'total_return' | 'sharpe_ratio' | 'profit_factor'>('sharpe_ratio');
  const [topN, setTopN] = useState<number>(20);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<string>('');
  const [results, setResults] = useState<OptimizationResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  const calculateCombinations = (): number => {
    let total = 1;
    const params = [holdingPeriod, stopLoss, takeProfit, positionSize];
    
    for (const param of params) {
      if (param.enabled) {
        const numValues = Math.floor((param.max - param.min) / param.step) + 1;
        total *= numValues;
      }
    }
    
    return total;
  };

  const runOptimization = async () => {
    if (symbols.length === 0) {
      setError('Please select at least one symbol');
      return;
    }

    setRunning(true);
    setError(null);
    setProgress('Starting optimization...');
    setResults(null);

    try {
      // Build parameter ranges
      const parameterRanges: Record<string, number[]> = {};
      
      const addRange = (param: ParameterRangeInput) => {
        if (!param.enabled) return;
        const values: number[] = [];
        for (let v = param.min; v <= param.max; v += param.step) {
          values.push(v);
        }
        parameterRanges[param.name] = values;
      };

      addRange(holdingPeriod);
      addRange(stopLoss);
      addRange(takeProfit);
      addRange(positionSize);

      if (Object.keys(parameterRanges).length === 0) {
        setError('Please enable at least one parameter to optimize');
        setRunning(false);
        return;
      }

      const totalCombinations = calculateCombinations();
      setProgress(`Running ${totalCombinations} backtests...`);

      // Call backend
      const response = await window.electronAPI.invoke('run-parameter-optimization', {
        scannerSpec,
        symbols,
        baseConfig,
        parameterRanges,
        metric: optimizationMetric,
        topN
      });

      if (response.error) {
        setError(response.error);
      } else {
        setResults(response as OptimizationResults);
        setProgress(`Completed ${response.successfulRuns} of ${response.totalCombinations} runs`);
        
        if (onOptimizationComplete) {
          onOptimizationComplete(response.topResults);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Optimization failed');
    } finally {
      setRunning(false);
    }
  };

  const renderParameterControl = (
    param: ParameterRangeInput,
    setter: React.Dispatch<React.SetStateAction<ParameterRangeInput>>,
    label: string,
    description: string
  ) => (
    <div className="parameter-control">
      <div className="parameter-header">
        <label className="parameter-checkbox">
          <input
            type="checkbox"
            checked={param.enabled}
            onChange={(e) => setter({ ...param, enabled: e.target.checked })}
          />
          <span className="parameter-label">{label}</span>
        </label>
        <span className="parameter-description">{description}</span>
      </div>

      {param.enabled && (
        <div className="parameter-ranges">
          <div className="range-input">
            <label>Min:</label>
            <input
              type="number"
              value={param.min}
              onChange={(e) => setter({ ...param, min: parseFloat(e.target.value) })}
              step={param.step}
            />
          </div>
          <div className="range-input">
            <label>Max:</label>
            <input
              type="number"
              value={param.max}
              onChange={(e) => setter({ ...param, max: parseFloat(e.target.value) })}
              step={param.step}
            />
          </div>
          <div className="range-input">
            <label>Step:</label>
            <input
              type="number"
              value={param.step}
              onChange={(e) => setter({ ...param, step: parseFloat(e.target.value) })}
              min={0.1}
              step={0.1}
            />
          </div>
          <div className="range-preview">
            Values: {Math.floor((param.max - param.min) / param.step) + 1}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="parameter-optimization">
      <div className="optimization-header">
        <h3>🔍 Parameter Optimization</h3>
        <p className="subtitle">Find optimal parameters through systematic grid search</p>
      </div>

      {/* Configuration Panel */}
      <div className="optimization-config">
        <h4>📊 Parameters to Optimize</h4>
        
        {renderParameterControl(
          holdingPeriod,
          setHoldingPeriod,
          'Holding Period',
          'Days to hold position before time-based exit'
        )}

        {renderParameterControl(
          stopLoss,
          setStopLoss,
          'Stop Loss (%)',
          'Maximum loss before exiting position'
        )}

        {renderParameterControl(
          takeProfit,
          setTakeProfit,
          'Take Profit (%)',
          'Target profit before exiting position'
        )}

        {renderParameterControl(
          positionSize,
          setPositionSize,
          'Position Size (%)',
          'Percentage of portfolio per position'
        )}

        {/* Optimization Settings */}
        <div className="optimization-settings">
          <h4>⚙️ Optimization Settings</h4>
          
          <div className="setting-row">
            <label>Optimization Metric:</label>
            <select
              value={optimizationMetric}
              onChange={(e) => setOptimizationMetric(e.target.value as any)}
            >
              <option value="sharpe_ratio">Sharpe Ratio</option>
              <option value="total_return">Total Return</option>
              <option value="profit_factor">Profit Factor</option>
            </select>
          </div>

          <div className="setting-row">
            <label>Top Results to Show:</label>
            <input
              type="number"
              value={topN}
              onChange={(e) => setTopN(parseInt(e.target.value))}
              min={5}
              max={50}
              step={5}
            />
          </div>
        </div>

        {/* Combination Counter */}
        <div className="combinations-info">
          <div className="info-box">
            <span className="info-label">Total Combinations:</span>
            <span className="info-value">{calculateCombinations().toLocaleString()}</span>
          </div>
          <div className="info-box">
            <span className="info-label">Estimated Time:</span>
            <span className="info-value">
              {calculateCombinations() < 100 ? '< 1 min' :
               calculateCombinations() < 500 ? '1-5 min' :
               calculateCombinations() < 1000 ? '5-15 min' : '15+ min'}
            </span>
          </div>
        </div>

        {/* Run Button */}
        <button
          className="run-optimization-button"
          onClick={runOptimization}
          disabled={running || symbols.length === 0}
        >
          {running ? (
            <>
              <span className="spinner"></span>
              Running Optimization...
            </>
          ) : (
            <>
              <span className="button-icon">▶️</span>
              Run Optimization
            </>
          )}
        </button>

        {/* Progress */}
        {progress && (
          <div className="progress-message">
            {progress}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      {/* Results */}
      {results && (
        <div className="optimization-results">
          {/* Statistics Summary */}
          <div className="results-summary">
            <h4>📊 Optimization Summary</h4>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-label">Total Runs</span>
                <span className="stat-value">{results.totalCombinations}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Successful</span>
                <span className="stat-value">{results.successfulRuns}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Best {optimizationMetric.replace('_', ' ')}</span>
                <span className="stat-value">{results.stats.max.toFixed(3)}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Average {optimizationMetric.replace('_', ' ')}</span>
                <span className="stat-value">{results.stats.mean.toFixed(3)}</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Std Dev</span>
                <span className="stat-value">{results.stats.std.toFixed(3)}</span>
              </div>
            </div>
          </div>

          {/* Top Results Table */}
          <div className="top-results">
            <h4>🏆 Top {topN} Parameter Combinations</h4>
            <div className="results-table-wrapper">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Parameters</th>
                    <th>Total Return</th>
                    <th>Sharpe Ratio</th>
                    <th>Max Drawdown</th>
                    <th>Win Rate</th>
                    <th>Profit Factor</th>
                  </tr>
                </thead>
                <tbody>
                  {results.topResults.map((result, idx) => (
                    <tr key={idx} className={idx === 0 ? 'best-result' : ''}>
                      <td>{result.rank}</td>
                      <td className="parameters-cell">
                        {Object.entries(result.parameters).map(([key, value]) => (
                          <div key={key} className="param-item">
                            <span className="param-name">{key.replace(/_/g, ' ')}:</span>
                            <span className="param-value">{value}</span>
                          </div>
                        ))}
                      </td>
                      <td className={result.metrics.total_return >= 0 ? 'positive' : 'negative'}>
                        {(result.metrics.total_return * 100).toFixed(2)}%
                      </td>
                      <td>{result.metrics.sharpe_ratio?.toFixed(2) || 'N/A'}</td>
                      <td className="negative">
                        {(result.metrics.max_drawdown * 100).toFixed(2)}%
                      </td>
                      <td>{(result.metrics.win_rate * 100).toFixed(1)}%</td>
                      <td>{result.metrics.profit_factor?.toFixed(2) || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Distribution Chart */}
          <div className="distribution-chart">
            <h4>📊 Results Distribution</h4>
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="total_return"
                  type="number"
                  label={{ value: 'Total Return (%)', position: 'insideBottom', offset: -5 }}
                  tickFormatter={(value) => (value * 100).toFixed(0)}
                />
                <YAxis
                  dataKey="sharpe_ratio"
                  type="number"
                  label={{ value: 'Sharpe Ratio', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="custom-tooltip">
                          <p><strong>Total Return:</strong> {(data.metrics.total_return * 100).toFixed(2)}%</p>
                          <p><strong>Sharpe Ratio:</strong> {data.metrics.sharpe_ratio?.toFixed(2) || 'N/A'}</p>
                          <p><strong>Max Drawdown:</strong> {(data.metrics.max_drawdown * 100).toFixed(2)}%</p>
                          <p><strong>Win Rate:</strong> {(data.metrics.win_rate * 100).toFixed(1)}%</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter
                  data={results.allResults.map(r => ({
                    total_return: r.metrics.total_return || 0,
                    sharpe_ratio: r.metrics.sharpe_ratio || 0,
                    metrics: r.metrics
                  }))}
                  fill="#1f77b4"
                >
                  {results.allResults.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={index < topN ? '#28a745' : '#1f77b4'}
                      opacity={index < topN ? 1 : 0.3}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <div className="chart-note">
              <span className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#28a745' }}></span>
                Top {topN} Results
              </span>
              <span className="legend-item">
                <span className="legend-color" style={{ backgroundColor: '#1f77b4', opacity: 0.3 }}></span>
                Other Results
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
