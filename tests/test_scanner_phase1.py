import sqlite3
import time
from pathlib import Path

import pandas as pd

from backend.main import handle_request, DatabaseService


def seed_small_db(tmp_db_dir: Path):
    service = DatabaseService(db_dir=str(tmp_db_dir))
    with sqlite3.connect(service.market_db_path) as conn:
        # Insert two symbols with simple sequences
        now = int(time.time())
        rows = []
        # SYM1 increasing close to trigger SMA(2) > SMA(3) on last bar perhaps
        prices1 = [10, 11, 12, 13, 14]
        for i, c in enumerate(prices1):
            ts = now - (len(prices1) - i) * 86400
            rows.append(('SYM1', ts, c-0.5, c+0.5, c-1, c, 1000 + i))
        # SYM2 flat
        prices2 = [20, 20, 20, 20, 20]
        for i, c in enumerate(prices2):
            ts = now - (len(prices2) - i) * 86400
            rows.append(('SYM2', ts, c-0.5, c+0.5, c-1, c, 1000 + i))
        conn.executemany(
            'INSERT OR REPLACE INTO price_data (symbol, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)',
            rows
        )
        conn.commit()
    return service


def test_compare_close_gt_const(tmp_path):
    service = seed_small_db(tmp_path)

    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': ['SYM1', 'SYM2'],
                'filters': [
                    {
                        'op': 'compare',
                        'cmp': '>',
                        'left': { 'type': 'attr', 'name': 'close' },
                        'right': { 'type': 'const', 'value': 12 }
                    }
                ]
            },
            'options': { 'latestOnly': True }
        },
        'requestId': 'scan-phase1-compare'
    }
    res = handle_request(req, db_service_override=service)
    assert 'error' not in res
    syms = {r['symbol'] for r in res.get('results', [])}
    assert 'SYM1' in syms


def test_sma_cross(tmp_path):
    service = seed_small_db(tmp_path)
    req = {
        'action': 'run-scan',
        'data': {
            'scannerSpec': {
                'timeframe': '1D',
                'universe': ['SYM1', 'SYM2'],
                'filters': [
                    {
                        'op': 'crossover',
                        'type': 'CROSSES_ABOVE',
                        'left': { 'type': 'indicator', 'name': 'SMA', 'params': { 'src': { 'type': 'attr', 'name': 'close' }, 'period': 2 } },
                        'right': { 'type': 'indicator', 'name': 'SMA', 'params': { 'src': { 'type': 'attr', 'name': 'close' }, 'period': 3 } }
                    }
                ]
            },
            'options': { 'latestOnly': True }
        },
        'requestId': 'scan-phase1-cross'
    }
    res = handle_request(req, db_service_override=service)
    assert 'error' not in res
    # SYM1 trending up is more likely to have SMA2 crossing above SMA3 on recent bars than SYM2 flat
    syms = {r['symbol'] for r in res.get('results', [])}
    assert 'SYM1' in syms
