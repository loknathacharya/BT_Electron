import React from 'react';
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { InvestedCapitalPoint, formatCurrency, formatPercentage } from '../../types/portfolio';
import './InvestedCapital.css';

interface InvestedCapitalProps {
  timeline: InvestedCapitalPoint[];
  initialCapital: number;
}

export const InvestedCapital: React.FC<InvestedCapitalProps> = ({
  timeline,
  initialCapital
}) => {
  // Calculate summary statistics
  const avgInvested = timeline.reduce((sum, point) => sum + point.investedValue, 0) / timeline.length;
  const avgUtilization = timeline.reduce((sum, point) => sum + point.utilizationPct, 0) / timeline.length;
  const maxInvested = Math.max(...timeline.map(p => p.investedValue));
  const maxUtilization = Math.max(...timeline.map(p => p.utilizationPct));

  // Find peak utilization point
  const peakPoint = timeline.find(p => p.utilizationPct === maxUtilization);

  // Prepare chart data
  const chartData = timeline.map(point => ({
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    fullDate: point.date,
    invested: point.investedValue,
    available: point.availableCash,
    utilizationPct: point.utilizationPct,
    totalValue: point.totalValue
  }));

  // Calculate capital allocation breakdown
  const lastPoint = timeline[timeline.length - 1];
  const allocations = [
    {
      category: 'Invested in Trades',
      amount: lastPoint.investedValue,
      percentage: lastPoint.utilizationPct,
      color: '#007bff'
    },
    {
      category: 'Available Cash',
      amount: lastPoint.availableCash,
      percentage: 100 - lastPoint.utilizationPct,
      color: '#28a745'
    }
  ];

  return (
    <div className="invested-capital">
      <div className="capital-header">
        <h3>💰 Invested Capital Analysis</h3>
        <p className="subtitle">Track capital allocation and utilization over time</p>
      </div>

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="capital-card">
          <div className="card-icon">💵</div>
          <div className="card-content">
            <span className="card-label">Initial Capital</span>
            <span className="card-value">{formatCurrency(initialCapital)}</span>
          </div>
        </div>

        <div className="capital-card">
          <div className="card-icon">📊</div>
          <div className="card-content">
            <span className="card-label">Avg Invested</span>
            <span className="card-value">{formatCurrency(avgInvested)}</span>
            <span className="card-hint">{formatPercentage(avgUtilization)} utilization</span>
          </div>
        </div>

        <div className="capital-card">
          <div className="card-icon">🔝</div>
          <div className="card-content">
            <span className="card-label">Peak Invested</span>
            <span className="card-value highlight">{formatCurrency(maxInvested)}</span>
            <span className="card-hint">{formatPercentage(maxUtilization)} utilization</span>
          </div>
        </div>

        <div className="capital-card">
          <div className="card-icon">💳</div>
          <div className="card-content">
            <span className="card-label">Current Available</span>
            <span className="card-value positive">{formatCurrency(lastPoint.availableCash)}</span>
            <span className="card-hint">{formatPercentage(100 - lastPoint.utilizationPct)}</span>
          </div>
        </div>
      </div>

      {/* Capital Timeline Chart */}
      <div className="chart-section">
        <h4>Capital Allocation Over Time</h4>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="investedGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#007bff" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#007bff" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="availableGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#28a745" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#28a745" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
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
                label={{ value: 'Capital ($)', angle: -90, position: 'insideLeft' }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip">
                        <p className="tooltip-date"><strong>{data.fullDate}</strong></p>
                        <p className="tooltip-invested">
                          <strong>Invested:</strong> {formatCurrency(data.invested)}
                        </p>
                        <p className="tooltip-available">
                          <strong>Available:</strong> {formatCurrency(data.available)}
                        </p>
                        <p className="tooltip-util">
                          <strong>Utilization:</strong> {formatPercentage(data.utilizationPct)}
                        </p>
                        <p className="tooltip-trades">
                          <strong>Active Trades:</strong> {data.activeTrades}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend 
                verticalAlign="top"
                height={36}
                iconType="rect"
              />
              <Area
                type="monotone"
                dataKey="invested"
                stackId="1"
                stroke="#007bff"
                fill="url(#investedGradient)"
                name="Invested Capital"
              />
              <Area
                type="monotone"
                dataKey="available"
                stackId="1"
                stroke="#28a745"
                fill="url(#availableGradient)"
                name="Available Cash"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Utilization Timeline */}
      <div className="chart-section">
        <h4>Capital Utilization %</h4>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
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
                label={{ value: 'Utilization (%)', angle: -90, position: 'insideLeft' }}
                domain={[0, 100]}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip">
                        <p><strong>{data.fullDate}</strong></p>
                        <p><strong>Utilization:</strong> {formatPercentage(data.utilizationPct)}</p>
                        <p><strong>Active Trades:</strong> {data.activeTrades}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line 
                type="monotone" 
                dataKey="utilizationPct" 
                stroke="#ff6b35" 
                strokeWidth={2}
                dot={{ fill: '#ff6b35', r: 3 }}
                activeDot={{ r: 5 }}
                name="Utilization %"
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="utilization-legend">
            <div className="util-range low">
              <span className="util-color"></span>
              <span className="util-text">Low (&lt;50%)</span>
            </div>
            <div className="util-range medium">
              <span className="util-color"></span>
              <span className="util-text">Medium (50-80%)</span>
            </div>
            <div className="util-range high">
              <span className="util-color"></span>
              <span className="util-text">High (&gt;80%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Allocation Breakdown Table */}
      <div className="allocation-breakdown">
        <h4>Current Capital Allocation</h4>
        <div className="allocation-table">
          <div className="table-header">
            <span className="col-category">Category</span>
            <span className="col-amount">Amount</span>
            <span className="col-percentage">Percentage</span>
            <span className="col-visual">Visual</span>
          </div>
          {allocations.map((allocation, index) => (
            <div key={index} className="table-row">
              <span className="col-category">
                <span 
                  className="category-indicator" 
                  style={{ backgroundColor: allocation.color }}
                ></span>
                {allocation.category}
              </span>
              <span className="col-amount">{formatCurrency(allocation.amount)}</span>
              <span className="col-percentage">{formatPercentage(allocation.percentage)}</span>
              <span className="col-visual">
                <div className="visual-bar">
                  <div 
                    className="visual-fill" 
                    style={{ 
                      width: `${allocation.percentage}%`,
                      backgroundColor: allocation.color
                    }}
                  ></div>
                </div>
              </span>
            </div>
          ))}
          <div className="table-footer">
            <span className="col-category"><strong>Total</strong></span>
            <span className="col-amount">
              <strong>{formatCurrency(lastPoint.investedValue + lastPoint.availableCash)}</strong>
            </span>
            <span className="col-percentage"><strong>100%</strong></span>
            <span className="col-visual"></span>
          </div>
        </div>
      </div>

      {/* Insights Panel */}
      <div className="insights-panel">
        <h4>💡 Capital Insights</h4>
        <div className="insights-grid">
          <div className="insight-card">
            <span className="insight-icon">
              {avgUtilization < 50 ? '⚠️' : avgUtilization < 80 ? '✅' : '🔥'}
            </span>
            <div className="insight-content">
              <span className="insight-title">Average Utilization</span>
              <span className="insight-text">
                {avgUtilization < 50 && 
                  `Your average utilization of ${formatPercentage(avgUtilization)} suggests conservative capital deployment. Consider increasing position sizes if comfortable with risk.`
                }
                {avgUtilization >= 50 && avgUtilization < 80 &&
                  `Your average utilization of ${formatPercentage(avgUtilization)} indicates balanced capital management with good risk control.`
                }
                {avgUtilization >= 80 &&
                  `Your average utilization of ${formatPercentage(avgUtilization)} is quite high. Ensure you have sufficient reserves for opportunities and risk management.`
                }
              </span>
            </div>
          </div>

          {peakPoint && (
            <div className="insight-card">
              <span className="insight-icon">🔝</span>
              <div className="insight-content">
                <span className="insight-title">Peak Utilization</span>
                <span className="insight-text">
                  Maximum utilization of {formatPercentage(maxUtilization)} occurred on{' '}
                  {new Date(peakPoint.date).toLocaleDateString()}.
                  {maxUtilization > 90 && ' Consider keeping some dry powder for new opportunities.'}
                </span>
              </div>
            </div>
          )}

          <div className="insight-card">
            <span className="insight-icon">📈</span>
            <div className="insight-content">
              <span className="insight-title">Capital Deployment</span>
              <span className="insight-text">
                Currently {formatCurrency(lastPoint.investedValue)} deployed with {formatCurrency(lastPoint.availableCash)} available.
                {lastPoint.availableCash > initialCapital * 0.3 &&
                  ' You have significant capital available for new positions.'
                }
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
