# Delete Dataset Feature - Quick Reference Guide

## How It Works

### For Users

1. **Navigate to Data Management → Browse Datasets**
2. **Find the dataset you want to delete**
3. **Click the red "🗑️ Delete" button** on the dataset card
4. **Review the warning modal** showing:
   - Dataset name
   - Number of rows to be deleted
   - Number of symbols to be deleted
   - Bold warning: "This action CANNOT be undone"
5. **Click "🗑️ Delete Forever"** to confirm deletion
6. **Wait for the green success message** confirming deletion
7. **Dataset is now removed** from the Available Datasets list

### What Gets Deleted

When you delete a dataset, the following is permanently removed:
- Dataset metadata (name, description, date range, etc.)
- All price data (OHLCV candles) associated with that dataset's symbols
- Any references in the database

### Safety Measures

✅ **Requires explicit confirmation** - You must click a second button to confirm  
✅ **Clear warning** - Modal states the action cannot be undone  
✅ **Data impact shown** - Number of rows and symbols displayed  
✅ **Error handling** - If deletion fails, you can retry  
✅ **Loading feedback** - Visual indication while deletion is in progress  

## Implementation Details

### Backend Endpoint

**IPC Action:** `delete-dataset`

```javascript
// Frontend call
const result = await window.electronAPI.invoke('delete-dataset', {
  name: 'dataset_name'
});
```

**Response on Success:**
```json
{
  "success": true,
  "message": "Dataset \"name\" and all associated data have been deleted.",
  "dataset_name": "dataset_name"
}
```

**Response on Error:**
```json
{
  "error": "error message",
  "success": false
}
```

### Database Operations

The backend performs these operations in sequence:
1. Validates the dataset exists
2. Retrieves the symbols list from dataset metadata
3. Deletes all price_data rows for each symbol
4. Deletes the dataset metadata entry
5. Commits the transaction

If any step fails, the transaction is rolled back and no data is deleted.

## Code Locations

### Frontend (`src/components/ViewResults.tsx`)

- **State variables:** Lines 32-35
- **Delete handlers:** Lines 154-201
- **Delete button:** Lines 416-428
- **Confirmation modal:** Lines 994-1027
- **Success message display:** Lines 376-380

### Backend (`backend/main.py`)

- **delete_dataset() method:** ~Line 728-780
- **delete-dataset handler:** ~Line 1797-1809

## Testing

### Manual Test Steps

1. Import a test dataset (if you don't have one)
2. Go to Data Management → Browse Datasets
3. Verify delete button appears on the dataset card
4. Click the delete button
5. Verify confirmation modal appears with correct info
6. Click Cancel - verify modal closes without deletion
7. Click delete button again
8. Click "Delete Forever"
9. Verify loading state appears
10. Verify success message appears after deletion
11. Verify dataset is removed from the list
12. Go to Data View tab - verify no data exists for that dataset

### Error Testing

1. Try deleting while network is slow
2. Verify error message displays on failure
3. Verify user can retry the deletion

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Delete button doesn't appear | Refresh the page or go back to Browse Datasets tab |
| Modal doesn't close after deletion | Check browser console for errors, try again |
| Dataset still appears after deletion | Refresh the page |
| Error message appears during deletion | Check database is accessible, try again |
| Success message is truncated | It auto-dismisses after 4 seconds |

## FAQ

**Q: Can I undo a deletion?**  
A: No, deletion is permanent and cannot be undone. The data is permanently removed from the database.

**Q: What happens if deletion fails halfway through?**  
A: If deletion fails at any point, the entire operation is rolled back and no data is deleted.

**Q: Can I delete multiple datasets at once?**  
A: Currently, you must delete datasets one at a time. Future versions may support bulk deletion.

**Q: Will deleting a dataset affect my backtest results?**  
A: No, backtest results are stored separately from the datasets. Deleting a dataset only affects the availability of that data for future analysis.

**Q: Can I delete a dataset that's currently selected?**  
A: Yes, but the selection will be automatically cleared after deletion.

## Performance Considerations

- **Deletion time depends on dataset size**
  - Small datasets (<1000 rows): < 1 second
  - Medium datasets (1000-100K rows): 1-5 seconds
  - Large datasets (100K+ rows): 5+ seconds
- **Deletion is non-blocking** - UI remains responsive
- **No impact on other datasets** - Only the selected dataset is affected
