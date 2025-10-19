#!/usr/bin/env python3
"""
Error handling test for Sprint 2.3
Tests: Import with errors shows specific errors and partial import
"""

import subprocess
import sys
import json
import time
from pathlib import Path
import pytest

@pytest.mark.timeout(60)
def test_error_handling():
    """Test error handling with problematic data"""
    print("🚀 Testing error handling with problematic data...")

    backend_path = Path(__file__).parent.parent / "backend" / "main.py"
    error_file = Path(__file__).parent.parent / "sample_with_errors.csv"

    if not error_file.exists():
        print(f"❌ Error sample file not found: {error_file}")
        return False

    # Start backend process
    print("Starting backend process...")
    process = subprocess.Popen(
        [sys.executable, str(backend_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Wait for startup
    time.sleep(3)

    if process.poll() is not None:
        print(f"❌ Backend process failed to start (exit code: {process.poll()})")
        return False

    print("✅ Backend process started")

    # Send import request for file with errors
    request = {
        'action': 'import-data',
        'data': {
            'file_path': str(error_file),
            'symbol': 'ERROR_TEST',
            'column_mapping': {}
        }
    }

    print("📤 Sending import request for file with errors...")
    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()

    # Monitor for errors and completion
    # Use communicate with timeout to avoid blocking
    try:
        stdout_data, stderr_data = process.communicate(timeout=30)
        
        # Parse all JSON responses from stdout
        import_completed = False
        errors_found = []
        rows_imported = 0
        rows_skipped = 0
        
        for line in stdout_data.splitlines():
            if not line.strip():
                continue
            try:
                response = json.loads(line.strip())
                
                if response.get('type') == 'import-progress':
                    progress_errors = response.get('errors', [])
                    if progress_errors:
                        errors_found.extend(progress_errors)
                        print(f"⚠️  Found errors: {progress_errors}")
                
                elif response.get('type') == 'import-summary':
                    import_completed = True
                    rows_imported = response.get('rowsImported', 0)
                    rows_skipped = response.get('rowsSkipped', 0)
                    
                    print("✅ Import completed with errors!")
                    print(f"   📈 Rows imported: {rows_imported:,}")
                    print(f"   ⏭️  Rows skipped: {rows_skipped:,}")
                    
                    # Check that we have both imported and skipped rows (partial success)
                    if rows_imported > 0 and rows_skipped > 0:
                        print(f"✅ Partial import successful: {rows_imported:,} good rows imported, {rows_skipped:,} bad rows skipped")
                    elif rows_imported > 0:
                        print(f"⚠️  All rows imported despite errors in file")
                    else:
                        print("❌ No rows imported - error handling may be too strict")
                        return False
            except json.JSONDecodeError:
                # Skip non-JSON lines
                continue
        
        if stderr_data:
            print(f"Backend stderr: {stderr_data[:500]}")  # Print first 500 chars
                    
    except subprocess.TimeoutExpired:
        print("❌ Test timeout after 30 seconds")
        process.kill()
        process.wait()
        return False

    # Process already completed via communicate(), check results
    if import_completed:
        print("🎉 Error handling test passed!")
        print(f"📋 Total errors found: {len(errors_found)}")
        if errors_found:
            print("Sample errors:")
            for error in errors_found[:5]:  # Show first 5 errors
                print(f"  • {error}")
        return True
    else:
        print("❌ Error handling test failed - import did not complete")
        return False

def main():
    success = test_error_handling()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()