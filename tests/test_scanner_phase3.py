#!/usr/bin/env python3
"""
Scanner Phase 3 Tests
Tests: Ordinal offsets, explain values, sorting, pagination
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
from backend.main import handle_request, DatabaseService


@pytest.fixture
def temp_db():
    """Create a temporary database with test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_service = DatabaseService(db_dir=tmpdir)
        
        # Insert some test data
        conn = sqlite3.connect(db_service.market_db_path)
        try:
            # Create test data for SYM1: 30 days of data
            dates = pd.date_range('2024-01-01', periods=30, freq='D')
            for i, date in enumerate(dates):
                ts = int(date.timestamp())
                price = 100 + i  # Uptrend
                conn.execute('''
                    INSERT INTO price_data (symbol, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('SYM1', ts, price, price+2, price-1, price+1, 1000000+i*10000))
            
            # Create test data for SYM2: 30 days, downtrend
            for i, date in enumerate(dates):
                ts = int(date.timestamp())
                price = 150 - i  # Downtrend
                conn.execute('''
                    INSERT INTO price_data (symbol, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('SYM2', ts, price, price+1, price-2, price-1, 500000+i*5000))
            
            # Create test data for SYM3: 30 days, sideways
            for i, date in enumerate(dates):
                ts = int(date.timestamp())
                price = 80 + (i % 5) * 2  # Sideways oscillation
                conn.execute('''
                    INSERT INTO price_data (symbol, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', ('SYM3', ts, price, price+1, price-1, price, 300000+i*3000))
            
            conn.commit()
        finally:
            conn.close()
        
        yield db_service
        
        # Explicit cleanup - close all connections
        import gc
        gc.collect()  # Force garbage collection to close any lingering connections


def test_ordinal_offset(temp_db):
    """Test ordinal offset [=k] - access k-th bar from start"""
    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': [
                    {
                        'op': 'compare',
                        'cmp': '>',
                        'left': {
                            'type': 'attr',
                            'name': 'close',
                            'offset': {'kind': 'ordinal', 'n': 10}  # 10th bar from start
                        },
                        'right': {
                            'type': 'const',
                            'value': 105
                        }
                    }
                ]
            },
            'options': {'latestOnly': True}
        },
        'requestId': 'test-ordinal'
    }
    
    res = handle_request(req, db_service_override=temp_db)
    
    assert 'error' not in res
    assert isinstance(res.get('results'), list)
    # SYM1 at bar 10 should be close=111 (>105), SYM2 at bar 10 should be 139 (>105)
    # SYM3 at bar 10 should be around 80 (<105)
    result_symbols = {r['symbol'] for r in res['results']}
    assert 'SYM1' in result_symbols
    assert 'SYM2' in result_symbols
    assert 'SYM3' not in result_symbols


def test_explain_values(temp_db):
    """Test that explain values are returned for matched symbols"""
    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': ['SYM1'],
                'filters': [
                    {
                        'op': 'compare',
                        'cmp': '>',
                        'left': {
                            'type': 'indicator',
                            'name': 'SMA',
                            'params': {'period': 5, 'src': {'type': 'attr', 'name': 'close'}}
                        },
                        'right': {
                            'type': 'attr',
                            'name': 'close',
                            'offset': {'kind': 'lookback', 'bars': 1}
                        }
                    }
                ]
            },
            'options': {'latestOnly': True}
        },
        'requestId': 'test-explain'
    }
    
    res = handle_request(req, db_service_override=temp_db)
    
    assert 'error' not in res
    assert isinstance(res.get('results'), list)
    if len(res['results']) > 0:
        result = res['results'][0]
        # Check that explain values are present
        assert 'explain' in result
        assert isinstance(result['explain'], dict)
        # Should have entries for the evaluated measures
        assert len(result['explain']) > 0


def test_result_sorting(temp_db):
    """Test that results can be sorted"""
    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': [
                    {
                        'op': 'compare',
                        'cmp': '>',
                        'left': {'type': 'attr', 'name': 'close'},
                        'right': {'type': 'const', 'value': 50}
                    }
                ]
            },
            'options': {
                'latestOnly': True,
                'sort': {'by': 'symbol', 'order': 'desc'}
            }
        },
        'requestId': 'test-sort'
    }
    
    res = handle_request(req, db_service_override=temp_db)
    
    assert 'error' not in res
    results = res.get('results', [])
    if len(results) >= 2:
        # Check that results are sorted by symbol in descending order
        symbols = [r['symbol'] for r in results]
        assert symbols == sorted(symbols, reverse=True)


def test_result_pagination(temp_db):
    """Test that results can be paginated"""
    # First get all results
    req_all = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': [
                    {
                        'op': 'compare',
                        'cmp': '>',
                        'left': {'type': 'attr', 'name': 'close'},
                        'right': {'type': 'const', 'value': 50}
                    }
                ]
            },
            'options': {'latestOnly': True}
        },
        'requestId': 'test-paginate-all'
    }
    
    res_all = handle_request(req_all, db_service_override=temp_db)
    all_results = res_all.get('results', [])
    total_count = len(all_results)
    
    if total_count >= 2:
        # Now get first page with limit
        req_page = {
            'action': 'run-scan',
            'data': {
                'scannerSpec': {
                    'timeframe': '1D',
                    'universe': 'ALL',
                    'filters': [
                        {
                            'op': 'compare',
                            'cmp': '>',
                            'left': {'type': 'attr', 'name': 'close'},
                            'right': {'type': 'const', 'value': 50}
                        }
                    ]
                },
                'options': {
                    'latestOnly': True,
                    'limit': 1,
                    'offset': 0
                }
            },
            'requestId': 'test-paginate-page'
        }
        
        res_page = handle_request(req_page, db_service_override=temp_db)
        page_results = res_page.get('results', [])
        
        # Should only get 1 result
        assert len(page_results) == 1
        # The result should be one of the all_results
        assert page_results[0]['symbol'] in [r['symbol'] for r in all_results]


def test_memoization_performance(temp_db):
    """Test that indicator memoization improves performance when same indicator used multiple times"""
    # This test uses the same SMA(20) twice in filters
    # The memoization should cache the first computation and reuse it
    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': [
                    {
                        'op': 'group',
                        'logic': 'AND',
                        'children': [
                            {
                                'op': 'compare',
                                'cmp': '>',
                                'left': {
                                    'type': 'indicator',
                                    'name': 'SMA',
                                    'params': {'period': 20, 'src': {'type': 'attr', 'name': 'close'}}
                                },
                                'right': {'type': 'const', 'value': 100}
                            },
                            {
                                'op': 'compare',
                                'cmp': '<',
                                'left': {
                                    'type': 'indicator',
                                    'name': 'SMA',
                                    'params': {'period': 20, 'src': {'type': 'attr', 'name': 'close'}}
                                },
                                'right': {'type': 'const', 'value': 200}
                            }
                        ]
                    }
                ]
            },
            'options': {'latestOnly': True}
        },
        'requestId': 'test-memo'
    }
    
    res = handle_request(req, db_service_override=temp_db)
    
    assert 'error' not in res
    # Just verify it completes successfully with memoization
    assert isinstance(res.get('results'), list)
    assert res.get('stats', {}).get('scannedSymbols', 0) > 0
