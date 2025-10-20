import React, { useMemo, useState } from 'react';
import BacktestResults from './BacktestResults';

type RunBacktestResponse = {
  error?: string;
  signals?: any;
  trades?: any[];
  metrics?: Record<string, number>;
  equity_curve?: { timestamps: number[]; equity: number[] };
};

export default function BacktestBuilder() {
  const [dsl, setDsl] = useState('SMA(close, 50) CROSSES_ABOVE SMA(close, 200)');
  const [symbol, setSymbol] = useState('TEST');
  const [timeframe, setTimeframe] = useState('1D');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [mode, setMode] = useState<'signals' | 'simulate'>('simulate');
  const [config, setConfig] = useState({
    initial_capital: 10000,
    position_size_mode: 'percent_capital',
    position_size_value: 100,
    stop_loss_percent: 0,
    take_profit_percent: 0,
    commission_per_trade: 0
  });
  const [resp, setResp] = useState<RunBacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const supportedTimeframes = ['1D', '1H', '15M', '5M'];

  function validate(): string[] {
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
    } catch (e: any) {
      setError(e?.message || 'Failed to run backtest');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h2>Backtest Builder</h2>
      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr' }}>
        <label>
          DSL
          <textarea value={dsl} onChange={e => setDsl(e.target.value)} rows={3} style={{ width: '100%' }} />
        </label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <label>Symbol <input value={symbol} onChange={e => setSymbol(e.target.value)} /></label>
          <label>Timeframe
            <select value={timeframe} onChange={e => setTimeframe(e.target.value)}>
              <option value="1D">1D</option>
              <option value="1H">1H</option>
              <option value="15M">15M</option>
              <option value="5M">5M</option>
            </select>
          </label>
          <label>Mode
            <select value={mode} onChange={e => setMode(e.target.value as any)}>
              <option value="simulate">simulate</option>
              <option value="signals">signals</option>
            </select>
          </label>
          <label>From <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} /></label>
          <label>To <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} /></label>
          <button onClick={run} disabled={loading}>Run</button>
        </div>
      </div>

      {mode === 'simulate' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(180px, 1fr))', gap: 8, marginTop: 12 }}>
          <label>Initial Capital
            <input type="number" value={config.initial_capital} onChange={e => setConfig({ ...config, initial_capital: Number(e.target.value) })} />
          </label>
          <label>Position Size Mode
            <select value={config.position_size_mode} onChange={e => setConfig({ ...config, position_size_mode: e.target.value })}>
              <option value="percent_capital">percent_capital</option>
            </select>
          </label>
          <label>Position Size Value (%)
            <input type="number" value={config.position_size_value} onChange={e => setConfig({ ...config, position_size_value: Number(e.target.value) })} />
          </label>
          <label>Stop Loss (%)
            <input type="number" value={config.stop_loss_percent} onChange={e => setConfig({ ...config, stop_loss_percent: Number(e.target.value) })} />
          </label>
          <label>Take Profit (%)
            <input type="number" value={config.take_profit_percent} onChange={e => setConfig({ ...config, take_profit_percent: Number(e.target.value) })} />
          </label>
          <label>Commission (rate)
            <input type="number" step={0.0001} value={config.commission_per_trade} onChange={e => setConfig({ ...config, commission_per_trade: Number(e.target.value) })} />
          </label>
        </div>
      )}

      {validationErrors.length > 0 && (
        <div style={{ color: '#d9534f', background: '#2a0f0f', padding: 8, border: '1px solid #611' }}>
          <strong>Fix the following:</strong>
          <ul style={{ margin: '6px 0 0 18px' }}>
            {validationErrors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
      {loading && <div>Running…</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {resp && !resp.error && (
        <div style={{ marginTop: 12 }}>
          <BacktestResults data={resp} />
        </div>
      )}
      <div style={{ marginTop: 8 }}>
        <button onClick={run} disabled={loading || !isValid}>Run Backtest</button>
        {!isValid && <span style={{ marginLeft: 8, color: '#d9534f' }}>(form has validation errors)</span>}
      </div>
    </div>
  );
}
