"""
Phase 6: Parameter Optimization
Grid search, random search, and walk-forward testing for backtest strategies.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import itertools
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import copy


def generate_parameter_grid(param_ranges: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate all combinations of parameters from ranges.
    
    Args:
        param_ranges: Dict with parameter names as keys and ranges as values.
                     Example: {'sma_fast': [10, 20, 30], 'sma_slow': [50, 100, 200]}
    
    Returns:
        List of parameter dictionaries, one for each combination.
    """
    if not param_ranges:
        return [{}]
    
    keys = list(param_ranges.keys())
    values = [param_ranges[k] for k in keys]
    
    # Generate cartesian product
    combinations = list(itertools.product(*values))
    
    # Convert to list of dicts
    result = []
    for combo in combinations:
        result.append({keys[i]: combo[i] for i in range(len(keys))})
    
    return result


def generate_random_parameters(param_ranges: Dict[str, Any], n_samples: int = 100, seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """Generate random parameter combinations from ranges.
    
    Args:
        param_ranges: Dict with parameter names and their ranges.
                     Can be list (discrete) or tuple (min, max, step) for continuous.
        n_samples: Number of random samples to generate.
        seed: Random seed for reproducibility.
    
    Returns:
        List of parameter dictionaries.
    """
    if seed is not None:
        np.random.seed(seed)
    
    if not param_ranges:
        return [{}]
    
    result = []
    for _ in range(n_samples):
        params = {}
        for key, value_range in param_ranges.items():
            if isinstance(value_range, list):
                # Discrete values
                params[key] = np.random.choice(value_range)
            elif isinstance(value_range, tuple) and len(value_range) == 3:
                # Continuous range: (min, max, step)
                min_val, max_val, step = value_range
                n_steps = int((max_val - min_val) / step) + 1
                params[key] = min_val + np.random.randint(0, n_steps) * step
            else:
                raise ValueError(f"Invalid range format for parameter '{key}': {value_range}")
        result.append(params)
    
    return result


def apply_parameters_to_spec(base_spec: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Apply parameter values to a scanner spec by replacing variable references.
    
    Args:
        base_spec: Base scanner spec (DSL JSON).
        params: Parameter values to apply.
    
    Returns:
        New spec with parameters substituted.
    """
    spec = copy.deepcopy(base_spec)
    
    # Recursively replace variables in the spec
    def replace_vars(obj):
        if isinstance(obj, dict):
            # Check if this is a variable reference: {"type": "variable", "name": "param_name"}
            if obj.get('type') == 'variable' and obj.get('name') in params:
                # Replace with actual value
                param_value = params[obj['name']]
                return {'type': 'number', 'value': param_value}
            else:
                # Recurse into dict values
                return {k: replace_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_vars(item) for item in obj]
        else:
            return obj
    
    return replace_vars(spec)


def split_data_for_walk_forward(
    start_date: str,
    end_date: str,
    in_sample_days: int = 180,
    out_sample_days: int = 60,
    step_days: int = 30
) -> List[Tuple[str, str, str, str]]:
    """Generate date ranges for walk-forward testing.
    
    Args:
        start_date: Overall start date (YYYY-MM-DD).
        end_date: Overall end date (YYYY-MM-DD).
        in_sample_days: Days for optimization (training).
        out_sample_days: Days for testing.
        step_days: Days to advance between windows.
    
    Returns:
        List of tuples: (in_start, in_end, out_start, out_end).
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    windows = []
    current_start = start_dt
    
    while True:
        in_end = current_start + timedelta(days=in_sample_days)
        out_start = in_end
        out_end = out_start + timedelta(days=out_sample_days)
        
        if out_end > end_dt:
            break
        
        windows.append((
            current_start.strftime('%Y-%m-%d'),
            in_end.strftime('%Y-%m-%d'),
            out_start.strftime('%Y-%m-%d'),
            out_end.strftime('%Y-%m-%d')
        ))
        
        current_start += timedelta(days=step_days)
    
    return windows


def rank_results(results: List[Dict[str, Any]], metric: str = 'sharpe_ratio', ascending: bool = False) -> List[Dict[str, Any]]:
    """Rank optimization results by a specific metric.
    
    Args:
        results: List of optimization result dicts with 'metrics' key.
        metric: Metric to rank by (e.g., 'sharpe_ratio', 'total_return', 'profit_factor').
        ascending: If True, lower values are better (e.g., max_drawdown).
    
    Returns:
        Sorted list of results.
    """
    # Filter results that have the metric
    valid_results = [r for r in results if metric in r.get('metrics', {})]
    
    if not valid_results:
        return results
    
    # Sort by metric
    sorted_results = sorted(
        valid_results,
        key=lambda r: r['metrics'][metric],
        reverse=not ascending
    )
    
    return sorted_results


def calculate_optimization_stats(results: List[Dict[str, Any]], metric: str = 'sharpe_ratio') -> Dict[str, Any]:
    """Calculate statistics across optimization results.
    
    Args:
        results: List of optimization result dicts.
        metric: Metric to analyze.
    
    Returns:
        Dict with min, max, mean, median, std of the metric.
    """
    values = [r['metrics'][metric] for r in results if metric in r.get('metrics', {})]
    
    if not values:
        return {
            'count': 0,
            'min': None,
            'max': None,
            'mean': None,
            'median': None,
            'std': None
        }
    
    return {
        'count': len(values),
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'mean': float(np.mean(values)),
        'median': float(np.median(values)),
        'std': float(np.std(values))
    }


def extract_best_parameters(results: List[Dict[str, Any]], metric: str = 'sharpe_ratio', top_n: int = 10) -> List[Dict[str, Any]]:
    """Extract top N parameter sets by metric.
    
    Args:
        results: List of optimization result dicts.
        metric: Metric to optimize.
        top_n: Number of top results to return.
    
    Returns:
        List of top N results with parameters and metrics.
    """
    ranked = rank_results(results, metric=metric, ascending=False)
    
    top_results = []
    for result in ranked[:top_n]:
        top_results.append({
            'parameters': result.get('parameters', {}),
            'metrics': result.get('metrics', {}),
            'rank': len(top_results) + 1
        })
    
    return top_results


def validate_parameter_ranges(param_ranges: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate parameter range specifications.
    
    Args:
        param_ranges: Parameter ranges to validate.
    
    Returns:
        (is_valid, error_message)
    """
    if not param_ranges:
        return False, "Parameter ranges cannot be empty"
    
    for key, value_range in param_ranges.items():
        if isinstance(value_range, list):
            if not value_range:
                return False, f"Parameter '{key}' has empty list"
            if not all(isinstance(v, (int, float)) for v in value_range):
                return False, f"Parameter '{key}' list must contain only numbers"
        elif isinstance(value_range, tuple):
            if len(value_range) != 3:
                return False, f"Parameter '{key}' tuple must have 3 elements (min, max, step)"
            min_val, max_val, step = value_range
            if not all(isinstance(v, (int, float)) for v in [min_val, max_val, step]):
                return False, f"Parameter '{key}' tuple values must be numbers"
            if min_val >= max_val:
                return False, f"Parameter '{key}' min must be less than max"
            if step <= 0:
                return False, f"Parameter '{key}' step must be positive"
        else:
            return False, f"Parameter '{key}' must be list or (min, max, step) tuple"
    
    return True, None
