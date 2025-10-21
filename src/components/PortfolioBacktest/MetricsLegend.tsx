import React, { useState } from 'react';
import './MetricsLegend.css';

export const MetricsLegend: React.FC = () => {
  const [showLegend, setShowLegend] = useState(false);

  const metrics = [
    {
      name: 'Total Return',
      description: 'Overall profit/loss as percentage of initial capital',
      example: '+45.2%'
    },
    {
      name: 'Annualized Return',
      description: 'Return scaled to annual basis for comparison',
      example: '+18.3%'
    },
    {
      name: 'Sharpe Ratio',
      description: 'Risk-adjusted return (higher is better)',
      example: '1.82',
      guide: '< 1.0 Poor | 1.0-2.0 Good | > 2.0 Excellent'
    },
    {
      name: 'Max Drawdown',
      description: 'Largest peak-to-trough decline during period',
      example: '-12.3%',
      guide: 'Measure of downside risk'
    },
    {
      name: 'Win Rate',
      description: 'Percentage of profitable trades',
      example: '62%'
    },
    {
      name: 'Profit Factor',
      description: 'Gross profit divided by gross loss',
      example: '2.1',
      guide: '> 1.5 Good | > 2.0 Excellent'
    },
    {
      name: 'Volatility',
      description: 'Standard deviation of returns',
      example: '15.2%'
    },
    {
      name: 'Diversification Ratio',
      description: 'Ratio of weighted average volatility to portfolio volatility',
      example: '1.45',
      guide: '> 1.0 indicates diversification benefit'
    }
  ];

  return (
    <div className="metrics-legend">
      <button 
        className="legend-toggle"
        onClick={() => setShowLegend(!showLegend)}
        title="Show metrics explanation"
      >
        ℹ️ Metrics Legend
      </button>
      
      {showLegend && (
        <div className="legend-popup">
          <div className="legend-header">
            <h4>Key Metrics Explained</h4>
            <button 
              className="close-button"
              onClick={() => setShowLegend(false)}
            >
              ×
            </button>
          </div>
          
          <div className="legend-content">
            {metrics.map((metric, idx) => (
              <div key={idx} className="metric-item">
                <div className="metric-name">{metric.name}</div>
                <div className="metric-description">{metric.description}</div>
                {metric.example && (
                  <div className="metric-example">Example: <strong>{metric.example}</strong></div>
                )}
                {metric.guide && (
                  <div className="metric-guide">Guide: {metric.guide}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
