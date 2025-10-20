import React, { useState, useEffect } from 'react';
import './BackupRecovery.css';

interface Backup {
  backup_name: string;
  backup_type: string;
  timestamp: string;
  datetime: string;
  files: Array<{ name: string; size: number; checksum: string }>;
  total_size: number;
  version: string;
}

interface BackupStats {
  total_backups: number;
  total_size: number;
  total_size_mb: number;
  oldest_backup: string;
  newest_backup: string;
  retention_days: number;
  max_backups: number;
}

interface BackupConfig {
  retention_days: number;
  max_backups: number;
  auto_backup_enabled: boolean;
  backup_on_startup: boolean;
  verify_integrity: boolean;
}

interface IntegrityResult {
  valid: boolean;
  database: string;
  error?: string;
  message?: string;
  corrupted?: boolean;
}

const BackupRecovery: React.FC = () => {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [stats, setStats] = useState<BackupStats | null>(null);
  const [config, setConfig] = useState<BackupConfig | null>(null);
  const [integrityResults, setIntegrityResults] = useState<IntegrityResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedBackup, setSelectedBackup] = useState<string | null>(null);

  useEffect(() => {
    loadBackups();
    loadStats();
    loadConfig();
  }, []);

  const loadBackups = async () => {
    try {
      const result = await window.electronAPI.invoke('list-backups');
      if (result.error) {
        setError(result.error);
      } else {
        setBackups(result.backups || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const loadStats = async () => {
    try {
      const result = await window.electronAPI.invoke('get-backup-stats');
      if (result.error) {
        setError(result.error);
      } else {
        setStats(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const loadConfig = async () => {
    try {
      const result = await window.electronAPI.invoke('get-backup-config');
      if (result.error) {
        setError(result.error);
      } else {
        setConfig(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const createBackup = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await window.electronAPI.invoke('create-backup', {
        backupType: 'manual'
      });

      if (result.error) {
        setError(result.error);
      } else if (result.success) {
        setSuccess(`Backup created successfully: ${result.backup_name}`);
        loadBackups();
        loadStats();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const verifyBackup = async (backupName: string) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await window.electronAPI.invoke('verify-backup', {
        backupName
      });

      if (result.error) {
        setError(`Verification failed: ${result.error}`);
      } else if (result.valid) {
        setSuccess(`Backup verified successfully: ${result.files_verified} files OK`);
      } else {
        setError(`Backup verification failed: ${result.error || 'Unknown error'}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const restoreBackup = async (backupName: string) => {
    if (!confirm(`Are you sure you want to restore from backup: ${backupName}?\n\nThis will replace your current databases!`)) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await window.electronAPI.invoke('restore-backup', {
        backupName
      });

      if (result.error) {
        setError(`Restore failed: ${result.error}`);
      } else if (result.success) {
        setSuccess(`Restore successful! Restored ${result.restored_files.length} files.`);
        alert('Databases restored successfully. Please restart the application.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const deleteBackup = async (backupName: string) => {
    if (!confirm(`Are you sure you want to delete backup: ${backupName}?`)) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await window.electronAPI.invoke('delete-backup', {
        backupName
      });

      if (result.error) {
        setError(`Delete failed: ${result.error}`);
      } else if (result.success) {
        setSuccess(`Backup deleted: ${backupName}`);
        loadBackups();
        loadStats();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const checkIntegrity = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await window.electronAPI.invoke('check-all-databases');

      if (result.error) {
        setError(result.error);
      } else {
        setIntegrityResults(result.databases || []);
        if (result.corrupted > 0) {
          setError(`Warning: ${result.corrupted} database(s) may be corrupted!`);
        } else {
          setSuccess(`All databases OK: ${result.valid} database(s) checked`);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const recoverFromWAL = async (dbName: string) => {
    if (!confirm(`Attempt to recover ${dbName} from WAL file?`)) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await window.electronAPI.invoke('recover-from-wal', {
        dbName
      });

      if (result.error) {
        setError(`Recovery failed: ${result.error}`);
      } else if (result.success) {
        setSuccess(`Recovery successful for ${dbName}`);
        checkIntegrity();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const updateConfig = async () => {
    if (!config) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await window.electronAPI.invoke('update-backup-config', {
        retentionDays: config.retention_days,
        maxBackups: config.max_backups,
        autoBackupEnabled: config.auto_backup_enabled,
        backupOnStartup: config.backup_on_startup,
        verifyIntegrity: config.verify_integrity
      });

      if (result.error) {
        setError(result.error);
      } else if (result.success) {
        setSuccess('Configuration updated successfully');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="backup-recovery-container">
      <h1>Backup & Recovery</h1>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      {/* Statistics Section */}
      {stats && (
        <div className="stats-section">
          <h2>Statistics</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total Backups</div>
              <div className="stat-value">{stats.total_backups}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Size</div>
              <div className="stat-value">{stats.total_size_mb.toFixed(2)} MB</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Retention Policy</div>
              <div className="stat-value">{stats.retention_days} days</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Max Backups</div>
              <div className="stat-value">{stats.max_backups}</div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="actions-section">
        <h2>Quick Actions</h2>
        <div className="action-buttons">
          <button onClick={createBackup} disabled={loading} className="btn-primary">
            {loading ? 'Creating...' : 'Create Backup Now'}
          </button>
          <button onClick={checkIntegrity} disabled={loading} className="btn-secondary">
            Check Database Integrity
          </button>
          <button onClick={loadBackups} disabled={loading} className="btn-secondary">
            Refresh List
          </button>
        </div>
      </div>

      {/* Configuration Section */}
      {config && (
        <div className="config-section">
          <h2>Configuration</h2>
          <div className="config-form">
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.auto_backup_enabled}
                  onChange={(e) => setConfig({ ...config, auto_backup_enabled: e.target.checked })}
                />
                Enable Automatic Backups
              </label>
            </div>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.backup_on_startup}
                  onChange={(e) => setConfig({ ...config, backup_on_startup: e.target.checked })}
                />
                Backup on Application Startup
              </label>
            </div>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.verify_integrity}
                  onChange={(e) => setConfig({ ...config, verify_integrity: e.target.checked })}
                />
                Verify Backup Integrity
              </label>
            </div>
            <div className="form-group">
              <label>
                Retention Period (days):
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={config.retention_days}
                  onChange={(e) => setConfig({ ...config, retention_days: parseInt(e.target.value) })}
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Maximum Backups:
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={config.max_backups}
                  onChange={(e) => setConfig({ ...config, max_backups: parseInt(e.target.value) })}
                />
              </label>
            </div>
            <button onClick={updateConfig} disabled={loading} className="btn-primary">
              Save Configuration
            </button>
          </div>
        </div>
      )}

      {/* Backups List */}
      <div className="backups-section">
        <h2>Available Backups</h2>
        {backups.length === 0 ? (
          <p className="no-backups">No backups found. Create your first backup above.</p>
        ) : (
          <div className="backups-list">
            {backups.map((backup) => (
              <div
                key={backup.backup_name}
                className={`backup-card ${selectedBackup === backup.backup_name ? 'selected' : ''}`}
                onClick={() => setSelectedBackup(backup.backup_name)}
              >
                <div className="backup-header">
                  <h3>{backup.backup_name}</h3>
                  <span className={`backup-type ${backup.backup_type}`}>
                    {backup.backup_type}
                  </span>
                </div>
                <div className="backup-details">
                  <div className="detail-row">
                    <span>Date:</span>
                    <span>{formatDate(backup.datetime)}</span>
                  </div>
                  <div className="detail-row">
                    <span>Files:</span>
                    <span>{backup.files.length}</span>
                  </div>
                  <div className="detail-row">
                    <span>Size:</span>
                    <span>{formatSize(backup.total_size)}</span>
                  </div>
                </div>
                <div className="backup-actions">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      verifyBackup(backup.backup_name);
                    }}
                    disabled={loading}
                    className="btn-verify"
                  >
                    Verify
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      restoreBackup(backup.backup_name);
                    }}
                    disabled={loading}
                    className="btn-restore"
                  >
                    Restore
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteBackup(backup.backup_name);
                    }}
                    disabled={loading}
                    className="btn-delete"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Integrity Check Results */}
      {integrityResults.length > 0 && (
        <div className="integrity-section">
          <h2>Database Integrity Check Results</h2>
          <div className="integrity-results">
            {integrityResults.map((result, index) => (
              <div
                key={index}
                className={`integrity-card ${result.valid ? 'valid' : 'invalid'}`}
              >
                <h4>{result.database}</h4>
                <p>
                  {result.valid ? (
                    <span className="status-ok">✓ OK</span>
                  ) : (
                    <span className="status-error">✗ {result.error}</span>
                  )}
                </p>
                {result.corrupted && (
                  <button
                    onClick={() => recoverFromWAL(result.database)}
                    disabled={loading}
                    className="btn-recover"
                  >
                    Attempt Recovery
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BackupRecovery;
