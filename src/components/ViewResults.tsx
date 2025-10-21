import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import CandlestickChart from './CandlestickChart';
import ImportData from './ImportData';
import DataAnalysis from './DataAnalysis';
import './ViewResults.css';

const ViewResults: React.FC = () => {
  const location = useLocation();
  // Default to Browse Datasets when opening Data Management
  const [selectedMetric, setSelectedMetric] = useState('browse-datasets');
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
  
  // New: Chart modal state
  const [chartModalOpen, setChartModalOpen] = useState(false);
  const [chartModalSymbol, setChartModalSymbol] = useState<string | null>(null);
  const [chartModalData, setChartModalData] = useState<any[]>([]);

  // New: Delete confirmation modal state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [datasetToDelete, setDatasetToDelete] = useState<any>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

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

  // Handle opening delete confirmation modal
  const handleOpenDeleteConfirm = (dataset: any) => {
    setDatasetToDelete(dataset);
    setDeleteConfirmOpen(true);
  };

  // Handle confirming dataset deletion
  const handleConfirmDelete = async () => {
    if (!datasetToDelete || !window.electronAPI) {
      return;
    }

    setIsDeleting(true);
    try {
      const result = await window.electronAPI.invoke('delete-dataset', {
        name: datasetToDelete.name
      });

      if (result.error) {
        throw new Error(result.error);
      }

      // Show success message
      const deletedName = datasetToDelete.name;
      setSuccessMessage(`✅ Dataset "${deletedName}" has been successfully deleted.`);
      
      // Auto-dismiss success message after 4 seconds
      setTimeout(() => setSuccessMessage(''), 4000);

      // Refresh datasets list after successful deletion
      await fetchDatasets();
      
      // Clear selected dataset if it was the one deleted
      if (selectedDataset === datasetToDelete.name) {
        setSelectedDataset(null);
      }

      console.log('Dataset deleted successfully:', datasetToDelete.name);
    } catch (err) {
      console.error('Error deleting dataset:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete dataset');
    } finally {
      setIsDeleting(false);
      setDeleteConfirmOpen(false);
      setDatasetToDelete(null);
    }
  };

  // Handle closing delete confirmation without deleting
  const handleCancelDelete = () => {
    setDeleteConfirmOpen(false);
    setDatasetToDelete(null);
  };

  // Handle opening chart modal for a specific symbol
  const handleOpenChartModal = async (symbol: string) => {
    setChartModalSymbol(symbol);
    
    // Fetch all data for this specific symbol (no date filters)
    if (!window.electronAPI) {
      setError('Electron API not available');
      return;
    }

    try {
      const result = await window.electronAPI.invoke('get-price-data', {
        symbol: symbol,
        limit: 10000, // Get a large limit to capture all available data
        offset: 0,
        start_date: null,
        end_date: null
      });
      
      if (result.error) {
        throw new Error(result.error);
      }

      setChartModalData(result.data || []);
    } catch (err) {
      console.error('Error fetching chart data:', err);
      setChartModalData([]);
    }
    
    setChartModalOpen(true);
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
      <div className="tab-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>{location.pathname === '/results' ? 'Results & Analysis' : 'Data Management'}</h2>
          <p>
            {location.pathname === '/results'
              ? 'View backtest results, performance metrics, and strategy analysis.'
              : 'Browse, import, and manage your datasets. View and explore OHLCV data from your available datasets.'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => {
              console.log('Import Data button clicked, navigating to /import');
              navigate('/import');
            }}
            title="Import Data"
          >
            Import Data
          </button>
        </div>
      </div>

  <div className="results-container">
        <div className="results-navigation tabs-with-descriptions">
          <button
            className={`nav-button tab-with-desc ${selectedMetric === 'browse-datasets' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('browse-datasets')}
          >
            <div className="tab-label">� Browse Datasets</div>
            <div className="tab-description">View and manage imported datasets</div>
          </button>
          <button
            className={`nav-button tab-with-desc ${selectedMetric === 'data-view' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('data-view')}
          >
            <div className="tab-label">📊 Data View</div>
            <div className="tab-description">Explore OHLCV data</div>
          </button>
          <button
            className={`nav-button tab-with-desc ${selectedMetric === 'results-analysis' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('results-analysis')}
          >
            <div className="tab-label">📊 Analysis</div>
            <div className="tab-description">Results & analysis</div>
          </button>
          <button
            className={`nav-button tab-with-desc ${selectedMetric === 'data-quality' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('data-quality')}
          >
            <div className="tab-label">✓ Data Quality</div>
            <div className="tab-description">Data quality metrics & analysis</div>
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

            {successMessage && (
              <div className="success-message" style={{ padding: '12px', backgroundColor: '#e8f5e9', color: '#2e7d32', borderRadius: '4px', marginBottom: '15px', border: '1px solid #c8e6c9' }}>
                {successMessage}
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
                    <button
                      className="btn btn-secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenDeleteConfirm(dataset);
                      }}
                      style={{ 
                        width: '100%', 
                        marginTop: '8px',
                        backgroundColor: '#ffebee',
                        color: '#d32f2f',
                        border: '1px solid #d32f2f'
                      }}
                      title="Delete this dataset (cannot be undone)"
                    >
                      🗑️ Delete
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
                          <th style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', borderRight: '1px solid #ddd' }}>Volume</th>
                          <th style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold' }}>Chart</th>
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
                            <td style={{ padding: '12px', borderRight: '1px solid #eee', textAlign: 'right' }}>{row.volume.toLocaleString()}</td>
                            <td style={{ padding: '12px', textAlign: 'center', borderRight: 'none' }}>
                              <button
                                className="btn btn-secondary"
                                onClick={() => handleOpenChartModal(row.symbol)}
                                style={{ padding: '4px 10px', fontSize: '12px' }}
                                title={`View chart for ${row.symbol}`}
                              >
                                📈 Chart
                              </button>
                            </td>
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

        <div className="results-actions">
          <button className="btn">Export Results</button>
          <button className="btn btn-secondary">Save Report</button>
          <button className="btn btn-secondary">Compare Strategies</button>
        </div>

        {selectedMetric === 'data-quality' && (
          <div className="data-quality-section">
            <DataAnalysis />
          </div>
        )}

        {/* Delete Dataset Confirmation Modal */}
        {deleteConfirmOpen && datasetToDelete && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1600,
            padding: '20px'
          }}>
            <div style={{
              width: 'min(500px, 100%)',
              backgroundColor: '#fff',
              borderRadius: '8px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
              padding: '30px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '15px', color: '#d32f2f' }}>⚠️</div>
              <h3 style={{ marginTop: 0, color: '#d32f2f', fontSize: '22px' }}>Delete Dataset?</h3>
              <p style={{ color: '#666', marginBottom: '15px', fontSize: '15px' }}>
                You are about to delete: <strong>{datasetToDelete.name}</strong>
              </p>
              <div style={{
                backgroundColor: '#fff3e0',
                border: '1px solid #ffb74d',
                borderRadius: '4px',
                padding: '12px',
                marginBottom: '20px',
                fontSize: '14px',
                color: '#e65100'
              }}>
                <strong>⚠️ Warning:</strong> This action <strong>CANNOT be undone</strong>. All associated data ({datasetToDelete.total_rows?.toLocaleString()} rows, {datasetToDelete.symbol_count} symbols) will be permanently deleted from the database.
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                <button
                  className="btn btn-secondary"
                  onClick={handleCancelDelete}
                  disabled={isDeleting}
                  style={{ 
                    padding: '10px 24px',
                    fontSize: '14px'
                  }}
                >
                  Cancel
                </button>
                <button
                  className="btn"
                  onClick={handleConfirmDelete}
                  disabled={isDeleting}
                  style={{ 
                    padding: '10px 24px',
                    fontSize: '14px',
                    backgroundColor: '#d32f2f',
                    color: '#fff',
                    border: 'none'
                  }}
                >
                  {isDeleting ? '⏳ Deleting...' : '🗑️ Delete Forever'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Chart Modal */}
        {chartModalOpen && chartModalSymbol && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1500,
            padding: '20px'
          }}>
            <div style={{
              width: 'min(1400px, 100%)',
              maxHeight: '90vh',
              overflowY: 'auto',
              backgroundColor: '#fff',
              borderRadius: '8px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
              position: 'relative',
              padding: '20px'
            }}>
              <button
                onClick={() => setChartModalOpen(false)}
                style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  background: 'transparent',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#666'
                }}
                aria-label="Close Chart"
              >
                ✕
              </button>

              <h3 style={{ marginTop: 0, marginBottom: '20px' }}>📈 OHLCV Chart - {chartModalSymbol}</h3>

              {chartModalData.length > 0 ? (
                <div>
                  {/* Chart Data Summary */}
                  <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                      <div>
                        <strong>Symbol:</strong> {chartModalSymbol}
                      </div>
                      <div>
                        <strong>Data Points:</strong> {chartModalData.length}
                      </div>
                      <div>
                        <strong>Date Range:</strong> {chartModalData.length > 0 ?
                          `${new Date(Math.min(...chartModalData.map(d => d.timestamp)) * 1000).toLocaleDateString()} - ${new Date(Math.max(...chartModalData.map(d => d.timestamp)) * 1000).toLocaleDateString()}` :
                          'No data available'}
                      </div>
                      <div>
                        <strong>Last Price:</strong> {chartModalData.length > 0 ? formatCurrency(chartModalData[chartModalData.length - 1].close) : 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* Candlestick Chart */}
                  <div style={{
                    padding: '15px',
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px',
                    border: '1px solid #e0e0e0'
                  }}>
                    <h4 style={{ marginTop: 0, marginBottom: '15px', color: '#333' }}>🕯️ OHLCV Candlestick Chart (Full Data Range)</h4>
                    <div style={{ width: '100%', height: 500 }}>
                      <CandlestickChart 
                        data={chartModalData.map(d => ({
                          name: d.date,
                          open: Number(parseFloat(String(d.open)).toFixed(2)),
                          high: Number(parseFloat(String(d.high)).toFixed(2)),
                          low: Number(parseFloat(String(d.low)).toFixed(2)),
                          close: Number(parseFloat(String(d.close)).toFixed(2)),
                          volume: d.volume,
                          candleColor: d.close >= d.open ? '#4CAF50' : '#FF6B6B',
                          wickColor: d.close >= d.open ? '#2E7D32' : '#C62828'
                        }))} 
                        height={500} 
                      />
                    </div>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '10px', fontStyle: 'italic' }}>
                      💡 Tip: Green bars show open price, red line shows close price. Dashed lines show high/low prices.
                      Purple bars show volume (right axis). Use zoom and pan to explore the data.
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ padding: '30px', textAlign: 'center', color: '#999' }}>
                  <p>No chart data available for {chartModalSymbol}</p>
                </div>
              )}
            </div>
          </div>
        )}

      {/* Import Data Modal (route: /import) — render inside tab-content so JSX has a single root */}
      {(() => {
        console.log('Modal condition check - pathname:', location.pathname, 'showing modal?', location.pathname === '/import');
        return location.pathname === '/import' && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.4)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 2000,
            padding: '20px'
          }}>
            <div style={{
              width: 'min(1200px, 100%)',
              maxHeight: '90vh',
              overflowY: 'auto',
              backgroundColor: '#fff',
              borderRadius: '8px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
              position: 'relative',
              padding: '20px'
            }}>
              <button
                onClick={() => navigate('/')}
                style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  background: 'transparent',
                  border: 'none',
                  fontSize: '18px',
                  cursor: 'pointer'
                }}
                aria-label="Close Import"
              >
                ✕
              </button>
              <ImportData />
            </div>
          </div>
        );
      })()}
    </div>
    </div>
  );
};

export default ViewResults;