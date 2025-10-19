import time
from backend.main import handle_request


def test_run_backtest_simulate_shape_smoke():
    """Smoke test: ensure run-backtest simulate mode returns trades, metrics, equity_curve.
    Does not assert counts since it depends on DB contents.
    """
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
            'mode': 'simulate',
            'backtest_config': {
                'initial_capital': 10000,
                'commission_per_trade': 0.0,
                'position_size_mode': 'percent_capital',
                'position_size_value': 100,
                'stop_loss_percent': 0,
                'take_profit_percent': 0
            }
        },
        'requestId': 'rb-sim-smoke-1'
    }
    res = handle_request(req)
    assert 'error' not in res, res.get('error')
    assert res.get('requestId') == 'rb-sim-smoke-1'
    # Basic shape checks
    assert 'signals' in res and isinstance(res['signals'], dict)
    assert 'trades' in res and isinstance(res['trades'], list)
    assert 'metrics' in res and isinstance(res['metrics'], dict)
    assert 'equity_curve' in res and isinstance(res['equity_curve'], dict)
    eq = res['equity_curve']
    assert 'timestamps' in eq and 'equity' in eq
