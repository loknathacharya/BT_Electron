# Delete Dataset Feature - User Flow Diagram

## User Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA MANAGEMENT PAGE                         │
│               Tabs: Browse Datasets | Data View                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Browse Datasets  │
                    │   Tab (Active)   │
                    └──────────────────┘
                              │
                              ▼
            ┌─────────────────────────────────────┐
            │    Available Datasets Grid          │
            │  ┌─────────────────────────────┐   │
            │  │ Dataset Card 1              │   │
            │  │ ────────────────────────    │   │
            │  │ Name: Sample Dataset        │   │
            │  │ Symbols: 5                  │   │
            │  │ Rows: 1,000                 │   │
            │  │ Range: Jan 2024 - Dec 2024  │   │
            │  │                             │   │
            │  │ [View Data Button]          │   │
            │  │ [🗑️ Delete Button] ◄─────┐ │   │
            │  └─────────────────────────────┘   │
            │                                     │
            │  [More dataset cards...]            │
            └─────────────────────────────────────┘
                              │
                    User clicks Delete
                              │
                              ▼
         ╔═════════════════════════════════════╗
         ║   ⚠️  DELETE DATASET CONFIRMATION  ║
         ║                                     ║
         ║  Are you sure?                      ║
         ║                                     ║
         ║  Deleting: Sample Dataset           ║
         ║                                     ║
         ║  ⚠️ WARNING:                         ║
         ║  This action CANNOT be undone!      ║
         ║                                     ║
         ║  Impact:                            ║
         ║  • 1,000 rows will be deleted       ║
         ║  • 5 symbols will be removed        ║
         ║                                     ║
         ║  [Cancel] [🗑️ Delete Forever]     ║
         ╚═════════════════════════════════════╝
                    │              │
          ┌─────────┘              └──────────┐
          │                                   │
    User clicks                        User clicks
    "Cancel"                      "Delete Forever"
          │                                   │
          ▼                                   ▼
    ┌──────────────┐          ┌──────────────────────┐
    │ Modal Closes │          │ Deletion in Progress │
    │ No Changes   │          │  (⏳ Deleting...)    │
    └──────────────┘          └──────────────────────┘
          │                            │
          │ Return to              Backend
          │ Browse Datasets       Processing:
          │ Tab                   • Verify dataset
          ▼                       • Delete metadata
    Nothing changed              • Delete price data
                                 • Commit changes
                                      │
                                      ▼
                          ┌──────────────────────────┐
                          │ Success Message Appears  │
                          │                          │
                          │ ✅ Dataset "Sample       │
                          │    Dataset" has been     │
                          │    successfully deleted. │
                          │                          │
                          │ (Auto-dismiss in 4 sec)  │
                          └──────────────────────────┘
                                      │
                                      ▼
                          ┌──────────────────────────┐
                          │ Browse Datasets Updated  │
                          │                          │
                          │ • Dataset card removed   │
                          │ • List refreshed         │
                          │ • Selection cleared      │
                          └──────────────────────────┘
```

## Alternative Flow - Error Handling

```
                    User clicks Delete
                              │
                              ▼
              Confirmation Modal Appears
                              │
                    User confirms deletion
                              │
                              ▼
         ┌────────────────────────────────┐
         │ Backend Processing Error       │
         │ (Network, DB Issue, etc)       │
         └────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────┐
         │ Error Message Displays         │
         │ ❌ Error: Database error       │
         │                                │
         │ Modal Remains Open             │
         │ [Try Again] [Cancel]           │
         └────────────────────────────────┘
                    │              │
          ┌─────────┘              └──────────┐
          │                                   │
    Click "Try Again"              Click "Cancel"
          │                                   │
          ▼                                   ▼
    Retry Deletion         Modal Closes
          │                 No Changes Made
          ▼
    (Process repeats)
```

## Data Flow Diagram

```
┌─────────────────────┐
│  Frontend UI        │
│  React Component    │
└──────────┬──────────┘
           │
           │ User clicks Delete Button
           │ (handleOpenDeleteConfirm)
           ▼
┌─────────────────────────────────────┐
│  Confirmation Modal Opens           │
│  - Saves dataset info to state      │
│  - Displays warning                 │
└──────────┬──────────────────────────┘
           │
           │ User confirms deletion
           │ (handleConfirmDelete)
           ▼
┌──────────────────────────────┐
│ Frontend IPC Call            │
│ invoke('delete-dataset',     │
│   { name: 'dataset_name' })  │
└──────────────┬───────────────┘
               │
               │ HTTP(S) IPC Bridge
               │
               ▼
┌───────────────────────────────────────┐
│  Electron Main Process                │
│  (IPC Handler)                        │
└──────────────┬────────────────────────┘
               │
               │ Route to handler
               │
               ▼
┌───────────────────────────────────────┐
│  handle_request(delete-dataset)       │
│  - Validate dataset name              │
│  - Call delete_dataset()              │
└──────────────┬────────────────────────┘
               │
               ▼
┌───────────────────────────────────────┐
│  Python Backend (main.py)             │
│  delete_dataset() method              │
└──────────────┬────────────────────────┘
               │
               ├─→ Connect to market_db
               │
               ├─→ Verify dataset exists
               │
               ├─→ Get symbols list
               │
               ├─→ DELETE FROM price_data
               │   WHERE symbol IN (...)
               │
               ├─→ DELETE FROM datasets
               │   WHERE name = ?
               │
               └─→ COMMIT transaction
                   │
                   ▼
        ┌──────────────────────┐
        │ Return Success/Error │
        │ to Frontend          │
        └──────────┬───────────┘
                   │
                   │ IPC Response
                   │
                   ▼
        ┌──────────────────────────────┐
        │ Frontend Receives Response   │
        │ - handleConfirmDelete()      │
        │ - Updates state             │
        │ - Refreshes dataset list    │
        │ - Shows success/error msg   │
        └──────────────────────────────┘
```

## State Management Flow

```
┌──────────────────────┐
│ ViewResults Component │
└──────┬───────────────┘
       │
       ├─ deleteConfirmOpen (boolean)
       │  └─ Controls modal visibility
       │
       ├─ datasetToDelete (object)
       │  └─ Stores dataset metadata
       │
       ├─ isDeleting (boolean)
       │  └─ Loading/processing state
       │
       ├─ successMessage (string)
       │  └─ Success notification text
       │
       └─ error (string)
          └─ Error notification text

State Transitions:

1. Initial: {
     deleteConfirmOpen: false,
     datasetToDelete: null,
     isDeleting: false,
     successMessage: ''
   }

2. After Delete Click: {
     deleteConfirmOpen: true,
     datasetToDelete: {...},
     isDeleting: false,
     successMessage: ''
   }

3. During Deletion: {
     deleteConfirmOpen: true,
     datasetToDelete: {...},
     isDeleting: true,
     successMessage: ''
   }

4. After Success: {
     deleteConfirmOpen: false,
     datasetToDelete: null,
     isDeleting: false,
     successMessage: '✅ Dataset "name" deleted.'
   }

5. After Dismiss (4 sec): {
     deleteConfirmOpen: false,
     datasetToDelete: null,
     isDeleting: false,
     successMessage: '' (auto-cleared)
   }
```

## Component Hierarchy

```
ViewResults Component
│
├─ Browse Datasets Tab
│  ├─ Available Datasets Grid
│  │  └─ Dataset Card (repeated)
│  │     ├─ Dataset Info Display
│  │     ├─ [View Data Button]
│  │     └─ [🗑️ Delete Button]
│  │
│  └─ Messages Section
│     ├─ Error Message (conditional)
│     └─ Success Message (conditional)
│
├─ Delete Confirmation Modal
│  ├─ Warning Icon
│  ├─ Title: "Delete Dataset?"
│  ├─ Dataset Name
│  ├─ Warning Box
│  ├─ Data Impact Details
│  └─ Action Buttons
│     ├─ [Cancel Button]
│     └─ [🗑️ Delete Forever Button]
│
└─ Chart Modal (other feature)

Event Handlers:
- handleOpenDeleteConfirm() → opens modal
- handleConfirmDelete() → processes deletion
- handleCancelDelete() → closes modal without action
```

This comprehensive flow ensures:
✅ User understands consequences  
✅ Single-click deletion is impossible  
✅ Clear feedback at each step  
✅ Graceful error handling  
✅ Data integrity preserved
