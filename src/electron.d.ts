/**
 * Global Electron preload API type definitions
 */

interface ElectronAPI {
  ok: () => boolean;
  ping: () => Promise<{ ok: boolean; from: string }>;
  pingPython: () => Promise<any>;
  invoke: (channel: string, data?: any) => Promise<any>;
  on: (channel: string, callback: (...args: any[]) => void) => () => void;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

export {};
