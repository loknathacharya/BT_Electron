/**
 * Phase 6: Parameter Optimization UI Component
 * Allows users to define parameter ranges and run optimization backtests
 */
import React, { useState } from 'react';
import './ParameterOptimizer.css';

interface ParameterRange {
  name: string;
  type: 'discrete' | 'continuous';
  values?: number[];  // For discrete
  min?: number;      // For continuous
  max?: number;
  step?: number;
}

interface OptimizationResult {
  parameters: Record<string, number>;
  metrics: Record<string, number>;
  tradeCount: number;
  rank?: number;
}

interface OptimizationStats {
  count: number;
  min: number;
  max: number;
  mean: number;
  median: number;
  std: number;
}

interface Props {
  scannerSpec?: any;
  symbol?: string;
  backtestConfig?: any;
}

const ParameterOptimizer: React.FC<Props> = ({ 
  scannerSpec, 
  symbol = 'AAPL',
  backtestConfig = {}
}) => {
  const [parameterRanges, setParameterRanges] = useState<ParameterRange[]>([]);
  const [searchMode, setSearchMode] = useState<'grid' | 'random'>('grid');
  const [randomSamples, setRandomSamples] = useState(100);
  const [rankMetric, setRankMetric] = useState('sharpe_ratio');
  const [topN, setTopN] = useState(10);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [results, setResults] = useState<OptimizationResult[]>([]);
  const [bestParameters, setBestParameters] = useState<OptimizationResult[]>([]);
  const [statistics, setStatistics] = useState<OptimizationStats | null>(null);
  const [error, setError] = useState<string>('');

  const addParameterRange = () => {
    setParameterRanges([...parameterRanges, {
      name: `param_${parameterRanges.length + 1}`,
      type: 'discrete',
      values: [10, 20, 30]
    }]);
  };

  const updateParameterRange = (index: number, updates: Partial<ParameterRange>) => {
    const newRanges = [...parameterRanges];
    newRanges[index] = { ...newRanges[index], ...updates };
    setParameterRanges(newRanges);
  };

  const removeParameterRange = (index: number) => {
    setParameterRanges(parameterRanges.filter((_, i) => i !== index));
  };

  const runOptimization = async () => {
    setError('');
    setIsOptimizing(true);
    
    try {
      // Convert parameter ranges to backend format
      const ranges: Record<string, number[] | [number, number, number]> = {};
      for (const range of parameterRanges) {
        if (range.type === 'discrete' && range.values) {
          ranges[range.name] = range.values;
        } else if (range.type === 'continuous' && range.min !== undefined && range.max !== undefined && range.step !== undefined) {
          ranges[range.name] = [range.min, range.max, range.step];
        }
      }

      const request = {
        action: 'optimize-backtest',
        data: {
          scannerSpec,
          symbol,
          backtestConfig,
          parameterRanges: ranges,
          optimizationConfig: {
            searchMode,
            randomSamples: searchMode === 'random' ? randomSamples : undefined,
            rankMetric,
            topN
          }
        }
      };

      // @ts-ignore - electronAPI is injected by preload
      const response = await window.electronAPI.invoke('optimize-backtest', request);
      
      if (response.error) {
        setError(response.error);
      } else {
        setResults(response.results || []);
        setBestParameters(response.bestParameters || []);
        setStatistics(response.statistics || null);
      }
    } catch (err: any) {
      setError(err.message || 'Optimization failed');
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="parameter-optimizer">
      <h2>Parameter Optimization</h2>
      
      {/* Parameter Range Definition */}
      <section className="optimizer-section">
        <h3>Parameter Ranges</h3>
        {parameterRanges.map((range, index) => (
          <div key={index} className="parameter-range-card">
            <input
              type="text"
              value={range.name}
              onChange={(e) => updateParameterRange(index, { name: e.target.value })}
              placeholder="Parameter name"
              className="param-name-input"
            />
            
            <select
              value={range.type}
              onChange={(e) => updateParameterRange(index, { type: e.target.value as 'discrete' | 'continuous' })}
              className="param-type-select"
            >
              <option value="discrete">Discrete</option>
              <option value="continuous">Continuous</option>
            </select>
            
            {range.type === 'discrete' ? (
              <input
                type="text"
                value={range.values?.join(', ') || ''}
                onChange={(e) => updateParameterRange(index, { 
                  values: e.target.value.split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v))
                })}
                placeholder="Values (comma-separated, e.g., 10, 20, 30)"
                className="param-values-input"
              />
            ) : (
              <div className="continuous-range">
                <input
                  type="number"
                  value={range.min || ''}
                  onChange={(e) => updateParameterRange(index, { min: parseFloat(e.target.value) })}
                  placeholder="Min"
                  className="param-number-input"
                />
                <input
                  type="number"
                  value={range.max || ''}
                  onChange={(e) => updateParameterRange(index, { max: parseFloat(e.target.value) })}
                  placeholder="Max"
                  className="param-number-input"
                />
                <input
                  type="number"
                  value={range.step || ''}
                  onChange={(e) => updateParameterRange(index, { step: parseFloat(e.target.value) })}
                  placeholder="Step"
                  className="param-number-input"
                />
              </div>
            )}
            
            <button onClick={() => removeParameterRange(index)} className="remove-param-btn">
              Remove
            </button>
          </div>
        ))}
        
        <button onClick={addParameterRange} className="add-param-btn">
          + Add Parameter
        </button>
      </section>
      
      {/* Optimization Configuration */}
      <section className="optimizer-section">
        <h3>Optimization Settings</h3>
        <div className="config-grid">
          <label>
            Search Mode:
            <select value={searchMode} onChange={(e) => setSearchMode(e.target.value as 'grid' | 'random')}>
              <option value="grid">Grid Search</option>
              <option value="random">Random Search</option>
            </select>
          </label>
          
          {searchMode === 'random' && (
            <label>
              Random Samples:
              <input
                type="number"
                value={randomSamples}
                onChange={(e) => setRandomSamples(parseInt(e.target.value))}
                min={1}
                max={10000}
              />
            </label>
          )}
          
          <label>
            Rank By:
            <select value={rankMetric} onChange={(e) => setRankMetric(e.target.value)}>
              <option value="sharpe_ratio">Sharpe Ratio</option>
              <option value="total_return">Total Return</option>
              <option value="profit_factor">Profit Factor</option>
              <option value="win_rate">Win Rate</option>
              <option value="max_drawdown">Max Drawdown</option>
            </select>
          </label>
          
          <label>
            Top N Results:
            <input
              type="number"
              value={topN}
              onChange={(e) => setTopN(parseInt(e.target.value))}
              min={1}
              max={100}
            />
          </label>
        </div>
      </section>
      
      {/* Run Button */}
      <button
        onClick={runOptimization}
        disabled={isOptimizing || parameterRanges.length === 0}
        className="run-optimization-btn"
      >
        {isOptimizing ? 'Optimizing...' : 'Run Optimization'}
      </button>
      
      {error && <div className="error-message">{error}</div>}
      
      {/* Results */}
      {bestParameters.length > 0 && (
        <section className="optimizer-section">
          <h3>Best Parameters</h3>
          <table className="results-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Parameters</th>
                <th>Sharpe</th>
                <th>Return %</th>
                <th>Profit Factor</th>
                <th>Win Rate %</th>
                <th>Trades</th>
              </tr>
            </thead>
            <tbody>
              {bestParameters.map((result, index) => (
                <tr key={index}>
                  <td>{result.rank}</td>
                  <td>
                    {Object.entries(result.parameters).map(([key, value]) => (
                      <div key={key}>{key}={value}</div>
                    ))}
                  </td>
                  <td>{result.metrics.sharpe_ratio?.toFixed(2) || '-'}</td>
                  <td>{result.metrics.total_return?.toFixed(2) || '-'}</td>
                  <td>{result.metrics.profit_factor?.toFixed(2) || '-'}</td>
                  <td>{result.metrics.win_rate?.toFixed(1) || '-'}</td>
                  <td>{result.tradeCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      
      {/* Statistics */}
      {statistics && (
        <section className="optimizer-section">
          <h3>Optimization Statistics</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total Combinations</div>
              <div className="stat-value">{statistics.count}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Best {rankMetric}</div>
              <div className="stat-value">{statistics.max?.toFixed(3)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Worst {rankMetric}</div>
              <div className="stat-value">{statistics.min?.toFixed(3)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Average {rankMetric}</div>
              <div className="stat-value">{statistics.mean?.toFixed(3)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Std Dev</div>
              <div className="stat-value">{statistics.std?.toFixed(3)}</div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default ParameterOptimizer;
