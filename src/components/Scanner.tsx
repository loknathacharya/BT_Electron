import React, { useEffect, useMemo, useState } from 'react';
import CandlestickChart from './CandlestickChart';
import { useNavigate } from 'react-router-dom';
import ScannerBuilder from './ScannerBuilder';
import { BuilderTree, treeToFilters } from './scannerBuilderModel';

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
  leftOffsetType: 'none' as 'none' | 'lookback' | 'ordinal',
  leftOffsetBars: 0,
  leftOffsetOrdinal: 0,
  rightType: 'const' as 'attr' | 'indicator' | 'const',
  right: { name: 'close' as AttrName },
  rightInd: { name: 'SMA' as IndicatorName, period: 50, src: 'close' as AttrName },
  rightOffsetType: 'none' as 'none' | 'lookback' | 'ordinal',
  rightOffsetBars: 0,
  rightOffsetOrdinal: 0,
  constValue: 100,
  crossType: 'CROSSES_ABOVE' as 'CROSSES_ABOVE' | 'CROSSES_BELOW',
});

const toMeasureNode = (side: 'left' | 'right', f: any) => {
  const t = f[`${side}Type`];
  const offsetType = f[`${side}OffsetType`];
  
  // Build offset object if needed
  let offset: any = undefined;
  if (offsetType === 'lookback') {
    const bars = Number(f[`${side}OffsetBars`] || 0);
    if (bars > 0) offset = { kind: 'lookback', bars };
  } else if (offsetType === 'ordinal') {
    const n = Number(f[`${side}OffsetOrdinal`] || 0);
    offset = { kind: 'ordinal', n };
  }
  
  if (t === 'const') return { type: 'const', value: Number(f.constValue) };
  if (t === 'attr') {
    const node: any = { type: 'attr', name: f[side].name };
    if (offset) node.offset = offset;
    return node;
  }
  if (t === 'indicator') {
    const i = f[`${side}Ind`];
    const name = i.name as IndicatorName;
    let node: any;
    if (name === 'SMA' || name === 'EMA' || name === 'RSI') {
      node = { type: 'indicator', name, params: { src: { type: 'attr', name: i.src }, period: Number(i.period || 14) } };
    } else if (name === 'MACD') {
      node = { type: 'indicator', name, params: { src: { type: 'attr', name: i.src }, fast: Number(i.fast || 12), slow: Number(i.slow || 26), signal: Number(i.signal || 9), output: i.output || 'line' } };
    } else if (name === 'ATR' || name === 'ADX') {
      node = { type: 'indicator', name, params: { period: Number(i.period || 14) } };
    } else if (name === 'VWAP') {
      node = { type: 'indicator', name, params: {} };
    } else if (name === 'BB_MIDDLE' || name === 'BB_UPPER' || name === 'BB_LOWER') {
      node = { type: 'indicator', name, params: { src: { type: 'attr', name: i.src }, period: Number(i.period || 20), std: Number(i.std || 2) } };
    } else {
      return { type: 'const', value: NaN };
    }
    if (offset) node.offset = offset;
    return node;
  }
  return { type: 'const', value: NaN };
};

const Scanner: React.FC = () => {
  const [timeframe, setTimeframe] = useState<'1D' | '1h' | '15m' | '5m'>('1D');
  const [universeMode, setUniverseMode] = useState<'ALL' | 'LIST'>('ALL');
  const [universeList, setUniverseList] = useState<string>('');
  const [filters, setFilters] = useState<any[]>([initialFilter()]);
  const [useBuilder, setUseBuilder] = useState<boolean>(true);
  const [builderTree, setBuilderTree] = useState<BuilderTree | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [maxSymbols, setMaxSymbols] = useState<number>(0);
  const [scanProgress, setScanProgress] = useState<{phase: 'start'|'running'|'done'; scanned?: number; totalSymbols?: number} | null>(null);
  
  // Phase 4: Sorting and pagination state
  const [sortBy, setSortBy] = useState<'symbol' | 'timestamp'>('symbol');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [pageSize, setPageSize] = useState(50);
  const [currentPage, setCurrentPage] = useState(0);
  const [includeExplain, setIncludeExplain] = useState(false);
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');

  const scannerSpec = useMemo(() => {
    const spec: any = {
      timeframe,
      universe: universeMode === 'ALL' ? 'ALL' : universeList.split(',').map(s => s.trim()).filter(Boolean),
      filters: useBuilder && builderTree ? treeToFilters(builderTree) : filters.map(f => {
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
  }, [timeframe, universeMode, universeList, filters, useBuilder, builderTree]);

  const runScan = async () => {
    try {
      setLoading(true);
      setError(null);
      setCurrentPage(0); // Reset to first page on new scan
      const response = await window.electronAPI.invoke('run-scan', {
        scannerSpec,
        options: {
          latestOnly: true,
          sort: { by: sortBy, order: sortOrder },
          offset: 0,
          limit: 5000, // Get all, we'll paginate in UI
          maxSymbols: maxSymbols > 0 ? maxSymbols : undefined,
          includeExplain: includeExplain || undefined,
          dateFrom: dateFrom || undefined,
          dateTo: dateTo || undefined,
        },
      });
      setResult(response);
      if (response?.error) setError(response.error);
      // Clear progress when done
      setScanProgress(null);
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

  const allResults = (result?.results || []) as Array<{ symbol: string; timestamp: number; explain?: Record<string, any> }>;
  const stats = result?.stats;
  
  // Client-side pagination
  const totalResults = allResults.length;
  const totalPages = Math.ceil(totalResults / pageSize);
  const startIdx = currentPage * pageSize;
  const endIdx = Math.min(startIdx + pageSize, totalResults);
  const results = allResults.slice(startIdx, endIdx);

  const navigate = useNavigate();

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSymbol, setPreviewSymbol] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Subscribe to scan-progress events from backend to drive spinner/progress line
  useEffect(() => {
    const off = window.electronAPI.on('scan-progress', (_event: any, payload: any) => {
      if (payload?.type !== 'scan-progress') return;
      const phase = payload.phase as 'start'|'running'|'done';
      if (!phase) return;
      setScanProgress({ phase, scanned: payload.scanned, totalSymbols: payload.totalSymbols });
      if (phase === 'done') {
        // Slight delay to allow response to arrive and clear
        setTimeout(() => setScanProgress(null), 1000);
      }
    });
    return () => { try { off && off(); } catch { /* ignore */ } };
  }, []);

  const openPreview = async (symbol: string) => {
    setPreviewSymbol(symbol);
    setPreviewOpen(true);
    setPreviewLoading(true);
    try {
      const res = await window.electronAPI.invoke('get-price-data', { symbol, limit: 200, offset: 0 });
      if (res.error) throw new Error(res.error);
      const data = (res.data || []).slice(-50).map((d: any) => ({
        name: d.date || new Date(d.timestamp * 1000).toLocaleDateString(),
        open: Number(d.open),
        high: Number(d.high),
        low: Number(d.low),
        close: Number(d.close),
        volume: d.volume
      }));
      setPreviewData(data);
    } catch (err: any) {
      console.error('Preview fetch error', err);
      setPreviewData([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const viewInDataManagement = (symbol: string) => {
    // Navigate to data management and pass symbol as query param
    navigate(`/data-management?symbol=${encodeURIComponent(symbol)}`);
  };

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
              <select value={timeframe} onChange={(e) => setTimeframe(e.target.value as any)} style={{ width: '100%' }}>
                <option value="1D">Daily (1D)</option>
                <option value="1h">1 Hour</option>
                <option value="15m">15 Minutes</option>
                <option value="5m">5 Minutes</option>
              </select>
            </div>
            <div>
              <label>Universe</label>
              <select value={universeMode} onChange={(e) => setUniverseMode(e.target.value as 'ALL' | 'LIST')} style={{ width: '100%' }}>
                <option value="ALL">All symbols</option>
                <option value="LIST">Symbol list</option>
              </select>
            </div>
            <div>
              <label>Max symbols (dev)</label>
              <input type="number" min={0} value={maxSymbols}
                     onChange={(e) => setMaxSymbols(Number(e.target.value) || 0)}
                     style={{ width: '100%' }} placeholder="0 = no cap" />
            </div>
            <div>
              <label>Date From</label>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} style={{ width: '100%' }} />
            </div>
            <div>
              <label>Date To</label>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} style={{ width: '100%' }} />
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
            <label style={{ marginLeft: 12, display: 'inline-flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={useBuilder} onChange={(e) => setUseBuilder(e.target.checked)} />
              Use Chartink-like Builder
            </label>
            <button className="btn btn-secondary" onClick={() => setShowJson(s => !s)} style={{ marginLeft: 8 }}>
              {showJson ? 'Hide JSON' : 'Show JSON'}
            </button>
            <label style={{ marginLeft: 12, display: 'inline-flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={includeExplain} onChange={(e) => setIncludeExplain(e.target.checked)} />
              Include explain & timings
            </label>
            {scanProgress && (
              <span style={{ marginLeft: 12, color: '#555', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <span className="spinner" style={{ width: 14, height: 14, border: '2px solid #ccc', borderTopColor: '#333', borderRadius: '50%', display: 'inline-block', animation: 'spin 1s linear infinite' }} />
                {scanProgress.phase === 'start' && (
                  <span>Scanning {scanProgress.totalSymbols || 0} symbols…</span>
                )}
                {scanProgress.phase === 'running' && (
                  <span>Scanned {scanProgress.scanned || 0} / {scanProgress.totalSymbols || 0}</span>
                )}
                {scanProgress.phase === 'done' && (
                  <span>Finishing…</span>
                )}
              </span>
            )}
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
          {useBuilder ? (
            <>
              <p style={{ color: '#666', marginTop: 0 }}>Build conditions with tokens. Toggle AND/OR for groups. Click tokens to edit timeframe, parameters, offsets.</p>
              <ScannerBuilder value={builderTree || undefined} onChange={setBuilderTree as any} />
            </>
          ) : (
            <>
              <p style={{ color: '#666', marginTop: 0 }}>Simple rows mode (legacy). All rows ANDed.</p>
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
                    {/* Left/right editors omitted for brevity in legacy mode */}
                    <div style={{ alignSelf: 'center' }}>
                      <button className="btn btn-secondary" onClick={() => removeFilter(f.id)}>Remove</button>
                    </div>
                  </div>
                </div>
              ))}
              <button className="btn btn-secondary" onClick={addFilter}>+ Add Filter</button>
            </>
          )}
        </div>
      </div>

      {/* Results Panel */}
      <div style={{ marginTop: 16, background: '#f5f5f5', border: '1px solid #e0e0e0', borderRadius: 8, padding: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h4 style={{ margin: 0 }}>Results</h4>
          {totalResults > 0 && (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <label style={{ fontSize: '0.9em', color: '#666' }}>Sort by:</label>
                <select value={sortBy} onChange={(e) => { setSortBy(e.target.value as any); setCurrentPage(0); }} style={{ fontSize: '0.9em' }}>
                  <option value="symbol">Symbol</option>
                  <option value="timestamp">Timestamp</option>
                </select>
                <select value={sortOrder} onChange={(e) => { setSortOrder(e.target.value as any); setCurrentPage(0); }} style={{ fontSize: '0.9em' }}>
                  <option value="asc">Ascending</option>
                  <option value="desc">Descending</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <label style={{ fontSize: '0.9em', color: '#666' }}>Page size:</label>
                <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(0); }} style={{ fontSize: '0.9em' }}>
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </div>
            </div>
          )}
        </div>
        {error && (
          <div style={{ padding: 10, background: '#ffebee', color: '#c62828', borderRadius: 4, marginBottom: 10 }}>
            {error}
          </div>
        )}
        {stats && (
          <div style={{ marginBottom: 10, color: '#666', display: 'flex', justifyContent: 'space-between' }}>
            <span>Scanned symbols: <strong>{stats.scannedSymbols}</strong> • Time: <strong>{stats.timeMs} ms</strong></span>
            {totalResults > 0 && (
              <span>Showing <strong>{startIdx + 1}-{endIdx}</strong> of <strong>{totalResults}</strong> matches</span>
            )}
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
                  <th style={{ textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #ddd' }}>Values</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #ddd' }}>Quick Actions</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, idx) => (
                  <tr key={`${r.symbol}-${idx}`} style={{ background: idx % 2 ? '#fff' : '#fafafa' }}>
                    <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>{r.symbol}</td>
                    <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>{new Date(r.timestamp * 1000).toLocaleString()}</td>
                    <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>
                      {r.explain ? (
                        <div title={JSON.stringify(r.explain, null, 2)} style={{ cursor: 'help', fontSize: '0.85em', color: '#555' }}>
                          {Object.keys(r.explain).length} values (hover)
                        </div>
                      ) : (
                        <span style={{ color: '#999', fontSize: '0.85em' }}>–</span>
                      )}
                    </td>
                    <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-secondary" onClick={() => openPreview(r.symbol)}>Quick Preview</button>
                        <button className="btn" onClick={() => viewInDataManagement(r.symbol)}>View in Data Management</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Pagination controls */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 16, paddingTop: 12, borderTop: '1px solid #ddd' }}>
                <button 
                  className="btn btn-secondary" 
                  disabled={currentPage === 0}
                  onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                  style={{ opacity: currentPage === 0 ? 0.5 : 1 }}
                >
                  ← Previous
                </button>
                <span style={{ color: '#666', fontSize: '0.9em' }}>
                  Page {currentPage + 1} of {totalPages}
                </span>
                <button 
                  className="btn btn-secondary" 
                  disabled={currentPage >= totalPages - 1}
                  onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                  style={{ opacity: currentPage >= totalPages - 1 ? 0.5 : 1 }}
                >
                  Next →
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Quick preview drawer */}
      {previewOpen && (
        <div style={{ position: 'fixed', right: 20, top: 80, width: 560, maxWidth: 'calc(100% - 40px)', background: '#fff', border: '1px solid #ddd', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', zIndex: 1200 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid #eee' }}>
            <div>
              <strong>Preview: {previewSymbol}</strong>
              <div style={{ fontSize: 12, color: '#666' }}>Last 50 bars</div>
            </div>
            <div>
              <button className="btn btn-secondary" onClick={() => setPreviewOpen(false)}>Close</button>
            </div>
          </div>
          <div style={{ padding: 12 }}>
            {previewLoading ? (
              <div style={{ padding: 20 }}>Loading preview…</div>
            ) : previewData.length === 0 ? (
              <div style={{ padding: 20, color: '#666' }}>No preview data</div>
            ) : (
              <div style={{ height: 320 }}>
                <CandlestickChart data={previewData} height={320} />
              </div>
            )}
            <div style={{ marginTop: 8, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn" onClick={() => previewSymbol && viewInDataManagement(previewSymbol)}>Open in Data Management</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Scanner;

// Inline spinner keyframes (scoped)
const style = document.createElement('style');
style.innerHTML = `@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}`;
document.head.appendChild(style);
