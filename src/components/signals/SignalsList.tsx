import React, { useState, useEffect, useCallback } from 'react';
import { Signal, SignalStrategy, SignalFilters } from '../../types/signals';

interface SignalsListProps {
  onSelectSignal?: (signalId: string) => void;
}

export const SignalsList: React.FC<SignalsListProps> = ({ onSelectSignal }) => {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [strategies, setStrategies] = useState<SignalStrategy[]>([]);
  const [datasets, setDatasets] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [datasetFilter, setDatasetFilter] = useState('');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<'' | 'open' | 'closed' | 'cancelled'>('');
  const [historicalFilter, setHistoricalFilter] = useState<'' | 'true' | 'false'>('');
  
  // Pagination
  const [page, setPage] = useState(0);
  const [pageSize] = useState(50);
  const [totalCount, setTotalCount] = useState(0);
  
  // Selected signal for detail view
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);

  useEffect(() => {
    loadStrategies();
    loadDatasets();
  }, []);

  useEffect(() => {
    loadSignals();
  }, [page, datasetFilter, symbolFilter, strategyFilter, statusFilter, historicalFilter]);

  const loadSignals = async () => {
    setLoading(true);
    setError(null);

    try {
      const filters: SignalFilters = {
        limit: pageSize,
        offset: page * pageSize
      };

      if (datasetFilter) filters.dataset_name = datasetFilter;
      if (symbolFilter) filters.symbol = symbolFilter;
      if (strategyFilter) filters.strategy_id = strategyFilter;
      if (statusFilter) filters.status = statusFilter;
      if (historicalFilter) filters.historical = historicalFilter === 'true';

      const result = await window.electron.invoke('get_signals', filters);

      if (result.success && result.signals) {
        setSignals(result.signals);
        setTotalCount(result.total || 0);
      } else {
        setError(result.error || 'Failed to load signals');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signals');
    } finally {
      setLoading(false);
    }
  };

  const loadStrategies = async () => {
    try {
      const result = await window.electron.invoke('get_signal_strategies', {});
      if (result.success && result.strategies) {
        setStrategies(result.strategies);
      }
    } catch (err) {
      console.error('Failed to load strategies:', err);
    }
  };

  const loadDatasets = async () => {
    try {
      const result = await window.electron.invoke('get-datasets', {});
      if (result.success && result.datasets) {
        setDatasets(result.datasets.map((d: any) => d.name));
      }
    } catch (err) {
      console.error('Failed to load datasets:', err);
    }
  };

  const handleCloseSignal = async (signalId: string) => {
    if (!confirm('Are you sure you want to close this signal?')) return;

    try {
      const result = await window.electron.invoke('close_signal', signalId, 'manual');
      if (result.success) {
        loadSignals(); // Refresh list
      } else {
        alert(`Failed to close signal: ${result.error}`);
      }
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleDeleteSignal = async (signalId: string) => {
    if (!confirm('Are you sure you want to delete this signal? This cannot be undone.')) return;

    try {
      const result = await window.electron.invoke('delete_signal', signalId);
      if (result.success) {
        loadSignals(); // Refresh list
      } else {
        alert(`Failed to delete signal: ${result.error}`);
      }
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleRefresh = () => {
    setPage(0);
    loadSignals();
  };

  const handleClearFilters = () => {
    setDatasetFilter('');
    setSymbolFilter('');
    setStrategyFilter('');
    setStatusFilter('');
    setHistoricalFilter('');
    setPage(0);
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const getStrategyName = (strategyId: string) => {
    const strategy = strategies.find(s => s.id === strategyId);
    return strategy?.name || strategyId.substring(0, 8);
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="signals-list">
      <div className="list-header">
        <h1>Signals</h1>
        <div className="header-actions">
          <button onClick={handleRefresh} className="button-secondary" disabled={loading}>
            {loading ? '⟳ Loading...' : '↻ Refresh'}
          </button>
        </div>
      </div>

      <div className="filters-panel">
        <div className="filters-grid">
          <div className="filter-group">
            <label>Dataset</label>
            <select
              value={datasetFilter}
              onChange={e => { setDatasetFilter(e.target.value); setPage(0); }}
              className="form-control"
            >
              <option value="">All Datasets</option>
              {datasets.map(ds => (
                <option key={ds} value={ds}>{ds}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Symbol</label>
            <input
              type="text"
              value={symbolFilter}
              onChange={e => { setSymbolFilter(e.target.value); setPage(0); }}
              placeholder="e.g., AAPL"
              className="form-control"
            />
          </div>

          <div className="filter-group">
            <label>Strategy</label>
            <select
              value={strategyFilter}
              onChange={e => { setStrategyFilter(e.target.value); setPage(0); }}
              className="form-control"
            >
              <option value="">All Strategies</option>
              {strategies.map(strategy => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Status</label>
            <select
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value as any); setPage(0); }}
              className="form-control"
            >
              <option value="">All Status</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <div className="filter-group">
            <label>Type</label>
            <select
              value={historicalFilter}
              onChange={e => { setHistoricalFilter(e.target.value as any); setPage(0); }}
              className="form-control"
            >
              <option value="">All Types</option>
              <option value="false">Live</option>
              <option value="true">Historical</option>
            </select>
          </div>

          <div className="filter-group filter-actions">
            <button onClick={handleClearFilters} className="button-link">
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <div className="results-summary">
        Showing {signals.length} of {totalCount} signals
      </div>

      <div className="table-container">
        <table className="signals-table">
          <thead>
            <tr>
              <th>Signal ID</th>
              <th>Strategy</th>
              <th>Symbol</th>
              <th>Direction</th>
              <th>Entry Time</th>
              <th>Status</th>
              <th>Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {signals.length === 0 ? (
              <tr>
                <td colSpan={8} className="no-results">
                  {loading ? 'Loading signals...' : 'No signals found'}
                </td>
              </tr>
            ) : (
              signals.map(signal => (
                <tr key={signal.id} className={selectedSignalId === signal.id ? 'selected' : ''}>
                  <td className="signal-id" title={signal.id}>
                    {signal.id.substring(0, 12)}...
                  </td>
                  <td>{getStrategyName(signal.strategy_id)}</td>
                  <td><strong>{signal.symbol}</strong></td>
                  <td>
                    <span className={`direction-badge ${signal.direction}`}>
                      {signal.direction === 'long' ? '↑' : '↓'} {signal.direction.toUpperCase()}
                    </span>
                  </td>
                  <td className="timestamp">
                    {new Date(signal.timestamp).toLocaleString()}
                  </td>
                  <td>
                    <span className={`status-badge ${signal.status}`}>
                      {signal.status}
                    </span>
                  </td>
                  <td>
                    {signal.historical ? (
                      <span className="type-badge historical">Historical</span>
                    ) : (
                      <span className="type-badge live">Live</span>
                    )}
                  </td>
                  <td className="actions">
                    <button
                      onClick={() => {
                        setSelectedSignalId(signal.id);
                        if (onSelectSignal) onSelectSignal(signal.id);
                      }}
                      className="action-button view"
                      title="View Details"
                    >
                      👁
                    </button>
                    {signal.status === 'open' && (
                      <button
                        onClick={() => handleCloseSignal(signal.id)}
                        className="action-button close"
                        title="Close Signal"
                      >
                        ✓
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteSignal(signal.id)}
                      className="action-button delete"
                      title="Delete Signal"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0 || loading}
            className="pagination-button"
          >
            ← Previous
          </button>
          <span className="pagination-info">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1 || loading}
            className="pagination-button"
          >
            Next →
          </button>
        </div>
      )}

      <style>{`
        .signals-list {
          padding: 2rem;
          max-width: 1400px;
          margin: 0 auto;
        }

        .list-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
        }

        .list-header h1 {
          margin: 0;
          font-size: 2rem;
        }

        .header-actions {
          display: flex;
          gap: 1rem;
        }

        .filters-panel {
          background: #f5f5f5;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
        }

        .filters-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          align-items: end;
        }

        .filter-group label {
          display: block;
          font-weight: 500;
          margin-bottom: 0.5rem;
          font-size: 0.9rem;
        }

        .filter-actions {
          display: flex;
          align-items: flex-end;
        }

        .form-control {
          width: 100%;
          padding: 0.5rem;
          border: 1px solid #ccc;
          border-radius: 4px;
          font-size: 0.9rem;
        }

        .button-secondary {
          background: white;
          border: 1px solid #ccc;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9rem;
        }

        .button-secondary:hover:not(:disabled) {
          background: #f5f5f5;
        }

        .button-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .button-link {
          background: none;
          border: none;
          color: #2196f3;
          cursor: pointer;
          text-decoration: underline;
          font-size: 0.9rem;
          padding: 0;
        }

        .button-link:hover {
          color: #1976d2;
        }

        .error-banner {
          background: #ffebee;
          border: 1px solid #ef5350;
          padding: 1rem;
          border-radius: 4px;
          margin-bottom: 1rem;
          color: #c62828;
        }

        .results-summary {
          margin-bottom: 1rem;
          color: #666;
          font-size: 0.9rem;
        }

        .table-container {
          overflow-x: auto;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .signals-table {
          width: 100%;
          border-collapse: collapse;
        }

        .signals-table thead {
          background: #f5f5f5;
        }

        .signals-table th {
          padding: 1rem;
          text-align: left;
          font-weight: 600;
          font-size: 0.9rem;
          border-bottom: 2px solid #e0e0e0;
        }

        .signals-table td {
          padding: 1rem;
          border-bottom: 1px solid #e0e0e0;
          font-size: 0.9rem;
        }

        .signals-table tbody tr:hover {
          background: #fafafa;
        }

        .signals-table tbody tr.selected {
          background: #e3f2fd;
        }

        .signal-id {
          font-family: monospace;
          color: #666;
          font-size: 0.85rem;
        }

        .timestamp {
          color: #666;
          font-size: 0.85rem;
        }

        .direction-badge {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .direction-badge.long {
          background: #c8e6c9;
          color: #2e7d32;
        }

        .direction-badge.short {
          background: #ffcdd2;
          color: #c62828;
        }

        .status-badge {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.8rem;
          font-weight: 500;
          text-transform: capitalize;
        }

        .status-badge.open {
          background: #fff3cd;
          color: #856404;
        }

        .status-badge.closed {
          background: #d1ecf1;
          color: #0c5460;
        }

        .status-badge.cancelled {
          background: #f8d7da;
          color: #721c24;
        }

        .type-badge {
          display: inline-block;
          padding: 0.2rem 0.5rem;
          border-radius: 3px;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .type-badge.live {
          background: #e8f5e9;
          color: #2e7d32;
        }

        .type-badge.historical {
          background: #e0e0e0;
          color: #616161;
        }

        .actions {
          display: flex;
          gap: 0.5rem;
        }

        .action-button {
          background: white;
          border: 1px solid #ccc;
          padding: 0.25rem 0.5rem;
          border-radius: 3px;
          cursor: pointer;
          font-size: 1rem;
        }

        .action-button:hover {
          background: #f5f5f5;
        }

        .action-button.view:hover {
          background: #e3f2fd;
          border-color: #2196f3;
        }

        .action-button.close:hover {
          background: #e8f5e9;
          border-color: #4caf50;
        }

        .action-button.delete:hover {
          background: #ffebee;
          border-color: #f44336;
        }

        .no-results {
          text-align: center;
          padding: 3rem;
          color: #999;
        }

        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 2rem;
          margin-top: 2rem;
        }

        .pagination-button {
          background: white;
          border: 1px solid #ccc;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9rem;
        }

        .pagination-button:hover:not(:disabled) {
          background: #f5f5f5;
        }

        .pagination-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .pagination-info {
          font-size: 0.9rem;
          color: #666;
        }
      `}</style>
    </div>
  );
};
