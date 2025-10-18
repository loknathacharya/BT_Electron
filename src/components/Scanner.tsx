import React, { useMemo, useState } from 'react';

type AttrName = 'open' | 'high' | 'low' | 'close' | 'volume';

type IndicatorName =
  | 'SMA'
  | 'EMA'
  | 'RSI'
  | 'MACD'
  | 'ATR'
  | 'BB_MIDDLE'
  | 'BB_UPPER'
  | 'BB_LOWER'
  | 'ADX'
  | 'VWAP';

type OpType = 'compare' | 'crossover';

const ATTRS: AttrName[] = ['open', 'high', 'low', 'close', 'volume'];
const INDICATORS: IndicatorName[] = [
  'SMA', 'EMA', 'RSI', 'MACD', 'ATR', 'BB_MIDDLE', 'BB_UPPER', 'BB_LOWER', 'ADX', 'VWAP'
];

const initialFilter = () => ({
  id: Math.random().toString(36).slice(2),
  op: 'compare' as OpType,
  cmp: '>' as '>' | '>=' | '<' | '<=' | '==' | '!=',
  leftType: 'attr' as 'attr' | 'indicator' | 'const',
  left: { name: 'close' as AttrName },
  leftInd: { name: 'SMA' as IndicatorName, period: 20, src: 'close' as AttrName },
  rightType: 'const' as 'attr' | 'indicator' | 'const',
  right: { name: 'close' as AttrName },
  rightInd: { name: 'SMA' as IndicatorName, period: 50, src: 'close' as AttrName },
  constValue: 100,
  crossType: 'CROSSES_ABOVE' as 'CROSSES_ABOVE' | 'CROSSES_BELOW',
});

const toMeasureNode = (side: 'left' | 'right', f: any) => {
  const t = f[`${side}Type`];
  if (t === 'const') return { type: 'const', value: Number(f.constValue) };
  if (t === 'attr') return { type: 'attr', name: f[side].name };
  if (t === 'indicator') {
    const i = f[`${side}Ind`];
    const name = i.name as IndicatorName;
    if (name === 'SMA' || name === 'EMA' || name === 'RSI') {
      return { type: 'indicator', name, params: { src: { type: 'attr', name: i.src }, period: Number(i.period || 14) } };
    }
    if (name === 'MACD') {
      return { type: 'indicator', name, params: { src: { type: 'attr', name: i.src }, fast: Number(i.fast || 12), slow: Number(i.slow || 26), signal: Number(i.signal || 9), output: i.output || 'line' } };
    }
    if (name === 'ATR' || name === 'ADX') {
      return { type: 'indicator', name, params: { period: Number(i.period || 14) } };
    }
    if (name === 'VWAP') {
      return { type: 'indicator', name, params: {} };
    }
    if (name === 'BB_MIDDLE' || name === 'BB_UPPER' || name === 'BB_LOWER') {
      return { type: 'indicator', name, params: { src: { type: 'attr', name: i.src }, period: Number(i.period || 20), std: Number(i.std || 2) } };
    }
    return { type: 'const', value: NaN };
  }
  return { type: 'const', value: NaN };
};

const Scanner: React.FC = () => {
  const [timeframe, setTimeframe] = useState<'1D'>('1D');
  const [universeMode, setUniverseMode] = useState<'ALL' | 'LIST'>('ALL');
  const [universeList, setUniverseList] = useState<string>('');
  const [filters, setFilters] = useState<any[]>([initialFilter()]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showJson, setShowJson] = useState(false);

  const scannerSpec = useMemo(() => {
    const spec: any = {
      timeframe,
      universe: universeMode === 'ALL' ? 'ALL' : universeList.split(',').map(s => s.trim()).filter(Boolean),
      filters: filters.map(f => {
        if (f.op === 'compare') {
          return {
            op: 'compare',
            cmp: f.cmp,
            left: toMeasureNode('left', f),
            right: toMeasureNode('right', f)
          };
        } else {
          return {
            op: 'crossover',
            type: f.crossType,
            left: toMeasureNode('left', f),
            right: toMeasureNode('right', f)
          };
        }
      })
    };
    return spec;
  }, [timeframe, universeMode, universeList, filters]);

  const runScan = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await window.electronAPI.invoke('run-scan', {
        scannerSpec,
        options: { latestOnly: true, limit: 5000 },
      });
      setResult(response);
      if (response?.error) setError(response.error);
    } catch (e: any) {
      setError(e?.message || 'Failed to run scan');
    } finally {
      setLoading(false);
    }
  };

  const updateFilter = (id: string, patch: Partial<any>) => {
    setFilters(prev => prev.map(f => (f.id === id ? { ...f, ...patch } : f)));
  };

  const addFilter = () => setFilters(prev => [...prev, initialFilter()]);
  const removeFilter = (id: string) => setFilters(prev => prev.filter(f => f.id !== id));

  const results = (result?.results || []) as Array<{ symbol: string; timestamp: number }>;
  const stats = result?.stats;

  return (
    <div style={{ padding: 20 }}>
      <h2>Scanner</h2>
      <p>Build scans using attributes and indicators, then run against your local OHLCV database.</p>

      {/* Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, alignItems: 'start' }}>
        <div style={{ background: '#f9f9f9', border: '1px solid #e0e0e0', borderRadius: 8, padding: 12 }}>
          <h4 style={{ marginTop: 0 }}>Scan Settings</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label>Timeframe</label>
              <select value={timeframe} onChange={(e) => setTimeframe(e.target.value as '1D')} style={{ width: '100%' }}>
                <option value="1D">Daily</option>
              </select>
            </div>
            <div>
              <label>Universe</label>
              <select value={universeMode} onChange={(e) => setUniverseMode(e.target.value as 'ALL' | 'LIST')} style={{ width: '100%' }}>
                <option value="ALL">All symbols</option>
                <option value="LIST">Symbol list</option>
              </select>
            </div>
            {universeMode === 'LIST' && (
              <div style={{ gridColumn: '1 / span 2' }}>
                <label>Symbols (comma separated)</label>
                <input
                  type="text"
                  placeholder="AAPL, MSFT, TSLA"
                  value={universeList}
                  onChange={(e) => setUniverseList(e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <button className="btn" onClick={runScan} disabled={loading}>
              {loading ? 'Running…' : 'Run Scan'}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowJson(s => !s)} style={{ marginLeft: 8 }}>
              {showJson ? 'Hide JSON' : 'Show JSON'}
            </button>
          </div>

          {showJson && (
            <div style={{ marginTop: 12 }}>
              <h4>Spec (JSON)</h4>
              <pre style={{ background: '#f7f7f7', padding: 12, borderRadius: 4, maxHeight: 240, overflow: 'auto' }}>
                {JSON.stringify(scannerSpec, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Filter Builder */}
        <div style={{ background: '#f9f9f9', border: '1px solid #e0e0e0', borderRadius: 8, padding: 12 }}>
          <h4 style={{ marginTop: 0 }}>Filters</h4>
          <p style={{ color: '#666', marginTop: 0 }}>All filters are ANDed together in this phase.</p>
          {filters.map((f) => (
            <div key={f.id} style={{ padding: 10, border: '1px solid #ddd', borderRadius: 6, marginBottom: 10, background: '#fff' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8, alignItems: 'end' }}>
                {/* Operation */}
                <div>
                  <label>Operation</label>
                  <select
                    value={f.op}
                    onChange={(e) => updateFilter(f.id, { op: e.target.value as OpType })}
                    style={{ width: '100%' }}
                  >
                    <option value="compare">Compare</option>
                    <option value="crossover">Crossover</option>
                  </select>
                </div>

                {/* Compare operator */}
                {f.op === 'compare' && (
                  <div>
                    <label>Compare</label>
                    <select
                      value={f.cmp}
                      onChange={(e) => updateFilter(f.id, { cmp: e.target.value })}
                      style={{ width: '100%' }}
                    >
                      <option value=">">{'>'}</option>
                      <option value=">=">≥</option>
                      <option value="<">{'<'}</option>
                      <option value="<=">≤</option>
                      <option value="==">==</option>
                      <option value="!=">!=</option>
                    </select>
                  </div>
                )}

                {/* Cross type */}
                {f.op === 'crossover' && (
                  <div>
                    <label>Cross Type</label>
                    <select
                      value={f.crossType}
                      onChange={(e) => updateFilter(f.id, { crossType: e.target.value })}
                      style={{ width: '100%' }}
                    >
                      <option value="CROSSES_ABOVE">Crosses Above</option>
                      <option value="CROSSES_BELOW">Crosses Below</option>
                    </select>
                  </div>
                )}

                {/* Left side */}
                <div>
                  <label>Left</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 6 }}>
                    <select
                      value={f.leftType}
                      onChange={(e) => updateFilter(f.id, { leftType: e.target.value })}
                    >
                      <option value="attr">Attribute</option>
                      <option value="indicator">Indicator</option>
                      <option value="const">Constant</option>
                    </select>
                    {f.leftType === 'attr' && (
                      <select
                        value={f.left.name}
                        onChange={(e) => updateFilter(f.id, { left: { name: e.target.value } })}
                      >
                        {ATTRS.map(a => <option key={a} value={a}>{a}</option>)}
                      </select>
                    )}
                    {f.leftType === 'indicator' && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                        <select
                          value={f.leftInd.name}
                          onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, name: e.target.value } })}
                        >
                          {INDICATORS.map(i => <option key={i} value={i}>{i}</option>)}
                        </select>
                        {/* Generic params */}
                        {['SMA','EMA','RSI','BB_MIDDLE','BB_UPPER','BB_LOWER'].includes(f.leftInd.name) && (
                          <>
                            <input type="number" placeholder="period" value={f.leftInd.period}
                              onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, period: Number(e.target.value) } })} />
                            <select value={f.leftInd.src} onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, src: e.target.value } })}>
                              {ATTRS.map(a => <option key={a} value={a}>{a}</option>)}
                            </select>
                          </>
                        )}
                        {f.leftInd.name === 'MACD' && (
                          <>
                            <input type="number" placeholder="fast" value={f.leftInd.fast || 12} onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, fast: Number(e.target.value) } })} />
                            <input type="number" placeholder="slow" value={f.leftInd.slow || 26} onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, slow: Number(e.target.value) } })} />
                            <input type="number" placeholder="signal" value={f.leftInd.signal || 9} onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, signal: Number(e.target.value) } })} />
                          </>
                        )}
                        {['ATR','ADX'].includes(f.leftInd.name) && (
                          <>
                            <input type="number" placeholder="period" value={f.leftInd.period || 14}
                              onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, period: Number(e.target.value) } })} />
                            <div />
                          </>
                        )}
                        {['BB_MIDDLE','BB_UPPER','BB_LOWER'].includes(f.leftInd.name) && (
                          <>
                            <input type="number" placeholder="std" value={f.leftInd.std || 2}
                              onChange={(e) => updateFilter(f.id, { leftInd: { ...f.leftInd, std: Number(e.target.value) } })} />
                          </>
                        )}
                      </div>
                    )}
                    {f.leftType === 'const' && (
                      <input type="number" value={f.constValue} onChange={(e) => updateFilter(f.id, { constValue: Number(e.target.value) })} />
                    )}
                  </div>
                </div>

                {/* Right side */}
                <div>
                  <label>Right</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 6 }}>
                    <select
                      value={f.rightType}
                      onChange={(e) => updateFilter(f.id, { rightType: e.target.value })}
                    >
                      <option value="attr">Attribute</option>
                      <option value="indicator">Indicator</option>
                      <option value="const">Constant</option>
                    </select>
                    {f.rightType === 'attr' && (
                      <select
                        value={f.right.name}
                        onChange={(e) => updateFilter(f.id, { right: { name: e.target.value } })}
                      >
                        {ATTRS.map(a => <option key={a} value={a}>{a}</option>)}
                      </select>
                    )}
                    {f.rightType === 'indicator' && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                        <select
                          value={f.rightInd.name}
                          onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, name: e.target.value } })}
                        >
                          {INDICATORS.map(i => <option key={i} value={i}>{i}</option>)}
                        </select>
                        {/* Generic params */}
                        {['SMA','EMA','RSI','BB_MIDDLE','BB_UPPER','BB_LOWER'].includes(f.rightInd.name) && (
                          <>
                            <input type="number" placeholder="period" value={f.rightInd.period}
                              onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, period: Number(e.target.value) } })} />
                            <select value={f.rightInd.src} onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, src: e.target.value } })}>
                              {ATTRS.map(a => <option key={a} value={a}>{a}</option>)}
                            </select>
                          </>
                        )}
                        {f.rightInd.name === 'MACD' && (
                          <>
                            <input type="number" placeholder="fast" value={f.rightInd.fast || 12} onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, fast: Number(e.target.value) } })} />
                            <input type="number" placeholder="slow" value={f.rightInd.slow || 26} onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, slow: Number(e.target.value) } })} />
                            <input type="number" placeholder="signal" value={f.rightInd.signal || 9} onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, signal: Number(e.target.value) } })} />
                          </>
                        )}
                        {['ATR','ADX'].includes(f.rightInd.name) && (
                          <>
                            <input type="number" placeholder="period" value={f.rightInd.period || 14}
                              onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, period: Number(e.target.value) } })} />
                            <div />
                          </>
                        )}
                        {['BB_MIDDLE','BB_UPPER','BB_LOWER'].includes(f.rightInd.name) && (
                          <>
                            <input type="number" placeholder="std" value={f.rightInd.std || 2}
                              onChange={(e) => updateFilter(f.id, { rightInd: { ...f.rightInd, std: Number(e.target.value) } })} />
                          </>
                        )}
                      </div>
                    )}
                    {f.rightType === 'const' && (
                      <input type="number" value={f.constValue} onChange={(e) => updateFilter(f.id, { constValue: Number(e.target.value) })} />
                    )}
                  </div>
                </div>

                {/* Remove */}
                <div style={{ alignSelf: 'center' }}>
                  <button className="btn btn-secondary" onClick={() => removeFilter(f.id)}>Remove</button>
                </div>
              </div>
            </div>
          ))}
          <button className="btn btn-secondary" onClick={addFilter}>+ Add Filter</button>
        </div>
      </div>

      {/* Results Panel */}
      <div style={{ marginTop: 16, background: '#f5f5f5', border: '1px solid #e0e0e0', borderRadius: 8, padding: 12 }}>
        <h4 style={{ marginTop: 0 }}>Results</h4>
        {error && (
          <div style={{ padding: 10, background: '#ffebee', color: '#c62828', borderRadius: 4, marginBottom: 10 }}>
            {error}
          </div>
        )}
        {stats && (
          <div style={{ marginBottom: 10, color: '#666' }}>
            Scanned symbols: <strong>{stats.scannedSymbols}</strong> • Time: <strong>{stats.timeMs} ms</strong>
          </div>
        )}
        {results.length === 0 ? (
          <div style={{ color: '#777' }}>No matches yet. Configure a scan and click Run Scan.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#eee' }}>
                  <th style={{ textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #ddd' }}>Symbol</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #ddd' }}>Last Bar</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #ddd' }}>Quick Actions</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, idx) => (
                  <tr key={`${r.symbol}-${idx}`} style={{ background: idx % 2 ? '#fff' : '#fafafa' }}>
                    <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>{r.symbol}</td>
                    <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>{new Date(r.timestamp * 1000).toLocaleString()}</td>
                    <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>
                      <button
                        className="btn btn-secondary"
                        onClick={() => window.alert(`Open quick preview for ${r.symbol} (Data Management → select symbol and view chart).`)}
                      >
                        Quick Preview
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Scanner;
