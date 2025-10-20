import React, { useState } from 'react';
import './RebalancingTimeline.css';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';

interface RebalancePeriod {
  date: string;
  period: number;
  weights: { [symbol: string]: number };
  trades: { [symbol: string]: { action: string; shares: number; value: number; deviation: number } };
  totalValue: number;
}

interface RebalancingTimelineProps {
  symbols: string[];
  initialWeights: { [symbol: string]: number };
  equityCurve: { timestamps: number[]; equity: number[] };
  symbolEquities: { [symbol: string]: number[] };
  rebalanceFrequency: 'monthly' | 'quarterly' | 'yearly';
  rebalanceThreshold: number;
}

const COLOR_PALETTE = [
  '#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#a4de6c',
  '#d0ed57', '#83a6ed', '#8dd1e1', '#d084d0', '#f4a460'
];

export const RebalancingTimeline: React.FC<RebalancingTimelineProps> = ({
  symbols,
  initialWeights,
  equityCurve,
  symbolEquities,
  rebalanceFrequency,
  rebalanceThreshold
}) => {
  const [selectedPeriod, setSelectedPeriod] = useState<number | null>(null);

  // Calculate rebalancing periods
  const calculateRebalancingPeriods = (): RebalancePeriod[] => {
    const periods: RebalancePeriod[] = [];
    
    // Determine step size based on frequency (assuming daily data)
    const stepSizes = {
      'monthly': 21, // ~21 trading days
      'quarterly': 63, // ~63 trading days
      'yearly': 252  // ~252 trading days
    };
    const stepSize = stepSizes[rebalanceFrequency];
    
    // Start from beginning of equity curve
    let periodNum = 0;
    for (let i = 0; i < equityCurve.timestamps.length; i += stepSize) {
      const idx = Math.min(i, equityCurve.timestamps.length - 1);
      const timestamp = equityCurve.timestamps[idx];
      const totalValue = equityCurve.equity[idx];
      
      // Calculate current allocation based on symbol equities
      const currentValues: { [symbol: string]: number } = {};
      symbols.forEach(symbol => {
        const equity = symbolEquities[symbol];
        if (equity && equity[idx] !== undefined) {
          currentValues[symbol] = equity[idx];
        } else {
          currentValues[symbol] = 0;
        }
      });
      
      // Calculate current weights
      const currentWeights: { [symbol: string]: number } = {};
      const currentTotal = Object.values(currentValues).reduce((sum, v) => sum + v, 0);
      if (currentTotal > 0) {
        symbols.forEach(symbol => {
          currentWeights[symbol] = currentValues[symbol] / currentTotal;
        });
      } else {
        symbols.forEach(symbol => {
          currentWeights[symbol] = initialWeights[symbol];
        });
      }
      
      // Calculate trades needed to rebalance
      const trades: { [symbol: string]: any } = {};
      let needsRebalance = false;
      
      symbols.forEach(symbol => {
        const currentWeight = currentWeights[symbol] || 0;
        const targetWeight = initialWeights[symbol] || 0;
        const deviation = Math.abs(currentWeight - targetWeight);
        
        if (deviation > rebalanceThreshold) {
          needsRebalance = true;
          const targetValue = totalValue * targetWeight;
          const currentValue = currentValues[symbol] || 0;
          const deltaValue = targetValue - currentValue;
          
          trades[symbol] = {
            action: deltaValue > 0 ? 'buy' : 'sell',
            shares: Math.abs(deltaValue / 100), // Simplified
            value: Math.abs(deltaValue),
            deviation: deviation
          };
        }
      });
      
      // Only add period if rebalancing is needed (or first period)
      if (needsRebalance || periodNum === 0) {
        periods.push({
          date: new Date(timestamp * 1000).toISOString().split('T')[0],
          period: periodNum,
          weights: currentWeights,
          trades: trades,
          totalValue: totalValue
        });
        periodNum++;
      }
    }
    
    return periods;
  };

  const rebalancePeriods = calculateRebalancingPeriods();

  // Prepare data for weight evolution chart
  const weightEvolutionData = rebalancePeriods.map(period => ({
    date: period.date,
    period: period.period,
    ...period.weights
  }));

  // Prepare data for trade volume chart (selected period)
  const getTradeVolumeData = (period: RebalancePeriod | null) => {
    if (!period) return [];
    
    return symbols.map(symbol => {
      const trade = period.trades[symbol];
      return {
        symbol,
        value: trade ? trade.value : 0,
        action: trade ? trade.action : 'none'
      };
    }).filter(item => item.value > 0);
  };

  const selected = selectedPeriod !== null ? rebalancePeriods[selectedPeriod] : null;
  const tradeVolumeData = getTradeVolumeData(selected);

  return (
    <div className="rebalancing-timeline">
      <h3>Rebalancing Timeline</h3>
      
      <div className="rebalance-summary">
        <div className="summary-card">
          <div className="card-label">Total Periods</div>
          <div className="card-value">{rebalancePeriods.length}</div>
        </div>
        <div className="summary-card">
          <div className="card-label">Frequency</div>
          <div className="card-value">{rebalanceFrequency}</div>
        </div>
        <div className="summary-card">
          <div className="card-label">Threshold</div>
          <div className="card-value">{(rebalanceThreshold * 100).toFixed(1)}%</div>
        </div>
      </div>

      {/* Weight Evolution Over Time */}
      <div className="chart-section">
        <h4>Portfolio Weight Evolution</h4>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={weightEvolutionData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={70}
            />
            <YAxis 
              label={{ value: 'Weight', angle: -90, position: 'insideLeft' }}
              domain={[0, 1]}
            />
            <Tooltip formatter={(value: number) => `${(value * 100).toFixed(2)}%`} />
            <Legend />
            {symbols.map((symbol, idx) => (
              <Line
                key={symbol}
                type="stepAfter"
                dataKey={symbol}
                stroke={COLOR_PALETTE[idx % COLOR_PALETTE.length]}
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Rebalancing Events Table */}
      <div className="rebalance-table-section">
        <h4>Rebalancing Events</h4>
        <table className="rebalance-table">
          <thead>
            <tr>
              <th>Period</th>
              <th>Date</th>
              <th>Portfolio Value</th>
              <th>Trades Required</th>
              <th>Max Deviation</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rebalancePeriods.map((period, idx) => {
              const tradeCount = Object.keys(period.trades).length;
              const maxDeviation = Math.max(
                ...Object.values(period.trades).map(t => t.deviation),
                0
              );
              
              return (
                <tr 
                  key={idx}
                  className={selectedPeriod === idx ? 'selected' : ''}
                  onClick={() => setSelectedPeriod(idx)}
                >
                  <td>{period.period}</td>
                  <td>{period.date}</td>
                  <td>${period.totalValue.toFixed(2)}</td>
                  <td>{tradeCount}</td>
                  <td className={maxDeviation > rebalanceThreshold * 2 ? 'high-deviation' : ''}>
                    {(maxDeviation * 100).toFixed(2)}%
                  </td>
                  <td>
                    <button 
                      className="view-details-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedPeriod(idx);
                      }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Selected Period Details */}
      {selected && (
        <div className="period-details">
          <h4>Period {selected.period} Details - {selected.date}</h4>
          
          <div className="details-grid">
            {/* Current Weights */}
            <div className="details-section">
              <h5>Current Allocation</h5>
              <table className="weights-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Weight</th>
                    <th>Target</th>
                    <th>Deviation</th>
                  </tr>
                </thead>
                <tbody>
                  {symbols.map(symbol => {
                    const current = selected.weights[symbol] || 0;
                    const target = initialWeights[symbol] || 0;
                    const deviation = current - target;
                    
                    return (
                      <tr key={symbol}>
                        <td><strong>{symbol}</strong></td>
                        <td>{(current * 100).toFixed(2)}%</td>
                        <td>{(target * 100).toFixed(2)}%</td>
                        <td className={Math.abs(deviation) > rebalanceThreshold ? 'out-of-range' : ''}>
                          {deviation > 0 ? '+' : ''}{(deviation * 100).toFixed(2)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Required Trades */}
            <div className="details-section">
              <h5>Required Trades</h5>
              {Object.keys(selected.trades).length > 0 ? (
                <table className="trades-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Action</th>
                      <th>Value</th>
                      <th>Deviation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(selected.trades).map(([symbol, trade]) => (
                      <tr key={symbol}>
                        <td><strong>{symbol}</strong></td>
                        <td className={`action-${trade.action}`}>
                          {trade.action.toUpperCase()}
                        </td>
                        <td>${trade.value.toFixed(2)}</td>
                        <td>{(trade.deviation * 100).toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="no-trades">No rebalancing needed</p>
              )}
            </div>
          </div>

          {/* Trade Volume Chart */}
          {tradeVolumeData.length > 0 && (
            <div className="chart-section">
              <h5>Trade Volumes</h5>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={tradeVolumeData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="symbol" />
                  <YAxis label={{ value: 'Trade Value ($)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
                  <Bar dataKey="value">
                    {tradeVolumeData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`}
                        fill={entry.action === 'buy' ? '#82ca9d' : '#ff7c7c'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="chart-legend">
                <div className="legend-item">
                  <span className="legend-color" style={{ backgroundColor: '#82ca9d' }}></span>
                  <span>Buy</span>
                </div>
                <div className="legend-item">
                  <span className="legend-color" style={{ backgroundColor: '#ff7c7c' }}></span>
                  <span>Sell</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
