import React, { useState, useEffect } from 'react';
import { ExpressionBuilder } from './ExpressionBuilder';
import {
  CreateSignalStrategyRequest,
  CreateSignalRequest,
  SignalStrategy
} from '../../types/signals';

interface ScannerResult {
  symbol: string;
  timestamp: string;
  [key: string]: any; // Indicator values
}

interface SaveSignalModalProps {
  isOpen: boolean;
  onClose: () => void;
  scannerResult: ScannerResult;
  scannerSpec: any; // Scanner configuration
  datasetName: string;
  onSuccess?: () => void;
}

export const SaveSignalModal: React.FC<SaveSignalModalProps> = ({
  isOpen,
  onClose,
  scannerResult,
  scannerSpec,
  datasetName,
  onSuccess
}) => {
  const [step, setStep] = useState<'strategy' | 'signal'>('strategy');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Strategy form fields
  const [strategyName, setStrategyName] = useState('');
  const [strategyDescription, setStrategyDescription] = useState('');
  const [defaultDirection, setDefaultDirection] = useState<'long' | 'short' | 'auto'>('auto');
  const [entryExpression, setEntryExpression] = useState('');
  const [includeExit, setIncludeExit] = useState(false);
  const [exitExpressions, setExitExpressions] = useState<string[]>(['']);
  const [exitLogic, setExitLogic] = useState<'any' | 'all'>('any');
  const [reversalMode, setReversalMode] = useState<'no-auto-reversal' | 'auto-reversal-to-opposite' | 'auto-reversal-with-confirmation'>('no-auto-reversal');
  
  // Signal direction (may differ from strategy default)
  const [signalDirection, setSignalDirection] = useState<'long' | 'short'>('long');
  
  // Validation states
  const [entryValid, setEntryValid] = useState(false);
  const [exitValid, setExitValid] = useState<boolean[]>([]);
  
  // Load existing strategies for selection
  const [existingStrategies, setExistingStrategies] = useState<SignalStrategy[]>([]);
  const [useExistingStrategy, setUseExistingStrategy] = useState(false);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadExistingStrategies();
      // Pre-fill entry expression from scanner spec if available
      if (scannerSpec?.conditions) {
        const firstCondition = scannerSpec.conditions[0];
        if (firstCondition) {
          setEntryExpression(firstCondition);
        }
      }
    }
  }, [isOpen, scannerSpec]);

  const loadExistingStrategies = async () => {
    try {
      const result = await window.electron.invoke('get_signal_strategies', {});
      if (result.success && result.strategies) {
        setExistingStrategies(result.strategies);
      }
    } catch (err) {
      console.error('Failed to load strategies:', err);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setError(null);

    try {
      let strategyId: string;

      if (useExistingStrategy && selectedStrategyId) {
        strategyId = selectedStrategyId;
      } else {
        // Create new strategy
        if (!strategyName.trim()) {
          setError('Strategy name is required');
          setLoading(false);
          return;
        }

        if (!entryExpression.trim()) {
          setError('Entry expression is required');
          setLoading(false);
          return;
        }

        if (!entryValid) {
          setError('Entry expression is invalid');
          setLoading(false);
          return;
        }

        if (includeExit) {
          const validExits = exitExpressions.filter(e => e.trim());
          if (validExits.length === 0) {
            setError('At least one exit expression is required when including exit criteria');
            setLoading(false);
            return;
          }
        }

        const strategyData: CreateSignalStrategyRequest = {
          name: strategyName,
          description: strategyDescription,
          conditions: {
            entry: [entryExpression],
            exit: includeExit ? exitExpressions.filter(e => e.trim()) : undefined
          },
          default_direction: defaultDirection,
          metadata: {
            reversal_mode: reversalMode,
            exit_logic: exitLogic
          }
        };

        const strategyResult = await window.electron.invoke('create_signal_strategy', strategyData);
        
        if (!strategyResult.success) {
          setError(strategyResult.error || 'Failed to create strategy');
          setLoading(false);
          return;
        }

        strategyId = strategyResult.strategy_id!;
      }

      // Extract indicator values from scanner result
      const entryValues: Record<string, number> = {};
      Object.keys(scannerResult).forEach(key => {
        if (key !== 'symbol' && key !== 'timestamp' && typeof scannerResult[key] === 'number') {
          entryValues[key] = scannerResult[key];
        }
      });

      // Create signal
      const signalData: CreateSignalRequest = {
        strategy_id: strategyId,
        dataset_name: datasetName,
        symbol: scannerResult.symbol,
        timestamp: scannerResult.timestamp,
        direction: signalDirection,
        entry_values: entryValues,
        exit_criteria: includeExit ? exitExpressions.filter(e => e.trim()) : undefined,
        metadata: {
          source: 'scanner',
          scanner_spec: scannerSpec
        }
      };

      const signalResult = await window.electron.invoke('create_signal', signalData);

      if (!signalResult.success) {
        setError(signalResult.error || 'Failed to create signal');
        setLoading(false);
        return;
      }

      // Success!
      if (onSuccess) onSuccess();
      handleClose();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setStrategyName('');
    setStrategyDescription('');
    setDefaultDirection('auto');
    setEntryExpression('');
    setIncludeExit(false);
    setExitExpressions(['']);
    setReversalMode('no-auto-reversal');
    setError(null);
    setUseExistingStrategy(false);
    setSelectedStrategyId(null);
    onClose();
  };

  const addExitExpression = () => {
    setExitExpressions([...exitExpressions, '']);
  };

  const removeExitExpression = (index: number) => {
    setExitExpressions(exitExpressions.filter((_, i) => i !== index));
  };

  const updateExitExpression = (index: number, value: string) => {
    const updated = [...exitExpressions];
    updated[index] = value;
    setExitExpressions(updated);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content save-signal-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Save Signal from Scanner Result</h2>
          <button className="close-button" onClick={handleClose}>×</button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="error-banner">
              <strong>Error:</strong> {error}
            </div>
          )}

          <div className="signal-info">
            <h3>Signal Details</h3>
            <div className="info-grid">
              <div><strong>Symbol:</strong> {scannerResult.symbol}</div>
              <div><strong>Dataset:</strong> {datasetName}</div>
              <div><strong>Timestamp:</strong> {new Date(scannerResult.timestamp).toLocaleString()}</div>
            </div>
          </div>

          <div className="form-section">
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={useExistingStrategy}
                  onChange={e => setUseExistingStrategy(e.target.checked)}
                />
                Use existing strategy
              </label>
            </div>

            {useExistingStrategy ? (
              <div className="form-group">
                <label>Select Strategy</label>
                <select
                  value={selectedStrategyId || ''}
                  onChange={e => setSelectedStrategyId(e.target.value)}
                  className="form-control"
                >
                  <option value="">-- Choose a strategy --</option>
                  {existingStrategies.map(strategy => (
                    <option key={strategy.id} value={strategy.id}>
                      {strategy.name} ({strategy.default_direction})
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label>Strategy Name *</label>
                  <input
                    type="text"
                    value={strategyName}
                    onChange={e => setStrategyName(e.target.value)}
                    placeholder="e.g., RSI Overbought"
                    className="form-control"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    value={strategyDescription}
                    onChange={e => setStrategyDescription(e.target.value)}
                    placeholder="Optional description of the strategy..."
                    className="form-control"
                    rows={2}
                  />
                </div>

                <div className="form-group">
                  <label>Default Direction *</label>
                  <div className="radio-group">
                    <label>
                      <input
                        type="radio"
                        value="long"
                        checked={defaultDirection === 'long'}
                        onChange={e => setDefaultDirection(e.target.value as 'long')}
                      />
                      Long
                    </label>
                    <label>
                      <input
                        type="radio"
                        value="short"
                        checked={defaultDirection === 'short'}
                        onChange={e => setDefaultDirection(e.target.value as 'short')}
                      />
                      Short
                    </label>
                    <label>
                      <input
                        type="radio"
                        value="auto"
                        checked={defaultDirection === 'auto'}
                        onChange={e => setDefaultDirection(e.target.value as 'auto')}
                      />
                      Auto-detect
                    </label>
                  </div>
                </div>

                <div className="form-group">
                  <ExpressionBuilder
                    label="Entry Expression *"
                    value={entryExpression}
                    onChange={setEntryExpression}
                    datasetName={datasetName}
                    symbol={scannerResult.symbol}
                    onValidate={setEntryValid}
                    placeholder="e.g., RSI(14) > 70"
                  />
                </div>

                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={includeExit}
                      onChange={e => setIncludeExit(e.target.checked)}
                    />
                    Include Exit Criteria
                  </label>
                </div>

                {includeExit && (
                  <>
                    <div className="exit-expressions">
                      {exitExpressions.map((expr, index) => (
                        <div key={index} className="exit-expression-row">
                          <ExpressionBuilder
                            label={`Exit Expression ${index + 1}`}
                            value={expr}
                            onChange={value => updateExitExpression(index, value)}
                            datasetName={datasetName}
                            symbol={scannerResult.symbol}
                            onValidate={valid => {
                              const updated = [...exitValid];
                              updated[index] = valid;
                              setExitValid(updated);
                            }}
                            placeholder="e.g., RSI(14) < 50"
                          />
                          {exitExpressions.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeExitExpression(index)}
                              className="remove-button"
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={addExitExpression}
                        className="add-button"
                      >
                        + Add Exit Expression
                      </button>
                    </div>

                    {exitExpressions.length > 1 && (
                      <div className="form-group">
                        <label>Exit Logic</label>
                        <div className="radio-group">
                          <label>
                            <input
                              type="radio"
                              value="any"
                              checked={exitLogic === 'any'}
                              onChange={() => setExitLogic('any')}
                            />
                            Any (OR) - Exit when any condition is met
                          </label>
                          <label>
                            <input
                              type="radio"
                              value="all"
                              checked={exitLogic === 'all'}
                              onChange={() => setExitLogic('all')}
                            />
                            All (AND) - Exit when all conditions are met
                          </label>
                        </div>
                      </div>
                    )}

                    <div className="form-group">
                      <label>Reversal Behavior</label>
                      <select
                        value={reversalMode}
                        onChange={e => setReversalMode(e.target.value as any)}
                        className="form-control"
                      >
                        <option value="no-auto-reversal">No Auto-Reversal</option>
                        <option value="auto-reversal-to-opposite">Auto-Reversal to Opposite</option>
                        <option value="auto-reversal-with-confirmation">Auto-Reversal with Confirmation</option>
                      </select>
                      <small className="help-text">
                        {reversalMode === 'no-auto-reversal' && 'Signal closes when exit condition is met'}
                        {reversalMode === 'auto-reversal-to-opposite' && 'Automatically creates opposite signal on exit'}
                        {reversalMode === 'auto-reversal-with-confirmation' && 'Creates opposite signal only if entry conditions are met'}
                      </small>
                    </div>
                  </>
                )}
              </>
            )}
          </div>

          <div className="form-section">
            <h3>This Signal</h3>
            <div className="form-group">
              <label>Direction for This Signal *</label>
              <div className="radio-group">
                <label>
                  <input
                    type="radio"
                    value="long"
                    checked={signalDirection === 'long'}
                    onChange={() => setSignalDirection('long')}
                  />
                  Long
                </label>
                <label>
                  <input
                    type="radio"
                    value="short"
                    checked={signalDirection === 'short'}
                    onChange={() => setSignalDirection('short')}
                  />
                  Short
                </label>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={handleClose} className="button-secondary" disabled={loading}>
            Cancel
          </button>
          <button onClick={handleSave} className="button-primary" disabled={loading}>
            {loading ? 'Saving...' : 'Save Signal'}
          </button>
        </div>

        <style>{`
          .modal-overlay {
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
          }

          .modal-content {
            background: white;
            border-radius: 8px;
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
          }

          .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem;
            border-bottom: 1px solid #e0e0e0;
          }

          .modal-header h2 {
            margin: 0;
            font-size: 1.25rem;
          }

          .close-button {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #666;
            padding: 0;
            width: 30px;
            height: 30px;
          }

          .close-button:hover {
            color: #000;
          }

          .modal-body {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem;
          }

          .modal-footer {
            display: flex;
            justify-content: flex-end;
            gap: 1rem;
            padding: 1.5rem;
            border-top: 1px solid #e0e0e0;
          }

          .error-banner {
            background: #ffebee;
            border: 1px solid #ef5350;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
            color: #c62828;
          }

          .signal-info {
            background: #f5f5f5;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1.5rem;
          }

          .signal-info h3 {
            margin: 0 0 0.75rem 0;
            font-size: 1rem;
          }

          .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.5rem;
            font-size: 0.9rem;
          }

          .form-section {
            margin-bottom: 1.5rem;
          }

          .form-section h3 {
            margin: 0 0 1rem 0;
            font-size: 1rem;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 0.5rem;
          }

          .form-group {
            margin-bottom: 1rem;
          }

          .form-group label {
            display: block;
            font-weight: 500;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
          }

          .form-control {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 0.9rem;
          }

          .form-control:focus {
            outline: none;
            border-color: #2196f3;
          }

          .radio-group {
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
          }

          .radio-group label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: normal;
            cursor: pointer;
          }

          .help-text {
            display: block;
            margin-top: 0.25rem;
            font-size: 0.85rem;
            color: #666;
          }

          .exit-expressions {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 1rem;
            background: #fafafa;
          }

          .exit-expression-row {
            margin-bottom: 1rem;
            position: relative;
          }

          .remove-button {
            position: absolute;
            top: 0;
            right: 0;
            background: #f44336;
            color: white;
            border: none;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.8rem;
          }

          .remove-button:hover {
            background: #d32f2f;
          }

          .add-button {
            background: #4caf50;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
          }

          .add-button:hover {
            background: #45a049;
          }

          .button-primary {
            background: #2196f3;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
          }

          .button-primary:hover:not(:disabled) {
            background: #1976d2;
          }

          .button-primary:disabled {
            background: #ccc;
            cursor: not-allowed;
          }

          .button-secondary {
            background: white;
            color: #333;
            border: 1px solid #ccc;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
          }

          .button-secondary:hover:not(:disabled) {
            background: #f5f5f5;
          }

          .button-secondary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }
        `}</style>
      </div>
    </div>
  );
};
