import React from 'react';

type RunBacktestResponse = {
  signals?: {
    symbol: string;
    timeframe: string;
    priceField: string;
    entries: { timestamp: number; price: number }[];
    count: number;
    seriesLength: number;
  };
  trades?: any[];
  metrics?: Record<string, number>;
  equity_curve?: { timestamps: number[]; equity: number[] };
};

function formatNumber(n: any, digits = 2) {
  const x = Number(n);
  if (!isFinite(x)) return String(n);
  return x.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function EquityChart({ equity, timestamps }: { equity: number[]; timestamps?: number[] }) {
  if (!equity || equity.length < 2) return null;
  const width = 420;
  const height = 140;
  const margin = { top: 8, right: 12, bottom: 18, left: 48 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const min = Math.min(...equity);
  const max = Math.max(...equity);
  const xStep = innerW / (equity.length - 1);
  const y = (v: number) => {
    if (max === min) return innerH / 2;
    return innerH - ((v - min) / (max - min)) * innerH;
  };
  const path = equity.map((v, i) => `${i === 0 ? 'M' : 'L'} ${i * xStep} ${y(v)}`).join(' ');

  // Axis ticks (5 y ticks, 6 x ticks)
  const yTicks = 5;
  const yVals = Array.from({ length: yTicks + 1 }, (_, i) => min + (i * (max - min)) / yTicks);
  const xTicks = Math.min(6, Math.max(2, Math.floor(equity.length / 20)));
  const xIdx = Array.from({ length: xTicks }, (_, i) => Math.round((i * (equity.length - 1)) / (xTicks - 1)));

  // Tooltip state via React (simple local state)
  const [hover, setHover] = React.useState<{ i: number; x: number; y: number } | null>(null);

  function onMove(e: React.MouseEvent<SVGRectElement>) {
    const rect = (e.target as SVGRectElement).getBoundingClientRect();
    const x = e.clientX - rect.left;
    const i = Math.max(0, Math.min(equity.length - 1, Math.round(x / xStep)));
    setHover({ i, x: i * xStep, y: y(equity[i]) });
  }

  function onLeave() {
    setHover(null);
  }

  const fmtVal = (v: number) => formatNumber(v, 2);
  const fmtTs = (t?: number) => (t ? new Date(t * 1000).toLocaleDateString() : '');

  return (
    <svg width={width} height={height} style={{ display: 'block', background: '#0a0a0a', border: '1px solid #333' }}>
      <g transform={`translate(${margin.left},${margin.top})`}>
        {/* Axes */}
        <line x1={0} y1={innerH} x2={innerW} y2={innerH} stroke="#555" strokeWidth={1} />
        <line x1={0} y1={0} x2={0} y2={innerH} stroke="#555" strokeWidth={1} />
        {/* Y ticks */}
        {yVals.map((v, i) => (
          <g key={i}>
            <line x1={-4} y1={y(v)} x2={0} y2={y(v)} stroke="#777" />
            <text x={-8} y={y(v)} fill="#aaa" fontSize={10} textAnchor="end" dominantBaseline="central">{fmtVal(v)}</text>
          </g>
        ))}
        {/* X ticks */}
        {xIdx.map((ix, i) => (
          <g key={i}>
            <line x1={ix * xStep} y1={innerH} x2={ix * xStep} y2={innerH + 4} stroke="#777" />
            <text x={ix * xStep} y={innerH + 12} fill="#aaa" fontSize={10} textAnchor="middle">
              {fmtTs(timestamps?.[ix])}
            </text>
          </g>
        ))}
        {/* Path */}
        <path d={path} fill="none" stroke="#4caf50" strokeWidth={1.5} />

        {/* Hover layer */}
        <rect x={0} y={0} width={innerW} height={innerH} fill="transparent" onMouseMove={onMove} onMouseLeave={onLeave} />
        {hover && (
          <g>
            <line x1={hover.x} y1={0} x2={hover.x} y2={innerH} stroke="#888" strokeDasharray="3 3" />
            <circle cx={hover.x} cy={hover.y} r={3} fill="#4caf50" />
            {/* Tooltip box */}
            <g transform={`translate(${Math.min(hover.x + 8, innerW - 120)},${Math.max(hover.y - 34, 0)})`}>
              <rect width={120} height={30} rx={3} ry={3} fill="#111" stroke="#444" />
              <text x={6} y={12} fill="#ddd" fontSize={10}>Eq: {fmtVal(equity[hover.i])}</text>
              <text x={6} y={24} fill="#aaa" fontSize={10}>{fmtTs(timestamps?.[hover.i])}</text>
            </g>
          </g>
        )}
      </g>
    </svg>
  );
}

export default function BacktestResults({ data }: { data: RunBacktestResponse }) {
  const metrics = data.metrics || {};
  const trades = data.trades || [];
  const equity = data.equity_curve?.equity || [];

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {data.signals && (
        <div>
          <h3>Signals</h3>
          <div>Symbol: {data.signals.symbol} &nbsp; Timeframe: {data.signals.timeframe}</div>
          <div>Entries: {data.signals.count}</div>
        </div>
      )}
      {Object.keys(metrics).length > 0 && (
        <div>
          <h3>Metrics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(160px, 1fr))', gap: 8 }}>
            {Object.entries(metrics).map(([k, v]) => (
              <div key={k}><strong>{k}:</strong> {formatNumber(v)}</div>
            ))}
          </div>
        </div>
      )}
      {equity.length > 0 && (
        <div>
          <h3>Equity Curve</h3>
          <EquityChart equity={equity.slice(0, 400)} timestamps={data.equity_curve?.timestamps?.slice(0, 400)} />
        </div>
      )}
      {trades.length > 0 && (
        <div>
          <h3>Trades ({trades.length})</h3>
          <div style={{ maxHeight: 260, overflow: 'auto', border: '1px solid #333' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Entry</th>
                  <th style={{ textAlign: 'left' }}>Exit</th>
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>PNL</th>
                  <th>PNL%</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t: any) => (
                  <tr key={t.trade_id}>
                    <td>{new Date((t.entry_timestamp || 0) * 1000).toLocaleDateString()}</td>
                    <td>{new Date((t.exit_timestamp || 0) * 1000).toLocaleDateString()}</td>
                    <td style={{ textAlign: 'right' }}>{formatNumber(t.quantity, 0)}</td>
                    <td style={{ textAlign: 'right' }}>{formatNumber(t.entry_price, 4)}</td>
                    <td style={{ textAlign: 'right' }}>{formatNumber(t.exit_price, 4)}</td>
                    <td style={{ textAlign: 'right' }}>{formatNumber(t.pnl, 2)}</td>
                    <td style={{ textAlign: 'right' }}>{formatNumber(t.pnl_percent, 2)}</td>
                    <td>{t.exit_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
