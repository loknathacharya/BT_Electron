import React, { useState } from 'react';

const ImportData: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files) as File[];
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Import Data</h2>
        <p>
          Import your trading data from CSV files. The application supports OHLCV data
          with timestamps. You can drag and drop files or browse to select them.
        </p>
      </div>

      <div className="import-section">
        <div
          className={`file-drop-zone ${isDragOver ? 'drag-over' : ''} ${
            selectedFile ? 'has-file' : ''
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {selectedFile ? (
            <div className="file-selected">
              <div className="file-icon">📄</div>
              <div className="file-info">
                <h3>{selectedFile.name}</h3>
                <p>Size: {(selectedFile.size / 1024).toFixed(2)} KB</p>
                <p>Type: {selectedFile.type || 'Unknown'}</p>
              </div>
              <button
                className="btn btn-secondary"
                onClick={() => setSelectedFile(null)}
              >
                Remove
              </button>
            </div>
          ) : (
            <div className="file-placeholder">
              <div className="placeholder-icon">📊</div>
              <h3>Drop your CSV file here</h3>
              <p>or click to browse for files</p>
              <input
                type="file"
                id="file-input"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileInputChange}
                style={{ display: 'none' }}
              />
              <label htmlFor="file-input" className="btn">
                Select File
              </label>
            </div>
          )}
        </div>

        {selectedFile && (
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

            <div className="column-mapping">
              <h3>Column Mapping</h3>
              <p>Map your CSV columns to the required format:</p>

              <div className="mapping-grid">
                <div className="mapping-item">
                  <label>Timestamp Column:</label>
                  <select defaultValue="">
                    <option value="">Select column...</option>
                    <option value="date">Date</option>
                    <option value="timestamp">Timestamp</option>
                    <option value="datetime">DateTime</option>
                  </select>
                </div>

                <div className="mapping-item">
                  <label>Open Price Column:</label>
                  <select defaultValue="">
                    <option value="">Select column...</option>
                    <option value="open">Open</option>
                    <option value="open_price">Open Price</option>
                  </select>
                </div>

                <div className="mapping-item">
                  <label>High Price Column:</label>
                  <select defaultValue="">
                    <option value="">Select column...</option>
                    <option value="high">High</option>
                    <option value="high_price">High Price</option>
                  </select>
                </div>

                <div className="mapping-item">
                  <label>Low Price Column:</label>
                  <select defaultValue="">
                    <option value="">Select column...</option>
                    <option value="low">Low</option>
                    <option value="low_price">Low Price</option>
                  </select>
                </div>

                <div className="mapping-item">
                  <label>Close Price Column:</label>
                  <select defaultValue="">
                    <option value="">Select column...</option>
                    <option value="close">Close</option>
                    <option value="close_price">Close Price</option>
                  </select>
                </div>

                <div className="mapping-item">
                  <label>Volume Column (Optional):</label>
                  <select defaultValue="">
                    <option value="">Select column...</option>
                    <option value="volume">Volume</option>
                    <option value="vol">Vol</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="import-actions">
              <button className="btn">Import Data</button>
              <button
                className="btn btn-secondary"
                onClick={() => setSelectedFile(null)}
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