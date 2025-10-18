#!/usr/bin/env python3
"""
Test script for incremental update functionality
"""
import os
import sys
import tempfile
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import json

# Add the backend directory to the path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

# Import the classes directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location("main", os.path.join(backend_path, "main.py"))
if spec is None:
    raise ImportError(f"Could not load main module from {backend_path}")
main_module = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise ImportError(f"Could not load main module from {backend_path}")
spec.loader.exec_module(main_module)

DatabaseService = main_module.DatabaseService
DataValidationPipeline = main_module.DataValidationPipeline

def create_test_data(start_date, end_date, symbol='TEST'):
    """Create test OHLCV data for the given date range"""
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    data = []
    
    for i, date in enumerate(dates):
        # Generate realistic price data
        base_price = 100 + i * 0.1
        data.append({
            'Date': date,
            'Open': base_price + (i % 3) - 1,
            'High': base_price + 2,
            'Low': base_price - 1,
            'Close': base_price + (i % 2),
            'Volume': 1000000 + i * 10000,
            'Ticker': symbol
        })
    
    return pd.DataFrame(data)

def test_incremental_updates():
    """Test the incremental update functionality"""
    print("Testing incremental update functionality...")
    
    # Create a temporary database
    temp_dir = tempfile.mkdtemp()
    try:
        db_service = DatabaseService(db_dir=temp_dir)
        
        # Test 1: Initial import (should import all data)
        print("\n=== Test 1: Initial Import ===")
        initial_data = create_test_data('2023-01-01', '2023-01-10', 'TEST')
        
        # Convert to the format expected by the database
        initial_data['Date'] = (initial_data['Date'].astype('int64') // 10**9).astype(int)
        
        print("DEBUG: About to insert initial data...")
        # Insert initial data
        with sqlite3.connect(db_service.market_db_path) as conn:
            print("DEBUG: Database connection opened for initial data insertion")
            for _, row in initial_data.iterrows():
                conn.execute('''
                    INSERT OR REPLACE INTO price_data
                    (symbol, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Ticker'], row['Date'], row['Open'], row['High'],
                    row['Low'], row['Close'], row['Volume']
                ))
            print("DEBUG: Initial data inserted, connection should auto-close")
        
        print("DEBUG: Initial data connection closed")
        
        # Update symbols metadata after getting the range
        range1 = db_service.get_symbol_data_range('TEST')
        print(f"DEBUG: Got range1: {range1}")
        with sqlite3.connect(db_service.market_db_path) as conn:
            print("DEBUG: Database connection opened for symbols metadata update")
            conn.execute('''
                INSERT OR REPLACE INTO symbols
                (symbol, data_start, data_end, total_rows, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                'TEST', range1['min_timestamp'], range1['max_timestamp'],
                range1['total_rows'], int(datetime.now().timestamp())
            ))
            print("DEBUG: Symbols metadata updated, connection should auto-close")
        
        print("DEBUG: Symbols metadata connection closed")
        
        # Verify initial data
        range1 = db_service.get_symbol_data_range('TEST')
        print(f"Initial data range: {range1}")
        assert range1['has_data'] == True
        assert range1['total_rows'] == 10
        
        # Test 2: Incremental update with new data only
        print("\n=== Test 2: Incremental Update (New Data Only) ===")
        new_data = create_test_data('2023-01-11', '2023-01-15', 'TEST')
        new_data['Date'] = (new_data['Date'].astype('int64') // 10**9).astype(int)
        
        # Test the filtering function
        filtered_new, filtered_existing = db_service.filter_incremental_data(new_data, 'TEST')
        print(f"New data rows: {len(filtered_new)}")
        print(f"Existing data rows: {len(filtered_existing)}")
        
        assert len(filtered_new) == 5  # All new dates
        assert len(filtered_existing) == 0  # No overlap
        
        print("DEBUG: About to insert new data...")
        # Insert the new data
        with sqlite3.connect(db_service.market_db_path) as conn:
            print("DEBUG: Database connection opened for new data insertion")
            for _, row in filtered_new.iterrows():
                conn.execute('''
                    INSERT OR REPLACE INTO price_data
                    (symbol, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Ticker'], row['Date'], row['Open'], row['High'],
                    row['Low'], row['Close'], row['Volume']
                ))
            print("DEBUG: New data inserted, connection should auto-close")
        
        print("DEBUG: New data connection closed")
        
        # Update symbols metadata after getting the new range
        print("DEBUG: About to get range2...")
        range2 = db_service.get_symbol_data_range('TEST')
        print(f"DEBUG: Got range2: {range2}")
        with sqlite3.connect(db_service.market_db_path) as conn:
            print("DEBUG: Database connection opened for symbols metadata update (round 2)")
            conn.execute('''
                INSERT OR REPLACE INTO symbols
                (symbol, data_start, data_end, total_rows, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                'TEST', range1['min_timestamp'], range2['max_timestamp'],
                range2['total_rows'], int(datetime.now().timestamp())
            ))
            print("DEBUG: Symbols metadata updated (round 2), connection should auto-close")
        
        print("DEBUG: Symbols metadata connection (round 2) closed")
        
        # Verify updated data
        range2 = db_service.get_symbol_data_range('TEST')
        print(f"Updated data range: {range2}")
        assert range2['has_data'] == True
        assert range2['total_rows'] == 15  # 10 + 5
        
        # Test 3: Incremental update with overlapping data
        print("\n=== Test 3: Incremental Update (With Overlap) ===")
        mixed_data = create_test_data('2023-01-12', '2023-01-20', 'TEST')
        mixed_data['Date'] = (mixed_data['Date'].astype('int64') // 10**9).astype(int)
        
        # Test the filtering function
        filtered_mixed, filtered_overlap = db_service.filter_incremental_data(mixed_data, 'TEST')
        print(f"New data rows: {len(filtered_mixed)}")
        print(f"Existing data rows: {len(filtered_overlap)}")
        
        # Debug: Print the actual dates to understand the filtering
        print("New data dates:", filtered_mixed['Date'].tolist() if len(filtered_mixed) > 0 else "None")
        print("Overlap data dates:", filtered_overlap['Date'].tolist() if len(filtered_overlap) > 0 else "None")
        
        # Should have 5 new rows (Jan 16-20) and 4 existing rows (Jan 12-15)
        # The current implementation only includes data outside the existing range
        assert len(filtered_mixed) == 5  # Jan 16-20
        assert len(filtered_overlap) == 4  # Jan 12-15 (one date might be missing)
        
        # Test 4: Full import mode (should import all data)
        print("\n=== Test 4: Full Import Mode ===")
        full_data = create_test_data('2023-01-05', '2023-01-08', 'TEST2')
        full_data['Date'] = (full_data['Date'].astype('int64') // 10**9).astype(int)
        
        # Test the filtering function with incremental=False
        filtered_full, _ = db_service.filter_incremental_data(full_data, 'TEST2')
        print(f"New data rows: {len(filtered_full)}")
        
        # Should have all 4 rows since it's a new symbol
        assert len(filtered_full) == 4
        
        # Test 5: Get import summary
        print("\n=== Test 5: Import Summary ===")
        summary = db_service.get_import_summary('TEST')
        print(f"Import summary: {summary}")
        assert summary['symbol'] == 'TEST'
        assert summary['total_rows'] == 15
        assert summary['data_start'] is not None
        assert summary['data_end'] is not None
        
        print("\n✅ All incremental update tests passed!")
        
    finally:
        # Clean up - need to handle SQLite WAL files properly
        print("Cleaning up temporary directory...")
        try:
            # Small delay to ensure SQLite releases all locks
            import time
            time.sleep(0.1)
            
            # Remove WAL and SHM files first if they exist
            market_db = os.path.join(temp_dir, 'market_data.db')
            wal_file = market_db + '-wal'
            shm_file = market_db + '-shm'
            
            for file in [wal_file, shm_file]:
                if os.path.exists(file):
                    try:
                        os.unlink(file)
                        print(f"Removed {os.path.basename(file)}")
                    except Exception as e:
                        print(f"Warning: Could not remove {os.path.basename(file)}: {e}")
            
            # Now remove the main database file
            if os.path.exists(market_db):
                try:
                    os.unlink(market_db)
                    print(f"Removed {os.path.basename(market_db)}")
                except Exception as e:
                    print(f"Warning: Could not remove {os.path.basename(market_db)}: {e}")
            
            # Finally, remove the entire directory
            import shutil
            shutil.rmtree(temp_dir)
            print("✅ Cleanup completed successfully!")
            
        except Exception as e:
            print(f"Warning: Cleanup had issues: {e}")
            # Don't fail the test if cleanup has issues

def test_validation_pipeline():
    """Test the data validation pipeline"""
    print("\nTesting data validation pipeline...")
    
    validator = DataValidationPipeline()
    
    # Test valid data
    valid_data = create_test_data('2023-01-01', '2023-01-05', 'TEST')
    is_valid, errors, warnings = validator.validate_dataframe(valid_data)
    print(f"Valid data validation: {is_valid}, errors: {len(errors)}, warnings: {len(warnings)}")
    assert is_valid == True
    assert len(errors) == 0
    
    # Test invalid data (missing required columns)
    invalid_data = valid_data.drop(columns=['Open'])
    is_valid, errors, warnings = validator.validate_dataframe(invalid_data)
    print(f"Invalid data validation: {is_valid}, errors: {len(errors)}, warnings: {len(warnings)}")
    assert is_valid == False
    assert len(errors) > 0
    
    print("✅ Data validation pipeline tests passed!")

if __name__ == '__main__':
    try:
        test_incremental_updates()
        test_validation_pipeline()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)