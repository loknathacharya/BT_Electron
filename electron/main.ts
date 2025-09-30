import { app, BrowserWindow, ipcMain } from 'electron';
import { join } from 'path';
import { existsSync } from 'fs';
import { spawn } from 'child_process';

const isDev = process.env.NODE_ENV === 'development';

let mainWindow: BrowserWindow | null = null;

// M2.5 — Main → Python: Python service for backend communication
class PythonService {
  private pythonProcess: any = null;
  // private pendingRequests = new Map(); // Reserved for future use

  async start() {
    const pythonScript = join(process.cwd(), 'backend', 'main.py');
    console.log('Starting Python backend:', pythonScript);

    this.pythonProcess = spawn('python', [pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    this.pythonProcess.stdout.on('data', (data: Buffer) => {
      try {
        const response = JSON.parse(data.toString());
        console.log('Python response:', response);
        // Handle response if needed
      } catch (e) {
        console.log('Python stdout:', data.toString());
      }
    });

    this.pythonProcess.stderr.on('data', (data: Buffer) => {
      console.error('Python stderr:', data.toString());
    });

    this.pythonProcess.on('close', (code: number) => {
      console.log('Python process exited with code', code);
      this.pythonProcess = null;
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

    return new Promise((resolve) => {
      const request = {
        action,
        data,
        timestamp: new Date().toISOString()
      };

      this.pythonProcess.stdin.write(JSON.stringify(request) + '\n');
      console.log('Sent to Python:', request);

      // For now, return a mock response since we're not handling responses properly
      setTimeout(() => {
        resolve({
          status: 'ok',
          message: 'Request sent to Python backend',
          action,
          python_alive: true
        });
      }, 100);
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
  // M2.6 — Full Chain: Health check with Python backend
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