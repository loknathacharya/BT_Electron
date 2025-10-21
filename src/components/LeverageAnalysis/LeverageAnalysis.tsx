import React from 'react';
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine
} from 'recharts';
import { LeverageMetrics } from '../../types/portfolio';
import './LeverageAnalysis.css';

interface LeverageAnalysisProps {
  metrics: LeverageMetrics;
  leverageTimeline: Array<{
    date: string;
    leverage: number;
  }>;
  leverageVsPerformance: Array<{
    leverage: number;
    pnlPct: number;
    symbol: string;
  }>;
}

export const LeverageAnalysis: React.FC<LeverageAnalysisProps> = ({
  metrics,
  leverageTimeline,
  leverageVsPerformance
}) => {
  // Prepare leverage distribution data
  const distributionData = Object.entries(metrics.leverageDistribution)
    .map(([range, count]) => ({
      range,
      count,
      leverage: parseFloat(range.split('-')[0])
    }))
    .sort((a, b) => a.leverage - b.leverage);

  // Calculate risk level
  const getRiskLevel = (score: number) => {
    if (score < 30) return { level: 'Low', color: '#28a745' };
    if (score < 60) return { level: 'Medium', color: '#ffc107' };
    return { level: 'High', color: '#dc3545' };
  };

  const riskInfo = getRiskLevel(metrics.leverageRiskScore);

  return (
    <div className="leverage-analysis">
      <div className="leverage-header">
        <h3>⚡ Leverage Analysis</h3>
        <p className="subtitle">Analyze leverage usage and its impact on performance</p>
      </div>

      {/* Metrics Summary */}
      <div className="metrics-summary">
        <h4>Leverage Metrics</h4>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon">📊</div>
            <div className="metric-content">
              <span className="metric-label">Average Leverage</span>
              <span className="metric-value">{metrics.averageLeverage.toFixed(2)}x</span>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">⚠️</div>
            <div className="metric-content">
              <span className="metric-label">Maximum Leverage</span>
              <span className="metric-value highlight">{metrics.maxLeverage.toFixed(2)}x</span>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">🔥</div>
            <div className="metric-content">
              <span className="metric-label">High Leverage Trades</span>
              <span className="metric-value">{metrics.highLeverageTrades}</span>
              <span className="metric-hint">Leverage &gt; 2x</span>
            </div>
          </div>

          <div className="metric-card risk-card" style={{ borderLeftColor: riskInfo.color }}>
            <div className="metric-icon">🎯</div>
            <div className="metric-content">
              <span className="metric-label">Risk Score</span>
              <span className="metric-value" style={{ color: riskInfo.color }}>
                {metrics.leverageRiskScore.toFixed(0)} / 100
              </span>
              <span className="metric-hint" style={{ color: riskInfo.color }}>
                {riskInfo.level} Risk
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Leverage Distribution */}
        <div className="chart-container">
          <h4 className="chart-title">Leverage Distribution</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={distributionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="range" 
                label={{ value: 'Leverage Range', position: 'insideBottom', offset: -5 }}
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                label={{ value: 'Number of Trades', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip">
                        <p><strong>Leverage:</strong> {data.range}x</p>
                        <p><strong>Trades:</strong> {data.count}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="count">
                {distributionData.map((entry, index) => (
                  <rect
                    key={`bar-${index}`}
                    fill={
                      entry.leverage < 1.5 ? '#28a745' :
                      entry.leverage < 2.5 ? '#ffc107' :
                      '#dc3545'
                    }
                  />
                ))}
              </Bar>
              <ReferenceLine 
                x="2.0-2.5" 
                stroke="#dc3545" 
                strokeDasharray="5 5"
                label={{ value: 'High Risk Threshold', position: 'top', fontSize: 11 }}
              />
            </BarChart>
          </ResponsiveContainer>
          <div className="chart-note">
            <span className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#28a745' }}></span>
              Low (≤1.5x)
            </span>
            <span className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#ffc107' }}></span>
              Medium (1.5-2.5x)
            </span>
            <span className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#dc3545' }}></span>
              High (&gt;2.5x)
            </span>
          </div>
        </div>

        {/* Leverage vs Performance Scatter */}
        <div className="chart-container">
          <h4 className="chart-title">Leverage vs Performance</h4>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="leverage"
                type="number"
                label={{ value: 'Leverage (x)', position: 'insideBottom', offset: -5 }}
              />
              <YAxis 
                dataKey="pnlPct"
                type="number"
                label={{ value: 'P&L (%)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip">
                        <p><strong>{data.symbol}</strong></p>
                        <p><strong>Leverage:</strong> {data.leverage.toFixed(2)}x</p>
                        <p><strong>P&L:</strong> {data.pnlPct.toFixed(2)}%</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter data={leverageVsPerformance} fill="#1f77b4">
                {leverageVsPerformance.map((entry, index) => (
                  <rect
                    key={`scatter-${index}`}
                    fill={entry.pnlPct >= 0 ? '#28a745' : '#dc3545'}
                  />
                ))}
              </Scatter>
              <ReferenceLine y={0} stroke="#dc3545" strokeDasharray="5 5" />
            </ScatterChart>
          </ResponsiveContainer>
          <div className="chart-note">
            ℹ️ Shows relationship between leverage used and trade profitability
          </div>
        </div>

        {/* Leverage Timeline */}
        <div className="chart-container full-width">
          <h4 className="chart-title">Leverage Over Time</h4>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={leverageTimeline}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date"
                label={{ value: 'Date', position: 'insideBottom', offset: -5 }}
                tick={{ fontSize: 11 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis 
                label={{ value: 'Leverage (x)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip">
                        <p><strong>Date:</strong> {data.date}</p>
                        <p><strong>Leverage:</strong> {data.leverage.toFixed(2)}x</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line 
                type="monotone" 
                dataKey="leverage" 
                stroke="#007bff" 
                strokeWidth={2}
                dot={{ fill: '#007bff', r: 4 }}
                activeDot={{ r: 6 }}
              />
              <ReferenceLine 
                y={metrics.averageLeverage} 
                stroke="#28a745" 
                strokeDasharray="5 5"
                label={{ 
                  value: `Avg: ${metrics.averageLeverage.toFixed(2)}x`, 
                  position: 'right',
                  fill: '#28a745',
                  fontSize: 12
                }}
              />
              <ReferenceLine 
                y={2.0} 
                stroke="#dc3545" 
                strokeDasharray="5 5"
                label={{ 
                  value: 'High Risk (2x)', 
                  position: 'right',
                  fill: '#dc3545',
                  fontSize: 12
                }}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="chart-note">
            ℹ️ Track how leverage changes across your trading history
          </div>
        </div>
      </div>

      {/* Risk Assessment Panel */}
      <div className="risk-panel">
        <h4>⚠️ Leverage Risk Assessment</h4>
        <div className="risk-content">
          <div className="risk-gauge">
            <div 
              className="gauge-fill" 
              style={{ 
                width: `${metrics.leverageRiskScore}%`,
                backgroundColor: riskInfo.color
              }}
            >
              <span className="gauge-text">{metrics.leverageRiskScore.toFixed(0)}%</span>
            </div>
          </div>

          <div className="risk-details">
            <div className="risk-item">
              <span className="risk-icon">
                {riskInfo.level === 'Low' ? '✅' : riskInfo.level === 'Medium' ? '⚠️' : '🚨'}
              </span>
              <div className="risk-text">
                <span className="risk-level" style={{ color: riskInfo.color }}>
                  {riskInfo.level} Risk Level
                </span>
                <span className="risk-description">
                  {riskInfo.level === 'Low' && 'Your leverage usage is conservative and well-controlled.'}
                  {riskInfo.level === 'Medium' && 'Moderate leverage usage. Monitor high-leverage trades carefully.'}
                  {riskInfo.level === 'High' && 'High leverage usage detected. Consider reducing position sizes or leverage.'}
                </span>
              </div>
            </div>

            {metrics.highLeverageTrades > 0 && (
              <div className="risk-warning">
                <strong>⚠️ Warning:</strong> {metrics.highLeverageTrades} trades used leverage above 2x.
                High leverage amplifies both gains and losses.
              </div>
            )}

            {metrics.maxLeverage > 3 && (
              <div className="risk-warning critical">
                <strong>🚨 Critical:</strong> Maximum leverage of {metrics.maxLeverage.toFixed(2)}x detected.
                Extremely high leverage can lead to rapid account depletion.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
