#!/usr/bin/env python3
"""
Debug preview functionality
"""

import subprocess
import sys
import json
import time
from pathlib import Path

def test_preview_functionality():
    """Test the preview functionality directly"""
    print("🔍 Testing preview functionality...")

    backend_path = Path(__file__).parent.parent / "backend" / "main.py"
    test_file = Path(__file__).parent.parent / "large_sample.csv"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"Testing preview for: {test_file}")

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

    # Send preview request
    request = {
        'action': 'preview-file',
        'data': {
            'file_path': str(test_file)
        }
    }

    print("📤 Sending preview request...")
    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()

    # Read response
    response = process.stdout.readline().strip()
    print(f"📥 Raw response: {response}")

    try:
        result = json.loads(response)
        print(f"📋 Parsed response: {json.dumps(result, indent=2)}")

        if 'error' in result:
            print(f"❌ Preview failed: {result['error']}")
            return False
        else:
            print("✅ Preview successful!")
            print(f"   📊 Columns: {result.get('columns', [])}")
            print(f"   📈 Total rows: {result.get('rows_total', 0)}")
            print(f"   👀 Preview rows: {len(result.get('preview', []))}")
            return True

    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse response as JSON: {e}")
        return False
    finally:
        process.terminate()
        process.wait(timeout=5)

if __name__ == "__main__":
    test_preview_functionality()