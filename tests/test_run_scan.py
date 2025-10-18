import pytest
from backend.main import handle_request


def test_run_scan_skeleton_returns_empty_results():
    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': 'ALL',
                'filters': []
            },
            'options': { 'latestOnly': True }
        },
        'requestId': 'scan-basic-1'
    }
    res = handle_request(req)
    assert 'error' not in res
    assert isinstance(res.get('results'), list)
    assert isinstance(res.get('stats'), dict)
    assert res['stats'].get('scannedSymbols') == 0
    assert res.get('requestId') == 'scan-basic-1'
