import React, { useState, useEffect } from 'react';

interface SymbolList {
  id: number;
  name: string;
  dataset_name: string;
  description: string;
  symbols: string[];
  symbol_count: number;
  created_at: number;
  updated_at: number;
  metadata?: any;
}

interface ValidationResult {
  success: boolean;
  valid_symbols: string[];
  invalid_symbols: string[];
  valid_count: number;
  invalid_count: number;
  suggestions: { [key: string]: string[] };
}

interface SymbolListManagerProps {
  selectedDataset: string | null;
  onSymbolListSelected?: (symbolList: SymbolList | null) => void;
}

const SymbolListManager: React.FC<SymbolListManagerProps> = ({ 
  selectedDataset,
  onSymbolListSelected 
}) => {
  const [symbolLists, setSymbolLists] = useState<SymbolList[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Create/Edit modal state
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [editingList, setEditingList] = useState<SymbolList | null>(null);
  
  // Form state
  const [listName, setListName] = useState('');
  const [listDescription, setListDescription] = useState('');
  const [symbolInput, setSymbolInput] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [inputMethod, setInputMethod] = useState<'manual' | 'csv'>('manual');
  
  // Validation state
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [showValidation, setShowValidation] = useState(false);
  const [validating, setValidating] = useState(false);
  
  // Delete confirmation
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [listToDelete, setListToDelete] = useState<SymbolList | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Fetch symbol lists when dataset changes
  useEffect(() => {
    if (selectedDataset) {
      fetchSymbolLists();
    } else {
      setSymbolLists([]);
    }
  }, [selectedDataset]);

  const fetchSymbolLists = async () => {
    if (!window.electronAPI || !selectedDataset) return;

    setLoading(true);
    setError('');

    try {
      const result = await window.electronAPI.invoke('get-symbol-lists', {
        dataset_name: selectedDataset
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setSymbolLists(result.symbol_lists || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch symbol lists');
      console.error('Error fetching symbol lists:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNew = () => {
    setModalMode('create');
    setEditingList(null);
    setListName('');
    setListDescription('');
    setSymbolInput('');
    setCsvFile(null);
    setInputMethod('manual');
    setValidationResult(null);
    setShowValidation(false);
    setShowModal(true);
  };

  const handleEdit = (list: SymbolList) => {
    setModalMode('edit');
    setEditingList(list);
    setListName(list.name);
    setListDescription(list.description);
    setSymbolInput(list.symbols.join('\n'));
    setInputMethod('manual');
    setValidationResult(null);
    setShowValidation(false);
    setShowModal(true);
  };

  const parseSymbolsFromInput = (input: string): string[] => {
    // Handle both line-separated and comma-separated
    const symbols = input
      .split(/[\n,]/)
      .map(s => s.trim().toUpperCase())
      .filter(s => s.length > 0);
    
    // Remove duplicates
    return [...new Set(symbols)];
  };

  const handleValidate = async () => {
    if (!window.electronAPI || !selectedDataset) return;

    const symbols = inputMethod === 'manual' 
      ? parseSymbolsFromInput(symbolInput)
      : [];

    if (symbols.length === 0) {
      setError('Please enter at least one symbol');
      return;
    }

    setValidating(true);
    setError('');

    try {
      const result = await window.electronAPI.invoke('validate-symbols', {
        dataset_name: selectedDataset,
        symbols
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setValidationResult(result);
      setShowValidation(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
      console.error('Error validating symbols:', err);
    } finally {
      setValidating(false);
    }
  };

  const handleSave = async () => {
    if (!window.electronAPI || !selectedDataset) return;

    if (!listName.trim()) {
      setError('Please enter a list name');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let result;

      if (inputMethod === 'csv' && csvFile) {
        // Read CSV file
        const csvContent = await csvFile.text();
        
        result = await window.electronAPI.invoke('import-symbol-list-csv', {
          name: listName,
          dataset_name: selectedDataset,
          csv_content: csvContent,
          description: listDescription
        });
      } else {
        // Manual input
        const symbols = parseSymbolsFromInput(symbolInput);

        if (symbols.length === 0) {
          setError('Please enter at least one symbol');
          setLoading(false);
          return;
        }

        if (modalMode === 'create') {
          result = await window.electronAPI.invoke('create-symbol-list', {
            name: listName,
            dataset_name: selectedDataset,
            symbols,
            description: listDescription
          });
        } else {
          result = await window.electronAPI.invoke('update-symbol-list', {
            name: listName,
            dataset_name: selectedDataset,
            symbols,
            description: listDescription
          });
        }
      }

      if (result.error) {
        throw new Error(result.error);
      }

      setSuccess(modalMode === 'create' 
        ? `Symbol list "${listName}" created successfully!` 
        : `Symbol list "${listName}" updated successfully!`
      );
      
      setTimeout(() => setSuccess(''), 4000);

      setShowModal(false);
      fetchSymbolLists();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save symbol list');
      console.error('Error saving symbol list:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.electronAPI || !listToDelete) return;

    setDeleting(true);

    try {
      const result = await window.electronAPI.invoke('delete-symbol-list', {
        name: listToDelete.name,
        dataset_name: listToDelete.dataset_name
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setSuccess(`Symbol list "${listToDelete.name}" deleted successfully!`);
      setTimeout(() => setSuccess(''), 4000);

      setDeleteConfirmOpen(false);
      setListToDelete(null);
      fetchSymbolLists();
      
      if (onSymbolListSelected) {
        onSymbolListSelected(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete symbol list');
      console.error('Error deleting symbol list:', err);
    } finally {
      setDeleting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setCsvFile(file);
    }
  };

  const excludeInvalidSymbols = () => {
    if (!validationResult) return;
    
    setSymbolInput(validationResult.valid_symbols.join('\n'));
    setValidationResult(null);
    setShowValidation(false);
  };

  if (!selectedDataset) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
        <p>Please select a dataset first to manage symbol lists.</p>
      </div>
    );
  }

  return (
    <div className="symbol-list-manager" style={{ padding: '20px' }}>
      <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: '0 0 5px 0' }}>Symbol Lists</h3>
          <p style={{ margin: 0, color: '#666', fontSize: '14px' }}>
            Dataset: <strong>{selectedDataset}</strong>
          </p>
        </div>
        <button
          className="btn"
          onClick={handleCreateNew}
          disabled={loading}
        >
          + Create Symbol List
        </button>
      </div>

      {error && (
        <div className="error-message" style={{ padding: '10px', backgroundColor: '#ffebee', color: '#d32f2f', borderRadius: '4px', marginBottom: '15px' }}>
          {error}
        </div>
      )}

      {success && (
        <div className="success-message" style={{ padding: '12px', backgroundColor: '#e8f5e9', color: '#2e7d32', borderRadius: '4px', marginBottom: '15px', border: '1px solid #c8e6c9' }}>
          {success}
        </div>
      )}

      {loading && !showModal ? (
        <div style={{ padding: '20px', textAlign: 'center' }}>Loading symbol lists...</div>
      ) : symbolLists.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', backgroundColor: '#f9f9f9', borderRadius: '8px', border: '1px dashed #ddd' }}>
          <p style={{ fontSize: '16px', color: '#666', marginBottom: '10px' }}>No symbol lists created yet</p>
          <p style={{ fontSize: '14px', color: '#999' }}>Click "Create Symbol List" to get started</p>
        </div>
      ) : (
        <div className="symbol-lists-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '15px' }}>
          {symbolLists.map((list) => (
            <div
              key={list.id}
              className="symbol-list-card"
              style={{
                padding: '15px',
                border: '1px solid #ddd',
                borderRadius: '8px',
                backgroundColor: '#fff',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
                e.currentTarget.style.borderColor = '#2196F3';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.borderColor = '#ddd';
              }}
            >
              <h4 style={{ margin: '0 0 10px 0', color: '#1976d2' }}>{list.name}</h4>
              {list.description && (
                <p style={{ margin: '5px 0', fontSize: '14px', color: '#666' }}>{list.description}</p>
              )}
              <div style={{ margin: '10px 0', fontSize: '13px', backgroundColor: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
                <p style={{ margin: '3px 0' }}>📊 Symbols: {list.symbol_count}</p>
                <p style={{ margin: '3px 0' }}>🕐 Updated: {new Date(list.updated_at * 1000).toLocaleDateString()}</p>
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                <button
                  className="btn btn-secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSymbolListSelected) {
                      onSymbolListSelected(list);
                    }
                  }}
                  style={{ flex: 1 }}
                >
                  Use
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEdit(list);
                  }}
                  style={{ flex: 1 }}
                >
                  Edit
                </button>
                <button
                  className="btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setListToDelete(list);
                    setDeleteConfirmOpen(true);
                  }}
                  style={{ 
                    flex: 1,
                    backgroundColor: '#f44336',
                    color: 'white'
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <>
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0,0,0,0.5)',
              zIndex: 999
            }} 
            onClick={() => setShowModal(false)}
          />
          
          <div style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            zIndex: 1000,
            minWidth: '600px',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <h3 style={{ marginTop: 0 }}>
              {modalMode === 'create' ? 'Create Symbol List' : 'Edit Symbol List'}
            </h3>

            <div className="form-group" style={{ marginBottom: '20px' }}>
              <label htmlFor="list-name">List Name: <span style={{ color: 'red' }}>*</span></label>
              <input
                type="text"
                id="list-name"
                value={listName}
                onChange={(e) => setListName(e.target.value)}
                placeholder="e.g., Top Tech Stocks, Energy Sector"
                disabled={modalMode === 'edit'}
                style={{ width: '100%', padding: '8px', fontSize: '14px' }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: '20px' }}>
              <label htmlFor="list-description">Description:</label>
              <textarea
                id="list-description"
                value={listDescription}
                onChange={(e) => setListDescription(e.target.value)}
                placeholder="Optional description of this symbol list"
                style={{ width: '100%', padding: '8px', fontSize: '14px', minHeight: '60px', resize: 'vertical' }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: '20px' }}>
              <label>Input Method:</label>
              <div style={{ display: 'flex', gap: '15px', marginTop: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="input-method"
                    value="manual"
                    checked={inputMethod === 'manual'}
                    onChange={(e) => setInputMethod(e.target.value as 'manual' | 'csv')}
                    style={{ marginRight: '8px' }}
                  />
                  Manual Entry
                </label>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="input-method"
                    value="csv"
                    checked={inputMethod === 'csv'}
                    onChange={(e) => setInputMethod(e.target.value as 'manual' | 'csv')}
                    style={{ marginRight: '8px' }}
                  />
                  Upload CSV
                </label>
              </div>
            </div>

            {inputMethod === 'manual' ? (
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label htmlFor="symbol-input">Symbols: <span style={{ color: 'red' }}>*</span></label>
                <textarea
                  id="symbol-input"
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value)}
                  placeholder="Enter symbols (one per line or comma-separated)&#10;Example:&#10;AAPL&#10;GOOGL&#10;MSFT"
                  style={{ width: '100%', padding: '8px', fontSize: '14px', minHeight: '150px', fontFamily: 'monospace' }}
                />
                <p style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                  Enter symbols one per line or separated by commas
                </p>
                <button
                  className="btn btn-secondary"
                  onClick={handleValidate}
                  disabled={validating || !symbolInput.trim()}
                  style={{ marginTop: '10px' }}
                >
                  {validating ? 'Validating...' : 'Validate Symbols'}
                </button>
              </div>
            ) : (
              <div className="form-group" style={{ marginBottom: '20px' }}>
                <label htmlFor="csv-file">CSV File: <span style={{ color: 'red' }}>*</span></label>
                <input
                  type="file"
                  id="csv-file"
                  accept=".csv,.txt"
                  onChange={handleFileChange}
                  style={{ width: '100%', padding: '8px', fontSize: '14px' }}
                />
                <p style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                  Upload a CSV file with symbols (one per line or comma-separated)
                </p>
              </div>
            )}

            {showValidation && validationResult && (
              <div style={{ 
                marginBottom: '20px', 
                padding: '15px', 
                backgroundColor: validationResult.invalid_count > 0 ? '#fff3cd' : '#d4edda',
                border: `1px solid ${validationResult.invalid_count > 0 ? '#ffc107' : '#28a745'}`,
                borderRadius: '4px'
              }}>
                <h4 style={{ marginTop: 0 }}>Validation Results</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                  <div>
                    <strong>✅ Valid Symbols:</strong> {validationResult.valid_count}
                  </div>
                  <div>
                    <strong>❌ Invalid Symbols:</strong> {validationResult.invalid_count}
                  </div>
                </div>

                {validationResult.invalid_count > 0 && (
                  <>
                    <div style={{ marginTop: '15px' }}>
                      <strong>Invalid Symbols:</strong>
                      <div style={{ marginTop: '8px', padding: '10px', backgroundColor: '#fff', borderRadius: '4px', maxHeight: '150px', overflowY: 'auto' }}>
                        {validationResult.invalid_symbols.map((symbol, idx) => (
                          <div key={idx} style={{ marginBottom: '8px' }}>
                            <span style={{ color: '#d32f2f', fontWeight: 'bold' }}>{symbol}</span>
                            {validationResult.suggestions[symbol] && validationResult.suggestions[symbol].length > 0 && (
                              <span style={{ marginLeft: '10px', fontSize: '13px', color: '#666' }}>
                                Did you mean: {validationResult.suggestions[symbol].join(', ')}?
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                    <button
                      className="btn btn-secondary"
                      onClick={excludeInvalidSymbols}
                      style={{ marginTop: '10px' }}
                    >
                      Exclude Invalid Symbols
                    </button>
                  </>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowModal(false)}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                className="btn"
                onClick={handleSave}
                disabled={loading || !listName.trim() || (inputMethod === 'manual' ? !symbolInput.trim() : !csvFile)}
              >
                {loading ? 'Saving...' : modalMode === 'create' ? 'Create' : 'Save Changes'}
              </button>
            </div>
          </div>
        </>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmOpen && listToDelete && (
        <>
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0,0,0,0.5)',
              zIndex: 999
            }} 
            onClick={() => setDeleteConfirmOpen(false)}
          />
          
          <div style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            zIndex: 1000,
            minWidth: '400px',
            maxWidth: '500px'
          }}>
            <h3 style={{ marginTop: 0, color: '#d32f2f' }}>⚠️ Confirm Deletion</h3>
            <p style={{ fontSize: '16px', lineHeight: '1.5' }}>
              Are you sure you want to delete the symbol list <strong>"{listToDelete.name}"</strong>?
            </p>
            <p style={{ fontSize: '14px', color: '#666' }}>
              This action cannot be undone. The list contains {listToDelete.symbol_count} symbols.
            </p>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setDeleteConfirmOpen(false);
                  setListToDelete(null);
                }}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="btn"
                onClick={handleDelete}
                disabled={deleting}
                style={{ backgroundColor: '#f44336', color: 'white' }}
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default SymbolListManager;
