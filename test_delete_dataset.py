#!/usr/bin/env python3
"""
Test script for dataset deletion functionality
Tests the delete_dataset() method in backend/main.py
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from backend.main import DatabaseService
except ImportError:
    print("❌ Error: Could not import DatabaseService")
    sys.exit(1)

def print_test(title):
    """Print test section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def create_test_dataset(db_service, dataset_name="Test_Dataset"):
    """Create a test dataset with sample data"""
    try:
        # Connect to market database
        with sqlite3.connect(db_service.market_db_path) as conn:
            # Insert test dataset metadata
            symbols = ["AAPL", "GOOGL", "MSFT"]
            conn.execute('''
                INSERT OR REPLACE INTO datasets 
                (name, description, symbols_json, date_range_start, date_range_end, 
                 symbol_count, total_rows, created_at, last_updated_at_ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dataset_name,
                "Test dataset for deletion testing",
                json.dumps(symbols),
                int(datetime(2024, 1, 1).timestamp()),
                int(datetime(2024, 12, 31).timestamp()),
                len(symbols),
                300,  # 100 rows per symbol
                int(datetime.now().timestamp()),
                int(datetime.now().timestamp())
            ))
            
            # Insert sample price data
            date = datetime(2024, 1, 1)
            for symbol in symbols:
                for i in range(100):
                    date_ts = int(date.timestamp())
                    conn.execute('''
                        INSERT INTO price_data 
                        (symbol, timestamp, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        date_ts,
                        date.strftime('%Y-%m-%d'),
                        100.0 + i,
                        105.0 + i,
                        98.0 + i,
                        102.0 + i,
                        1000000
                    ))
                    date += timedelta(days=1)
            
            conn.commit()
            return True
    except Exception as e:
        print_error(f"Failed to create test dataset: {e}")
        return False

def verify_dataset_exists(db_service, dataset_name):
    """Verify dataset exists in database"""
    try:
        with sqlite3.connect(db_service.market_db_path) as conn:
            cursor = conn.execute(
                'SELECT id, name FROM datasets WHERE name = ?',
                (dataset_name,)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        print_error(f"Failed to verify dataset: {e}")
        return False

def count_price_data(db_service, symbol):
    """Count price data rows for a symbol"""
    try:
        with sqlite3.connect(db_service.market_db_path) as conn:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM price_data WHERE symbol = ?',
                (symbol,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        print_error(f"Failed to count price data: {e}")
        return 0

def test_dataset_deletion():
    """Main test function"""
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*10 + "🗑️  DELETE DATASET FUNCTIONALITY TEST" + " "*12 + "║")
    print("╚" + "═"*58 + "╝")
    
    # Initialize database service
    print_test("Initializing Database Service")
    try:
        db_service = DatabaseService()
        print_success("Database service initialized")
        print_info(f"Market DB: {db_service.market_db_path}")
        print_info(f"User DB: {db_service.user_db_path}")
    except Exception as e:
        print_error(f"Failed to initialize database service: {e}")
        return False
    
    # Test 1: Create test dataset
    print_test("Test 1: Create Test Dataset")
    dataset_name = "DELETE_TEST_DATASET"
    if create_test_dataset(db_service, dataset_name):
        print_success(f"Created test dataset: {dataset_name}")
    else:
        print_error("Failed to create test dataset")
        return False
    
    # Verify dataset exists
    print_test("Test 2: Verify Dataset Exists Before Deletion")
    if verify_dataset_exists(db_service, dataset_name):
        print_success(f"✅ Dataset '{dataset_name}' exists")
    else:
        print_error(f"Dataset '{dataset_name}' does not exist")
        return False
    
    # Count price data before deletion
    print_test("Test 3: Count Price Data Before Deletion")
    symbols = ["AAPL", "GOOGL", "MSFT"]
    initial_counts = {}
    total_rows = 0
    for symbol in symbols:
        count = count_price_data(db_service, symbol)
        initial_counts[symbol] = count
        total_rows += count
        print_info(f"  {symbol}: {count} rows")
    print_success(f"Total price data rows: {total_rows}")
    
    if total_rows == 0:
        print_error("No price data found - test cannot continue")
        return False
    
    # Test deletion
    print_test("Test 4: Delete Dataset")
    result = db_service.delete_dataset(dataset_name)
    
    if result.get('success'):
        print_success(f"Deletion successful: {result.get('message')}")
    else:
        print_error(f"Deletion failed: {result.get('error')}")
        return False
    
    # Test 5: Verify dataset is deleted
    print_test("Test 5: Verify Dataset is Deleted")
    if not verify_dataset_exists(db_service, dataset_name):
        print_success(f"✅ Dataset '{dataset_name}' successfully removed from database")
    else:
        print_error(f"❌ Dataset '{dataset_name}' still exists - deletion failed!")
        return False
    
    # Test 6: Verify price data is deleted
    print_test("Test 6: Verify Price Data is Deleted")
    all_deleted = True
    for symbol in symbols:
        count = count_price_data(db_service, symbol)
        if count == 0:
            print_success(f"✅ {symbol}: All {initial_counts[symbol]} rows deleted")
        else:
            print_error(f"❌ {symbol}: {count} rows still remain (should be 0)")
            all_deleted = False
    
    if not all_deleted:
        return False
    
    # Test 7: Test deletion of non-existent dataset
    print_test("Test 7: Test Deletion of Non-existent Dataset")
    result = db_service.delete_dataset("NON_EXISTENT_DATASET")
    
    if not result.get('success') and result.get('error'):
        print_success(f"✅ Correctly rejected deletion of non-existent dataset")
        print_info(f"   Error message: {result.get('error')}")
    else:
        print_error("❌ Should have rejected deletion of non-existent dataset")
        return False
    
    # Test 8: Test with another dataset (ensure no side effects)
    print_test("Test 8: Create Another Dataset and Verify Isolation")
    another_dataset = "ISOLATION_TEST_DATASET"
    if create_test_dataset(db_service, another_dataset):
        print_success(f"Created second test dataset: {another_dataset}")
        
        # Verify it exists
        if verify_dataset_exists(db_service, another_dataset):
            print_success(f"✅ Second dataset exists and is independent")
        else:
            print_error("Second dataset not found")
            return False
    else:
        print_error("Failed to create second test dataset")
        return False
    
    # Clean up the second dataset
    print_test("Test 9: Clean Up Second Dataset")
    result = db_service.delete_dataset(another_dataset)
    if result.get('success'):
        print_success(f"Successfully cleaned up: {another_dataset}")
    else:
        print_error(f"Failed to clean up: {result.get('error')}")
        return False
    
    return True

def print_summary(success):
    """Print test summary"""
    print("\n")
    print("╔" + "═"*58 + "╗")
    if success:
        print("║" + " "*18 + "🎉 ALL TESTS PASSED! 🎉" + " "*14 + "║")
    else:
        print("║" + " "*15 + "❌ SOME TESTS FAILED ❌" + " "*16 + "║")
    print("╚" + "═"*58 + "╝")
    print()

if __name__ == "__main__":
    try:
        success = test_dataset_deletion()
        print_summary(success)
        sys.exit(0 if success else 1)
    except Exception as e:
        print_error(f"Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        print_summary(False)
        sys.exit(1)
