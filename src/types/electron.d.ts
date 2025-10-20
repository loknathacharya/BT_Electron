// Type declarations for the Electron preload API injected on window.electron
// This file tells TypeScript that `window.electron` exists and what methods it provides.

declare global {
  interface Window {
    electron: {
      // Invoke a channel that returns a promise (ipcRenderer.invoke)
      invoke(channel: string, ...args: any[]): Promise<any>;

      // Send a fire-and-forget message (ipcRenderer.send)
      send(channel: string, ...args: any[]): void;

      // Basic on/once/removeListener helpers (if provided by preload)
      on?(channel: string, listener: (...args: any[]) => void): void;
      once?(channel: string, listener: (...args: any[]) => void): void;
      removeListener?(channel: string, listener: (...args: any[]) => void): void;
    };
  }
}

export {};
