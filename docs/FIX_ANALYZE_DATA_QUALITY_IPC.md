# Fix: Add Missing analyze-data-quality IPC Handler

## Problem
The Data Analysis page was throwing an error:
```
Error: Invalid channel: analyze-data-quality
```

## Root Cause
The `analyze-data-quality` Electron IPC handler was not registered in `electron/main.ts`, even though:
- The backend handler exists in `backend/main.py`
- The frontend component tries to invoke it with `window.electronAPI.invoke('analyze-data-quality')`

This created a missing link in the IPC communication chain.

## Solution
Added the missing IPC handler to `electron/main.ts`:

```typescript
// Analyze data quality
ipcMain.handle('analyze-data-quality', async (_event, data) => {
  try {
    const payload = data || {};
    const result = await pythonService.sendToPython('analyze-data-quality', payload) as any;
    if (result?.error) {
      throw new Error(result.error);
    }
    return result;
  } catch (error) {
    console.error('Error in analyze-data-quality:', error);
    return {
      error: error instanceof Error ? error.message : String(error)
    };
  }
});
```

## File Modified
- `electron/main.ts` - Added IPC handler at end of file (lines 1028-1041)

## Communication Chain
Now the full chain works:

```
React Component (DataAnalysis.tsx)
    ↓ window.electronAPI.invoke('analyze-data-quality')
Electron Main Process (electron/main.ts)
    ↓ pythonService.sendToPython('analyze-data-quality')
Python Backend (backend/main.py)
    ↓ handle_request(action='analyze-data-quality')
    ↓ DataQualityAnalyzer.analyze_all_symbols()
    ↓ returns results
Python → Electron → React (display results)
```

## Build Status
✅ Build successful - all components compiled cleanly

## Testing
To verify the fix:
1. Start dev server: `npm run dev`
2. Go to Data Management → Data Quality tab
3. The data quality analysis dashboard should now load without errors
4. Quality metrics table and summary cards should display correctly

## Related Files
- `src/components/DataAnalysis.tsx` - Frontend component (no changes needed)
- `backend/data_quality_analyzer.py` - Backend analyzer (no changes needed)
- `backend/main.py` - Backend handler (already exists, no changes needed)
- `electron/preload.ts` - Preload script (already exposes electronAPI.invoke, no changes needed)

## Notes
This was part of the data quality feature that was moved to be a sub-tab inside Data Management. The backend and frontend were properly set up, but the Electron IPC bridge was missing.
