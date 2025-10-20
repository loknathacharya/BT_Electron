import React, { useState } from 'react';

type RunBacktestResponse = {
  signals?: {
    symbol: string;
    timeframe: string;
    priceField: string;
    entries: { timestamp: number; price: number }[];
    count: number;
    seriesLength: number;
  };
  error?: string;
  stats?: any;
  trades?: any[];
  metrics?: Record<string, number>;
  equity_curve?: { timestamps: number[]; equity: number[] };
};

const sampleSpec = {
  timeframe: '1D',
  universe: 'ALL',
  filters: [
    {
      op: 'crossover',
      type: 'CROSSES_ABOVE',
      left: { type: 'indicator', name: 'SMA', params: { period: 50, src: { type: 'attr', name: 'close' } } },
      right: { type: 'indicator', name: 'SMA', params: { period: 200, src: { type: 'attr', name: 'close' } } }
    }
  ]
};

export default function BacktestDev() {
  const [symbol, setSymbol] = useState('TEST');
  const [timeframe, setTimeframe] = useState('1D');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [mode, setMode] = useState<'signals' | 'simulate'>('signals');
  const [config, setConfig] = useState({
    initial_capital: 10000,
    position_size_mode: 'percent_capital',
    position_size_value: 100,
    stop_loss_percent: 5,
    take_profit_percent: 10,
    commission_per_trade: 0.001
  });
  const [resp, setResp] = useState<RunBacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResp(null);
    try {
      const payload: any = {
        scanner_spec: sampleSpec,
        symbol,
        timeframe,
        mode,
      };
      if (dateFrom) payload.start_date = dateFrom;
      if (dateTo) payload.end_date = dateTo;
      if (mode === 'simulate') payload.backtest_config = config;
      const result = await (window as any).electronAPI.invoke('run-backtest', payload);
      setResp(result);
      if (result?.error) setError(result.error);
    } catch (e: any) {
      setError(e?.message || 'Failed to run backtest');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h2>Backtest Dev</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <label>
          Symbol:
          <input value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="TEST" />
        </label>
        <label>
          Timeframe:
          <select value={timeframe} onChange={e => setTimeframe(e.target.value)}>
            <option value="1D">1D</option>
            <option value="1H">1H</option>
            <option value="15M">15M</option>
            <option value="5M">5M</option>
          </select>
        </label>
        <label>
          Mode:
          <select value={mode} onChange={e => setMode(e.target.value as any)}>
            <option value="signals">signals</option>
            <option value="simulate">simulate</option>
          </select>
        </label>
        <label>
          From:
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
        </label>
        <label>
          To:
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
        </label>
        <button onClick={run} disabled={loading}>Run</button>
      </div>
      {mode === 'simulate' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(180px, 1fr))', gap: 8, marginBottom: 12 }}>
          <label>
            Initial Capital
            <input type="number" value={config.initial_capital}
              onChange={e => setConfig({ ...config, initial_capital: Number(e.target.value) })} />
          </label>
          <label>
            Position Size Mode
            <select value={config.position_size_mode}
              onChange={e => setConfig({ ...config, position_size_mode: e.target.value })}>
              <option value="percent_capital">percent_capital</option>
            </select>
          </label>
          <label>
            Position Size Value (%)
            <input type="number" value={config.position_size_value}
              onChange={e => setConfig({ ...config, position_size_value: Number(e.target.value) })} />
          </label>
          <label>
            Stop Loss (%)
            <input type="number" value={config.stop_loss_percent}
              onChange={e => setConfig({ ...config, stop_loss_percent: Number(e.target.value) })} />
          </label>
          <label>
            Take Profit (%)
            <input type="number" value={config.take_profit_percent}
              onChange={e => setConfig({ ...config, take_profit_percent: Number(e.target.value) })} />
          </label>
          <label>
            Commission (rate)
            <input type="number" step="0.0001" value={config.commission_per_trade}
              onChange={e => setConfig({ ...config, commission_per_trade: Number(e.target.value) })} />
          </label>
        </div>
      )}
      {loading && <div>Running…</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {resp && !resp.error && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
          {resp.signals && (
            <div>
              <h3>Signals</h3>
              <div>Count: {resp.signals.count}</div>
            </div>
          )}
          {resp.metrics && (
            <div>
              <h3>Metrics</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(160px, 1fr))', gap: 8 }}>
                {Object.entries(resp.metrics).slice(0, 12).map(([k, v]) => (
                  <div key={k}><strong>{k}:</strong> {String(v)}</div>
                ))}
              </div>
            </div>
          )}
          {Array.isArray(resp.trades) && resp.trades.length > 0 && (
            <div>
              <h3>Trades ({resp.trades.length})</h3>
              <div style={{ maxHeight: 240, overflow: 'auto', border: '1px solid #333' }}>
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
                    {resp.trades.map((t: any) => (
                      <tr key={t.trade_id}>
                        <td>{new Date(t.entry_timestamp * 1000).toLocaleDateString()}</td>
                        <td>{new Date(t.exit_timestamp * 1000).toLocaleDateString()}</td>
                        <td style={{ textAlign: 'right' }}>{t.quantity}</td>
                        <td style={{ textAlign: 'right' }}>{t.entry_price}</td>
                        <td style={{ textAlign: 'right' }}>{t.exit_price}</td>
                        <td style={{ textAlign: 'right' }}>{t.pnl}</td>
                        <td style={{ textAlign: 'right' }}>{t.pnl_percent}</td>
                        <td>{t.exit_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {resp.equity_curve && Array.isArray(resp.equity_curve.equity) && resp.equity_curve.equity.length > 0 && (
            <div>
              <h3>Equity Curve (preview)</h3>
              <div style={{ maxHeight: 180, overflow: 'auto', background: '#111', color: '#ddd', padding: 8 }}>
                <pre style={{ margin: 0 }}>{JSON.stringify(resp.equity_curve.equity.slice(0, 20))} ...</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
