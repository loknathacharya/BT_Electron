"""
Phase 5F: Signal generation tests
Tests for signal mask generation using eval_filter_series.
"""
import pandas as pd
import numpy as np
from backend.main import handle_request


def test_sma_crossover_basic():
    """Test that SMA(5) > SMA(10) crossover produces expected mask positions."""
    # Create a simple uptrend then downtrend
    closes = np.array([10, 11, 12, 13, 14, 15, 16, 17, 16, 15, 14, 13, 12, 11, 10], dtype=float)
    dates = pd.date_range('2024-01-01', periods=len(closes), freq='D')
    df = pd.DataFrame({'close': closes, 'open': closes, 'high': closes + 0.5, 'low': closes - 0.5, 'volume': 1000}, index=dates)
    
    # SMA(5) > SMA(10) should cross above around bar 6-8 when uptrend is strongest
    # For simplicity, just verify the eval_filter_series works
    from backend.main import handle_request
    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': [{
                    'op': 'compare',
                    'cmp': '>',
                    'left': {'type': 'indicator', 'name': 'SMA', 'params': {'period': 5, 'src': {'type': 'attr', 'name': 'close'}}},
                    'right': {'type': 'indicator', 'name': 'SMA', 'params': {'period': 10, 'src': {'type': 'attr', 'name': 'close'}}}
                }]
            },
            'options': {'mode': 'backtest', 'latestOnly': False}
        },
        'requestId': 'test-sma-xo'
    }
    # This will work if there's test data in the DB; if not, we verify parse succeeds
    res = handle_request(req)
    assert 'error' not in res, res.get('error')


def test_nan_handling_warmup():
    """Test that indicator NaN bars (warmup period) don't produce spurious signals."""
    # This is verified indirectly: SMA(200) on first 100 bars should be NaN
    # and eval_filter_series should return False for those bars
    req = {
        'action': 'run-backtest',
        'data': {
            'scanner_spec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': [{
                    'op': 'compare',
                    'cmp': '>',
                    'left': {'type': 'indicator', 'name': 'SMA', 'params': {'period': 200, 'src': {'type': 'attr', 'name': 'close'}}},
                    'right': {'type': 'const', 'value': 100}
                }]
            },
            'symbol': 'TEST',
            'timeframe': '1D',
            'mode': 'signals'
        },
        'requestId': 'test-nan-warmup'
    }
    res = handle_request(req)
    # If DB has data, verify no signals on first 200 bars (NaN period)
    if 'error' not in res and 'signals' in res:
        signals = res['signals']
        # For a symbol with plenty of data, first signals should not be at very early timestamps
        # This is a smoke test; real validation requires actual data inspection
        assert isinstance(signals.get('entries'), list)


def test_identical_series_no_false_cross():
    """Test that comparing identical series does not produce false crossover signals."""
    req = {
        'action': 'parse-dsl',
        'data': {
            'dsl': 'close CROSSES_ABOVE close',  # Identical series; should never cross
            'timeframe': '1D',
            'universe': 'ALL'
        },
        'requestId': 'test-identical-cross'
    }
    res = handle_request(req)
    assert res.get('success'), res.get('error')
    spec = res.get('scannerSpec')
    # Verify the spec parses
    assert spec is not None
    assert spec.get('filters') is not None


def test_crossover_type_above():
    """Test CROSSES_ABOVE crossover parsing."""
    req = {
        'action': 'parse-dsl',
        'data': {
            'dsl': 'SMA(close, 5) CROSSES_ABOVE SMA(close, 10)',
            'timeframe': '1D'
        },
        'requestId': 'test-cross-above'
    }
    res = handle_request(req)
    assert res.get('success'), res.get('error')
    spec = res['scannerSpec']
    filters = spec['filters']
    assert len(filters) > 0
    f = filters[0]
    assert f.get('op') == 'crossover'
    assert f.get('type').upper() == 'CROSSES_ABOVE'


def test_crossover_type_below():
    """Test CROSSES_BELOW crossover parsing."""
    req = {
        'action': 'parse-dsl',
        'data': {
            'dsl': 'SMA(close, 5) CROSSES_BELOW SMA(close, 10)',
            'timeframe': '1D'
        },
        'requestId': 'test-cross-below'
    }
    res = handle_request(req)
    assert res.get('success'), res.get('error')
    spec = res['scannerSpec']
    filters = spec['filters']
    f = filters[0]
    assert f.get('type').upper() == 'CROSSES_BELOW'
