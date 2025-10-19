import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import { join } from 'path';
import { existsSync } from 'fs';
import { spawn } from 'child_process';

const isDev = process.env.NODE_ENV === 'development';

let mainWindow: BrowserWindow | null = null;

// M2.5 — Main → Python: Python service for backend communication
class PythonService {
  private pythonProcess: any = null;
  private pendingRequests = new Map();
  private requestId = 0;

  async start() {
    const pythonScript = join(process.cwd(), 'backend', 'main.py');
    console.log('Starting Python backend:', pythonScript);

    this.pythonProcess = spawn('python', [pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    this.pythonProcess.stdout.on('data', (data: Buffer) => {
       const output = data.toString().trim();

       try {
         const response = JSON.parse(output);

         // Handle progress events and forward to renderer
         if (response.type === 'import-progress' || response.type === 'import-summary' || response.type === 'scan-progress') {
           console.log('IMPORT-PROGRESS:', response);
           if (mainWindow && !mainWindow.isDestroyed()) {
             const channel = response.type === 'scan-progress' ? 'scan-progress' : 'import-progress';
             mainWindow.webContents.send(channel, response);
           }
           // Also resolve the request if it's a final summary
           if (response.type === 'import-summary') {
             const requestId = response.requestId;
             if (requestId && this.pendingRequests.has(requestId)) {
               const resolve = this.pendingRequests.get(requestId);
               this.pendingRequests.delete(requestId);
               resolve(response);
             }
           }
         } else {
           // Handle regular responses by resolving pending requests
           const requestId = response.requestId;
           if (requestId && this.pendingRequests.has(requestId)) {
             const resolve = this.pendingRequests.get(requestId);
             this.pendingRequests.delete(requestId);
             resolve(response);
           }
         }
       } catch (e) {
         // Only log import-related stderr output
         if (output && (output.includes('IMPORT:') || output.includes('DEBUG:') || output.includes('Starting') || output.includes('File') || output.includes('Database'))) {
           console.log('PYTHON:', output);
         }
       }
     });

    this.pythonProcess.stderr.on('data', (data: Buffer) => {
      console.error('Python stderr:', data.toString());
    });

    this.pythonProcess.on('close', (code: number) => {
       console.log('Python process exited with code', code);
       console.log('DEBUG: Pending requests count before cleanup:', this.pendingRequests.size);
       this.pythonProcess = null;
       // Reject all pending requests
       this.pendingRequests.forEach((resolve, _requestId) => {
         console.log('DEBUG: Rejecting pending request');
         resolve({
           error: 'Python process terminated',
           code: code
         });
       });
       this.pendingRequests.clear();
       console.log('DEBUG: All pending requests cleared');
     });

    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (this.pythonProcess) {
          console.log('Python backend process started');
          resolve(true);
        } else {
          reject(new Error('Failed to start Python process'));
        }
      }, 1000);
    });
  }

  async sendToPython(action: string, data?: any) {
    if (!this.pythonProcess) {
      await this.start();
    }

    return new Promise((resolve, reject) => {
      const requestId = ++this.requestId;
      const request = {
        action,
        data,
        requestId,
        timestamp: new Date().toISOString()
      };

      // Set a timeout for the request
      const longTimeoutActions = new Set(['import-data', 'run-scan']);
      const actionTimeoutMs = longTimeoutActions.has(action) ? 300000 : 60000; // 5 min for heavy actions
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        if (longTimeoutActions.has(action)) {
          console.error(`Python request timeout for action: ${action}, requestId: ${requestId}`);
          console.error(`Request details:`, request);
          console.error(`Python process alive: ${this.pythonProcess ? 'yes' : 'no'}`);
          console.error(`Pending requests count at timeout: ${this.pendingRequests.size}`);
          console.error(`Process PID: ${this.pythonProcess.pid}`);
          console.error(`Process stdin writeable: ${this.pythonProcess.stdin?.writable}`);
          console.error(`Process stdout readable: ${this.pythonProcess.stdout?.readable}`);
          console.error(`Process stderr readable: ${this.pythonProcess.stderr?.readable}`);
        }
        reject(new Error(`Python request timeout for action: ${action}`));
      }, actionTimeoutMs); // 5 minutes for heavy actions, 60 seconds for others

      // Store the resolve function with timeout cleanup
      this.pendingRequests.set(requestId, (response: any) => {
        clearTimeout(timeout);
        if (action === 'import-data') {
          console.log(`IMPORT-RESPONSE: Received response for import-data request ${requestId}`);
        } else if (action === 'run-scan') {
          console.log(`SCAN-RESPONSE: Received response for run-scan request ${requestId}`);
        }
        resolve(response);
      });

      if (action === 'import-data') {
        console.log('IMPORT-DEBUG: Sending import-data to Python:', request);
        console.log('IMPORT-DEBUG: Python process state before write:', {
          pid: this.pythonProcess.pid,
          stdinWritable: this.pythonProcess.stdin?.writable,
          stdoutReadable: this.pythonProcess.stdout?.readable,
          stderrReadable: this.pythonProcess.stderr?.readable
        });
      } else if (action === 'run-scan') {
        console.log('SCAN-DEBUG: Sending run-scan to Python:', { requestId, hasOptions: !!data?.options, hasSpec: !!data?.scannerSpec });
      }
      this.pythonProcess.stdin.write(JSON.stringify(request) + '\n');
      if (action === 'import-data') {
        console.log(`IMPORT-DEBUG: Sent to Python, pending requests count: ${this.pendingRequests.size}`);
        console.log('IMPORT-DEBUG: Python process state after write:', {
          stdinWritable: this.pythonProcess.stdin?.writable,
          stdoutReadable: this.pythonProcess.stdout?.readable,
          stderrReadable: this.pythonProcess.stderr?.readable
        });
      } else if (action === 'run-scan') {
        console.log(`SCAN-DEBUG: Sent to Python, pending requests count: ${this.pendingRequests.size}`);
      }
    });
  }

  // Helper method to get database path for testing
  getDatabasePath() {
    const path = require('path');
    const os = require('os');
    return path.join(os.homedir(), '.byod_backtesting', 'trading_data.db');
  }

  stop() {
    if (this.pythonProcess) {
      this.pythonProcess.kill();
      this.pythonProcess = null;
    }
  }
}

const pythonService = new PythonService();

function createWindow(): void {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: join(process.cwd(), 'dist-electron', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    },
    icon: join(process.cwd(), 'assets', 'icon.png'), // Will be created later
    title: 'BYOD Strategy Backtesting',
    titleBarStyle: 'default',
  });

  // Load the app
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    const indexPath = join(process.cwd(), 'dist', 'index.html');
    console.log('Loading file:', indexPath);
    console.log('File exists:', existsSync(indexPath));
    mainWindow.loadFile(indexPath);

    // Add error handling
    mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription) => {
      console.error('Failed to load:', errorCode, errorDescription);
    });

    mainWindow.webContents.on('did-finish-load', () => {
       console.log('Page loaded successfully');

       // M2.7 — Automatic Probe: Catch missing preload early
       mainWindow!.webContents.executeJavaScript(
         'console.log("Probe:", typeof window.electronAPI);' +
         'if (!window.electronAPI) console.error("Preload missing!");'
       ).then((result: any) => {
         console.log('Preload probe result:', result);
       }).catch((error: Error) => {
         console.error('Preload probe failed:', error);
       });
     });
  }

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // Allow external links to open in default browser
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });
}

// App event listeners
app.whenReady().then(async () => {
   // M2.5 — Main → Python: Start Python backend service
   try {
     await pythonService.start();
     console.log('Python backend service initialized');
   } catch (error) {
     console.error('Failed to start Python backend:', error);
   }

   createWindow();

   app.on('activate', () => {
    // On macOS, re-create window when dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // On macOS, keep app running even when all windows are closed
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Security: Prevent new window creation
app.on('web-contents-created', (_, contents) => {
  contents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });
});

// IPC handlers for basic functionality
ipcMain.handle('health-check', async () => {
  // M2.6 — Full Chain: Health check with Python backend (silent for debugging)
  try {
    const pythonHealth = await pythonService.sendToPython('health-check');
    const fs = require('fs');
    const path = require('path');
    const os = require('os');

    const dbPath = path.join(os.homedir(), '.byod_backtesting', 'trading_data.db');
    const dbExists = fs.existsSync(dbPath);
    const dbSize = dbExists ? fs.statSync(dbPath).size : 0;

    return {
      status: 'ok',
      database: dbExists ? 'connected' : 'created',
      timestamp: new Date().toISOString(),
      version: app.getVersion(),
      python_backend: pythonHealth,
      electron_main: { ok: true, from: 'main' },
      database_info: {
        path: dbPath,
        exists: dbExists,
        size: dbSize
      }
    };
  } catch (error) {
    return {
      status: 'error',
      timestamp: new Date().toISOString(),
      version: app.getVersion(),
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// M2.4 — Renderer → Main IPC: Simple ping handler
ipcMain.handle('ping', () => ({ ok: true, from: 'main' }));

// M2.5 — Main → Python: Test ping to Python
ipcMain.handle('ping-python', async () => {
  try {
    return await pythonService.sendToPython('ping');
  } catch (error) {
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

// File dialog handler for opening file selection dialog
ipcMain.handle('open-file-dialog', async () => {
  try {
    if (!mainWindow) {
      throw new Error('Main window not available');
    }

    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      filters: [
        {
          name: 'Data Files',
          extensions: ['csv', 'xlsx', 'xls', 'parquet']
        },
        {
          name: 'All Files',
          extensions: ['*']
        }
      ]
    });

    if (result.canceled) {
      return { canceled: true };
    }

    if (result.filePaths.length === 0) {
      return { canceled: true };
    }

    const filePath = result.filePaths[0];
    console.log('File selected:', filePath);

    return {
      canceled: false,
      filePath: filePath
    };
  } catch (error) {
    console.error('Error in open-file-dialog:', error);
    return {
      canceled: false,
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// File preview handler for reading and parsing CSV files
ipcMain.handle('preview-file', async (_event, data) => {
  try {
    const { filePath } = data;

    if (!filePath) {
      throw new Error('No file path provided');
    }

    if (!existsSync(filePath)) {
      throw new Error('File does not exist');
    }

    // Use Python backend for file preview
    const result = await pythonService.sendToPython('preview-file', {
      file_path: filePath
    }) as any;

    if (result.error) {
      throw new Error(result.error);
    }

    console.log('File preview generated via Python:', {
      columns: result.columns?.length || 0,
      previewRows: result.preview?.length || 0,
      totalRows: result.rows_total || 0
    });

    return result;
  } catch (error) {
    console.error('Error in preview-file:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// Import data handler for importing CSV data into database
ipcMain.handle('import-data', async (_event, data) => {
  try {
    const { filePath, symbol, columnMapping, incremental, dataset_name, dataset_description } = data;

    if (!filePath) {
      throw new Error('No file path provided');
    }

    if (!existsSync(filePath)) {
      throw new Error('File does not exist');
    }

    // Send to Python backend for processing with column mapping and incremental flag
    const result = await pythonService.sendToPython('import-data', {
      file_path: filePath,
      symbol: symbol || 'DEFAULT',
      column_mapping: columnMapping || {},
      incremental: incremental !== undefined ? incremental : true,  // Default to true if not specified
      dataset_name: dataset_name || '',
      dataset_description: dataset_description || ''
    }) as any;

    if (result.error) {
      throw new Error(result.error);
    }

    console.log('Data import successful:', result);

    return {
      success: true,
      rowsImported: result.rowsImported || result.rows_imported || 0,
      rowsSkipped: result.rowsSkipped || result.rows_skipped || 0,
      symbol: symbol || 'DEFAULT',
      timeElapsed: result.timeElapsed || result.time_elapsed || 0,
      validationWarnings: result.validationWarnings || result.validation_warnings || [],
      incrementalUpdate: result.incrementalUpdate || result.incremental_update || false,
      existingDataRange: result.existingDataRange || result.existing_data_range || null
    };
  } catch (error) {
    console.error('Error in import-data:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// Get price data handler for viewing imported data
ipcMain.handle('get-price-data', async (_event, data) => {
  try {
    const { symbol, limit = 1000, offset = 0, start_date, end_date } = data;

    if (!symbol) {
      throw new Error('No symbol provided');
    }

    // Send to Python backend for database query
    const result = await pythonService.sendToPython('get-price-data', {
      symbol,
      limit,
      offset,
      start_date,
      end_date
    }) as any;

    if (result.error) {
      throw new Error(result.error);
    }

    console.log('Price data retrieved successfully:', {
      symbol,
      count: result.data?.length || 0,
      symbols: result.symbols?.length || 0,
      start_date,
      end_date
    });

    return result;
  } catch (error) {
    console.error('Error in get-price-data:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// Generic IPC handler for dataset operations
ipcMain.handle('get-datasets', async () => {
  try {
    const result = await pythonService.sendToPython('get-datasets') as any;

    if (result.error) {
      throw new Error(result.error);
    }

    console.log('Datasets retrieved successfully:', {
      count: result.datasets?.length || 0
    });

    return result;
  } catch (error) {
    console.error('Error in get-datasets:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// Get specific dataset handler
ipcMain.handle('get-dataset', async (_event, data) => {
  try {
    const { dataset_name } = data;

    if (!dataset_name) {
      throw new Error('No dataset name provided');
    }

    const result = await pythonService.sendToPython('get-dataset', {
      dataset_name
    }) as any;

    if (result.error) {
      throw new Error(result.error);
    }

    console.log('Dataset retrieved successfully:', {
      dataset_name
    });

    return result;
  } catch (error) {
    console.error('Error in get-dataset:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// Create dataset handler
ipcMain.handle('create-dataset', async (_event, data) => {
  try {
    const { dataset_name, dataset_description } = data;

    if (!dataset_name) {
      throw new Error('No dataset name provided');
    }

    const result = await pythonService.sendToPython('create-dataset', {
      dataset_name,
      dataset_description: dataset_description || ''
    }) as any;

    if (result.error) {
      throw new Error(result.error);
    }

    console.log('Dataset created successfully:', {
      dataset_name
    });

    return result;
  } catch (error) {
    console.error('Error in create-dataset:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// Run scanner handler (Phase 0 skeleton)
ipcMain.handle('run-scan', async (_event, data) => {
  try {
    const { scannerSpec, options } = data || {};
    const result = await pythonService.sendToPython('run-scan', {
      scannerSpec: scannerSpec || {},
      options: options || { latestOnly: true, limit: 5000 }
    }) as any;

    if (result.error) {
      throw new Error(result.error);
    }

    return result;
  } catch (error) {
    console.error('Error in run-scan:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});

// Saved scans CRUD handlers
ipcMain.handle('save-scan', async (_event, data) => {
  try {
    const { name, spec, description } = data || {};
    if (!name || !spec) {
      throw new Error('name and spec are required');
    }
    const result = await pythonService.sendToPython('save-scan', { name, spec, description }) as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in save-scan:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

ipcMain.handle('get-scans', async () => {
  try {
    const result = await pythonService.sendToPython('get-scans') as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in get-scans:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

ipcMain.handle('get-scan', async (_event, data) => {
  try {
    const { name } = data || {};
    if (!name) throw new Error('name is required');
    const result = await pythonService.sendToPython('get-scan', { name }) as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in get-scan:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

ipcMain.handle('delete-scan', async (_event, data) => {
  try {
    const { name } = data || {};
    if (!name) throw new Error('name is required');
    const result = await pythonService.sendToPython('delete-scan', { name }) as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in delete-scan:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

// Watchlists CRUD handlers
ipcMain.handle('save-watchlist', async (_event, data) => {
  try {
    const { name, symbols, description } = data || {};
    if (!name || !symbols) throw new Error('name and symbols are required');
    const result = await pythonService.sendToPython('save-watchlist', { name, symbols, description }) as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in save-watchlist:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

ipcMain.handle('get-watchlists', async () => {
  try {
    const result = await pythonService.sendToPython('get-watchlists') as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in get-watchlists:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

ipcMain.handle('get-watchlist-symbols', async (_event, data) => {
  try {
    const { name } = data || {};
    if (!name) throw new Error('name is required');
    const result = await pythonService.sendToPython('get-watchlist-symbols', { name }) as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in get-watchlist-symbols:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

ipcMain.handle('delete-watchlist', async (_event, data) => {
  try {
    const { name } = data || {};
    if (!name) throw new Error('name is required');
    const result = await pythonService.sendToPython('delete-watchlist', { name }) as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in delete-watchlist:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});

// Parse DSL to scannerSpec
ipcMain.handle('parse-dsl', async (_event, data) => {
  try {
    const { dsl, timeframe, universe } = data || {};
    const result = await pythonService.sendToPython('parse-dsl', { dsl, timeframe, universe }) as any;
    if (result.error) throw new Error(result.error);
    return result;
  } catch (error) {
    console.error('Error in parse-dsl:', error);
    return { error: error instanceof Error ? error.message : String(error) };
  }
});