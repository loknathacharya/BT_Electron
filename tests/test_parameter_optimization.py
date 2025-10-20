"""
Phase 6: Parameter optimization tests
Tests for grid search, random search, parameter application, and walk-forward testing.
"""
import pytest
from backend.parameter_optimizer import (
    generate_parameter_grid,
    generate_random_parameters,
    apply_parameters_to_spec,
    split_data_for_walk_forward,
    rank_results,
    extract_best_parameters,
    calculate_optimization_stats,
    validate_parameter_ranges
)


def test_generate_parameter_grid():
    """Test that grid generation creates all combinations."""
    param_ranges = {
        'sma_fast': [10, 20],
        'sma_slow': [50, 100]
    }
    
    grid = generate_parameter_grid(param_ranges)
    
    # Should generate 2 x 2 = 4 combinations
    assert len(grid) == 4
    
    # Check all combinations are present
    assert {'sma_fast': 10, 'sma_slow': 50} in grid
    assert {'sma_fast': 10, 'sma_slow': 100} in grid
    assert {'sma_fast': 20, 'sma_slow': 50} in grid
    assert {'sma_fast': 20, 'sma_slow': 100} in grid


def test_generate_parameter_grid_single_param():
    """Test grid generation with single parameter."""
    param_ranges = {'threshold': [0.5, 1.0, 1.5]}
    
    grid = generate_parameter_grid(param_ranges)
    
    assert len(grid) == 3
    assert {'threshold': 0.5} in grid
    assert {'threshold': 1.0} in grid
    assert {'threshold': 1.5} in grid


def test_generate_parameter_grid_empty():
    """Test grid generation with no parameters."""
    grid = generate_parameter_grid({})
    
    assert len(grid) == 1
    assert grid[0] == {}


def test_generate_random_parameters():
    """Test random parameter generation."""
    param_ranges = {
        'sma_fast': [10, 20, 30],
        'sma_slow': [50, 100, 200]
    }
    
    random_params = generate_random_parameters(param_ranges, n_samples=5, seed=42)
    
    assert len(random_params) == 5
    for params in random_params:
        assert 'sma_fast' in params
        assert 'sma_slow' in params
        assert params['sma_fast'] in [10, 20, 30]
        assert params['sma_slow'] in [50, 100, 200]


def test_generate_random_parameters_continuous():
    """Test random parameter generation with continuous ranges."""
    param_ranges = {
        'threshold': (0.5, 2.0, 0.1)  # min, max, step
    }
    
    random_params = generate_random_parameters(param_ranges, n_samples=10, seed=42)
    
    assert len(random_params) == 10
    for params in random_params:
        assert 'threshold' in params
        assert 0.5 <= params['threshold'] <= 2.0
        # Check it's within valid range and follows step pattern
        normalized = params['threshold'] - 0.5
        assert abs(normalized - round(normalized / 0.1) * 0.1) < 0.01


def test_apply_parameters_to_spec():
    """Test applying parameters to a scanner spec."""
    base_spec = {
        'filters': [
            {
                'op': 'compare',
                'cmp': '>',
                'left': {
                    'type': 'indicator',
                    'name': 'sma',
                    'params': [{'type': 'variable', 'name': 'sma_fast'}]
                },
                'right': {
                    'type': 'indicator',
                    'name': 'sma',
                    'params': [{'type': 'variable', 'name': 'sma_slow'}]
                }
            }
        ]
    }
    
    params = {'sma_fast': 20, 'sma_slow': 100}
    
    result_spec = apply_parameters_to_spec(base_spec, params)
    
    # Check that variables were replaced
    left_params = result_spec['filters'][0]['left']['params']
    right_params = result_spec['filters'][0]['right']['params']
    
    assert left_params[0] == {'type': 'number', 'value': 20}
    assert right_params[0] == {'type': 'number', 'value': 100}


def test_apply_parameters_nested():
    """Test applying parameters in nested structures."""
    base_spec = {
        'filters': [
            {
                'op': 'and',
                'operands': [
                    {
                        'op': 'compare',
                        'cmp': '>',
                        'left': {'type': 'attr', 'name': 'close'},
                        'right': {'type': 'variable', 'name': 'threshold'}
                    },
                    {
                        'op': 'compare',
                        'cmp': '<',
                        'left': {'type': 'attr', 'name': 'volume'},
                        'right': {'type': 'variable', 'name': 'volume_limit'}
                    }
                ]
            }
        ]
    }
    
    params = {'threshold': 100, 'volume_limit': 1000000}
    
    result_spec = apply_parameters_to_spec(base_spec, params)
    
    operands = result_spec['filters'][0]['operands']
    assert operands[0]['right'] == {'type': 'number', 'value': 100}
    assert operands[1]['right'] == {'type': 'number', 'value': 1000000}


def test_split_data_for_walk_forward():
    """Test walk-forward date splitting."""
    windows = split_data_for_walk_forward(
        start_date='2023-01-01',
        end_date='2024-01-01',
        in_sample_days=180,
        out_sample_days=60,
        step_days=60
    )
    
    # Should generate at least one window
    assert len(windows) > 0
    
    # Check first window structure
    in_start, in_end, out_start, out_end = windows[0]
    
    assert in_start == '2023-01-01'
    assert out_start == in_end  # Out-sample starts where in-sample ends
    
    # All dates should be in YYYY-MM-DD format
    for window in windows:
        for date_str in window:
            parts = date_str.split('-')
            assert len(parts) == 3
            assert len(parts[0]) == 4  # year
            assert len(parts[1]) == 2  # month
            assert len(parts[2]) == 2  # day


def test_rank_results():
    """Test ranking optimization results."""
    results = [
        {'parameters': {'a': 1}, 'metrics': {'sharpe_ratio': 1.5, 'total_return': 10}},
        {'parameters': {'a': 2}, 'metrics': {'sharpe_ratio': 2.0, 'total_return': 15}},
        {'parameters': {'a': 3}, 'metrics': {'sharpe_ratio': 1.0, 'total_return': 8}},
    ]
    
    ranked = rank_results(results, metric='sharpe_ratio', ascending=False)
    
    # Should be sorted by sharpe_ratio descending
    assert ranked[0]['metrics']['sharpe_ratio'] == 2.0
    assert ranked[1]['metrics']['sharpe_ratio'] == 1.5
    assert ranked[2]['metrics']['sharpe_ratio'] == 1.0


def test_rank_results_ascending():
    """Test ranking with ascending order (e.g., drawdown)."""
    results = [
        {'parameters': {'a': 1}, 'metrics': {'max_drawdown': -10}},
        {'parameters': {'a': 2}, 'metrics': {'max_drawdown': -5}},
        {'parameters': {'a': 3}, 'metrics': {'max_drawdown': -15}},
    ]
    
    ranked = rank_results(results, metric='max_drawdown', ascending=True)
    
    # Should be sorted by max_drawdown ascending (less negative is better)
    assert ranked[0]['metrics']['max_drawdown'] == -15
    assert ranked[1]['metrics']['max_drawdown'] == -10
    assert ranked[2]['metrics']['max_drawdown'] == -5


def test_extract_best_parameters():
    """Test extracting top N parameter sets."""
    results = [
        {'parameters': {'a': 1}, 'metrics': {'sharpe_ratio': 1.5}},
        {'parameters': {'a': 2}, 'metrics': {'sharpe_ratio': 2.0}},
        {'parameters': {'a': 3}, 'metrics': {'sharpe_ratio': 1.0}},
        {'parameters': {'a': 4}, 'metrics': {'sharpe_ratio': 1.8}},
    ]
    
    best = extract_best_parameters(results, metric='sharpe_ratio', top_n=2)
    
    assert len(best) == 2
    assert best[0]['parameters'] == {'a': 2}
    assert best[0]['rank'] == 1
    assert best[1]['parameters'] == {'a': 4}
    assert best[1]['rank'] == 2


def test_calculate_optimization_stats():
    """Test calculating statistics across results."""
    results = [
        {'parameters': {'a': 1}, 'metrics': {'sharpe_ratio': 1.0}},
        {'parameters': {'a': 2}, 'metrics': {'sharpe_ratio': 2.0}},
        {'parameters': {'a': 3}, 'metrics': {'sharpe_ratio': 3.0}},
    ]
    
    stats = calculate_optimization_stats(results, metric='sharpe_ratio')
    
    assert stats['count'] == 3
    assert stats['min'] == 1.0
    assert stats['max'] == 3.0
    assert stats['mean'] == 2.0
    assert stats['median'] == 2.0


def test_validate_parameter_ranges_valid():
    """Test validation of valid parameter ranges."""
    param_ranges = {
        'sma_fast': [10, 20, 30],
        'threshold': (0.5, 2.0, 0.1)
    }
    
    is_valid, error_msg = validate_parameter_ranges(param_ranges)
    
    assert is_valid is True
    assert error_msg is None


def test_validate_parameter_ranges_empty_list():
    """Test validation rejects empty lists."""
    param_ranges = {
        'sma_fast': []
    }
    
    is_valid, error_msg = validate_parameter_ranges(param_ranges)
    
    assert is_valid is False
    assert 'empty list' in error_msg.lower()


def test_validate_parameter_ranges_invalid_tuple():
    """Test validation rejects invalid tuples."""
    param_ranges = {
        'threshold': (0.5, 2.0)  # Missing step
    }
    
    is_valid, error_msg = validate_parameter_ranges(param_ranges)
    
    assert is_valid is False
    assert '3 elements' in error_msg


def test_validate_parameter_ranges_min_max_order():
    """Test validation checks min < max."""
    param_ranges = {
        'threshold': (2.0, 0.5, 0.1)  # min > max
    }
    
    is_valid, error_msg = validate_parameter_ranges(param_ranges)
    
    assert is_valid is False
    assert 'min must be less than max' in error_msg.lower()


def test_validate_parameter_ranges_negative_step():
    """Test validation rejects negative step."""
    param_ranges = {
        'threshold': (0.5, 2.0, -0.1)
    }
    
    is_valid, error_msg = validate_parameter_ranges(param_ranges)
    
    assert is_valid is False
    assert 'step must be positive' in error_msg.lower()


def test_empty_parameter_ranges():
    """Test handling of empty parameter ranges."""
    is_valid, error_msg = validate_parameter_ranges({})
    
    assert is_valid is False
    assert 'cannot be empty' in error_msg.lower()
