import time
import pandas as pd
from backend.main import handle_request


def test_run_backtest_signals_shape_smoke():
    # Minimal smoke: invoke run-backtest with a simple SMA crossover spec.
    # This test doesn't assert specific entries (depends on DB), but validates response shape.
    req = {
        'action': 'run-backtest',
        'data': {
            'scanner_spec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': [
                    {
                        'op': 'crossover',
                        'type': 'CROSSES_ABOVE',
                        'left': { 'type': 'indicator', 'name': 'SMA', 'params': { 'period': 5, 'src': { 'type': 'attr', 'name': 'close' } } },
                        'right': { 'type': 'indicator', 'name': 'SMA', 'params': { 'period': 10, 'src': { 'type': 'attr', 'name': 'close' } } }
                    }
                ]
            },
            'symbol': 'TEST',
            'timeframe': '1D',
        },
        'requestId': 'rb-smoke-1'
    }
    res = handle_request(req)
    assert 'error' not in res, res.get('error')
    assert res.get('requestId') == 'rb-smoke-1'
    assert 'signals' in res
    sig = res['signals']
    assert isinstance(sig, dict)
    assert sig.get('symbol') == 'TEST'
    assert 'entries' in sig and isinstance(sig['entries'], list)
    # entries are { timestamp, price }
    for e in sig['entries']:
        assert 'timestamp' in e and 'price' in e
