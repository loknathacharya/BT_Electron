import React, { useState } from 'react';

const ViewResults: React.FC = () => {
  const [selectedMetric, setSelectedMetric] = useState('overview');

  const mockResults = {
    overview: {
      totalReturn: 15.7,
      maxDrawdown: -8.2,
      winRate: 62.5,
      profitFactor: 1.85,
      totalTrades: 48,
      sharpeRatio: 1.23,
    },
    trades: [
      {
        id: 1,
        entryDate: '2024-01-15',
        exitDate: '2024-01-22',
        entryPrice: 150.25,
        exitPrice: 158.75,
        quantity: 100,
        side: 'Long',
        pnl: 850,
        commission: 2.50,
      },
      {
        id: 2,
        entryDate: '2024-01-23',
        exitDate: '2024-01-25',
        entryPrice: 159.00,
        exitPrice: 155.80,
        quantity: 100,
        side: 'Long',
        pnl: -320,
        commission: 2.50,
      },
      {
        id: 3,
        entryDate: '2024-01-26',
        exitDate: '2024-02-02',
        entryPrice: 156.00,
        exitPrice: 162.30,
        quantity: 100,
        side: 'Long',
        pnl: 630,
        commission: 2.50,
      },
    ],
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>View Results</h2>
        <p>
          Analyze your backtesting results with detailed performance metrics,
          trade logs, and equity curve visualization.
        </p>
      </div>

      <div className="results-container">
        <div className="results-navigation">
          <button
            className={`nav-button ${selectedMetric === 'overview' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('overview')}
          >
            📊 Overview
          </button>
          <button
            className={`nav-button ${selectedMetric === 'trades' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('trades')}
          >
            📋 Trade Log
          </button>
          <button
            className={`nav-button ${selectedMetric === 'charts' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('charts')}
          >
            📈 Charts
          </button>
        </div>

        {selectedMetric === 'overview' && (
          <div className="metrics-overview">
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-label">Total Return</div>
                <div className={`metric-value ${mockResults.overview.totalReturn >= 0 ? 'positive' : 'negative'}`}>
                  {formatPercentage(mockResults.overview.totalReturn)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Max Drawdown</div>
                <div className="metric-value negative">
                  {formatPercentage(mockResults.overview.maxDrawdown)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Win Rate</div>
                <div className="metric-value positive">
                  {mockResults.overview.winRate.toFixed(1)}%
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Profit Factor</div>
                <div className="metric-value positive">
                  {mockResults.overview.profitFactor.toFixed(2)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Total Trades</div>
                <div className="metric-value">
                  {mockResults.overview.totalTrades}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Sharpe Ratio</div>
                <div className="metric-value positive">
                  {mockResults.overview.sharpeRatio.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedMetric === 'trades' && (
          <div className="trade-log">
            <div className="table-container">
              <table className="trade-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th>Side</th>
                    <th>Quantity</th>
                    <th>P&L</th>
                    <th>Commission</th>
                  </tr>
                </thead>
                <tbody>
                  {mockResults.trades.map((trade) => (
                    <tr key={trade.id}>
                      <td>
                        <div>{trade.entryDate}</div>
                        <div className="exit-date">→ {trade.exitDate}</div>
                      </td>
                      <td>{formatCurrency(trade.entryPrice)}</td>
                      <td>{formatCurrency(trade.exitPrice)}</td>
                      <td>
                        <span className={`side-badge ${trade.side.toLowerCase()}`}>
                          {trade.side}
                        </span>
                      </td>
                      <td>{trade.quantity}</td>
                      <td className={trade.pnl >= 0 ? 'positive' : 'negative'}>
                        {formatCurrency(trade.pnl)}
                      </td>
                      <td>{formatCurrency(trade.commission)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {selectedMetric === 'charts' && (
          <div className="charts-section">
            <div className="chart-placeholder">
              <div className="placeholder-content">
                <div className="placeholder-icon">📊</div>
                <h3>Equity Curve Chart</h3>
                <p>Interactive equity curve visualization will be displayed here</p>
                <div className="chart-features">
                  <ul>
                    <li>📈 Portfolio value over time</li>
                    <li>📊 Benchmark comparison</li>
                    <li>🔍 Zoom and pan controls</li>
                    <li>📥 Export to PNG/PDF</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="results-actions">
          <button className="btn">Export Results</button>
          <button className="btn btn-secondary">Save Report</button>
          <button className="btn btn-secondary">Compare Strategies</button>
        </div>
      </div>
    </div>
  );
};

export default ViewResults;