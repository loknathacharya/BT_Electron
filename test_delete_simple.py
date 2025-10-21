#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test for dataset deletion functionality
"""
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backend.main import DatabaseService

print("\n" + "="*70)
print("DELETE DATASET FUNCTIONALITY TEST")
print("="*70)

# Initialize database service
print("\n[*] Initializing database service...")
db_service = DatabaseService()
print("[+] Database service ready")

# Check schema
print("\n" + "="*70)
print("TABLE SCHEMA VERIFICATION")
print("="*70)

print("\n[*] price_data columns:")
with sqlite3.connect(db_service.market_db_path) as conn:
    cursor = conn.execute("PRAGMA table_info(price_data)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"    - {col[1]:20} ({col[2]})")

print("\n[*] datasets columns:")
with sqlite3.connect(db_service.market_db_path) as conn:
    cursor = conn.execute("PRAGMA table_info(datasets)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"    - {col[1]:30} ({col[2]})")

# Get existing datasets
print("\n" + "="*70)
print("EXISTING DATASETS (First 3)")
print("="*70)

result = db_service.get_all_datasets()
if result.get('datasets'):
    for i, ds in enumerate(result['datasets'][:3], 1):
        print(f"\n[{i}] {ds['name']}")
        print(f"    Symbols: {ds['symbol_count']}")
        print(f"    Rows: {ds['total_rows']:,}")
        print(f"    Created: {datetime.fromtimestamp(ds['created_at']).strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("No datasets found")
    sys.exit(0)

# Count total rows before deletion
total_before = result['count']
print(f"\n[*] Total datasets in database: {total_before}")

# Test deletion
print("\n" + "="*70)
print("DELETION TEST")
print("="*70)

if result.get('datasets') and len(result['datasets']) > 0:
    test_dataset = result['datasets'][0]
    print(f"\n[*] Attempting to delete: {test_dataset['name']}")
    print(f"    - Symbols: {test_dataset['symbol_count']}")
    print(f"    - Rows: {test_dataset['total_rows']:,}")
    print(f"    - ID: {test_dataset['id']}")
    
    # Delete the dataset
    print(f"\n[*] Calling delete_dataset()...")
    delete_result = db_service.delete_dataset(test_dataset['name'])
    
    if delete_result.get('success'):
        print(f"\n[+] DELETION SUCCESSFUL")
        print(f"    Message: {delete_result.get('message')}")
        
        # Verify it's gone
        print(f"\n[*] Verifying deletion...")
        verify_result = db_service.get_all_datasets()
        found = any(ds['name'] == test_dataset['name'] for ds in verify_result.get('datasets', []))
        
        if not found:
            print(f"[+] VERIFIED: Dataset no longer in database")
            print(f"[+] Datasets before: {total_before}")
            print(f"[+] Datasets after:  {verify_result['count']}")
        else:
            print(f"[!] ERROR: Dataset still exists in database!")
    else:
        print(f"\n[-] DELETION FAILED")
        print(f"    Error: {delete_result.get('error')}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")
