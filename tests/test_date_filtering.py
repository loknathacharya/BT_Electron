
#!/usr/bin/env python3
"""
Test suite for date filtering functionality in the OHLCV data import system.
Tests both backend date filtering and frontend date handling.
"""

import pytest
import sqlite3
import tempfile
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = str(Path(__file__).parent.parent / 'backend')
sys.path.insert(0, backend_dir)

# Import the functions we need
import importlib.util
spec = importlib.util.spec_from_file_location("main", f"{backend_dir}/main.py")
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)

DatabaseService = main_module.DatabaseService
handle_request = main_module.handle_request

class TestDateFiltering:
    """Test suite for date filtering functionality"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        temp_dir = tempfile.mkdtemp()
        db_service = DatabaseService(temp_dir)
        
        # Create test data with known date ranges
        test_data = [
            # Symbol AAPL: 2023-01-01 to 2023-01-05
            ('AAPL', int(datetime(2023, 1, 1).timestamp()), 150.0, 152.0, 149.0, 151.0, 1000000),
            ('AAPL', int(datetime(2023, 1, 2).timestamp()), 151.0, 153.0, 150.0, 152.0, 1200000),
            ('AAPL', int(datetime(2023, 1, 3).timestamp()), 152.0, 154.0, 151.0, 153.0, 1100000),
            ('AAPL', int(datetime(2023, 1, 4).timestamp()), 153.0, 155.0, 152.0, 154.0, 1300000),
            ('AAPL', int(datetime(2023, 1, 5).timestamp()), 154.0, 156.0, 153.0, 155.0, 1400000),
            
            # Symbol MSFT: 2023-01-03 to 2023-01-07
            ('MSFT', int(datetime(2023, 1, 3).timestamp()), 300.0, 302.0, 299.0, 301.0, 800000),
            ('MSFT', int(datetime(2023, 1, 4).timestamp()), 301.0, 303.0, 300.0, 302.0, 900000),
            ('MSFT', int(datetime(2023, 1, 5).timestamp()), 302.0, 304.0, 301.0, 303.0, 850000),
            ('MSFT', int(datetime(2023, 1, 6).timestamp()), 303.0, 305.0, 302.0, 304.0, 950000),
            ('MSFT', int(datetime(2023, 1, 7).timestamp()), 304.0, 306.0, 303.0, 305.0, 1000000),
            
            # Symbol GOOGL: 2023-01-02 to 2023-01-04
            ('GOOGL', int(datetime(2023, 1, 2).timestamp()), 120.0, 122.0, 119.0, 121.0, 500000),
            ('GOOGL', int(datetime(2023, 1, 3).timestamp()), 121.0, 123.0, 120.0, 122.0, 550000),
            ('GOOGL', int(datetime(2023, 1, 4).timestamp()), 122.0, 124.0, 121.0, 123.0, 600000),
        ]
        
        # Insert test data
        with sqlite3.connect(db_service.market_db_path) as conn:
            conn.executemany('''
                INSERT OR REPLACE INTO price_data 
                (symbol, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', test_data)
            
            # Update symbols metadata
            symbols_data = [
                ('AAPL', 'Apple Inc.', int(datetime(2023, 1, 1).timestamp()), int(datetime(2023, 1, 5).timestamp()), 5, int(datetime.now().timestamp())),
                ('MSFT', 'Microsoft Corp.', int(datetime(2023, 1, 3).timestamp()), int(datetime(2023, 1, 7).timestamp()), 5, int(datetime.now().timestamp())),
                ('GOOGL', 'Alphabet Inc.', int(datetime(2023, 1, 2).timestamp()), int(datetime(2023, 1, 4).timestamp()), 3, int(datetime.now().timestamp())),
            ]
            
            conn.executemany('''
                INSERT OR REPLACE INTO symbols 
                (symbol, name, data_start, data_end, total_rows, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', symbols_data)
        
        yield db_service
        
        # Cleanup: properly close any open database connections
        try:
            # Close any open connections (SQLite on Windows can lock files)
            import gc
            gc.collect()  # Force garbage collection to close connection handles
            
            # Try to close databases explicitly if possible
            try:
                # SQLite may have open handles, force close
                db_conn_market = sqlite3.connect(db_service.market_db_path)
                db_conn_market.close()
                db_conn_user = sqlite3.connect(db_service.user_db_path)
                db_conn_user.close()
            except:
                pass
            
            # Give OS time to release file locks
            import time
            time.sleep(0.1)
        except:
            pass
        
        # Cleanup temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            # If still locked on Windows, try again after a brief wait
            import time
            time.sleep(0.5)
            try:
                shutil.rmtree(temp_dir)
            except:
                # If it still fails, leave it for OS cleanup
                pass
    
    def test_get_price_data_without_date_filter(self, temp_db):
        """Test getting price data without date filters"""
        request = {
            'action': 'get-price-data',
            'data': {
                'symbol': 'AAPL',
                'limit': 100,
                'offset': 0
            },
            'requestId': 'test-1'
        }
        
        response = handle_request(request, db_service_override=temp_db)

        assert 'data' in response
        assert len(response['data']) == 5  # All AAPL data
        assert all(item['symbol'] == 'AAPL' for item in response['data'])
        
        # Check dates are in correct order (newest first)
        dates = [datetime.fromtimestamp(item['timestamp']) for item in response['data']]
        assert dates == sorted(dates, reverse=True)
    
    def test_get_price_data_with_start_date_filter(self, temp_db):
        """Test getting price data with start date filter"""
        start_date = int(datetime(2023, 1, 3).timestamp())
        
        request = {
            'action': 'get-price-data',
            'data': {
                'symbol': 'AAPL',
                'limit': 100,
                'offset': 0,
                'start_date': start_date
            },
            'requestId': 'test-2'
        }
        
        response = handle_request(request, db_service_override=temp_db)

        assert 'data' in response
        assert len(response['data']) == 3  # Only data from Jan 3 onwards
        
        # Check all dates are after or equal to start date
        for item in response['data']:
            assert item['timestamp'] >= start_date
    
    def test_get_price_data_with_end_date_filter(self, temp_db):
        """Test getting price data with end date filter"""
        end_date = int(datetime(2023, 1, 3).timestamp())
        
        request = {
            'action': 'get-price-data',
            'data': {
                'symbol': 'AAPL',
                'limit': 100,
                'offset': 0,
                'end_date': end_date
            },
            'requestId': 'test-3'
        }
        
        response = handle_request(request, db_service_override=temp_db)

        assert 'data' in response
        assert len(response['data']) == 3  # Only data up to Jan 3
        
        # Check all dates are before or equal to end date
        for item in response['data']:
            assert item['timestamp'] <= end_date
    
    def test_get_price_data_with_date_range_filter(self, temp_db):
        """Test getting price data with both start and end date filters"""
        start_date = int(datetime(2023, 1, 2).timestamp())
        end_date = int(datetime(2023, 1, 4).timestamp())
        
        request = {
            'action': 'get-price-data',
            'data': {
                'symbol': 'AAPL',
                'limit': 100,
                'offset': 0,
                'start_date': start_date,
                'end_date': end_date
            },
            'requestId': 'test-4'
        }
        
        response = handle_request(request, db_service_override=temp_db)

        assert 'data' in response
        assert len(response['data']) == 3  # Data from Jan 2 to Jan 4
        
        # Check all dates are within the range
        for item in response['data']:
            assert start_date <= item['timestamp'] <= end_date
    
    def test_get_price_data_all_symbols_with_date_filter(self, temp_db):
        """Test getting price data for all symbols with date filter"""
        start_date = int(datetime(2023, 1, 3).timestamp())
        end_date = int(datetime(2023, 1, 5).timestamp())
        
        request = {
            'action': 'get-price-data',
            'data': {
                'symbol': 'ALL',
                'limit': 100,
                'offset': 0,
                'start_date': start_date,
                'end_date': end_date
            },
            'requestId': 'test-5'
        }
        
        response = handle_request(request, db_service_override=temp_db)

        assert 'data' in response
        assert 'symbols' in response
        assert len(response['data']) == 8  # AAPL (3) + MSFT (3) + GOOGL (2)
        assert len(response['symbols']) == 3  # AAPL, MSFT, GOOGL
        
        # Check all dates are within the range
        for item in response['data']:
            assert start_date <= item['timestamp'] <= end_date
    
    def test_get_price_data_no_data_in_range(self, temp_db):
        """Test getting price data when no data exists in the specified range"""
        start_date = int(datetime(2024, 1, 1).timestamp())  # Future date
        end_date = int(datetime(2024, 1, 31).timestamp())
        
        request = {
            'action': 'get-price-data',
            'data': {
                'symbol': 'AAPL',
                'limit': 100,
                'offset': 0,
                'start_date': start_date,
                'end_date': end_date
            },
            'requestId': 'test-6'
        }
        
        response = handle_request(request, db_service_override=temp_db)

        assert 'data' in response
        assert len(response['data']) == 0  # No data expected
        
        # Check that the response contains all symbols (not just AAPL)
        # because we always return all available symbols in database
        assert 'symbols' in response
        assert 'AAPL' in response['symbols']
        assert 'MSFT' in response['symbols']
        assert 'GOOGL' in response['symbols']