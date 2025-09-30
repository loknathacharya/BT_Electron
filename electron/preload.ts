import { contextBridge, ipcRenderer } from 'electron';

// M2.1 — Preload Executes: Confirm preload actually runs
console.log('[preload] loaded, contextIsolation=%s', process.contextIsolated);

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // M2.3 — API Exposure Smoke Test: Simple test method
  ok: () => true,

  // M2.4 — Renderer → Main IPC: Simple ping method
  ping: () => ipcRenderer.invoke('ping'),

  // M2.5 — Main → Python: Test ping to Python backend
  pingPython: () => ipcRenderer.invoke('ping-python'),

  invoke: (channel: string, data?: any) => {
    // Whitelist of allowed channels
    const validChannels = [
      'health-check',
      'open-file-dialog',
      'preview-file',
      'import-data',
      'run-backtest',
      'get-strategies',
      'save-strategy',
      'get-price-data',
      'get-backtest-results'
    ];

    if (validChannels.includes(channel)) {
      return ipcRenderer.invoke(channel, data);
    }

    throw new Error(`Invalid channel: ${channel}`);
  },

  // Add other IPC methods as needed
  on: (channel: string, callback: (...args: any[]) => void) => {
    const validChannels = ['progress-update', 'error-occurred'];

    if (validChannels.includes(channel)) {
      ipcRenderer.on(channel, callback);
      // Return cleanup function
      return () => ipcRenderer.removeListener(channel, callback);
    }

    throw new Error(`Invalid channel: ${channel}`);
  },
});

// TypeScript declarations for window object
declare global {
   interface Window {
     electronAPI: {
       ok: () => boolean;
       ping: () => Promise<{ ok: boolean; from: string }>;
       pingPython: () => Promise<any>;
       invoke: (channel: string, data?: any) => Promise<any>;
       on: (channel: string, callback: (...args: any[]) => void) => () => void;
     };
   }
 }

// Add debugging
console.log('Preload script loaded successfully');
console.log('Electron API exposed to renderer process');