#!/usr/bin/env python3
"""
Sprint 2.3 Import Validation Tests
Tests: Full import process, validation rules, database storage
"""

import subprocess
import sys
import os
import json
import time
import sqlite3
import pandas as pd
from pathlib import Path
import tempfile
import csv

class ImportValidationTester:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.test_data_dir = Path(__file__).parent.parent

    def log(self, message, success=True):
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
        if not success:
            self.failed += 1
        else:
            self.passed += 1

    def run(self):
        print("🚀 Starting Sprint 2.3 Import Validation Tests...\n")

        # Test 1: Test data files exist
        self.test_test_files_exist()

        # Test 2: Backend can process large file
        self.test_large_file_processing()

        # Test 3: Error handling with problematic data
        self.test_error_handling()

        # Test 4: Database storage verification
        self.test_database_storage()

        # Test 5: Column mapping functionality
        self.test_column_mapping()

        # Test 6: Performance benchmark
        self.test_performance_benchmark()

        # Summary
        print(f"\n📊 Test Summary: {self.passed} passed, {self.failed} failed")

        if self.failed == 0:
            print("🎉 All import validation tests passed! Sprint 2.3 requirements met.")
            return True
        else:
            print("💥 Some import validation tests failed. Please check the implementation.")
            return False

    def test_test_files_exist(self):
        """Test that required test files exist"""
        large_file = self.test_data_dir / "large_sample.csv"
        error_file = self.test_data_dir / "sample_with_errors.csv"

        if large_file.exists():
            self.log(f"Large sample file exists: {large_file}")
            # Check file size (should be > 100k rows)
            with open(large_file, 'r') as f:
                row_count = sum(1 for _ in f) - 1  # -1 for header
                if row_count >= 100000:
                    self.log(f"Large file has sufficient rows: {row_count}")
                else:
                    self.log(f"Large file has insufficient rows: {row_count}", False)
        else:
            self.log(f"Large sample file not found: {large_file}", False)

        if error_file.exists():
            self.log(f"Error sample file exists: {error_file}")
        else:
            self.log(f"Error sample file not found: {error_file}", False)

    def test_large_file_processing(self):
        """Test processing of large CSV file"""
        try:
            # Test the backend preview functionality
            backend_path = Path(__file__).parent.parent / "backend" / "main.py"

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
            time.sleep(2)

            if process.poll() is None:
                # Send preview request
                request = {
                    'action': 'preview-file',
                    'data': {
                        'file_path': str(self.test_data_dir / "large_sample.csv")
                    }
                }

                process.stdin.write(json.dumps(request) + '\n')
                process.stdin.flush()

                # Read response
                response = process.stdout.readline().strip()
                result = json.loads(response)

                if 'error' not in result:
                    self.log(f"Large file preview successful: {result.get('rows_total', 0)} rows")
                else:
                    self.log(f"Large file preview failed: {result['error']}", False)

                process.terminate()
                process.wait(timeout=5)
            else:
                self.log(f"Backend process failed to start for large file test", False)

        except Exception as e:
            self.log(f"Large file processing test failed: {e}", False)

    def test_error_handling(self):
        """Test error handling with problematic data"""
        try:
            backend_path = Path(__file__).parent.parent / "backend" / "main.py"

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
            time.sleep(2)

            if process.poll() is None:
                # Send import request for file with errors
                request = {
                    'action': 'import-data',
                    'data': {
                        'file_path': str(self.test_data_dir / "sample_with_errors.csv"),
                        'symbol': 'TEST_ERROR',
                        'column_mapping': {}
                    }
                }

                process.stdin.write(json.dumps(request) + '\n')
                process.stdin.flush()

                # Read response
                response = process.stdout.readline().strip()
                result = json.loads(response)

                if 'error' not in result:
                    # Check if some rows were imported and some skipped
                    rows_imported = result.get('rowsImported', 0)
                    rows_skipped = result.get('rowsSkipped', 0)

                    if rows_imported > 0 and rows_skipped > 0:
                        self.log(f"Error handling works: {rows_imported} imported, {rows_skipped} skipped")
                    elif rows_imported > 0:
                        self.log(f"Partial import successful: {rows_imported} rows imported")
                    else:
                        self.log("No rows imported from error file", False)
                else:
                    self.log(f"Error file import failed: {result['error']}", False)

                process.terminate()
                process.wait(timeout=5)
            else:
                self.log(f"Backend process failed to start for error handling test", False)

        except Exception as e:
            self.log(f"Error handling test failed: {e}", False)

    def test_database_storage(self):
        """Test database storage functionality"""
        try:
            # Check if database exists and has the right structure
            db_path = Path.home() / ".byod_backtesting" / "trading_data.db"

            if not db_path.exists():
                self.log("Database file not found for storage test", False)
                return

            with sqlite3.connect(db_path) as conn:
                # Check tables exist
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [table[0] for table in cursor.fetchall()]

                required_tables = ['price_data', 'strategies', 'backtest_results', 'trades']
                if all(table in tables for table in required_tables):
                    self.log(f"All required tables exist: {required_tables}")
                else:
                    self.log(f"Missing tables: {[t for t in required_tables if t not in tables]}", False)

                # Check if we can query price_data
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM price_data")
                    count = cursor.fetchone()[0]
                    self.log(f"Database storage working: {count} price data records found")
                except sqlite3.Error as e:
                    self.log(f"Cannot query price_data table: {e}", False)

        except Exception as e:
            self.log(f"Database storage test failed: {e}", False)

    def test_column_mapping(self):
        """Test column mapping functionality"""
        try:
            # Create a test CSV with different column names
            test_csv_content = """Timestamp,Open_Price,High_Price,Low_Price,Close_Price,Vol
2023-01-01,100.0,105.0,99.0,102.5,1000
2023-01-02,102.5,107.0,101.0,105.0,1200
"""

            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(test_csv_content)
                temp_file = f.name

            try:
                backend_path = Path(__file__).parent.parent / "backend" / "main.py"

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
                time.sleep(2)

                if process.poll() is None:
                    # Test column mapping
                    column_mapping = {
                        'timestamp': 'Timestamp',
                        'open': 'Open_Price',
                        'high': 'High_Price',
                        'low': 'Low_Price',
                        'close': 'Close_Price',
                        'volume': 'Vol'
                    }

                    # Send import request with column mapping
                    request = {
                        'action': 'import-data',
                        'data': {
                            'file_path': temp_file,
                            'symbol': 'COLUMN_TEST',
                            'column_mapping': column_mapping
                        }
                    }

                    process.stdin.write(json.dumps(request) + '\n')
                    process.stdin.flush()

                    # Read response
                    response = process.stdout.readline().strip()
                    result = json.loads(response)

                    if 'error' not in result:
                        rows_imported = result.get('rowsImported', 0)
                        if rows_imported > 0:
                            self.log(f"Column mapping works: {rows_imported} rows imported with mapping")
                        else:
                            self.log("Column mapping test: no rows imported", False)
                    else:
                        self.log(f"Column mapping failed: {result['error']}", False)

                    process.terminate()
                    process.wait(timeout=5)
                else:
                    self.log(f"Backend process failed to start for column mapping test", False)

            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        except Exception as e:
            self.log(f"Column mapping test failed: {e}", False)

    def test_performance_benchmark(self):
        """Test performance with large file"""
        try:
            large_file = self.test_data_dir / "large_sample.csv"

            if not large_file.exists():
                self.log("Large file not found for performance test", False)
                return

            # Get file size for reference
            file_size = large_file.stat().st_size / (1024 * 1024)  # MB
            self.log(f"Performance test file size: {file_size:.1f} MB")

            # Simple performance check - read file and count rows
            start_time = time.time()
            with open(large_file, 'r') as f:
                row_count = sum(1 for _ in f) - 1  # -1 for header

            read_time = time.time() - start_time

            if row_count >= 100000:
                self.log(f"File reading performance: {row_count} rows in {read_time:.2f}s")
                if read_time < 5.0:  # Should be able to read 100k rows in under 5 seconds
                    self.log("File reading performance meets requirements")
                else:
                    self.log(f"File reading performance slow: {read_time:.2f}s", False)
            else:
                self.log(f"Insufficient rows for performance test: {row_count}", False)

        except Exception as e:
            self.log(f"Performance benchmark test failed: {e}", False)

def main():
    tester = ImportValidationTester()
    success = tester.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()