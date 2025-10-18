#!/usr/bin/env python3
"""
Test preview with different column format
"""

import subprocess
import sys
import json
import time
from pathlib import Path

def test_different_format_preview():
    """Test preview with compound column names"""
    print("🔍 Testing preview with different column format...")

    backend_path = Path(__file__).parent.parent / "backend" / "main.py"
    test_file = Path(__file__).parent.parent / "test_different_format.csv"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"Testing preview for: {test_file}")

    # Start backend process
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

    # Send preview request
    request = {
        'action': 'preview-file',
        'data': {
            'file_path': str(test_file)
        }
    }

    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()

    # Read response
    response = process.stdout.readline().strip()

    try:
        result = json.loads(response)

        if 'error' in result:
            print(f"❌ Preview failed: {result['error']}")
            return False
        else:
            print("✅ Preview successful!")
            print(f"   📊 Columns: {result.get('columns', [])}")
            print(f"   📈 Total rows: {result.get('rows_total', 0)}")
            return True

    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse response as JSON: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

if __name__ == "__main__":
    test_different_format_preview()