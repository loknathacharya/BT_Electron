import React from 'react';
import {
  PieChart, Pie, Cell, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Trade, TradeAnalytics } from '../../types/portfolio';
import './TradeAnalyticsDashboard.css';

interface TradeAnalyticsDashboardProps {
  analytics: TradeAnalytics;
  trades: Trade[];
}

const COLORS = {
  takeProfit: '#28a745',
  stopLoss: '#dc3545',
  timeExit: '#ffc107',
  manual: '#6c757d',
  profit: '#28a745',
  loss: '#dc3545',
  neutral: '#1f77b4'
};

export const TradeAnalyticsDashboard: React.FC<TradeAnalyticsDashboardProps> = ({
  analytics,
  trades
}) => {
  // Prepare exit reasons data
  const exitReasonData = Object.entries(analytics.exitReasons).map(([reason, count]) => ({
    name: reason.replace('_', ' ').toUpperCase(),
    value: count,
    percentage: (count / analytics.totalTrades * 100).toFixed(1)
  }));

  const getExitReasonColor = (reason: string): string => {
    switch (reason) {
      case 'TAKE PROFIT':
        return COLORS.takeProfit;
      case 'STOP LOSS':
        return COLORS.stopLoss;
      case 'TIME EXIT':
        return COLORS.timeExit;
      case 'MANUAL':
        return COLORS.manual;
      default:
        return COLORS.neutral;
    }
  };

  // Prepare holding period histogram data
  const holdingPeriodBins: Record<string, number> = {};
  analytics.holdingPeriods.forEach(days => {
    const bin = Math.floor(days / 5) * 5; // Group by 5-day bins
    const key = `${bin}-${bin + 5}`;
    holdingPeriodBins[key] = (holdingPeriodBins[key] || 0) + 1;
  });

  const holdingPeriodData = Object.entries(holdingPeriodBins)
    .map(([range, count]) => ({
      range,
      count,
      binStart: parseInt(range.split('-')[0])
    }))
    .sort((a, b) => a.binStart - b.binStart);

  // Prepare P&L distribution histogram data
  const plBins: Record<string, number> = {};
  analytics.plDistribution.forEach(pl => {
    const bin = Math.floor(pl / 2) * 2; // Group by 2% bins
    const key = `${bin} to ${bin + 2}%`;
    plBins[key] = (plBins[key] || 0) + 1;
  });

  const plDistributionData = Object.entries(plBins)
    .map(([range, count]) => ({
      range,
      count,
      binStart: parseInt(range.split(' ')[0])
    }))
    .sort((a, b) => a.binStart - b.binStart);

  // Prepare P&L timeline data
  const plTimelineData = analytics.plTimeline.map((t, idx) => ({
    index: idx + 1,
    date: new Date(t.date).toLocaleDateString(),
    pl: t.pnlPct,
    symbol: t.symbol,
    reason: t.reason.replace('_', ' ')
  }));

  return (
    <div className="trade-analytics-dashboard">
      <div className="analytics-header">
        <h3>📊 Trade Analytics Dashboard</h3>
        <p className="subtitle">Comprehensive analysis of {analytics.totalTrades} trades</p>
      </div>

      <div className="analytics-grid">
        {/* Exit Reason Pie Chart */}
        <div className="chart-container">
          <h4 className="chart-title">Exit Reason Distribution</h4>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={exitReasonData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={(entry) => `${entry.name}: ${entry.percentage}%`}
              >
                {exitReasonData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={getExitReasonColor(entry.name)} 
                  />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Holding Period Histogram */}
        <div className="chart-container">
          <h4 className="chart-title">Holding Period Distribution</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={holdingPeriodData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="range" label={{ value: 'Days Held', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'Frequency', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Bar dataKey="count" fill={COLORS.neutral} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* P&L Distribution */}
        <div className="chart-container">
          <h4 className="chart-title">P&L Distribution (%)</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={plDistributionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="range" label={{ value: 'Profit/Loss (%)', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'Frequency', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Bar dataKey="count" fill={COLORS.neutral}>
                {plDistributionData.map((entry, index) => (
                  <Cell 
                    key={`bar-cell-${index}`} 
                    fill={entry.binStart >= 0 ? COLORS.profit : COLORS.loss}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* P&L Over Time Scatter */}
        <div className="chart-container">
          <h4 className="chart-title">P&L Over Time</h4>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="index" 
                label={{ value: 'Trade Number', position: 'insideBottom', offset: -5 }} 
              />
              <YAxis 
                label={{ value: 'Profit/Loss (%)', angle: -90, position: 'insideLeft' }} 
              />
              <Tooltip 
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="custom-tooltip">
                        <p><strong>{data.symbol}</strong></p>
                        <p>Date: {data.date}</p>
                        <p>P&L: {data.pl.toFixed(2)}%</p>
                        <p>Exit: {data.reason}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter 
                data={plTimelineData} 
                fill={COLORS.neutral}
                shape="circle"
              >
                {plTimelineData.map((entry, index) => (
                  <Cell 
                    key={`scatter-cell-${index}`} 
                    fill={entry.pl >= 0 ? COLORS.profit : COLORS.loss}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Summary Statistics */}
      <div className="analytics-summary">
        <h4>Key Statistics</h4>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-label">Win Rate</span>
            <span className="stat-value positive">{(analytics.winRate * 100).toFixed(1)}%</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Profit Factor</span>
            <span className="stat-value">{analytics.profitFactor.toFixed(2)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Avg Win</span>
            <span className="stat-value positive">{analytics.averageWin.toFixed(2)}%</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Avg Loss</span>
            <span className="stat-value negative">{analytics.averageLoss.toFixed(2)}%</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Max Consecutive Wins</span>
            <span className="stat-value">{analytics.maxConsecutiveWins}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Max Consecutive Losses</span>
            <span className="stat-value">{analytics.maxConsecutiveLosses}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
