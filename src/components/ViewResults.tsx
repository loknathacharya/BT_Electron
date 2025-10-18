import React, { useState, useEffect } from 'react';

const ViewResults: React.FC = () => {
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

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>View Results</h2>
        <p>
          Analyze your backtesting results with detailed performance metrics,
          trade logs, and equity curve visualization.
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
            className={`nav-button ${selectedMetric === 'trades' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('trades')}
          >
            📋 Trade Log
          </button>
          <button
            className={`nav-button ${selectedMetric === 'charts' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('charts')}
          >
            📊 Charts
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
              <div className="data-controls">
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
                    <label htmlFor="startDate">From:</label>
                    <input
                      type="date"
                      id="startDate"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  
                  <div className="date-input-group">
                    <label htmlFor="endDate">To:</label>
                    <input
                      type="date"
                      id="endDate"
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
                  className="btn btn-secondary"
                  onClick={fetchPriceData}
                  disabled={loading}
                >
                  {loading ? 'Loading...' : 'Refresh'}
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
                Loading data...
              </div>
            ) : (
              <div className="data-table-container">
                <div className="data-summary" style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                  <p><strong>Total Rows:</strong> {filteredData.length}</p>
                  <p><strong>Selected Symbol:</strong> {selectedSymbol}</p>
                  <p><strong>Data Range:</strong> {filteredData.length > 0 ?
                    `${new Date(filteredData[0].timestamp * 1000).toLocaleDateString()} - ${new Date(filteredData[filteredData.length - 1].timestamp * 1000).toLocaleDateString()}` :
                    'No data available'}</p>
                </div>

                <div className="data-table-wrapper" style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Date</th>
                        <th>Open</th>
                        <th>High</th>
                        <th>Low</th>
                        <th>Close</th>
                        <th>Volume</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredData.map((row, index) => (
                        <tr key={index} className={index % 2 === 0 ? 'even-row' : 'odd-row'}>
                          <td>{row.symbol}</td>
                          <td>{row.date}</td>
                          <td className="price-cell">{row.open.toFixed(2)}</td>
                          <td className="price-cell">{row.high.toFixed(2)}</td>
                          <td className="price-cell">{row.low.toFixed(2)}</td>
                          <td className="price-cell">{row.close.toFixed(2)}</td>
                          <td>{row.volume.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {filteredData.length === 0 && (
                  <div className="no-data-message" style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                    No data found for the selected symbol.
                  </div>
                )}
              </div>
            )}

            <div className="data-verification" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#e8f5e8', borderRadius: '4px' }}>
              <h4>Data Verification</h4>
              <p>✅ Data imported successfully. You can now:</p>
              <ul>
                <li>Spot-check random rows against original CSV</li>
                <li>Verify OHLC values match exactly</li>
                <li>Check timestamp parsing is correct</li>
              </ul>
              <button
                className="btn"
                onClick={() => {
                  // Generate random sample for verification
                  const sample = filteredData.slice(0, 5);
                  console.log('Sample data for verification:', sample);
                  alert(`Sample data logged to console. Check rows 1-5 for verification against original CSV.`);
                }}
              >
                📋 Generate Sample for Verification
              </button>
            </div>
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
                    `${new Date(filteredData[0].timestamp * 1000).toLocaleDateString()} - ${new Date(filteredData[filteredData.length - 1].timestamp * 1000).toLocaleDateString()}` :
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