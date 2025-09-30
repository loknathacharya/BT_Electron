# Implement an ipcMain.handle in the main process that uses dialog.showOpenDialog, expose a preload API with contextBridge, and call it from React; this is the recommended pattern with contextIsolation.
    // main.ts (Electron main process)
    import { app, BrowserWindow, dialog, ipcMain } from "electron";
import path from "node:path";

async function handleOpenFileDialog() {
    const res = await dialog.showOpenDialog({
        properties: ["openFile"],
        filters: [{ name: "All Files", extensions: ["*"] }],
    });
    if (res.canceled) return null;
    return res.filePaths; // or return res.filePaths[0]
}

function createWindow() {
    const win = new BrowserWindow({
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            // contextIsolation: true (default in modern templates)
            // nodeIntegration: false
        },
    });
    win.loadURL(process.env.VITE_DEV_SERVER_URL ?? "file://" + path.join(__dirname, "index.html"));
}

app.whenReady().then(() => {
    // Register handler BEFORE creating the window
    ipcMain.handle("open-file-dialog", handleOpenFileDialog);
    createWindow();
});

// preload.ts (Electron preload)
import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
    openFileDialog: () => ipcRenderer.invoke("open-file-dialog"),
});

// ImportData.tsx (renderer / React)
declare global {
    interface Window {
        electronAPI?: {
            openFileDialog: () => Promise<string[] | string | null>;
        };
    }
}

async function handleSelectFile() {
    try {
        const result = await window.electronAPI?.openFileDialog();
        // result is null if canceled; otherwise array or string depending on return
        // handle result here
    } catch (err) {
        // display error
    }
}
