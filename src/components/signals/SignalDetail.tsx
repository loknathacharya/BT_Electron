import React, { useState, useEffect } from 'react';
import { Signal, SignalStrategy } from '../../types/signals';
import { ExpressionBuilder } from './ExpressionBuilder';

interface SignalDetailProps {
  signalId: string;
  onClose: () => void;
  onUpdate?: () => void;
}

export const SignalDetail: React.FC<SignalDetailProps> = ({ signalId, onClose, onUpdate }) => {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [strategy, setStrategy] = useState<SignalStrategy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  
  // Edit form state
  const [editedExitCriteria, setEditedExitCriteria] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSignalAndStrategy();
  }, [signalId]);

  const loadSignalAndStrategy = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load signal
      const signalResult = await window.electron.invoke('get_signal', signalId);
      if (!signalResult.success || !signalResult.signal) {
        throw new Error(signalResult.error || 'Failed to load signal');
      }
      setSignal(signalResult.signal);
      setEditedExitCriteria(signalResult.signal.exit_criteria || []);

      // Load strategy
      const strategyResult = await window.electron.invoke('get_signal_strategy', signalResult.signal.strategy_id);
      if (strategyResult.success && strategyResult.strategy) {
        setStrategy(strategyResult.strategy);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signal');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveExitCriteria = async () => {
    if (!signal) return;

    setSaving(true);
    try {
      const result = await window.electron.invoke('update_signal', signalId, {
        exit_criteria: editedExitCriteria
      });

      if (result.success) {
        await loadSignalAndStrategy();
        setEditMode(false);
        if (onUpdate) onUpdate();
      } else {
        alert(`Failed to update signal: ${result.error}`);
      }
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCloseSignal = async () => {
    if (!signal) return;
    if (!confirm('Are you sure you want to close this signal?')) return;

    try {
      const result = await window.electron.invoke('close_signal', signalId, 'manual');
      if (result.success) {
        await loadSignalAndStrategy();
        if (onUpdate) onUpdate();
      } else {
        alert(`Failed to close signal: ${result.error}`);
      }
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleCancelSignal = async () => {
    if (!signal) return;
    if (!confirm('Are you sure you want to cancel this signal?')) return;

    try {
      const result = await window.electron.invoke('close_signal', signalId, 'cancelled');
      if (result.success) {
        await loadSignalAndStrategy();
        if (onUpdate) onUpdate();
      } else {
        alert(`Failed to cancel signal: ${result.error}`);
      }
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const formatDate = (timestamp: string | number) => {
    // Handle both ISO8601 string and Unix timestamp
    if (typeof timestamp === 'string') {
      return new Date(timestamp).toLocaleString();
    }
    return new Date(timestamp * 1000).toLocaleString();
  };

  if (loading) {
    return (
      <div className="signal-detail-modal">
        <div className="modal-content">
          <div className="loading">Loading signal details...</div>
        </div>
      </div>
    );
  }

  if (error || !signal) {
    return (
      <div className="signal-detail-modal">
        <div className="modal-content">
          <div className="modal-header">
            <h2>Error</h2>
            <button onClick={onClose} className="close-button">✕</button>
          </div>
          <div className="modal-body">
            <div className="error-message">{error || 'Signal not found'}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="signal-detail-modal" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>Signal Details</h2>
            <button onClick={onClose} className="close-button">✕</button>
          </div>

          <div className="modal-body">
            {/* Status Banner */}
            <div className={`status-banner status-${signal.status}`}>
              <span className="status-icon">
                {signal.status === 'open' ? '🟢' : signal.status === 'closed' ? '🔵' : '⚫'}
              </span>
              <span className="status-text">
                {signal.status.toUpperCase()}
                {signal.status === 'closed' && signal.close_reason && ` - ${signal.close_reason}`}
              </span>
            </div>

            {/* Basic Information */}
            <div className="info-section">
              <h3>Basic Information</h3>
              <div className="info-grid">
                <div className="info-item">
                  <label>Signal ID:</label>
                  <span className="mono">{signal.id}</span>
                </div>
                <div className="info-item">
                  <label>Symbol:</label>
                  <span className="highlight">{signal.symbol}</span>
                </div>
                <div className="info-item">
                  <label>Direction:</label>
                  <span className={`direction-badge ${signal.direction}`}>
                    {signal.direction === 'long' ? '↑' : '↓'} {signal.direction.toUpperCase()}
                  </span>
                </div>
                <div className="info-item">
                  <label>Type:</label>
                  <span>{signal.historical ? 'Historical' : 'Live'}</span>
                </div>
                <div className="info-item">
                  <label>Dataset:</label>
                  <span>{signal.dataset_name}</span>
                </div>
                <div className="info-item">
                  <label>Entry Time:</label>
                  <span>{formatDate(signal.timestamp)}</span>
                </div>
                {signal.closed_at && (
                  <div className="info-item">
                    <label>Closed Time:</label>
                    <span>{formatDate(signal.closed_at)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Strategy Information */}
            {strategy && (
              <div className="info-section">
                <h3>Strategy: {strategy.name}</h3>
                {strategy.description && (
                  <p className="strategy-description">{strategy.description}</p>
                )}
                <div className="info-grid">
                  <div className="info-item">
                    <label>Scope:</label>
                    <span>{strategy.scope}</span>
                  </div>
                  <div className="info-item">
                    <label>Direction:</label>
                    <span>{strategy.default_direction}</span>
                  </div>
                  <div className="info-item">
                    <label>Exit Logic:</label>
                    <span>{strategy.metadata.exit_logic === 'any' ? 'Any (first exit)' : 'All (all exits)'}</span>
                  </div>
                  <div className="info-item">
                    <label>Reversal:</label>
                    <span>{strategy.metadata.reversal_mode?.replace(/-/g, ' ') || 'N/A'}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Entry Conditions */}
            <div className="info-section">
              <h3>Entry Conditions</h3>
              {strategy?.conditions.entry && strategy.conditions.entry.length > 0 ? (
                strategy.conditions.entry.map((expr, index) => (
                  <div key={index} className="expression-display">
                    <code>{expr}</code>
                  </div>
                ))
              ) : (
                <div className="no-data">No entry expression defined</div>
              )}
              {signal.entry_values && Object.keys(signal.entry_values).length > 0 && (
                <div className="values-grid">
                  <h4>Entry Values</h4>
                  {Object.entries(signal.entry_values).map(([key, value]) => (
                    <div key={key} className="value-item">
                      <label>{key}:</label>
                      <span>{typeof value === 'number' ? value.toFixed(4) : String(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Exit Criteria */}
            <div className="info-section">
              <div className="section-header">
                <h3>Exit Criteria</h3>
                {signal.status === 'open' && !editMode && (
                  <button onClick={() => setEditMode(true)} className="button-secondary small">
                    Edit
                  </button>
                )}
                {editMode && (
                  <div className="edit-actions">
                    <button onClick={handleSaveExitCriteria} disabled={saving} className="button-primary small">
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => {
                        setEditMode(false);
                        setEditedExitCriteria(signal.exit_criteria || []);
                      }}
                      className="button-secondary small"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {editMode ? (
                <div className="exit-criteria-editor">
                  {editedExitCriteria.map((expr, index) => (
                    <div key={index} className="exit-criterion-edit">
                      <div className="criterion-header">
                        <label>Exit Condition {index + 1}</label>
                        <button
                          onClick={() => setEditedExitCriteria(editedExitCriteria.filter((_, i) => i !== index))}
                          className="button-link"
                        >
                          Remove
                        </button>
                      </div>
                      <ExpressionBuilder
                        value={expr}
                        onChange={(newExpr) => {
                          const updated = [...editedExitCriteria];
                          updated[index] = newExpr;
                          setEditedExitCriteria(updated);
                        }}
                        placeholder="Exit condition expression"
                        datasetName={signal.dataset_name}
                      />
                    </div>
                  ))}
                  <button
                    onClick={() => setEditedExitCriteria([...editedExitCriteria, ''])}
                    className="button-secondary small"
                  >
                    + Add Exit Condition
                  </button>
                </div>
              ) : (
                <div className="exit-criteria-display">
                  {signal.exit_criteria && signal.exit_criteria.length > 0 ? (
                    signal.exit_criteria.map((expr, index) => (
                      <div key={index} className="expression-display">
                        <label>Exit {index + 1}:</label>
                        <code>{expr}</code>
                      </div>
                    ))
                  ) : (
                    <div className="no-data">No exit criteria defined</div>
                  )}
                </div>
              )}
            </div>

            {/* Status Timeline */}
            <div className="info-section">
              <h3>Timeline</h3>
              <div className="timeline">
                <div className="timeline-item">
                  <div className="timeline-marker created"></div>
                  <div className="timeline-content">
                    <strong>Created</strong>
                    <span>{formatDate(signal.timestamp)}</span>
                  </div>
                </div>
                {signal.closed_at && (
                  <div className="timeline-item">
                    <div className="timeline-marker closed"></div>
                    <div className="timeline-content">
                      <strong>Closed</strong>
                      <span>{formatDate(signal.closed_at)}</span>
                      {signal.close_reason && (
                        <span className="reason">Reason: {signal.close_reason}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="modal-footer">
            {signal.status === 'open' && (
              <>
                <button onClick={handleCloseSignal} className="button-primary">
                  Close Signal
                </button>
                <button onClick={handleCancelSignal} className="button-secondary">
                  Cancel Signal
                </button>
              </>
            )}
            <button onClick={onClose} className="button-secondary">
              Close
            </button>
          </div>
        </div>
      </div>

      <style>{`
        .signal-detail-modal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 1rem;
        }

        .signal-detail-modal .modal-content {
          background: white;
          border-radius: 8px;
          max-width: 900px;
          width: 100%;
          max-height: 90vh;
          display: flex;
          flex-direction: column;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }

        .signal-detail-modal .modal-header {
          padding: 1.5rem;
          border-bottom: 1px solid #e0e0e0;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .signal-detail-modal .modal-header h2 {
          margin: 0;
          font-size: 1.5rem;
        }

        .signal-detail-modal .close-button {
          background: none;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          color: #999;
          padding: 0;
          width: 2rem;
          height: 2rem;
        }

        .signal-detail-modal .close-button:hover {
          color: #333;
        }

        .signal-detail-modal .modal-body {
          padding: 1.5rem;
          overflow-y: auto;
          flex: 1;
        }

        .signal-detail-modal .modal-footer {
          padding: 1rem 1.5rem;
          border-top: 1px solid #e0e0e0;
          display: flex;
          gap: 1rem;
          justify-content: flex-end;
        }

        .loading,
        .error-message {
          padding: 3rem;
          text-align: center;
          color: #999;
        }

        .error-message {
          color: #c62828;
        }

        .status-banner {
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-weight: 600;
        }

        .status-banner.status-open {
          background: #fff3cd;
          color: #856404;
        }

        .status-banner.status-closed {
          background: #d1ecf1;
          color: #0c5460;
        }

        .status-banner.status-cancelled {
          background: #f8d7da;
          color: #721c24;
        }

        .info-section {
          margin-bottom: 2rem;
        }

        .info-section h3 {
          margin: 0 0 1rem 0;
          font-size: 1.2rem;
          color: #333;
        }

        .info-section h4 {
          margin: 1rem 0 0.5rem 0;
          font-size: 1rem;
          color: #666;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .edit-actions {
          display: flex;
          gap: 0.5rem;
        }

        .info-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .info-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .info-item label {
          font-size: 0.85rem;
          color: #666;
          font-weight: 500;
        }

        .info-item span {
          font-size: 0.95rem;
        }

        .mono {
          font-family: monospace;
          font-size: 0.85rem;
          color: #666;
        }

        .highlight {
          font-weight: 600;
          color: #2196f3;
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

        .strategy-description {
          margin: 0 0 1rem 0;
          color: #666;
        }

        .expression-display {
          background: #f5f5f5;
          padding: 1rem;
          border-radius: 4px;
          margin-bottom: 0.5rem;
        }

        .expression-display label {
          display: block;
          font-size: 0.85rem;
          color: #666;
          margin-bottom: 0.5rem;
          font-weight: 500;
        }

        .expression-display code {
          font-family: monospace;
          font-size: 0.9rem;
          color: #333;
        }

        .values-grid {
          margin-top: 1rem;
          padding: 1rem;
          background: #fafafa;
          border-radius: 4px;
        }

        .value-item {
          display: flex;
          justify-content: space-between;
          padding: 0.5rem 0;
          border-bottom: 1px solid #e0e0e0;
        }

        .value-item:last-child {
          border-bottom: none;
        }

        .value-item label {
          font-weight: 500;
          color: #666;
        }

        .no-data {
          color: #999;
          font-style: italic;
          padding: 1rem;
          text-align: center;
          background: #f5f5f5;
          border-radius: 4px;
        }

        .exit-criteria-editor {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .exit-criterion-edit {
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          padding: 1rem;
        }

        .criterion-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }

        .criterion-header label {
          font-weight: 500;
          color: #666;
        }

        .exit-criteria-display {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .timeline {
          position: relative;
          padding-left: 2rem;
        }

        .timeline::before {
          content: '';
          position: absolute;
          left: 0.5rem;
          top: 0;
          bottom: 0;
          width: 2px;
          background: #e0e0e0;
        }

        .timeline-item {
          position: relative;
          margin-bottom: 1.5rem;
        }

        .timeline-marker {
          position: absolute;
          left: -1.6rem;
          width: 1rem;
          height: 1rem;
          border-radius: 50%;
          border: 2px solid white;
          box-shadow: 0 0 0 2px currentColor;
        }

        .timeline-marker.created {
          color: #4caf50;
        }

        .timeline-marker.closed {
          color: #2196f3;
        }

        .timeline-content {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .timeline-content strong {
          font-size: 0.95rem;
        }

        .timeline-content span {
          font-size: 0.85rem;
          color: #666;
        }

        .timeline-content .reason {
          color: #999;
          font-style: italic;
        }

        .button-primary {
          background: #2196f3;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .button-primary:hover:not(:disabled) {
          background: #1976d2;
        }

        .button-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .button-primary.small {
          padding: 0.25rem 0.75rem;
          font-size: 0.85rem;
        }

        .button-secondary {
          background: white;
          border: 1px solid #ccc;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9rem;
        }

        .button-secondary:hover {
          background: #f5f5f5;
        }

        .button-secondary.small {
          padding: 0.25rem 0.75rem;
          font-size: 0.85rem;
        }

        .button-link {
          background: none;
          border: none;
          color: #2196f3;
          cursor: pointer;
          text-decoration: underline;
          font-size: 0.85rem;
          padding: 0;
        }

        .button-link:hover {
          color: #1976d2;
        }
      `}</style>
    </>
  );
};
