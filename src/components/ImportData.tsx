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
      const previewResult = await window.electronAPI.invoke('preview-file', { filePath: selectedPath });
      if (previewResult.error) {
        throw new Error(previewResult.error);
      }

      setPreview(previewResult.preview || []);
      setColumns(previewResult.columns || []);
      setRowsTotal(previewResult.rows_total || 0);
      setError('');
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

    try {
      // Get the symbol from the input field
      const symbolInput = document.getElementById('symbol') as HTMLInputElement;
      const symbol = symbolInput?.value?.trim() || 'DEFAULT';

      const result = await window.electronAPI.invoke('import-data', {
        filePath,
        symbol
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setImportSuccess(`Successfully imported ${result.rowsImported || 0} rows of ${symbol} data`);
      console.log('Import successful:', result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import data');
      console.error('Import error:', err);
    } finally {
      setImporting(false);
    }
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

        {importSuccess && (
          <div className="success-message" style={{ color: 'green', marginTop: '10px' }}>
            {importSuccess}
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

            {/* Column mapping placeholder for Sprint 2.1 */}
            <div className="column-mapping">
              <h3>Column Mapping (Sprint 2.2)</h3>
              <p>Preview shows standardized columns. Manual mapping coming soon.</p>
            </div>

            <div className="import-actions">
              <button
                className="btn"
                onClick={handleImportData}
                disabled={!filePath || loading || importing}
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