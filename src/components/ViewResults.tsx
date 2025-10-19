import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import CandlestickChart from './CandlestickChart';

const ViewResults: React.FC = () => {
  const location = useLocation();
  const [selectedMetric, setSelectedMetric] = useState('data-view');
  const [priceData, setPriceData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('ALL');
  const [symbols, setSymbols] = useState<string[]>([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [dateFilterApplied, setDateFilterApplied] = useState(false);
  
  // New: Dataset browsing state
  const [datasets, setDatasets] = useState<any[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  
  // New: Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 100;
  
  // New: Symbol search state
  const [symbolSearch, setSymbolSearch] = useState('');

  // Convert date string to timestamp
  const dateToTimestamp = (dateString: string) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return Math.floor(date.getTime() / 1000); // Convert to seconds
  };

  // Fetch price data from database
  const fetchPriceData = async () => {
    if (!window.electronAPI) {
      setError('Electron API not available');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Convert date strings to timestamps
      const startTimestamp = dateToTimestamp(startDate);
      const endTimestamp = dateToTimestamp(endDate);

      // Get both symbols and data in a single call
      const result = await window.electronAPI.invoke('get-price-data', {
        symbol: selectedSymbol || 'ALL',
        limit: 1000,
        offset: 0,
        start_date: startTimestamp,
        end_date: endTimestamp
      });
      
      if (result.error) {
        throw new Error(result.error);
      }

      // Update symbols list
      const availableSymbols = result.symbols ? ['ALL', ...result.symbols] : ['ALL'];
      setSymbols(availableSymbols);

      // Update price data
      setPriceData(result.data || []);
      
      // Check if date filter was applied
      setDateFilterApplied(!!(startTimestamp || endTimestamp));
      
      console.log('Data fetched successfully:', {
        symbol: selectedSymbol || 'ALL',
        dataCount: result.data?.length || 0,
        symbolsCount: availableSymbols.length,
        start_date: startTimestamp,
        end_date: endTimestamp
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching price data:', err);
    } finally {
      setLoading(false);
    }
  };

  const navigate = useNavigate();

  // If a symbol query param is provided, preselect it
  useEffect(() => {
    const qp = new URLSearchParams(window.location.search);
    const sym = qp.get('symbol');
    if (sym) {
      setSelectedSymbol(sym);
    }
  }, []);

  // Fetch available datasets from database
  const fetchDatasets = async () => {
    if (!window.electronAPI) {
      setError('Electron API not available');
      return;
    }

    setDatasetsLoading(true);
    setError('');

    try {
      const result = await window.electronAPI.invoke('get-datasets', {});
      
      if (result.error) {
        throw new Error(result.error);
      }

      setDatasets(result.datasets || []);
      console.log('Datasets fetched successfully:', result.datasets);
    } catch (err) {
      console.error('Error fetching datasets:', err);
      setDatasets([]);
    } finally {
      setDatasetsLoading(false);
    }
  };

  // Handle dataset selection
  const handleSelectDataset = (datasetName: string) => {
    setSelectedDataset(datasetName);
    // The data will be loaded via the normal price data fetch
    setSelectedSymbol('ALL');
    setStartDate('');
    setEndDate('');
  };

  // Fetch datasets on component mount
  useEffect(() => {
    fetchDatasets();
  }, []);

  // Fetch data on component mount and when selected symbol or date filters change
  useEffect(() => {
    fetchPriceData();
  }, [selectedSymbol, startDate, endDate]);

  // Filter data by selected symbol
  const filteredData = selectedSymbol === 'ALL'
    ? priceData
    : priceData.filter(item => item.symbol === selectedSymbol);

  // Filter symbols by search term
  const filteredSymbols = symbols.filter(symbol =>
    symbol.toLowerCase().includes(symbolSearch.toLowerCase())
  );

  // Pagination logic
  const totalPages = Math.ceil(filteredData.length / rowsPerPage);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  // Transform data for candlestick chart
  const candlestickData = filteredData.map((row, index) => ({
    time: row.date,
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
    volume: row.volume,
    timestamp: row.timestamp,
    index
  }));

  // Get candle chart data (limit to last 50 bars for readability)
  const candleChartData = candlestickData.slice(-50).map(d => ({
    name: d.time,
    open: Number(parseFloat(String(d.open)).toFixed(2)),
    high: Number(parseFloat(String(d.high)).toFixed(2)),
    low: Number(parseFloat(String(d.low)).toFixed(2)),
    close: Number(parseFloat(String(d.close)).toFixed(2)),
    volume: d.volume,
    // Calculate candle color (green for bullish, red for bearish)
    candleColor: d.close >= d.open ? '#4CAF50' : '#FF6B6B',
    // Calculate wick color (darker shade)
    wickColor: d.close >= d.open ? '#2E7D32' : '#C62828'
  }));

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Inline CandlestickChart component (SVG) — renders correct OHLC candles and volume bars
  // Use shared candlestick chart component

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>{location.pathname === '/results' ? 'Results & Analysis' : 'Data Management'}</h2>
        <p>
          {location.pathname === '/results'
            ? 'View backtest results, performance metrics, and strategy analysis.'
            : 'Browse, import, and manage your datasets. View and explore OHLCV data from your available datasets.'}
        </p>
      </div>

      <div className="results-container">
        <div className="results-navigation">
          <button
            className={`nav-button ${selectedMetric === 'browse-datasets' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('browse-datasets')}
          >
            📚 Browse Datasets
          </button>
          <button
            className={`nav-button ${selectedMetric === 'data-view' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('data-view')}
          >
            📊 Data View
          </button>
          <button
            className={`nav-button ${selectedMetric === 'overview' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('overview')}
          >
            📈 Overview
          </button>
          <button
            className={`nav-button ${selectedMetric === 'results-analysis' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('results-analysis')}
          >
            📋 Results & Analysis
          </button>
          <button
            className={`nav-button ${selectedMetric === 'ohlcv-chart' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('ohlcv-chart')}
          >
            📊 OHLCV Chart
          </button>
        </div>

        {selectedMetric === 'browse-datasets' && (
          <div className="browse-datasets-section">
            <div className="datasets-header">
              <h3>Available Datasets</h3>
              <p>Select an existing dataset to view its data without re-importing</p>
              <button
                className="btn btn-secondary"
                onClick={fetchDatasets}
                disabled={datasetsLoading}
              >
                {datasetsLoading ? 'Loading...' : 'Refresh'}
              </button>
            </div>

            {error && (
              <div className="error-message" style={{ padding: '10px', backgroundColor: '#ffebee', color: '#d32f2f', borderRadius: '4px', marginBottom: '15px' }}>
                {error}
              </div>
            )}

            {datasetsLoading ? (
              <div className="loading-message" style={{ padding: '20px', textAlign: 'center' }}>
                Loading datasets...
              </div>
            ) : datasets.length === 0 ? (
              <div className="no-data-message" style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                No datasets available. Import data first to create a dataset.
              </div>
            ) : (
              <div className="datasets-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '15px', marginBottom: '20px' }}>
                {datasets.map((dataset) => (
                  <div
                    key={dataset.id}
                    className={`dataset-card ${selectedDataset === dataset.name ? 'selected' : ''}`}
                    style={{
                      padding: '15px',
                      border: selectedDataset === dataset.name ? '2px solid #2196F3' : '1px solid #ddd',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      backgroundColor: selectedDataset === dataset.name ? '#f0f7ff' : '#fff',
                      transition: 'all 0.2s'
                    }}
                    onClick={() => handleSelectDataset(dataset.name)}
                  >
                    <h4 style={{ margin: '0 0 10px 0', color: '#1976d2' }}>{dataset.name}</h4>
                    <p style={{ margin: '5px 0', fontSize: '14px', color: '#666' }}>
                      {dataset.description}
                    </p>
                    <div style={{ margin: '10px 0', fontSize: '13px', backgroundColor: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
                      <p style={{ margin: '3px 0' }}>📊 Symbols: {dataset.symbol_count}</p>
                      <p style={{ margin: '3px 0' }}>📈 Rows: {dataset.total_rows?.toLocaleString()}</p>
                      <p style={{ margin: '3px 0' }}>📅 Range: {dataset.date_range_start ? new Date(dataset.date_range_start * 1000).toLocaleDateString() : 'N/A'} to {dataset.date_range_end ? new Date(dataset.date_range_end * 1000).toLocaleDateString() : 'N/A'}</p>
                      <p style={{ margin: '3px 0' }}>🕐 Last Updated: {new Date(dataset.last_updated * 1000).toLocaleDateString()}</p>
                    </div>
                    <button
                      className="btn btn-secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectDataset(dataset.name);
                        setSelectedMetric('data-view');
                      }}
                      style={{ width: '100%', marginTop: '10px' }}
                    >
                      View Data
                    </button>
                  </div>
                ))}
              </div>
            )}

            {selectedDataset && (
              <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e8f5e8', borderRadius: '4px' }}>
                <h4>Dataset Selected: {selectedDataset}</h4>
                <p>Click "View Data" above or go to Data View tab to see the data for this dataset.</p>
              </div>
            )}
          </div>
        )}

        {selectedMetric === 'data-view' && (
          <div className="data-view-section">
            <div className="data-view-header">
              <h3>Imported Data View</h3>
              {selectedDataset && (
                <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px', color: '#1976d2' }}>
                  📦 Current Dataset: <strong>{selectedDataset}</strong>
                </div>
              )}
              
              {/* Enhanced Controls Section */}
              <div className="data-controls" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                {/* Symbol Selection with Search/Filter */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <label style={{ fontWeight: 'bold', fontSize: '14px', color: '#333' }}>📊 Symbol Selection</label>
                  <input
                    type="text"
                    placeholder="🔍 Search symbols..."
                    value={symbolSearch}
                    onChange={(e) => setSymbolSearch(e.target.value)}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  />
                  <select
                    value={selectedSymbol}
                    onChange={(e) => {
                      setSelectedSymbol(e.target.value);
                      setCurrentPage(1);
                    }}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  >
                    {filteredSymbols.map(symbol => (
                      <option key={symbol} value={symbol}>{symbol}</option>
                    ))}
                  </select>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {filteredSymbols.length === symbols.length 
                      ? `${filteredSymbols.length} symbols available`
                      : `${filteredSymbols.length} of ${symbols.length} symbols match`}
                  </div>
                </div>
                
                {/* Improved Date Range Filter */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '10px', alignItems: 'flex-end' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label htmlFor="startDate" style={{ fontWeight: 'bold', fontSize: '14px', color: '#333' }}>📅 From Date</label>
                    <input
                      type="date"
                      id="startDate"
                      value={startDate}
                      onChange={(e) => {
                        setStartDate(e.target.value);
                        setCurrentPage(1);
                      }}
                      disabled={loading}
                      style={{
                        padding: '8px 12px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label htmlFor="endDate" style={{ fontWeight: 'bold', fontSize: '14px', color: '#333' }}>📅 To Date</label>
                    <input
                      type="date"
                      id="endDate"
                      value={endDate}
                      onChange={(e) => {
                        setEndDate(e.target.value);
                        setCurrentPage(1);
                      }}
                      disabled={loading}
                      style={{
                        padding: '8px 12px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                  
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="btn btn-secondary"
                      onClick={() => {
                        setStartDate('');
                        setEndDate('');
                        setDateFilterApplied(false);
                        setCurrentPage(1);
                      }}
                      disabled={loading || (!startDate && !endDate)}
                      style={{ padding: '8px 12px', fontSize: '14px' }}
                    >
                      🔄 Clear
                    </button>
                    
                    <button
                      className="btn btn-secondary"
                      onClick={fetchPriceData}
                      disabled={loading}
                      style={{ padding: '8px 12px', fontSize: '14px' }}
                    >
                      {loading ? '⏳ Loading...' : '🔄 Refresh'}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {dateFilterApplied && (
              <div className="filter-status" style={{
                padding: '10px',
                backgroundColor: '#e3f2fd',
                borderRadius: '4px',
                marginBottom: '15px',
                fontSize: '14px',
                color: '#1976d2',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span>📅</span>
                <span>Date filter applied: {startDate || 'Beginning'} to {endDate || 'End'}</span>
              </div>
            )}

            {error && (
              <div className="error-message" style={{ padding: '10px', backgroundColor: '#ffebee', color: '#d32f2f', borderRadius: '4px', marginBottom: '15px' }}>
                {error}
              </div>
            )}

            {loading ? (
              <div className="loading-message" style={{ padding: '20px', textAlign: 'center' }}>
                Loading data...
              </div>
            ) : (
              <div>
                {/* Candlestick Chart */}
                {selectedSymbol !== 'ALL' && candleChartData.length > 0 && (
                  <div style={{ 
                    marginBottom: '30px', 
                    padding: '15px', 
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px',
                    border: '1px solid #e0e0e0'
                  }}>
                    <h4 style={{ marginTop: 0, marginBottom: '15px', color: '#333' }}>🕯️ OHLCV Candlestick Chart (Last 50 Bars)</h4>
                    <div style={{ width: '100%', height: 400 }}>
                      <CandlestickChart data={candleChartData} height={400} />
                    </div>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '10px', fontStyle: 'italic' }}>
                      💡 Tip: Green bars show open price, red line shows close price. Dashed lines show high/low prices.
                      Purple bars show volume (right axis).
                    </div>
                  </div>
                )}

                {/* Data Summary */}
                <div className="data-summary" style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                    <div>
                      <p style={{ margin: '0 0 5px 0', color: '#666', fontSize: '12px' }}>📈 Total Rows</p>
                      <p style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: '#1976d2' }}>{filteredData.length.toLocaleString()}</p>
                    </div>
                    <div>
                      <p style={{ margin: '0 0 5px 0', color: '#666', fontSize: '12px' }}>📊 Selected Symbol</p>
                      <p style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: '#333' }}>{selectedSymbol}</p>
                    </div>
                    <div>
                      <p style={{ margin: '0 0 5px 0', color: '#666', fontSize: '12px' }}>📅 Data Range</p>
                      <p style={{ margin: 0, fontSize: '14px', fontWeight: 'bold', color: '#333' }}>
                        {filteredData.length > 0
                          ? `${new Date(filteredData[0].timestamp * 1000).toLocaleDateString()} - ${new Date(filteredData[filteredData.length - 1].timestamp * 1000).toLocaleDateString()}`
                          : 'No data'}
                      </p>
                    </div>
                    <div>
                      <p style={{ margin: '0 0 5px 0', color: '#666', fontSize: '12px' }}>📄 Showing Page</p>
                      <p style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: '#333' }}>{currentPage} of {totalPages || 1}</p>
                    </div>
                  </div>
                </div>

                {/* Data Table with Pagination */}
                <div className="data-table-container">
                  <div className="data-table-wrapper" style={{ overflowX: 'auto', border: '1px solid #ddd', borderRadius: '4px' }}>
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead style={{ backgroundColor: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                        <tr>
                          <th style={{ padding: '12px', textAlign: 'left', fontWeight: 'bold', borderRight: '1px solid #ddd' }}>Symbol</th>
                          <th style={{ padding: '12px', textAlign: 'left', fontWeight: 'bold', borderRight: '1px solid #ddd' }}>Date</th>
                          <th style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', borderRight: '1px solid #ddd' }}>Open</th>
                          <th style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', borderRight: '1px solid #ddd' }}>High</th>
                          <th style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', borderRight: '1px solid #ddd' }}>Low</th>
                          <th style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', borderRight: '1px solid #ddd' }}>Close</th>
                          <th style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold' }}>Volume</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedData.map((row, index) => (
                          <tr 
                            key={index} 
                            style={{
                              backgroundColor: index % 2 === 0 ? '#fff' : '#fafafa',
                              borderBottom: '1px solid #eee',
                              height: '40px'
                            }}
                          >
                            <td style={{ padding: '12px', borderRight: '1px solid #eee', fontWeight: '500' }}>{row.symbol}</td>
                            <td style={{ padding: '12px', borderRight: '1px solid #eee' }}>{row.date}</td>
                            <td style={{ padding: '12px', borderRight: '1px solid #eee', textAlign: 'right' }}>${row.open.toFixed(2)}</td>
                            <td style={{ padding: '12px', borderRight: '1px solid #eee', textAlign: 'right', color: '#4CAF50', fontWeight: '500' }}>${row.high.toFixed(2)}</td>
                            <td style={{ padding: '12px', borderRight: '1px solid #eee', textAlign: 'right', color: '#FF6B6B', fontWeight: '500' }}>${row.low.toFixed(2)}</td>
                            <td style={{ padding: '12px', borderRight: '1px solid #eee', textAlign: 'right', fontWeight: '500' }}>${row.close.toFixed(2)}</td>
                            <td style={{ padding: '12px', textAlign: 'right' }}>{row.volume.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {filteredData.length === 0 && (
                    <div className="no-data-message" style={{ padding: '30px', textAlign: 'center', color: '#999' }}>
                      <p style={{ fontSize: '16px', margin: '0 0 5px 0' }}>No data found</p>
                      <p style={{ fontSize: '14px', margin: 0, color: '#ccc' }}>Try adjusting your filters or selecting a different symbol</p>
                    </div>
                  )}

                  {/* Pagination Controls */}
                  {filteredData.length > 0 && (
                    <div style={{
                      marginTop: '15px',
                      padding: '15px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      backgroundColor: '#f5f5f5',
                      borderRadius: '4px'
                    }}>
                      <div style={{ fontSize: '14px', color: '#666' }}>
                        Showing <strong>{((currentPage - 1) * rowsPerPage) + 1}</strong> to <strong>{Math.min(currentPage * rowsPerPage, filteredData.length)}</strong> of <strong>{filteredData.length.toLocaleString()}</strong> rows ({rowsPerPage} per page)
                      </div>
                      <div style={{ display: 'flex', gap: '5px' }}>
                        <button
                          className="btn btn-secondary"
                          onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                          disabled={currentPage === 1}
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                        >
                          ◀ Previous
                        </button>
                        {/* Page numbers */}
                        {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                          const pageNum = i + 1;
                          return (
                            <button
                              key={pageNum}
                              onClick={() => setCurrentPage(pageNum)}
                              style={{
                                padding: '6px 10px',
                                fontSize: '12px',
                                border: pageNum === currentPage ? '2px solid #2196F3' : '1px solid #ddd',
                                backgroundColor: pageNum === currentPage ? '#e3f2fd' : '#fff',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontWeight: pageNum === currentPage ? 'bold' : 'normal'
                              }}
                            >
                              {pageNum}
                            </button>
                          );
                        })}
                        {totalPages > 5 && <span style={{ padding: '6px 8px' }}>...</span>}
                        <button
                          className="btn btn-secondary"
                          onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                          disabled={currentPage === totalPages}
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                        >
                          Next ▶
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Data Verification Section */}
                <div className="data-verification" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e8f5e8', borderRadius: '4px', borderLeft: '4px solid #4CAF50' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#2e7d32' }}>✅ Data Verification</h4>
                  <p style={{ margin: '0 0 10px 0', color: '#555' }}>Data imported successfully. You can now:</p>
                  <ul style={{ margin: 0, paddingLeft: '20px', color: '#555' }}>
                    <li>Spot-check random rows against original CSV</li>
                    <li>Verify OHLC values match exactly</li>
                    <li>Check timestamp parsing is correct</li>
                  </ul>
                  <button
                    className="btn"
                    onClick={() => {
                      const sample = filteredData.slice(0, 5);
                      console.log('Sample data for verification:', sample);
                      alert(`Sample data logged to console. Check rows 1-5 for verification against original CSV.`);
                    }}
                    style={{ marginTop: '10px', padding: '8px 16px', fontSize: '14px' }}
                  >
                    📋 Generate Sample for Verification
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {selectedMetric === 'overview' && (
          <div className="metrics-overview">
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-label">Total Data Points</div>
                <div className="metric-value positive">
                  {filteredData.length.toLocaleString()}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Symbols Available</div>
                <div className="metric-value">
                  {symbols.length - 1} {/* Excluding 'ALL' */}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Date Range</div>
                <div className="metric-value">
                  {filteredData.length > 0 ?
                    `${new Date(Math.min(...filteredData.map(d => d.timestamp)) * 1000).toLocaleDateString()} - ${new Date(Math.max(...filteredData.map(d => d.timestamp)) * 1000).toLocaleDateString()}` :
                    'No data'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Avg Volume</div>
                <div className="metric-value">
                  {filteredData.length > 0 ?
                    Math.round(filteredData.reduce((sum, item) => sum + (item.volume || 0), 0) / filteredData.length).toLocaleString() :
                    '0'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Avg Price</div>
                <div className="metric-value positive">
                  {filteredData.length > 0 ?
                    (filteredData.reduce((sum, item) => sum + item.close, 0) / filteredData.length).toFixed(2) :
                    '0.00'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Data Status</div>
                <div className="metric-value positive">
                  ✅ Imported
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedMetric === 'trades' && (
          <div className="trade-log">
            <div className="table-container">
              <table className="trade-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Date</th>
                    <th>Open</th>
                    <th>High</th>
                    <th>Low</th>
                    <th>Close</th>
                    <th>Volume</th>
                    <th>Price Change</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredData.slice(0, 20).map((row, index) => {
                    const priceChange = row.close - row.open;
                    const priceChangePercent = (priceChange / row.open) * 100;
                    
                    return (
                      <tr key={index}>
                        <td>{row.symbol}</td>
                        <td>{row.date}</td>
                        <td>{row.open.toFixed(2)}</td>
                        <td>{row.high.toFixed(2)}</td>
                        <td>{row.low.toFixed(2)}</td>
                        <td>{row.close.toFixed(2)}</td>
                        <td>{row.volume.toLocaleString()}</td>
                        <td className={priceChange >= 0 ? 'positive' : 'negative'}>
                          {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {filteredData.length > 20 && (
              <div className="more-data-notice" style={{ marginTop: '10px', color: '#666', fontSize: '14px' }}>
                Showing first 20 rows of {filteredData.length} total rows
              </div>
            )}
          </div>
        )}

        {selectedMetric === 'charts' && (
          <div className="charts-section">
            <div className="chart-placeholder">
              <div className="placeholder-content">
                <div className="placeholder-icon">📊</div>
                <h3>Equity Curve Chart</h3>
                <p>Interactive equity curve visualization will be displayed here</p>
                <div className="chart-features">
                  <ul>
                    <li>📈 Portfolio value over time</li>
                    <li>📊 Benchmark comparison</li>
                    <li>🔍 Zoom and pan controls</li>
                    <li>📥 Export to PNG/PDF</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedMetric === 'results-analysis' && (
          <div className="results-analysis-section">
            {/* Price Movement Analysis Section */}
            <div className="results-subsection">
              <h3>Price Movement Analysis</h3>
              <p style={{ color: '#666', marginBottom: '15px' }}>
                Detailed view of price movements and daily changes
              </p>
              <div className="table-container">
                <table className="trade-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Date</th>
                      <th>Open</th>
                      <th>High</th>
                      <th>Low</th>
                      <th>Close</th>
                      <th>Volume</th>
                      <th>Price Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredData.slice(0, 20).map((row, index) => {
                      const priceChange = row.close - row.open;
                      const priceChangePercent = (priceChange / row.open) * 100;
                      
                      return (
                        <tr key={index}>
                          <td>{row.symbol}</td>
                          <td>{row.date}</td>
                          <td>{row.open.toFixed(2)}</td>
                          <td>{row.high.toFixed(2)}</td>
                          <td>{row.low.toFixed(2)}</td>
                          <td>{row.close.toFixed(2)}</td>
                          <td>{row.volume.toLocaleString()}</td>
                          <td className={priceChange >= 0 ? 'positive' : 'negative'}>
                            {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {filteredData.length > 20 && (
                <div className="more-data-notice" style={{ marginTop: '10px', color: '#666', fontSize: '14px' }}>
                  Showing first 20 rows of {filteredData.length} total rows
                </div>
              )}
            </div>

            {/* Charts & Visualizations Section */}
            <div className="results-subsection" style={{ marginTop: '30px' }}>
              <h3>Charts & Visualizations</h3>
              <p style={{ color: '#666', marginBottom: '15px' }}>
                Interactive charts and equity curve visualization
              </p>
              <div className="chart-placeholder">
                <div className="placeholder-content">
                  <div className="placeholder-icon">📊</div>
                  <h4>Equity Curve Chart</h4>
                  <p>Interactive equity curve visualization will be displayed here</p>
                  <div className="chart-features">
                    <ul>
                      <li>📈 Portfolio value over time</li>
                      <li>📊 Benchmark comparison</li>
                      <li>🔍 Zoom and pan controls</li>
                      <li>📥 Export to PNG/PDF</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {selectedMetric === 'ohlcv-chart' && (
          <div className="ohlcv-chart-section">
            <div className="chart-header">
              <h3>OHLCV Chart</h3>
              <p style={{ color: '#666', marginBottom: '15px' }}>
                Interactive OHLCV (Open, High, Low, Close, Volume) chart visualization
              </p>
              <div className="chart-controls">
                <div className="symbol-filter">
                  <select
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value)}
                    className="symbol-select"
                  >
                    {symbols.map(symbol => (
                      <option key={symbol} value={symbol}>{symbol}</option>
                    ))}
                  </select>
                </div>
                
                <div className="date-filters">
                  <div className="date-input-group">
                    <label htmlFor="chartStartDate">From:</label>
                    <input
                      type="date"
                      id="chartStartDate"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  
                  <div className="date-input-group">
                    <label htmlFor="chartEndDate">To:</label>
                    <input
                      type="date"
                      id="chartEndDate"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  
                  <button
                    className="btn btn-secondary"
                    onClick={() => {
                      setStartDate('');
                      setEndDate('');
                      setDateFilterApplied(false);
                    }}
                    disabled={loading || (!startDate && !endDate)}
                  >
                    Clear
                  </button>
                </div>
                
                <button
                  className="btn"
                  onClick={fetchPriceData}
                  disabled={loading}
                >
                  {loading ? 'Loading...' : 'Update Chart'}
                </button>
              </div>
            </div>

            {dateFilterApplied && (
              <div className="filter-status" style={{
                padding: '10px',
                backgroundColor: '#e3f2fd',
                borderRadius: '4px',
                marginBottom: '15px',
                fontSize: '14px',
                color: '#1976d2',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span>📅</span>
                <span>Date filter applied: {startDate || 'Beginning'} to {endDate || 'End'}</span>
              </div>
            )}

            {error && (
              <div className="error-message" style={{ padding: '10px', backgroundColor: '#ffebee', color: '#d32f2f', borderRadius: '4px', marginBottom: '15px' }}>
                {error}
              </div>
            )}

            {loading ? (
              <div className="loading-message" style={{ padding: '20px', textAlign: 'center' }}>
                Loading chart data...
              </div>
            ) : (
              <div className="ohlcv-chart-container">
                {/* OHLCV Candlestick Chart */}
                {selectedSymbol !== 'ALL' && candleChartData.length > 0 ? (
                  <div style={{
                    marginBottom: '20px',
                    padding: '15px',
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px',
                    border: '1px solid #e0e0e0'
                  }}>
                    <h4 style={{ marginTop: 0, marginBottom: '15px', color: '#333' }}>🕯️ OHLCV Candlestick Chart</h4>
                    <div style={{ width: '100%', height: 400 }}>
                      <CandlestickChart data={candleChartData} height={400} />
                    </div>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '10px', fontStyle: 'italic' }}>
                      💡 Tip: Green bars show open price, red line shows close price. Dashed lines show high/low prices.
                      Purple bars show volume (right axis).
                    </div>
                  </div>
                ) : (
                  <div className="ohlcv-chart-placeholder">
                    <div className="placeholder-content">
                      <div className="placeholder-icon">📈</div>
                      <h4>OHLCV Chart</h4>
                      <p>Select a specific symbol to view the OHLCV candlestick chart</p>
                      <div className="chart-features">
                        <ul>
                          <li>🕯️ Candlestick patterns</li>
                          <li>📊 Volume bars</li>
                          <li>🔍 Zoom and pan controls</li>
                          <li>📈 Technical indicators</li>
                          <li>📥 Export to PNG/PDF</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
                
                <div className="ohlcv-data-summary" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                  <h4>Data Summary</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '10px' }}>
                    <div>
                      <strong>Symbol:</strong> {selectedSymbol}
                    </div>
                    <div>
                      <strong>Data Points:</strong> {filteredData.length}
                    </div>
                    <div>
                      <strong>Date Range:</strong> {filteredData.length > 0 ?
                        `${new Date(Math.min(...filteredData.map(d => d.timestamp)) * 1000).toLocaleDateString()} - ${new Date(Math.max(...filteredData.map(d => d.timestamp)) * 1000).toLocaleDateString()}` :
                        'No data available'}
                    </div>
                    <div>
                      <strong>Last Price:</strong> {filteredData.length > 0 ? formatCurrency(filteredData[filteredData.length - 1].close) : 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="results-actions">
          <button className="btn">Export Results</button>
          <button className="btn btn-secondary">Save Report</button>
          <button className="btn btn-secondary">Compare Strategies</button>
        </div>
      </div>
    </div>
  );
};

export default ViewResults;