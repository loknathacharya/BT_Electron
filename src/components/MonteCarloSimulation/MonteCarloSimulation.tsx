import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from 'recharts';
import { MonteCarloResults } from '../../types/portfolio';
import './MonteCarloSimulation.css';

interface MonteCarloSimulationProps {
  trades: any[]; // Trade array from backend
  initialCapital: number;
  onRunSimulation: (numSimulations: number, numTrades: number) => Promise<MonteCarloResults>;
}

export const MonteCarloSimulation: React.FC<MonteCarloSimulationProps> = ({
  trades,
  initialCapital,
  onRunSimulation
}) => {
  const [numSimulations, setNumSimulations] = useState(1000);
  const [numTrades, setNumTrades] = useState(Math.min(100, trades.length));
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<MonteCarloResults | null>(null);
  const [error, setError] = useState<string>('');

  const handleRunSimulation = async () => {
    if (trades.length < 10) {
      setError('At least 10 trades required for Monte Carlo simulation');
      return;
    }

    if (numTrades > trades.length) {
      setError(`Cannot simulate ${numTrades} trades. Only ${trades.length} trades available.`);
      return;
    }

    setError('');
    setLoading(true);

    try {
      const result = await onRunSimulation(numSimulations, numTrades);
      setResults(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run simulation');
    } finally {
      setLoading(false);
    }
  };

  // Prepare histogram data from results
  const prepareHistogramData = () => {
    if (!results) return [];

    const simulations = results.simulations || [];
    const min = Math.min(...simulations);
    const max = Math.max(...simulations);
    const numBins = 30;
    const binSize = (max - min) / numBins;

    const bins = new Array(numBins).fill(0).map((_, i) => ({
      range: `${(min + i * binSize).toFixed(0)}`,
      count: 0,
      binStart: min + i * binSize
    }));

    simulations.forEach((value: number) => {
      const binIndex = Math.min(Math.floor((value - min) / binSize), numBins - 1);
      bins[binIndex].count++;
    });

    return bins;
  };

  const histogramData = results ? prepareHistogramData() : [];

  // Calculate risk score (0-100)
  const calculateRiskScore = () => {
    if (!results) return 0;
    
    const lossProb = (results.probabilityLoss10 * 100);
    const probProfitFactor = results.probabilityProfit > 0.5 ? 0 : 50;
    const volatility = (results.std / initialCapital) * 100;
    
    // Higher score = higher risk
    return Math.min(100, (lossProb * 0.5 + probProfitFactor * 0.2 + volatility * 0.3));
  };

  const riskScore = results ? calculateRiskScore() : 0;
  const riskLevel = riskScore < 30 ? 'Low' : riskScore < 60 ? 'Medium' : 'High';
  const riskColor = riskScore < 30 ? '#28a745' : riskScore < 60 ? '#ffc107' : '#dc3545';

  const minTrades = Math.min(10, trades.length);
  const maxTrades = trades.length;

  return (
    <div className="monte-carlo-simulation">
      <div className="simulation-header">
        <h3>🎲 Monte Carlo Simulation</h3>
        <p className="subtitle">
          Analyze potential outcomes by randomly reordering your historical trades
        </p>
      </div>

      {trades.length < 10 && (
        <div className="warning-message">
          <strong>⚠️ Insufficient Data:</strong> At least 10 trades are required for Monte Carlo simulation.
          Current trades: {trades.length}
        </div>
      )}

      <div className="control-panel">
        <h4>Simulation Parameters</h4>
        
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="numSimulations">
              Number of Simulations
              <span className="control-hint">More simulations = more accurate results</span>
            </label>
            <input
              id="numSimulations"
              type="range"
              min="100"
              max="10000"
              step="100"
              value={numSimulations}
              onChange={(e) => setNumSimulations(parseInt(e.target.value))}
              disabled={loading || trades.length < 10}
            />
            <span className="control-value">{numSimulations.toLocaleString()}</span>
          </div>

          <div className="control-group">
            <label htmlFor="numTrades">
              Trades per Simulation
              <span className="control-hint">Subset of your historical trades</span>
            </label>
            <input
              id="numTrades"
              type="range"
              min={minTrades}
              max={maxTrades}
              step="10"
              value={numTrades}
              onChange={(e) => setNumTrades(parseInt(e.target.value))}
              disabled={loading || trades.length < 10}
            />
            <span className="control-value">{numTrades} / {trades.length}</span>
          </div>
        </div>

        <button
          className="run-button"
          onClick={handleRunSimulation}
          disabled={loading || trades.length < 10}
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              Running Simulation...
            </>
          ) : (
            <>
              <span className="button-icon">▶️</span>
              Run Simulation
            </>
          )}
        </button>

        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      {results && (
        <>
          {/* Histogram Chart */}
          <div className="results-section">
            <h4>Final Equity Distribution</h4>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={histogramData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="range" 
                    label={{ value: 'Final Equity ($)', position: 'insideBottom', offset: -5 }}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis 
                    label={{ value: 'Frequency', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip 
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        const pct = ((data.count / numSimulations) * 100).toFixed(2);
                        return (
                          <div className="custom-tooltip">
                            <p><strong>Equity:</strong> ${parseFloat(data.range).toLocaleString()}</p>
                            <p><strong>Count:</strong> {data.count}</p>
                            <p><strong>Probability:</strong> {pct}%</p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="count" fill="#1f77b4">
                    {histogramData.map((entry, index) => (
                      <rect 
                        key={`bar-${index}`}
                        fill={entry.binStart < initialCapital ? '#dc3545' : '#28a745'}
                      />
                    ))}
                  </Bar>
                  <ReferenceLine 
                    x={initialCapital.toString()} 
                    stroke="#ff7300" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    label={{ value: 'Initial Capital', position: 'top' }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Statistics Panel */}
          <div className="statistics-panel">
            <h4>Simulation Statistics</h4>
            <div className="stats-grid">
              <div className="stat-box">
                <span className="stat-label">Mean Final Equity</span>
                <span className="stat-value">
                  ${results.mean.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="stat-change" style={{ 
                  color: results.mean >= 0 ? '#28a745' : '#dc3545' 
                }}>
                  {results.mean.toFixed(2)}%
                </span>
              </div>

              <div className="stat-box">
                <span className="stat-label">Median Final Equity (50th %ile)</span>
                <span className="stat-value">
                  ${results.percentile50.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="stat-change" style={{ 
                  color: results.percentile50 >= 0 ? '#28a745' : '#dc3545' 
                }}>
                  {results.percentile50.toFixed(2)}%
                </span>
              </div>

              <div className="stat-box">
                <span className="stat-label">Standard Deviation</span>
                <span className="stat-value">
                  ${results.std.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="stat-hint">Volatility measure</span>
              </div>

              <div className="stat-box">
                <span className="stat-label">Best Case (95th %ile)</span>
                <span className="stat-value positive">
                  ${results.percentile95.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="stat-hint">95% chance of doing worse</span>
              </div>

              <div className="stat-box percentile-box">
                <span className="stat-label">Worst Case (5th %ile)</span>
                <span className="stat-value negative">
                  ${results.percentile5.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="stat-hint">95% chance of doing better</span>
              </div>
            </div>
          </div>

          {/* Risk Assessment */}
          <div className="risk-assessment">
            <h4>Risk Assessment</h4>
            <div className="risk-content">
              <div className="risk-score">
                <div className="risk-circle" style={{ borderColor: riskColor }}>
                  <span className="risk-number" style={{ color: riskColor }}>
                    {riskScore.toFixed(0)}
                  </span>
                  <span className="risk-label">{riskLevel} Risk</span>
                </div>
              </div>

              <div className="risk-metrics">
                <div className="risk-metric">
                  <span className="metric-label">Probability of Loss &gt; 10%</span>
                  <span className="metric-value" style={{ 
                    color: results.probabilityLoss10 < 0.2 ? '#28a745' : 
                           results.probabilityLoss10 < 0.4 ? '#ffc107' : '#dc3545' 
                  }}>
                    {(results.probabilityLoss10 * 100).toFixed(2)}%
                  </span>
                  <div className="metric-bar">
                    <div 
                      className="metric-fill"
                      style={{ 
                        width: `${results.probabilityLoss10 * 100}%`,
                        backgroundColor: results.probabilityLoss10 < 0.2 ? '#28a745' : 
                                       results.probabilityLoss10 < 0.4 ? '#ffc107' : '#dc3545'
                      }}
                    ></div>
                  </div>
                </div>

                <div className="risk-metric">
                  <span className="metric-label">Best Case Scenario</span>
                  <span className="metric-value positive">
                    ${results.percentile95.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                  <span className="metric-hint">
                    +{(results.percentile95).toFixed(2)}%
                  </span>
                </div>

                <div className="risk-metric">
                  <span className="metric-label">Worst Case Scenario</span>
                  <span className="metric-value negative">
                    ${results.percentile5.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                  <span className="metric-hint">
                    {(results.percentile5).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
