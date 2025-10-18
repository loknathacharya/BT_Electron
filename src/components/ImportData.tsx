import React, { useState } from 'react';

const ImportData: React.FC = () => {
  const [filePath, setFilePath] = useState<string>('');
  const [preview, setPreview] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [rowsTotal, setRowsTotal] = useState<number>(0);
  const [importing, setImporting] = useState(false);
  const [importSuccess, setImportSuccess] = useState<string>('');
  const [importProgress, setImportProgress] = useState(0);
  const [importSummary, setImportSummary] = useState<any>(null);
  const [importErrors, setImportErrors] = useState<string[]>([]);
  const [columnMapping, setColumnMapping] = useState<{[key: string]: string}>({});
  const [mappingErrors, setMappingErrors] = useState<string[]>([]);
  const [autoMapping, setAutoMapping] = useState<{[key: string]: string}>({});
  const [confidenceScores, setConfidenceScores] = useState<{[key: string]: number}>({});
  const [showAutoMappingDialog, setShowAutoMappingDialog] = useState(false);
  const [autoMappingApplied, setAutoMappingApplied] = useState(false);

  const handleSelectFile = async () => {
    if (!window.electronAPI) {
      setError('Electron API not available. Running in browser?');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await window.electronAPI.invoke('open-file-dialog');
      if (result.canceled) {
        return;
      }
      if (result.error) {
        throw new Error(result.error);
      }

      const selectedPath = result.filePath;
      setFilePath(selectedPath);

      // Preview the file
       console.log('Previewing file:', selectedPath);
       const previewResult = await window.electronAPI.invoke('preview-file', { filePath: selectedPath });
       console.log('Preview result:', previewResult);

       if (previewResult.error) {
         console.error('Preview error:', previewResult.error);
         throw new Error(previewResult.error);
       }

       console.log('Preview data received:', {
         previewLength: previewResult.preview?.length || 0,
         columnsLength: previewResult.columns?.length || 0,
         rowsTotal: previewResult.rows_total || 0,
         autoMapping: previewResult.auto_mapping,
         confidenceScores: previewResult.confidence_scores
       });

       setPreview(previewResult.preview || []);
       setColumns(previewResult.columns || []);
       setRowsTotal(previewResult.rows_total || 0);
       setError('');

       // Handle auto-mapping if available
       if (previewResult.auto_mapping && Object.keys(previewResult.auto_mapping).length > 0) {
         setAutoMapping(previewResult.auto_mapping);
         setConfidenceScores(previewResult.confidence_scores || {});
         setShowAutoMappingDialog(true);
         setAutoMappingApplied(false);
       } else {
         setAutoMapping({});
         setConfidenceScores({});
         setShowAutoMappingDialog(false);
       }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select or preview file');
      console.error('File selection error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleImportData = async () => {
    if (!window.electronAPI || !filePath) {
      setError('No file selected or Electron API not available');
      return;
    }

    setImporting(true);
    setError('');
    setImportSuccess('');
    setImportProgress(0);
    setImportSummary(null);
    setImportErrors([]);

    try {
      // Get the symbol from the input field
      const symbolInput = document.getElementById('symbol') as HTMLInputElement;
      const symbol = symbolInput?.value?.trim() || 'DEFAULT';

      console.log('IMPORT-DEBUG: Starting import process:', {
        filePath,
        symbol,
        columnMapping,
        rowsTotal
      });

      // Set up progress listener with enhanced logging
      const progressHandler = (progressData: any) => {
        console.log('IMPORT-DEBUG: Progress update received:', progressData);
        if (progressData.progress !== undefined) {
          setImportProgress(progressData.progress);
        }
        if (progressData.errors) {
          console.log('IMPORT-DEBUG: Import errors:', progressData.errors);
          setImportErrors(prev => [...prev, ...progressData.errors]);
        }
        if (progressData.currentRow !== undefined && progressData.totalRows !== undefined) {
          console.log(`IMPORT-DEBUG: Processing row ${progressData.currentRow}/${progressData.totalRows}`);
        }
        if (progressData.type === 'import-summary') {
          console.log('IMPORT-DEBUG: Final summary received:', progressData);
        }
      };

      // Listen for progress events
      const removeListener = window.electronAPI.on('import-progress', progressHandler);

      const startTime = Date.now();
      console.log('IMPORT-DEBUG: Sending import request to Electron main process...');

      const result = await window.electronAPI.invoke('import-data', {
        filePath,
        symbol,
        columnMapping: columnMapping
      });

      const endTime = Date.now();
      console.log(`IMPORT-DEBUG: Import request completed in ${endTime - startTime}ms`);

      // Remove progress listener
      removeListener();

      if (result.error) {
        console.error('IMPORT-DEBUG: Import result error:', result);
        throw new Error(result.error);
      }

      console.log('IMPORT-DEBUG: Import successful:', result);
      setImportSummary(result);
      setImportSuccess(`Successfully imported ${result.rowsImported || 0} rows of ${symbol} data`);
    } catch (err) {
      console.error('IMPORT-DEBUG: Import caught error:', err);
      setError(err instanceof Error ? err.message : 'Failed to import data');
    } finally {
      setImporting(false);
      setImportProgress(0);
    }
  };

  const handleColumnMapping = (fieldName: string, sourceColumn: string) => {
    setColumnMapping(prev => ({
      ...prev,
      [fieldName]: sourceColumn
    }));

    // Validate mapping
    validateColumnMapping(fieldName, sourceColumn);
  };

  const handleAcceptAutoMapping = () => {
    setColumnMapping(autoMapping);
    setAutoMappingApplied(true);
    setShowAutoMappingDialog(false);
    // Validate all auto-mapped fields
    Object.entries(autoMapping).forEach(([fieldName, sourceColumn]) => {
      validateColumnMapping(fieldName, sourceColumn);
    });
  };

  const handleRejectAutoMapping = () => {
    setAutoMapping({});
    setConfidenceScores({});
    setShowAutoMappingDialog(false);
    setAutoMappingApplied(false);
  };

  const handleModifyAutoMapping = (fieldName: string, sourceColumn: string) => {
    setColumnMapping(prev => ({
      ...prev,
      [fieldName]: sourceColumn
    }));
    setAutoMapping(prev => ({
      ...prev,
      [fieldName]: sourceColumn
    }));
    validateColumnMapping(fieldName, sourceColumn);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 90) return '#4CAF50'; // Green
    if (score >= 70) return '#FFC107'; // Yellow
    if (score >= 50) return '#FF9800'; // Orange
    return '#F44336'; // Red
  };

  const getConfidenceText = (score: number) => {
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Fair';
    return 'Poor';
  };

  const validateColumnMapping = (fieldName: string, sourceColumn: string) => {
    const errors: string[] = [];
    console.log('Validating column mapping:', { fieldName, sourceColumn, availableColumns: columns });

    // Check if source column exists in the file
    if (!columns.includes(sourceColumn)) {
      const errorMsg = `Source column '${sourceColumn}' not found in file`;
      console.error('Column validation error:', errorMsg);
      errors.push(errorMsg);
    }

    // Check for duplicate mappings
    const isDuplicate = Object.entries(columnMapping).some(([field, col]) => {
      return field !== fieldName && col === sourceColumn;
    });

    if (isDuplicate) {
      const errorMsg = `Column '${sourceColumn}' is already mapped to another field`;
      console.error('Duplicate mapping error:', errorMsg);
      errors.push(errorMsg);
    }

    // Type validation based on field
    if (preview.length > 0) {
      const sampleValue = preview[0][sourceColumn];
      console.log('Sample value for validation:', { sourceColumn, sampleValue });

      if (sampleValue !== undefined && sampleValue !== null && sampleValue !== '') {
        if (['open', 'high', 'low', 'close'].includes(fieldName)) {
          if (isNaN(Number(sampleValue))) {
            const errorMsg = `Column '${sourceColumn}' contains non-numeric data for ${fieldName} field`;
            console.error('Type validation error:', errorMsg, { sampleValue, fieldName });
            errors.push(errorMsg);
          }
        } else if (fieldName === 'timestamp') {
          if (isNaN(Date.parse(String(sampleValue))) && isNaN(Number(sampleValue))) {
            const errorMsg = `Column '${sourceColumn}' doesn't appear to contain valid date/timestamp data`;
            console.error('Date validation error:', errorMsg, { sampleValue, fieldName });
            errors.push(errorMsg);
          }
        }
      }
    }

    console.log('Validation complete:', { errors: errors.length, fieldName, sourceColumn });
    setMappingErrors(errors);
  };

  const isMappingValid = () => {
    const requiredFields = ['timestamp', 'open', 'high', 'low', 'close'];
    return requiredFields.every(field => columnMapping[field]);
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Import Data</h2>
        <p>
          Import your trading data from CSV, Excel, or Parquet files. The application supports OHLCV data
          with timestamps. Click below to select a file and preview its contents.
        </p>
      </div>

      <div className="import-section">
        <button
          className="btn"
          onClick={handleSelectFile}
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Select Data File'}
        </button>

        {error && (
          <div className="error-message" style={{ color: 'red', marginTop: '10px' }}>
            {error}
          </div>
        )}

        {/* Auto-mapping dialog */}
        {showAutoMappingDialog && (
          <div className="auto-mapping-dialog" style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '8px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            zIndex: 1000,
            minWidth: '500px',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0,0,0,0.5)',
              zIndex: 999
            }} onClick={() => setShowAutoMappingDialog(false)} />
            
            <div style={{ position: 'relative', zIndex: 1001 }}>
              <h3 style={{ marginBottom: '15px', color: '#333' }}>
                🤖 Auto-detected Column Mapping
              </h3>
              <p style={{ marginBottom: '20px', color: '#666' }}>
                The system has automatically detected column mappings based on your file structure.
                Review the suggestions below and accept or modify them as needed.
              </p>

              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ marginBottom: '10px', color: '#333' }}>Detected Mappings:</h4>
                <div style={{ display: 'grid', gap: '10px' }}>
                  {Object.entries(autoMapping).map(([fieldName, sourceColumn]) => {
                    const confidence = confidenceScores[fieldName] || 0;
                    const confidenceColor = getConfidenceColor(confidence);
                    const confidenceText = getConfidenceText(confidence);
                    
                    return (
                      <div key={fieldName} style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '10px',
                        backgroundColor: '#f5f5f5',
                        borderRadius: '4px',
                        borderLeft: `4px solid ${confidenceColor}`
                      }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                            {fieldName.toUpperCase()}
                          </div>
                          <div style={{ fontSize: '14px', color: '#666' }}>
                            → {sourceColumn}
                          </div>
                        </div>
                        <div style={{
                          backgroundColor: confidenceColor,
                          color: 'white',
                          padding: '4px 8px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: 'bold'
                        }}>
                          {confidenceText} ({confidence}%)
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  className="btn btn-secondary"
                  onClick={handleRejectAutoMapping}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#f5f5f5',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Reject All
                </button>
                <button
                  className="btn"
                  onClick={handleAcceptAutoMapping}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Accept All
                </button>
              </div>
            </div>
          </div>
        )}

        {importSuccess && (
          <div className="success-message" style={{ color: 'green', marginTop: '10px' }}>
            {importSuccess}
          </div>
        )}

        {importing && (
          <div className="import-progress" style={{ marginTop: '20px' }}>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${importProgress}%`,
                  height: '20px',
                  backgroundColor: '#4CAF50',
                  transition: 'width 0.3s ease'
                }}
              />
            </div>
            <p style={{ textAlign: 'center', marginTop: '10px' }}>
              Importing... {importProgress}%
            </p>
          </div>
        )}

        {importSummary && (
          <div className="import-summary" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '5px' }}>
            <h3>Import Summary</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <div>
                <strong>Rows Imported:</strong> {importSummary.rowsImported || 0}
              </div>
              <div>
                <strong>Rows Skipped:</strong> {importSummary.rowsSkipped || 0}
              </div>
              <div>
                <strong>Symbol:</strong> {importSummary.symbol || 'N/A'}
              </div>
              <div>
                <strong>Time Elapsed:</strong> {importSummary.timeElapsed ? `${importSummary.timeElapsed}s` : 'N/A'}
              </div>
            </div>
          </div>
        )}

        {importErrors.length > 0 && (
          <div className="import-errors" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#ffebee', borderRadius: '5px' }}>
            <h3>Import Errors ({importErrors.length})</h3>
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {importErrors.map((error, index) => (
                <div key={index} style={{ marginBottom: '5px', color: '#d32f2f' }}>
                  • {error}
                </div>
              ))}
            </div>
          </div>
        )}

        {filePath && !loading && (
          <div className="file-selected" style={{ marginTop: '20px' }}>
            <h3>Selected: {filePath.split(/[\\/]/).pop()}</h3>
            <p>Total rows: {rowsTotal}</p>
          </div>
        )}

        {preview.length > 0 && (
          <div className="preview-section" style={{ marginTop: '20px' }}>
            <h3>Data Preview (First 10 Rows)</h3>
            <div className="preview-table" style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                  <tr>
                    {columns.map(col => (
                      <th key={col} style={{ border: '1px solid #ddd', padding: '8px', backgroundColor: '#f2f2f2' }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.map((row, index) => (
                    <tr key={index}>
                      {columns.map(col => (
                        <td key={col} style={{ border: '1px solid #ddd', padding: '8px' }}>
                          {row[col] ?? ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {filePath && (
          <div className="import-controls">
            <div className="form-group">
              <label htmlFor="symbol">Symbol:</label>
              <input
                type="text"
                id="symbol"
                placeholder="e.g., AAPL, BTC-USD"
                defaultValue=""
              />
            </div>

            {/* Column mapping interface for Sprint 2.2 */}
            <div className="column-mapping">
              <h3>Column Mapping</h3>
              <p>Drag columns from your file to the required fields below. Required fields are highlighted.</p>

              <div className="mapping-container" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '15px' }}>
                {/* Source columns (from CSV) */}
                <div className="source-columns">
                  <h4>Your File Columns:</h4>
                  <div className="column-list" style={{ border: '1px solid #ddd', padding: '10px', minHeight: '200px', backgroundColor: '#f9f9f9' }}>
                    {columns.map(col => (
                      <div
                        key={col}
                        className="draggable-column"
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData('text/plain', col);
                          e.dataTransfer.effectAllowed = 'copy';
                        }}
                        style={{
                          padding: '8px',
                          margin: '4px 0',
                          backgroundColor: '#fff',
                          border: '1px solid #ccc',
                          borderRadius: '4px',
                          cursor: 'grab'
                        }}
                      >
                        {col}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Target fields (required OHLC format) */}
                <div className="target-fields">
                  <h4>Required Fields:</h4>
                  <div className="field-list" style={{ border: '1px solid #ddd', padding: '10px', minHeight: '200px' }}>
                    {[
                      { name: 'timestamp', label: 'Timestamp', required: true },
                      { name: 'open', label: 'Open', required: true },
                      { name: 'high', label: 'High', required: true },
                      { name: 'low', label: 'Low', required: true },
                      { name: 'close', label: 'Close', required: true },
                      { name: 'volume', label: 'Volume', required: false },
                      { name: 'ticker', label: 'Ticker', required: false }
                    ].map(field => {
                      const mappedColumn = columnMapping[field.name];
                      const autoMappedColumn = autoMapping[field.name];
                      const confidence = confidenceScores[field.name] || 0;
                      const isAutoMapped = autoMappedColumn && !autoMappingApplied;
                      const isCurrentlyMapped = mappedColumn && mappedColumn !== autoMappedColumn;

                      return (
                        <div
                          key={field.name}
                          className={`droppable-field ${field.required ? 'required' : 'optional'}`}
                          onDragOver={(e) => {
                            e.preventDefault();
                            e.dataTransfer.dropEffect = 'copy';
                          }}
                          onDrop={(e) => {
                            e.preventDefault();
                            const sourceColumn = e.dataTransfer.getData('text/plain');
                            if (sourceColumn) {
                              handleModifyAutoMapping(field.name, sourceColumn);
                            }
                          }}
                          style={{
                            padding: '8px',
                            margin: '4px 0',
                            border: '1px dashed #999',
                            borderRadius: '4px',
                            backgroundColor: field.required ?
                              (isCurrentlyMapped ? '#fff3e0' : (isAutoMapped ? '#e8f5e8' : '#ffebee')) :
                              (isCurrentlyMapped ? '#f5f5f5' : (isAutoMapped ? '#f1f8e9' : '#f5f5f5')),
                            minHeight: '30px',
                            display: 'flex',
                            alignItems: 'center',
                            position: 'relative',
                            borderLeft: isAutoMapped ? `4px solid ${getConfidenceColor(confidence)}` : 'none'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                            <span style={{ fontWeight: field.required ? 'bold' : 'normal' }}>
                              {field.label} {field.required && '*'}
                            </span>
                            {isAutoMapped && (
                              <span style={{
                                marginLeft: '8px',
                                fontSize: '12px',
                                color: '#666',
                                fontStyle: 'italic'
                              }}>
                                (Auto-detected)
                              </span>
                            )}
                          </div>
                          
                          {field.required && (
                            <span style={{
                              position: 'absolute',
                              right: '8px',
                              color: '#d32f2f',
                              fontSize: '16px'
                            }}>
                              ●
                            </span>
                          )}
                          
                          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {mappedColumn && (
                              <span style={{
                                backgroundColor: isAutoMapped ? getConfidenceColor(confidence) : '#4CAF50',
                                color: 'white',
                                padding: '2px 6px',
                                borderRadius: '3px',
                                fontSize: '12px',
                                fontWeight: 'bold'
                              }}>
                                {mappedColumn}
                                {isAutoMapped && (
                                  <span style={{ marginLeft: '4px', fontSize: '10px' }}>
                                    ({confidence}%)
                                  </span>
                                )}
                              </span>
                            )}
                            {!mappedColumn && autoMappedColumn && (
                              <span style={{
                                backgroundColor: '#FFC107',
                                color: 'white',
                                padding: '2px 6px',
                                borderRadius: '3px',
                                fontSize: '12px'
                              }}>
                                Click to accept
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Column mapping state */}
              {Object.keys(columnMapping).length > 0 && (
                <div className="mapping-summary" style={{ marginTop: '15px', padding: '10px', backgroundColor: '#e8f5e8', borderRadius: '4px' }}>
                  <h4>Current Mapping:</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
                    {Object.entries(columnMapping).map(([field, column]) => (
                      <div key={field} style={{ fontSize: '14px' }}>
                        <strong>{field}:</strong> {column}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Validation messages */}
              {mappingErrors.length > 0 && (
                <div className="mapping-errors" style={{ marginTop: '15px', padding: '10px', backgroundColor: '#ffebee', borderRadius: '4px' }}>
                  <h4>Mapping Issues:</h4>
                  {mappingErrors.map((error, index) => (
                    <div key={index} style={{ color: '#d32f2f', fontSize: '14px', marginBottom: '5px' }}>
                      • {error}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="import-actions">
              <button
                className="btn"
                onClick={handleImportData}
                disabled={!filePath || loading || importing || !isMappingValid()}
              >
                {importing ? 'Importing...' : 'Import Data'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setFilePath('');
                  setPreview([]);
                  setColumns([]);
                  setRowsTotal(0);
                  setError('');
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ImportData;