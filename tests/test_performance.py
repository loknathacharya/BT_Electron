#!/usr/bin/env python3
"""
Performance test for Sprint 2.3
Tests: Import 100k rows in under 30 seconds
"""

import subprocess
import sys
import json
import time
from pathlib import Path
import pytest

@pytest.mark.timeout(120)
def test_large_import_performance():
    """Test importing 100k rows meets performance requirements"""
    print("🚀 Testing large file import performance...")

    backend_path = Path(__file__).parent.parent / "backend" / "main.py"
    large_file = Path(__file__).parent.parent / "large_sample.csv"

    if not large_file.exists():
        print(f"❌ Large sample file not found: {large_file}")
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

    # Send import request
    start_time = time.time()

    request = {
        'action': 'import-data',
        'data': {
            'file_path': str(large_file),
            'symbol': 'PERF_TEST',
            'column_mapping': {}
        }
    }

    print("📤 Sending import request...")
    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()

    # Monitor progress and measure total time
    import_completed = False
    last_progress = 0
    
    # Add timeout to prevent test from hanging
    loop_start_time = time.time()
    timeout_seconds = 90

    while True:
        if process.poll() is not None:
            print("❌ Backend process terminated unexpectedly")
            break
        
        # Check timeout
        if time.time() - loop_start_time > timeout_seconds:
            print(f"❌ Test timeout after {timeout_seconds} seconds")
            process.terminate()
            return False

        line = process.stdout.readline()
        if not line:
            # No data available, short sleep to avoid busy-wait
            time.sleep(0.1)
            continue

        try:
            response = json.loads(line.strip())
            response_time = time.time() - start_time

            if response.get('type') == 'import-progress':
                progress = response.get('progress', 0)
                if progress > last_progress:
                    print(f"📊 Progress: {progress}% ({response.get('currentRow', 0)}/{response.get('totalRows', 0)} rows) - {response_time:.1f}s")
                    last_progress = progress

            elif response.get('type') == 'import-summary':
                import_completed = True
                total_time = response_time
                rows_imported = response.get('rowsImported', 0)
                rows_skipped = response.get('rowsSkipped', 0)

                print("✅ Import completed!")
                print(f"   📈 Rows imported: {rows_imported:,}")
                print(f"   ⏭️  Rows skipped: {rows_skipped:,}")
                print(f"   ⏱️  Total time: {total_time:.2f}s")

                # Check performance requirements
                if total_time < 30.0:
                    print(f"✅ Performance target met: {total_time:.2f}s < 30s")
                else:
                    print(f"❌ Performance target missed: {total_time:.2f}s >= 30s")
                    return False

                if rows_imported >= 99000:  # Allow for some validation failures
                    print(f"✅ Import efficiency good: {rows_imported:,} rows imported")
                else:
                    print(f"⚠️  Import efficiency low: only {rows_imported:,} rows imported")
                    return False

                break

        except json.JSONDecodeError:
            # Skip non-JSON lines (likely startup messages)
            continue

    # Clean up
    process.terminate()
    process.wait(timeout=5)

    if import_completed:
        print("🎉 Performance test passed!")
        return True
    else:
        print("❌ Performance test failed - import did not complete")
        return False

def main():
    success = test_large_import_performance()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()