import React, { useMemo, useState } from 'react';
import BacktestResults from './BacktestResults';

type RunBacktestResponse = {
  error?: string;
  signals?: any;
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

export default function BacktestEngine() {
  // Dev mode is now internal state (can be toggled)
  const [devMode, setDevMode] = useState(false);
  
  // DSL mode (production) or hardcoded spec mode (dev)
  const [dsl, setDsl] = useState('SMA(close, 50) CROSSES_ABOVE SMA(close, 200)');
  const [symbol, setSymbol] = useState('TEST');
  const [timeframe, setTimeframe] = useState('1D');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [mode, setMode] = useState<'signals' | 'simulate'>(devMode ? 'signals' : 'simulate');
  const [config, setConfig] = useState({
    initial_capital: 10000,
    position_size_mode: 'percent_capital',
    position_size_value: 100,
    stop_loss_percent: devMode ? 5 : 0,
    take_profit_percent: devMode ? 10 : 0,
    commission_per_trade: devMode ? 0.001 : 0
  });
  const [resp, setResp] = useState<RunBacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const supportedTimeframes = ['1D', '1H', '15M', '5M'];

  // Validation only needed in production DSL mode
  function validate(): string[] {
    if (devMode) return [];
    
    const errs: string[] = [];
    if (!dsl || dsl.trim().length === 0) errs.push('DSL must not be empty.');
    if (dsl.length > 5000) errs.push('DSL is too long (>5000 characters).');
    if (!symbol || symbol.trim().length === 0) errs.push('Symbol is required.');
    if (!supportedTimeframes.includes(timeframe)) errs.push(`Timeframe must be one of: ${supportedTimeframes.join(', ')}`);
    if (dateFrom && dateTo && dateFrom > dateTo) errs.push('From date must be on or before To date.');
    if (!(config.initial_capital > 0)) errs.push('Initial capital must be greater than 0.');
    if (config.position_size_mode !== 'percent_capital') errs.push('Only percent_capital sizing is supported currently.');
    if (!(config.position_size_value > 0 && config.position_size_value <= 100)) errs.push('Position size value (%) must be in (0, 100].');
    if (config.stop_loss_percent < 0 || config.stop_loss_percent > 100) errs.push('Stop loss (%) must be between 0 and 100.');
    if (config.take_profit_percent < 0 || config.take_profit_percent > 100) errs.push('Take profit (%) must be between 0 and 100.');
    if (config.commission_per_trade < 0 || config.commission_per_trade > 0.05) errs.push('Commission (rate) must be between 0 and 0.05.');
    return errs;
  }

  const isValid = useMemo(() => validate().length === 0, [dsl, symbol, timeframe, dateFrom, dateTo, config]);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResp(null);
    try {
      if (!devMode) {
        // Production mode: parse DSL
        const errs = validate();
        setValidationErrors(errs);
        if (errs.length > 0) throw new Error('Please fix validation errors before running.');
        const parsed = await (window as any).electronAPI.invoke('parse-dsl', { dsl, timeframe, universe: 'ALL' });
        if (!parsed?.success) throw new Error(parsed?.error || 'Failed to parse DSL');
        const payload: any = {
          scanner_spec: parsed.scannerSpec,
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
      } else {
        // Dev mode: use hardcoded spec
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
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to run backtest');
    } finally {
      setLoading(false);
    }
  };

  const title = devMode ? 'Backtest Dev' : 'Backtest Builder';
  const inputLayout = devMode ? 'flex' : 'grid';
  const marginBottom = devMode ? 12 : 8;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2>{title}</h2>
        <button 
          onClick={() => setDevMode(!devMode)}
          style={{
            padding: '8px 16px',
            backgroundColor: devMode ? '#28a745' : '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          {devMode ? '🔧 Dev Mode ON' : '📊 Production Mode'}
        </button>
      </div>
      
      {!devMode && (
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr', marginBottom: 12 }}>
          <label>
            DSL
            <textarea value={dsl} onChange={e => setDsl(e.target.value)} rows={3} style={{ width: '100%' }} />
          </label>
        </div>
      )}

      <div style={{ display: inputLayout, gap: 8, flexWrap: 'wrap', marginBottom: marginBottom }}>
        <label>
          {devMode ? 'Symbol:' : 'Symbol'}
          <input value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="TEST" />
        </label>
        <label>
          {devMode ? 'Timeframe:' : 'Timeframe'}
          <select value={timeframe} onChange={e => setTimeframe(e.target.value)}>
            <option value="1D">1D</option>
            <option value="1H">1H</option>
            <option value="15M">15M</option>
            <option value="5M">5M</option>
          </select>
        </label>
        <label>
          {devMode ? 'Mode:' : 'Mode'}
          <select value={mode} onChange={e => setMode(e.target.value as any)}>
            {devMode ? (
              <>
                <option value="signals">signals</option>
                <option value="simulate">simulate</option>
              </>
            ) : (
              <>
                <option value="simulate">simulate</option>
                <option value="signals">signals</option>
              </>
            )}
          </select>
        </label>
        <label>
          {devMode ? 'From:' : 'From'}
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
        </label>
        <label>
          {devMode ? 'To:' : 'To'}
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
        </label>
        <button onClick={run} disabled={loading}>Run</button>
      </div>

      {mode === 'simulate' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(180px, 1fr))', gap: 8, marginBottom: marginBottom }}>
          <label>
            Initial Capital
            <input type="number" value={config.initial_capital} onChange={e => setConfig({ ...config, initial_capital: Number(e.target.value) })} />
          </label>
          <label>
            Position Size Mode
            <select value={config.position_size_mode} onChange={e => setConfig({ ...config, position_size_mode: e.target.value })}>
              <option value="percent_capital">percent_capital</option>
            </select>
          </label>
          <label>
            Position Size Value (%)
            <input type="number" value={config.position_size_value} onChange={e => setConfig({ ...config, position_size_value: Number(e.target.value) })} />
          </label>
          <label>
            Stop Loss (%)
            <input type="number" value={config.stop_loss_percent} onChange={e => setConfig({ ...config, stop_loss_percent: Number(e.target.value) })} />
          </label>
          <label>
            Take Profit (%)
            <input type="number" value={config.take_profit_percent} onChange={e => setConfig({ ...config, take_profit_percent: Number(e.target.value) })} />
          </label>
          <label>
            Commission (rate)
            <input type="number" step={0.0001} value={config.commission_per_trade} onChange={e => setConfig({ ...config, commission_per_trade: Number(e.target.value) })} />
          </label>
        </div>
      )}

      {!devMode && validationErrors.length > 0 && (
        <div style={{ color: '#d9534f', background: '#2a0f0f', padding: 8, border: '1px solid #611', marginBottom: 12 }}>
          <strong>Fix the following:</strong>
          <ul style={{ margin: '6px 0 0 18px' }}>
            {validationErrors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      {loading && <div style={{ marginBottom: 12 }}>Running…</div>}
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}

      {resp && !resp.error && (
        <div style={{ marginTop: 12, marginBottom: 12 }}>
          {devMode ? (
            // Dev mode: detailed display
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
          ) : (
            // Production mode: use BacktestResults component
            <BacktestResults data={resp} />
          )}
        </div>
      )}

      <div style={{ marginTop: 8 }}>
        {!devMode ? (
          <>
            <button onClick={run} disabled={loading || !isValid}>Run Backtest</button>
            {!isValid && <span style={{ marginLeft: 8, color: '#d9534f' }}>(form has validation errors)</span>}
          </>
        ) : (
          <button onClick={run} disabled={loading}>Run Backtest</button>
        )}
      </div>
    </div>
  );
}
