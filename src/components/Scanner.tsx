import React, { useEffect, useMemo, useState } from 'react';
import CandlestickChart from './CandlestickChart';
import { useNavigate } from 'react-router-dom';
import ScannerBuilder from './ScannerBuilder';
import { BuilderTree, treeToFilters } from './scannerBuilderModel';
import { useSymbolLists } from '../hooks/useSymbolLists';

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
  const [universeMode, setUniverseMode] = useState<'ALL' | 'LIST' | 'SAVED_LIST'>('ALL');
  const [universeList, setUniverseList] = useState<string>('');
  const [validationStatus, setValidationStatus] = useState<string>('');
  const [saveListName, setSaveListName] = useState<string>('');
  const [filters, setFilters] = useState<any[]>([initialFilter()]);
  const [useBuilder, setUseBuilder] = useState<boolean>(true);
  const [builderTree, setBuilderTree] = useState<BuilderTree | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [maxSymbols, setMaxSymbols] = useState<number>(0);
  const [scanProgress, setScanProgress] = useState<{phase: 'start'|'running'|'done'; scanned?: number; totalSymbols?: number} | null>(null);
  
  // Symbol list state
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [selectedSavedList, setSelectedSavedList] = useState<string>('');
  const [datasets, setDatasets] = useState<any[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const { symbolLists, loading: listsLoading } = useSymbolLists(selectedDataset);
  
  // Phase 4: Sorting and pagination state
  const [sortBy, setSortBy] = useState<'symbol' | 'timestamp'>('symbol');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [pageSize, setPageSize] = useState(50);
  const [currentPage, setCurrentPage] = useState(0);
  const [includeExplain, setIncludeExplain] = useState(false);
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  // DSL editor state
  const [useDsl, setUseDsl] = useState(false);
  const [dslText, setDslText] = useState<string>('');
  const [dslParse, setDslParse] = useState<{ ok: boolean; spec?: any; error?: string; pos?: number; token?: any } | null>(null);
  const [backtestMode, setBacktestMode] = useState<boolean>(false);
  const [backtestPerSymbolCap, setBacktestPerSymbolCap] = useState<number>(500);

  // Simple in-memory cache for parsed DSL
  const dslCacheRef = React.useRef<Map<string, any>>(new Map());
  const dslKey = useMemo(() => {
    if (!useDsl || !dslText) return '';
    let uni: any = 'ALL';
    if (universeMode === 'ALL') {
      uni = 'ALL';
    } else if (universeMode === 'LIST') {
      uni = universeList;
    } else if (universeMode === 'SAVED_LIST' && selectedSavedList) {
      const list = symbolLists.find(l => l.name === selectedSavedList);
      uni = list ? list.symbols : 'ALL';
    }
    return `${dslText}::${timeframe}::${JSON.stringify(uni)}`;
  }, [useDsl, dslText, timeframe, universeMode, universeList, selectedSavedList, symbolLists]);

  const scannerSpec = useMemo(() => {
    let uni: any = 'ALL';
    if (universeMode === 'ALL') {
      uni = 'ALL';
    } else if (universeMode === 'LIST') {
      uni = universeList.split(',').map(s => s.trim()).filter(Boolean);
    } else if (universeMode === 'SAVED_LIST' && selectedSavedList) {
      const list = symbolLists.find(l => l.name === selectedSavedList);
      uni = list ? list.symbols : 'ALL';
    }

    const spec: any = {
      timeframe,
      universe: uni,
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
  }, [timeframe, universeMode, universeList, selectedSavedList, symbolLists, filters, useBuilder, builderTree]);

  const runScan = async () => {
    try {
      setLoading(true);
      setError(null);
      setCurrentPage(0); // Reset to first page on new scan
      const uni = universeMode === 'ALL' ? 'ALL' : universeList.split(',').map(s => s.trim()).filter(Boolean);
      const baseOptions: any = {
        latestOnly: !backtestMode,
        sort: { by: sortBy, order: sortOrder },
        offset: 0,
        limit: 5000,
        maxSymbols: maxSymbols > 0 ? maxSymbols : undefined,
        includeExplain: includeExplain || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
      };
      if (backtestMode) {
        baseOptions.mode = 'backtest';
        baseOptions.backtestLimitPerSymbol = backtestPerSymbolCap || 500;
      }
      let payload: any;
      if (useDsl && dslText.trim()) {
        payload = {
          dsl: dslText,
          timeframe,
          universe: universeMode === 'ALL' ? 'ALL' : uni,
          options: baseOptions,
        };
      } else {
        payload = {
          scannerSpec,
          options: baseOptions,
        };
      }
      const response = await window.electronAPI.invoke('run-scan', payload);
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

  const rawResults = (result?.results || []) as any[];
  const stats = result?.stats;
  
  // Client-side pagination
  const totalResults = rawResults.length;
  const totalPages = Math.ceil(totalResults / pageSize);
  const startIdx = currentPage * pageSize;
  const endIdx = Math.min(startIdx + pageSize, totalResults);
  const results = rawResults.slice(startIdx, endIdx);

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

  // Fetch available datasets
  useEffect(() => {
    const fetchDatasets = async () => {
      setDatasetsLoading(true);
      try {
        const result = await window.electronAPI.invoke('get-all-datasets', {});
        if (!result.error) {
          setDatasets(result.datasets || []);
        }
      } catch (err) {
        console.error('Error fetching datasets:', err);
      } finally {
        setDatasetsLoading(false);
      }
    };

    fetchDatasets();
  }, []);

  // Load last used dataset and symbol list from localStorage on mount
  useEffect(() => {
    const lastDataset = localStorage.getItem('scanner_last_dataset');
    const lastSymbolList = localStorage.getItem('scanner_last_symbol_list');
    
    if (lastDataset && datasets.some(ds => ds.name === lastDataset)) {
      setSelectedDataset(lastDataset);
      setUniverseMode('SAVED_LIST');
      if (lastSymbolList) {
        setSelectedSavedList(lastSymbolList);
      }
    }
  }, [datasets]);

  // Save selectedDataset to localStorage
  useEffect(() => {
    if (selectedDataset) {
      localStorage.setItem('scanner_last_dataset', selectedDataset);
    } else {
      localStorage.removeItem('scanner_last_dataset');
    }
  }, [selectedDataset]);

  // Save selectedSavedList to localStorage
  useEffect(() => {
    if (selectedSavedList) {
      localStorage.setItem('scanner_last_symbol_list', selectedSavedList);
    } else {
      localStorage.removeItem('scanner_last_symbol_list');
    }
  }, [selectedSavedList]);

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
              <select value={universeMode} onChange={(e) => setUniverseMode(e.target.value as 'ALL' | 'LIST' | 'SAVED_LIST')} style={{ width: '100%' }}>
                <option value="ALL">All symbols</option>
                <option value="LIST">Manual list</option>
                <option value="SAVED_LIST">Saved list</option>
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
            {universeMode === 'SAVED_LIST' && (
              <>
                <div style={{ gridColumn: '1 / span 2' }}>
                  <label>Dataset</label>
                  <select
                    value={selectedDataset || ''}
                    onChange={(e) => {
                      setSelectedDataset(e.target.value);
                      setSelectedSavedList('');
                    }}
                    disabled={datasetsLoading}
                    style={{ width: '100%', marginBottom: 8 }}
                  >
                    <option value="">-- Select Dataset --</option>
                    {datasets.map(ds => (
                      <option key={ds.name} value={ds.name}>
                        {ds.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ gridColumn: '1 / span 2' }}>
                  <label>Saved Symbol List</label>
                  <select
                    value={selectedSavedList}
                    onChange={(e) => setSelectedSavedList(e.target.value)}
                    disabled={!selectedDataset || listsLoading}
                    style={{ width: '100%', marginBottom: 8 }}
                  >
                    <option value="">-- Select List --</option>
                    {symbolLists.map(list => (
                      <option key={list.id} value={list.name}>
                        {list.name} ({list.symbol_count} symbols)
                      </option>
                    ))}
                  </select>
                  {selectedSavedList && symbolLists.find(l => l.name === selectedSavedList)?.description && (
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                      {symbolLists.find(l => l.name === selectedSavedList)?.description}
                    </div>
                  )}
                </div>
              </>
            )}
            {universeMode === 'LIST' && (
              <div style={{ gridColumn: '1 / span 2' }}>
                <label>Symbols (comma separated)</label>
                <input
                  type="text"
                  placeholder="AAPL, MSFT, TSLA"
                  value={universeList}
                  onChange={(e) => setUniverseList(e.target.value)}
                  style={{ width: '100%', marginBottom: 8 }}
                />
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 8, marginBottom: 8 }}>
                  <button
                    className="btn btn-secondary"
                    onClick={async () => {
                      const list = universeList.split(',').map(s => s.trim()).filter(Boolean);
                      const first = list[0];
                      if (!first) { setValidationStatus('Enter at least one symbol'); return; }
                      const res = await window.electronAPI.invoke('validate-symbols', { symbols: [first] });
                      if (res?.error) { setValidationStatus(res.error); return; }
                      if (res.invalid && res.invalid.length) {
                        setValidationStatus(`Invalid: ${res.invalid.join(', ')}`);
                      } else {
                        setValidationStatus('Valid');
                      }
                    }}
                  >Validate</button>
                  <button
                    className="btn btn-secondary"
                    onClick={async () => {
                      const dlg = await window.electronAPI.invoke('open-file-dialog');
                      if (!dlg || dlg.canceled || !dlg.filePath) return;
                      const parsed = await window.electronAPI.invoke('parse-symbol-csv', { filePath: dlg.filePath });
                      if (parsed?.error) { setValidationStatus(parsed.error); return; }
                      const syms: string[] = parsed.symbols || [];
                      setUniverseList(syms.join(', '));
                      setValidationStatus(`Loaded ${syms.length} symbols from CSV`);
                    }}
                  >Load CSV</button>
                  <button
                    className="btn btn-secondary"
                    onClick={async () => {
                      const list = universeList.split(',').map(s => s.trim()).filter(Boolean);
                      if (!saveListName) { setValidationStatus('Enter watchlist name'); return; }
                      if (list.length === 0) { setValidationStatus('Enter symbols first'); return; }
                      const res = await window.electronAPI.invoke('save-watchlist', { name: saveListName, symbols: list, description: `Saved from scanner on ${new Date().toISOString()}` });
                      if (res?.error) { setValidationStatus(res.error); return; }
                      setValidationStatus(`Saved watchlist '${saveListName}' (${list.length} symbols)`);
                      setSaveListName('');
                    }}
                  >Save as Watchlist</button>
                </div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <input type="text" placeholder="Watchlist name to save" value={saveListName} onChange={e => setSaveListName(e.target.value)} style={{ flex: 1 }} />
                </div>
                {validationStatus && (
                  <div style={{ padding: 8, borderRadius: 4, background: validationStatus.startsWith('Invalid') ? '#ffebee' : '#e8f5e9', color: validationStatus.startsWith('Invalid') ? '#c62828' : '#2e7d32', fontSize: '0.9em' }}>
                    {validationStatus}
                  </div>
                )}
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
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8 }}>
            <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={useBuilder && !useDsl} onChange={(e) => { setUseBuilder(e.target.checked); if (e.target.checked) setUseDsl(false); }} />
              Use Builder
            </label>
            <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={useDsl} onChange={(e) => { setUseDsl(e.target.checked); if (e.target.checked) setUseBuilder(false); }} />
              Use DSL
            </label>
            <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={backtestMode} onChange={(e) => setBacktestMode(e.target.checked)} />
              Backtest mode
            </label>
            {backtestMode && (
              <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                <span>Per-symbol cap</span>
                <input type="number" min={1} max={5000} value={backtestPerSymbolCap} onChange={(e) => setBacktestPerSymbolCap(Number(e.target.value) || 500)} style={{ width: 90 }} />
              </span>
            )}
          </div>
          {useDsl ? (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                <textarea
                  value={dslText}
                  onChange={(e) => setDslText(e.target.value)}
                  placeholder="Enter DSL, e.g.:\nSMA(close, 50) CROSSES_ABOVE SMA(close, 200) AND RSI(close, 14) > 70"
                  style={{ width: '100%', minHeight: 120, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace', fontSize: 13, padding: 8 }}
                />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <button
                    className="btn btn-secondary"
                    onClick={async () => {
                      try {
                        setDslParse(null);
                        // Cache check
                        if (dslKey && dslCacheRef.current.has(dslKey)) {
                          const cached = dslCacheRef.current.get(dslKey);
                          setDslParse({ ok: true, spec: cached });
                          return;
                        }
                        const uni = universeMode === 'ALL' ? 'ALL' : universeList.split(',').map(s => s.trim()).filter(Boolean);
                        const res = await window.electronAPI.invoke('parse-dsl', { dsl: dslText, timeframe, universe: universeMode === 'ALL' ? 'ALL' : uni });
                        if (res?.error) {
                          const message = res.error === 'ParseError' ? res.message : res.error;
                          setDslParse({ ok: false, error: message, pos: res.pos, token: res.token });
                        } else {
                          setDslParse({ ok: true, spec: res.scannerSpec });
                          if (dslKey) dslCacheRef.current.set(dslKey, res.scannerSpec);
                        }
                      } catch (err: any) {
                        setDslParse({ ok: false, error: err?.message || 'parse failed' });
                      }
                    }}
                  >Parse</button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      setDslText('SMA(close, 50) CROSSES_ABOVE SMA(close, 200) AND RSI(close, 14) > 70');
                    }}
                  >Example 1</button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      setDslText('MAX(252, high) == high');
                    }}
                  >Example 2</button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      setDslText('[-1] close * 1.03 < open');
                    }}
                  >Example 3</button>
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                {dslParse?.ok && (
                  <>
                    <div style={{ color: '#2e7d32' }}>Parsed ✓</div>
                    <pre style={{ background: '#f7f7f7', padding: 8, borderRadius: 4, maxHeight: 180, overflow: 'auto' }}>{JSON.stringify(dslParse.spec, null, 2)}</pre>
                  </>
                )}
                {dslParse && !dslParse.ok && (
                  <div style={{ color: '#c62828' }}>
                    {dslParse.error}
                    {typeof dslParse.pos === 'number' && (
                      <>
                        <div style={{ fontSize: 12, marginTop: 4 }}>At position: {dslParse.pos}</div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </>
          ) : useBuilder ? (
            <>
              <p style={{ color: '#666', marginTop: 0 }}>Build conditions with tokens. Toggle AND/OR for groups. Click tokens to edit timeframe, parameters, offsets.</p>
              <ScannerBuilder value={builderTree || undefined} onChange={setBuilderTree as any} />
            </>
          ) : (
            <>
              <p style={{ color: '#666', marginTop: 0 }}>Simple rows mode (legacy). All rows ANDed.</p>
              {filters.map((f) => (
                <div key={f.id} style={{ padding: 10, border: '1px solid #ddd', borderRadius: 6, marginBottom: 10, background: '#fff' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
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
                    {f.op === 'compare' ? (
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
                    ) : (
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
                  </div>
                  {/* Left/right editors omitted for brevity in legacy mode */}
                  <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
                    <button className="btn btn-secondary" onClick={() => removeFilter(f.id)}>Remove</button>
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
                {results.map((r, idx) => {
                  // Handle both backtest and non-backtest modes
                  const isBacktest = Array.isArray(r.matches);
                  const displayTimestamp = r.timestamp ? new Date(r.timestamp * 1000).toLocaleString() : 
                                          (isBacktest && r.matches?.length > 0 ? new Date(r.matches[r.matches.length - 1].timestamp * 1000).toLocaleString() : 'N/A');
                  
                  return (
                    <tr key={`${r.symbol}-${idx}`} style={{ background: idx % 2 ? '#fff' : '#fafafa' }}>
                      <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>{r.symbol}</td>
                      <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>{displayTimestamp}</td>
                      <td style={{ padding: '8px 10px', borderBottom: '1px solid #eee' }}>
                        {r.explain ? (
                          <div title={JSON.stringify(r.explain, null, 2)} style={{ cursor: 'help', fontSize: '0.85em', color: '#555' }}>
                            {Object.keys(r.explain).length} values (hover)
                          </div>
                        ) : isBacktest ? (
                          <div style={{ fontSize: '0.85em', color: '#555' }}>
                            {r.matches?.length || 0} match{r.matches?.length !== 1 ? 'es' : ''}
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
                  );
                })}
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
