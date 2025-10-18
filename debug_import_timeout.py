#!/usr/bin/env python3
"""
Debug script to reproduce and diagnose the import timeout issue
"""

import subprocess
import sys
import json
import time
import os
from pathlib import Path

def test_import_timeout():
    """Test import process to identify timeout causes"""
    print("🚀 Starting import timeout diagnosis...")
    
    backend_path = Path(__file__).parent / "backend" / "main.py"
    test_files = [
        "sample_ohlc_data.csv",
        "sample_with_errors.csv", 
        "test_different_format.csv"
    ]
    
    # Find available test files
    available_files = []
    for file in test_files:
        if Path(file).exists():
            available_files.append(file)
    
    if not available_files:
        print("❌ No test files found. Looking for CSV files...")
        csv_files = list(Path(".").glob("*.csv"))
        if csv_files:
            available_files = [str(f) for f in csv_files]
        else:
            print("❌ No CSV files found in current directory")
            return False
    
    print(f"📁 Found test files: {available_files}")
    
    # Test each file
    for test_file in available_files:
        print(f"\n🔍 Testing file: {test_file}")
        
        # Start backend process
        print("Starting backend process...")
        process = subprocess.Popen(
            [sys.executable, str(backend_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent
        )
        
        # Wait for startup
        time.sleep(3)
        
        if process.poll() is not None:
            print(f"❌ Backend process failed to start (exit code: {process.poll()})")
            continue
        
        print("✅ Backend process started")
        
        # Send import request
        request = {
            'action': 'import-data',
            'data': {
                'file_path': str(Path(test_file).absolute()),
                'symbol': 'DEBUG_TEST',
                'column_mapping': {
                    'timestamp': 'Date',
                    'open': 'Open', 
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close'
                }
            }
        }
        
        print(f"📤 Sending import request for {test_file}...")
        print(f"Request details: {json.dumps(request, indent=2)}")
        
        if process.stdin:
            process.stdin.write(json.dumps(request) + '\n')
            process.stdin.flush()
        
        # Monitor output with detailed logging
        start_time = time.time()
        last_progress = 0
        import_completed = False
        error_occurred = False
        
        print("\n📊 Monitoring import process...")
        
        while True:
            # Check if process terminated
            if process.poll() is not None:
                elapsed = time.time() - start_time
                print(f"❌ Process terminated after {elapsed:.1f}s (exit code: {process.poll()})")
                error_occurred = True
                break
            
            # Read stdout
            if process.stdout:
                line = process.stdout.readline()
            else:
                line = ''
            if not line:
                time.sleep(0.1)  # Small delay to prevent busy waiting
                continue
                
            try:
                response = json.loads(line.strip())
                elapsed = time.time() - start_time
                
                if response.get('type') == 'import-progress':
                    progress = response.get('progress', 0)
                    current_row = response.get('currentRow', 0)
                    total_rows = response.get('totalRows', 0)
                    errors = response.get('errors', [])
                    
                    if progress != last_progress:
                        print(f"📈 Progress: {progress}% ({current_row}/{total_rows} rows) - {elapsed:.1f}s")
                        last_progress = progress
                    
                    if errors:
                        print(f"⚠️  Errors: {errors}")
                
                elif response.get('type') == 'import-summary':
                    import_completed = True
                    total_time = elapsed
                    rows_imported = response.get('rowsImported', 0)
                    rows_skipped = response.get('rowsSkipped', 0)
                    
                    print(f"✅ Import completed in {total_time:.2f}s!")
                    print(f"   📈 Rows imported: {rows_imported:,}")
                    print(f"   ⏭️  Rows skipped: {rows_skipped:,}")
                    break
                
                elif 'error' in response:
                    print(f"❌ Error response: {response}")
                    error_occurred = True
                    break
                    
            except json.JSONDecodeError as e:
                # Log non-JSON output that might be useful
                if line.strip():
                    print(f"📝 Raw output: {line.strip()}")
                continue
        
        # Check stderr for additional debugging info
        if process.poll() is None:
            if process.stderr:
                stderr_output = process.stderr.read()
            else:
                stderr_output = ''
            if stderr_output.strip():
                print(f"\n🔥 Stderr output:")
                print(stderr_output)
        
        # Clean up
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        if import_completed:
            print(f"🎉 Import of {test_file} completed successfully!")
        else:
            print(f"❌ Import of {test_file} failed or timed out")
        
        # Small delay between tests
        time.sleep(2)
    
    print("\n🏁 Import timeout diagnosis complete!")
    return True

if __name__ == "__main__":
    test_import_timeout()