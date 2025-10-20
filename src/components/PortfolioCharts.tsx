import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import './PortfolioCharts.css';

interface EquityCurveData {
  timestamp: string;
  portfolioValue: number;
  [key: string]: number | string; // For individual symbol curves
}

interface PortfolioEquityCurveProps {
  portfolioEquityCurve: { timestamp: string; value: number }[];
  symbolEquityCurves?: Record<string, { timestamp: string; value: number }[]>;
  symbols?: string[];
}

export const PortfolioEquityCurve: React.FC<PortfolioEquityCurveProps> = ({
  portfolioEquityCurve,
  symbolEquityCurves,
  symbols = []
}) => {
  // Transform data for Recharts
  const chartData: EquityCurveData[] = portfolioEquityCurve.map((point, idx) => {
    const dataPoint: EquityCurveData = {
      timestamp: new Date(point.timestamp).toLocaleDateString(),
      portfolioValue: point.value
    };

    // Add individual symbol values
    if (symbolEquityCurves) {
      symbols.forEach(symbol => {
        if (symbolEquityCurves[symbol] && symbolEquityCurves[symbol][idx]) {
          dataPoint[symbol] = symbolEquityCurves[symbol][idx].value;
        }
      });
    }

    return dataPoint;
  });

  // Color palette for different symbols
  const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#a28ee6', '#ff9999'];

  return (
    <div className="portfolio-equity-curve">
      <h3>Portfolio Equity Curve</h3>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="timestamp" 
            angle={-45}
            textAnchor="end"
            height={80}
            interval="preserveStartEnd"
          />
          <YAxis 
            label={{ value: 'Portfolio Value ($)', angle: -90, position: 'insideLeft' }}
            domain={['auto', 'auto']}
          />
          <Tooltip 
            formatter={(value: number) => `$${value.toFixed(2)}`}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          
          {/* Portfolio line (bold) */}
          <Line
            type="monotone"
            dataKey="portfolioValue"
            stroke="#2563eb"
            strokeWidth={3}
            dot={false}
            name="Portfolio"
          />
          
          {/* Individual symbol lines */}
          {symbols.map((symbol, idx) => (
            <Line
              key={symbol}
              type="monotone"
              dataKey={symbol}
              stroke={colors[idx % colors.length]}
              strokeWidth={2}
              dot={false}
              strokeDasharray="5 5"
              name={symbol}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

interface AllocationPieChartProps {
  weights: Record<string, number>;
}

export const AllocationPieChart: React.FC<AllocationPieChartProps> = ({ weights }) => {
  // Transform weights to pie chart data
  const data = Object.entries(weights).map(([symbol, weight]) => ({
    name: symbol,
    value: weight * 100, // Convert to percentage
  }));

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

  return (
    <div className="allocation-pie-chart">
      <h3>Portfolio Allocation</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

interface CorrelationHeatmapProps {
  correlationMatrix: Record<string, Record<string, number>>;
}

export const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({ correlationMatrix }) => {
  const symbols = Object.keys(correlationMatrix);
  
  if (symbols.length === 0) {
    return (
      <div className="correlation-heatmap">
        <h3>Correlation Matrix</h3>
        <p className="no-data">No correlation data available</p>
      </div>
    );
  }

  // Get color based on correlation value
  const getColor = (value: number): string => {
    // Red (-1) -> White (0) -> Green (1)
    if (value < 0) {
      const intensity = Math.abs(value);
      return `rgba(239, 68, 68, ${intensity})`;
    } else {
      const intensity = value;
      return `rgba(34, 197, 94, ${intensity})`;
    }
  };

  return (
    <div className="correlation-heatmap">
      <h3>Correlation Matrix</h3>
      <div className="heatmap-container">
        <table className="heatmap-table">
          <thead>
            <tr>
              <th></th>
              {symbols.map(sym => (
                <th key={sym}>{sym}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {symbols.map(row => (
              <tr key={row}>
                <th>{row}</th>
                {symbols.map(col => {
                  const value = correlationMatrix[row]?.[col] ?? 0;
                  return (
                    <td
                      key={`${row}-${col}`}
                      style={{ backgroundColor: getColor(value) }}
                      title={`${row} vs ${col}: ${value.toFixed(3)}`}
                    >
                      {value.toFixed(2)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="heatmap-legend">
          <div className="legend-item">
            <div className="legend-color" style={{ background: 'rgba(239, 68, 68, 0.8)' }}></div>
            <span>-1.0 (Negative)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ background: 'rgba(255, 255, 255, 1)' }}></div>
            <span>0.0 (No correlation)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ background: 'rgba(34, 197, 94, 0.8)' }}></div>
            <span>+1.0 (Positive)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

interface DiversificationMetricsProps {
  diversificationRatio: number;
  symbolCount: number;
  avgCorrelation: number;
}

export const DiversificationMetrics: React.FC<DiversificationMetricsProps> = ({
  diversificationRatio,
  symbolCount,
  avgCorrelation
}) => {
  return (
    <div className="diversification-metrics">
      <h3>Diversification Analysis</h3>
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Diversification Ratio</div>
          <div className="metric-value">{diversificationRatio.toFixed(2)}</div>
          <div className="metric-hint">
            {diversificationRatio > 1.2 ? '✓ Well diversified' : 
             diversificationRatio > 1.0 ? '⚠ Moderate diversification' : 
             '⚠ Low diversification'}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Number of Assets</div>
          <div className="metric-value">{symbolCount}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Avg Correlation</div>
          <div className="metric-value">{avgCorrelation.toFixed(2)}</div>
          <div className="metric-hint">
            {avgCorrelation < 0.3 ? '✓ Low correlation' : 
             avgCorrelation < 0.7 ? '⚠ Moderate correlation' : 
             '⚠ High correlation'}
          </div>
        </div>
      </div>
    </div>
  );
};
