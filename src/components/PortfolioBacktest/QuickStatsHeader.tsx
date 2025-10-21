import React from 'react';
import './QuickStatsHeader.css';

interface QuickStatsHeaderProps {
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  totalTrades: number;
  winRate: number;
}

export const QuickStatsHeader: React.FC<QuickStatsHeaderProps> = ({
  totalReturn,
  sharpeRatio,
  maxDrawdown,
  totalTrades,
  winRate
}) => {
  // Determine overall performance rating
  const getPerformanceRating = () => {
    if (totalReturn < 0) return { rating: '❌ Loss', color: '#dc3545' };
    if (sharpeRatio > 2) return { rating: '⭐⭐⭐ Excellent', color: '#28a745' };
    if (sharpeRatio > 1) return { rating: '⭐⭐ Good', color: '#17a2b8' };
    if (sharpeRatio > 0) return { rating: '⭐ Fair', color: '#ffc107' };
    return { rating: '❌ Poor', color: '#dc3545' };
  };

  const rating = getPerformanceRating();

  return (
    <div className="quick-stats-header">
      <div className="stats-content">
        <div className="stat-group">
          <div className="stat">
            <span className="stat-label">Return</span>
            <span className={`stat-value ${totalReturn >= 0 ? 'positive' : 'negative'}`}>
              {(totalReturn * 100).toFixed(1)}%
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Sharpe</span>
            <span className="stat-value">{sharpeRatio.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Max DD</span>
            <span className="stat-value negative">{(maxDrawdown * 100).toFixed(1)}%</span>
          </div>
          <div className="stat">
            <span className="stat-label">Win Rate</span>
            <span className="stat-value">{(winRate * 100).toFixed(1)}%</span>
          </div>
          <div className="stat">
            <span className="stat-label">Trades</span>
            <span className="stat-value">{totalTrades}</span>
          </div>
        </div>
        
        <div className="rating-box" style={{ borderLeftColor: rating.color }}>
          <span className="rating-label">Overall Rating</span>
          <span className="rating-value">{rating.rating}</span>
        </div>
      </div>
    </div>
  );
};
